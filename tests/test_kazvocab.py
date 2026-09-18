"""Тесты kazvocab. Запуск:  python -m pytest -v"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kazvocab import (  # noqa: E402
    INTERVALS,
    MAX_BOX,
    Card,
    CardProgress,
    Deck,
    DeckError,
    due_cards,
    interval_for,
    load_deck,
    load_progress,
    review,
    save_progress,
    summary,
)
from kazvocab.cli import is_correct, main, normalize  # noqa: E402

TODAY = date(2026, 9, 19)


# --------------------------------------------------------------------------- #
# Card
# --------------------------------------------------------------------------- #

def test_card_key_is_case_insensitive():
    assert Card("Су", "вода").key == "су"


def test_card_rejects_empty_sides():
    with pytest.raises(ValueError):
        Card("", "вода")
    with pytest.raises(ValueError):
        Card("су", "   ")


def test_card_prompt_and_answer_follow_direction():
    c = Card("су", "вода")
    assert c.prompt("kk->ru") == "су" and c.answer("kk->ru") == "вода"
    assert c.prompt("ru->kk") == "вода" and c.answer("ru->kk") == "су"


def test_card_rejects_unknown_direction():
    with pytest.raises(ValueError):
        Card("су", "вода").prompt("kk->en")


# --------------------------------------------------------------------------- #
# Deck
# --------------------------------------------------------------------------- #

def test_deck_groups_by_topic():
    d = Deck("t", [Card("бір", "один", "numbers"),
                   Card("екі", "два", "numbers"),
                   Card("су", "вода", "food")])
    assert d.topics == ["food", "numbers"]
    assert len(d.by_topic("numbers")) == 2
    assert d.by_topic("nope") == []


def test_deck_find_is_case_insensitive():
    d = Deck("t", [Card("су", "вода")])
    assert d.find("СУ").ru == "вода"
    assert d.find("жоқ") is None


# --------------------------------------------------------------------------- #
# Интервальное повторение
# --------------------------------------------------------------------------- #

def test_correct_answer_promotes_one_box():
    p = review(CardProgress("су", box=0), True, TODAY)
    assert p.box == 1
    assert p.seen == 1 and p.correct == 1


def test_wrong_answer_drops_to_box_zero():
    p = review(CardProgress("су", box=4), False, TODAY)
    assert p.box == 0
    assert p.correct == 0 and p.seen == 1


def test_box_never_exceeds_maximum():
    p = CardProgress("су", box=MAX_BOX)
    assert review(p, True, TODAY).box == MAX_BOX


def test_due_date_matches_the_interval_table():
    p = review(CardProgress("су", box=1), True, TODAY)
    expected = TODAY + timedelta(days=INTERVALS[2])
    assert p.due == expected.isoformat()


def test_failed_card_is_due_again_today():
    p = review(CardProgress("су", box=3), False, TODAY)
    assert p.due == TODAY.isoformat()
    assert p.is_due(TODAY)


def test_interval_for_rejects_negative_box():
    with pytest.raises(ValueError):
        interval_for(-1)


def test_review_does_not_mutate_the_original():
    before = CardProgress("су", box=2, seen=5, correct=3)
    review(before, True, TODAY)
    assert before.box == 2 and before.seen == 5


def test_accuracy_is_zero_before_any_review():
    assert CardProgress("су").accuracy == 0.0


def test_accuracy_counts_only_correct_answers():
    assert CardProgress("су", seen=4, correct=3).accuracy == 0.75


# --------------------------------------------------------------------------- #
# Очередь на повторение
# --------------------------------------------------------------------------- #

def test_new_cards_are_always_due():
    assert due_cards({}, ["су", "нан"], TODAY) == ["су", "нан"]


def test_card_scheduled_for_later_is_not_due():
    future = (TODAY + timedelta(days=5)).isoformat()
    pr = {"су": CardProgress("су", box=3, due=future)}
    assert due_cards(pr, ["су"], TODAY) == []


def test_card_due_today_is_included():
    pr = {"су": CardProgress("су", box=1, due=TODAY.isoformat())}
    assert due_cards(pr, ["су"], TODAY) == ["су"]


def test_weakest_cards_come_first():
    pr = {
        "а": CardProgress("а", box=3, due=TODAY.isoformat()),
        "б": CardProgress("б", box=0, due=TODAY.isoformat()),
    }
    assert due_cards(pr, ["а", "б", "в"], TODAY) == ["в", "б", "а"]


# --------------------------------------------------------------------------- #
# Сводка
# --------------------------------------------------------------------------- #

def test_summary_counts_learned_and_untouched():
    pr = {
        "а": CardProgress("а", box=MAX_BOX, seen=6, correct=6),
        "б": CardProgress("б", box=1, seen=4, correct=2),
    }
    s = summary(pr, total=10)
    assert s["total"] == 10
    assert s["started"] == 2
    assert s["untouched"] == 8
    assert s["learned"] == 1
    assert s["reviews"] == 10
    assert s["accuracy"] == 0.8


def test_summary_of_untouched_deck():
    s = summary({}, total=5)
    assert s["started"] == 0 and s["accuracy"] == 0.0


# --------------------------------------------------------------------------- #
# Проверка ответа
# --------------------------------------------------------------------------- #

def test_answer_ignores_case_and_spaces():
    assert is_correct("  ВоДа ", "вода")


def test_any_listed_variant_counts():
    assert is_correct("дочь", "девочка, дочь")
    assert is_correct("девочка", "девочка, дочь")
    assert is_correct("девочка, дочь", "девочка, дочь")


def test_empty_answer_is_wrong():
    assert not is_correct("   ", "вода")


def test_kazakh_letters_are_not_folded_away():
    # ә и а — разные буквы, различать их и есть смысл упражнения
    assert not is_correct("ake", "әке")
    assert not is_correct("аке", "әке")
    assert is_correct("әке", "әке")


def test_yo_is_folded_to_ye():
    assert normalize("ёлка") == "елка"


# --------------------------------------------------------------------------- #
# Колода и хранение
# --------------------------------------------------------------------------- #

def test_bundled_deck_loads_and_has_unique_entries():
    deck = load_deck()
    assert len(deck) >= 50
    keys = [c.key for c in deck]
    assert len(keys) == len(set(keys))
    assert deck.find("су").ru == "вода"


def test_bundled_deck_covers_several_topics():
    assert len(load_deck().topics) >= 5


def test_missing_deck_file_raises(tmp_path):
    with pytest.raises(DeckError, match="not found"):
        load_deck(tmp_path / "nope.json")


def test_malformed_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(DeckError, match="valid JSON"):
        load_deck(p)


def test_deck_without_cards_key_raises(tmp_path):
    p = tmp_path / "d.json"
    p.write_text('{"name": "x"}', encoding="utf-8")
    with pytest.raises(DeckError):
        load_deck(p)


def test_duplicate_card_raises(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"cards": [{"kk": "су", "ru": "вода"},
                                       {"kk": "Су", "ru": "water"}]}),
                 encoding="utf-8")
    with pytest.raises(DeckError, match="duplicate"):
        load_deck(p)


def test_progress_survives_a_save_load_cycle(tmp_path):
    p = tmp_path / "progress.json"
    original = {"су": CardProgress("су", box=2, due="2026-09-25", seen=3, correct=2)}
    save_progress(original, p)
    restored = load_progress(p)
    assert restored["су"].box == 2
    assert restored["су"].due == "2026-09-25"
    assert restored["су"].correct == 2


def test_missing_progress_file_means_empty(tmp_path):
    assert load_progress(tmp_path / "none.json") == {}


def test_corrupted_progress_does_not_block_studying(tmp_path):
    p = tmp_path / "progress.json"
    p.write_text("{{{", encoding="utf-8")
    assert load_progress(p) == {}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def test_cli_topics_lists_the_deck(capsys):
    assert main(["topics"]) == 0
    out = capsys.readouterr().out
    assert "numbers" in out and "food" in out


def test_cli_status_on_a_fresh_profile(tmp_path, capsys):
    assert main(["status", "--progress", str(tmp_path / "p.json")]) == 0
    out = capsys.readouterr().out
    assert "не тронуто" in out


def test_cli_reset_clears_progress(tmp_path, capsys):
    p = tmp_path / "p.json"
    save_progress({"су": CardProgress("су", box=3)}, p)
    assert main(["reset", "--progress", str(p)]) == 0
    assert load_progress(p) == {}


def test_cli_reports_a_missing_deck(tmp_path, capsys):
    assert main(["topics", "--deck", str(tmp_path / "nope.json")]) == 1
    assert "ошибка" in capsys.readouterr().err
