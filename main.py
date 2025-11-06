import os
import asyncio
from flask import Flask
from telethon import TelegramClient
from telebot import TeleBot

# === ENVIRONMENT VARIABLES ===
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))
TOPIC_ID_2 = int(os.getenv("TOPIC_ID_2"))
TOPIC_ID_3 = int(os.getenv("TOPIC_ID_3"))

# === INIT TELETHON + TELEBOT ===
telethon_client = TelegramClient("session", API_ID, API_HASH)
bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Jalankan Telethon 1x saat startup
loop = asyncio.get_event_loop()
loop.create_task(telethon_client.start())

# === LOGIC ===
async def check_reactions(chat_id, topic_id, start_hour, end_hour, test_mode=False):
    try:
        print(f"✅ Checking reactions for topic {topic_id} between {start_hour}-{end_hour}")
        if not test_mode:
            message = f"✅ Sesi {start_hour}-{end_hour} selesai, laporan terkirim!"
        else:
            message = f"🧪 Test mode aktif! Koneksi berhasil ke topic {topic_id}."

        bot.send_message(chat_id, message, message_thread_id=topic_id)
        print(f"📨 Message sent to {chat_id} (topic {topic_id})")
    except Exception as e:
        print(f"❌ Error in check_reactions: {e}")

# === ROUTES ===
@app.route("/")
def home():
    return "✅ Bot aktif dan siap digunakan!", 200

@app.route("/test")
def test():
    loop.create_task(check_reactions(CHAT_ID, TOPIC_ID_1, 0, 0, test_mode=True))
    return "🧪 Test route dijalankan!", 200

@app.route("/sesi1")
def sesi1():
    loop.create_task(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15))
    return "Sesi 1 dijalankan!", 200

@app.route("/sesi2")
def sesi2():
    loop.create_task(check_reactions(CHAT_ID, TOPIC_ID_2, 17, 18))
    return "Sesi 2 dijalankan!", 200

@app.route("/sesi3")
def sesi3():
    loop.create_task(check_reactions(CHAT_ID, TOPIC_ID_3, 20, 21))
    return "Sesi 3 dijalankan!", 200

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000)
