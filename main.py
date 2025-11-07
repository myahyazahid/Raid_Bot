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
telethon_client = TelegramClient("session", API_ID, API_HASH)  # untuk BACA pesan (akun user)

# ==========================
# ⚙️ SINGLE EVENT LOOP (THREAD)
# ==========================
_loop = asyncio.new_event_loop()

def _loop_runner():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

threading.Thread(target=_loop_runner, daemon=True).start()

async def _telethon_start():
    if not telethon_client.is_connected():
        await telethon_client.start()
        me = await telethon_client.get_me()
        print(f"✅ Telethon connected as {me.first_name} (@{getattr(me, 'username','-')})")

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()

run_async(_telethon_start())

# ==========================
# 🧠 CORE: CEK REAKSI
# ==========================
async def check_reactions(chat_id: int, topic_id: int, start_hour_wib: int, end_hour_wib: int, sesi_nama: str):
    try:
        if not telethon_client.is_connected():
            await telethon_client.connect()

        now_utc = datetime.now(timezone.utc)
        today_wib = (now_utc + timedelta(hours=7)).date()
        tz_wib = timezone(timedelta(hours=7))

        start_wib = datetime(today_wib.year, today_wib.month, today_wib.day, start_hour_wib, 0, 0, tzinfo=tz_wib)
        end_wib   = datetime(today_wib.year, today_wib.month, today_wib.day, end_hour_wib,   0, 0, tzinfo=tz_wib)
        start_utc = start_wib.astimezone(timezone.utc)
        end_utc   = end_wib.astimezone(timezone.utc)

        print(f"🔎 {sesi_nama} | WIB {start_wib.time()}–{end_wib.time()} | UTC {start_utc.time()}–{end_utc.time()} | topic={topic_id}")

        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, offset_date=end_utc, reverse=True):
            if msg.date < start_utc:
                break
            if getattr(msg, "top_msg_id", None) != topic_id:
                continue
            if (msg.text and "http" in msg.text) or (msg.media and msg.caption and "http" in msg.caption):
                link_messages.append(msg)

        all_reactors = set()
        for m in link_messages:
            if m.reactions:
                async for u in telethon_client.get_reaction_users(chat_id, m.id):
                    if u.username:
                        all_reactors.add(u.username)

        senders = {m.sender.username for m in link_messages if m.sender and m.sender.username}
        not_reacted = senders - all_reactors

        total_links = len(link_messages)
        belum_text = "\n".join(f"- @{u}" for u in sorted(not_reacted)) if not_reacted else "✅ Semua sudah melakukan raid."

        hasil = (
            f"📊 Pengecekan Raid {sesi_nama}\n"
            f"Total links : {total_links}\n"
            f"Belum raid :\n{belum_text}"
        )

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
        try:
            bot.send_message(CHAT_ID, "✅ /status: bot aktif", message_thread_id=TOPIC_ID_1)
        except Exception:
            pass
        return f"🟢 Telethon: {me.first_name} (@{getattr(me,'username','-')})", 200
    except Exception as e:
        return f"⚠️ Status error: {e}", 200

@app.route("/test")
def test():
    now_wib = datetime.now(timezone.utc) + timedelta(hours=7)
    start_hour = 0
    end_hour = now_wib.hour + 1
    run_async(check_reactions(CHAT_ID, TOPIC_ID_1, start_hour, end_hour, "🧪 Test Semua Link Hari Ini"))
    return "✅ Test dijalankan", 200

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
# 🧩 DEBUG ROUTE
# ==========================
@app.route("/debug")
def debug():
    async def debug_all():
        try:
            # 1️⃣ Tes koneksi Telethon
            if not telethon_client.is_connected():
                await telethon_client.connect()
            me = await telethon_client.get_me()
            print(f"✅ Telethon aktif sebagai {me.first_name} (@{getattr(me,'username','-')})")

            # 2️⃣ Tes kirim pesan via bot
            try:
                bot.send_message(CHAT_ID, "✅ Bot test: bisa kirim pesan ke grup.", message_thread_id=TOPIC_ID_1)
                print("✅ Bot test: pesan terkirim ke thread.")
            except Exception as e:
                print(f"❌ Bot gagal kirim pesan: {e}")

            # 3️⃣ Ambil semua pesan hari ini di thread target
            now_wib = datetime.now(timezone.utc) + timedelta(hours=7)
            start_of_day_wib = now_wib.replace(hour=0, minute=0, second=0, microsecond=0)
            tz_wib = timezone(timedelta(hours=7))
            start_utc = start_of_day_wib.astimezone(timezone.utc)
            end_utc = now_wib.astimezone(timezone.utc)

            print(f"🔎 Mengambil pesan thread {TOPIC_ID_1} antara {start_utc} - {end_utc} (UTC)")

            link_messages = []
            async for msg in telethon_client.iter_messages(CHAT_ID, offset_date=end_utc, reverse=True):
                if msg.date < start_utc:
                    break
                if getattr(msg, "top_msg_id", None) != TOPIC_ID_1:
                    continue

                preview = (msg.text or msg.message or "[no text]")[:80].replace("\n", " ")
                print(f"[DEBUG] id={msg.id} | date={msg.date} | text={preview}")

                if (msg.text and "http" in msg.text) or (msg.media and msg.caption and "http" in msg.caption):
                    link_messages.append(msg)

            print(f"🔗 Total pesan dengan link: {len(link_messages)}")

            # 4️⃣ Cek reaksi pengguna
            all_reactors = set()
            for m in link_messages:
                if m.reactions:
                    async for u in telethon_client.get_reaction_users(CHAT_ID, m.id):
                        if u.username:
                            all_reactors.add(u.username)
            print(f"👥 Total pengguna kasih reaksi: {len(all_reactors)}")

            hasil = (
                f"🧩 Debug Report\n"
                f"Telethon: {me.first_name}\n"
                f"Thread ID: {TOPIC_ID_1}\n"
                f"Total link ditemukan: {len(link_messages)}\n"
                f"Total pengguna kasih reaksi: {len(all_reactors)}"
            )
            await asyncio.to_thread(bot.send_message, CHAT_ID, hasil, message_thread_id=TOPIC_ID_1)
            print("✅ Debug report dikirim ke Telegram.")

        except Exception as e:
            print(f"❌ Debug error: {e}")
            try:
                await asyncio.to_thread(bot.send_message, CHAT_ID, f"❌ Debug error: {e}", message_thread_id=TOPIC_ID_1)
            except Exception:
                pass

    run_async(debug_all())
    return "🧩 Debug route dijalankan. Cek log di Render + Telegram.", 200

# ==========================
# 🚀 RUN SERVER
# ==========================
if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
