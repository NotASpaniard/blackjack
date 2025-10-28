import discord
from discord.ext import commands
from typing import Optional

from config import config

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
    
    def is_admin(self, user_id: int) -> bool:
        """Kiểm tra có phải admin không"""
        return user_id in config.ADMIN_IDS
    
    @commands.command(name="addmoney")
    async def add_money(self, ctx, member: discord.Member, amount: int):
        """Thêm tiền cho người chơi (Admin only)"""
        if not self.is_admin(ctx.author.id):
            await ctx.send("❌ Bạn không có quyền sử dụng command này!")
            return
        
        try:
            if amount <= 0:
                await ctx.send("❌ Số tiền phải lớn hơn 0!")
                return
            
            self.db.update_balance(member.id, ctx.guild.id, amount)
            self.db.add_transaction(
                member.id, ctx.guild.id, amount, "admin",
                f"Admin {ctx.author.display_name} add money"
            )
            
            embed = discord.Embed(
                title="✅ Thêm tiền thành công",
                description=f"Đã thêm {amount:,} cho {member.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi thêm tiền!")
    
    @commands.command(name="removemoney")
    async def remove_money(self, ctx, member: discord.Member, amount: int):
        """Xóa tiền của người chơi (Admin only)"""
        if not self.is_admin(ctx.author.id):
            await ctx.send("❌ Bạn không có quyền sử dụng command này!")
            return
        
        try:
            if amount <= 0:
                await ctx.send("❌ Số tiền phải lớn hơn 0!")
                return
            
            current_balance = self.db.get_user_balance(member.id, ctx.guild.id).balance
            remove_amount = min(amount, current_balance)
            
            self.db.update_balance(member.id, ctx.guild.id, -remove_amount)
            self.db.add_transaction(
                member.id, ctx.guild.id, -remove_amount, "admin",
                f"Admin {ctx.author.display_name} remove money"
            )
            
            embed = discord.Embed(
                title="✅ Xóa tiền thành công",
                description=f"Đã xóa {remove_amount:,} từ {member.mention}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi xóa tiền!")
    
    @commands.command(name="setbalance")
    async def set_balance(self, ctx, member: discord.Member, amount: int):
        """Set số dư cụ thể cho người chơi (Admin only)"""
        if not self.is_admin(ctx.author.id):
            await ctx.send("❌ Bạn không có quyền sử dụng command này!")
            return
        
        try:
            if amount < 0:
                await ctx.send("❌ Số dư không thể âm!")
                return
            
            current_balance = self.db.get_user_balance(member.id, ctx.guild.id)
            difference = amount - current_balance.balance
            
            self.db.update_balance(member.id, ctx.guild.id, difference)
            self.db.add_transaction(
                member.id, ctx.guild.id, difference, "admin",
                f"Admin {ctx.author.display_name} set balance to {amount}"
            )
            
            embed = discord.Embed(
                title="✅ Set số dư thành công",
                description=f"Đã set số dư của {member.mention} thành {amount:,}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi set số dư!")
    
    @commands.command(name="serverconfig")
    async def server_config(self, ctx):
        """Xem cấu hình server (Admin only)"""
        if not self.is_admin(ctx.author.id):
            await ctx.send("❌ Bạn không có quyền sử dụng command này!")
            return
        
        try:
            guild_config = self.db.get_guild_config(ctx.guild.id)
            if not guild_config:
                await ctx.send("❌ Server chưa được đăng ký! Sử dụng `!register`")
                return
            
            embed = discord.Embed(
                title="⚙️ Cấu hình Server",
                color=discord.Color.purple()
            )
            embed.add_field(name="Prefix", value=guild_config.prefix, inline=True)
            embed.add_field(name="Trạng thái", value="✅ Bật" if guild_config.enabled else "❌ Tắt", inline=True)
            embed.add_field(name="Số tiền khởi đầu", value=f"{guild_config.starting_balance:,}", inline=True)
            embed.add_field(name="Ngày tạo", value=guild_config.created_at.strftime("%Y-%m-%d %H:%M"), inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Đã xảy ra lỗi khi xem cấu hình!")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))