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
        try:
            user = await app.get_users(user_id)
            name = user.first_name if user.first_name else "Unknown User"
            await message.reply_text(f"✅ **{name} ({user_id}) added as admin**")
        except:
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
        try:
            user = await app.get_users(user_id)
            name = user.first_name if user.first_name else "Unknown User"
            await message.reply_text(f"✅ **{name} ({user_id}) removed from admin**")
        except:
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
        try:
            user = await app.get_users(admin_id)
            name = user.first_name if user.first_name else "Unknown"
            username = f"@{user.username}" if user.username else "No username"
            admin_text += f"• **{name}** - {username} (`{admin_id}`)\n"
        except:
            admin_text += f"• **Unknown User** (`{admin_id}`)\n"
    
    await message.reply_text(admin_text)

@app.on_message(filters.command("admins"))
async def show_admins(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
    
    admins = await Database.get_admins()
    admin_count = len(admins)
    
    admin_text = f"👥 **Total Admins**: {admin_count}\n\n"
    
    if admin_count > 0:
        admin_text += "**Admin List:**\n"
        for admin_id in admins[:10]:
            try:
                user = await app.get_users(admin_id)
                name = user.first_name if user.first_name else "Unknown"
                admin_text += f"• {name} (`{admin_id}`)\n"
            except:
                admin_text += f"• Unknown User (`{admin_id}`)\n"
        
        if admin_count > 10:
            admin_text += f"\n*... and {admin_count - 10} more admins*"
    else:
        admin_text += "**No admins found**"
    
    await message.reply_text(admin_text)

@app.on_message(filters.command("promote") & filters.user(OWNER_ID))
async def promote_user(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ **Reply to a user to promote them as admin**")
        return
    
    user_id = message.reply_to_message.from_user.id
    
    if user_id == OWNER_ID:
        await message.reply_text("❌ **Owner cannot be promoted as admin**")
        return
    
    if await Database.is_admin(user_id):
        await message.reply_text("❌ **User is already an admin**")
        return
    
    success = await Database.add_admin(user_id)
    if success:
        user = message.reply_to_message.from_user
        name = user.first_name if user.first_name else "Unknown User"
        await message.reply_text(f"✅ **{name} promoted as admin**")
    else:
        await message.reply_text("❌ **Failed to promote user**")

@app.on_message(filters.command("demote") & filters.user(OWNER_ID))
async def demote_user(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ **Reply to a user to demote them from admin**")
        return
    
    user_id = message.reply_to_message.from_user.id
    
    if not await Database.is_admin(user_id):
        await message.reply_text("❌ **User is not an admin**")
        return
    
    success = await Database.remove_admin(user_id)
    if success:
        user = message.reply_to_message.from_user
        name = user.first_name if user.first_name else "Unknown User"
        await message.reply_text(f"✅ **{name} demoted from admin**")
    else:
        await message.reply_text("❌ **Failed to demote user**")

@app.on_message(filters.command("adminhelp"))
async def admin_help(client, message: Message):
    if not await is_admin_or_owner(message.from_user.id):
        await message.reply_text("❌ **Access denied**")
        return
    
    help_text = """
🔧 **Admin Commands:**

**Owner Only:**
• `/addadmin <user_id>` - Add admin by ID
• `/rmadmin <user_id>` - Remove admin by ID
• `/promote` - Promote replied user as admin
• `/demote` - Demote replied user from admin
• `/adminlist` - Show detailed admin list

**Admin & Owner:**
• `/admins` - Show admin count and list
• `/adminhelp` - Show this help message

**Video Compression Settings:**
• `/codec <value>` - Set video codec
• `/crf <value>` - Set CRF value (0-51)
• `/preset <value>` - Set encoding preset
• `/audio <value>` - Set audio codec
• `/audiobit <value>` - Set audio bitrate
• `/settings` - Show current settings

**Thumbnail Management:**
• `/setthumbnail` - Set custom thumbnail (Owner only)
• `/getthumbnail` - Get current thumbnail (Owner only)
• `/delthumbnail` - Delete current thumbnail (Owner only)
"""
    
    await message.reply_text(help_text)
        
