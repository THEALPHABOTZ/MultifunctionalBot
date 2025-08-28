import os
import re
import time
import math
import asyncio
import subprocess
from pyrogram import filters
from pyrogram.types import Message
from bot import app
from config import OWNER_ID, DOWNLOAD_DIR
from database import Database, thumbnail_manager

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
    
    async def load_settings(self):
        try:
            saved_settings = await Database.load_video_settings()
            if saved_settings:
                self.settings.update(saved_settings)
        except Exception:
            pass
    
    async def save_settings(self):
        try:
            await Database.save_video_settings(self.settings)
        except Exception:
            pass
    
    async def update_setting(self, key: str, value: str) -> bool:
        setting_map = {
            "codec": "codec",
            "crf": "crf", 
            "preset": "preset",
            "audio": "audio_codec",
            "audiobit": "audio_bitrate"
        }
        
        if key in setting_map:
            self.settings[setting_map[key]] = value
            await self.save_settings()
            return True
        return False
    
    def get_settings_text(self) -> str:
        return f"""**Current Video Compression Settings:**

🎥 **Codec**: `{self.settings['codec']}`
🎯 **CRF**: `{self.settings['crf']}`
📐 **Resolution**: `{self.settings['resolution']}`
⚡ **Preset**: `{self.settings['preset']}`
🔊 **Audio Codec**: `{self.settings['audio_codec']}`
🎵 **Audio Bitrate**: `{self.settings['audio_bitrate']}`

**Available Commands:**
• `/codec <value>` - Set video codec
• `/crf <value>` - Set CRF value (0-51)
• `/preset <value>` - Set encoding preset
• `/audio <value>` - Set audio codec
• `/audiobit <value>` - Set audio bitrate"""

video_settings = VideoSettings()

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

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2] if tmp else "0s"

