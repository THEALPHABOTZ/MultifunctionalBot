# ---------------------------------------------------------
# Copyright (c) 2021-2025
# Developers: TheAlphaBotz
# Telegram: @TheAlphaBotz
# License: All Rights Reserved
# ---------------------------------------------------------

import time

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

def time_formatter(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    out = []
    if h: out.append(f"{h}h")
    if m: out.append(f"{m}m")
    if s or not out: out.append(f"{s}s")
    return " ".join(out)

async def progress_bar(current, total, msg, start_time, last_edit):
    """
    Stylish '●●●○○○○○○○' progress bar.
    Updates every 7 seconds.
    """
    now = time.time()
  
    if now - last_edit[1] < 7:
        return

    diff = max(1e-6, now - start_time)
    percent = int(current * 100 / max(1, total))
    speed = current / diff
    eta = int((total - current) / max(1e-6, speed))

    blocks = 10
    filled_blocks = int(blocks * percent // 100)
    empty_blocks = blocks - filled_blocks

    bar = "●" * filled_blocks + "○" * empty_blocks

    text = (
        f"Progress: |{bar}| {percent}%\n"
        f"Speed: {humanbytes(speed)}/s\n"
        f"ETA: {time_formatter(eta)}"
    )

    try:
        await msg.edit_text(text)
        last_edit[0] = percent
        last_edit[1] = now  
    except:
        pass
