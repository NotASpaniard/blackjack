import discord
from discord.ext import commands
import os
import logging
from typing import Optional, Dict, Any
import asyncio

from database.database_manager import DatabaseManager
from games.blackjack import BlackjackGame, BlackjackGame
from games.bau_cua import BauCuaGame, BauCuaAnimal
from games.xoc_dia import XocDiaGame, XocDiaBetType
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('casino_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class CasinoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix=self.get_prefix, intents=intents)
        
        self.db = DatabaseManager()
        self.active_games: Dict[str, Any] = {}
        
    async def get_prefix(self, message) -> str:
        """Lấy prefix theo guild"""
        if message.guild:
            guild_config = self.db.get_guild_config(message.guild.id)
            if guild_config:
                return guild_config.prefix
        return config.DEFAULT_PREFIX
    
    async def setup_hook(self):
        """Setup khi bot khởi động"""
        await self.load_extension('cogs.casino_cog')
        await self.load_extension('cogs.admin_cog')
        logger.info("Cogs loaded successfully")

bot = CasinoBot()

@bot.event
async def on_ready():
    """Khi bot sẵn sàng"""
    logger.info(f'{bot.user} đã sẵn sàng!')
    logger.info(f'Kết nối đến {len(bot.guilds)} guilds')
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.playing, name="!help - Casino Bot")
    await bot.change_presence(activity=activity)

@bot.event
async def on_command_error(ctx, error):
    """Xử lý lỗi command"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Thiếu tham số: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Tham số không hợp lệ!")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Bạn không có quyền sử dụng command này!")
    else:
        logger.error(f"Command error: {error}", exc_info=True)
        await ctx.send("❌ Đã xảy ra lỗi khi thực thi command!")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set!")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"Bot run failed: {e}", exc_info=True)