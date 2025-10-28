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
            total_bet = 0
            
            animal_map = {
                "bau": BauCuaAnimal.BAU,
                "cua": BauCuaAnimal.CUA,
                "tom": BauCuaAnimal.TOM,
                "ca": BauCuaAnimal.CA,
                "ga": BauCuaAnimal.GA,
                "nai": BauCuaAnimal.NAI
            }
            
            bet_per_animal = bet // len(animals)
            if bet_per_animal <= 0:
                await ctx.send("❌ Số tiền cược mỗi cửa phải lớn hơn 0!")
                return
            
            for animal_str in animals:
                animal = animal_map.get(animal_str.lower())
                if not animal:
                    await ctx.send(f"❌ Cửa cược '{animal_str}' không hợp lệ!")
                    return
                animal_bets[animal] = bet_per_animal
                total_bet += bet_per_animal
            
            # Kiểm tra số dư
            if not self.is_admin(user_id):
                balance = self.get_user_balance(user_id, guild_id)
                if balance < total_bet:
                    await ctx.send("❌ Bạn không đủ tiền để đặt cược!")
                    return
            
            # Tạo game
            luck_factor = 1.0
            game = BauCuaGame(animal_bets, user_id, luck_factor)
            
            # Trừ tiền cược
            if not self.is_admin(user_id):
                self.db.update_balance(user_id, guild_id, -total_bet)
                self.db.add_transaction(
                    user_id, guild_id, -total_bet, "game",
                    f"Bau Cua bet: {total_bet}"
                )
            
            # Hiển thị kết quả
            await self.display_bau_cua_result(ctx, game)
            
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi chơi Bầu Cua!")
    
    async def display_bau_cua_result(self, ctx, game: BauCuaGame):
        """Hiển thị kết quả Bầu Cua"""
        state = game.get_game_state()
        
        embed = discord.Embed(title="🎲 Bầu Cua", color=discord.Color.green())
        
        # Hiển thị kết quả xúc xắc
        dice_display = " ".join([emoji for _, emoji in state['dice_results']])
        embed.add_field(name="🎯 Kết quả", value=dice_display, inline=False)
        
        # Hiển thị cược
        bets_text = "\n".join([f"{animal}: {amount:,}" for animal, amount in state['bets'].items()])
        embed.add_field(name="💰 Cược của bạn", value=bets_text, inline=True)
        
        # Hiển thị kết quả chi tiết
        result_text = f"Tổng cược: {state['total_bet']:,}\n"
        result_text += f"Thưởng: {state['payout']:,}\n"
        result_text += f"Lợi nhuận: {state['profit']:,}"
        
        embed.add_field(name="📊 Kết quả", value=result_text, inline=True)
        
        # Cộng tiền thắng
        if not self.is_admin(game.user_id) and state['payout'] > 0:
            self.db.update_balance(game.user_id, ctx.guild.id, state['payout'])
            self.db.add_transaction(
                game.user_id, ctx.guild.id, state['payout'], "game",
                f"Bau Cua win: {state['payout']}"
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="xocdia", aliases=["xd"])
    async def play_xoc_dia(self, ctx, bet: int, bet_type: str):
        """Chơi Xóc Đĩa - !xocdia <cược> <loại cược>"""
        try:
            user_id = ctx.author.id
            guild_id = ctx.guild.id
            
            # Parse loại cược
            bet_type_map = {
                "chan": XocDiaBetType.EVEN,
                "le": XocDiaBetType.ODD,
                "4do": XocDiaBetType.FOUR_RED,
                "4trang": XocDiaBetType.FOUR_WHITE,
                "3do": XocDiaBetType.THREE_RED,
                "3trang": XocDiaBetType.THREE_WHITE,
                "2do": XocDiaBetType.TWO_RED
            }
            
            xd_bet_type = bet_type_map.get(bet_type.lower())
            if not xd_bet_type:
                await ctx.send("❌ Loại cược không hợp lệ! Các loại: chan, le, 4do, 4trang, 3do, 3trang, 2do")
                return
            
            # Kiểm tra số dư
            if not self.is_admin(user_id):
                balance = self.get_user_balance(user_id, guild_id)
                if balance < bet:
                    await ctx.send("❌ Bạn không đủ tiền để đặt cược!")
                    return
            
            # Tạo game
            bets = {xd_bet_type: bet}
            luck_factor = 1.0
            game = XocDiaGame(bets, user_id, luck_factor)
            
            # Trừ tiền cược
            if not self.is_admin(user_id):
                self.db.update_balance(user_id, guild_id, -bet)
                self.db.add_transaction(
                    user_id, guild_id, -bet, "game",
                    f"Xoc Dia bet: {bet} ({bet_type})"
                )
            
            # Hiển thị kết quả
            await self.display_xoc_dia_result(ctx, game)
            
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi chơi Xóc Đĩa!")
    
    async def display_xoc_dia_result(self, ctx, game: XocDiaGame):
        """Hiển thị kết quả Xóc Đĩa"""
        state = game.get_game_state()
        
        embed = discord.Embed(title="🎪 Xóc Đĩa", color=discord.Color.orange())
        
        # Hiển thị kết quả đồng xu
        coins_display = " ".join(state['coin_results'])
        embed.add_field(name="🎯 Kết quả", value=coins_display, inline=False)
        embed.add_field(name="🔴 Số mặt đỏ", value=state['red_count'], inline=True)
        
        # Hiển thị kết quả
        result_text = f"Cược: {state['total_bet']:,}\n"
        result_text += f"Thưởng: {state['payout']:,}\n"
        result_text += f"Lợi nhuận: {state['profit']:,}"
        
        embed.add_field(name="📊 Kết quả", value=result_text, inline=True)
        
        # Cộng tiền thắng
        if not self.is_admin(game.user_id) and state['payout'] > 0:
            self.db.update_balance(game.user_id, ctx.guild.id, state['payout'])
            self.db.add_transaction(
                game.user_id, ctx.guild.id, state['payout'], "game",
                f"Xoc Dia win: {state['payout']}"
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="transfer")
    async def transfer_money(self, ctx, member: discord.Member, amount: int):
        """Chuyển tiền cho người chơi khác"""
        try:
            if amount <= 0:
                await ctx.send("❌ Số tiền chuyển phải lớn hơn 0!")
                return
            
            if member == ctx.author:
                await ctx.send("❌ Bạn không thể chuyển tiền cho chính mình!")
                return
            
            # Kiểm tra số dư
            sender_balance = self.get_user_balance(ctx.author.id, ctx.guild.id)
            if sender_balance < amount:
                await ctx.send("❌ Bạn không đủ tiền để chuyển!")
                return
            
            # Thực hiện chuyển tiền
            self.db.update_balance(ctx.author.id, ctx.guild.id, -amount)
            self.db.update_balance(member.id, ctx.guild.id, amount)
            
            # Ghi log transaction
            self.db.add_transaction(
                ctx.author.id, ctx.guild.id, -amount, "transfer",
                f"Chuyển tiền cho {member.display_name}"
            )
            self.db.add_transaction(
                member.id, ctx.guild.id, amount, "transfer",
                f"Nhận tiền từ {ctx.author.display_name}"
            )
            
            embed = discord.Embed(
                title="✅ Chuyển tiền thành công",
                description=f"Đã chuyển {amount:,} cho {member.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi chuyển tiền!")

async def setup(bot):
    await bot.add_cog(CasinoCog(bot))