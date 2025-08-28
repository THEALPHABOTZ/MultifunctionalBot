from pyrogram import filters
from pyrogram.types import Message
from config import OWNER_ID
from database import Database
from bot import app

db = Database()

@app.on_message(filters.command(["addadmin"]) & filters.private)
async def add_admin_cmd(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("🚫 **Only owner can add admins!**")
    
    try:
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        elif len(message.command) == 2:
            target_id = int(message.command[1])
        else:
            return await message.reply_text(
                "**Usage:** Reply to a user or use `/addadmin user_id`"
            )

        if target_id == OWNER_ID:
            return await message.reply_text("⚠️ **Owner cannot be added as admin!**")

        success = await db.add_admin(target_id)
        
        if success:
            await message.reply_text(f"✅ **Successfully added** `{target_id}` **as admin!**")
        else:
            await message.reply_text(f"⚠️ **User** `{target_id}` **is already an admin!**")
            
    except ValueError:
        await message.reply_text("❌ **Please provide a valid user ID!**")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

@app.on_message(filters.command(["rmadmin"]) & filters.private)
async def remove_admin_cmd(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("🚫 **Only owner can remove admins!**")
    
    try:
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        elif len(message.command) == 2:
            target_id = int(message.command[1])
        else:
            return await message.reply_text(
                "**Usage:** Reply to a user or use `/rmadmin user_id`"
            )

        if target_id == OWNER_ID:
            return await message.reply_text("⚠️ **Owner cannot be removed!**")

        removed = await db.remove_admin(target_id)
        
        if removed:
            await message.reply_text(f"✅ **Successfully removed** `{target_id}` **from admin list!**")
        else:
            await message.reply_text(f"⚠️ **User** `{target_id}` **is not an admin!**")
            
    except ValueError:
        await message.reply_text("❌ **Please provide a valid user ID!**")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

@app.on_message(filters.command(["adminlist"]) & filters.private)
async def admin_list_cmd(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("🚫 **Only owner can view admin list!**")
    
    try:
        admins = await db.get_admins()
        
        if not admins:
            return await message.reply_text("⚠️ **No admins found!**")
        
        text = "**👥 Admin List:**\n\n"
        for idx, admin_id in enumerate(admins, 1):
            if admin_id == OWNER_ID:
                text += f"{idx}. `{admin_id}` **(Owner)**\n"
            else:
                text += f"{idx}. `{admin_id}`\n"
                
        await message.reply_text(text)
        
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")
