"""
app.py — Flask 서버 진입점

계정
  GET/POST /login, /signup     : 로그인 / 가입 (INVITE_CODE 를 정하면 가입에 초대 코드 필요)
  POST     /logout             : 로그아웃
  GET/POST /account            : 하루 목표 · 목표 점수 · 비밀번호 변경

화면 (로그인 필요)
  /            : 홈 — 오늘 할 일(목표·진행률) + 연속 학습 + 주간 활동
  /vocab       : 단어 암기 (직접 추가·AI 추천·단어장)
  /toeic       : TOEIC — 오늘의 단어 · Part 5 (유형·난이도별) · 오답 복습
  /toeic/test  : 미니 모의고사 (시간 제한)
  /opic        : OPIC — 주제별 질문 은행 + 답변 틀·표현 + 첨삭
  /talk        : 회화 (문장 첨삭 + AI 프리토킹)
  /quiz        : 단어 복습 퀴즈 (간격 반복)
  /review      : 플래시카드
  /history     : 약점 분석 + 모의고사 결과 + 날짜별 기록

API (JSON, 로그인 필요) — 주요 항목
  POST /api/word, DELETE /api/word/<id>, POST /api/wordbook/pull, POST /api/recommend-words
  POST /api/sentence, POST /api/chat
  POST /api/vocab/daily        : 목표 수준의 새 토익 어휘를 오늘 단어로 담기
  POST /api/toeic/words        : 토익 어휘 추천 (아직 안 외운 것)
  POST /api/toeic/question     : Part 5 문제 (유형·난이도 필터, 안 푼 문제 우선)
  POST /api/toeic/answer       : 풀이 저장 (틀리면 오답 복습 큐로)
  GET  /api/toeic/review       : 오늘 복습할 오답
  GET  /api/toeic/wrong        : (예전) 다시 풀 오답 목록
  GET  /api/toeic/test         : 모의고사 문제 (정답 없이)
  POST /api/toeic/test         : 모의고사 채점 + 저장
  POST /api/opic/question, POST /api/opic/answer
  GET  /api/review, GET /api/quiz, POST /api/quiz/answer

실행:  python app.py  (기본 http://127.0.0.1:5000)
배포:  gunicorn app:app  (Procfile / Dockerfile 참고)
"""

import hmac
import os
import random
import re
import secrets
import socket
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import ai_feedback
import content
import db

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024
if os.path.dirname(db.DB_PATH):
    os.makedirs(os.path.dirname(db.DB_PATH), exist_ok=True)


def _secret_key():
    """세션 서명 키. SECRET_KEY 가 없으면 DB 옆 파일에 한 번 만들어 두고 같이 쓴다.

    (실행마다 새로 만들면 재시작할 때마다 로그아웃되고, gunicorn worker 끼리 키가 달라 로그인이 풀린다.)
    """
    env = os.getenv("SECRET_KEY", "").strip()
    if env:
        return env
    path = os.path.join(os.path.dirname(os.path.abspath(db.DB_PATH)), ".secret_key")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    except OSError:
        return secrets.token_hex(32)
    for _ in range(20):  # 다른 worker 가 막 만든 파일이면 내용이 써질 때까지 잠깐 기다린다
        with open(path) as f:
            key = f.read().strip()
        if key:
            return key
        time.sleep(0.05)
    return secrets.token_hex(32)


app.config.update(
    SECRET_KEY=_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)
db.init_db()


# ---------------------------------------------------------------------------
# 접근 보호
#   1) APP_PASSWORD (선택): 사이트 전체에 브라우저 비밀번호 창을 한 겹 더 건다.
#   2) 계정 로그인: 학습 기록은 사람마다 따로 저장된다.
# ---------------------------------------------------------------------------
PUBLIC_PATHS = ("/healthz", "/static/", "/favicon.ico")
AUTH_PATHS = ("/login", "/signup")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_가-힣]{2,20}$")
MIN_PASSWORD = 8
MAX_PASSWORD = 128

# 로그인 실패 제한 (worker 별 메모리) — IP 당 10분에 10번
_LOGIN_FAILS = {}
LOGIN_WINDOW = 600
LOGIN_MAX_FAILS = 10


def hash_password(password):
    """pbkdf2-sha256 — 어느 파이썬/OpenSSL 에서도 동작한다 (scrypt 는 일부 환경에 없음)."""
    return generate_password_hash(password, method="pbkdf2:sha256:600000")


def _client_ip():
    return request.remote_addr or "?"


