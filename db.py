"""
db.py — SQLite 데이터 계층

여러 사람이 각자 계정으로 쓰며, 모든 학습 기록은 user_id 로 나뉜다.

'기록이 사라지지 않도록' 다음을 지킨다.
  1) 매 저장마다 명시적으로 commit() 한다.
  2) WAL 모드 + synchronous=NORMAL 로 쓰기 안정성을 높인다.
  3) 저장은 트랜잭션으로 감싸고, 실패 시 rollback 후 예외를 다시 던진다.
  4) 요청마다 새 커넥션을 열고 with 블록으로 확실히 닫는다.

테이블
  users          : 계정 (아이디, 비밀번호 해시, 하루 목표, 목표 점수)
  words          : 외운 단어 (+ 간격 반복 SM-2 상태)
  sentences      : 공부한 회화 문장
  opic_answers   : 오픽 답변 연습
  toeic_quiz_log : 토익 Part5 풀이 기록 (문제 id·유형·출처 포함)
  p5_srs         : 틀린 Part5 문제의 복습 일정 (SM-2)
  review_log     : 단어 퀴즈 채점 기록 (오늘 복습량·정답률)
  mock_tests     : 미니 모의고사 결과
  wordbook       : 일괄 적재한 단어장 (공용) / wordbook_pulls : 사용자별로 가져간 단어

계정 도입 전 데이터(user_id 컬럼이 없던 DB)는 user_id=1 로 남는다.
첫 계정(또는 OWNER_USERNAME 과 같은 아이디로 만든 계정)이 id 1 을 받아 그 기록을 이어받는다.

모든 조회/저장 함수는 uid 키워드를 받는다 (기본값 1 = 기존 단일 사용자 데이터).
"""

import hashlib
import json
import os
import random
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

import content

