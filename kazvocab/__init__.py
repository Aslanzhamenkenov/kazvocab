"""
kazvocab — тренажёр казахских слов с интервальным повторением.

    >>> from kazvocab import load_deck
    >>> deck = load_deck()
    >>> len(deck)
    77
    >>> deck.find("су").ru
    'вода'

Карточки распределяются по коробкам Лейтнера: верный ответ повышает коробку и
отодвигает следующий показ, неверный возвращает карточку в начало. Интервалы
заданы явным списком, чтобы поведение можно было проверить, а не угадывать.
"""

__version__ = "0.1.0"

from .models import Card, CardProgress, Deck  # noqa: F401
from .srs import INTERVALS, MAX_BOX, due_cards, interval_for, review, summary  # noqa: F401
from .storage import DeckError, load_deck, load_progress, save_progress  # noqa: F401

__all__ = [
    "Card",
    "CardProgress",
    "Deck",
    "load_deck",
    "load_progress",
    "save_progress",
    "DeckError",
    "review",
    "due_cards",
    "summary",
    "interval_for",
    "INTERVALS",
    "MAX_BOX",
    "__version__",
]
