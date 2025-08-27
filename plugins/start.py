# ---------------------------------------------------------
# Copyright (c) 2021-2025
# Developers: TheAlphaBotz
# Telegram: @TheAlphaBotz
# License: All Rights Reserved
# ---------------------------------------------------------

from pyrogram import filters
from bot import app

@app.on_message(filters.command("start"))
async def start_cmd(_, message):
    await message.reply_text(
        "Reply to a video/document with /extaudio to extract ALL audio tracks."
    )
