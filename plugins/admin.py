from pyrogram import filters
from pyrogram.types import Message
from bot import app
from config import OWNER_ID
from database import Database


async def is_admin_or_owner(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return await Database.is_admin(user_id)


@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_admin(client, message: Message):
    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID")
            return

    if not user_id:
        await message.reply_text("❌ Reply to a user or provide user ID")
        return

    if user_id == OWNER_ID:
        await message.reply_text("❌ Owner cannot be added as admin")
        return

    if await Database.is_admin(user_id):
        await message.reply_text("❌ User is already an admin")
        return

    success = await Database.add_admin(user_id)
    if success:
        try:
            user = await app.get_users(user_id)
            await message.reply_text(f"✅ {user.first_name} (`{user_id}`) added as admin")
        except:
            await message.reply_text(f"✅ User {user_id} added as admin")
    else:
        await message.reply_text("❌ Failed to add admin")


@app.on_message(filters.command("rmadmin") & filters.user(OWNER_ID))
async def remove_admin(client, message: Message):
    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID")
            return

    if not user_id:
        await message.reply_text("❌ Reply to a user or provide user ID")
        return

    success = await Database.remove_admin(user_id)
    if success:
        try:
            user = await app.get_users(user_id)
            await message.reply_text(f"✅ {user.first_name} (`{user_id}`) removed from admin")
        except:
            await message.reply_text(f"✅ User {user_id} removed from admin")
    else:
        await message.reply_text("❌ User not found in admin list")


@app.on_message(filters.command("adminlist") & filters.user(OWNER_ID))
async def admin_list(client, message: Message):
    admins = await Database.get_admins()
    if not admins:
        await message.reply_text("📝 No admins found")
        return

    text = "👥 **Admin List:**\n\n"
    for admin_id in admins:
        try:
            user = await app.get_users(admin_id)
            text += f"• {user.first_name} (`{admin_id}`)\n"
        except:
            text += f"• Unknown User (`{admin_id}`)\n"

    await message.reply_text(text)


@app.on_message(filters.command("admins"))
async def show_admins(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ Access denied")
        return

    admins = await Database.get_admins()
    if not admins:
        await message.reply_text("👥 No admins found")
        return

    text = f"👥 Total Admins: {len(admins)}\n\n"
    for admin_id in admins[:10]:
        try:
            user = await app.get_users(admin_id)
            text += f"• {user.first_name} (`{admin_id}`)\n"
        except:
            text += f"• Unknown User (`{admin_id}`)\n"

    if len(admins) > 10:
        text += f"\n...and {len(admins) - 10} more"

    await message.reply_text(text)
