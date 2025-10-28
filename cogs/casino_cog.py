import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import Optional, Dict, Any
import random

from database.database_manager import DatabaseManager
from games.blackjack import BlackjackGame
from games.bau_cua import BauCuaGame, BauCuaAnimal
from games.xoc_dia import XocDiaGame, XocDiaBetType
from config import config

class CasinoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
    
    def get_user_balance(self, user_id: int, guild_id: int) -> int:
        """Lấy số dư của user"""
        balance_obj = self.db.get_user_balance(user_id, guild_id)
        if not balance_obj:
            balance_obj = self.db.create_user_balance(user_id, guild_id)
        return balance_obj.balance
    
    def is_admin(self, user_id: int) -> bool:
        """Kiểm tra có phải admin không"""
        return user_id in config.ADMIN_IDS
    
    @commands.command(name="register")
    @commands.has_permissions(administrator=True)
    async def register_guild(self, ctx, prefix: str = "!", starting_balance: int = 1000):
        """Đăng ký server với casino bot"""
        try:
            guild_config = self.db.get_guild_config(ctx.guild.id)
            if guild_config:
                await ctx.send("❌ Server này đã được đăng ký!")
                return
            
            self.db.create_guild_config(ctx.guild.id, prefix, starting_balance)
            await ctx.send(f"✅ Đã đăng ký server thành công! Prefix: `{prefix}`, Số tiền khởi đầu: `{starting_balance}`")
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi đăng ký server!")
    
    @commands.command(name="balance", aliases=["bal"])
    async def check_balance(self, ctx, member: discord.Member = None):
        """Kiểm tra số dư"""
        try:
            target = member or ctx.author
            balance = self.get_user_balance(target.id, ctx.guild.id)
            
            if self.is_admin(target.id):
                balance_text = "♾️ Vô hạn (Admin)"
            else:
                balance_text = f"💰 {balance:,}"
            
            embed = discord.Embed(
                title=f"Số dư của {target.display_name}",
                description=balance_text,
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi kiểm tra số dư!")
    
    @commands.command(name="blackjack", aliases=["bj"])
    async def play_blackjack(self, ctx, bet: int):
        """Chơi Blackjack"""
        try:
            user_id = ctx.author.id
            guild_id = ctx.guild.id
            
            # Kiểm tra số dư
            if not self.is_admin(user_id):
                balance = self.get_user_balance(user_id, guild_id)
                if balance < bet:
                    await ctx.send("❌ Bạn không đủ tiền để đặt cược!")
                    return
                
                if bet <= 0:
                    await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
                    return
            
            # Tạo game mới
            luck_factor = 1.0  # Có thể điều chỉnh dựa trên user stats
            game = BlackjackGame(bet, user_id, luck_factor)
            
            # Lưu game active
            game_key = f"{user_id}_{guild_id}"
            self.bot.active_games[game_key] = game
            
            # Trừ tiền cược
            if not self.is_admin(user_id):
                self.db.update_balance(user_id, guild_id, -bet)
                self.db.add_transaction(
                    user_id, guild_id, -bet, "game", 
                    f"Blackjack bet: {bet}"
                )
            
            # Hiển thị game
            await self.display_blackjack_game(ctx, game)
            
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ!")
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi bắt đầu game Blackjack!")
    
    async def display_blackjack_game(self, ctx, game: BlackjackGame):
        """Hiển thị game Blackjack"""
        state = game.get_game_state()
        
        embed = discord.Embed(title="🎰 Blackjack", color=discord.Color.blue())
        embed.add_field(
            name="Bài của bạn",
            value=f"{' '.join(state['player_hand'])} (Điểm: {state['player_value']})",
            inline=False
        )
        
        if state['game_over']:
            embed.add_field(
                name="Bài của Dealer", 
                value=f"{' '.join(state['dealer_hand'])} (Điểm: {state['dealer_value']})",
                inline=False
            )
        else:
            embed.add_field(
                name="Bài của Dealer",
                value=f"{state['dealer_hand'][0]} ? ? (Điểm: {state['dealer_value']}+)",
                inline=False
            )
        
        embed.add_field(name="💰 Cược", value=f"{state['bet']:,}", inline=True)
        
        if state['game_over']:
            result_text = {
                "BUST": "💥 Bạn đã quá 21!",
                "DEALER_BUST": "🎉 Dealer quá 21! Bạn thắng!",
                "WIN": "🎉 Bạn thắng!",
                "LOSE": "😞 Bạn thua!",
                "PUSH": "🤝 Hòa!",
                "BLACKJACK": "🎯 Blackjack! Tuyệt vời!"
            }.get(state['result'], state['result'])
            
            embed.add_field(name="Kết quả", value=result_text, inline=False)
            embed.add_field(name="💰 Thưởng", value=f"{state['payout']:,}", inline=True)
            
            # Cộng tiền thắng
            if not self.is_admin(game.user_id) and state['payout'] > 0:
                self.db.update_balance(game.user_id, ctx.guild.id, state['payout'])
                self.db.add_transaction(
                    game.user_id, ctx.guild.id, state['payout'], "game",
                    f"Blackjack win: {state['payout']}"
                )
            
            # Xóa game khỏi active
            game_key = f"{game.user_id}_{ctx.guild.id}"
            self.bot.active_games.pop(game_key, None)
            
        else:
            # Hiển thị nút điều khiển
            controls = ["🔄 !hit", "✋ !stand", "💰 !double"] 
            if state['can_double']:
                controls.append("💰 !double")
            if state['can_split']:
                controls.append("➗ !split")
                
            embed.add_field(
                name="Điều khiển", 
                value=" | ".join(controls),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="hit")
    async def blackjack_hit(self, ctx):
        """Rút thêm bài trong Blackjack"""
        await self.handle_blackjack_action(ctx, "hit")
    
    @commands.command(name="stand")
    async def blackjack_stand(self, ctx):
        """Dừng lại trong Blackjack"""
        await self.handle_blackjack_action(ctx, "stand")
    
    @commands.command(name="double")
    async def blackjack_double(self, ctx):
        """Double trong Blackjack"""
        await self.handle_blackjack_action(ctx, "double")
    
    async def handle_blackjack_action(self, ctx, action: str):
        """Xử lý action Blackjack"""
        try:
            game_key = f"{ctx.author.id}_{ctx.guild.id}"
            game = self.bot.active_games.get(game_key)
            
            if not game or not isinstance(game, BlackjackGame):
                await ctx.send("❌ Bạn không có game Blackjack đang active!")
                return
            
            # Xử lý action
            if action == "hit":
                success = game.player_hit()
            elif action == "stand":
                game.player_stand()
                success = True
            elif action == "double":
                if not self.is_admin(ctx.author.id):
                    balance = self.get_user_balance(ctx.author.id, ctx.guild.id)
                    if balance < game.bet:
                        await ctx.send("❌ Bạn không đủ tiền để double!")
                        return
                    self.db.update_balance(ctx.author.id, ctx.guild.id, -game.bet)
                
                success = game.player_double()
            else:
                success = False
            
            if success:
                await self.display_blackjack_game(ctx, game)
            else:
                await ctx.send("❌ Action không hợp lệ!")
                
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi xử lý action!")
    
    @commands.command(name="baucua", aliases=["bc"])
    async def play_bau_cua(self, ctx, bet: int, *animals: str):
        """Chơi Bầu Cua - !baucua <tổng cược> <cửa1> <cửa2> ..."""
        try:
            user_id = ctx.author.id
            guild_id = ctx.guild.id
            
            if not animals:
                await ctx.send("❌ Vui lòng chọn ít nhất một cửa cược! (bau, cua, tom, ca, ga, nai)")
                return
            
            # Parse cược
            animal_bets: Dict[BauCuaAnimal, int] = {}
            total_bet = 