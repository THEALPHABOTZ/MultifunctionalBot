import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID
from database import Database

db = Database()
logger = logging.getLogger(__name__)


# ─────────────────────────────
# Database utility functions
# ─────────────────────────────

async def add_admin_to_db(user_id: int) -> bool:
    try:
        existing = await db.admin_collection.find_one({"user_id": user_id})
        if existing:
            return False
        await db.admin_collection.insert_one({"user_id": user_id})
        return True
    except Exception as e:
        logger.error(f"Error adding admin: {e}")
        return False


async def remove_admin_from_db(user_id: int) -> bool:
    try:
        result = await db.admin_collection.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing admin: {e}")
        return False


async def get_all_admin_ids() -> list:
    try:
        cursor = db.admin_collection.find({})
        admins = await cursor.to_list(length=None)
        admin_ids = [admin["user_id"] for admin in admins]
        admin_ids.append(OWNER_ID)  # always include owner
        return list(set(admin_ids))
    except Exception as e:
        logger.error(f"Error fetching admins: {e}")
        return [OWNER_ID]


# ─────────────────────────────
# Command handlers
# ─────────────────────────────

@Client.on_message(filters.command("addadmin") & filters.private)
async def add_admin_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("🚫 Only the owner can add admins.")

    if len(message.command) != 2:
        return await message.reply_text("Usage: `/addadmin user_id`")

    try:
        target_id = int(message.command[1])
        success = await add_admin_to_db(target_id)
        if success:
            await message.reply_text(f"✅ User `{target_id}` added as admin.")
        else:
            await message.reply_text(f"⚠️ User `{target_id}` is already an admin.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{str(e)}`")


@Client.on_message(filters.command("rmadmin") & filters.private)
async def remove_admin_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("🚫 Only the owner can remove admins.")

    if len(message.command) != 2:
        return await message.reply_text("Usage: `/rmadmin user_id`")

    try:
        target_id = int(message.command[1])
        removed = await remove_admin_from_db(target_id)
        if removed:
            await message.reply_text(f"✅ User `{target_id}` removed from admin list.")
        else:
            await message.reply_text(f"⚠️ User `{target_id}` was not in admin list.")
    except Exception as e:
        await message.reply_text(f"❌ Error: `{str(e)}`")


@Client.on_message(filters.command("adminlist") & filters.private)
async def list_admins_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("🚫 Only the owner can view admins.")

    try:
        admin_ids = await get_all_admin_ids()
        text = "**🔐 Admins:**\n" + "\n".join([f"- `{uid}`" for uid in admin_ids])
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ Error: `{str(e)}`")
