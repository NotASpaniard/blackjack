from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()
import discord
from discord.ext import commands
import os
import logging
from typing import Optional, Dict, Any
import asyncio

from database.database_manager import DatabaseManager
from games.blackjack import BlackjackGame
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
            # Kiểm tra nếu bot ở chế độ restricted và server không được phép
            if config.RESTRICTED_MODE and message.guild.id not in config.ALLOWED_GUILD_IDS:
                return "!"  # Trả về prefix mặc định
            
            guild_config = self.db.get_guild_config(message.guild.id)
            if guild_config:
                return guild_config.prefix
        return config.DEFAULT_PREFIX
    
    async def setup_hook(self):
        """Setup khi bot khởi động"""
        await self.load_extension('cogs.casino_cog')
        await self.load_extension('cogs.admin_cog')
        logger.info("Cogs loaded successfully")
        
        # Kiểm tra cấu hình admin
        if not config.ADMIN_IDS:
            logger.warning("Không có ADMIN_IDS được cấu hình!")
        else:
            logger.info(f"Admin IDs: {config.ADMIN_IDS}")
            
        # Kiểm tra chế độ restricted
        if config.RESTRICTED_MODE:
            if not config.ALLOWED_GUILD_IDS:
                logger.warning("RESTRICTED_MODE được bật nhưng không có ALLOWED_GUILD_IDS!")
            else:
                logger.info(f"Bot restricted to guilds: {config.ALLOWED_GUILD_IDS}")

bot = CasinoBot()

@bot.event
async def on_ready():
    """Khi bot sẵn sàng"""
    logger.info(f'{bot.user} đã sẵn sàng!')
    logger.info(f'Kết nối đến {len(bot.guilds)} guilds')
    
    # Kiểm tra và thông báo server không được phép
    if config.RESTRICTED_MODE:
        for guild in bot.guilds:
            if guild.id not in config.ALLOWED_GUILD_IDS:
                logger.warning(f"Bot đang ở server không được phép: {guild.name} (ID: {guild.id})")
                try:
                    # Gửi thông báo đến server không được phép
                    channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
                    if channel:
                        embed = discord.Embed(
                            title="⚠️ Bot Không Khả Dụng",
                            description="Bot này chỉ được phép hoạt động trên server được chỉ định.",
                            color=discord.Color.red()
                        )
                        await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Không thể gửi thông báo đến server {guild.name}: {e}")
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.playing, name="!help - Casino Bot")
    await bot.change_presence(activity=activity)

@bot.event
async def on_guild_join(guild):
    """Khi bot được thêm vào server mới"""
    if config.RESTRICTED_MODE and guild.id not in config.ALLOWED_GUILD_IDS:
        logger.warning(f"Bot được thêm vào server không được phép: {guild.name} (ID: {guild.id})")
        
        # Thông báo và rời server
        try:
            channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
            if channel:
                embed = discord.Embed(
                    title="❌ Bot Tự Động Rời Đi",
                    description="Bot này chỉ được phép hoạt động trên server được chỉ định bởi developer.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Không thể gửi thông báo rời server: {e}")
        
        # Tự động rời server sau 5 giây
        await asyncio.sleep(5)
        await guild.leave()
        logger.info(f"Đã rời server không được phép: {guild.name}")

@bot.event
async def on_message(message):
    """Xử lý mọi message"""
    # Bỏ qua message từ bot
    if message.author.bot:
        return
    
    # Kiểm tra nếu bot ở chế độ restricted và message từ server không được phép
    if message.guild and config.RESTRICTED_MODE and message.guild.id not in config.ALLOWED_GUILD_IDS:
        # Không xử lý commands từ server không được phép
        return
    
    await bot.process_commands(message)

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
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"❌ Command đang trong thời gian chờ! Thử lại sau {error.retry_after:.1f}s")
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