def _login_blocked():
    now = time.time()
    fails = [t for t in _LOGIN_FAILS.get(_client_ip(), []) if now - t < LOGIN_WINDOW]
    _LOGIN_FAILS[_client_ip()] = fails
    return len(fails) >= LOGIN_MAX_FAILS


def _note_login_fail():
    _LOGIN_FAILS.setdefault(_client_ip(), []).append(time.time())


def _csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def _check_csrf():
    sent = request.form.get("csrf", "")
    if not sent or not hmac.compare_digest(sent, session.get("csrf", "")):
        abort(400)


def _safe_next(target):
    """로그인 후 돌아갈 주소 — 같은 사이트 경로만 허용."""
    if not target:
        return "/"
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return "/"
    return target


@app.before_request
def guard():
    password = os.getenv("APP_PASSWORD", "")
    if password and not request.path.startswith(PUBLIC_PATHS):
        auth = request.authorization
        if not (auth and hmac.compare_digest((auth.password or "").encode(), password.encode())):
            return Response(
                "비밀번호가 필요합니다.", 401,
                {"WWW-Authenticate": 'Basic realm="English World", charset="UTF-8"'},
            )

    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = db.get_user(uid)
        if g.user is None:
            session.pop("uid", None)

    if request.path.startswith(PUBLIC_PATHS) or request.path.startswith(AUTH_PATHS):
        return None
    if g.user is None:
        if request.path.startswith("/api/"):
            return jsonify({"error": "로그인이 필요해요. 페이지를 새로고침해 주세요."}), 401
        return redirect(url_for("login", next=request.full_path.rstrip("?")))

    # 다른 사이트가 몰래 보내는 요청 차단: 상태를 바꾸는 API 는 JSON 으로만 받는다
    # (브라우저는 다른 사이트에서 JSON 요청을 보낼 때 사전 확인을 거치므로 막힌다)
    if request.path.startswith("/api/") and request.method == "POST" and not request.is_json:
        return jsonify({"error": "JSON 형식으로 보내 주세요."}), 415
    if request.method == "POST" and not request.path.startswith("/api/"):
        _check_csrf()
    return None


def uid():
    return g.user["id"]


@app.context_processor
def inject_globals():
    return {"current_user": getattr(g, "user", None), "csrf_token": _csrf_token}


@app.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="icons/icon-192.png"), code=301)


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# 계정
# ---------------------------------------------------------------------------
def _invite_code():
    return os.getenv("INVITE_CODE", "").strip()


def _login_user(user):
    session.clear()
    session.permanent = True
    session["uid"] = user["id"]
    _csrf_token()


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect("/")
    next_url = _safe_next(request.values.get("next"))
    error = None
    username = ""
    if request.method == "POST":
        _check_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if _login_blocked():
            error = "로그인 시도가 너무 많아요. 10분 뒤에 다시 시도해 주세요."
        else:
            user = db.get_user_by_name(username) if username else None
            if user and check_password_hash(user["password_hash"], password):
                _login_user(user)
                return redirect(next_url)
            _note_login_fail()
            error = "아이디 또는 비밀번호가 맞지 않아요."
    return render_template("login.html", error=error, username=username, next_url=next_url,
                           first_run=db.count_users() == 0), (400 if error else 200)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user:
        return redirect("/")
    need_invite = bool(_invite_code())
    error = None
    form = {"username": ""}
    if request.method == "POST":
        _check_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("password2", "")
        form["username"] = username
        if need_invite and not hmac.compare_digest(request.form.get("invite", "").strip().encode(),
                                                   _invite_code().encode()):
            error = "초대 코드가 맞지 않아요. 앱을 소개한 친구에게 물어보세요."
        elif not USERNAME_RE.match(username):
            error = "아이디는 한글·영문·숫자·밑줄(_)로 2~20자로 정해 주세요."
        elif len(password) < MIN_PASSWORD or len(password) > MAX_PASSWORD:
            error = f"비밀번호는 {MIN_PASSWORD}자 이상으로 정해 주세요."
        elif password != confirm:
            error = "비밀번호 확인이 일치하지 않아요."
        else:
            try:
                new_id = db.create_user(username, hash_password(password),
                                        owner_username=os.getenv("OWNER_USERNAME", "").strip() or None)
            except ValueError as e:
                error = str(e)
            else:
                _login_user(db.get_user(new_id))
                flash("가입을 환영해요. 오늘 할 일부터 시작해 볼까요?")
                return redirect("/")
    counts = {"vocab": len(content.vocab()), "p5": len(content.part5()),
              "opic": sum(len(t["questions"]) for t in content.opic_topics())}
    return render_template("signup.html", error=error, form=form, need_invite=need_invite,
                           counts=counts), (400 if error else 200)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