DB_PATH = os.getenv("DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "learning.db")

LEGACY_UID = 1


@contextmanager
def get_conn():
    """안전한 커넥션 컨텍스트 매니저 (dict 접근, WAL, commit/rollback 보장)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        # 여러 gunicorn worker 가 새 DB 를 동시에 열면 WAL 전환이 잠깐 겹친다 — 파일 설정을 그대로 쓴다.
        pass
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _enable_wal(retries=20):
    for _ in range(retries):
        conn = sqlite3.connect(DB_PATH, timeout=10)
        try:
            mode = conn.execute("PRAGMA journal_mode=WAL;").fetchone()[0]
            if str(mode).lower() == "wal":
                return
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
        time.sleep(0.1)


def _ensure_column(conn, table, column, decl):
    """테이블에 컬럼이 없으면 추가한다. 새로 추가했으면 True."""
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        return True
    return False


def init_db():
    """테이블 생성 + 기존 DB 마이그레이션. 앱 시작 시 1회 호출 (여러 번 호출해도 안전)."""
    _enable_wal()
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL,
                goal_words    INTEGER NOT NULL DEFAULT 10,   -- 하루 새 단어 목표
                goal_p5       INTEGER NOT NULL DEFAULT 10,   -- 하루 Part 5 문제 목표
                goal_opic     INTEGER NOT NULL DEFAULT 1,    -- 하루 오픽 답변 목표
                target_level  TEXT    NOT NULL DEFAULT '800' -- 토익 목표 점수대
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS words (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                word        TEXT    NOT NULL,
                meaning     TEXT    NOT NULL,
                pronunciation TEXT  NOT NULL DEFAULT '',
                example     TEXT    NOT NULL DEFAULT '',
                example_kr  TEXT    NOT NULL DEFAULT ''
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sentences (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                original    TEXT    NOT NULL,
                corrected   TEXT    NOT NULL,
                feedback    TEXT    NOT NULL,
                meaning     TEXT    NOT NULL DEFAULT '',
                score       INTEGER NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opic_answers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    NOT NULL,
                date         TEXT    NOT NULL,
                topic        TEXT    NOT NULL DEFAULT '',
                question     TEXT    NOT NULL,
                answer       TEXT    NOT NULL,
                corrected    TEXT    NOT NULL DEFAULT '',
                feedback     TEXT    NOT NULL DEFAULT '',
                model_answer TEXT    NOT NULL DEFAULT '',
                score        INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS toeic_quiz_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at     TEXT    NOT NULL,
                date           TEXT    NOT NULL,
                question       TEXT    NOT NULL,
                choices        TEXT    NOT NULL,              -- 보기 4개 (JSON 배열)
                my_answer      INTEGER NOT NULL,
                correct_answer INTEGER NOT NULL,
                explanation    TEXT    NOT NULL DEFAULT '',
                is_correct     INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wordbook (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                word       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                meaning    TEXT    NOT NULL,
                example    TEXT    NOT NULL DEFAULT '',
                example_kr TEXT    NOT NULL DEFAULT '',
                added      INTEGER NOT NULL DEFAULT 0,   -- (계정 도입 전) 이미 가져감 표시
                added_at   TEXT    NOT NULL DEFAULT ''
            );
            """
        )

        # --- 예전 마이그레이션: SRS(Leitner) · 모드 태그 ---
        _ensure_column(conn, "words", "box", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "words", "next_review", "TEXT NOT NULL DEFAULT ''")
        conn.execute("UPDATE words SET next_review = date WHERE next_review = ''")
        _ensure_column(conn, "words", "mode", "TEXT NOT NULL DEFAULT 'talk'")
        _ensure_column(conn, "sentences", "mode", "TEXT NOT NULL DEFAULT 'talk'")

        # --- 계정별 데이터: 기존 행은 user_id=1(첫 계정)로 남는다 ---
        for table in ("words", "sentences", "opic_answers", "toeic_quiz_log"):
            _ensure_column(conn, table, "user_id", f"INTEGER NOT NULL DEFAULT {LEGACY_UID}")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_user_date ON {table}(user_id, date)")

        # --- 단어 SM-2 상태 + 출처 ---
        added_sm2 = _ensure_column(conn, "words", "ease", "REAL NOT NULL DEFAULT 2.5")
        _ensure_column(conn, "words", "interval", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "words", "reps", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "words", "lapses", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "words", "pos", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "words", "source_id", "TEXT NOT NULL DEFAULT ''")
        if added_sm2:
            # Leitner 박스 → SM-2 간격으로 옮긴다 (박스 2=3일, 3=7일, 4=14일, 5=30일)
            conn.execute(
                """UPDATE words SET
                     interval = CASE box WHEN 2 THEN 3 WHEN 3 THEN 7 WHEN 4 THEN 14 WHEN 5 THEN 30 ELSE 0 END,
                     reps = MAX(box - 1, 0)"""
            )

        # --- Part 5 풀이 기록: 문제 id·유형·출처 ---
        _ensure_column(conn, "toeic_quiz_log", "qid", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "toeic_quiz_log", "category", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "toeic_quiz_log", "source", "TEXT NOT NULL DEFAULT 'practice'")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS p5_srs (
                user_id     INTEGER NOT NULL,
                qkey        TEXT    NOT NULL,              -- 문제 id (은행) 또는 h:해시 (AI 문제)
                payload     TEXT    NOT NULL,              -- 문제 JSON (question, choices, answer, explanation, category)
                ease        REAL    NOT NULL DEFAULT 2.5,
                interval    INTEGER NOT NULL DEFAULT 0,
                reps        INTEGER NOT NULL DEFAULT 0,
                lapses      INTEGER NOT NULL DEFAULT 0,
                next_review TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL,
                PRIMARY KEY (user_id, qkey)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS review_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                date       TEXT    NOT NULL,
                kind       TEXT    NOT NULL,     -- 'word'
                ref        TEXT    NOT NULL,
                correct    INTEGER NOT NULL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_review_user_date ON review_log(user_id, date)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mock_tests (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                created_at TEXT    NOT NULL,
                date       TEXT    NOT NULL,
                total      INTEGER NOT NULL,
                correct    INTEGER NOT NULL,
                seconds    INTEGER NOT NULL,
                limit_sec  INTEGER NOT NULL,
                detail     TEXT    NOT NULL DEFAULT '{}'   -- 유형별 정답 수 JSON
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wordbook_pulls (
                user_id     INTEGER NOT NULL,
                wordbook_id INTEGER NOT NULL,
                pulled_at   TEXT    NOT NULL,
                PRIMARY KEY (user_id, wordbook_id)
            );
            """
        )
        # 계정 도입 전에 이미 가져간 단어장 항목은 첫 계정이 가져간 것으로 옮긴다
        conn.execute(
            f"""INSERT OR IGNORE INTO wordbook_pulls (user_id, wordbook_id, pulled_at)
                SELECT {LEGACY_UID}, id, added_at FROM wordbook WHERE added = 1"""
        )
        conn.execute("UPDATE wordbook SET added = 0 WHERE added = 1")


def _now():
    now = datetime.now()
    return now.isoformat(timespec="seconds"), now.strftime("%Y-%m-%d")


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 계정
# ---------------------------------------------------------------------------
def _has_legacy_data(conn):
    for table in ("words", "sentences", "opic_answers", "toeic_quiz_log"):
        if conn.execute(f"SELECT 1 FROM {table} WHERE user_id=? LIMIT 1", (LEGACY_UID,)).fetchone():
            return True
    return False


def create_user(username, password_hash, owner_username=None):
    """계정을 만들고 id 를 반환한다. 같은 아이디가 있으면 ValueError.

    id 1(계정 도입 전 기록의 주인)은 owner_username 이 정해져 있으면 그 아이디에게,
    아니면 첫 계정에게 준다. 다른 사람이 먼저 가입하면 id 2 부터 받는다.
    """
    username = username.strip()
    created_at, _ = _now()
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise ValueError("이미 사용 중인 아이디입니다.")
        uid = None
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (LEGACY_UID,)).fetchone():
            if not owner_username or owner_username.strip().lower() == username.lower():
                uid = LEGACY_UID
            else:
                top = conn.execute("SELECT COALESCE(MAX(id), 0) FROM users").fetchone()[0]
                uid = max(top, LEGACY_UID) + 1
        try:
            cur = conn.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (uid, username, password_hash, created_at),
            )
        except sqlite3.IntegrityError:
            raise ValueError("이미 사용 중인 아이디입니다.")
        return cur.lastrowid


def has_legacy_data():
    with get_conn() as conn:
        return _has_legacy_data(conn)


def get_user(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(row) if row else None


def get_user_by_name(username):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", ((username or "").strip(),)).fetchone()
        return dict(row) if row else None


def count_users():
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def update_password(uid, password_hash):
    with get_conn() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, uid))


def update_goals(uid, goal_words, goal_p5, goal_opic, target_level):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET goal_words=?, goal_p5=?, goal_opic=?, target_level=? WHERE id=?",
            (int(goal_words), int(goal_p5), int(goal_opic), target_level, uid),
        )


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------
VALID_MODES = ("toeic", "opic", "talk", "vocab")


def _clean_mode(mode):
    return mode if mode in VALID_MODES else "talk"


def add_word(word, meaning, pronunciation="", example="", example_kr="", mode="talk",
             pos="", source_id="", uid=LEGACY_UID):
    """단어 1개를 저장하고 id 를 반환한다. (새 단어는 오늘부터 복습 대상)"""
    created_at, date = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO words (user_id, created_at, date, word, meaning, pronunciation, example, example_kr,
                               box, next_review, mode, pos, source_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (uid, created_at, date, word.strip(), meaning.strip(),
             (pronunciation or "").strip(), (example or "").strip(), (example_kr or "").strip(), date,
             _clean_mode(mode), (pos or "").strip(), source_id or ""),
        )
        return cur.lastrowid


def find_word(word, uid=LEGACY_UID):
    """같은 단어(대소문자 무시)가 이 사용자에게 이미 있으면 그 행, 없으면 None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM words WHERE user_id=? AND LOWER(word) = LOWER(?) LIMIT 1", (uid, word.strip())
        ).fetchone()
        return dict(row) if row else None


def delete_word(word_id, uid=LEGACY_UID):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM words WHERE id=? AND user_id=?", (int(word_id), uid))
        return cur.rowcount > 0


def add_sentence(original, corrected, feedback, meaning="", score=0, mode="talk", uid=LEGACY_UID):
    created_at, date = _now()
    score = int(max(0, min(100, score)))
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO sentences (user_id, created_at, date, original, corrected, feedback, meaning, score, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, created_at, date, original.strip(), corrected.strip(),
             feedback.strip(), meaning.strip(), score, _clean_mode(mode)),
        )
        return cur.lastrowid


