# ---------------------------------------------------------
# Copyright (c) 2021-2025
# Developers: TheAlphaBotz
# Telegram: @TheAlphaBotz
# License: All Rights Reserved
# ---------------------------------------------------------

from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "video_audio_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)