GOAL_LIMITS = {"goal_words": (0, 50), "goal_p5": (0, 100), "goal_opic": (0, 10)}


@app.route("/account", methods=["GET", "POST"])
def account():
    error = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "goals":
            values = {}
            for key, (lo, hi) in GOAL_LIMITS.items():
                v = _to_int(request.form.get(key))
                if v is None or not lo <= v <= hi:
                    error = f"목표는 {lo}~{hi} 사이 숫자로 입력해 주세요."
                    break
                values[key] = v
            level = request.form.get("target_level", "800")
            if level not in content.VOCAB_LEVELS:
                error = "목표 점수대를 다시 골라 주세요."
            if not error:
                db.update_goals(uid(), target_level=level, **values)
                flash("목표를 저장했어요.")
                return redirect(url_for("account"))
        elif action == "password":
            current = request.form.get("current", "")
            new = request.form.get("new", "")
            if not check_password_hash(g.user["password_hash"], current):
                error = "현재 비밀번호가 맞지 않아요."
            elif len(new) < MIN_PASSWORD or len(new) > MAX_PASSWORD:
                error = f"새 비밀번호는 {MIN_PASSWORD}자 이상으로 정해 주세요."
            elif new != request.form.get("new2", ""):
                error = "새 비밀번호 확인이 일치하지 않아요."
            else:
                db.update_password(uid(), hash_password(new))
                flash("비밀번호를 바꿨어요.")
                return redirect(url_for("account"))
        else:
            error = "알 수 없는 요청이에요."
    return render_template("account.html", user=db.get_user(uid()), error=error,
                           stats=db.get_stats(uid=uid())), (400 if error else 200)


# ---------------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------------
WORDS_GOAL = 5          # 추천 단어 개수
SENTENCES_GOAL = 3      # 회화 모드 하루 문장 목표

MAX_WORD_LEN = 60
MAX_SENTENCE_LEN = 500
MAX_ANSWER_LEN = 3000
TEST_SECONDS_PER_Q = 24  # 실제 Part 5 권장 풀이 속도에 맞춘 문제당 제한 시간


def _bad_request(message):
    return jsonify({"error": message}), 400


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ai_context():
    return {
        "using_real_ai": ai_feedback.is_using_real_ai(),
        "provider_label": ai_feedback.current_provider_label(),
    }


def _greeting(hour):
    if 5 <= hour < 12:
        return "좋은 아침이에요"
    if 12 <= hour < 18:
        return "좋은 오후예요"
    if 18 <= hour < 23:
        return "오늘 하루도 수고했어요"
    return "늦은 시간까지 열공 중이네요"


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    now = datetime.now()
    week = db.get_week_activity(uid=uid())
    weakness = db.get_weakness(uid=uid())
    weak = [c for c in weakness["categories"] if c["rate"] is not None and c["total"] >= 3][:3]
    return render_template(
        "home.html",
        plan=db.get_today_plan(uid=uid()),
        summary=db.get_today_mode_summary(uid=uid()),
        today_total=week[-1]["count"],
        week=week,
        week_max=max([d["count"] for d in week] + [1]),
        stats=db.get_stats(uid=uid()),
        weak=weak,
        greeting=_greeting(now.hour),
        today_label=f"{now.month}월 {now.day}일 {'월화수목금토일'[now.weekday()]}요일",
        due_count=db.count_due_words(uid=uid()),
        **_ai_context(),
    )


@app.route("/vocab")
def vocab():
    return render_template(
        "vocab.html",
        items=db.get_today_items(mode="vocab", uid=uid()),
        due_count=db.count_due_words(uid=uid()),
        wordbook=db.wordbook_stats(uid=uid()),
        **_ai_context(),
    )


@app.route("/toeic")
def toeic():
    user = g.user
    weakness = db.get_weakness(uid=uid())
    return render_template(
        "toeic.html",
        items=db.get_today_items(mode="toeic", uid=uid()),
        categories=weakness["categories"],
        category_order=content.P5_CATEGORIES,
        level_label=content.P5_LEVEL_LABEL,
        vocab_progress=db.vocab_progress(uid=uid()),
        p5_progress=db.p5_progress(uid=uid()),
        due_p5=db.count_due_p5(uid=uid()),
        target_level=user["target_level"],
        goal_words=user["goal_words"],
        start_review=request.args.get("review") == "1",
        start_category=request.args.get("cat", "") if request.args.get("cat") in content.P5_CATEGORIES else "",
        **_ai_context(),
    )


