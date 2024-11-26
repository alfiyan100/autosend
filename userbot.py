import logging
from telethon import TelegramClient, events
from telethon.errors import rpcerrorlist
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, Channel
from database import save_media, get_all_media, save_temp_media, get_all_temp_media, clear_temp_media, get_temp_media_by_id
import time
import re
import os
import asyncio
from datetime import datetime
import pytz  # Library untuk konversi waktu
from telethon.sessions import StringSession  # Tambahkan impor untuk StringSession

# Ganti dengan API ID dan hash dari aplikasi Telegram kamu
api_id = '29534642'
api_hash = '0163712ff5842fa356424ad75a53442b'
string_session = '1BVtsOH0Bu2hB73LTrUYcRyrrw7UgpAA8J8ajXNbt92Bc5rJP1csb1E20URERMkvkDKQhPmIhX0UtN0Z9OZN7C8wa0FSgwGCaYHDjx0Gj0k-0PDay-hxlp6fnFKDO1tVmrisiaffUcfh4dByEuifrbotnG5CUX0Q1m0Yfacid22xDVi_YB2EXqGJqdNZKWmI3xxzpOUSqNGoynxClnYjjjOiFjk03ItytIadrMSuqqpdrue3O0kQUvo2Hl99lzsowciFlvkwOrVhOvN4NIeFYE7BFR_MWDekTwwSB3OVCw_15qtbJ677A_00pyMndG7ebCkxahB-crMN3peFXh2Bz4LndG454O10='  # Masukkan string session Anda di sini

