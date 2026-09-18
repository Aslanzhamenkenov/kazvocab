"""
Как работает интервальное повторение — без интерактива.

Запуск:  python examples/demo.py
"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kazvocab import (  # noqa: E402
    CardProgress,
    due_cards,
    load_deck,
    load_progress,
    review,
    save_progress,
    summary,
)

TODAY = date(2026, 9, 19)


def main() -> None:
    deck = load_deck()
    print(f"колода «{deck.name}» — {len(deck)} карточек")
    print(f"темы: {', '.join(deck.topics)}\n")

    # ---- 1. что показать сегодня -----------------------------------------
    progress: dict[str, CardProgress] = {}
    keys = [c.key for c in deck.by_topic("numbers")]
    print(f"новых слов в теме «numbers»: {len(due_cards(progress, keys, TODAY))}")
    print("новые карточки считаются просроченными всегда\n")

    # ---- 2. верный ответ отодвигает повтор --------------------------------
    print("три верных ответа подряд по слову «бір»:")
    p = CardProgress("бір")
    for step in range(1, 4):
        p = review(p, correct=True, today=TODAY)
        days = (date.fromisoformat(p.due) - TODAY).days
        print(f"  {step}. коробка {p.box} → следующий показ через {days} дн.")

    # ---- 3. ошибка возвращает в начало ------------------------------------
    p = review(p, correct=False, today=TODAY)
    print(f"\nошибка: коробка {p.box}, показать снова {p.due} (сегодня)")
    print(f"статистика слова: {p.correct} из {p.seen}, точность {p.accuracy:.0%}\n")

    # ---- 4. сводка --------------------------------------------------------
    progress = {
        "бір": CardProgress("бір", box=5, seen=6, correct=6),
        "екі": CardProgress("екі", box=2, seen=4, correct=3),
        "үш": CardProgress("үш", box=0, seen=2, correct=0),
    }
    s = summary(progress, total=len(deck))
    print("сводка:")
    for label, value in [("всего слов", s["total"]), ("начато", s["started"]),
                         ("не тронуто", s["untouched"]), ("выучено", s["learned"]),
                         ("повторений", s["reviews"])]:
        print(f"  {label:12} {value}")
    print(f"  {'точность':12} {s['accuracy']:.0%}\n")

    # ---- 5. прогресс переживает перезапуск --------------------------------
    tmp = Path(tempfile.mkdtemp()) / "progress.json"
    save_progress(progress, tmp)
    restored = load_progress(tmp)
    print(f"сохранено и прочитано обратно: {len(restored)} записей, "
          f"коробка «бір» = {restored['бір'].box}")


if __name__ == "__main__":
    main()
