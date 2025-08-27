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
import asyncio
import subprocess
from typing import Dict, Any
from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID, DOWNLOAD_DIR

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class VideoSettings:
    def __init__(self):
        self.settings = {
            "codec": "libx264",
            "crf": "25",
            "resolution": "854x480",
            "preset": "veryfast",
            "audio_bitrate": "48k",
            "audio_codec": "libopus"
        }
        self.settings_file = os.path.join(DOWNLOAD_DIR, "video_settings.json")
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception:
            pass
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass
    
    def update_setting(self, key: str, value: str) -> bool:
        """Update a specific setting"""
        setting_map = {
            "codec": "codec",
            "crf": "crf", 
            "preset": "preset",
            "audio": "audio_codec",
            "audiobit": "audio_bitrate"
        }
        
        if key in setting_map:
            self.settings[setting_map[key]] = value
            self.save_settings()
            return True
        return False
    
    def get_settings_text(self) -> str:
        """Get formatted settings text"""
        return f"""**Current Video Compression Settings:**

🎥 **Codec**: `{self.settings['codec']}`
🎯 **CRF**: `{self.settings['crf']}`
📐 **Resolution**: `{self.settings['resolution']}`
⚡ **Preset**: `{self.settings['preset']}`
🔊 **Audio Codec**: `{self.settings['audio_codec']}`
🎵 **Audio Bitrate**: `{self.settings['audio_bitrate']}`

**Available Commands:**
• `/codec <value>` - Set video codec (e.g., libx264, libx265, libvpx-vp9)
• `/crf <value>` - Set CRF value (0-51, lower = better quality)
• `/preset <value>` - Set encoding preset (ultrafast, veryfast, fast, medium, slow)
• `/audio <value>` - Set audio codec (aac, libopus, mp3)
• `/audiobit <value>` - Set audio bitrate (32k, 48k, 64k, 128k, etc.)"""

# Initialize settings
video_settings = VideoSettings()

