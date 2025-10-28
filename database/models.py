from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class GuildConfig(Base):
    __tablename__ = 'guild_configs'
    
    guild_id = Column(BigInteger, primary_key=True)
    prefix = Column(String(5), default='!')
    enabled = Column(Boolean, default=True)
    casino_channel = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    starting_balance = Column(Integer, default=1000)

class UserBalance(Base):
    __tablename__ = 'user_balances'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    balance = Column(Integer, default=1000)
    last_daily = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TransactionHistory(Base):
    __tablename__ = 'transaction_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # 'game', 'transfer', 'admin'
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ActiveGame(Base):
    __tablename__ = 'active_games'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    game_type = Column(String(50), nullable=False)  # 'blackjack', 'bau_cua', 'xoc_dia'
    game_data = Column(Text, nullable=False)  # JSON data
    created_at = Column(DateTime, default=datetime.datetime.utcnow)