async def is_admin_or_owner(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return await Database.is_admin(user_id)

async def get_video_duration(video_path: str) -> int:
    process = subprocess.Popen(
        ['ffmpeg', "-hide_banner", '-i', video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    stdout, stderr = process.communicate()
    output = stdout.decode().strip()
    duration = re.search(r"Duration:\s*(\d*):(\d*):(\d+\.?\d*)[\s\w*$]", output)
    
    if duration is not None:
        hours = int(duration.group(1))
        minutes = int(duration.group(2))
        seconds = math.floor(float(duration.group(3)))
        total_seconds = (hours * 60 * 60) + (minutes * 60) + seconds
        return total_seconds
    return 0

async def progress_bar(current, total, msg, start_time, last_edit, operation="Processing"):
    now = time.time()
    diff = max(1e-6, now - start_time)
    percent = int(current * 100 / max(1, total))
    speed = current / diff if operation == "Downloading" else 0
    eta = int((total - current) / max(1e-6, speed)) if speed > 0 else 0
    
    if now - last_edit[0] >= 7:
        filled = "●" * (percent // 10)
        empty = "○" * (10 - percent // 10)
        text = (
            f"📥 **Downloading...**\n\n"
            f"「 {filled}{empty} 」 {percent}%\n"
            f"**Speed**: {humanbytes(speed)}/s\n"
            f"**ETA**: {time_formatter(eta * 1000)}\n"
            f"**Size**: {humanbytes(current)} / {humanbytes(total)}"
        )
        
        try:
            await msg.edit_text(text)
            last_edit[0] = now
        except Exception:
            pass

def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name

async def download_video(message: Message) -> str:
    media = message.video or message.document
    file_name = sanitize_filename(getattr(media, 'file_name', f"video_{int(time.time())}.mp4"))
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    progress_msg = await message.reply_text("📥 **Starting download...**")
    start_time = time.time()
    last_edit = [start_time - 7]
    
    try:
        await app.download_media(
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
    await video_settings.load_settings()
    settings = video_settings.settings
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(DOWNLOAD_DIR, f"{base_name}_480p.mp4")
    progress_file = os.path.join(DOWNLOAD_DIR, f"progress_{int(time.time())}.txt")
    
    with open(progress_file, 'w') as f:
        pass
    
    total_duration = await get_video_duration(input_path)
    if total_duration == 0:
        total_duration = 3600
    
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "quiet",
        "-progress", progress_file,
        "-i", input_path,
        "-c:v", settings["codec"],
        "-crf", settings["crf"],
        "-s", settings["resolution"],
        "-preset", settings["preset"],
        "-c:a", settings["audio_codec"],
        "-b:a", settings["audio_bitrate"],
        "-y", output_path
    ]
    
    progress_msg = await message.reply_text("🔄 **Starting compression...**")
    compression_start_time = time.time()
    last_update_time = compression_start_time - 7
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        is_done = False
        while process.returncode is None:
            await asyncio.sleep(3)
            
            if time.time() - last_update_time >= 7:
                try:
                    with open(progress_file, 'r') as file:
                        text = file.read()
                        
                        frame = re.findall(r"frame=(\d+)", text)
                        time_in_us = re.findall(r"out_time_ms=(\d+)", text)
                        progress_status = re.findall(r"progress=(\w+)", text)
                        speed = re.findall(r"speed=(\d+\.?\d*)", text)
                        
                        if len(frame):
                            frame = int(frame[-1])
                        else:
                            frame = 1
                            
                        if len(speed):
                            speed_val = float(speed[-1])
                        else:
                            speed_val = 1
                            
                        if len(time_in_us):
                            elapsed_time = int(time_in_us[-1]) / 1000000
                        else:
                            elapsed_time = 1
                            
                        if len(progress_status):
                            if progress_status[-1] == "end":
                                is_done = True
                                break
                        
                        percentage = math.floor(elapsed_time * 100 / total_duration)
                        percentage = min(100, max(0, percentage))
                        
                        difference = math.floor((total_duration - elapsed_time) / float(speed_val))
                        eta = time_formatter(difference * 1000) if difference > 0 else "calculating..."
                        
                        filled = "█" * (percentage // 10)
                        empty = "░" * (10 - (percentage // 10))
                        
                        progress_str = f"♻️ᴘʀᴏɢʀᴇss: {percentage}%\n[{filled}{empty}]"
                        
                        stats = (
                            f"⚡ ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss\n\n"
                            f"🕛 ᴛɪᴍᴇ ʟᴇғᴛ: {eta}\n\n"
                            f"{progress_str}"
                        )
                        
                        await progress_msg.edit_text(stats)
                        last_update_time = time.time()
                        
                except Exception:
                    pass
        
        stdout, stderr = await process.communicate()
        
        try:
            os.remove(progress_file)
        except:
            pass
        
        if process.returncode == 0:
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            compression_ratio = ((input_size - output_size) / input_size) * 100
            
            await progress_msg.edit_text(
                f"✅ **Compression completed!**\n\n"
                f"📁 **Original**: {humanbytes(input_size)}\n"
                f"📁 **Compressed**: {humanbytes(output_size)}\n"
                f"💾 **Saved**: {compression_ratio:.1f}%\n"
                f"⏱️ **Time**: {time_formatter(int((time.time() - compression_start_time) * 1000))}"
            )
            return output_path
        else:
            error = stderr.decode() if stderr else "Unknown error"
            await progress_msg.edit_text(f"❌ **Compression failed**: {error}")
            raise RuntimeError(f"FFmpeg failed: {error}")
            
    except Exception as e:
        try:
            os.remove(progress_file)
        except:
            pass
        await progress_msg.edit_text(f"❌ **Compression failed**: {str(e)}")
        raise

@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_admin(client, message: Message):
    user_id = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ **Invalid user ID**")
            return
    
    if not user_id:
        await message.reply_text("❌ **Reply to a user or provide user ID**")
        return
    
    if user_id == OWNER_ID:
        await message.reply_text("❌ **Owner cannot be added as admin**")
        return
    
    success = await Database.add_admin(user_id)
    if success:
        await message.reply_text(f"✅ **User {user_id} added as admin**")
    else:
        await message.reply_text("❌ **Failed to add admin**")

@app.on_message(filters.command("rmadmin") & filters.user(OWNER_ID))
async def remove_admin(client, message: Message):
    user_id = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ **Invalid user ID**")
            return
    
    if not user_id:
        await message.reply_text("❌ **Reply to a user or provide user ID**")
        return
    
    success = await Database.remove_admin(user_id)
    if success:
        await message.reply_text(f"✅ **User {user_id} removed from admin**")
    else:
        await message.reply_text("❌ **User not found in admin list**")

@app.on_message(filters.command("adminlist") & filters.user(OWNER_ID))
async def admin_list(client, message: Message):
    admins = await Database.get_admins()
    if not admins:
        await message.reply_text("📝 **No admins found**")
        return
    
    admin_text = "👥 **Admin List:**\n\n"
    for admin_id in admins:
        admin_text += f"• `{admin_id}`\n"
    
    await message.reply_text(admin_text)

@app.on_message(filters.command("setthumbnail") & filters.user(OWNER_ID))
async def set_thumbnail(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("❌ **Reply to a photo to set as thumbnail**")
        return
    
    try:
        temp_path = await app.download_media(message.reply_to_message.photo)
        success = await thumbnail_manager.set_thumbnail(temp_path)
        
        if success:
            await message.reply_text("✅ **Thumbnail set successfully**")
        else:
            await message.reply_text("❌ **Failed to set thumbnail**")
        
        try:
            os.remove(temp_path)
        except:
            pass
            
    except Exception as e:
        await message.reply_text(f"❌ **Error setting thumbnail**: {str(e)}")

@app.on_message(filters.command("getthumbnail") & filters.user(OWNER_ID))
async def get_thumbnail(client, message: Message):
    thumbnail_path = await thumbnail_manager.get_thumbnail()
    if thumbnail_path:
        await message.reply_photo(thumbnail_path, caption="📷 **Current Thumbnail**")
    else:
        await message.reply_text("❌ **No thumbnail set**")

@app.on_message(filters.command("delthumbnail") & filters.user(OWNER_ID))
async def delete_thumbnail(client, message: Message):
    success = await thumbnail_manager.delete_thumbnail()
    if success:
        await message.reply_text("✅ **Thumbnail deleted successfully**")
    else:
        await message.reply_text("❌ **No thumbnail found to delete**")

@app.on_message(filters.command("codec"))
async def set_codec(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
        
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/codec <codec_name>`\n**Examples**: `libx264`, `libx265`, `libvpx-vp9`")
        return
    
    codec = message.command[1]
    if await video_settings.update_setting("codec", codec):
        await message.reply_text(f"✅ **Video codec set to**: `{codec}`")
    else:
        await message.reply_text("❌ **Failed to update codec**")

@app.on_message(filters.command("crf"))
async def set_crf(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
        
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/crf <value>`\n**Range**: 0-51 (lower = better quality)")
        return
    
    try:
        crf = int(message.command[1])
        if 0 <= crf <= 51:
            await video_settings.update_setting("crf", str(crf))
            await message.reply_text(f"✅ **CRF set to**: `{crf}`")
        else:
            await message.reply_text("❌ **CRF must be between 0-51**")
    except ValueError:
        await message.reply_text("❌ **CRF must be a number**")

@app.on_message(filters.command("preset"))
async def set_preset(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
        
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/preset <preset>`\n**Options**: ultrafast, veryfast, fast, medium, slow, slower, veryslow")
        return
    
    preset = message.command[1]
    valid_presets = ["ultrafast", "veryfast", "fast", "medium", "slow", "slower", "veryslow"]
    
    if preset in valid_presets:
        await video_settings.update_setting("preset", preset)
        await message.reply_text(f"✅ **Preset set to**: `{preset}`")
    else:
        await message.reply_text(f"❌ **Invalid preset**. Choose from: {', '.join(valid_presets)}")

@app.on_message(filters.command("audio"))
async def set_audio_codec(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
        
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/audio <codec>`\n**Examples**: `aac`, `libopus`, `mp3`")
        return
    
    codec = message.command[1]
    await video_settings.update_setting("audio", codec)
    await message.reply_text(f"✅ **Audio codec set to**: `{codec}`")

@app.on_message(filters.command("audiobit"))
async def set_audio_bitrate(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
        
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage**: `/audiobit <bitrate>`\n**Examples**: `32k`, `48k`, `64k`, `128k`")
        return
    
    bitrate = message.command[1]
    await video_settings.update_setting("audiobit", bitrate)
    await message.reply_text(f"✅ **Audio bitrate set to**: `{bitrate}`")

@app.on_message(filters.command("settings"))
async def show_settings(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
        
    await video_settings.load_settings()
    await message.reply_text(video_settings.get_settings_text())

@app.on_message(filters.command("test480") & filters.user(OWNER_ID))
async def test_plugin(client, message: Message):
    await message.reply_text("✅ **480p Plugin is working!**\n\nReply to a video with `/c480p` to compress it to 480p.")

@app.on_message(filters.command("c480p"))
async def compress_video_command(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ **Please reply to a video file with this command**")
        return
    
    replied_message = message.reply_to_message
    
    if not (replied_message.video or (replied_message.document and replied_message.document.mime_type and replied_message.document.mime_type.startswith("video"))):
        await message.reply_text("❌ **The replied message must contain a video file**")
        return
    
    try:
        media = replied_message.video or replied_message.document
        file_size = media.file_size
        
        if file_size > 2 * 1024 * 1024 * 1024:
            await message.reply_text("❌ **File too large! Maximum size: 2GB**")
            return
        
        duration = getattr(media, 'duration', 0) or 0
        
        await message.reply_text(
            f"📺 **Video received!**\n\n"
            f"📁 **Size**: {humanbytes(file_size)}\n"
            f"⏱️ **Duration**: {duration}s\n\n"
            f"🔄 **Starting compression with current settings...**"
        )
        
        input_path = await download_video(replied_message)
        output_path = await compress_video(input_path, message)
        
        upload_msg = await message.reply_text("📤 **Uploading compressed video...**")
        
        thumbnail_path = await thumbnail_manager.get_thumbnail()
        
        await app.send_document(
            chat_id=message.chat.id,
            document=output_path,
            thumb=thumbnail_path,
            caption=f"🎥 **Video compressed to 480p**\n\n{video_settings.get_settings_text().split('**Available Commands:**')[0]}",
            reply_to_message_id=message.reply_to_message.id
 
