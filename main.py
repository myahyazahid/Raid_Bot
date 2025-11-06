from flask import Flask
from telethon import TelegramClient
from telebot import TeleBot
from datetime import datetime, timedelta, timezone
import asyncio
import re
import os

app = Flask(__name__)

# --- Environment Variables ---
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])  # contoh: -1002632100535

TOPIC_ID_1 = int(os.environ.get("TOPIC_ID_1", 0))
TOPIC_ID_2 = int(os.environ.get("TOPIC_ID_2", 0))
TOPIC_ID_3 = int(os.environ.get("TOPIC_ID_3", 0))

# --- Setup Clients ---
telethon_client = TelegramClient('session', API_ID, API_HASH)
bot = TeleBot(BOT_TOKEN, parse_mode="Markdown")

# --- Fungsi utama: cek siapa yang belum kasih reaction ---
async def check_reactions(chat_id, topic_id, start_hour, end_hour, test_mode=False):
    now = datetime.now(timezone.utc) + timedelta(hours=7)  # WIB

    # mode test = 10 menit terakhir
    if test_mode:
        start_time = now - timedelta(minutes=10)
        end_time = now
        label = "🧪 *Test Mode (10 menit terakhir)*"
    else:
        start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        label = f"📊 *Laporan {start_hour}:00–{end_hour}:00 WIB*"

    await telethon_client.start()

    link_messages = []
    async for msg in telethon_client.iter_messages(chat_id, offset_date=end_time):
        if msg.date < start_time:
            break
        if getattr(msg, "top_msg_id", None) != topic_id:
            continue
        if msg.text and re.search(r'https?://', msg.text):
            link_messages.append(msg)

    all_reactors = set()
    for msg in link_messages:
        if msg.reactions:
            async for u in telethon_client.get_reaction_users(chat_id, msg.id):
                if u.username:
                    all_reactors.add(u.username)

    senders = {m.sender.username for m in link_messages if m.sender and m.sender.username}
    not_reacted = senders - all_reactors

    # --- Format laporan ---
    text = f"{label}\n📎 Total link: {len(link_messages)}\n\n"
    if not_reacted:
        text += "🚫 Belum react:\n" + "\n".join(f"@{u}" for u in not_reacted)
    else:
        text += "✅ Semua sudah react."

    # --- Kirim hasil ke thread ---
    bot.send_message(chat_id, text, reply_to_message_id=topic_id)

# --- ROUTES Flask ---
@app.route("/")
def home():
    return "✅ Hybrid Bot aktif (Telethon + BOT_TOKEN)", 200

@app.route("/sesi1")
def sesi1():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15))
    return "Sesi 1 done", 200

@app.route("/sesi2")
def sesi2():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_2, 17, 18))
    return "Sesi 2 done", 200

@app.route("/sesi3")
def sesi3():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_3, 20, 21))
    return "Sesi 3 done", 200

# --- Mode Testing Manual ---
@app.route("/sesi1_test")
def sesi1_test():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, test_mode=True))
    return "Tes sesi 1 selesai!", 200

@app.route("/sesi2_test")
def sesi2_test():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_2, 17, 18, test_mode=True))
    return "Tes sesi 2 selesai!", 200

@app.route("/sesi3_test")
def sesi3_test():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_3, 20, 21, test_mode=True))
    return "Tes sesi 3 selesai!", 200

# --- Jalankan Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
