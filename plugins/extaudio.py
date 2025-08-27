# ---------------------------------------------------------
# Copyright (c) 2021-2025
# Developers: TheAlphaBotz
# Telegram: @TheAlphaBotz
# License: All Rights Reserved
# ---------------------------------------------------------

import os
import re
import subprocess
import json
import asyncio
from bot import app
from typing import List, Dict
from pyrogram import Client, filters
from pyrogram.types import Message
from config import DOWNLOAD_DIR
from progressbar import progress_bar, humanbytes, time_formatter

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ----------------- Utility Functions -----------------

def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name

def ffprobe_streams(file_path: str) -> Dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index,codec_name:stream_tags=language,title",
        "-of", "json", file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "ffprobe failed")
    return json.loads(res.stdout or "{}")

def get_audio_tracks(file_path: str) -> List[Dict]:
    data = ffprobe_streams(file_path)
    tracks = []
    for i, stream in enumerate(data.get("streams", [])):
        codec = stream.get("codec_name") or "audio"
        tags = stream.get("tags", {}) or {}
        tracks.append({
            "map_index": i,
            "codec": codec,
            "language": normalize_language(tags.get("language")),
            "title": tags.get("title") or ""
        })
    return tracks

def normalize_language(lang: str) -> str:
    if not lang:
        return "Unknown"
    table = {
        "eng": "English", "en": "English",
        "hin": "Hindi", "hi": "Hindi",
        "jpn": "Japanese", "ja": "Japanese",
        "tam": "Tamil", "ta": "Tamil",
        "tel": "Telugu", "te": "Telugu",
        "kan": "Kannada", "kn": "Kannada",
        "mar": "Marathi", "mr": "Marathi",
        "ben": "Bengali", "bn": "Bengali",
        "urd": "Urdu", "ur": "Urdu",
        "fra": "French", "fr": "French",
        "spa": "Spanish", "es": "Spanish",
        "unk": "Unknown"
    }
    l = lang.strip().lower()
    return table.get(l, lang.capitalize())

def build_output_path(base_name: str, language: str, codec: str, track_no: int) -> str:
    safe_base = sanitize_filename(base_name)
    safe_lang = sanitize_filename(language).replace(" ", "")
    ext = codec if codec else "audio"
    return os.path.join(DOWNLOAD_DIR, f"{safe_base}{safe_lang}_track{track_no}.{ext}")

# ----------------- Bot Command -----------------

@app.on_message(filters.command("extaudio") & filters.private)
async def extract_audio(client: Client, message: Message):
    # Check if replied to a file
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Please reply to a video/audio file to extract its audio tracks.")
        return

    # Download original media
    file_msg = message.reply_to_message
    status_msg = await message.reply_text("Downloading media...")
    file_path = await client.download_media(file_msg)

    # Get audio tracks
    tracks = get_audio_tracks(file_path)
    if not tracks:
        await status_msg.edit_text("No audio tracks found in this file.")
        return

    await status_msg.edit_text(f"Found {len(tracks)} audio track(s). Extracting...")

    last_edit = [0, 0]
    start_time = asyncio.get_event_loop().time()

    for idx, track in enumerate(tracks, 1):
        out_path = build_output_path(file_msg.document.file_name, track["language"], track["codec"], idx)
        # ffmpeg command to extract specific audio track
        cmd = [
            "ffmpeg", "-y",
            "-i", file_path,
            "-map", f"0:a:{track['map_index']}",
            "-c", "copy",
            out_path
        ]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        while True:
            if process.returncode is not None:
                break
            await progress_bar(idx, len(tracks), status_msg, start_time, last_edit)
            await asyncio.sleep(1)
        await process.wait()
    
    await status_msg.edit_text(f"✅ Audio extraction completed. Tracks saved in `{DOWNLOAD_DIR}`")
