import random
from typing import List, Tuple, Dict
from enum import Enum

class CardSuit(Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

class CardValue(Enum):
    ACE = ("A", 1, 11)
    TWO = ("2", 2, 2)
    THREE = ("3", 3, 3)
    FOUR = ("4", 4, 4)
    FIVE = ("5", 5, 5)
    SIX = ("6", 6, 6)
    SEVEN = ("7", 7, 7)
    EIGHT = ("8", 8, 8)
    NINE = ("9", 9, 9)
    TEN = ("10", 10, 10)
    JACK = ("J", 10, 10)
    QUEEN = ("Q", 10, 10)
    KING = ("K", 10, 10)

class Card:
    def __init__(self, suit: CardSuit, value: CardValue):
        self.suit = suit
        self.value = value
    
    def __str__(self) -> str:
        suit_emojis = {
            CardSuit.HEARTS: "♥",
            CardSuit.DIAMONDS: "♦",
            CardSuit.CLUBS: "♣",
            CardSuit.SPADES: "♠"
        }
        return f"{self.value.value[0]}{suit_emojis[self.suit]}"
    
    def get_value(self) -> int:
        return self.value.value[1]
    
    def get_soft_value(self) -> int:
        return self.value.value[2]

class Deck:
    def __init__(self, num_decks: int = 1):
        self.cards: List[Card] = []
        self.num_decks = num_decks
        self.reset()
    
    def reset(self):
        """Reset bộ bài"""
        self.cards = []
        for _ in range(self.num_decks):
            for suit in CardSuit:
                for value in CardValue:
                    self.cards.append(Card(suit, value))
        self.shuffle()
    
    def shuffle(self):
        """Xáo bài"""
        random.shuffle(self.cards)
    
    def draw(self) -> Card:
        """Rút bài"""
        if not self.cards:
            self.reset()
        return self.cards.pop()