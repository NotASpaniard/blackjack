import os
from typing import Dict, Any

class Config:
    """Cấu hình bot"""
    DEFAULT_PREFIX = "!"
    STARTING_BALANCE = 1000
    ADMIN_IDS = [123456789]  # Thay bằng ID admin thực tế
    DATABASE_URL = "sqlite:///casino_bot.db"
    
    # Emoji cho các trò chơi
    EMOJIS = {
        "cards": {
            "hearts": "♥",
            "diamonds": "♦", 
            "clubs": "♣",
            "spades": "♠"
        },
        "bau_cua": {
            "bau": "🎉",
            "cua": "🦀", 
            "tom": "🦐",
            "ca": "🐟",
            "ga": "🐓",
            "nai": "🦌"
        },
        "xoc_dia": {
            "heads": "🟡",
            "tails": "⚫"
        }
    }

config = Config()