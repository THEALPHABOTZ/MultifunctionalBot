# ---------------------------------------------------------
# Copyright (c) 2021-2025
# Developers: TheAlphaBotz
# Telegram: @TheAlphaBotz
# License: All Rights Reserved
# ---------------------------------------------------------

import os
import pkgutil
import importlib
from bot import app

BANNER = r"""
---------------------------------------------------------
   Telegram Bot  [2021–2025]
   Developers: TheAlphaBotz  |  Telegram: @TheAlphaBotz
---------------------------------------------------------
"""

def load_plugins():
    base = os.path.join(os.path.dirname(__file__), "plugins")
    pkg_name = "plugins"
    for mod in pkgutil.iter_modules([base]):
        if mod.ispkg:
            continue
        name = f"{pkg_name}.{mod.name}"
        try:
            importlib.import_module(name)
            print(f"[PLUGIN LOADED] {name}")
        except Exception as e:
            print(f"[PLUGIN ERROR ] {name} -> {e}")

if __name__ == "__main__":
    print(BANNER)
    load_plugins()
    print("Bot is running...")
    app.run()
