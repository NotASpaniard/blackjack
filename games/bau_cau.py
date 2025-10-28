import random
from typing import List, Dict, Tuple
from enum import Enum

class BauCuaAnimal(Enum):
    BAU = ("Bầu", "🎉")
    CUA = ("Cua", "🦀")
    TOM = ("Tôm", "🦐")
    CA = ("Cá", "🐟")
    GA = ("Gà", "🐓")
    NAI = ("Nai", "🦌")

class BauCuaGame:
    def __init__(self, bets: Dict[BauCuaAnimal, int], user_id: int, luck_factor: float = 1.0):
        self.bets = bets
        self.user_id = user_id
        self.luck_factor = luck_factor
        self.dice_results: List[BauCuaAnimal] = []
        self.payout = 0
        self.total_bet = sum(bets.values())
        
        self.roll_dice()
        self.calculate_payout()
    
    def roll_dice(self):
        """Xúc xắc"""
        self.dice_results = []
        animals = list(BauCuaAnimal)
        
        for _ in range(3):
            # Áp dụng luck factor
            adjusted_probabilities = self._adjust_probabilities(animals)
            result = random.choices(animals, weights=adjusted_probabilities)[0]
            self.dice_results.append(result)
    
    def _adjust_probabilities(self, animals: List[BauCuaAnimal]) -> List[float]:
        """Điều chỉnh xác suất dựa trên luck factor"""
        base_prob = 1.0 / len(animals)
        probabilities = [base_prob] * len(animals)
        
        # Tăng xác suất cho các cửa đã đặt cược
        for i, animal in enumerate(animals):
            if animal in self.bets and self.bets[animal] > 0:
                probabilities[i] *= self.luck_factor
        
        # Chuẩn hóa probabilities
        total = sum(probabilities)
        return [p / total for p in probabilities]
    
    def calculate_payout(self):
        """Tính toán payout"""
        self.payout = 0
        
        for animal, bet_amount in self.bets.items():
            count = self.dice_results.count(animal)
            if count > 0:
                self.payout += bet_amount * count  # Trả 1:1 cho mỗi lần xuất hiện
    
    def get_game_state(self) -> Dict:
        """Lấy trạng thái game"""
        return {
            "dice_results": [(animal.value[0], animal.value[1]) for animal in self.dice_results],
            "bets": {animal.value[0]: amount for animal, amount in self.bets.items()},
            "total_bet": self.total_bet,
            "payout": self.payout,
            "profit": self.payout - self.total_bet
        }