# ID chat target default untuk meneruskan media
default_target_chat_id = '@filebotkep'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname=s - %(message=s')
logger = logging.getLogger(__name__)

# Inisialisasi client Telethon dengan string session
client = TelegramClient(StringSession(string_session), api_id, api_hash)

# Penanda untuk menghentikan proses
stop_process = False

# Fungsi untuk memulai klien
async def start_client():
    try:
        await client.start()
        user = await client.get_me()
        logger.info(f"Userbot started successfully as {user.first_name} ({user.id}).")
    except Exception as e:
        logger.error(f"Error starting userbot: {e}")
        exit(1)

# Fungsi untuk menghentikan proses
@client.on(events.NewMessage(pattern=r'/stop'))
async def stop_handler(event):
    global stop_process
    stop_process = True
    await event.respond("Proses sedang dihentikan...")

# Event handler untuk menerima media dan perintah
@client.on(events.NewMessage)
async def handler(event):
    global stop_process

    # Cek perintah /ping
    if event.raw_text == '/ping':
        start_time = time.time()
        await event.reply('Pong!')
        end_time = time.time()
        ping_time = (end_time - start_time) * 1000
        await event.reply(f'Ping: {ping_time:.2f} ms')
        logger.info(f'Ping command executed: {ping_time:.2f} ms')

    # Cek perintah /cek
    if event.raw_text == '/cek':
        user_id = event.sender_id
        sender = await event.get_sender()
        username = f"@{sender.username}" if sender.username else 'Tidak ada'
        await event.respond(f"ID Pengirim: {user_id}\nUsername: {username}")
        logger.info(f'User checked: {user_id} - {username}')

    # Tangani media yang masuk
    if isinstance(event.media, MessageMediaPhoto) or isinstance(event.media, MessageMediaDocument):
        try:
            file_type = 'photo' if isinstance(event.media, MessageMediaPhoto) else 'video'
            file_id = event.media.photo.id if file_type == 'photo' else event.media.document.id

            # Cek apakah file sudah ada di database
            existing_media = get_all_media()
            if any(media['file_id'] == file_id for media in existing_media):
                return

            file_date = event.date.strftime('%Y-%m-%d %H:%M:%S')
            file_path = await event.download_media(file=f'media/{file_id}')

            # Simpan media ke MongoDB
            save_media(file_id, file_type, file_date, file_path)

            # Dapatkan informasi pengirim
            sender = await event.get_sender()
            username = f"@{sender.username}" if sender.username else 'Tidak ada'
            user_id = sender.id

            # Format waktu dan tanggal
            tz = pytz.timezone('Asia/Jakarta')
            time_sent = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

            # Kirim media ke target chat default dengan format baru
            caption = f"Oleh: {username} (ID: {user_id})\nDikirim pada: {time_sent} (GMT+7)"
            await client.send_file(default_target_chat_id, file_path, caption=caption)
            logger.info(f"{file_type.capitalize()} received and sent to {default_target_chat_id} with caption.")

        except Exception as e:
            logger.error(f"Error processing media: {e}")

# Perintah /salin untuk menyalin foto dan video ke dalam database sementara
@client.on(events.NewMessage(pattern=r'/salin'))
async def copy_files(event):
    global stop_process
    stop_process = False

    user_input = event.raw_text.split(maxsplit=1)[1]
    try:
        if user_input.startswith('@'):
            link = user_input
        elif re.match(r'https://t\.me/c/\d+/\d+', user_input):
            link = user_input
        else:
            link = int(user_input.strip())

        entity = await client.get_entity(link)
        if isinstance(entity, Channel):
            total_files = 0
            copied_files = 0

            async for message in client.iter_messages(entity):
                if isinstance(message.media, MessageMediaPhoto) or isinstance(message.media, MessageMediaDocument):
                    total_files += 1

            async for message in client.iter_messages(entity):
                if stop_process:
                    await event.respond("Proses penyalinan dihentikan.")
                    break

                if isinstance(message.media, MessageMediaPhoto) or isinstance(message.media, MessageMediaDocument):
                    file_type = 'photo' if isinstance(message.media, MessageMediaPhoto) else 'video'
                    file_date = message.date.strftime('%Y-%m-%d %H:%M:%S')
                    file_id = message.media.photo.id if file_type == 'photo' else message.media.document.id

                    # Cek apakah file sudah ada di database sementara atau database utama
                    if get_temp_media_by_id(file_id) or any(media['file_id'] == file_id for media in get_all_media()):
                        continue

                    file_path = await message.download_media(file=f'temp_media/{file_id}')

                    # Simpan kode file ke database sementara
                    save_temp_media(file_id, file_type, file_date, file_path)
                    copied_files += 1
                    progress = (copied_files / total_files) * 100
                    await event.respond(f'Progres penyalinan: {progress:.2f}%')

            if not stop_process:
                await event.respond(f'Semua foto dan video dari {entity.title} telah disalin ke dalam database sementara.')
        else:
            await event.respond(f"Entitas bukan channel.")
    except Exception as e:
        await event.respond(f"Gagal menyalin file. Error: {e}\nUsage: /salin <@username atau channel_id atau link postingan>")

# Perintah /tampilkan untuk menampilkan semua data file yang disalin dari database sementara
@client.on(events.NewMessage(pattern=r'/tampilkan'))
async def paste_files(event):
    global stop_process
    stop_process = False

    try:
        media_files = get_all_temp_media()
        if not media_files:
            await event.respond("Tidak ada file yang disalin dalam database sementara.")
            return

        total_files = len(media_files)
        displayed_files = 0

        for media in media_files:
            if stop_process:
                await event.respond("Proses penampilan dihentikan.")
                break

            file_path = media['file_path']
            if not os.path.exists(file_path):
                await event.respond(f"Gagal menampilkan file: {file_path} tidak ditemukan.")
                continue

            await client.send_file(event.chat_id, file_path, caption=f"{media['file_type'].capitalize()} received on {media['file_date']}")
            displayed_files += 1
            progress = (displayed_files / total_files) * 100
            await event.respond(f'Progres penampilan: {progress:.2f}%')

        if not stop_process:
            await event.respond("Semua file dari database sementara telah ditampilkan.")
            clear_temp_media()  # Hapus database sementara setelah file ditampilkan
            await event.respond("Database sementara telah dihapus.")
    except Exception as e:
        await event.respond(f"Gagal menampilkan file. Error: {e}")

# Jalankan bot
async def run_client():
    try:
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Error running userbot: {e}")

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_client())
    loop.run_until_complete(run_client())
