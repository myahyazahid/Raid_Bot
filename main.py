from flask import Flask
from telethon import TelegramClient
from telebot import TeleBot
from datetime import datetime, timedelta
import asyncio, os, re, threading

app = Flask(__name__)

# ==========================
# 🔧 CONFIG (env variables)
# ==========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = int(os.getenv("CHAT_ID"))         # e.g. -1002632100535
TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))   # e.g. 366
TOPIC_ID_2 = int(os.getenv("TOPIC_ID_2"))
TOPIC_ID_3 = int(os.getenv("TOPIC_ID_3"))

# pyTelegramBotAPI (synchronous)
bot = TeleBot(BOT_TOKEN)

# Telethon client; keep session in /tmp so it survives the container while it's alive
telethon_client = TelegramClient("/tmp/session", API_ID, API_HASH)

# =======================================================
# 🧵 Dedicated asyncio loop running in a background thread
# =======================================================
_loop = asyncio.new_event_loop()

def _loop_runner():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

threading.Thread(target=_loop_runner, daemon=True).start()

async def _telethon_start():
    try:
        if not telethon_client.is_connected():
            await telethon_client.start(bot_token=BOT_TOKEN)
        me = await telethon_client.get_me()
        print(f"✅ Telethon connected as @{getattr(me, 'username', 'bot')} (ID: {me.id})")
    except Exception as e:
        print(f"❌ Telethon connect error: {e}")

# Start Telethon on our dedicated loop
def _ensure_telethon():
    asyncio.run_coroutine_threadsafe(_telethon_start(), _loop).result()

@app.before_first_request
def _boot():
    _ensure_telethon()

# ==========================
# 🧠 Core logic (async)
# ==========================
async def _check_reactions(chat_id: int, topic_id: int, start_hour: int, end_hour: int, sesi_nama: str):
    try:
        if not telethon_client.is_connected():
            await telethon_client.connect()

        # WIB time
        now = datetime.utcnow() + timedelta(hours=7)
        start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time   = now.replace(hour=end_hour,   minute=0, second=0, microsecond=0)

        print(f"🔍 [{sesi_nama}] Window {start_hour}:00–{end_hour}:00 WIB | Topic {topic_id}")

        # Collect link messages inside the time window & topic
        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, offset_date=end_time, reverse=True):
            if msg.date < start_time:
                break
            if getattr(msg, "top_msg_id", None) != topic_id:
                continue
            if msg.text and re.search(r"https?://", msg.text):
                link_messages.append(msg)

        # Collect all reactors across those messages
        all_reactors = set()
        for msg in link_messages:
            if msg.reactions:
                async for u in telethon_client.get_reaction_users(chat_id, msg.id):
                    if u.username:
                        all_reactors.add(u.username)

        # Set of users who posted links
        senders = {
            m.sender.username
            for m in link_messages
            if m.sender and m.sender.username
        }

        not_reacted = senders - all_reactors
        total_links = len(link_messages)

        belum_text = "\n".join(f"- @{u}" for u in sorted(not_reacted)) if not_reacted else "✅ Semua sudah melakukan raid."

        message = (
            f"📊 Pengecekan Raid {sesi_nama}\n"
            f"Total links : {total_links}\n"
            f"Belum raid :\n{belum_text}"
        )

        # Send via TeleBot; run it in a worker so we don't block the Telethon loop
        await asyncio.to_thread(
            bot.send_message,
            chat_id,
            message,
            message_thread_id=topic_id  # MUST be a forum-enabled supergroup to take effect
        )
        print(f"✅ [{sesi_nama}] Report sent to topic {topic_id}")

    except Exception as e:
        print(f"❌ [{sesi_nama}] Error: {e}")
        # Best-effort error notify (to main chat if topic fails)
        try:
            await asyncio.to_thread(
                bot.send_message, chat_id, f"❌ [{sesi_nama}] Error: {e}", message_thread_id=topic_id
            )
        except Exception:
            await asyncio.to_thread(bot.send_message, chat_id, f"❌ [{sesi_nama}] Error: {e}")

# Convenience wrapper for routes (sync → schedule on loop)
def _run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()

# ==========================
# 🌐 Routes (synchronous)
# ==========================
@app.route("/")
def home():
    return "🚀 Raid Bot aktif (single event loop, WIB).", 200

@app.route("/status")
def status():
    try:
        _ensure_telethon()
        me = _run_async(telethon_client.get_me())
        # Try a small ping (to main chat)
        try:
            bot.send_message(CHAT_ID, "✅ /status: bot aktif & bisa kirim pesan")
            ping = "✅ Bot berhasil kirim pesan ke grup."
        except Exception as err:
            ping = f"⚠️ Gagal kirim pesan: {err}"
        return f"🤖 @{getattr(me, 'username', 'bot')} (ID: {me.id})\n{ping}", 200
    except Exception as e:
        return f"❌ Error status: {e}", 200

@app.route("/test")
def test():
    # Check current hour → +1 hour window
    now = datetime.utcnow() + timedelta(hours=7)
    start_hour = now.hour
    end_hour = (start_hour + 1) % 24
    _run_async(_check_reactions(CHAT_ID, TOPIC_ID_1, start_hour, end_hour, "🧪 Test Mode"))
    return f"🧪 Test untuk {start_hour}:00–{end_hour}:00 WIB dijalankan.", 200

@app.route("/sesi1")
def sesi1():
    _run_async(_check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, "🕐 Sesi 1 (14.00–15.00 WIB)"))
    return "✅ Sesi 1 dijalankan.", 200

@app.route("/sesi2")
def sesi2():
    _run_async(_check_reactions(CHAT_ID, TOPIC_ID_2, 17, 18, "🕔 Sesi 2 (17.00–18.00 WIB)"))
    return "✅ Sesi 2 dijalankan.", 200

@app.route("/sesi3")
def sesi3():
    _run_async(_check_reactions(CHAT_ID, TOPIC_ID_3, 20, 21, "🌙 Sesi 3 (20.00–21.00 WIB)"))
    return "✅ Sesi 3 dijalankan.", 200

# ==========================
# 🚀 Run server
# ==========================
if __name__ == "__main__":
    # On Render, Flask is started by your process; this is for local runs
    app.run(host="0.0.0.0", port=10000)
