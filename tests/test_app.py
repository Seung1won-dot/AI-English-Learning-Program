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
@pytest.mark.parametrize("path", ["/", "/vocab", "/toeic", "/opic", "/talk", "/history", "/review", "/quiz"])
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_vocab_word_saved_and_history_renders(client):
    res = client.post("/api/word", json={"word": "memorize", "meaning": "암기하다", "mode": "vocab"})
    assert res.status_code == 200
    assert db.get_today_items(mode="vocab")["words"][0]["mode"] == "vocab"
    # vocab 모드 항목이 있어도 기록 페이지가 렌더링되어야 한다 (모드 라벨 매핑 누락 방지)
    assert client.get("/history").status_code == 200


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


# ----- 단어 관리 (중복 방지 / 삭제) -----
def test_duplicate_word_rejected(client):
    client.post("/api/word", json={"word": "invoice", "meaning": "송장"})
    res = client.post("/api/word", json={"word": "Invoice", "meaning": "송장"})
    assert res.status_code == 409
    data = res.get_json()
    assert data["duplicate"] is True
    # 저장은 1건만
    assert len(db.get_today_items()["words"]) == 1


def test_delete_word_api(client):
    res = client.post("/api/word", json={"word": "typo", "meaning": "오타"})
    wid = res.get_json()["id"]
    assert client.delete(f"/api/word/{wid}").status_code == 200
    assert db.get_today_items()["words"] == []
    assert client.delete(f"/api/word/{wid}").status_code == 404


# ----- 단어장 -----
def test_wordbook_pull_api(client):
    db.import_wordbook([
        {"word": "abandon", "meaning": "포기하다"},
        {"word": "ability", "meaning": "능력"},
    ])
    res = client.post("/api/wordbook/pull", json={"count": 1})
    data = res.get_json()
    assert res.status_code == 200
    assert len(data["pulled"]) == 1
    assert data["pulled"][0]["word"] == "abandon"
    assert data["stats"]["remaining"] == 1
    assert data["due_count"] == 1


# ----- 퀴즈 (객관식 보기) -----
def test_quiz_includes_choices(client):
    client.post("/api/word", json={"word": "apple", "meaning": "사과"})
    data = client.get("/api/quiz").get_json()
    assert len(data["words"]) == 1
    w = data["words"][0]
    assert len(w["choices"]) == 4
    assert w["word"] in w["choices"]
    assert len(set(c.lower() for c in w["choices"])) == 4


# ----- 토익 오답 다시 풀기 -----
def test_toeic_wrong_list(client):
    q = client.post("/api/toeic/question", json={}).get_json()
    wrong_answer = (q["answer"] + 1) % 4
    client.post("/api/toeic/answer", json={
        "question": q["question"], "choices": q["choices"],
        "my_answer": wrong_answer, "correct_answer": q["answer"],
        "explanation": q["explanation"],
    })
    data = client.get("/api/toeic/wrong").get_json()
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question"] == q["question"]

    # 다시 풀어 맞히면 목록에서 빠진다
    client.post("/api/toeic/answer", json={
        "question": q["question"], "choices": q["choices"],
        "my_answer": q["answer"], "correct_answer": q["answer"],
        "explanation": q["explanation"],
    })
    assert client.get("/api/toeic/wrong").get_json()["questions"] == []


# ----- 기존 기능 회귀 -----
def test_sentence_defaults_to_talk_mode(client):
    res = client.post("/api/sentence", json={"sentence": "i like coffee"})
    assert res.status_code == 200
    assert db.get_today_items(mode="talk")["sentences"][0]["mode"] == "talk"


def test_unknown_page_renders_404(client):
    res = client.get("/no-such-page")
    assert res.status_code == 404
    assert "페이지를 찾을 수 없어요".encode() in res.data


def test_unknown_api_returns_json_404(client):
    res = client.get("/api/no-such")
    assert res.status_code == 404
    assert "error" in res.get_json()


def test_home_shows_week_activity(client):
    client.post("/api/word", json={"word": "grit", "meaning": "끈기", "mode": "vocab"})
    html = client.get("/").get_data(as_text=True)
    assert "week-bar" in html and "오늘" in html


def test_password_protection(client, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    assert client.get("/").status_code == 401
    assert client.get("/healthz").status_code == 200
    import base64
    bad = base64.b64encode(b"me:wrong").decode()
    good = base64.b64encode(b"me:s3cret").decode()
    assert client.get("/", headers={"Authorization": f"Basic {bad}"}).status_code == 401
    assert client.get("/", headers={"Authorization": f"Basic {good}"}).status_code == 200


def test_no_password_means_open(client, monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert client.get("/").status_code == 200