def add_opic_answer(topic, question, answer, corrected="", feedback="", model_answer="", score=0,
                    uid=LEGACY_UID):
    created_at, date = _now()
    score = int(max(0, min(100, score)))
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO opic_answers (user_id, created_at, date, topic, question, answer, corrected, feedback,
                                      model_answer, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, created_at, date, topic.strip(), question.strip(), answer.strip(),
             corrected.strip(), feedback.strip(), model_answer.strip(), score),
        )
        return cur.lastrowid


def add_toeic_quiz(question, choices, my_answer, correct_answer, explanation="", is_correct=False,
                   qid="", category="", source="practice", uid=LEGACY_UID):
    """Part5 풀이 1건을 저장하고, 틀린 문제는 복습 일정(p5_srs)에 넣는다. id 반환."""
    created_at, date = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO toeic_quiz_log (user_id, created_at, date, question, choices, my_answer, correct_answer,
                                        explanation, is_correct, qid, category, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, created_at, date, question.strip(), json.dumps(list(choices), ensure_ascii=False),
             int(my_answer), int(correct_answer), (explanation or "").strip(), 1 if is_correct else 0,
             qid or "", category or "", source),
        )
        log_id = cur.lastrowid
    payload = {
        "id": qid or "", "question": question.strip(), "choices": list(choices),
        "answer": int(correct_answer), "explanation": (explanation or "").strip(), "category": category or "",
    }
    _update_p5_srs(uid, payload, bool(is_correct))
    return log_id


# ---------------------------------------------------------------------------
# 간격 반복 — SM-2 간소화
#   grade: 0 = 모름(틀림), 3 = 어렵게 맞힘, 4 = 맞힘, 5 = 쉬움
#   틀리면 간격 0(오늘 다시), 맞히면 1일 → 3일 → 간격 × 쉬움 정도 (최대 180일)
# ---------------------------------------------------------------------------
MAX_INTERVAL = 180


def sm2(ease, interval, reps, grade):
    """다음 (ease, interval, reps). interval=0 이면 오늘 다시."""
    if grade < 3:
        return max(1.3, ease - 0.2), 0, 0
    ease = max(1.3, ease + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)))
    reps += 1
    if reps == 1:
        interval = 1
    elif reps == 2:
        interval = 3
    else:
        interval = round(max(interval, 1) * ease * (1.3 if grade == 5 else 1.0))
    return round(ease, 2), min(interval, MAX_INTERVAL), reps


