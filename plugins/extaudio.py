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
import time
from bot import app
from typing import List, Dict
from pyrogram import Client, filters
from pyrogram.types import Message
from config import DOWNLOAD_DIR
from progressbar import humanbytes, time_formatter

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ----------------- Circular Progress Bar -----------------

def get_circular_progress(percentage: float) -> str:
    """Generate circular progress bar representation"""
    if percentage < 0:
        percentage = 0
    elif percentage > 100:
        percentage = 100
    
    # Circular progress states
    circles = ["◯", "◔", "◑", "◕", "●"]
    filled_circles = int(percentage // 20)
    remainder = percentage % 20
    
    # Create progress string
    progress_str = "●" * filled_circles
    
    if filled_circles < 5:
        if remainder < 5:
            progress_str += "◯"
        elif remainder < 10:
            progress_str += "◔"
        elif remainder < 15:
            progress_str += "◑"
        else:
            progress_str += "◕"
        
        # Add empty circles
        progress_str += "◯" * (4 - filled_circles)
    
    return progress_str

def format_circular_progress(current: int, total: int, file_name: str, start_time: float) -> str:
    """Format the circular progress message"""
    percentage = (current / total) * 100 if total > 0 else 0
    elapsed_time = time.time() - start_time
    
    # Circular progress bar
    circular_bar = get_circular_progress(percentage)
    
    # Time formatting
    elapsed_str = time_formatter(elapsed_time)
    
    # Estimate remaining time
    if percentage > 0:
        total_estimated = elapsed_time * (100 / percentage)
        remaining = total_estimated - elapsed_time
        remaining_str = time_formatter(remaining) if remaining > 0 else "0s"
    else:
        remaining_str = "Calculating..."
    
    message = f"""
🎵 **Extracting Audio Tracks**

📁 **File:** `{file_name}`
📊 **Progress:** {circular_bar} `{percentage:.1f}%`
🎯 **Track:** `{current}/{total}`

⏱️ **Elapsed:** `{elapsed_str}`
⏳ **Remaining:** `{remaining_str}`

🔄 *Processing...*
"""
    return message

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

async def extract_single_track(file_path: str, track: Dict, output_path: str) -> bool:
    """Extract a single audio track using ffmpeg"""
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-map", f"0:a:{track['map_index']}",
        "-c", "copy",
        output_path
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()
        return process.returncode == 0
    except Exception as e:
        print(f"Error extracting track: {e}")
        return False

# ----------------- Bot Command -----------------

@app.on_message(filters.command("extaudio") & filters.private)
async def extract_audio(client: Client, message: Message):
    # Check if replied to a file
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Please reply to a video/audio file to extract its audio tracks.")
        return

    # Download original media
    file_msg = message.reply_to_message
    status_msg = await message.reply_text("📥 **Downloading media...**")
    
    try:
        file_path = await client.download_media(file_msg)
        
        # Get audio tracks
        await status_msg.edit_text("🔍 **Analyzing audio tracks...**")
        tracks = get_audio_tracks(file_path)
        
        if not tracks:
            await status_msg.edit_text("❌ **No audio tracks found in this file.**")
            return

        # Start extraction process
        file_name = file_msg.document.file_name or "Unknown"
        total_tracks = len(tracks)
        start_time = time.time()
        last_update = 0
        
        await status_msg.edit_text(
            format_circular_progress(0, total_tracks, file_name, start_time)
        )

        successful_extractions = 0
        
        for idx, track in enumerate(tracks, 1):
            current_time = time.time()
            
            # Update progress every 7 seconds or on track completion
            if current_time - last_update >= 7 or idx == 1:
                progress_text = format_circular_progress(idx-1, total_tracks, file_name, start_time)
                try:
                    await status_msg.edit_text(progress_text)
                    last_update = current_time
                except Exception:
                    pass  # Ignore edit errors (rate limits, etc.)
            
            # Extract the track
            out_path = build_output_path(
                file_name, 
                track["language"], 
                track["codec"], 
                idx
            )
            
            success = await extract_single_track(file_path, track, out_path)
            if success:
                successful_extractions += 1
            
            # Update progress after track completion
            try:
                progress_text = format_circular_progress(idx, total_tracks, file_name, start_time)
                await status_msg.edit_text(progress_text)
            except Exception:
                pass

        # Final completion message
        total_time = time_formatter(time.time() - start_time)
        
        if successful_extractions == total_tracks:
            completion_text = f"""
✅ **Audio Extraction Completed!**

📁 **File:** `{file_name}`
🎵 **Tracks Extracted:** `{successful_extractions}/{total_tracks}`
📍 **Location:** `{DOWNLOAD_DIR}`
⏱️ **Total Time:** `{total_time}`

🎉 **All tracks extracted successfully!**
"""
        else:
            completion_text = f"""
⚠️ **Audio Extraction Completed with Issues**

📁 **File:** `{file_name}`
🎵 **Successful:** `{successful_extractions}/{total_tracks}`
📍 **Location:** `{DOWNLOAD_DIR}`
⏱️ **Total Time:** `{total_time}`

❗ **Some tracks failed to extract**
"""
        
        await status_msg.edit_text(completion_text)
        
        # Clean up downloaded file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        error_text = f"❌ **Error during extraction:**\n\n`{str(e)}`"
        await status_msg.edit_text(error_text)
    