@app.route("/toeic/test")
def toeic_test():
    return render_template("test.html", tests=db.get_mock_tests(uid=uid(), limit=5),
                           seconds_per_q=TEST_SECONDS_PER_Q)


@app.route("/opic")
def opic():
    return render_template("opic.html", topics=content.opic_topics(), kinds=content.OPIC_KINDS,
                           **_ai_context())


@app.route("/talk")
def talk():
    return render_template(
        "talk.html",
        counts=db.get_today_counts(mode="talk", uid=uid()),
        items=db.get_today_items(mode="talk", uid=uid()),
        words_goal=WORDS_GOAL,
        sentences_goal=SENTENCES_GOAL,
        today=db.today_str(),
        **_ai_context(),
    )


@app.route("/chat")
def chat_redirect():
    return redirect("/talk")


@app.route("/history")
def history():
    return render_template(
        "history.html",
        history=db.get_history(limit_days=60, uid=uid()),
        stats=db.get_stats(uid=uid()),
        weakness=db.get_weakness(uid=uid()),
        tests=db.get_mock_tests(uid=uid(), limit=10),
    )


@app.route("/review")
def review():
    return render_template("review.html")


@app.route("/quiz")
def quiz():
    return render_template("quiz.html", due_count=db.count_due_words(uid=uid()))


# ---------------------------------------------------------------------------
# 단어 / 문장
# ---------------------------------------------------------------------------
@app.route("/api/word", methods=["POST"])
def api_word():
    data = request.get_json(silent=True) or {}
    word = str(data.get("word") or "").strip()
    mode = db._clean_mode(str(data.get("mode") or "talk").strip())
    if not word:
        return _bad_request("단어를 입력해 주세요.")
    if len(word) > MAX_WORD_LEN:
        return _bad_request(f"단어(구)는 {MAX_WORD_LEN}자 이내로 입력해 주세요.")

    existing = db.find_word(word, uid=uid())
    if existing:
        return jsonify({
            "duplicate": True,
            "error": f"'{existing['word']}'는 {existing['date']}에 이미 저장한 단어예요.",
            "id": existing["id"],
        }), 409

    source_id = str(data.get("id") or "") if str(data.get("id") or "") in content.vocab_by_id() else ""
    if source_id:
        # 토익 어휘 은행 단어는 은행 내용을 그대로 쓴다
        bank = content.vocab_by_id()[source_id]
        analysis = {"meaning": bank["meaning"], "pronunciation": "", "example": bank["example"],
                    "example_kr": bank["example_kr"], "pos": bank["pos"]}
    elif data.get("meaning"):
        analysis = {
            "meaning": str(data.get("meaning", ""))[:200],
            "pronunciation": str(data.get("pronunciation", ""))[:80],
            "example": str(data.get("example", ""))[:MAX_SENTENCE_LEN],
            "example_kr": str(data.get("example_kr", ""))[:MAX_SENTENCE_LEN],
        }
    else:
        try:
            analysis = ai_feedback.explain_word(word)
        except Exception as e:
            return jsonify({"error": f"단어 분석 중 오류: {e}"}), 500

    try:
        word_id = db.add_word(
            word=word, meaning=analysis["meaning"], pronunciation=analysis.get("pronunciation", ""),
            example=analysis.get("example", ""), example_kr=analysis.get("example_kr", ""),
            mode=mode, pos=analysis.get("pos", ""), source_id=source_id, uid=uid(),
        )
    except Exception as e:
        return jsonify({"error": f"단어 저장에 실패했습니다: {e}"}), 500

    return jsonify({"id": word_id, "word": word, **analysis,
                    "counts": db.get_today_counts(mode=mode, uid=uid())})


@app.route("/api/word/<int:word_id>", methods=["DELETE"])
def api_delete_word(word_id):
    try:
        deleted = db.delete_word(word_id, uid=uid())
    except Exception as e:
        return jsonify({"error": f"삭제에 실패했습니다: {e}"}), 500
    if not deleted:
        return jsonify({"error": "해당 단어를 찾을 수 없습니다."}), 404
    return jsonify({"id": word_id, "deleted": True})