def _box_for(interval):
    """화면 표시용 단계 1~5 (간격 기준)."""
    if interval <= 0:
        return 1
    if interval <= 2:
        return 2
    if interval <= 6:
        return 3
    if interval <= 20:
        return 4
    return 5


def _qkey(payload):
    if payload.get("id"):
        return payload["id"]
    return "h:" + hashlib.sha1(payload["question"].encode("utf-8")).hexdigest()[:16]


def _update_p5_srs(uid, payload, correct):
    """틀린 문제는 복습 큐에 넣고, 큐에 있는 문제를 맞히면 간격을 늘린다."""
    key = _qkey(payload)
    now, today = _now()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM p5_srs WHERE user_id=? AND qkey=?", (uid, key)).fetchone()
        if row is None:
            if correct:
                return  # 처음부터 맞힌 문제는 복습할 필요 없음
            conn.execute(
                """INSERT INTO p5_srs (user_id, qkey, payload, ease, interval, reps, lapses, next_review, updated_at)
                   VALUES (?, ?, ?, 2.3, 0, 0, 1, ?, ?)""",
                (uid, key, json.dumps(payload, ensure_ascii=False), today, now),
            )
            return
        ease, interval, reps = sm2(row["ease"], row["interval"], row["reps"], 4 if correct else 0)
        nxt = (datetime.now().date() + timedelta(days=interval)).strftime("%Y-%m-%d")
        conn.execute(
            """UPDATE p5_srs SET ease=?, interval=?, reps=?, lapses=lapses+?, next_review=?, updated_at=?
               WHERE user_id=? AND qkey=?""",
            (ease, interval, reps, 0 if correct else 1, nxt, now, uid, key),
        )


def get_due_p5(uid=LEGACY_UID, limit=20):
    """오늘 복습할 Part5 오답 (정답·해설 포함)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT payload, lapses, next_review FROM p5_srs
               WHERE user_id=? AND next_review <= ? ORDER BY next_review ASC, lapses DESC LIMIT ?""",
            (uid, today_str(), limit),
        ).fetchall()
    out = []
    for r in rows:
        p = json.loads(r["payload"])
        p["lapses"] = r["lapses"]
        out.append(p)
    return out


def count_due_p5(uid=LEGACY_UID):
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM p5_srs WHERE user_id=? AND next_review <= ?", (uid, today_str())
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------
def get_today_counts(mode=None, uid=LEGACY_UID):
    today = today_str()
    with get_conn() as conn:
        if mode:
            w = conn.execute("SELECT COUNT(*) FROM words WHERE user_id=? AND date=? AND mode=?",
                             (uid, today, mode)).fetchone()[0]
            s = conn.execute("SELECT COUNT(*) FROM sentences WHERE user_id=? AND date=? AND mode=?",
                             (uid, today, mode)).fetchone()[0]
        else:
            w = conn.execute("SELECT COUNT(*) FROM words WHERE user_id=? AND date=?", (uid, today)).fetchone()[0]
            s = conn.execute("SELECT COUNT(*) FROM sentences WHERE user_id=? AND date=?",
                             (uid, today)).fetchone()[0]
    return {"words": w, "sentences": s}


def get_today_items(mode=None, uid=LEGACY_UID):
    today = today_str()
    with get_conn() as conn:
        if mode:
            words = conn.execute("SELECT * FROM words WHERE user_id=? AND date=? AND mode=? ORDER BY id ASC",
                                 (uid, today, mode)).fetchall()
            sentences = conn.execute(
                "SELECT * FROM sentences WHERE user_id=? AND date=? AND mode=? ORDER BY id ASC",
                (uid, today, mode)).fetchall()
        else:
            words = conn.execute("SELECT * FROM words WHERE user_id=? AND date=? ORDER BY id ASC",
                                 (uid, today)).fetchall()
            sentences = conn.execute("SELECT * FROM sentences WHERE user_id=? AND date=? ORDER BY id ASC",
                                     (uid, today)).fetchall()
    return {"words": [dict(r) for r in words], "sentences": [dict(r) for r in sentences]}


def get_today_mode_summary(uid=LEGACY_UID):
    today = today_str()
    q = lambda sql: conn.execute(sql, (uid, today)).fetchone()[0]  # noqa: E731
    with get_conn() as conn:
        summary = {
            "toeic": {"words": q("SELECT COUNT(*) FROM words WHERE user_id=? AND date=? AND mode='toeic'"),
                      "quiz": q("SELECT COUNT(*) FROM toeic_quiz_log WHERE user_id=? AND date=?")},
            "opic": {"answers": q("SELECT COUNT(*) FROM opic_answers WHERE user_id=? AND date=?")},
            "talk": {"words": q("SELECT COUNT(*) FROM words WHERE user_id=? AND date=? AND mode='talk'"),
                     "sentences": q("SELECT COUNT(*) FROM sentences WHERE user_id=? AND date=? AND mode='talk'")},
            "vocab": {"words": q("SELECT COUNT(*) FROM words WHERE user_id=? AND date=? AND mode='vocab'")},
        }
    return summary


