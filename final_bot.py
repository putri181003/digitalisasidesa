import os
import logging
import aiohttp
import base64
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# === KONFIGURASI ===
load_dotenv()
API_URL = "https://script.google.com/macros/s/AKfycbxnk0g6CB9cwql6AnFEr7rKIOBCNfW032xWI5rHX6jFnq8SgTctwR0Uu_AB3E48rQ6D/exec"  # Ganti
BOT_TOKEN = "8295545188:AAGwBAa8eW3zyCvzua53wysDjgP98iMHcso"  # Ganti

# === LOGGING ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === NORMALIZER KEY ===
def normalize_key(key: str) -> str:
    return key.lower().replace(" ", "").replace("/", "").replace("_", "")

# === PARSER ===
def parse_fields(text: str) -> dict:
    field_map = {
        "laporan": "laporan",
        "namasaar": "nama_sa_ar",
        "bulan": "bulan",
        "tahun": "tahun",
        "namapelanggan": "nama_pelanggan",
        "namadesa": "nama_desa",
        "namakecamatan": "nama_kecamatan",
        "keterangan": "keterangan",
        "trackid": "track_id"
    }

    data = {}
    for line in text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            norm_key = normalize_key(key.strip())
            val = val.strip()
            if norm_key in field_map:
                data[field_map[norm_key]] = val
    
    

    # Tambahkan default bulan & tahun jika kosong
    
    now = datetime.now()
    if "bulan" not in data:
        data["bulan"] = now.strftime("%B")
    if "tahun" not in data:
        data["tahun"] = now.strftime("%Y")

    return data

# === HANDLER COMMAND /activity ===
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    text = (
        "/activity\n"
        "Laporan: Visit/PS \n"
        "Nama SA/AR: \n"
        f"Bulan: {datetime.now().strftime('%B')}\n"
        f"Tahun: {datetime.now().strftime('%Y')}\n"
        "Nama Pelanggan: \n"
        "Nama Desa: \n"
        "Nama Kecamatan: \n"
        "Keterangan: \n"
        "Track ID: \n"
    )
    await update.message.reply_text(text)
    logger.info("[ACTIVITY] User %s meminta template activity.", user)

# === HANDLER TEKS ===
async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nama = update.message.from_user.first_name
    pesan = update.message.text.strip()
    logger.info("[MESSAGE] Dari %s: %s", nama, pesan)

    try:
        data = parse_fields(pesan)
        if not data:
            await update.message.reply_text("⚠️ Format tidak dikenali. Gunakan /activity untuk melihat format input.")
            return

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=data) as r:
                resp_text = await r.text()
                logger.info("[API RESPON PESAN] Status: %s, Body: %s", r.status, resp_text)

                if r.status == 200:
                    await update.message.reply_text("✅ Laporan berhasil disimpan ke Google Sheets!")
                else:
                    await update.message.reply_text(f"❌ Gagal simpan. Code: {r.status}")

    except Exception as e:
        logger.error("[ERROR PESAN] %s", e)
        await update.message.reply_text(f"❌ Error: {e}")

# === HANDLER FOTO ===
async def save_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nama = update.message.from_user.first_name
    caption = update.message.caption or ""
    photo = update.message.photo[-1]

    logger.info("[PHOTO] Dari %s, caption: %s", nama, caption)

    try:
        # Download foto
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        # Encode base64 → kirim ke GAS
        base64_img = base64.b64encode(photo_bytes).decode("utf-8")

        data = parse_fields(caption)
        now = datetime.now()
        if "bulan" not in data:
            data["bulan"] = now.strftime("%B")
        if "tahun" not in data:
            data["tahun"] = now.strftime("%Y")
        data["foto"] = base64_img

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=data) as r:
                resp_text = await r.text()
                logger.info("[API RESPON FOTO] Status: %s, Body: %s", r.status, resp_text)

                if r.status == 200:
                    await update.message.reply_text("✅ Foto berhasil diupload & link tersimpan di Google Sheets!")
                else:
                    await update.message.reply_text(f"❌ Gagal simpan foto. Code: {r.status}")

    except Exception as e:
        logger.error("[ERROR FOTO] %s", e)
        await update.message.reply_text(f"❌ Error upload foto: {e}")

# === MAIN ===
def main():
    logger.info("🚀 Bot sedang berjalan...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("activity", laporan))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_message))
    app.add_handler(MessageHandler(filters.PHOTO, save_photo))

    app.run_polling(allowed_updates=[])

if __name__ == "__main__":
    main()