@app.route("/api/wordbook/pull", methods=["POST"])
def api_wordbook_pull():
    data = request.get_json(silent=True) or {}
    count = _to_int(data.get("count") or 10)
    if count is None or count < 1:
        return _bad_request("가져올 단어 수가 올바르지 않습니다.")
    try:
        pulled = db.pull_wordbook(count, uid=uid())
    except Exception as e:
        return jsonify({"error": f"단어장에서 가져오지 못했습니다: {e}"}), 500
    return jsonify({"pulled": pulled, "stats": db.wordbook_stats(uid=uid()),
                    "due_count": db.count_due_words(uid=uid())})


@app.route("/api/recommend-words", methods=["POST"])
def api_recommend_words():
    data = request.get_json(silent=True) or {}
    topic = str(data.get("topic") or "일상생활").strip()[:40] or "일상생활"
    try:
        words = ai_feedback.recommend_words(topic=topic, count=WORDS_GOAL)
    except Exception as e:
        return jsonify({"error": f"추천 중 오류: {e}"}), 500
    return jsonify({"topic": topic, "words": words, "fallback": ai_feedback.consume_fallback_flag()})


@app.route("/api/sentence", methods=["POST"])
def api_sentence():
    data = request.get_json(silent=True) or {}
    sentence = str(data.get("sentence") or "").strip()
    mode = db._clean_mode(str(data.get("mode") or "talk").strip())
    if not sentence:
        return _bad_request("문장을 입력해 주세요.")
    if len(sentence) > MAX_SENTENCE_LEN:
        return _bad_request(f"문장은 {MAX_SENTENCE_LEN}자 이내로 입력해 주세요.")
    try:
        result = ai_feedback.get_feedback(sentence)
    except Exception as e:
        return jsonify({"error": f"첨삭 중 오류: {e}"}), 500
    try:
        sid = db.add_sentence(original=sentence, corrected=result["corrected"], feedback=result["feedback"],
                              meaning=result.get("meaning", ""), score=result["score"], mode=mode, uid=uid())
    except Exception as e:
        return jsonify({"error": f"문장 저장에 실패했습니다: {e}"}), 500
    return jsonify({"id": sid, "original": sentence, **result,
                    "counts": db.get_today_counts(mode=mode, uid=uid())})


# ---------------------------------------------------------------------------
# TOEIC
# ---------------------------------------------------------------------------
def _level(value):
    value = str(value or "").strip()
    return value if value in content.VOCAB_LEVELS else g.user["target_level"]


def _bank_word(w):
    return {"id": w["id"], "word": w["word"], "pos": w["pos"], "meaning": w["meaning"], "pronunciation": "",
            "example": w["example"], "example_kr": w["example_kr"], "level": w["level"], "topic": w["topic"]}


@app.route("/api/toeic/words", methods=["POST"])
def api_toeic_words():
    """아직 외우지 않은 토익 어휘 추천 (미리보기 — 담으면 /api/word 로 저장)."""
    data = request.get_json(silent=True) or {}
    level = _level(data.get("level"))
    words = [_bank_word(w) for w in db.unseen_vocab(level, WORDS_GOAL, uid=uid(), shuffle=True)]
    return jsonify({"level": level, "words": words, "fallback": False,
                    "progress": db.vocab_progress(uid=uid())[level]})


@app.route("/api/vocab/daily", methods=["POST"])
def api_vocab_daily():
    """오늘의 단어 — 목표 수준의 새 어휘를 순서대로 담는다."""
    data = request.get_json(silent=True) or {}
    level = _level(data.get("level"))
    count = _to_int(data["count"]) if "count" in data else (g.user["goal_words"] or 10)
    if count is None or not 1 <= count <= 50:
        return _bad_request("담을 단어 수는 1~50 사이로 정해 주세요.")
    added = db.add_bank_words(level, count, uid=uid())
    return jsonify({"level": level, "added": added, "progress": db.vocab_progress(uid=uid())[level],
                    "due_count": db.count_due_words(uid=uid())})


def _with_meta(q):
    return {**q, "level_label": content.P5_LEVEL_LABEL.get(q.get("level"), "")}


