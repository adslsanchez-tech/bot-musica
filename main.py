import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from shazamio import Shazam
from syncedlyrics import search as get_synced_lyrics
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, error

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    
    if msg.audio or msg.voice or (msg.document and msg.document.mime_type and 'audio' in msg.document.mime_type):
        await msg.reply_text("🎧 Analizando el audio...")
        audio_file = msg.audio or msg.voice or msg.document
        file = await context.bot.get_file(audio_file.file_id)
        temp_in = "temp_input.mp3"
        await file.download_to_drive(temp_in)

        shazam = Shazam()
        out = await shazam.recognize(temp_in)
        if os.path.exists(temp_in):
            os.remove(temp_in)

        if not out.get('track'):
            await msg.reply_text("❌ No se reconoció la canción. Envía el nombre por texto.")
            return

        song_title = out['track']['title']
        artist_name = out['track']['subtitle']
        search_query = f"{artist_name} - {song_title}"
    elif msg.text:
        search_query = msg.text
    else:
        await msg.reply_text("Envía un audio, una nota de voz o el nombre de una canción.")
        return

    await msg.reply_text(f"🎵 Canción: {search_query}\nProcesando descarga y letras...")

    out_filename = "cancion_final.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'song_temp',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }, {
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }],
        'writethumb': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch1:{search_query}"])

        if os.path.exists("song_temp.mp3"):
            os.rename("song_temp.mp3", out_filename)

        lrc_text = get_synced_lyrics(search_query)
        if lrc_text and os.path.exists(out_filename):
            try:
                audio = MP3(out_filename, ID3=ID3)
                try:
                    audio.add_tags()
                except error:
                    pass
                audio.tags.add(USLT(encoding=3, lang='eng', desc='Lyrics', text=lrc_text))
                audio.save()
            except Exception as e:
                logging.error(f"Error guardando letra: {e}")

        with open(out_filename, 'rb') as audio_out:
            await msg.reply_audio(audio=audio_out, title=search_query)

    except Exception as e:
        await msg.reply_text(f"Error procesando: {e}")
    finally:
        if os.path.exists(out_filename):
            os.remove(out_filename)

if __name__ == '__main__':
    TOKEN = "8729383352:AAEP52uBVA9PvM9-WgEpD0C_nmCfWdjox7E"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, process_audio))
    print("Bot activo...")
    app.run_polling()
