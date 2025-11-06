from flask import Flask
from telethon import TelegramClient
from telebot import TeleBot
from datetime import datetime, timedelta
import asyncio, os, re

app = Flask(__name__)

# ==========================
# 🔧 KONFIGURASI
# ==========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = int(os.getenv("CHAT_ID"))
TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))
TOPIC_ID_2 = int(os.getenv("TOPIC_ID_2"))
TOPIC_ID_3 = int(os.getenv("TOPIC_ID_3"))

bot = TeleBot(BOT_TOKEN)
telethon_client = TelegramClient("session", API_ID, API_HASH)

# ==========================
# 🚀 START TELETHON
# ==========================
async def start_telethon():
    await telethon_client.start(bot_token=BOT_TOKEN)
    print("✅ Telethon connected as bot")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.create_task(start_telethon())

# ==========================
# 🧩 FUNGSI CEK REAKSI
# ==========================
async def check_reactions(chat_id, topic_id, start_hour, end_hour, sesi_nama):
    try:
        if not telethon_client.is_connected():
            await telethon_client.connect()

        now_utc = datetime.utcnow()
        now = now_utc + timedelta(hours=7)  # WIB

        start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

        print(f"🔍 Mengecek {sesi_nama} | {start_hour}:00–{end_hour}:00 WIB")

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

        await asyncio.to_thread(bot.send_message, chat_id, hasil, message_thread_id=topic_id)
        print(f"✅ Laporan {sesi_nama} dikirim")

    except Exception as e:
        print(f"❌ Error di check_reactions: {e}")
        await asyncio.to_thread(bot.send_message, chat_id, f"❌ Error: {e}")

# ==========================
# 🧩 CEK STATUS / IZIN BOT
# ==========================
@app.route("/status")
def status():
    try:
        if not telethon_client.is_connected():
            return "❌ Telethon belum connect.", 200
        me = loop.run_until_complete(telethon_client.get_me())
        bot_info = f"🤖 Bot: @{me.username} (ID: {me.id})"

        # Coba kirim pesan test singkat (tidak di thread)
        try:
            bot.send_message(CHAT_ID, "✅ Bot aktif & bisa kirim pesan (tes /status)")
            status_msg = "✅ Bot berhasil kirim pesan ke grup."
        except Exception as err:
            status_msg = f"⚠️ Gagal kirim pesan: {err}"

        return f"{bot_info}\n{status_msg}", 200
    except Exception as e:
        return f"❌ Error status: {e}", 200

# ==========================
# 🌐 ROUTES RAID
# ==========================
@app.route("/")
def home():
    return "🚀 Raid Bot aktif (Zona waktu: WIB)", 200

@app.route("/test")
def test():
    now_utc = datetime.utcnow()
    now = now_utc + timedelta(hours=7)
    start_hour = now.hour
    end_hour = start_hour + 1
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, start_hour, end_hour, "🧪 Test Mode"))
    return f"✅ Test dijalankan untuk {start_hour}:00–{end_hour}:00 WIB", 200

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
# 🚀 START FLASK SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
