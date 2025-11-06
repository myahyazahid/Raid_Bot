from flask import Flask
from telethon import TelegramClient
from datetime import datetime
import asyncio, re, os

app = Flask(__name__)

api_id = int(os.environ["API_ID"])
api_hash = os.environ["API_HASH"]

CHAT_ID = int(os.environ["CHAT_ID_1"])  # Channel ID utama

# Thread (topic) untuk masing-masing sesi
TOPIC_ID_1 = int(os.environ.get("TOPIC_ID_1", 0))
TOPIC_ID_2 = int(os.environ.get("TOPIC_ID_2", 0))
TOPIC_ID_3 = int(os.environ.get("TOPIC_ID_3", 0))

client = TelegramClient('session', api_id, api_hash)

async def check_reactions(chat_id, topic_id, start_hour, end_hour):
    now = datetime.now()
    start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end_time   = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    link_messages = []
    async for msg in client.iter_messages(chat_id, offset_date=end_time):
        if msg.date < start_time:
            break
        if getattr(msg, "top_msg_id", None) != topic_id:
            continue
        if msg.text and re.search(r'https?://', msg.text):
            link_messages.append(msg)

    all_reactors = set()
    for msg in link_messages:
        if msg.reactions:
            async for u in client.get_reaction_users(chat_id, msg.id):
                if u.username:
                    all_reactors.add(u.username)

    senders = {m.sender.username for m in link_messages if m.sender and m.sender.username}
    not_reacted = senders - all_reactors

    text = f"📊 Laporan {start_hour}:00–{end_hour}:00\n📎 Total link: {len(link_messages)}\n\n"
    text += "🚫 Belum react:\n" + "\n".join(f"@{u}" for u in not_reacted) if not_reacted else "✅ Semua sudah react."

    await client.send_message(chat_id, text, reply_to=topic_id)

@app.route("/")
def home():
    return "Bot aktif!", 200

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

if __name__ == "__main__":
    client.start()
    app.run(host="0.0.0.0", port=5000)