@app.route("/api/toeic/question", methods=["POST"])
def api_toeic_question():
    """Part 5 문제 1개. 기본은 문제 은행(안 푼 문제 우선), ai=true 이고 AI 키가 있으면 새로 생성."""
    data = request.get_json(silent=True) or {}
    category = str(data.get("category") or "").strip()
    level = str(data.get("level") or "").strip()
    if category and category not in content.P5_CATEGORIES:
        return _bad_request("알 수 없는 문제 유형입니다.")
    if level and level not in content.P5_LEVEL_LABEL:
        return _bad_request("알 수 없는 난이도입니다.")
    recent = data.get("recent") or []
    if not isinstance(recent, list):
        recent = []
    recent = [str(q)[:300] for q in recent[-30:]]

    if data.get("ai") and ai_feedback.is_using_real_ai():
        try:
            q = ai_feedback.generate_part5_question(recent_questions=recent)
        except Exception as e:
            return jsonify({"error": f"문제 생성 중 오류: {e}"}), 500
        return jsonify({**q, "id": "", "category": "", "level": "", "source": "ai",
                        "fallback": ai_feedback.consume_fallback_flag()})

    picked = db.pick_p5(uid=uid(), category=category or None, level=level or None, exclude=set(recent))
    if not picked:  # 조건에 맞는 문제를 최근에 다 풀었으면 제외 목록 없이 다시
        picked = db.pick_p5(uid=uid(), category=category or None, level=level or None)
    if not picked:
        return jsonify({"error": "조건에 맞는 문제가 없어요."}), 404
    return jsonify({**_with_meta(picked[0]), "source": "bank", "fallback": False})


def _clean_answer_payload(data):
    """풀이 저장 요청을 검사한다. 은행 문제면 정답·해설은 서버 값을 쓴다. (payload, error)"""
    my_answer = _to_int(data.get("my_answer"))
    if my_answer not in range(4):
        return None, "문제 정보가 올바르지 않습니다."
    qid = str(data.get("id") or data.get("qid") or "")
    bank = content.part5_by_id().get(qid)
    if bank:
        return {"question": bank["question"], "choices": bank["choices"], "correct_answer": bank["answer"],
                "explanation": bank["explanation"], "qid": qid, "category": bank["category"],
                "my_answer": my_answer}, None
    question = str(data.get("question") or "").strip()[:1000]
    choices = data.get("choices") or []
    correct_answer = _to_int(data.get("correct_answer"))
    if not question or not isinstance(choices, list) or len(choices) != 4 or correct_answer not in range(4):
        return None, "문제 정보가 올바르지 않습니다."
    return {"question": question, "choices": [str(c)[:200] for c in choices], "correct_answer": correct_answer,
            "explanation": str(data.get("explanation") or "").strip()[:2000], "qid": "", "category": "",
            "my_answer": my_answer}, None


@app.route("/api/toeic/answer", methods=["POST"])
def api_toeic_answer():
    data = request.get_json(silent=True) or {}
    p, err = _clean_answer_payload(data)
    if err:
        return _bad_request(err)
    source = data.get("source") if data.get("source") in ("practice", "review") else "practice"
    is_correct = p["my_answer"] == p["correct_answer"]
    try:
        qid = db.add_toeic_quiz(
            question=p["question"], choices=p["choices"], my_answer=p["my_answer"],
            correct_answer=p["correct_answer"], explanation=p["explanation"], is_correct=is_correct,
            qid=p["qid"], category=p["category"], source=source, uid=uid(),
        )
    except Exception as e:
        return jsonify({"error": f"풀이 저장에 실패했습니다: {e}"}), 500
    return jsonify({"id": qid, "is_correct": is_correct, "correct_answer": p["correct_answer"],
                    "due_p5": db.count_due_p5(uid=uid()), "p5_solved": db.p5_progress(uid=uid())["solved"]})


@app.route("/api/toeic/review")
def api_toeic_review():
    return jsonify({"questions": [_with_meta(q) for q in db.get_due_p5(uid=uid(), limit=20)]})


@app.route("/api/toeic/wrong")
def api_toeic_wrong():
    return jsonify({"questions": db.get_wrong_toeic(limit=20, uid=uid())})


