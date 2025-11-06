from flask import Flask
from telethon import TelegramClient
from telebot import TeleBot
from datetime import datetime, timedelta
import asyncio, os, re

app = Flask(__name__)

# ==========================
# 🔧 KONFIGURASI ENVIRONMENT
# ==========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = int(os.getenv("CHAT_ID"))  # ID supergroup
TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))  # Thread sesi 1
TOPIC_ID_2 = int(os.getenv("TOPIC_ID_2"))  # Thread sesi 2
TOPIC_ID_3 = int(os.getenv("TOPIC_ID_3"))  # Thread sesi 3

bot = TeleBot(BOT_TOKEN)
telethon_client = TelegramClient("session", API_ID, API_HASH)

# ==========================
# 🧠 FUNGSI CEK REAKSI
# ==========================
async def check_reactions(chat_id, topic_id, start_hour, end_hour, sesi_nama):
    try:
        await telethon_client.connect()
        if not await telethon_client.is_user_authorized():
            print("❌ Telethon belum login.")
            return

        # Konversi ke waktu WIB
        now_utc = datetime.utcnow()
        now = now_utc + timedelta(hours=7)  # WIB = UTC + 7

        start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

        print(f"🕒 Mengecek {sesi_nama} | {start_time.time()} - {end_time.time()} WIB")

        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, offset_date=end_time):
            if msg.date < start_time:
                break
            if getattr(msg, "top_msg_id", None) != topic_id:
                continue
            if msg.text and re.search(r"https?://", msg.text):
                link_messages.append(msg)

        # Ambil user yang kasih reaction
        all_reactors = set()
        for msg in link_messages:
            if msg.reactions:
                async for u in telethon_client.get_reaction_users(chat_id, msg.id):
                    if u.username:
                        all_reactors.add(u.username)

        # Ambil pengirim link
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

        await asyncio.to_thread(bot.send_message, chat_id, hasil, message_thread_id=topic_id)
        print(f"✅ Laporan {sesi_nama} dikirim ke topic {topic_id}")

    except Exception as e:
        print(f"❌ Error di check_reactions: {e}")


# ==========================
# 🌐 ROUTES
# ==========================
@app.route("/")
def home():
    return "🚀 Raid Bot aktif (Zona waktu WIB)!", 200


@app.route("/test")
def test():
    """Tes manual sesuai jam saat ini"""
    now_utc = datetime.utcnow()
    now = now_utc + timedelta(hours=7)  # WIB
    start_hour = now.hour
    end_hour = start_hour + 1

    print(f"🧪 Test dijalankan untuk {start_hour}:00–{end_hour}:00 WIB")
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, start_hour, end_hour, "🧪 Test Mode"))
    return f"🧪 Test dijalankan untuk {start_hour}:00–{end_hour}:00 WIB", 200


@app.route("/sesi1")
def sesi1():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, "🕐 Sesi 1 (14.00–15.00 WIB)"))
    return "✅ Sesi 1 dijalankan!", 200


@app.route("/sesi2")
def sesi2():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_2, 17, 18, "🕔 Sesi 2 (17.00–18.00 WIB)"))
    return "✅ Sesi 2 dijalankan!", 200


@app.route("/sesi3")
def sesi3():
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_3, 20, 21, "🌙 Sesi 3 (20.00–21.00 WIB)"))
    return "✅ Sesi 3 dijalankan!", 200


# ==========================
# 🚀 START SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
