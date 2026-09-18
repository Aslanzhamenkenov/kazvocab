"""Core data structures: a vocabulary card and a learner's progress on it."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class Card:
    """One vocabulary item: a Kazakh word and its translation."""

    kk: str  # Kazakh
    ru: str  # Russian
    topic: str = "general"
    example_kk: str = ""
    example_ru: str = ""

    def __post_init__(self) -> None:
        if not self.kk.strip():
            raise ValueError("Kazakh side cannot be empty")
        if not self.ru.strip():
            raise ValueError("Russian side cannot be empty")

    @property
    def key(self) -> str:
        """Stable identifier used to store progress."""
        return self.kk.strip().lower()

    def prompt(self, direction: str = "kk->ru") -> str:
        """The side shown to the learner."""
        if direction == "kk->ru":
            return self.kk
        if direction == "ru->kk":
            return self.ru
        raise ValueError(f"unknown direction: {direction!r}")

    def answer(self, direction: str = "kk->ru") -> str:
        """The side the learner has to produce."""
        return self.ru if direction == "kk->ru" else self.kk

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Card":
        known = {f for f in ("kk", "ru", "topic", "example_kk", "example_ru")}
        return cls(**{k: v for k, v in raw.items() if k in known})


@dataclass
class CardProgress:
    """
    How well one card is known, as a Leitner box plus a due date.

    Box 0 means "new or just failed"; higher boxes are reviewed less often.
    """

    key: str
    box: int = 0
    due: str = ""  # ISO date; empty means "due now"
    seen: int = 0
    correct: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.seen if self.seen else 0.0

    def is_due(self, today: date | None = None) -> bool:
        if not self.due:
            return True
        today = today or date.today()
        return date.fromisoformat(self.due) <= today

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CardProgress":
        return cls(**{k: v for k, v in raw.items()
                      if k in ("key", "box", "due", "seen", "correct")})


@dataclass
class Deck:
    """A named collection of cards."""

    name: str
    cards: list[Card] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    @property
    def topics(self) -> list[str]:
        return sorted({c.topic for c in self.cards})

    def by_topic(self, topic: str) -> list[Card]:
        return [c for c in self.cards if c.topic == topic]

    def find(self, kk: str) -> Card | None:
        needle = kk.strip().lower()
        return next((c for c in self.cards if c.key == needle), None)
