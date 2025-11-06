import os
import base64
import asyncio
import re
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telebot import TeleBot
from flask import Flask

# ========================
# 🔧 KONFIGURASI
# ========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))

# Inisialisasi bot
bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Dekode session Telethon
if os.getenv("SESSION_DATA"):
    with open("session.session", "wb") as f:
        f.write(base64.b64decode(os.getenv("SESSION_DATA")))

telethon_client = TelegramClient("session", API_ID, API_HASH)

# ========================
# 🧠 CEK REAKSI
# ========================
async def check_reactions(chat_id, topic_id, start_hour, end_hour, sesi_nama):
    try:
        await telethon_client.connect()
        if not await telethon_client.is_user_authorized():
            print("❌ Telethon belum login.")
            return

        # Konversi waktu UTC → WIB
        now_utc = datetime.now(timezone.utc)
        now_wib = now_utc + timedelta(hours=7)

        start_time = now_wib.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = now_wib.replace(hour=end_hour, minute=0, second=0, microsecond=0)

        print(f"🕒 Mengecek {sesi_nama}: {start_time.time()}–{end_time.time()} WIB")

        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, offset_date=end_time):
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

        total_links = len(link_messages)
        if not_reacted:
            belum_text = "\n".join(f"- @{u}" for u in not_reacted)
        else:
            belum_text = "✅ Semua sudah melakukan raid."

        hasil = (
            f"📊 Pengecekan Raid {sesi_nama}\n"
            f"Total links : {total_links}\n"
            f"Belum raid :\n{belum_text}"
        )

        # ✅ kirim pakai bot (bukan Telethon)
        bot.send_message(chat_id, hasil, message_thread_id=topic_id)
        print("✅ Laporan dikirim via bot.")

    except Exception as e:
        print(f"❌ Error check_reactions: {e}")


# ========================
# 🌐 ROUTES
# ========================
@app.route("/")
def home():
    return "🚀 Redscale Raid Bot aktif!", 200

@app.route("/test")
def test():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, "🧪 Test Mode"))
    return "✅ Test dijalankan!", 200

@app.route("/sesi1")
def sesi1():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, "🕐 Sesi 1 (14.00–15.00 WIB)"))
    return "✅ Sesi 1 dijalankan!", 200


# ========================
# 🚦 START
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
