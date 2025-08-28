from pyrogram import Client, filters
from pyrogram.types import Message
from database import Database
from config import OWNER_ID
import os

db = Database()
THUMB_DIR = "thumbnails"
os.makedirs(THUMB_DIR, exist_ok=True)

async def is_admin_or_owner(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    admins = await db.get_admins()
    return user_id in admins

@Client.on_message(filters.command(["savethumb", "setthumb"]) & filters.private)
async def save_thumbnail(client, message: Message):
    user_id = message.from_user.id
    
    if not await is_admin_or_owner(user_id):
        return await message.reply_text("Only owner and admins can save thumbnails!")
    
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text("Reply to a photo to save it as thumbnail.")
    
    try:
        file_id = message.reply_to_message.photo.file_id
        if await db.save_thumbnail(user_id, file_id):
            await message.reply_text("✅ Thumbnail saved successfully!")
        else:
            await message.reply_text("❌ Failed to save thumbnail!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.command(["delthumb", "rmthumb"]) & filters.private)
async def delete_thumbnail(client, message: Message):
    user_id = message.from_user.id
    
    if not await is_admin_or_owner(user_id):
        return await message.reply_text("Only owner and admins can delete thumbnails!")
    
    try:
        if await db.delete_thumbnail(user_id):
            await message.reply_text("✅ Thumbnail deleted successfully!")
        else:
            await message.reply_text("❌ No thumbnail found to delete!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("showthumb") & filters.private)
async def show_thumbnail(client, message: Message):
    user_id = message.from_user.id
    
    try:
        thumb = await db.get_thumbnail(user_id)
        if thumb:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=thumb,
                caption="Your current thumbnail"
            )
        else:
            await message.reply_text("No thumbnail found!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
