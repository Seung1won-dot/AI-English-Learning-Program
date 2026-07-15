"""
db.py — SQLite 데이터 계층

매일 공부하는 '단어'와 '회화 문장'을 따로 저장하고,
날짜별 기록 / 통계 / 복습용 조회를 담당한다.

'기록이 사라지지 않도록' 다음을 지킨다.
  1) 매 저장마다 명시적으로 commit() 한다. (커밋 누락 = 데이터 유실의 주원인)
  2) WAL 모드 + synchronous=NORMAL 로 쓰기 안정성을 높인다.
  3) 저장은 트랜잭션으로 감싸고, 실패 시 rollback 후 예외를 다시 던진다.
  4) 요청마다 새 커넥션을 열고 with 블록으로 확실히 닫는다.

테이블
  words          : 외운 단어 (단어, 뜻, 발음, 예문, 예문해석, 모드)
  sentences      : 공부한 회화 문장 (원문, 교정, 피드백, 한글뜻, 점수, 모드)
  opic_answers   : 오픽 답변 연습 (질문, 내 답변, 교정, 피드백, 모범답변, 점수)
  toeic_quiz_log : 토익 Part5 문제 풀이 기록 (문제, 보기, 내 답, 정답, 해설, 정오)

모드(mode) 값: 'toeic' | 'opic' | 'talk'  — 학습 기록을 목적별로 구분하는 태그
"""

import json
import os
import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

# DB 파일 경로 (이 파일과 같은 폴더에 생성)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learning.db")


