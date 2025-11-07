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
bot = TeleBot(BOT_TOKEN)
telethon_client = TelegramClient("session", API_ID, API_HASH)

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
# 🧠 CORE: CEK REAKSI (FULL FIX)
# ==========================
async def check_reactions(chat_id: int, topic_id: int, start_hour_wib: int, end_hour_wib: int, sesi_nama: str):
    try:
        if not telethon_client.is_connected():
            await telethon_client.connect()

        tz_wib = timezone(timedelta(hours=7))
        now_utc = datetime.now(timezone.utc)
        today_wib = (now_utc + timedelta(hours=7)).date()

        start_wib = datetime(today_wib.year, today_wib.month, today_wib.day, start_hour_wib, 0, 0, tzinfo=tz_wib)
        end_wib   = datetime(today_wib.year, today_wib.month, today_wib.day, end_hour_wib, 0, 0, tzinfo=tz_wib)
        start_utc = start_wib.astimezone(timezone.utc)
        end_utc   = end_wib.astimezone(timezone.utc)

        print(f"🔎 {sesi_nama} | WIB {start_wib.time()}–{end_wib.time()} | topic={topic_id}")

        await telethon_client.get_entity(chat_id)

        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, reverse=True, limit=500):
            if not (start_utc <= msg.date <= end_utc):
                continue

            top_id = getattr(msg, "top_msg_id", None)
            reply_top = getattr(msg, "reply_to_top_id", None)
            reply_msg = getattr(msg, "reply_to_msg_id", None)
            if topic_id not in (top_id, reply_top, reply_msg):
                continue

            text = (msg.text or msg.message or "")
            caption = getattr(msg, "caption", "")
            links = set()

            # 🔗 Ambil semua jenis link (text, caption, hyperlink)
            if "http" in text:
                urls = re.findall(r"https?://\S+", text)
                links.update(urls)
            if "http" in caption:
                urls = re.findall(r"https?://\S+", caption)
                links.update(urls)
            if msg.entities:
                for ent in msg.entities:
                    if hasattr(ent, 'url') and ent.url:
                        links.add(ent.url)

            if links:
                link_messages.append(msg)
                link_preview = ", ".join(list(links)[:2])
                print(f"🔗 [LINK] {msg.id} | {link_preview}")

        print(f"📊 Total link ditemukan: {len(link_messages)}")

        # 👥 Cek siapa yang kasih reaksi
        all_reactors = set()
        for m in link_messages:
            try:
                if hasattr(telethon_client, "get_reaction_users"):
                    async for u in telethon_client.get_reaction_users(chat_id, m.id):
                        if u.username:
                            all_reactors.add(u.username)
                else:
                    # fallback lama (jika Telethon lawas)
                    if hasattr(m, "reactions") and hasattr(m.reactions, "recent_reactions"):
                        for rr in m.reactions.recent_reactions:
                            user = getattr(rr, "peer_id", None)
                            if hasattr(user, "user_id"):
                                u = await telethon_client.get_entity(user.user_id)
                                if u.username:
                                    all_reactors.add(u.username)
            except Exception as err:
                print(f"⚠️ Gagal ambil reaksi di msg {m.id}: {err}")

        senders = {m.sender.username for m in link_messages if m.sender and m.sender.username}
        not_reacted = senders - all_reactors
        belum_text = "\n".join(f"- @{u}" for u in sorted(not_reacted)) if not_reacted else "✅ Semua sudah react."

        hasil = (
            f"📊 Pengecekan Raid {sesi_nama}\n"
            f"Total links : {len(link_messages)}\n"
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
        bot.send_message(CHAT_ID, "✅ /status: bot aktif", message_thread_id=TOPIC_ID_1)
        return f"🟢 Telethon: {me.first_name} (@{getattr(me,'username','-')})", 200
    except Exception as e:
        return f"⚠️ Status error: {e}", 200

@app.route("/threads")
def list_threads():
    async def get_threads():
        try:
            async for dialog in telethon_client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    print(f"📁 {dialog.name} | id={dialog.id}")
            bot.send_message(CHAT_ID, "✅ Daftar thread tampil di Render log", message_thread_id=TOPIC_ID_1)
        except Exception as e:
            print(f"❌ Error list_threads: {e}")
    run_async(get_threads())
    return "🧾 Thread list dikirim ke log Render", 200

@app.route("/test_today")
def test_today():
    now_wib = datetime.now(timezone.utc) + timedelta(hours=7)
    run_async(check_reactions(CHAT_ID, TOPIC_ID_2, 0, now_wib.hour + 1, "🧪 Scan Semua Link Hari Ini"))
    return "✅ Scan semua link hari ini dijalankan", 200

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

@app.route("/debug")
def debug():
    async def debug_all():
        try:
            if not telethon_client.is_connected():
                await telethon_client.connect()
            me = await telethon_client.get_me()
            print(f"✅ Telethon aktif sebagai {me.first_name} (@{getattr(me,'username','-')})")

            await telethon_client.get_entity(CHAT_ID)

            now_wib = datetime.now(timezone.utc) + timedelta(hours=7)
            start_of_day_wib = now_wib.replace(hour=0, minute=0, second=0, microsecond=0)
            tz_wib = timezone(timedelta(hours=7))
            start_utc = start_of_day_wib.astimezone(timezone.utc)
            end_utc = now_wib.astimezone(timezone.utc)

            print(f"🔎 Mengambil pesan thread {TOPIC_ID_1} antara {start_utc} - {end_utc} (UTC)")

            link_messages = []
            async for msg in telethon_client.iter_messages(CHAT_ID, reverse=True, limit=500):
                top_id = getattr(msg, "top_msg_id", None)
                reply_top = getattr(msg, "reply_to_top_id", None)
                if TOPIC_ID_1 not in (top_id, reply_top):
                    continue
                text = (msg.text or msg.message or "")
                caption = getattr(msg, "caption", "")
                links = set()
                if "http" in text:
                    urls = re.findall(r"https?://\S+", text)
                    links.update(urls)
                if "http" in caption:
                    urls = re.findall(r"https?://\S+", caption)
                    links.update(urls)
                if msg.entities:
                    for ent in msg.entities:
                        if hasattr(ent, 'url') and ent.url:
                            links.add(ent.url)
                if links:
                    link_messages.append(msg)
                    print(f"[DEBUG LINK] id={msg.id} | {', '.join(list(links)[:2])}")

            print(f"🔗 Total pesan dengan link: {len(link_messages)}")

            hasil = (
                f"🧩 Debug Report\n"
                f"Telethon: {me.first_name}\n"
                f"Thread ID: {TOPIC_ID_1}\n"
                f"Total link ditemukan: {len(link_messages)}"
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

