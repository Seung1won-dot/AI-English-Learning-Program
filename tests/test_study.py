"""계정 · 사용자별 데이터 분리 · 콘텐츠 · 학습 흐름(SRS, 오늘 할 일, 모의고사) 테스트."""

import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import app as app_module
import content
import db
from scripts import validate_content

HASH = app_module.hash_password("password123")


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("INVITE_CODE", raising=False)
    monkeypatch.delenv("OWNER_USERNAME", raising=False)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
    app_module._LOGIN_FAILS.clear()
    db.init_db()
    app_module.app.config["TESTING"] = True


def anon():
    return app_module.app.test_client()


def as_user(name="amy"):
    c = anon()
    uid = db.create_user(name, HASH)
    with c.session_transaction() as s:
        s["uid"] = uid
    return c, uid


def csrf(client, path):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


# ----- 계정 -----
def test_pages_require_login():
    c = anon()
    res = c.get("/toeic")
    assert res.status_code == 302 and "/login" in res.headers["Location"]
    assert c.get("/api/quiz").status_code == 401
    assert c.get("/healthz").status_code == 200
    assert c.get("/login").status_code == 200


def test_signup_login_logout_flow():
    c = anon()
    token = csrf(c, "/signup")
    res = c.post("/signup", data={"csrf": token, "username": "minji", "password": "goodpass1",
                                  "password2": "goodpass1"})
    assert res.status_code == 302
    assert c.get("/").status_code == 200
    assert "minji" in c.get("/").get_data(as_text=True)

    c.post("/logout", data={"csrf": csrf(c, "/account")})
    assert c.get("/").status_code == 302

    token = csrf(c, "/login")
    bad = c.post("/login", data={"csrf": token, "username": "minji", "password": "nope-nope"})
    assert bad.status_code == 400
    ok = c.post("/login", data={"csrf": token, "username": "MINJI", "password": "goodpass1", "next": "/toeic"})
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/toeic")


def test_login_next_cannot_leave_site():
    db.create_user("amy", HASH)
    c = anon()
    token = csrf(c, "/login")
    res = c.post("/login", data={"csrf": token, "username": "amy", "password": "password123",
                                 "next": "https://evil.example/"})
    assert res.headers["Location"].endswith("/")
    assert "evil" not in res.headers["Location"]


def test_signup_validation():
    c = anon()
    token = csrf(c, "/signup")
    short = c.post("/signup", data={"csrf": token, "username": "a", "password": "goodpass1", "password2": "goodpass1"})
    assert short.status_code == 400
    weak = c.post("/signup", data={"csrf": token, "username": "amy", "password": "short", "password2": "short"})
    assert weak.status_code == 400
    mismatch = c.post("/signup", data={"csrf": token, "username": "amy", "password": "goodpass1", "password2": "goodpass2"})
    assert mismatch.status_code == 400
    db.create_user("taken", HASH)
    dup = c.post("/signup", data={"csrf": token, "username": "TAKEN", "password": "goodpass1", "password2": "goodpass1"})
    assert dup.status_code == 400
    assert db.count_users() == 1


def test_signup_requires_invite_code(monkeypatch):
    monkeypatch.setenv("INVITE_CODE", "study-2026")
    c = anon()
    token = csrf(c, "/signup")
    form = {"csrf": token, "username": "amy", "password": "goodpass1", "password2": "goodpass1"}
    assert c.post("/signup", data={**form, "invite": "wrong"}).status_code == 400
    assert c.post("/signup", data={**form, "invite": "study-2026"}).status_code == 302


def test_form_post_without_csrf_is_rejected():
    c = anon()
    assert c.post("/login", data={"username": "x", "password": "y"}).status_code == 400


def test_api_post_must_be_json():
    c, _ = as_user()
    assert c.post("/api/vocab/daily", data="x", content_type="text/plain").status_code == 415


def test_login_rate_limit():
    db.create_user("amy", HASH)
    c = anon()
    token = csrf(c, "/login")
    for _ in range(app_module.LOGIN_MAX_FAILS):
        c.post("/login", data={"csrf": token, "username": "amy", "password": "wrong-pass"})
    res = c.post("/login", data={"csrf": token, "username": "amy", "password": "password123"})
    assert res.status_code == 400
    assert "너무 많아요" in res.get_data(as_text=True)


