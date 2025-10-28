import random
from typing import List, Dict, Tuple
from enum import Enum

class XocDiaBetType(Enum):
    EVEN = "even"  # Chẵn: 0, 2, 4 mặt đỏ
    ODD = "odd"    # Lẻ: 1, 3 mặt đỏ
    FOUR_RED = "four_red"  # 4 đỏ
    FOUR_WHITE = "four_white"  # 4 trắng
    THREE_RED = "three_red"  # 3 đỏ 1 trắng
    THREE_WHITE = "three_white"  # 3 trắng 1 đỏ
    TWO_RED = "two_red"  # 2 đỏ 2 trắng

class XocDiaGame:
    def __init__(self, bets: Dict[XocDiaBetType, int], user_id: int, luck_factor: float = 1.0):
        self.bets = bets
        self.user_id = user_id
        self.luck_factor = luck_factor
        self.coin_results: List[bool] = []  # True = đỏ, False = trắng
        self.payout = 0
        self.total_bet = sum(bets.values())
        
        self.flip_coins()
        self.calculate_payout()
    
    def flip_coins(self):
        """Lắc đồng xu"""
        self.coin_results = []
        
        for _ in range(4):
            # Áp dụng luck factor
            base_prob = 0.5
            adjusted_prob = min(0.9, base_prob * self.luck_factor)
            result = random.random() < adjusted_prob
            self.coin_results.append(result)
    
    def calculate_payout(self):
        """Tính toán payout"""
        self.payout = 0
        red_count = sum(self.coin_results)
        
        payout_rates = {
            XocDiaBetType.EVEN: (red_count % 2 == 0, 1),
            XocDiaBetType.ODD: (red_count % 2 == 1, 1),
            XocDiaBetType.FOUR_RED: (red_count == 4, 8),
            XocDiaBetType.FOUR_WHITE: (red_count == 0, 8),
            XocDiaBetType.THREE_RED: (red_count == 3, 4),
            XocDiaBetType.THREE_WHITE: (red_count == 1, 4),
            XocDiaBetType.TWO_RED: (red_count == 2, 2)
        }
        
        for bet_type, bet_amount in self.bets.items():
            condition, multiplier = payout_rates[bet_type]
            if condition:
                self.payout += bet_amount * multiplier
    
    def get_game_state(self) -> Dict:
        """Lấy trạng thái game"""
        red_count = sum(self.coin_results)
        return {
            "coin_results": ["🔴" if result else "⚪" for result in self.coin_results],
            "red_count": red_count,
            "bets": {bet_type.value: amount for bet_type, amount in self.bets.items()},
            "total_bet": self.total_bet,
            "payout": self.payout,
            "profit": self.payout - self.total_bet
        }