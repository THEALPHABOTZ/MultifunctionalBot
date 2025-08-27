# ---------------------------------------------------------
# Copyright (c) 2021-2025
# Developers: TheAlphaBotz
# Telegram: @TheAlphaBotz
# License: All Rights Reserved
# ---------------------------------------------------------

import os
import time
import subprocess
from pyrogram import filters
from bot import app
from config import DOWNLOAD_DIR
from utils import (
    progress_bar, get_audio_tracks, build_output_path,
    sanitize_filename
)

@app.on_message(filters.command("extaudio") & filters.reply)
async def extaudio_cmd(client, message):
    replied = message.reply_to_message
    if not (replied and (replied.video or replied.document or replied.audio)):
        await message.reply_text("Reply to a video/document message with /extaudio.")
        return

    msg = await message.reply_text("Downloading file…")
    last_edit = [0]
    start_time = time.time()

    orig_name = (replied.video and replied.video.file_name) or \
                (replied.document and replied.document.file_name) or \
                (replied.audio and replied.audio.file_name) or \
                "input"
    base_name = os.path.splitext(os.path.basename(orig_name))[0]

    file_path = await replied.download(
        file_name=os.path.join(DOWNLOAD_DIR, sanitize_filename(orig_name)),
        progress=progress_bar,
        progress_args=(msg, start_time, last_edit)
    )

    await msg.edit_text("Scanning audio streams…")
    try:
        tracks = get_audio_tracks(file_path)
    except Exception as e:
        await msg.edit_text(f"ffprobe failed: {e}")
        try: os.remove(file_path)
        except: pass
        return

    if not tracks:
        await msg.edit_text("No audio tracks found.")
        try: os.remove(file_path)
        except: pass
        return

    extracted = 0
    errors = []

    for i, t in enumerate(tracks, start=1):
        out_path = build_output_path(base_name, t["language"], t["codec"], i)
        cmd = [
            "ffmpeg", "-y",
            "-i", file_path,
            "-map", f"0:a:{t['map_index']}",
            "-c", "copy",
            out_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0 or not os.path.exists(out_path):
                raise RuntimeError(res.stderr.strip() or "ffmpeg failed")

            up_msg = await message.reply_text(f"Uploading track {i}…")
            last_edit_up = [0]
            start_up = time.time()

            caption = f"Extracted Track {i} | Language: {t['language']}"
            await message.reply_document(
                out_path,
                caption=caption,
                progress=progress_bar,
                progress_args=(up_msg, start_up, last_edit_up)
            )
            await up_msg.delete()
            extracted += 1
            try: os.remove(out_path)
            except: pass
        except Exception as e:
            errors.append(f"Track {i} ({t['language']}): {e}")

    try: os.remove(file_path)
    except: pass

    if errors:
        err_text = "\n".join(errors[:6])
        await msg.edit_text(f"Done: {extracted}/{len(tracks)} extracted.\nErrors:\n{err_text}")
    else:
        await msg.edit_text(f"All {extracted} audio tracks extracted.")