# 학습한 날로 치는 기록들 (날짜 컬럼 이름이 모두 date)
_ACTIVITY_TABLES = ("words", "sentences", "opic_answers", "toeic_quiz_log", "review_log", "mock_tests")


def get_week_activity(days=7, uid=LEGACY_UID):
    """최근 N일(오늘 포함) 날짜별 학습 항목 수 (오래된 날 → 오늘)."""
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]
    counts = {d: 0 for d in dates}
    with get_conn() as conn:
        for table in ("words", "sentences", "opic_answers", "toeic_quiz_log", "review_log"):
            rows = conn.execute(
                f"SELECT date, COUNT(*) FROM {table} WHERE user_id=? AND date >= ? GROUP BY date",
                (uid, dates[0]),
            ).fetchall()
            for d, n in rows:
                if d in counts:
                    counts[d] += n
    weekdays = "월화수목금토일"
    return [
        {"date": d, "weekday": weekdays[datetime.strptime(d, "%Y-%m-%d").weekday()],
         "count": counts[d], "is_today": d == dates[-1]}
        for d in dates
    ]


def get_history(limit_days=60, uid=LEGACY_UID):
    """날짜별로 묶은 학습 기록 (최신 날짜 순)."""
    with get_conn() as conn:
        dates = conn.execute(
            """
            SELECT date FROM (
                SELECT date FROM words WHERE user_id=:u
                UNION SELECT date FROM sentences WHERE user_id=:u
                UNION SELECT date FROM opic_answers WHERE user_id=:u
                UNION SELECT date FROM toeic_quiz_log WHERE user_id=:u
            ) ORDER BY date DESC LIMIT :n
            """,
            {"u": uid, "n": limit_days},
        ).fetchall()

        history = []
        for row in dates:
            d = row["date"]
            fetch = lambda t: conn.execute(  # noqa: E731
                f"SELECT * FROM {t} WHERE user_id=? AND date=? ORDER BY id ASC", (uid, d)).fetchall()
            history.append({
                "date": d,
                "words": [dict(r) for r in fetch("words")],
                "sentences": [dict(r) for r in fetch("sentences")],
                "opic": [dict(r) for r in fetch("opic_answers")],
                "toeic": [{**dict(r), "choices": json.loads(r["choices"])} for r in fetch("toeic_quiz_log")],
            })
    return history


def _study_dates(conn, uid):
    union = " UNION ".join(f"SELECT date FROM {t} WHERE user_id=:u" for t in _ACTIVITY_TABLES)
    return [r[0] for r in conn.execute(f"SELECT date FROM ({union}) ORDER BY date DESC", {"u": uid})]


def get_stats(uid=LEGACY_UID):
    """전체 통계 + 연속 학습일(streak) + 최장 연속."""
    with get_conn() as conn:
        c = lambda t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE user_id=?", (uid,)).fetchone()[0]  # noqa
        stats = {
            "total_words": c("words"),
            "total_sentences": c("sentences"),
            "total_opic": c("opic_answers"),
            "total_toeic": c("toeic_quiz_log"),
            "total_reviews": c("review_log"),
            "total_tests": c("mock_tests"),
        }
        study_dates = _study_dates(conn, uid)
    stats["total_days"] = len(study_dates)
    stats["streak"] = _calc_streak(study_dates)
    stats["best_streak"] = _best_streak(study_dates)
    stats["studied_today"] = today_str() in set(study_dates)
    return stats


def _calc_streak(study_dates):
    """오늘(또는 어제)부터 며칠 연속으로 공부했는지."""
    if not study_dates:
        return 0
    dateset = set(study_dates)
    today = datetime.now().date()
    cur = today if today.strftime("%Y-%m-%d") in dateset else today - timedelta(days=1)
    streak = 0
    while cur.strftime("%Y-%m-%d") in dateset:
        streak += 1
        cur -= timedelta(days=1)
    return streak


def _best_streak(study_dates):
    days = sorted({datetime.strptime(d, "%Y-%m-%d").date() for d in study_dates})
    best = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    return best


def get_review_items(kind="words", limit=100, uid=LEGACY_UID):
    """플래시카드용 [{front(한글), back(영어), extra}]."""
    with get_conn() as conn:
        if kind == "sentences":
            rows = conn.execute(
                "SELECT meaning, corrected, feedback FROM sentences WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (uid, limit),
            ).fetchall()
            return [{"front": r["meaning"] or "(한글 뜻 없음 — 영어를 보고 떠올려보세요)",
                     "back": r["corrected"], "extra": r["feedback"]} for r in rows]
        rows = conn.execute(
            "SELECT word, meaning, pronunciation, example, example_kr FROM words WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?", (uid, limit),
        ).fetchall()
        return [{"front": r["meaning"], "back": r["word"],
                 "extra": (r["pronunciation"] + "  ·  " if r["pronunciation"] else "") + (r["example"] or "")}
                for r in rows]


