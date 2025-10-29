import discord
from discord.ext import commands
import os
import logging
import sys
from typing import Optional, Dict, Any
import asyncio
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

from database.database_manager import DatabaseManager
from games.blackjack import BlackjackGame
from games.bau_cua import BauCuaGame, BauCuaAnimal
from games.xoc_dia import XocDiaGame, XocDiaBetType
from config import config

# Setup logging với UTF-8 encoding
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Encode sang UTF-8 và replace các ký tự lỗi
            msg = msg.encode('utf-8', 'replace').decode('utf-8')
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Configure logging
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Formatter với UTF-8
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (luôn dùng UTF-8)
    file_handler = logging.FileHandler('casino_bot.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Stream handler với Unicode support
    stream_handler = UnicodeStreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    
    # Xóa handlers cũ và thêm handlers mới
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# Gọi setup logging
setup_logging()

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
            if config.RESTRICTED_MODE and message.guild.id not in config.ALLOWED_GUILD_IDS:
                return "!"
            
            guild_config = self.db.get_guild_config(message.guild.id)
            if guild_config:
                return guild_config.prefix
        return config.DEFAULT_PREFIX
    
    async def setup_hook(self):
        """Setup khi bot khởi động"""
        # Xóa commands cũ
        await self.clear_old_commands()
        
        # Load cogs
        await self.load_extension('cogs.casino_cog')
        await self.load_extension('cogs.admin_cog')
        await self.load_extension('cogs.slash_commands')
        
        # Sync slash commands mới
        try:
            synced = await self.tree.sync()
            logger.info("✅ Đa sync %d slash commands moi", len(synced))
        except Exception as e:
            logger.error("❌ Loi sync slash commands: %s", e)
        
        logger.info("Cogs loaded successfully")
    
    async def clear_old_commands(self):
        """Xóa tất cả slash commands cũ"""
        try:
            # Lấy tất cả commands hiện tại
            current_commands = await self.tree.fetch_commands()
            logger.info("📋 Dang xoa %d commands cu...", len(current_commands))
            
            # Xóa từng command
            for cmd in current_commands:
                self.tree.remove_command(cmd.name)
                logger.info("🗑️ Da xoa command: %s", cmd.name)
            
            # Sync để xóa trên Discord
            await self.tree.sync()
            logger.info("✅ Da xoa tat ca commands cu!")
            
        except Exception as e:
            logger.error("❌ Loi khi xoa commands cu: %s", e)

bot = CasinoBot()

@bot.event
async def on_ready():
    """Khi bot sẵn sàng"""
    # Sử dụng ASCII thay vì Unicode để tránh lỗi encoding
    logger.info("%s da san sang!", str(bot.user))
    logger.info("Ket noi den %d guilds", len(bot.guilds))
    
    # Kiểm tra và thông báo server không được phép
    if config.RESTRICTED_MODE:
        for guild in bot.guilds:
            if guild.id not in config.ALLOWED_GUILD_IDS:
                logger.warning("Bot dang o server khong duoc phep: %s (ID: %d)", guild.name, guild.id)
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.playing, name="!help - Casino Bot")
    await bot.change_presence(activity=activity)

@bot.event
async def on_guild_join(guild):
    """Khi bot được thêm vào server mới"""
    if config.RESTRICTED_MODE and guild.id not in config.ALLOWED_GUILD_IDS:
        logger.warning("Bot duoc them vao server khong duoc phep: %s (ID: %d)", guild.name, guild.id)
        
        # Thông báo và rời server
        try:
            channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
            if channel:
                embed = discord.Embed(
                    title="❌ Bot Tu Dong Roi Di",
                    description="Bot nay chi duoc phep hoat dong tren server duoc chi dinh boi developer.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
        except Exception as e:
            logger.error("Khong the gui thong bao roi server: %s", e)
        
        # Tự động rời server sau 5 giây
        await asyncio.sleep(5)
        await guild.leave()
        logger.info("Da roi server khong duoc phep: %s", guild.name)

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
        await ctx.send("❌ Thieu tham so: %s" % error.param.name)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Tham so khong hop le!")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Ban khong co quyen su dung command nay!")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send("❌ Command dang trong thoi gian cho! Thu lai sau %.1fs" % error.retry_after)
    else:
        logger.error("Command error: %s", error, exc_info=True)
        await ctx.send("❌ Da xay ra loi khi thuc thi command!")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set!")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        logger.error("Bot run failed: %s", e, exc_info=True)