def humanbytes(size: float) -> str:
    """Convert bytes to human readable format"""
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
    """Format seconds to human readable time"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    out = []
    if h: out.append(f"{h}h")
    if m: out.append(f"{m}m")
    if s or not out: out.append(f"{s}s")
    return " ".join(out)

async def progress_bar(current, total, msg, start_time, last_edit, operation="Processing"):
    """Circular progress bar that updates every 7 seconds"""
    now = time.time()
    diff = max(1e-6, now - start_time)
    percent = int(current * 100 / max(1, total))
    speed = current / diff if operation == "Downloading" else 0
    eta = int((total - current) / max(1e-6, speed)) if speed > 0 else 0
    
    # Update every 7 seconds
    if now - last_edit[0] >= 7:
        filled = "●" * (percent // 10)    # Filled circles
        empty = "○" * (10 - percent // 10)  # Empty circles
        
        if operation == "Downloading":
            text = (
                f"📥 **Downloading...**\n\n"
                f"「 {filled}{empty} 」 {percent}%\n"
                f"**Speed**: {humanbytes(speed)}/s\n"
                f"**ETA**: {time_formatter(eta)}\n"
                f"**Size**: {humanbytes(current)} / {humanbytes(total)}"
            )
        else:
            elapsed = time_formatter(int(now - start_time))
            text = (
                f"🔄 **Compressing Video...**\n\n"
                f"「 {filled}{empty} 」 {percent}%\n"
                f"**Elapsed**: {elapsed}\n"
                f"**Frame**: {int(current)} / {int(total)}"
            )
        
        try:
            await msg.edit_text(text)
            last_edit[0] = now
        except Exception:
            pass

def sanitize_filename(name: str) -> str:
    """Sanitize filename for safe storage"""
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name

async def download_video(client: Client, message: Message) -> str:
    """Download video from Telegram with progress"""
    file_name = sanitize_filename(getattr(message.video, 'file_name', f"video_{int(time.time())}.mp4"))
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    progress_msg = await message.reply_text("📥 **Starting download...**")
    start_time = time.time()
    last_edit = [start_time - 7]  # Ensure immediate first update
    
    try:
        await client.download_media(
            message,
            file_name=file_path,
            progress=progress_bar,
            progress_args=(progress_msg, start_time, last_edit, "Downloading")
        )
        await progress_msg.edit_text("✅ **Download completed!**")
        return file_path
    except Exception as e:
        await progress_msg.edit_text(f"❌ **Download failed**: {str(e)}")
        raise

async def compress_video(input_path: str, message: Message) -> str:
    """Compress video using ffmpeg with progress tracking"""
    settings = video_settings.settings
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(DOWNLOAD_DIR, f"{base_name}_480p.mp4")
    
    # Get total frame count for progress tracking
    probe_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-count_packets", "-show_entries", "stream=nb_read_packets",
        "-csv=p=0", input_path
    ]
    
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        total_frames = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 1000
    except:
        total_frames = 1000
    
    # FFmpeg compression command
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", settings["codec"],
        "-crf", settings["crf"],
        "-s", settings["resolution"],
        "-preset", settings["preset"],
        "-c:a", settings["audio_codec"],
        "-b:a", settings["audio_bitrate"],
        "-progress", "pipe:1",
        "-y", output_path
    ]
    
    progress_msg = await message.reply_text("🔄 **Starting compression...**")
    start_time = time.time()
    last_edit = [start_time - 7]
    current_frame = 0
    
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, bufsize=1
        )
        
        # Monitor progress
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
                
            if output.startswith('frame='):
                try:
                    frame_num = int(output.split('=')[1].strip())
                    current_frame = frame_num
                    await progress_bar(current_frame, total_frames, progress_msg, start_time, last_edit, "Compressing")
                except:
                    pass
        
        process.wait()
        
        if process.returncode == 0:
            # Get file sizes
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            compression_ratio = ((input_size - output_size) / input_size) * 100
            
            await progress_msg.edit_text(
                f"✅ **Compression completed!**\n\n"
                f"📁 **Original**: {humanbytes(input_size)}\n"
                f"📁 **Compressed**: {humanbytes(output_size)}\n"
                f"💾 **Saved**: {compression_ratio:.1f}%\n"
                f"⏱️ **Time**: {time_formatter(int(time.time() - start_time))}"
            )
            return output_path
        else:
            error = process.stderr.read()
            await progress_msg.edit_text(f"❌ **Compression failed**: {error}")
            raise RuntimeError(f"FFmpeg failed: {error}")
            
    except Exception as e:
        await progress_msg.edit_text(f"❌ **Compression failed**: {str(e)}")
        raise

# Command handlers
@Client.on_message(filters.command("codec") & filters.user(OWNER_ID))
async def set_codec(client: Client, message: Message):
    """Set video codec"""
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/codec <codec_name>`\n**Examples**: `libx264`, `libx265`, `libvpx-vp9`")
        return
    
    codec = message.command[1]
    if video_settings.update_setting("codec", codec):
        await message.reply_text(f"✅ **Video codec set to**: `{codec}`")
    else:
        await message.reply_text("❌ **Failed to update codec**")

@Client.on_message(filters.command("crf") & filters.user(OWNER_ID))
async def set_crf(client: Client, message: Message):
    """Set CRF value"""
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/crf <value>`\n**Range**: 0-51 (lower = better quality)")
        return
    
    try:
        crf = int(message.command[1])
        if 0 <= crf <= 51:
            video_settings.update_setting("crf", str(crf))
            await message.reply_text(f"✅ **CRF set to**: `{crf}`")
        else:
            await message.reply_text("❌ **CRF must be between 0-51**")
    except ValueError:
        await message.reply_text("❌ **CRF must be a number**")

@Client.on_message(filters.command("preset") & filters.user(OWNER_ID))
async def set_preset(client: Client, message: Message):
    """Set encoding preset"""
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/preset <preset>`\n**Options**: ultrafast, veryfast, fast, medium, slow, slower, veryslow")
        return
    
    preset = message.command[1]
    valid_presets = ["ultrafast", "veryfast", "fast", "medium", "slow", "slower", "veryslow"]
    
    if preset in valid_presets:
        video_settings.update_setting("preset", preset)
        await message.reply_text(f"✅ **Preset set to**: `{preset}`")
    else:
        await message.reply_text(f"❌ **Invalid preset**. Choose from: {', '.join(valid_presets)}")

@Client.on_message(filters.command("audio") & filters.user(OWNER_ID))
async def set_audio_codec(client: Client, message: Message):
    """Set audio codec"""
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/audio <codec>`\n**Examples**: `aac`, `libopus`, `mp3`")
        return
    
    codec = message.command[1]
    video_settings.update_setting("audio", codec)
    await message.reply_text(f"✅ **Audio codec set to**: `{codec}`")

@Client.on_message(filters.command("audiobit") & filters.user(OWNER_ID))
async def set_audio_bitrate(client: Client, message: Message):
    """Set audio bitrate"""
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/audiobit <bitrate>`\n**Examples**: `32k`, `48k`, `64k`, `128k`")
        return
    
    bitrate = message.command[1]
    video_settings.update_setting("audiobit", bitrate)
    await message.reply_text(f"✅ **Audio bitrate set to**: `{bitrate}`")

@Client.on_message(filters.command("settings") & filters.user(OWNER_ID))
async def show_settings(client: Client, message: Message):
    """Show current settings"""
    await message.reply_text(video_settings.get_settings_text())

@Client.on_message(filters.video)
async def handle_video(client: Client, message: Message):
    """Handle incoming videos for compression"""
    try:
        # Check file size (optional limit)
        file_size = message.video.file_size
        if file_size > 2 * 1024 * 1024 * 1024:  # 2GB limit
            await message.reply_text("❌ **File too large! Maximum size: 2GB**")
            return
        
        await message.reply_text(
            f"📺 **Video received!**\n\n"
            f"📁 **Size**: {humanbytes(file_size)}\n"
            f"⏱️ **Duration**: {time_formatter(message.video.duration)}\n\n"
            f"🔄 **Starting compression with current settings...**"
        )
        
        # Download video
        input_path = await download_video(client, message)
        
        # Compress video
        output_path = await compress_video(input_path, message)
        
        # Send compressed video back
        upload_msg = await message.reply_text("📤 **Uploading compressed video...**")
        
        await client.send_video(
            chat_id=message.chat.id,
            video=output_path,
            caption=f"🎥 **Video compressed to 480p**\n\n{video_settings.get_settings_text().split('**Available Commands:**')[0]}",
            reply_to_message_id=message.id
        )
        
        await upload_msg.delete()
        
        # Clean up files
        try:
            os.remove(input_path)
            os.remove(output_path)
        except:
            pass
            
    except Exception as e:
        await message.reply_text(f"❌ **Error**: {str(e)}")
        
        # Clean up on error
        try:
            if 'input_path' in locals():
                os.remove(input_path)
            if 'output_path' in locals():
                os.remove(output_path)
        except:
            pass
      
