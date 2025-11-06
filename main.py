import os
import base64
import asyncio
import re
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telebot import TeleBot
from flask import Flask

# ========================
# 🔧 KONFIGURASI
# ========================
API_ID     = int(os.getenv("API_ID"))
API_HASH   = os.getenv("API_HASH")
BOT_TOKEN  = os.getenv("BOT_TOKEN")
CHAT_ID    = int(os.getenv("CHAT_ID"))

TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1"))  # Sesi 1
TOPIC_ID_2 = int(os.getenv("TOPIC_ID_2"))  # Sesi 2
TOPIC_ID_3 = int(os.getenv("TOPIC_ID_3"))  # Sesi 3

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ========================
# 🔐 RESTORE SESSION USER
# ========================
if os.getenv("SESSION_DATA"):
    with open("session.session", "wb") as f:
        f.write(base64.b64decode(os.getenv("SESSION_DATA")))

telethon_client = TelegramClient("session", API_ID, API_HASH)

# ========================
# 🧠 CEK REAKSI (window WIB)
# ========================
async def check_reactions(chat_id: int, topic_id: int, start_hour_wib: int, end_hour_wib: int, sesi_nama: str):
    try:
        await telethon_client.connect()
        if not await telethon_client.is_user_authorized():
            print("❌ Telethon belum login user.")
            return

        # Waktu sekarang UTC
        now_utc = datetime.now(timezone.utc)

        # Bangun window WIB untuk "hari ini" lalu konversi ke UTC
        # WIB = UTC+7  => UTC = WIB - 7
        today_wib = (now_utc + timedelta(hours=7)).date()
        start_wib = datetime(today_wib.year, today_wib.month, today_wib.day, start_hour_wib, 0, 0, tzinfo=timezone(timedelta(hours=7)))
        end_wib   = datetime(today_wib.year, today_wib.month, today_wib.day, end_hour_wib,   0, 0, tzinfo=timezone(timedelta(hours=7)))

        start_utc = (start_wib - timedelta(hours=7)).astimezone(timezone.utc)
        end_utc   = (end_wib   - timedelta(hours=7)).astimezone(timezone.utc)

        print(f"🔎 {sesi_nama} | Window WIB: {start_wib.time()}–{end_wib.time()} | UTC: {start_utc.time()}–{end_utc.time()} | topic={topic_id}")

        # Kumpulkan pesan berisi link dalam window & topic yang sama
        link_messages = []
        async for msg in telethon_client.iter_messages(chat_id, offset_date=end_utc, reverse=True):
            # msg.date adalah timezone-aware UTC
            if msg.date < start_utc:
                break
            if getattr(msg, "top_msg_id", None) != topic_id:
                continue
            if msg.text and re.search(r"https?://", msg.text):
                link_messages.append(msg)

        # Ambil semua user yang kasih reaction di pesan-pesan link
        all_reactors = set()
        for m in link_messages:
            if m.reactions:
                async for u in telethon_client.get_reaction_users(chat_id, m.id):
                    if u.username:
                        all_reactors.add(u.username)

        # Siapa saja pengirim link
        senders = {m.sender.username for m in link_messages if m.sender and m.sender.username}
        not_reacted = senders - all_reactors

        total_links = len(link_messages)
        belum_text = "\n".join(f"- @{u}" for u in sorted(not_reacted)) if not_reacted else "✅ Semua sudah melakukan raid."

        hasil = (
            f"📊 Pengecekan Raid {sesi_nama}\n"
            f"Total links : {total_links}\n"
            f"Belum raid :\n{belum_text}"
        )

        # Kirim via bot admin ke thread
        bot.send_message(chat_id, hasil, message_thread_id=topic_id)
        print(f"✅ Laporan terkirim ({sesi_nama}) ke topic {topic_id}")

    except Exception as e:
        print(f"❌ Error check_reactions ({sesi_nama}): {e}")
        try:
            bot.send_message(chat_id, f"❌ Error {sesi_nama}: {e}", message_thread_id=topic_id)
        except Exception:
            pass

# ========================
# 🌐 ROUTES
# ========================
@app.route("/")
def home():
    return "🚀 Redscale Raid Bot aktif (WIB window, kirim via bot admin)", 200

@app.route("/status")
def status():
    # Tampilkan waktu WIB biar gampang cek
    wib_now = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S WIB")
    return f"🟢 Bot up. Sekarang: {wib_now}", 200

@app.route("/test")
def test():
    # Test pakai TOPIC_ID_1 dan window "satu jam terakhir" agar bisa dicoba kapan saja
    wib_now = datetime.now(timezone.utc) + timedelta(hours=7)
    start_h = (wib_now - timedelta(hours=1)).hour
    end_h   = wib_now.hour
    asyncio.run(check_reactions(CHAT_ID, TOPIC_ID_1, start_h, end_h, "🧪 Test Mode (1 jam terakhir)"))
    return "✅ Test dijalankan!", 200

# Sesi-sesi fix sesuai permintaanmu
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

# ========================
# 🚦 START
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