# ---------------------------------------------------------------------------
# 단어 퀴즈 + 간격 반복
# ---------------------------------------------------------------------------
def get_due_words(limit=20, uid=LEGACY_UID):
    """오늘 복습할 단어 (기한이 오래 지난 것, 자주 틀린 것 먼저)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, word, meaning, pronunciation, example, example_kr, pos, box, interval, reps, next_review
            FROM words WHERE user_id=? AND next_review <= ?
            ORDER BY next_review ASC, interval ASC, lapses DESC, id ASC
            LIMIT ?
            """,
            (uid, today_str(), limit),
        ).fetchall()
        return [dict(r) for r in rows]


def count_due_words(uid=LEGACY_UID):
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM words WHERE user_id=? AND next_review <= ?", (uid, today_str())
        ).fetchone()[0]


_DISTRACTOR_POOL = [
    "improve", "schedule", "available", "decision", "experience", "recommend",
    "invoice", "quarterly", "reimburse", "comply", "merger", "warranty",
    "postpone", "routine", "reserve", "travel", "order", "budget",
]


def get_distractors(word_id, count=3, uid=LEGACY_UID):
    """객관식 오답 보기 — 내 단어(같은 품사 우선) → 토익 어휘 → 내장 풀 순으로 채운다."""
    with get_conn() as conn:
        ans = conn.execute("SELECT word, pos FROM words WHERE id=? AND user_id=?", (int(word_id), uid)).fetchone()
        answer = (ans["word"] if ans else "").strip().lower()
        pos = ans["pos"] if ans else ""
        rows = conn.execute(
            "SELECT DISTINCT word, pos FROM words WHERE user_id=? AND id != ? ORDER BY RANDOM() LIMIT ?",
            (uid, int(word_id), count * 4),
        ).fetchall()

    candidates = [r["word"].strip() for r in rows if pos and r["pos"] == pos]
    candidates += [r["word"].strip() for r in rows if not (pos and r["pos"] == pos)]
    bank = [w["word"] for w in content.vocab() if w["pos"] == pos] if pos else []
    random.shuffle(bank)
    pool = list(_DISTRACTOR_POOL)
    random.shuffle(pool)

    picked, seen = [], {answer}
    for w in candidates + bank + pool:
        if w.lower() not in seen:
            picked.append(w)
            seen.add(w.lower())
        if len(picked) >= count:
            break
    return picked


def update_word_review(word_id, correct, grade=None, uid=LEGACY_UID):
    """퀴즈 결과로 SM-2 상태를 갱신하고 채점 기록을 남긴다. 반환: {box, interval, next_review}"""
    if grade is None:
        grade = 4 if correct else 0
    grade = int(grade)
    today = datetime.now().date()
    with get_conn() as conn:
        row = conn.execute("SELECT ease, interval, reps FROM words WHERE id=? AND user_id=?",
                           (word_id, uid)).fetchone()
        if row is None:
            raise ValueError("단어를 찾을 수 없습니다.")
        ease, interval, reps = sm2(row["ease"] or 2.5, row["interval"] or 0, row["reps"] or 0, grade)
        next_str = (today + timedelta(days=interval)).strftime("%Y-%m-%d")
        box = _box_for(interval)
        conn.execute(
            "UPDATE words SET ease=?, interval=?, reps=?, lapses=lapses+?, box=?, next_review=? WHERE id=?",
            (ease, interval, reps, 1 if grade < 3 else 0, box, next_str, word_id),
        )
        conn.execute(
            "INSERT INTO review_log (user_id, date, kind, ref, correct) VALUES (?, ?, 'word', ?, ?)",
            (uid, today.strftime("%Y-%m-%d"), str(word_id), 1 if grade >= 3 else 0),
        )
    return {"box": box, "interval": interval, "next_review": next_str}


# ---------------------------------------------------------------------------
# 토익 어휘 은행 → 내 단어
# ---------------------------------------------------------------------------
def _my_word_keys(conn, uid):
    return {r[0] for r in conn.execute("SELECT LOWER(word) FROM words WHERE user_id=?", (uid,))}


def vocab_progress(uid=LEGACY_UID):
    """수준별 토익 어휘 진도 {level: {"total", "learned"}}."""
    with get_conn() as conn:
        mine = _my_word_keys(conn, uid)
    out = {}
    for lv in content.VOCAB_LEVELS:
        words = [w for w in content.vocab() if w["level"] == lv]
        out[lv] = {"total": len(words), "learned": sum(1 for w in words if w["word"].lower() in mine)}
    return out


def unseen_vocab(level, count, uid=LEGACY_UID, shuffle=False):
    """아직 내 단어에 없는 토익 어휘 (은행 순서 = 쉬운 것부터)."""
    with get_conn() as conn:
        mine = _my_word_keys(conn, uid)
    words = [w for w in content.vocab() if w["level"] == level and w["word"].lower() not in mine]
    if shuffle:
        random.shuffle(words)
    return words[:count]