def test_account_goals_and_password():
    c, uid = as_user()
    token = csrf(c, "/account")
    res = c.post("/account", data={"csrf": token, "action": "goals", "goal_words": "5", "goal_p5": "20",
                                   "goal_opic": "2", "target_level": "900"})
    assert res.status_code == 302
    u = db.get_user(uid)
    assert (u["goal_words"], u["goal_p5"], u["goal_opic"], u["target_level"]) == (5, 20, 2, "900")
    bad = c.post("/account", data={"csrf": token, "action": "goals", "goal_words": "999", "goal_p5": "1",
                                   "goal_opic": "1", "target_level": "800"})
    assert bad.status_code == 400
    wrong = c.post("/account", data={"csrf": token, "action": "password", "current": "nope",
                                     "new": "newpass99", "new2": "newpass99"})
    assert wrong.status_code == 400
    ok = c.post("/account", data={"csrf": token, "action": "password", "current": "password123",
                                  "new": "newpass99", "new2": "newpass99"})
    assert ok.status_code == 302
    assert app_module.check_password_hash(db.get_user(uid)["password_hash"], "newpass99")


# ----- 사용자별 데이터 분리 -----
def test_users_do_not_see_each_others_data():
    a, _ = as_user("amy")
    b, _ = as_user("ben")
    wid = a.post("/api/word", json={"word": "invoice", "meaning": "송장"}).get_json()["id"]
    a.post("/api/sentence", json={"sentence": "i like coffee"})

    assert len(a.get("/api/quiz").get_json()["words"]) == 1
    assert b.get("/api/quiz").get_json()["words"] == []
    assert b.get("/api/review?kind=sentences").get_json()["cards"] == []
    assert b.delete(f"/api/word/{wid}").status_code == 404
    assert b.post("/api/quiz/answer", json={"id": wid, "correct": True}).status_code == 404
    # 같은 단어를 다른 사람은 따로 저장할 수 있다
    assert b.post("/api/word", json={"word": "invoice", "meaning": "송장"}).status_code == 200
    assert db.get_stats(uid=2)["total_sentences"] == 0


def test_legacy_rows_go_to_first_account(tmp_path, monkeypatch):
    """계정 도입 전 DB 의 기록은 첫 계정이 이어받는다."""
    old = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(old))
    conn.execute("CREATE TABLE words (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,"
                 " date TEXT NOT NULL, word TEXT NOT NULL, meaning TEXT NOT NULL,"
                 " pronunciation TEXT NOT NULL DEFAULT '', example TEXT NOT NULL DEFAULT '',"
                 " example_kr TEXT NOT NULL DEFAULT '', box INTEGER NOT NULL DEFAULT 1,"
                 " next_review TEXT NOT NULL DEFAULT '')")
    conn.execute("INSERT INTO words (created_at, date, word, meaning, box, next_review)"
                 " VALUES ('2026-01-01T09:00:00', '2026-01-01', 'legacy', '옛날', 3, '2026-01-08')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", str(old))
    db.init_db()
    db.init_db()  # 두 번 돌려도 안전

    assert db.has_legacy_data()
    first = db.create_user("owner", HASH)
    second = db.create_user("friend", HASH)
    assert first == 1
    assert db.get_stats(uid=first)["total_words"] == 1
    assert db.get_stats(uid=second)["total_words"] == 0
    # Leitner 박스 3 → SM-2 간격 7일로 옮겨졌다
    w = db.get_due_words(uid=first)[0]
    assert w["interval"] == 7 and w["reps"] == 2


def test_owner_username_reserves_legacy_data():
    db.add_word("legacy", "옛날", uid=1)
    friend = db.create_user("friend", HASH, owner_username="seungwon")
    owner = db.create_user("seungwon", HASH, owner_username="seungwon")
    assert friend == 2 and owner == 1
    assert db.get_stats(uid=owner)["total_words"] == 1