@app.route("/api/toeic/test", methods=["GET"])
def api_toeic_test_questions():
    """모의고사 문제 — 유형이 고르게 섞이도록 뽑고, 정답·해설은 보내지 않는다."""
    count = _to_int(request.args.get("count")) or 10
    if count not in (10, 20, 30):
        return _bad_request("문제 수는 10, 20, 30 중에서 골라 주세요.")
    per_cat = max(1, count // len(content.P5_CATEGORIES))
    picked = []
    for cat in content.P5_CATEGORIES:
        picked += db.pick_p5(uid=uid(), category=cat, count=per_cat)
    if len(picked) < count:
        picked += db.pick_p5(uid=uid(), exclude={q["id"] for q in picked}, count=count - len(picked))
    random.shuffle(picked)
    return jsonify({"questions": [content.public_question(q) for q in picked[:count]],
                    "limit_sec": count * TEST_SECONDS_PER_Q})


@app.route("/api/toeic/test", methods=["POST"])
def api_toeic_test_submit():
    data = request.get_json(silent=True) or {}
    answers = data.get("answers")
    if not isinstance(answers, list) or not 1 <= len(answers) <= 30:
        return _bad_request("답안 형식이 올바르지 않습니다.")
    bank = content.part5_by_id()
    results, seen = [], set()
    for a in answers:
        if not isinstance(a, dict):
            return _bad_request("답안 형식이 올바르지 않습니다.")
        qid = str(a.get("id") or "")
        q = bank.get(qid)
        if not q or qid in seen:
            return _bad_request("알 수 없는 문제가 섞여 있습니다.")
        seen.add(qid)
        choice = _to_int(a.get("choice"))
        choice = choice if choice in range(4) else None
        results.append({"q": q, "choice": choice})

    seconds = max(0, min(_to_int(data.get("seconds")) or 0, 3600))
    limit_sec = len(results) * TEST_SECONDS_PER_Q
    detail, correct, out = {}, 0, []
    for r in results:
        q, choice = r["q"], r["choice"]
        ok = choice == q["answer"]
        correct += ok
        d = detail.setdefault(q["category"], [0, 0])
        d[0] += 1
        d[1] += 1 if ok else 0
        # 안 푼 문제는 틀린 것으로 기록 (복습 큐에 들어간다). 기록상 내 답은 정답이 아닌 보기로 남긴다.
        db.add_toeic_quiz(question=q["question"], choices=q["choices"],
                          my_answer=choice if choice is not None else (q["answer"] + 1) % 4,
                          correct_answer=q["answer"], explanation=q["explanation"], is_correct=ok,
                          qid=q["id"], category=q["category"], source="test", uid=uid())
        out.append({**_with_meta(q), "choice": choice, "is_correct": ok})
    test_id = db.add_mock_test(len(results), correct, seconds, limit_sec, detail, uid=uid())
    return jsonify({"id": test_id, "total": len(results), "correct": correct, "seconds": seconds,
                    "limit_sec": limit_sec, "results": out,
                    "by_category": [{"category": k, "total": v[0], "correct": v[1]} for k, v in detail.items()]})


# ---------------------------------------------------------------------------
# OPIC
# ---------------------------------------------------------------------------
def _topic_guide(t):
    return {"template": t["template"], "expressions": t["expressions"], "sample": t["sample"],
            "sample_question": t["questions"][0]["q"], "kind": t["kind"], "topic_id": t["id"]}


@app.route("/api/opic/question", methods=["POST"])
def api_opic_question():
    """오픽 질문 — 질문 은행에서 최근에 안 받은 질문을 고른다. 은행에 없는 주제는 AI(또는 예비 질문)."""
    data = request.get_json(silent=True) or {}
    topic = str(data.get("topic") or "자기소개").strip()[:40] or "자기소개"
    recent = data.get("recent") if isinstance(data.get("recent"), list) else []
    t = content.opic_topic(topic)
    if t and not data.get("ai"):
        pool = [q for q in t["questions"] if q["id"] not in recent] or list(t["questions"])
        q = random.choice(pool)
        return jsonify({"topic": t["name"], "id": q["id"], "question": q["q"], "question_kr": q["q_kr"],
                        "type": q["type"], "tip": q["tip"], **_topic_guide(t), "fallback": False})
    try:
        q = ai_feedback.opic_question(topic)
    except Exception as e:
        return jsonify({"error": f"질문 생성 중 오류: {e}"}), 500
    extra = _topic_guide(t) if t else {}
    return jsonify({"topic": topic, **q, **extra, "fallback": ai_feedback.consume_fallback_flag()})


@app.route("/api/opic/answer", methods=["POST"])
def api_opic_answer():
    data = request.get_json(silent=True) or {}
    topic = str(data.get("topic") or "").strip()[:40]
    question = str(data.get("question") or "").strip()
    answer = str(data.get("answer") or "").strip()
    if not question or not answer:
        return _bad_request("질문과 답변이 모두 필요합니다.")
    if len(answer) > MAX_ANSWER_LEN or len(question) > 1000:
        return _bad_request(f"답변은 {MAX_ANSWER_LEN}자 이내로 입력해 주세요.")
    try:
        result = ai_feedback.opic_feedback(question, answer)
    except Exception as e:
        return jsonify({"error": f"첨삭 중 오류: {e}"}), 500

    # AI 가 모범답변을 못 줄 때(목업 모드)는 질문 은행의 예시 답변을 보여 준다
    t = content.opic_topic(topic)
    if not result.get("model_answer") and t and question == t["questions"][0]["q"]:
        result["model_answer"] = t["sample"]
    try:
        oid = db.add_opic_answer(topic=topic, question=question, answer=answer, corrected=result["corrected"],
                                 feedback=result["feedback"], model_answer=result.get("model_answer", ""),
                                 score=result["score"], uid=uid())
    except Exception as e:
        return jsonify({"error": f"답변 저장에 실패했습니다: {e}"}), 500
    words = len(answer.split())
    return jsonify({"id": oid, "answer": answer, "word_count": words, **result})


# ---------------------------------------------------------------------------
# 복습 / 퀴즈 / 챗봇
# ---------------------------------------------------------------------------
@app.route("/api/review")
def api_review():
    kind = request.args.get("kind", "words")
    if kind not in ("words", "sentences"):
        kind = "words"
    return jsonify({"kind": kind, "cards": db.get_review_items(kind, uid=uid())})


@app.route("/api/quiz")
def api_quiz():
    words = db.get_due_words(limit=20, uid=uid())
    for w in words:
        choices = db.get_distractors(w["id"], count=3, uid=uid()) + [w["word"]]
        random.shuffle(choices)
        w["choices"] = choices
    return jsonify({"words": words})


@app.route("/api/quiz/answer", methods=["POST"])
def api_quiz_answer():
    data = request.get_json(silent=True) or {}
    word_id = _to_int(data.get("id"))
    correct = bool(data.get("correct"))
    grade = _to_int(data.get("grade"))
    if word_id is None:
        return _bad_request("단어 id가 필요합니다.")
    if grade is not None and grade not in (0, 3, 4, 5):
        return _bad_request("grade 는 0, 3, 4, 5 중 하나입니다.")
    try:
        result = db.update_word_review(word_id, correct, grade=grade, uid=uid())
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"갱신 실패: {e}"}), 500
    return jsonify({"id": word_id, **result, "due_count": db.count_due_words(uid=uid())})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    history = data.get("history") or []
    topic = str(data.get("topic") or "").strip()[:40]
    if not isinstance(history, list):
        return _bad_request("대화 형식이 올바르지 않습니다.")
    history = [
        {"role": m.get("role"), "content": str(m.get("content", ""))[:MAX_SENTENCE_LEN]}
        for m in history[-12:] if isinstance(m, dict)
    ]
    if not history or not history[-1]["content"].strip():
        return _bad_request("메시지가 비어 있습니다.")
    try:
        reply = ai_feedback.chat_reply(history, topic)
    except Exception as e:
        return jsonify({"error": f"대화 생성 중 오류: {e}"}), 500
    return jsonify({"reply": reply})