def add_bank_words(level, count, uid=LEGACY_UID):
    """오늘의 단어: 목표 수준의 새 어휘 count 개를 내 단어(토익 모드)에 넣는다. 저장된 단어 목록 반환."""
    added = []
    for w in unseen_vocab(level, count, uid=uid):
        wid = add_word(word=w["word"], meaning=w["meaning"], example=w["example"], example_kr=w["example_kr"],
                       mode="toeic", pos=w["pos"], source_id=w["id"], uid=uid)
        added.append({"id": wid, "word": w["word"], "meaning": w["meaning"], "pos": w["pos"],
                      "pronunciation": "", "example": w["example"], "example_kr": w["example_kr"]})
    return added


# ---------------------------------------------------------------------------
# 토익 Part 5 문제 은행
# ---------------------------------------------------------------------------
def _p5_seen(conn, uid):
    """qid → (풀이 횟수, 마지막 풀이 id)."""
    return {r["qid"]: (r["n"], r["last"]) for r in conn.execute(
        "SELECT qid, COUNT(*) AS n, MAX(id) AS last FROM toeic_quiz_log WHERE user_id=? AND qid != '' "
        "GROUP BY qid", (uid,))}


def pick_p5(uid=LEGACY_UID, category=None, level=None, exclude=(), count=1):
    """안 푼 문제부터, 그다음은 오래전에 푼 문제부터 고른다 (같은 우선순위 안에서는 무작위)."""
    with get_conn() as conn:
        seen = _p5_seen(conn, uid)
    pool = [q for q in content.part5()
            if (not category or q["category"] == category)
            and (not level or q["level"] == level)
            and q["id"] not in exclude]
    random.shuffle(pool)
    pool.sort(key=lambda q: (seen.get(q["id"], (0, 0))[0] > 0, seen.get(q["id"], (0, 0))[1]))
    return pool[:count]


def p5_progress(uid=LEGACY_UID):
    """{"solved": 은행에서 한 번이라도 푼 문제 수, "total": 은행 문제 수}"""
    with get_conn() as conn:
        seen = _p5_seen(conn, uid)
    ids = content.part5_by_id()
    return {"solved": sum(1 for k in seen if k in ids), "total": len(ids)}


