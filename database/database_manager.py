from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from typing import Optional, List
import json
from .models import Base, GuildConfig, UserBalance, TransactionHistory, ActiveGame
from config import config

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_guild_config(self, guild_id: int) -> Optional[GuildConfig]:
        """Lấy cấu hình của guild"""
        session = self.Session()
        try:
            return session.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
        finally:
            session.close()
    
    def create_guild_config(self, guild_id: int, prefix: str = "!", starting_balance: int = 1000) -> GuildConfig:
        """Tạo cấu hình mới cho guild"""
        session = self.Session()
        try:
            config = GuildConfig(
                guild_id=guild_id,
                prefix=prefix,
                starting_balance=starting_balance
            )
            session.add(config)
            session.commit()
            return config
        finally:
            session.close()
    
    def get_or_create_user_balance(self, user_id: int, guild_id: int) -> UserBalance:
        """Lấy hoặc tạo balance mới cho user"""
        session = self.Session()
        try:
            balance = session.query(UserBalance).filter(
                and_(UserBalance.user_id == user_id, UserBalance.guild_id == guild_id)
            ).first()
            
            if not balance:
                # Lấy starting balance từ guild config
                guild_config = self.get_guild_config(guild_id)
                starting_balance = guild_config.starting_balance if guild_config else config.STARTING_BALANCE
                
                balance = UserBalance(
                    user_id=user_id,
                    guild_id=guild_id,
                    balance=starting_balance
                )
                session.add(balance)
                session.commit()
                print(f"✅ Created balance for user {user_id} in guild {guild_id}: {starting_balance}")
            
            return balance
        except Exception as e:
            session.rollback()
            print(f"❌ Error in get_or_create_user_balance: {e}")
            raise
        finally:
            session.close()
    
    def get_user_balance(self, user_id: int, guild_id: int) -> Optional[UserBalance]:
        """Lấy số dư của user (giữ nguyên cho tương thích)"""
        return self.get_or_create_user_balance(user_id, guild_id)
    
    def create_user_balance(self, user_id: int, guild_id: int, balance: int = None) -> UserBalance:
        """Tạo balance mới cho user"""
        return self.get_or_create_user_balance(user_id, guild_id)
    
    def update_balance(self, user_id: int, guild_id: int, amount: int) -> bool:
        """Cập nhật số dư của user"""
        session = self.Session()
        try:
            balance = self.get_or_create_user_balance(user_id, guild_id)
            balance.balance += amount
            session.commit()
            print(f"✅ Updated balance for user {user_id}: {amount}")
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ Error updating balance: {e}")
            return False
        finally:
            session.close()
    
    def add_transaction(self, user_id: int, guild_id: int, amount: int, transaction_type: str, description: str):
        """Thêm lịch sử giao dịch"""
        session = self.Session()
        try:
            transaction = TransactionHistory(
                user_id=user_id,
                guild_id=guild_id,
                amount=amount,
                transaction_type=transaction_type,
                description=description
            )
            session.add(transaction)
            session.commit()
            print(f"✅ Added transaction for user {user_id}: {description}")
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding transaction: {e}")
        finally:
            session.close()
    
    def save_active_game(self, user_id: int, guild_id: int, game_type: str, game_data: dict) -> int:
        """Lưu game đang active"""
        session = self.Session()
        try:
            # Xóa game cũ nếu có
            session.query(ActiveGame).filter(
                and_(ActiveGame.user_id == user_id, ActiveGame.guild_id == guild_id)
            ).delete()
            
            game = ActiveGame(
                user_id=user_id,
                guild_id=guild_id,
                game_type=game_type,
                game_data=json.dumps(game_data)
            )
            session.add(game)
            session.commit()
            return game.id
        finally:
            session.close()
    
    def get_active_game(self, user_id: int, guild_id: int) -> Optional[dict]:
        """Lấy game đang active"""
        session = self.Session()
        try:
            game = session.query(ActiveGame).filter(
                and_(ActiveGame.user_id == user_id, ActiveGame.guild_id == guild_id)
            ).first()
            return json.loads(game.game_data) if game else None
        finally:
            session.close()
    
    def delete_active_game(self, user_id: int, guild_id: int):
        """Xóa game active"""
        session = self.Session()
        try:
            session.query(ActiveGame).filter(
                and_(ActiveGame.user_id == user_id, ActiveGame.guild_id == guild_id)
            ).delete()
            session.commit()
        finally:
            session.close()