@contextmanager
def get_conn():
    """안전한 커넥션 컨텍스트 매니저.

    - row_factory 로 컬럼명을 dict 처럼 접근하게 한다.
    - WAL 저널 모드로 쓰기 도중 크래시에도 데이터가 보존되도록 한다.
    - 정상 종료 시 commit, 예외 시 rollback 을 보장한다.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
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


def init_db():
    """테이블이 없으면 생성한다. 앱 시작 시 1회 호출."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS words (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL,   -- ISO 8601
                date        TEXT    NOT NULL,   -- YYYY-MM-DD
                word        TEXT    NOT NULL,   -- 영어 단어
                meaning     TEXT    NOT NULL,   -- 한글 뜻
                pronunciation TEXT  NOT NULL DEFAULT '',  -- 발음
                example     TEXT    NOT NULL DEFAULT '',   -- 영어 예문
                example_kr  TEXT    NOT NULL DEFAULT ''    -- 예문 해석
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sentences (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                original    TEXT    NOT NULL,   -- 내가 쓴 문장
                corrected   TEXT    NOT NULL,   -- AI 교정 문장
                feedback    TEXT    NOT NULL,   -- AI 피드백
                meaning     TEXT    NOT NULL DEFAULT '',  -- 한글 뜻
                score       INTEGER NOT NULL    -- 0~100
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_words_date ON words(date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sentences_date ON sentences(date);")

        # --- SRS(간격 반복) 컬럼: 기존 DB 에도 안전하게 추가 ---
        _ensure_column(conn, "words", "box", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "words", "next_review", "TEXT NOT NULL DEFAULT ''")
        # SRS 도입 전에 저장된 단어(next_review='')는 저장일부터 복습 대상으로 정규화
        conn.execute("UPDATE words SET next_review = date WHERE next_review = ''")

        # --- 학습 모드 태그: 기존 데이터는 '회화(talk)'로 분류 (데이터 유실 없음) ---
        _ensure_column(conn, "words", "mode", "TEXT NOT NULL DEFAULT 'talk'")
        _ensure_column(conn, "sentences", "mode", "TEXT NOT NULL DEFAULT 'talk'")

        # --- OPIC 답변 연습 기록 ---
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opic_answers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    NOT NULL,
                date         TEXT    NOT NULL,
                topic        TEXT    NOT NULL DEFAULT '',   -- 서베이 주제 (자기소개/집/취미...)
                question     TEXT    NOT NULL,              -- 오픽 질문
                answer       TEXT    NOT NULL,              -- 내 답변 (타이핑 또는 음성 인식)
                corrected    TEXT    NOT NULL DEFAULT '',   -- AI 교정문
                feedback     TEXT    NOT NULL DEFAULT '',   -- AI 피드백 (한국어)
                model_answer TEXT    NOT NULL DEFAULT '',   -- AI 모범답변
                score        INTEGER NOT NULL DEFAULT 0     -- 0~100
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_opic_date ON opic_answers(date);")

        # --- TOEIC Part5 문제 풀이 기록 ---
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS toeic_quiz_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at     TEXT    NOT NULL,
                date           TEXT    NOT NULL,
                question       TEXT    NOT NULL,              -- 문제 (빈칸 포함 문장)
                choices        TEXT    NOT NULL,              -- 보기 4개 (JSON 배열)
                my_answer      INTEGER NOT NULL,              -- 내가 고른 보기 (0~3)
                correct_answer INTEGER NOT NULL,              -- 정답 보기 (0~3)
                explanation    TEXT    NOT NULL DEFAULT '',   -- 해설 (한국어)
                is_correct     INTEGER NOT NULL DEFAULT 0     -- 1=정답, 0=오답
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_toeic_date ON toeic_quiz_log(date);")

        # --- 단어장 (PDF 등에서 일괄 적재해 두고 매일 조금씩 꺼내 외우는 풀) ---
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wordbook (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                word       TEXT    NOT NULL UNIQUE COLLATE NOCASE,  -- 영어 단어
                meaning    TEXT    NOT NULL,              -- 한글 뜻
                example    TEXT    NOT NULL DEFAULT '',   -- 영어 예문
                example_kr TEXT    NOT NULL DEFAULT '',   -- 예문 해석
                added      INTEGER NOT NULL DEFAULT 0,    -- 1=이미 학습 목록으로 가져감
                added_at   TEXT    NOT NULL DEFAULT ''    -- 가져간 날짜
            );
            """
        )


def _ensure_column(conn, table, column, decl):
    """테이블에 컬럼이 없으면 ALTER 로 추가한다 (마이그레이션)."""
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


# 간격 반복(Leitner) — 박스 단계별 다음 복습까지의 일수
SRS_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def _now():
    now = datetime.now()
    return now.isoformat(timespec="seconds"), now.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------
VALID_MODES = ("toeic", "opic", "talk", "vocab")


def _clean_mode(mode):
    """모드 값을 검증한다. 모르는 값이 오면 'talk'로 저장한다."""
    return mode if mode in VALID_MODES else "talk"


def add_word(word, meaning, pronunciation="", example="", example_kr="", mode="talk"):
    """단어 1개를 저장하고 id 를 반환한다. (새 단어는 오늘부터 복습 대상)"""
    created_at, date = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO words (created_at, date, word, meaning, pronunciation, example, example_kr, box, next_review, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (created_at, date, word.strip(), meaning.strip(),
             pronunciation.strip(), example.strip(), example_kr.strip(), date,
             _clean_mode(mode)),
        )
        return cur.lastrowid


def find_word(word):
    """같은 단어(대소문자 무시)가 이미 저장돼 있으면 그 행을, 없으면 None 을 반환한다."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM words WHERE LOWER(word) = LOWER(?) LIMIT 1", (word.strip(),)
        ).fetchone()
        return dict(row) if row else None


def delete_word(word_id):
    """단어 1개를 삭제한다. 삭제했으면 True, 해당 id 가 없으면 False."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM words WHERE id=?", (int(word_id),))
        return cur.rowcount > 0


def add_sentence(original, corrected, feedback, meaning="", score=0, mode="talk"):
    """회화 문장 1개를 저장하고 id 를 반환한다."""
    created_at, date = _now()
    score = int(max(0, min(100, score)))
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO sentences (created_at, date, original, corrected, feedback, meaning, score, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (created_at, date, original.strip(), corrected.strip(),
             feedback.strip(), meaning.strip(), score, _clean_mode(mode)),
        )
        return cur.lastrowid


def add_opic_answer(topic, question, answer, corrected="", feedback="", model_answer="", score=0):
    """오픽 답변 연습 1건을 저장하고 id 를 반환한다."""
    created_at, date = _now()
    score = int(max(0, min(100, score)))
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO opic_answers (created_at, date, topic, question, answer, corrected, feedback, model_answer, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (created_at, date, topic.strip(), question.strip(), answer.strip(),
             corrected.strip(), feedback.strip(), model_answer.strip(), score),
        )
        return cur.lastrowid


def add_toeic_quiz(question, choices, my_answer, correct_answer, explanation="", is_correct=False):
    """토익 Part5 문제 풀이 1건을 저장하고 id 를 반환한다. choices 는 보기 4개 리스트."""
    created_at, date = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO toeic_quiz_log (created_at, date, question, choices, my_answer, correct_answer, explanation, is_correct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (created_at, date, question.strip(), json.dumps(list(choices), ensure_ascii=False),
             int(my_answer), int(correct_answer), explanation.strip(), 1 if is_correct else 0),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------
def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def get_today_counts(mode=None):
    """오늘 공부한 단어 수 / 문장 수 (진행도 표시용). mode 를 주면 그 모드만 센다."""
    today = today_str()
    with get_conn() as conn:
        if mode:
            w = conn.execute("SELECT COUNT(*) FROM words WHERE date=? AND mode=?", (today, mode)).fetchone()[0]
            s = conn.execute("SELECT COUNT(*) FROM sentences WHERE date=? AND mode=?", (today, mode)).fetchone()[0]
        else:
            w = conn.execute("SELECT COUNT(*) FROM words WHERE date=?", (today,)).fetchone()[0]
            s = conn.execute("SELECT COUNT(*) FROM sentences WHERE date=?", (today,)).fetchone()[0]
    return {"words": w, "sentences": s}


def get_today_items(mode=None):
    """오늘 저장한 단어/문장 목록 (오늘 학습 화면에서 바로 보여주기)."""
    today = today_str()
    with get_conn() as conn:
        if mode:
            words = conn.execute(
                "SELECT * FROM words WHERE date=? AND mode=? ORDER BY id ASC", (today, mode)
            ).fetchall()
            sentences = conn.execute(
                "SELECT * FROM sentences WHERE date=? AND mode=? ORDER BY id ASC", (today, mode)
            ).fetchall()
        else:
            words = conn.execute(
                "SELECT * FROM words WHERE date=? ORDER BY id ASC", (today,)
            ).fetchall()
            sentences = conn.execute(
                "SELECT * FROM sentences WHERE date=? ORDER BY id ASC", (today,)
            ).fetchall()
    return {
        "words": [dict(r) for r in words],
        "sentences": [dict(r) for r in sentences],
    }


def get_today_mode_summary():
    """홈 화면 모드 카드용 — 모드별 오늘 학습량 요약.

    반환: {"toeic": {"words": n, "quiz": n}, "opic": {"answers": n},
           "talk": {"words": n, "sentences": n}, "vocab": {"words": n}}
    """
    today = today_str()
    with get_conn() as conn:
        toeic_words = conn.execute(
            "SELECT COUNT(*) FROM words WHERE date=? AND mode='toeic'", (today,)).fetchone()[0]
        toeic_quiz = conn.execute(
            "SELECT COUNT(*) FROM toeic_quiz_log WHERE date=?", (today,)).fetchone()[0]
        opic_answers = conn.execute(
            "SELECT COUNT(*) FROM opic_answers WHERE date=?", (today,)).fetchone()[0]
        talk_words = conn.execute(
            "SELECT COUNT(*) FROM words WHERE date=? AND mode='talk'", (today,)).fetchone()[0]
        talk_sents = conn.execute(
            "SELECT COUNT(*) FROM sentences WHERE date=? AND mode='talk'", (today,)).fetchone()[0]
        vocab_words = conn.execute(
            "SELECT COUNT(*) FROM words WHERE date=? AND mode='vocab'", (today,)).fetchone()[0]
    return {
        "toeic": {"words": toeic_words, "quiz": toeic_quiz},
        "opic": {"answers": opic_answers},
        "talk": {"words": talk_words, "sentences": talk_sents},
        "vocab": {"words": vocab_words},
    }


def get_history(limit_days=60):
    """날짜별로 묶은 학습 기록을 최신 날짜 순으로 반환한다.

    반환: [{date, words:[...], sentences:[...], opic:[...], toeic:[...]}, ...]
    (words/sentences 각 항목에는 mode 태그가 포함된다)
    """
    with get_conn() as conn:
        dates = conn.execute(
            """
            SELECT date FROM (
                SELECT date FROM words
                UNION
                SELECT date FROM sentences
                UNION
                SELECT date FROM opic_answers
                UNION
                SELECT date FROM toeic_quiz_log
            )
            ORDER BY date DESC
            LIMIT ?
            """,
            (limit_days,),
        ).fetchall()

        history = []
        for row in dates:
            d = row["date"]
            words = conn.execute(
                "SELECT * FROM words WHERE date=? ORDER BY id ASC", (d,)
            ).fetchall()
            sentences = conn.execute(
                "SELECT * FROM sentences WHERE date=? ORDER BY id ASC", (d,)
            ).fetchall()
            opic = conn.execute(
                "SELECT * FROM opic_answers WHERE date=? ORDER BY id ASC", (d,)
            ).fetchall()
            toeic = conn.execute(
                "SELECT * FROM toeic_quiz_log WHERE date=? ORDER BY id ASC", (d,)
            ).fetchall()
            history.append({
                "date": d,
                "words": [dict(r) for r in words],
                "sentences": [dict(r) for r in sentences],
                "opic": [dict(r) for r in opic],
                "toeic": [{**dict(r), "choices": json.loads(r["choices"])} for r in toeic],
            })
    return history


def get_stats():
    """전체 통계 + 연속 학습일(streak)."""
    with get_conn() as conn:
        total_words = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        total_sentences = conn.execute("SELECT COUNT(*) FROM sentences").fetchone()[0]
        total_opic = conn.execute("SELECT COUNT(*) FROM opic_answers").fetchone()[0]
        total_toeic = conn.execute("SELECT COUNT(*) FROM toeic_quiz_log").fetchone()[0]
        study_dates = [r[0] for r in conn.execute(
            """
            SELECT date FROM (
                SELECT date FROM words
                UNION SELECT date FROM sentences
                UNION SELECT date FROM opic_answers
                UNION SELECT date FROM toeic_quiz_log
            ) ORDER BY date DESC
            """
        ).fetchall()]

    total_days = len(study_dates)
    streak = _calc_streak(study_dates)
    return {
        "total_words": total_words,
        "total_sentences": total_sentences,
        "total_opic": total_opic,
        "total_toeic": total_toeic,
        "total_days": total_days,
        "streak": streak,
    }


def _calc_streak(study_dates):
    """오늘(또는 어제)부터 며칠 연속으로 공부했는지 계산."""
    if not study_dates:
        return 0
    dateset = set(study_dates)
    today = datetime.now().date()
    # 오늘 안 했으면 어제부터 카운트 (오늘 끊긴 게 아니라 진행 중일 수 있으므로)
    start = today if today.strftime("%Y-%m-%d") in dateset else today - timedelta(days=1)
    streak = 0
    cur = start
    while cur.strftime("%Y-%m-%d") in dateset:
        streak += 1
        cur -= timedelta(days=1)
    return streak


def get_review_items(kind="words", limit=100):
    """복습(플래시카드)용 항목.

    반환 형식 통일: [{front(한글), back(영어), extra(보조설명)}, ...]
    """
    with get_conn() as conn:
        if kind == "sentences":
            rows = conn.execute(
                "SELECT meaning, corrected, feedback FROM sentences ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "front": r["meaning"] or "(한글 뜻 없음 — 영어를 보고 떠올려보세요)",
                    "back": r["corrected"],
                    "extra": r["feedback"],
                }
                for r in rows
            ]
        else:
            rows = conn.execute(
                "SELECT word, meaning, pronunciation, example, example_kr FROM words ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {
                    "front": r["meaning"],
                    "back": r["word"],
                    "extra": (r["pronunciation"] + "  ·  " if r["pronunciation"] else "")
                             + (r["example"] or ""),
                }
                for r in rows
            ]


# ---------------------------------------------------------------------------
# 단어 퀴즈 + 간격 반복(SRS)
# ---------------------------------------------------------------------------
def get_due_words(limit=20):
    """오늘 복습할 단어(next_review <= 오늘)를 반환한다.

    오래 안 본 것(박스 낮고 기한 지난 것)부터 우선.
    """
    today = today_str()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, word, meaning, pronunciation, example, example_kr, box, next_review
            FROM words
            WHERE next_review <= ?
            ORDER BY box ASC, next_review ASC
            LIMIT ?
            """,
            (today, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def count_due_words():
    """오늘 복습 대상 단어 수."""
    today = today_str()
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM words WHERE next_review <= ?", (today,)
        ).fetchone()[0]


# 객관식 보기 보충용 기본 오답 풀 (저장 단어가 적을 때 사용)
_DISTRACTOR_POOL = [
    "improve", "schedule", "available", "decision", "experience", "recommend",
    "invoice", "quarterly", "reimburse", "comply", "merger", "warranty",
    "postpone", "routine", "reserve", "travel", "order", "budget",
]


def get_distractors(word_id, count=3):
    """객관식 퀴즈용 오답 보기.

    다른 저장 단어에서 무작위로 뽑고, 부족하면 내장 풀에서 보충한다.
    정답 단어와 겹치지 않는 서로 다른 단어 count개를 반환한다.
    """
    with get_conn() as conn:
        answer_row = conn.execute(
            "SELECT word FROM words WHERE id=?", (int(word_id),)
        ).fetchone()
        answer = (answer_row["word"] if answer_row else "").strip().lower()
        rows = conn.execute(
            "SELECT DISTINCT word FROM words WHERE id != ? ORDER BY RANDOM() LIMIT ?",
            (int(word_id), count * 2),
        ).fetchall()

    picked = []
    seen = {answer}
    for r in rows:
        w = r["word"].strip()
        if w.lower() not in seen:
            picked.append(w)
            seen.add(w.lower())
        if len(picked) >= count:
            return picked

    pool = [w for w in _DISTRACTOR_POOL if w.lower() not in seen]
    random.shuffle(pool)
    for w in pool:
        picked.append(w)
        if len(picked) >= count:
            break
    return picked


def update_word_review(word_id, correct):
    """퀴즈 결과로 단어의 박스/다음 복습일을 갱신한다.

    맞으면 박스를 올려 복습 간격을 늘리고,
    틀리면 박스를 1로 되돌려 오늘 다시 복습 대상으로 만든다.
    반환: {box, next_review}
    """
    today = datetime.now().date()
    with get_conn() as conn:
        row = conn.execute("SELECT box FROM words WHERE id=?", (word_id,)).fetchone()
        if row is None:
            raise ValueError("단어를 찾을 수 없습니다.")
        box = row["box"] or 1

        if correct:
            box = min(5, box + 1)
            next_review = today + timedelta(days=SRS_INTERVALS[box])
        else:
            box = 1
            next_review = today  # 오늘 다시 복습

        next_str = next_review.strftime("%Y-%m-%d")
        conn.execute(
            "UPDATE words SET box=?, next_review=? WHERE id=?",
            (box, next_str, word_id),
        )
    return {"box": box, "next_review": next_str}


# ---------------------------------------------------------------------------
# 단어장 — 일괄 적재해 두고 매일 조금씩 학습 목록으로 가져온다
# ---------------------------------------------------------------------------
def import_wordbook(entries):
    """단어장에 단어들을 적재한다. 이미 있는 단어(대소문자 무시)는 건너뛰고,
    새로 넣은 개수를 반환한다.

    entries: [{word, meaning, example?, example_kr?}, ...]
    """
    inserted = 0
    with get_conn() as conn:
        for e in entries:
            word = (e.get("word") or "").strip()
            meaning = " ".join((e.get("meaning") or "").split())
            if not word or not meaning:
                continue
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO wordbook (word, meaning, example, example_kr)
                VALUES (?, ?, ?, ?)
                """,
                (word, meaning, (e.get("example") or "").strip(),
                 (e.get("example_kr") or "").strip()),
            )
            inserted += cur.rowcount
    return inserted


def wordbook_stats():
    """단어장 현황 {total, added, remaining}."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM wordbook").fetchone()[0]
        added = conn.execute("SELECT COUNT(*) FROM wordbook WHERE added=1").fetchone()[0]
    return {"total": total, "added": added, "remaining": total - added}