def get_weakness(uid=LEGACY_UID):
    """유형별 정답률 (Part 5) — 정답률 낮은 순. 시도 0인 유형도 포함."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n, SUM(is_correct) AS ok FROM toeic_quiz_log "
            "WHERE user_id=? AND category != '' GROUP BY category", (uid,)
        ).fetchall()
        word = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(correct), 0) AS ok FROM review_log "
            "WHERE user_id=? AND kind='word' AND date >= ?",
            (uid, (datetime.now().date() - timedelta(days=30)).strftime("%Y-%m-%d")),
        ).fetchone()
        opic = conn.execute(
            "SELECT topic, COUNT(*) AS n, ROUND(AVG(score)) AS avg FROM opic_answers WHERE user_id=? "
            "GROUP BY topic ORDER BY avg ASC", (uid,)
        ).fetchall()
    by_cat = {r["category"]: (r["n"], r["ok"] or 0) for r in rows}
    cats = []
    for c in content.P5_CATEGORIES:
        n, ok = by_cat.get(c, (0, 0))
        cats.append({"category": c, "total": n, "correct": ok, "rate": round(ok * 100 / n) if n else None})
    cats.sort(key=lambda x: (x["rate"] is None, x["rate"] if x["rate"] is not None else 0))
    return {
        "categories": cats,
        "word_quiz": {"total": word["n"], "correct": word["ok"],
                      "rate": round(word["ok"] * 100 / word["n"]) if word["n"] else None},
        "opic": [{"topic": r["topic"] or "기타", "count": r["n"], "avg": int(r["avg"] or 0)} for r in opic],
    }


def add_mock_test(total, correct, seconds, limit_sec, detail, uid=LEGACY_UID):
    created_at, date = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO mock_tests (user_id, created_at, date, total, correct, seconds, limit_sec, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, created_at, date, int(total), int(correct), int(seconds), int(limit_sec),
             json.dumps(detail, ensure_ascii=False)),
        )
        return cur.lastrowid


def get_mock_tests(uid=LEGACY_UID, limit=10):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM mock_tests WHERE user_id=? ORDER BY id DESC LIMIT ?",
                            (uid, limit)).fetchall()
    return [{**dict(r), "detail": json.loads(r["detail"] or "{}")} for r in rows]


# ---------------------------------------------------------------------------
# 오늘 할 일
# ---------------------------------------------------------------------------
def get_today_plan(uid=LEGACY_UID):
    """홈 화면 '오늘 할 일' — 각 항목 {key, done, goal, remaining, complete} + 전체 진행률."""
    user = get_user(uid) or {"goal_words": 10, "goal_p5": 10, "goal_opic": 1, "target_level": "800"}
    today = today_str()
    with get_conn() as conn:
        one = lambda sql, *a: conn.execute(sql, (uid, today, *a)).fetchone()[0]  # noqa: E731
        reviewed = one("SELECT COUNT(DISTINCT ref) FROM review_log WHERE user_id=? AND date=? AND kind='word'")
        new_words = one("SELECT COUNT(*) FROM words WHERE user_id=? AND date=?")
        p5_done = one("SELECT COUNT(*) FROM toeic_quiz_log WHERE user_id=? AND date=?")
        opic_done = one("SELECT COUNT(*) FROM opic_answers WHERE user_id=? AND date=?")
    due_words = count_due_words(uid=uid)
    due_p5 = count_due_p5(uid=uid)

    items = [
        {"key": "review", "title": "단어 복습", "done": reviewed, "goal": reviewed + due_words,
         "remaining": due_words, "href": "/quiz", "unit": "개"},
        {"key": "words", "title": "새 단어", "done": new_words, "goal": user["goal_words"],
         "remaining": max(0, user["goal_words"] - new_words), "href": "/toeic#vocab", "unit": "개"},
        {"key": "p5", "title": "Part 5 문제", "done": p5_done, "goal": user["goal_p5"],
         "remaining": max(0, user["goal_p5"] - p5_done), "href": "/toeic", "unit": "문제"},
        {"key": "wrong", "title": "오답 복습", "done": 0, "goal": due_p5,
         "remaining": due_p5, "href": "/toeic?review=1", "unit": "문제"},
        {"key": "opic", "title": "오픽 답변", "done": opic_done, "goal": user["goal_opic"],
         "remaining": max(0, user["goal_opic"] - opic_done), "href": "/opic", "unit": "개"},
    ]
    for it in items:
        it["complete"] = it["remaining"] == 0
        it["ratio"] = 1.0 if it["goal"] <= 0 else min(1.0, it["done"] / it["goal"])
        if it["complete"]:
            it["ratio"] = 1.0
    # 비어 있는 복습 항목(할 게 없음)은 진행률 계산에서 뺀다
    counted = [it for it in items if not (it["key"] in ("review", "wrong") and it["goal"] == 0)]
    percent = round(sum(it["ratio"] for it in counted) * 100 / len(counted)) if counted else 100
    return {"items": items, "percent": percent,
            "complete": all(it["complete"] for it in items), "target_level": user["target_level"]}


# ---------------------------------------------------------------------------
# 단어장 — 공용 풀, 사용자마다 따로 가져간다
# ---------------------------------------------------------------------------
def import_wordbook(entries):
    """단어장에 단어들을 적재한다 (이미 있는 단어는 건너뜀). 새로 넣은 개수 반환."""
    inserted = 0
    with get_conn() as conn:
        for e in entries:
            word = (e.get("word") or "").strip()
            meaning = " ".join((e.get("meaning") or "").split())
            if not word or not meaning:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO wordbook (word, meaning, example, example_kr) VALUES (?, ?, ?, ?)",
                (word, meaning, (e.get("example") or "").strip(), (e.get("example_kr") or "").strip()),
            )
            inserted += cur.rowcount
    return inserted


def wordbook_stats(uid=LEGACY_UID):
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM wordbook").fetchone()[0]
        added = conn.execute("SELECT COUNT(*) FROM wordbook_pulls WHERE user_id=?", (uid,)).fetchone()[0]
    return {"total": total, "added": added, "remaining": total - added}


def pull_wordbook(count=10, uid=LEGACY_UID):
    """단어장에서 아직 안 가져온 단어 count 개를 학습 목록(vocab 모드)으로 옮긴다."""
    count = int(max(1, min(50, count)))
    today = today_str()
    pulled = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM wordbook WHERE id NOT IN (SELECT wordbook_id FROM wordbook_pulls WHERE user_id=?) "
            "ORDER BY id ASC", (uid,)
        ).fetchall()
    for row in rows:
        if len(pulled) >= count:
            break
        entry = dict(row)
        with get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO wordbook_pulls (user_id, wordbook_id, pulled_at) VALUES (?, ?, ?)",
                         (uid, entry["id"], today))
        if find_word(entry["word"], uid=uid):
            continue
        wid = add_word(word=entry["word"], meaning=entry["meaning"], example=entry["example"],
                       example_kr=entry["example_kr"], mode="vocab", uid=uid)
        pulled.append({"id": wid, "word": entry["word"], "meaning": entry["meaning"], "pronunciation": "",
                       "example": entry["example"], "example_kr": entry["example_kr"]})
    return pulled


# ---------------------------------------------------------------------------
# 토익 오답 노트 (예전 방식 — 문제 문장 기준)
# ---------------------------------------------------------------------------
def get_wrong_toeic(limit=20, uid=LEGACY_UID):
    """틀린 기록이 있고 이후 정답 기록이 없는 문제."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM toeic_quiz_log
            WHERE user_id = :u AND is_correct = 0
              AND question NOT IN (SELECT question FROM toeic_quiz_log WHERE user_id = :u AND is_correct = 1)
            GROUP BY question
            ORDER BY MAX(id) DESC
            LIMIT :n
            """,
            {"u": uid, "n": limit},
        ).fetchall()
        return [{**dict(r), "choices": json.loads(r["choices"])} for r in rows]
