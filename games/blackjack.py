from .card_game import Deck, Card
from typing import List, Tuple, Dict, Optional
import random

class BlackjackGame:
    def __init__(self, bet_amount: int, user_id: int, luck_factor: float = 1.0):
        self.bet = bet_amount
        self.user_id = user_id
        self.luck_factor = luck_factor  # 1.0 = bình thường, >1.0 = may mắn hơn
        self.deck = Deck(6)  # 6 bộ bài
        self.player_hand: List[Card] = []
        self.dealer_hand: List[Card] = []
        self.game_over = False
        self.result = ""
        self.payout = 0
        
        self.deal_initial_cards()
    
    def deal_initial_cards(self):
        """Chia bài ban đầu"""
        self.player_hand = [self.deck.draw(), self.deck.draw()]
        self.dealer_hand = [self.deck.draw(), self.deck.draw()]
        
        # Áp dụng luck factor
        if random.random() < (self.luck_factor - 1.0) / 10:
            # Cơ hội nhận bài tốt hơn
            while self.calculate_hand_value(self.player_hand)[0] < 17:
                if len(self.player_hand) < 5:
                    self.player_hand.append(self.deck.draw())
                else:
                    break
    
    def calculate_hand_value(self, hand: List[Card]) -> Tuple[int, bool]:
        """Tính giá trị bài và có soft ace không"""
        value = 0
        soft_ace = False
        aces = 0
        
        for card in hand:
            if card.value == CardValue.ACE:
                aces += 1
                value += 11
            else:
                value += card.get_value()
        
        # Xử lý aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
            soft_ace = True
        
        return value, soft_ace
    
    def player_hit(self) -> bool:
        """Người chơi rút thêm bài"""
        if self.game_over:
            return False
        
        self.player_hand.append(self.deck.draw())
        player_value, _ = self.calculate_hand_value(self.player_hand)
        
        if player_value > 21:
            self.game_over = True
            self.result = "BUST"
            self.payout = 0
            return False
        
        return True
    
    def player_stand(self):
        """Người chơi dừng"""
        if self.game_over:
            return
        
        self.dealer_play()
        self.determine_winner()
    
    def player_double(self) -> bool:
        """Người chơi double"""
        if self.game_over or len(self.player_hand) != 2:
            return False
        
        self.bet *= 2
        self.player_hand.append(self.deck.draw())
        
        player_value, _ = self.calculate_hand_value(self.player_hand)
        if player_value > 21:
            self.game_over = True
            self.result = "BUST"
            self.payout = 0
        else:
            self.dealer_play()
            self.determine_winner()
        
        return True
    
    def can_split(self) -> bool:
        """Kiểm tra có thể split không"""
        return (len(self.player_hand) == 2 and 
                self.player_hand[0].value == self.player_hand[1].value)
    
    def player_split(self) -> bool:
        """Người chơi split"""
        if not self.can_split():
            return False
        
        # TODO: Implement split logic (phức tạp hơn, cần xử lý multiple hands)
        return False
    
    def dealer_play(self):
        """Dealer chơi tự động"""
        dealer_value, _ = self.calculate_hand_value(self.dealer_hand)
        
        while dealer_value < 17:
            self.dealer_hand.append(self.deck.draw())
            dealer_value, _ = self.calculate_hand_value(self.dealer_hand)
    
    def determine_winner(self):
        """Xác định người thắng"""
        self.game_over = True
        player_value, _ = self.calculate_hand_value(self.player_hand)
        dealer_value, _ = self.calculate_hand_value(self.dealer_hand)
        
        if player_value > 21:
            self.result = "BUST"
            self.payout = 0
        elif dealer_value > 21:
            self.result = "DEALER_BUST"
            self.payout = self.bet * 2
        elif player_value > dealer_value:
            self.result = "WIN"
            self.payout = self.bet * 2
        elif player_value == dealer_value:
            self.result = "PUSH"
            self.payout = self.bet
        else:
            self.result = "LOSE"
            self.payout = 0
        
        # Áp dụng blackjack
        if (len(self.player_hand) == 2 and player_value == 21 and 
            not (len(self.dealer_hand) == 2 and dealer_value == 21)):
            self.result = "BLACKJACK"
            self.payout = int(self.bet * 2.5)
    
    def get_game_state(self) -> Dict:
        """Lấy trạng thái game"""
        player_value, player_soft = self.calculate_hand_value(self.player_hand)
        dealer_value, dealer_soft = self.calculate_hand_value(self.dealer_hand)
        
        return {
            "player_hand": [str(card) for card in self.player_hand],
            "dealer_hand": [str(card) for card in self.dealer_hand],
            "player_value": player_value,
            "dealer_value": dealer_value if self.game_over else self.dealer_hand[0].get_value(),
            "game_over": self.game_over,
            "result": self.result,
            "bet": self.bet,
            "payout": self.payout,
            "can_double": len(self.player_hand) == 2 and not self.game_over,
            "can_split": self.can_split() and not self.game_over
        }