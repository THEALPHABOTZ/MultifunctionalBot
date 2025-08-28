from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID
from database import Database

db = Database()

def check_user(func):
    async def wrapper(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text("Only owner can use this command!")
            return
        return await func(client, message)
    return wrapper

@Client.on_message(filters.command("addadmin") & filters.private)
@check_user
async def add_admin(client, message):
    try:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
        elif len(message.command) == 2:
            user_id = int(message.command[1])
        else:
            return await message.reply_text(
                "Reply to a user's message or use /addadmin user_id"
            )

        if await db.add_admin(user_id):
            await message.reply_text(f"Successfully added {user_id} as admin!")
        else:
            await message.reply_text("Failed to add admin or already an admin!")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

@Client.on_message(filters.command("rmadmin") & filters.private)
@check_user
async def remove_admin(client, message):
    try:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
        elif len(message.command) == 2:
            user_id = int(message.command[1])
        else:
            return await message.reply_text(
                "Reply to a user's message or use /rmadmin user_id"
            )

        if await db.remove_admin(user_id):
            await message.reply_text(f"Successfully removed {user_id} from admin list!")
        else:
            await message.reply_text("Failed to remove admin or not an admin!")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

@Client.on_message(filters.command("adminlist") & filters.private)
@check_user
async def admin_list(client, message):
    try:
        admins = await db.get_admins()
        if not admins:
            return await message.reply_text("No admins found!")
        
        text = "**Admin List:**\n\n"
        for idx, admin_id in enumerate(admins, 1):
            text += f"{idx}. `{admin_id}`\n"
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
