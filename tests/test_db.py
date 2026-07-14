"""db.py 테스트 — 임시 DB 파일로 저장/조회/마이그레이션을 검증한다."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """테스트마다 새 임시 DB 를 쓴다 (실제 learning.db 를 건드리지 않음)."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def test_add_word_with_mode():
    wid = db.add_word("improve", "향상시키다", mode="toeic")
    assert wid > 0
    items = db.get_today_items(mode="toeic")
    assert len(items["words"]) == 1
    assert items["words"][0]["mode"] == "toeic"
    # 다른 모드로는 조회되지 않아야 한다
    assert db.get_today_items(mode="talk")["words"] == []


def test_add_word_default_mode_is_talk():
    db.add_word("hello", "안녕")
    assert db.get_today_items()["words"][0]["mode"] == "talk"


def test_invalid_mode_falls_back_to_talk():
    db.add_word("test", "시험", mode="hacked")
    assert db.get_today_items()["words"][0]["mode"] == "talk"


def test_add_opic_answer():
    oid = db.add_opic_answer(
        topic="자기소개", question="Tell me about yourself.",
        answer="I am a student.", corrected="I am a student.",
        feedback="좋아요", model_answer="Hi, I'm ...", score=85,
    )
    assert oid > 0
    day = db.get_history(limit_days=5)[0]
    assert len(day["opic"]) == 1
    assert day["opic"][0]["score"] == 85


def test_add_toeic_quiz_choices_roundtrip():
    choices = ["quickly", "quick", "quicken", "quickness"]
    db.add_toeic_quiz(
        question="He finished the report ___.", choices=choices,
        my_answer=0, correct_answer=0, explanation="부사 자리", is_correct=True,
    )
    day = db.get_history(limit_days=5)[0]
    assert day["toeic"][0]["choices"] == choices
    assert day["toeic"][0]["is_correct"] == 1


def test_today_mode_summary():
    db.add_word("budget", "예산", mode="toeic")
    db.add_word("hello", "안녕", mode="talk")
    db.add_sentence("I like coffee", "I like coffee.", "좋아요", mode="talk")
    db.add_opic_answer("집", "Describe your home.", "My home is small.")
    summary = db.get_today_mode_summary()
    assert summary["toeic"]["words"] == 1
    assert summary["opic"]["answers"] == 1
    assert summary["talk"]["words"] == 1
    assert summary["talk"]["sentences"] == 1


def test_stats_include_new_tables():
    db.add_opic_answer("취미", "What do you do for fun?", "I play games.")
    stats = db.get_stats()
    assert stats["total_opic"] == 1
    assert stats["total_toeic"] == 0
    assert stats["total_days"] == 1
    assert stats["streak"] == 1


def test_find_word_case_insensitive():
    db.add_word("Improve", "향상시키다")
    found = db.find_word("improve")
    assert found is not None
    assert found["word"] == "Improve"
    assert db.find_word("nonexistent") is None


def test_delete_word():
    wid = db.add_word("typo", "오타")
    assert db.delete_word(wid) is True
    assert db.get_today_items()["words"] == []
    # 없는 id 는 False
    assert db.delete_word(9999) is False


def test_new_word_is_due_today():
    db.add_word("fresh", "신선한")
    due = db.get_due_words()
    assert len(due) == 1
    assert due[0]["word"] == "fresh"


def test_get_distractors_excludes_answer():
    for w, m in [("apple", "사과"), ("banana", "바나나"), ("cherry", "체리"),
                 ("grape", "포도"), ("melon", "멜론")]:
        db.add_word(w, m)
    target = db.get_due_words()[0]
    distractors = db.get_distractors(target["id"], count=3)
    assert len(distractors) == 3
    assert target["word"] not in distractors
    assert len(set(distractors)) == 3


def test_get_distractors_pads_when_few_words():
    db.add_word("alone", "혼자")
    target = db.get_due_words()[0]
    distractors = db.get_distractors(target["id"], count=3)
    # 저장 단어가 부족해도 내장 풀에서 보충해 3개를 채운다
    assert len(distractors) == 3
    assert "alone" not in distractors


def test_get_wrong_toeic_excludes_later_correct():
    db.add_toeic_quiz("Q1 ___.", ["a", "b", "c", "d"], my_answer=1,
                      correct_answer=0, explanation="", is_correct=False)
    db.add_toeic_quiz("Q2 ___.", ["a", "b", "c", "d"], my_answer=0,
                      correct_answer=0, explanation="", is_correct=True)
    wrong = db.get_wrong_toeic()
    assert len(wrong) == 1
    assert wrong[0]["question"] == "Q1 ___."
    assert wrong[0]["choices"] == ["a", "b", "c", "d"]

    # 같은 문제를 나중에 맞히면 오답 목록에서 빠진다
    db.add_toeic_quiz("Q1 ___.", ["a", "b", "c", "d"], my_answer=0,
                      correct_answer=0, explanation="", is_correct=True)
    assert db.get_wrong_toeic() == []


def test_migration_fills_empty_next_review(tmp_path, monkeypatch):
    """SRS 도입 전 데이터(next_review='')는 저장일로 정규화된다."""
    import sqlite3
    old = tmp_path / "srs.db"
    conn = sqlite3.connect(str(old))
    conn.execute(
        "CREATE TABLE words (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,"
        " date TEXT NOT NULL, word TEXT NOT NULL, meaning TEXT NOT NULL,"
        " pronunciation TEXT NOT NULL DEFAULT '', example TEXT NOT NULL DEFAULT '',"
        " example_kr TEXT NOT NULL DEFAULT '')"
    )
    conn.execute(
        "INSERT INTO words (created_at, date, word, meaning) VALUES ('2026-06-20T09:00:00', '2026-06-20', 'legacy', '옛날 단어')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", str(old))
    db.init_db()

    due = db.get_due_words()
    assert len(due) == 1
    assert due[0]["next_review"] == "2026-06-20"


def test_migration_preserves_existing_rows(tmp_path, monkeypatch):
    """mode 컬럼이 없던 옛 DB 에 init_db 를 다시 돌려도 기존 행이 talk 로 유지된다."""
    import sqlite3
    old = tmp_path / "old.db"
    conn = sqlite3.connect(str(old))
    conn.execute(
        "CREATE TABLE words (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,"
        " date TEXT NOT NULL, word TEXT NOT NULL, meaning TEXT NOT NULL,"
        " pronunciation TEXT NOT NULL DEFAULT '', example TEXT NOT NULL DEFAULT '',"
        " example_kr TEXT NOT NULL DEFAULT '')"
    )
    conn.execute(
        "INSERT INTO words (created_at, date, word, meaning) VALUES ('2026-01-01T09:00:00', '2026-01-01', 'legacy', '옛날 단어')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", str(old))
    db.init_db()

    hist = db.get_history()
    assert hist[0]["words"][0]["word"] == "legacy"
    assert hist[0]["words"][0]["mode"] == "talk"
