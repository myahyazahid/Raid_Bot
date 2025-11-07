import os
import re
import base64
import asyncio
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask
from telebot import TeleBot
from telethon import TelegramClient

# ==========================
# 🔧 CONFIG (ENV)
# ==========================
API_ID     = int(os.getenv("API_ID"))
API_HASH   = os.getenv("API_HASH")
BOT_TOKEN  = os.getenv("BOT_TOKEN")
CHAT_ID    = int(os.getenv("CHAT_ID"))

TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))  # 14–15 WIB
TOPIC_ID_2 = int(os.getenv("TOPIC_ID_2"))  # 17–18 WIB
TOPIC_ID_3 = int(os.getenv("TOPIC_ID_3"))  # 20–21 WIB

# ==========================
# 🔐 RESTORE SESSION USER
# ==========================
if os.getenv("SESSION_DATA"):
    with open("session.session", "wb") as f:
        f.write(base64.b64decode(os.getenv("SESSION_DATA")))

# ==========================
# 🤖 Bots/Clients
# ==========================
bot = TeleBot(BOT_TOKEN)                                   # untuk KIRIM pesan (bot admin)
telethon_client = TelegramClient("session", API_ID, API_HASH)  # untuk BACA pesan/reaksi (akun user)

# ==========================
# ⚙️ SINGLE EVENT LOOP (THREAD)
# ==========================
_loop = asyncio.new_event_loop()

def _loop_runner():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

threading.Thread(target=_loop_runner, daemon=True).start()

async def _telethon_start():
    # Start sekali saja di loop global
    if not telethon_client.is_connected():
        await telethon_client.start()  # LOGIN user (bukan bot)
        me = await telethon_client.get_me()
        print(f"✅ Telethon connected as {me.first_name} (@{getattr(me, 'username','-')})")

def run_async(coro):
    """Jalankan coroutine di loop global secara sinkron dari route Flask."""
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()

# Start telethon saat proses naik
run_async(_telethon_start())

# ==========================
# 🧠 CORE: CEK REAKSI (WIB window)
# ==========================
async def check_reactions(chat_id: int, topic_id: int, start_hour_wib: int, end_hour_wib: int, sesi_nama: str):
    try:
        if not telethon_client.is_connected():
            await telethon_client.connect()

        # WIB -> UTC window (untuk HARI INI)
        now_utc = datetime.now(timezone.utc)
        today_wib = (now_utc + timedelta(hours=7)).date()
        tz_wib = timezone(timedelta(hours=7))

        start_wib = datetime(today_wib.year, today_wib.month, today_wib.day, start_hour_wib, 0, 0, tzinfo=tz_wib)
        end_wib   = datetime(today_wib.year, today_wib.month, today_wib.day, end_hour_wib,   0, 0, tzinfo=tz_wib)
        start_utc = start_wib.astimezone(timezone.utc)
        end_utc   = end_wib.astimezone(timezone.utc)

        print(f"🔎 {sesi_nama} | WIB {start_wib.time()}–{end_wib.time()} | UTC {start_utc.time()}–{end_utc.time()} | topic={topic_id}")

        # Kumpulkan pesan link dalam window & topic
        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, offset_date=end_utc, reverse=True):
            # msg.date timezone-aware (UTC)
            if msg.date < start_utc:
                break
            if getattr(msg, "top_msg_id", None) != topic_id:
                continue
            if (msg.text and "http" in msg.text) or (msg.media and msg.caption and "http" in msg.caption):
    link_messages.append(msg)

           

        # Kumpulkan reaktor
        all_reactors = set()
        for m in link_messages:
            if m.reactions:
                async for u in telethon_client.get_reaction_users(chat_id, m.id):
                    if u.username:
                        all_reactors.add(u.username)

        # Pengirim link
        senders = {m.sender.username for m in link_messages if m.sender and m.sender.username}
        not_reacted = senders - all_reactors

        total_links = len(link_messages)
        belum_text = "\n".join(f"- @{u}" for u in sorted(not_reacted)) if not_reacted else "✅ Semua sudah melakukan raid."

        hasil = (
            f"📊 Pengecekan Raid {sesi_nama}\n"
            f"Total links : {total_links}\n"
            f"Belum raid :\n{belum_text}"
        )

        # KIRIM via BOT ADMIN (bisa kirim meski grup ditutup)
        await asyncio.to_thread(bot.send_message, chat_id, hasil, message_thread_id=topic_id)
        print(f"✅ Report terkirim → topic {topic_id}")

    except Exception as e:
        print(f"❌ Error {sesi_nama}: {e}")
        try:
            await asyncio.to_thread(bot.send_message, chat_id, f"❌ Error {sesi_nama}: {e}", message_thread_id=topic_id)
        except Exception:
            pass

# ==========================
# 🌐 FLASK ROUTES
# ==========================
app = Flask(__name__)

@app.route("/")
def home():
    wib_now = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S WIB")
    return f"🚀 Bot up. Sekarang: {wib_now}", 200

@app.route("/status")
def status():
    try:
        me = run_async(telethon_client.get_me())
        # coba kirim ping via bot (silent failure OK)
        try:
            bot.send_message(CHAT_ID, "✅ /status: bot aktif", message_thread_id=TOPIC_ID_1)
        except Exception as _:
            pass
        return f"🟢 Telethon: {me.first_name} (@{getattr(me,'username','-')})", 200
    except Exception as e:
        return f"⚠️ Status error: {e}", 200

# Test: 1 jam terakhir (bisa kapan saja)
@app.route("/test")
def test():
    wib_now = datetime.now(timezone.utc) + timedelta(hours=7)
    start_h = (wib_now - timedelta(hours=1)).hour
    end_h   = wib_now.hour
    run_async(check_reactions(CHAT_ID, TOPIC_ID_1, start_h, end_h, "🧪 Test Mode (1 jam terakhir)"))
    return "✅ Test dijalankan", 200

# Sesi tetap sesuai WIB
@app.route("/sesi1")
def sesi1():
    run_async(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, "🕐 Sesi 1 (14.00–15.00 WIB)"))
    return "✅ Sesi 1 dijalankan", 200

@app.route("/sesi2")
def sesi2():
    run_async(check_reactions(CHAT_ID, TOPIC_ID_2, 17, 18, "🕔 Sesi 2 (17.00–18.00 WIB)"))
    return "✅ Sesi 2 dijalankan", 200

@app.route("/sesi3")
def sesi3():
    run_async(check_reactions(CHAT_ID, TOPIC_ID_3, 20, 21, "🌙 Sesi 3 (20.00–21.00 WIB)"))
    return "✅ Sesi 3 dijalankan", 200

# ==========================
# 🚀 RUN (local only; Render jalankan proses ini juga)
# ==========================
if __name__ == "__main__":
    from waitress import serve  # opsional, tapi Flask dev server juga oke di Render
    serve(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
    # atau:
    # app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

