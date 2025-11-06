from flask import Flask
from telethon import TelegramClient
from telebot import TeleBot
from datetime import datetime, timedelta
import asyncio, os, re, threading

app = Flask(__name__)

# ==========================
# 🔧 CONFIG
# ==========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = int(os.getenv("CHAT_ID"))
TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))
TOPIC_ID_2 = int(os.getenv("TOPIC_ID_2"))
TOPIC_ID_3 = int(os.getenv("TOPIC_ID_3"))

bot = TeleBot(BOT_TOKEN)
telethon_client = TelegramClient("/tmp/session", API_ID, API_HASH)

# ==========================
# ⚙️ Event Loop Tunggal
# ==========================
_loop = asyncio.new_event_loop()

def loop_runner():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()

threading.Thread(target=loop_runner, daemon=True).start()

async def start_telethon():
    try:
        if not telethon_client.is_connected():
            await telethon_client.start(bot_token=BOT_TOKEN)
        me = await telethon_client.get_me()
        print(f"✅ Telethon connected as @{getattr(me, 'username', 'bot')} (ID: {me.id})")
    except Exception as e:
        print(f"❌ Telethon connect error: {e}")

def ensure_telethon():
    asyncio.run_coroutine_threadsafe(start_telethon(), _loop).result()

# Panggil segera setelah app start
ensure_telethon()

# ==========================
# 🔍 Cek Reaksi
# ==========================
async def check_reactions(chat_id, topic_id, start_hour, end_hour, sesi_nama):
    try:
        if not telethon_client.is_connected():
            await telethon_client.connect()

        now = datetime.utcnow() + timedelta(hours=7)
        start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

        print(f"🔍 [{sesi_nama}] {start_hour}:00–{end_hour}:00 WIB")

        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, offset_date=end_time, reverse=True):
            if msg.date < start_time:
                break
            if getattr(msg, "top_msg_id", None) != topic_id:
                continue
            if msg.text and re.search(r"https?://", msg.text):
                link_messages.append(msg)

        all_reactors = set()
        for msg in link_messages:
            if msg.reactions:
                async for u in telethon_client.get_reaction_users(chat_id, msg.id):
                    if u.username:
                        all_reactors.add(u.username)

        senders = {m.sender.username for m in link_messages if m.sender and m.sender.username}
        not_reacted = senders - all_reactors
        belum_text = "\n".join(f"- @{u}" for u in sorted(not_reacted)) if not_reacted else "✅ Semua sudah melakukan raid."

        msg_text = (
            f"📊 Pengecekan Raid {sesi_nama}\n"
            f"Total links: {len(link_messages)}\n"
            f"Belum raid:\n{belum_text}"
        )

        await asyncio.to_thread(bot.send_message, chat_id, msg_text, message_thread_id=topic_id)
        print(f"✅ [{sesi_nama}] report dikirim ke topic {topic_id}")
    except Exception as e:
        print(f"❌ [{sesi_nama}] Error: {e}")
        await asyncio.to_thread(bot.send_message, chat_id, f"❌ Error: {e}", message_thread_id=topic_id)

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()

# ==========================
# 🌐 ROUTES
# ==========================
@app.route("/")
def home():
    return "🚀 Raid Bot aktif (WIB, Flask 3+)", 200

@app.route("/status")
def status():
    try:
        ensure_telethon()
        me = run_async(telethon_client.get_me())
        bot.send_message(CHAT_ID, "✅ /status: bot aktif & bisa kirim pesan")
        return f"🤖 @{getattr(me, 'username', 'bot')} (ID: {me.id})\n✅ Bot berhasil kirim pesan ke grup.", 200
    except Exception as e:
        return f"❌ Error status: {e}", 200

@app.route("/test")
def test():
    now = datetime.utcnow() + timedelta(hours=7)
    start_hour = now.hour
    end_hour = (start_hour + 1) % 24
    run_async(check_reactions(CHAT_ID, TOPIC_ID_1, start_hour, end_hour, "🧪 Test Mode"))
    return f"🧪 Test {start_hour}:00–{end_hour}:00 WIB dijalankan.", 200

@app.route("/sesi1")
def sesi1():
    run_async(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, "🕐 Sesi 1 (14.00–15.00 WIB)"))
    return "✅ Sesi 1 dijalankan.", 200

@app.route("/sesi2")
def sesi2():
    run_async(check_reactions(CHAT_ID, TOPIC_ID_2, 17, 18, "🕔 Sesi 2 (17.00–18.00 WIB)"))
    return "✅ Sesi 2 dijalankan.", 200

@app.route("/sesi3")
def sesi3():
    run_async(check_reactions(CHAT_ID, TOPIC_ID_3, 20, 21, "🌙 Sesi 3 (20.00–21.00 WIB)"))
    return "✅ Sesi 3 dijalankan.", 200

# ==========================
# 🚀 RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