# ---------------------------------------------------------------------------
# 오류 화면
# ---------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request_page(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "요청 형식이 올바르지 않습니다."}), 400
    return render_template("error.html", code=400,
                           message="요청이 만료됐거나 올바르지 않아요. 페이지를 새로고침한 뒤 다시 시도해 주세요."), 400


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "요청한 API 를 찾을 수 없습니다."}), 404
    return render_template("error.html", code=404,
                           message="찾으시는 페이지가 없어요. 주소를 다시 확인해 주세요."), 404


@app.errorhandler(405)
def method_not_allowed(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "허용되지 않는 요청 방식입니다."}), 405
    return render_template("error.html", code=405, message="이 주소는 그렇게 열 수 없어요."), 405


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "요청이 너무 큽니다."}), 413


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500
    return render_template("error.html", code=500,
                           message="잠시 문제가 생겼어요. 잠시 후 다시 시도해 주세요."), 500


def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # 실제 전송은 없음 — 라우팅 경로만 확인
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1" and host != "0.0.0.0"

    print()
    print("  [English World] 시작!")
    print(f"  PC에서 : http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        ip = _lan_ip()
        if ip:
            print(f"  폰에서 : http://{ip}:{port}  (같은 와이파이에서 접속)")
    print()

    app.run(host=host, port=port, debug=debug)