# ----- 콘텐츠 -----
def test_content_files_are_valid():
    report = validate_content.validate_all()
    for name, (errors, _warnings, size) in report.items():
        assert errors == [], f"{name}: {errors[:3]}"
        assert size > 0
    assert len(content.vocab()) >= 300
    assert len(content.part5()) >= 150
    assert {q["category"] for q in content.part5()} == set(content.P5_CATEGORIES)
    assert sum(len(t["questions"]) for t in content.opic_topics()) >= 60


def test_validator_catches_bad_questions():
    bad = {"questions": [{"id": "x", "question": "No blank here.", "choices": ["a", "a", "b"], "answer": 5,
                          "category": "품사", "level": "easy", "explanation": "짧음"}]}
    errors, _ = validate_content.validate_part5(bad)
    joined = " ".join(errors)
    assert "빈칸" in joined and "보기는 4개" in joined and "answer" in joined


# ----- 학습 흐름 -----
def test_sm2_intervals_grow_and_reset():
    ease, interval, reps = 2.5, 0, 0
    seen = []
    for _ in range(4):
        ease, interval, reps = db.sm2(ease, interval, reps, 4)
        seen.append(interval)
    assert seen[:2] == [1, 3] and seen[2] > 3 and seen[3] > seen[2]
    ease2, interval2, reps2 = db.sm2(ease, interval, reps, 0)
    assert interval2 == 0 and reps2 == 0 and ease2 < ease


def test_daily_vocab_adds_unseen_bank_words():
    c, uid = as_user()
    data = c.post("/api/vocab/daily", json={"level": "600", "count": 5}).get_json()
    assert len(data["added"]) == 5
    assert data["progress"]["learned"] == 5
    again = c.post("/api/vocab/daily", json={"level": "600", "count": 5}).get_json()
    assert not {w["word"] for w in data["added"]} & {w["word"] for w in again["added"]}
    rec = c.post("/api/toeic/words", json={"level": "600"}).get_json()
    mine = {w["word"] for w in data["added"] + again["added"]}
    assert rec["words"] and not mine & {w["word"] for w in rec["words"]}
    assert c.post("/api/vocab/daily", json={"count": 0}).status_code == 400
    # 은행 단어는 품사도 저장되고, 퀴즈 보기도 4개
    quiz = c.get("/api/quiz").get_json()["words"]
    assert quiz[0]["pos"] and len(set(x.lower() for x in quiz[0]["choices"])) == 4


def test_part5_filter_and_wrong_answer_goes_to_review():
    c, uid = as_user()
    q = c.post("/api/toeic/question", json={"category": "전치사", "level": "easy"}).get_json()
    assert q["category"] == "전치사" and q["level"] == "easy" and q["id"]
    assert c.post("/api/toeic/question", json={"category": "없는유형"}).status_code == 400

    wrong = (q["answer"] + 1) % 4
    # 클라이언트가 정답을 속여 보내도 은행 문제는 서버 정답으로 채점한다
    res = c.post("/api/toeic/answer", json={"id": q["id"], "my_answer": wrong, "correct_answer": wrong}).get_json()
    assert res["is_correct"] is False and res["due_p5"] == 1

    due = c.get("/api/toeic/review").get_json()["questions"]
    assert [d["id"] for d in due] == [q["id"]]
    res = c.post("/api/toeic/answer", json={"id": q["id"], "my_answer": q["answer"], "source": "review"}).get_json()
    assert res["is_correct"] is True and res["due_p5"] == 0

    weak = db.get_weakness(uid=uid)
    prep = next(x for x in weak["categories"] if x["category"] == "전치사")
    assert prep["total"] == 2 and prep["correct"] == 1 and prep["rate"] == 50


def test_part5_prefers_unsolved_questions():
    c, _ = as_user()
    seen = set()
    for _ in range(5):
        q = c.post("/api/toeic/question", json={"category": "비교"}).get_json()
        assert q["id"] not in seen
        seen.add(q["id"])
        c.post("/api/toeic/answer", json={"id": q["id"], "my_answer": q["answer"]})


