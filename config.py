import os
from typing import Dict, Any, List

class Config:
    """Cấu hình bot"""
    DEFAULT_PREFIX = "!"
    STARTING_BALANCE = 1000
    
    # Lấy ID admin từ biến môi trường
    ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
    
    # Lấy ID server được phép từ biến môi trường (nếu có)
    ALLOWED_GUILD_IDS = [int(id.strip()) for id in os.getenv('ALLOWED_GUILD_IDS', '').split(',') if id.strip()]
    
    # Mode restricted - nếu True, bot chỉ chạy trên server được chỉ định
    RESTRICTED_MODE = os.getenv('RESTRICTED_MODE', 'False').lower() == 'true'
    
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///casino_bot.db')
    
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