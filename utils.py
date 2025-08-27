# ---------------------------------------------------------
# Copyright (c) 2021-2025
# Developers: TheAlphaBotz
# Telegram: @TheAlphaBotz
# License: All Rights Reserved
# ---------------------------------------------------------

import os
import re
import time
import json
import subprocess
from typing import List, Dict
from config import DOWNLOAD_DIR

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def humanbytes(size: float) -> str:
    if not size:
        return "0 B"
    power = 2 ** 10
    n = 0
    units = ["B", "KB", "MB", "GB", "TB"]
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def time_formatter(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    out = []
    if h: out.append(f"{h}h")
    if m: out.append(f"{m}m")
    if s or not out: out.append(f"{s}s")
    return " ".join(out)

async def progress_bar(current, total, msg, start_time, last_edit):
    now = time.time()
    diff = max(1e-6, now - start_time)
    percent = int(current * 100 / max(1, total))
    speed = current / diff
    eta = int((total - current) / max(1e-6, speed))
    
    # Update every 7 seconds instead of every 10%
    if now - last_edit[0] >= 7:
        filled = "█" * (percent // 10)  # Sharp filled blocks
        empty = "▒" * (10 - percent // 10)  # Sharp empty blocks
        text = (
            f"「 {filled}{empty} 」 {percent}%\n"
            f"Speed: {humanbytes(speed)}/s\n"
            f"ETA: {time_formatter(eta)}"
        )
        try:
            await msg.edit_text(text)
            last_edit[0] = now  # Store last update time instead of percentage
        except:
            pass

def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
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
    safe_lang = sanitize_filename(language).replace(" ", "_")
    ext = codec if codec else "audio"
    return os.path.join(DOWNLOAD_DIR, f"{safe_base}_{safe_lang}_track{track_no}.{ext}")
        
