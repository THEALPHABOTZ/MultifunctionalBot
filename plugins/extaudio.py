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
from typing import List, Dict
from config import DOWNLOAD_DIR
from progressbar import progress_bar, humanbytes, time_formatter  

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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
