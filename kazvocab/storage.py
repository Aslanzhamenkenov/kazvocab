"""Loading decks from JSON and keeping the learner's progress on disk."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Card, CardProgress, Deck

DEFAULT_DECK = Path(__file__).resolve().parent.parent / "data" / "basic.json"
DEFAULT_PROGRESS = Path.home() / ".kazvocab" / "progress.json"

__all__ = ["load_deck", "load_progress", "save_progress", "DeckError",
           "DEFAULT_DECK", "DEFAULT_PROGRESS"]


class DeckError(ValueError):
    """Raised when a deck file is missing or malformed."""


def load_deck(path: str | Path | None = None) -> Deck:
    """
    Read a deck from JSON.

    Expected shape::

        {"name": "Basic Kazakh",
         "cards": [{"kk": "су", "ru": "вода", "topic": "food"}, ...]}
    """
    p = Path(path) if path else DEFAULT_DECK
    if not p.is_file():
        raise DeckError(f"deck file not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeckError(f"{p.name} is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict) or "cards" not in raw:
        raise DeckError(f"{p.name} must be an object with a 'cards' list")

    cards: list[Card] = []
    for i, item in enumerate(raw["cards"], start=1):
        try:
            cards.append(Card.from_dict(item))
        except (TypeError, ValueError) as exc:
            raise DeckError(f"card #{i} in {p.name} is invalid: {exc}") from exc

    if not cards:
        raise DeckError(f"{p.name} contains no cards")

    seen: set[str] = set()
    for c in cards:
        if c.key in seen:
            raise DeckError(f"duplicate entry in {p.name}: {c.kk!r}")
        seen.add(c.key)

    return Deck(name=raw.get("name", p.stem), cards=cards)


def load_progress(path: str | Path | None = None) -> dict[str, CardProgress]:
    """Read saved progress. A missing file simply means "nothing learned yet"."""
    p = Path(path) if path else DEFAULT_PROGRESS
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}  # corrupted history must not block studying
    out: dict[str, CardProgress] = {}
    for key, item in (raw or {}).items():
        try:
            out[key] = CardProgress.from_dict({**item, "key": key})
        except (TypeError, ValueError):
            continue
    return out


def save_progress(progress: dict[str, CardProgress],
                  path: str | Path | None = None) -> Path:
    """Write progress atomically so an interrupted run cannot corrupt it."""
    p = Path(path) if path else DEFAULT_PROGRESS
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v.to_dict() for k, v in progress.items()}
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return p