def pull_wordbook(count=10):
    """단어장에서 아직 안 가져온 단어 count개를 학습 목록(words, vocab 모드)으로 옮긴다.

    이미 words 에 저장된 단어는 건너뛰되 소진(added=1) 처리해서 다시 나오지 않게 한다.
    반환: 새로 저장된 단어 dict 목록 (id 포함).
    """
    count = int(max(1, min(50, count)))
    today = today_str()
    pulled = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM wordbook WHERE added=0 ORDER BY id ASC", ()
        ).fetchall()

    for row in rows:
        if len(pulled) >= count:
            break
        entry = dict(row)
        with get_conn() as conn:
            conn.execute(
                "UPDATE wordbook SET added=1, added_at=? WHERE id=?",
                (today, entry["id"]),
            )
        if find_word(entry["word"]):
            continue  # 이미 학습 목록에 있음 — 소진만 하고 건너뜀
        wid = add_word(
            word=entry["word"], meaning=entry["meaning"],
            example=entry["example"], example_kr=entry["example_kr"],
            mode="vocab",
        )
        pulled.append({
            "id": wid, "word": entry["word"], "meaning": entry["meaning"],
            "pronunciation": "",
            "example": entry["example"], "example_kr": entry["example_kr"],
        })
    return pulled


# ---------------------------------------------------------------------------
# 토익 오답 노트
# ---------------------------------------------------------------------------
def get_wrong_toeic(limit=20):
    """다시 풀어볼 토익 오답 문제.

    틀린 기록이 있는 문제 중, 이후에 정답 기록이 없는 것만 반환한다.
    (다시 풀어서 맞히면 목록에서 자연히 빠진다)
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM toeic_quiz_log
            WHERE is_correct = 0
              AND question NOT IN (
                  SELECT question FROM toeic_quiz_log WHERE is_correct = 1
              )
            GROUP BY question
            ORDER BY MAX(id) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {**dict(r), "choices": json.loads(r["choices"])}
            for r in rows
        ]
