import os
import base64
import asyncio
from datetime import datetime, timezone
from telethon import TelegramClient, events
from flask import Flask

# ========================
# 🔧 KONFIGURASI DASAR
# ========================
API_ID = int(os.getenv("API_ID", "39993754"))
API_HASH = os.getenv("API_HASH", "0eea9b16eb5dd10d958f815f58a0e2e5")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "-100XXXXXXXXXX"))  # Ganti dengan ID grup kamu
TOPIC_ID_1 = int(os.getenv("TOPIC_ID_1", "0"))  # Thread ID untuk sesi 1

# ========================
# 🔐 RESTORE SESSION
# ========================
if os.getenv("SESSION_DATA"):
    print("🔑 Dekode session Telethon dari ENV...")
    with open("session.session", "wb") as f:
        f.write(base64.b64decode(os.getenv("SESSION_DATA")))
else:
    print("⚠️ Tidak ada SESSION_DATA di environment!")

# ========================
# 🚀 SETUP FLASK & TELETHON
# ========================
app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
client = TelegramClient("session", API_ID, API_HASH)

# ========================
# 🔁 FUNGSIONALITAS TELETHON
# ========================
async def start_telethon():
    print("🚀 Menghubungkan ke Telegram...")
    await client.start()
    me = await client.get_me()
    print(f"✅ Login sebagai {me.first_name} (@{getattr(me, 'username', '-')})")

    # Handler contoh
    @client.on(events.NewMessage(pattern="/ping"))
    async def ping_handler(event):
        await event.reply("🏓 Pong dari Redscale Raid Bot!")

    print("🟢 Telethon aktif dan siap digunakan.")
    await client.run_until_disconnected()

# ========================
# ⚙️ FUNGSI CEK SEGERA
# ========================
async def check_reactions(chat_id, topic_id, jam_mulai, jam_selesai, nama_sesi):
    now_utc = datetime.now(timezone.utc)
    pesan = (
        f"📢 Pengecekan Raid\n"
        f"🕐 {nama_sesi}\n"
        f"⏰ Waktu server UTC: {now_utc.strftime('%H:%M:%S')}\n"
        f"Total links : 0\n"
        f"Belum raid : - (belum ada data)"
    )
    await client.send_message(chat_id, pesan, reply_to=topic_id)
    print("📨 Pesan pengecekan terkirim ke thread.")

# ========================
# 🧠 BACKGROUND RUNNER
# ========================
async def background_runner():
    await start_telethon()

def ensure_telethon_running():
    if not client.is_connected():
        loop.create_task(background_runner())

# ========================
# 🌐 ROUTES FLASK
# ========================
@app.route("/")
def home():
    return "🚀 Redscale Raid Bot is live on Render!"

@app.route("/status")
def status():
    ensure_telethon_running()
    return "🟢 Bot status: Telethon connected and Flask running."

@app.route("/test")
def test():
    ensure_telethon_running()
    loop.create_task(client.send_message(CHAT_ID, "✅ Test: Bot Redscale aktif!"))
    return "✅ Pesan test dikirim ke grup."

@app.route("/sesi1")
def sesi1():
    ensure_telethon_running()
    loop.create_task(check_reactions(CHAT_ID, TOPIC_ID_1, 14, 15, "Sesi 1 (14.00–15.00 WIB)"))
    return "📊 Pemeriksaan sesi 1 dijalankan."

# ========================
# 🚦 MAIN ENTRY
# ========================
if __name__ == "__main__":
    print("🔥 Menjalankan Flask server...")
    loop.create_task(background_runner())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
