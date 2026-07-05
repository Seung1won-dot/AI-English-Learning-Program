"""app.py API 테스트 — 목업 AI 모드 + 임시 DB 로 신규 API 를 검증한다."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import db
import app as app_module


@pytest.fixture(autouse=True)
def mock_env(tmp_path, monkeypatch):
    """AI 키를 제거해 목업 모드로 강제하고, 임시 DB 를 쓴다."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


# ----- 화면 -----
@pytest.mark.parametrize("path", ["/", "/toeic", "/opic", "/talk", "/history", "/review", "/quiz"])
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_old_chat_redirects_to_talk(client):
    res = client.get("/chat")
    assert res.status_code == 302
    assert "/talk" in res.headers["Location"]


# ----- TOEIC -----
def test_toeic_words(client):
    res = client.post("/api/toeic/words", json={"level": "800"})
    data = res.get_json()
    assert res.status_code == 200
    assert len(data["words"]) == 5
    assert data["words"][0]["word"]


def test_toeic_question_and_answer_flow(client):
    q = client.post("/api/toeic/question", json={}).get_json()
    assert len(q["choices"]) == 4
    assert 0 <= q["answer"] <= 3

    res = client.post("/api/toeic/answer", json={
        "question": q["question"], "choices": q["choices"],
        "my_answer": q["answer"], "correct_answer": q["answer"],
        "explanation": q["explanation"],
    })
    data = res.get_json()
    assert res.status_code == 200
    assert data["is_correct"] is True

    # 날짜별 기록에 저장되었는지
    day = db.get_history(limit_days=5)[0]
    assert day["toeic"][0]["is_correct"] == 1


def test_toeic_answer_rejects_bad_payload(client):
    res = client.post("/api/toeic/answer", json={"question": "x", "choices": ["a"]})
    assert res.status_code == 400


def test_word_saved_with_toeic_mode(client):
    res = client.post("/api/word", json={
        "word": "invoice", "meaning": "송장", "mode": "toeic",
    })
    assert res.status_code == 200
    assert db.get_today_items(mode="toeic")["words"][0]["word"] == "invoice"


# ----- OPIC -----
def test_opic_question(client):
    res = client.post("/api/opic/question", json={"topic": "집"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["question"]
    assert data["topic"] == "집"


def test_opic_answer_flow(client):
    res = client.post("/api/opic/answer", json={
        "topic": "자기소개",
        "question": "Tell me about yourself.",
        "answer": "i am a university student in korea",
    })
    data = res.get_json()
    assert res.status_code == 200
    assert data["corrected"]
    assert 0 <= data["score"] <= 100

    day = db.get_history(limit_days=5)[0]
    assert len(day["opic"]) == 1
    assert day["opic"][0]["topic"] == "자기소개"


def test_opic_answer_requires_question_and_answer(client):
    assert client.post("/api/opic/answer", json={"answer": "hi"}).status_code == 400
    assert client.post("/api/opic/answer", json={"question": "q"}).status_code == 400


# ----- 기존 기능 회귀 -----
def test_sentence_defaults_to_talk_mode(client):
    res = client.post("/api/sentence", json={"sentence": "i like coffee"})
    assert res.status_code == 200
    assert db.get_today_items(mode="talk")["sentences"][0]["mode"] == "talk"
