"""Command-line trainer."""

from __future__ import annotations

import argparse
import random
import sys
import unicodedata

from . import __version__
from .models import Card, CardProgress, Deck
from .srs import due_cards, review, summary
from .storage import DeckError, load_deck, load_progress, save_progress

__all__ = ["normalize", "is_correct", "main", "build_parser"]


def normalize(text: str) -> str:
    """
    Compare answers forgivingly but not carelessly.

    Case and surrounding spaces are ignored, and the Cyrillic 'ё' is folded to
    'е' because keyboards disagree about it. Kazakh-specific letters such as
    ә, ғ, қ, ң, ө, ұ, ү, һ, і are preserved: telling them apart is the point
    of the exercise.
    """
    text = unicodedata.normalize("NFC", text)
    return text.strip().lower().replace("ё", "е")


def is_correct(given: str, expected: str) -> bool:
    """
    True when the answer matches.

    Translations with several variants are stored comma-separated
    ("девочка, дочь"); naming any one of them counts as correct.
    """
    got = normalize(given)
    if not got:
        return False
    variants = [normalize(v) for v in expected.split(",")]
    return got in variants or got == normalize(expected)


def _ask(card: Card, direction: str) -> bool:
    question = card.prompt(direction)
    expected = card.answer(direction)
    try:
        given = input(f"  {question}  →  ")
    except (EOFError, KeyboardInterrupt):
        print("\n  прервано")
        raise
    ok = is_correct(given, expected)
    print("  ✓ верно" if ok else f"  ✗ неверно — правильный ответ: {expected}")
    return ok


def run_quiz(deck: Deck, progress: dict[str, CardProgress], limit: int,
             direction: str, topic: str | None) -> dict[str, CardProgress]:
    pool = deck.by_topic(topic) if topic else list(deck)
    if not pool:
        print(f"нет карточек по теме {topic!r}. Доступные: {', '.join(deck.topics)}")
        return progress

    keys = [c.key for c in pool]
    queue = due_cards(progress, keys)[:limit]
    if not queue:
        print("на сегодня всё повторено. Возвращайтесь завтра.")
        return progress

    by_key = {c.key: c for c in pool}
    random.shuffle(queue)

    print(f"\n{len(queue)} карточек · направление {direction}\n")
    right = 0
    asked = 0
    for i, key in enumerate(queue, start=1):
        card = by_key[key]
        print(f"[{i}/{len(queue)}]")
        try:
            ok = _ask(card, direction)
        except (EOFError, KeyboardInterrupt):
            break
        asked += 1
        right += ok
        current = progress.get(key, CardProgress(key=key))
        progress[key] = review(current, ok)
        print()

    print(f"результат: {right} из {asked} правильно")
    return progress


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kazvocab",
        description="Тренажёр казахских слов с интервальным повторением.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Примеры:\n"
               "  kazvocab quiz\n"
               "  kazvocab quiz --topic numbers --limit 10\n"
               "  kazvocab quiz --direction ru->kk\n"
               "  kazvocab status\n"
               "  kazvocab topics\n",
    )
    p.add_argument("command", choices=("quiz", "status", "topics", "reset"),
                   help="что сделать")
    p.add_argument("--deck", default=None, help="путь к файлу колоды (JSON)")
    p.add_argument("--progress", default=None, help="путь к файлу прогресса")
    p.add_argument("--limit", type=int, default=15, help="сколько карточек за подход")
    p.add_argument("--topic", default=None, help="ограничить одной темой")
    p.add_argument("--direction", choices=("kk->ru", "ru->kk"), default="kk->ru",
                   help="направление перевода")
    p.add_argument("--version", action="version", version=f"kazvocab {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        deck = load_deck(args.deck)
    except DeckError as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return 1

    progress = load_progress(args.progress)

    if args.command == "topics":
        print(f"колода «{deck.name}» · {len(deck)} карточек\n")
        for t in deck.topics:
            print(f"  {t:12} {len(deck.by_topic(t)):>3}")
        return 0

    if args.command == "status":
        s = summary(progress, len(deck))
        print(f"колода «{deck.name}»\n")
        print(f"  всего слов     {s['total']}")
        print(f"  начато         {s['started']}")
        print(f"  не тронуто     {s['untouched']}")
        print(f"  выучено        {s['learned']}")
        print(f"  повторений     {s['reviews']}")
        print(f"  точность       {s['accuracy'] * 100:.0f}%")
        return 0

    if args.command == "reset":
        path = save_progress({}, args.progress)
        print(f"прогресс очищен: {path}")
        return 0

    progress = run_quiz(deck, progress, args.limit, args.direction, args.topic)
    path = save_progress(progress, args.progress)
    print(f"прогресс сохранён: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