def test_mock_test_hides_answers_and_grades():
    c, uid = as_user()
    data = c.get("/api/toeic/test?count=10").get_json()
    qs = data["questions"]
    assert len(qs) == 10 and data["limit_sec"] == 10 * app_module.TEST_SECONDS_PER_Q
    assert all("answer" not in q and "explanation" not in q for q in qs)
    assert len({q["category"] for q in qs}) == 10  # 유형이 고르게 섞인다

    bank = content.part5_by_id()
    answers = [{"id": q["id"], "choice": bank[q["id"]]["answer"]} for q in qs[:7]]
    answers += [{"id": q["id"], "choice": None} for q in qs[7:]]
    res = c.post("/api/toeic/test", json={"answers": answers, "seconds": 123}).get_json()
    assert res["total"] == 10 and res["correct"] == 7
    assert all("explanation" in r for r in res["results"])
    assert db.count_due_p5(uid=uid) == 3          # 안 푼 문제는 오답 복습으로
    assert db.get_mock_tests(uid=uid)[0]["correct"] == 7
    assert c.get("/api/toeic/test?count=7").status_code == 400
    assert c.post("/api/toeic/test", json={"answers": [{"id": "nope", "choice": 0}]}).status_code == 400
    assert c.get("/toeic/test").status_code == 200


def test_opic_bank_question_has_guide_and_sample_answer():
    c, uid = as_user()
    q = c.post("/api/opic/question", json={"topic": "집"}).get_json()
    assert q["id"].startswith("home-") and q["template"] and q["expressions"] and q["tip"]
    q2 = c.post("/api/opic/question", json={"topic": "집", "recent": [q["id"]]}).get_json()
    assert q2["id"] != q["id"]
    t = content.opic_topic("집")
    res = c.post("/api/opic/answer", json={"topic": "집", "question": t["questions"][0]["q"],
                                           "answer": "I live in an apartment with my family."}).get_json()
    assert res["model_answer"] == t["sample"]
    assert res["word_count"] == 8


def test_today_plan_tracks_progress_and_streak():
    c, uid = as_user()
    plan = db.get_today_plan(uid=uid)
    assert plan["percent"] == 0 and not plan["complete"]
    c.post("/api/vocab/daily", json={"count": 10})
    words = c.get("/api/quiz").get_json()["words"]
    for w in words:
        c.post("/api/quiz/answer", json={"id": w["id"], "correct": True})
    plan = {it["key"]: it for it in db.get_today_plan(uid=uid)["items"]}
    assert plan["words"]["complete"] and plan["review"]["complete"] and plan["review"]["done"] == 10
    assert not plan["p5"]["complete"]
    assert db.get_stats(uid=uid)["streak"] == 1
    html = c.get("/").get_data(as_text=True)
    assert "오늘 할 일" in html and "plan-row complete" in html


def test_quiz_grade_validation():
    c, _ = as_user()
    wid = c.post("/api/word", json={"word": "apple", "meaning": "사과"}).get_json()["id"]
    assert c.post("/api/quiz/answer", json={"id": wid, "grade": 2}).status_code == 400
    res = c.post("/api/quiz/answer", json={"id": wid, "correct": True, "grade": 5}).get_json()
    assert res["interval"] == 1 and res["due_count"] == 0


@pytest.mark.parametrize("path", ["/", "/toeic", "/toeic?review=1", "/toeic?cat=%EC%96%B4%ED%9C%98",
                                  "/toeic/test", "/opic", "/history", "/account", "/quiz", "/vocab"])
def test_pages_render_with_data(path):
    c, _ = as_user()
    c.post("/api/vocab/daily", json={"count": 3})
    q = c.post("/api/toeic/question", json={}).get_json()
    c.post("/api/toeic/answer", json={"id": q["id"], "my_answer": (q["answer"] + 1) % 4})
    assert c.get(path).status_code == 200


def test_secret_key_is_persisted_when_env_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "k.db"))
    first = app_module._secret_key()
    assert len(first) >= 32 and first == app_module._secret_key()
    assert (tmp_path / ".secret_key").exists()
