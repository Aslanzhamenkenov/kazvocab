"""
Leitner spaced repetition.

Cards live in numbered boxes. A correct answer promotes a card one box and
pushes its next review further away; a wrong answer sends it back to box 0,
due again today. The intervals are deliberately simple and inspectable —
no opaque scoring, no hidden state.
"""

from __future__ import annotations

from datetime import date, timedelta

from .models import CardProgress

#: Days until the next review, indexed by box number.
INTERVALS: tuple[int, ...] = (0, 1, 3, 7, 16, 35)

MAX_BOX = len(INTERVALS) - 1

__all__ = ["INTERVALS", "MAX_BOX", "interval_for", "review", "due_cards", "summary"]


def interval_for(box: int) -> int:
    """Days to wait before showing a card in ``box`` again."""
    if box < 0:
        raise ValueError("box cannot be negative")
    return INTERVALS[min(box, MAX_BOX)]


def review(progress: CardProgress, correct: bool, today: date | None = None) -> CardProgress:
    """
    Apply one answer and return the updated progress.

    The input object is not mutated, so callers can diff old against new.
    """
    today = today or date.today()
    box = min(progress.box + 1, MAX_BOX) if correct else 0
    due = today + timedelta(days=interval_for(box))
    return CardProgress(
        key=progress.key,
        box=box,
        due=due.isoformat(),
        seen=progress.seen + 1,
        correct=progress.correct + (1 if correct else 0),
    )


def due_cards(progress: dict[str, CardProgress], keys: list[str],
              today: date | None = None) -> list[str]:
    """
    Keys that should be studied now, hardest first.

    A key with no progress yet counts as due: new words are always offered.
    """
    today = today or date.today()
    pending = [k for k in keys
               if k not in progress or progress[k].is_due(today)]
    return sorted(pending, key=lambda k: progress[k].box if k in progress else -1)


def summary(progress: dict[str, CardProgress], total: int) -> dict[str, int | float]:
    """Aggregate counts for the status screen."""
    started = len(progress)
    learned = sum(1 for p in progress.values() if p.box >= MAX_BOX)
    seen = sum(p.seen for p in progress.values())
    correct = sum(p.correct for p in progress.values())
    return {
        "total": total,
        "started": started,
        "untouched": total - started,
        "learned": learned,
        "reviews": seen,
        "accuracy": round(correct / seen, 3) if seen else 0.0,
    }
