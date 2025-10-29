import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import random
from games.blackjack import BlackjackGame
from games.bau_cua import BauCuaGame, BauCuaAnimal
from games.xoc_dia import XocDiaGame, XocDiaBetType

class BlackjackView(discord.ui.View):
    def __init__(self, game: BlackjackGame, db, bot, user_id: int, guild_id: int):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.game = game
        self.db = db
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
        
        # Cập nhật buttons dựa trên trạng thái game
        self.update_buttons()
    
    def update_buttons(self):
        """Cập nhật buttons dựa trên trạng thái game hiện tại"""
        # Xóa tất cả buttons cũ
        self.clear_items()
        
        state = self.game.get_game_state()
        
        if not state['game_over']:
            # Thêm button Hit
            self.add_item(HitButton())
            
            # Thêm button Stand
            self.add_item(StandButton())
            
            # Thêm button Double nếu có thể
            if state['can_double']:
                self.add_item(DoubleButton())
            
            # Thêm button Split nếu có thể
            if state['can_split']:
                self.add_item(SplitButton())
    
    async def update_message(self, interaction: discord.Interaction):
        """Cập nhật message với trạng thái game mới"""
        state = self.game.get_game_state()
        
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
            from config import config
            if self.user_id not in config.ADMIN_IDS and state['payout'] > 0:
                self.db.update_balance(self.user_id, self.guild_id, state['payout'])
                self.db.add_transaction(
                    self.user_id, self.guild_id, state['payout'], "game",
                    f"Blackjack win: {state['payout']}"
                )
            
            # Xóa game khỏi active
            game_key = f"{self.user_id}_{self.guild_id}"
            if game_key in self.bot.active_games:
                del self.bot.active_games[game_key]
            
            # Disable tất cả buttons khi game kết thúc
            for item in self.children:
                item.disabled = True
                
        else:
            embed.add_field(
                name="Bài của Dealer",
                value=f"{state['dealer_hand'][0]} ? ? (Điểm: {state['dealer_value']}+)",
                inline=False
            )
            
            # Cập nhật buttons cho trạng thái mới
            self.update_buttons()
        
        embed.add_field(name="💰 Cược", value=f"{state['bet']:,}", inline=True)
        
        try:
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            print(f"Error updating message: {e}")

class HitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="🔄 Hit", custom_id="hit")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        view: BlackjackView = self.view
        success = view.game.player_hit()
        
        if success:
            await view.update_message(interaction)
        else:
            await interaction.followup.send("❌ Không thể rút bài!", ephemeral=True)

class StandButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="✋ Stand", custom_id="stand")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        view: BlackjackView = self.view
        view.game.player_stand()
        
        await view.update_message(interaction)

class DoubleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="💰 Double", custom_id="double")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        view: BlackjackView = self.view
        
        # Kiểm tra số dư
        from config import config
        if view.user_id not in config.ADMIN_IDS:
            balance_obj = view.db.get_user_balance(view.user_id, view.guild_id)
            if balance_obj.balance < view.game.bet:
                await interaction.followup.send("❌ Bạn không đủ tiền để double!", ephemeral=True)
                return
            
            # Trừ thêm tiền cược
            view.db.update_balance(view.user_id, view.guild_id, -view.game.bet)
        
        success = view.game.player_double()
        
        if success:
            await view.update_message(interaction)
        else:
            await interaction.followup.send("❌ Không thể double!", ephemeral=True)

class SplitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="➗ Split", custom_id="split")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("❌ Tính năng Split chưa được hỗ trợ!", ephemeral=True)

class SlashCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    def get_user_balance(self, user_id: int, guild_id: int) -> int:
        """Lấy số dư của user"""
        try:
            balance_obj = self.bot.db.get_or_create_user_balance(user_id, guild_id)
            return balance_obj.balance
        except Exception as e:
            print(f"Error getting balance for {user_id}: {e}")
            return 0

    def is_admin(self, user_id: int) -> bool:
        """Kiểm tra có phải admin không"""
        from config import config
        return user_id in config.ADMIN_IDS

    # SLASH COMMANDS - KINH TẾ
    @app_commands.command(name="balance", description="Kiểm tra số dư của bạn hoặc người khác")
    @app_commands.describe(member="Người muốn kiểm tra số dư (để trống để xem của bạn)")
    async def slash_balance(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """Kiểm tra số dư qua slash command"""
        try:
            target = member or interaction.user
            print(f"Checking balance for user: {target.id}, guild: {interaction.guild.id}")
            
            # Đảm bảo user có balance record
            balance_obj = self.db.get_or_create_user_balance(target.id, interaction.guild.id)
            balance = balance_obj.balance
            
            if self.is_admin(target.id):
                balance_text = "♾️ Vô hạn (Admin)"
            else:
                balance_text = f"💰 {balance:,}"
            
            embed = discord.Embed(
                title=f"Số dư của {target.display_name}",
                description=balance_text,
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Balance error: {e}")
            await interaction.response.send_message("❌ Đã xảy ra lỗi khi kiểm tra số dư!", ephemeral=True)

    # SLASH COMMANDS - BLACKJACK (VỚI BUTTONS)
    @app_commands.command(name="blackjack", description="Chơi Blackjack")
    @app_commands.describe(bet="Số tiền cược")
    async def slash_blackjack(self, interaction: discord.Interaction, bet: int):
        """Chơi Blackjack qua slash command với buttons"""
        try:
            if bet <= 0:
                await interaction.response.send_message("❌ Số tiền cược phải lớn hơn 0!", ephemeral=True)
                return

            user_id = interaction.user.id
            guild_id = interaction.guild.id
            
            # Đảm bảo user có balance record
            balance_obj = self.db.get_or_create_user_balance(user_id, guild_id)
            
            # Kiểm tra số dư
            if not self.is_admin(user_id):
                if balance_obj.balance < bet:
                    await interaction.response.send_message("❌ Bạn không đủ tiền để đặt cược!", ephemeral=True)
                    return

            # Tạo game Blackjack mới
            luck_factor = 1.0
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
            
            # Hiển thị game state với buttons
            state = game.get_game_state()
            
            embed = discord.Embed(title="🎰 Blackjack", color=discord.Color.blue())
            embed.add_field(
                name="Bài của bạn",
                value=f"{' '.join(state['player_hand'])} (Điểm: {state['player_value']})",
                inline=False
            )
            embed.add_field(
                name="Bài của Dealer",
                value=f"{state['dealer_hand'][0]} ? ? (Điểm: {state['dealer_value']}+)",
                inline=False
            )
            embed.add_field(name="💰 Cược", value=f"{state['bet']:,}", inline=True)
            
            # Tạo view với buttons
            view = BlackjackView(game, self.db, self.bot, user_id, guild_id)
            
            await interaction.response.send_message(embed=embed, view=view)
            
        except Exception as e:
            print(f"Blackjack error: {e}")
            await interaction.response.send_message("❌ Đã xảy ra lỗi khi bắt đầu game Blackjack!", ephemeral=True)

    # SLASH COMMANDS - BẦU CUA
    @app_commands.command(name="baucua", description="Chơi Bầu Cua")
    @app_commands.describe(
        bet="Tổng số tiền cược",
        animal1="Cửa cược thứ nhất",
        animal2="Cửa cược thứ hai", 
        animal3="Cửa cược thứ ba"
    )
    @app_commands.choices(
        animal1=[
            app_commands.Choice(name="Bầu 🎉", value="bau"),
            app_commands.Choice(name="Cua 🦀", value="cua"),
            app_commands.Choice(name="Tôm 🦐", value="tom"),
            app_commands.Choice(name="Cá 🐟", value="ca"),
            app_commands.Choice(name="Gà 🐓", value="ga"),
            app_commands.Choice(name="Nai 🦌", value="nai")
        ],
        animal2=[
            app_commands.Choice(name="Bầu 🎉", value="bau"),
            app_commands.Choice(name="Cua 🦀", value="cua"), 
            app_commands.Choice(name="Tôm 🦐", value="tom"),
            app_commands.Choice(name="Cá 🐟", value="ca"),
            app_commands.Choice(name="Gà 🐓", value="ga"),
            app_commands.Choice(name="Nai 🦌", value="nai")
        ],
        animal3=[
            app_commands.Choice(name="Bầu 🎉", value="bau"),
            app_commands.Choice(name="Cua 🦀", value="cua"),
            app_commands.Choice(name="Tôm 🦐", value="tom"),
            app_commands.Choice(name="Cá 🐟", value="ca"),
            app_commands.Choice(name="Gà 🐓", value="ga"),
            app_commands.Choice(name="Nai 🦌", value="nai")
        ]
    )
    async def slash_baucua(self, interaction: discord.Interaction, bet: int, 
                          animal1: str, animal2: Optional[str] = None, animal3: Optional[str] = None):
        """Chơi Bầu Cua qua slash command"""
        try:
            animals = [animal1]
            if animal2:
                animals.append(animal2)
            if animal3:
                animals.append(animal3)

            user_id = interaction.user.id
            guild_id = interaction.guild.id

            # Parse cược
            animal_bets = {}
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
                await interaction.response.send_message("❌ Số tiền cược mỗi cửa phải lớn hơn 0!", ephemeral=True)
                return
            
            for animal_str in animals:
                animal = animal_map.get(animal_str)
                if not animal:
                    await interaction.response.send_message(f"❌ Cửa cược '{animal_str}' không hợp lệ!", ephemeral=True)
                    return
                animal_bets[animal] = bet_per_animal

            total_bet = bet_per_animal * len(animals)
            
            # Đảm bảo user có balance record
            balance_obj = self.db.get_or_create_user_balance(user_id, guild_id)
            
            # Kiểm tra số dư
            if not self.is_admin(user_id):
                if balance_obj.balance < total_bet:
                    await interaction.response.send_message("❌ Bạn không đủ tiền để đặt cược!", ephemeral=True)
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
            profit = state['payout'] - state['total_bet']
            result_text += f"Lợi nhuận: {profit:,}"
            
            embed.add_field(name="📊 Kết quả", value=result_text, inline=True)
            
            # Cộng tiền thắng
            if not self.is_admin(user_id) and state['payout'] > 0:
                self.db.update_balance(user_id, guild_id, state['payout'])
                self.db.add_transaction(
                    user_id, guild_id, state['payout'], "game",
                    f"Bau Cua win: {state['payout']}"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Bau cua error: {e}")
            await interaction.response.send_message("❌ Đã xảy ra lỗi khi chơi Bầu Cua!", ephemeral=True)

    # SLASH COMMANDS - XÓC ĐĨA
    @app_commands.command(name="xocdia", description="Chơi Xóc Đĩa")
    @app_commands.describe(
        bet="Số tiền cược", 
        bet_type="Loại cược"
    )
    @app_commands.choices(
        bet_type=[
            app_commands.Choice(name="Chẵn (1:1)", value="chan"),
            app_commands.Choice(name="Lẻ (1:1)", value="le"),
            app_commands.Choice(name="2 Đỏ 2 Trắng (1:2)", value="2do"),
            app_commands.Choice(name="3 Đỏ 1 Trắng (1:4)", value="3do"),
            app_commands.Choice(name="3 Trắng 1 Đỏ (1:4)", value="3trang"), 
            app_commands.Choice(name="4 Đỏ (1:8)", value="4do"),
            app_commands.Choice(name="4 Trắng (1:8)", value="4trang")
        ]
    )
    async def slash_xocdia(self, interaction: discord.Interaction, bet: int, bet_type: str):
        """Chơi Xóc Đĩa qua slash command"""
        try:
            user_id = interaction.user.id
            guild_id = interaction.guild.id
            
            # Parse loại cược
            bet_type_map = {
                "chan": XocDiaBetType.EVEN,
                "le": XocDiaBetType.ODD,
                "2do": XocDiaBetType.TWO_RED,
                "3do": XocDiaBetType.THREE_RED,
                "3trang": XocDiaBetType.THREE_WHITE,
                "4do": XocDiaBetType.FOUR_RED,
                "4trang": XocDiaBetType.FOUR_WHITE
            }
            
            xd_bet_type = bet_type_map.get(bet_type)
            if not xd_bet_type:
                await interaction.response.send_message("❌ Loại cược không hợp lệ!", ephemeral=True)
                return
            
            # Đảm bảo user có balance record
            balance_obj = self.db.get_or_create_user_balance(user_id, guild_id)
            
            # Kiểm tra số dư
            if not self.is_admin(user_id):
                if balance_obj.balance < bet:
                    await interaction.response.send_message("❌ Bạn không đủ tiền để đặt cược!", ephemeral=True)
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
            state = game.get_game_state()
            
            embed = discord.Embed(title="🎪 Xóc Đĩa", color=discord.Color.orange())
            
            # Hiển thị kết quả đồng xu
            coins_display = " ".join(state['coin_results'])
            embed.add_field(name="🎯 Kết quả", value=coins_display, inline=False)
            embed.add_field(name="🔴 Số mặt đỏ", value=state['red_count'], inline=True)
            
            # Hiển thị kết quả
            result_text = f"Cược: {state['total_bet']:,}\n"
            result_text += f"Thưởng: {state['payout']:,}\n"
            profit = state['payout'] - state['total_bet']
            result_text += f"Lợi nhuận: {profit:,}"
            
            embed.add_field(name="📊 Kết quả", value=result_text, inline=True)
            
            # Cộng tiền thắng
            if not self.is_admin(user_id) and state['payout'] > 0:
                self.db.update_balance(user_id, guild_id, state['payout'])
                self.db.add_transaction(
                    user_id, guild_id, state['payout'], "game",
                    f"Xoc Dia win: {state['payout']}"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Xoc dia error: {e}")
            await interaction.response.send_message("❌ Đã xảy ra lỗi khi chơi Xóc Đĩa!", ephemeral=True)

    # SLASH COMMANDS - CHUYỂN TIỀN
    @app_commands.command(name="transfer", description="Chuyển tiền cho người chơi khác")
    @app_commands.describe(
        member="Người nhận tiền",
        amount="Số tiền chuyển"
    )
    async def slash_transfer(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """Chuyển tiền qua slash command"""
        try:
            if amount <= 0:
                await interaction.response.send_message("❌ Số tiền chuyển phải lớn hơn 0!", ephemeral=True)
                return
            
            if member == interaction.user:
                await interaction.response.send_message("❌ Bạn không thể chuyển tiền cho chính mình!", ephemeral=True)
                return
            
            # Đảm bảo cả 2 user đều có balance record
            sender_balance_obj = self.db.get_or_create_user_balance(interaction.user.id, interaction.guild.id)
            receiver_balance_obj = self.db.get_or_create_user_balance(member.id, interaction.guild.id)
            
            # Kiểm tra số dư
            if sender_balance_obj.balance < amount:
                await interaction.response.send_message("❌ Bạn không đủ tiền để chuyển!", ephemeral=True)
                return
            
            # Thực hiện chuyển tiền
            self.db.update_balance(interaction.user.id, interaction.guild.id, -amount)
            self.db.update_balance(member.id, interaction.guild.id, amount)
            
            # Ghi log transaction
            self.db.add_transaction(
                interaction.user.id, interaction.guild.id, -amount, "transfer",
                f"Chuyển tiền cho {member.display_name}"
            )
            self.db.add_transaction(
                member.id, interaction.guild.id, amount, "transfer",
                f"Nhận tiền từ {interaction.user.display_name}"
            )
            
            embed = discord.Embed(
                title="✅ Chuyển tiền thành công",
                description=f"Đã chuyển {amount:,} cho {member.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Transfer error: {e}")
            await interaction.response.send_message("❌ Đã xảy ra lỗi khi chuyển tiền!", ephemeral=True)

    # SLASH COMMANDS - ADMIN
    @app_commands.command(name="addmoney", description="Thêm tiền cho người chơi (Admin only)")
    @app_commands.describe(
        member="Người nhận tiền",
        amount="Số tiền thêm"
    )
    async def slash_addmoney(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """Thêm tiền qua slash command"""
        try:
            if not self.is_admin(interaction.user.id):
                await interaction.response.send_message("❌ Bạn không có quyền sử dụng command này!", ephemeral=True)
                return

            if amount <= 0:
                await interaction.response.send_message("❌ Số tiền phải lớn hơn 0!", ephemeral=True)
                return
            
            # Đảm bảo user có balance record
            self.db.get_or_create_user_balance(member.id, interaction.guild.id)
            
            self.db.update_balance(member.id, interaction.guild.id, amount)
            self.db.add_transaction(
                member.id, interaction.guild.id, amount, "admin",
                f"Admin {interaction.user.display_name} add money"
            )
            
            embed = discord.Embed(
                title="✅ Thêm tiền thành công",
                description=f"Đã thêm {amount:,} cho {member.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Add money error: {e}")
            await interaction.response.send_message("❌ Đã xảy ra lỗi khi thêm tiền!", ephemeral=True)

    @app_commands.command(name="removemoney", description="Xóa tiền của người chơi (Admin only)")
    @app_commands.describe(
        member="Người bị xóa tiền",
        amount="Số tiền xóa"
    )
    async def slash_removemoney(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """Xóa tiền qua slash command"""
        try:
            if not self.is_admin(interaction.user.id):
                await interaction.response.send_message("❌ Bạn không có quyền sử dụng command này!", ephemeral=True)
                return
        
            if amount <= 0:
                await interaction.response.send_message("❌ Số tiền phải lớn hơn 0!", ephemeral=True)
                return
            
            # Đảm bảo user có balance record
            balance_obj = self.db.get_or_create_user_balance(member.id, interaction.guild.id)
            current_balance = balance_obj.balance
            remove_amount = min(amount, current_balance)
            
            self.db.update_balance(member.id, interaction.guild.id, -remove_amount)
            self.db.add_transaction(
                member.id, interaction.guild.id, -remove_amount, "admin",
                f"Admin {interaction.user.display_name} remove money"
            )
            
            embed = discord.Embed(
                title="✅ Xóa tiền thành công",
                description=f"Đã xóa {remove_amount:,} từ {member.mention}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"Remove money error: {e}")
            await interaction.response.send_message("❌ Đã xảy ra lỗi khi xóa tiền!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SlashCommandsCog(bot))