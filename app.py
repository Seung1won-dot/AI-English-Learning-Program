"""
app.py — Flask 서버 진입점

화면
  GET  /          : 홈 — 학습 모드 선택 (TOEIC / OPIC / 회화) + 오늘 요약
  GET  /toeic     : TOEIC 모드 (빈출 단어 + Part 5 문제)
  GET  /opic      : OPIC 모드 (질문 → 타이핑/음성 답변 → AI 첨삭)
  GET  /talk      : 회화 모드 (단어 외우기 + 문장 첨삭 + AI 챗봇)
  GET  /history   : 날짜별 학습 기록 + 통계 (모드 필터)
  GET  /review    : 플래시카드 복습
  GET  /quiz      : SRS 단어 퀴즈

API (JSON)
  POST /api/word            : 단어 분석 + 저장 (mode 태그)
  POST /api/recommend-words : 오늘의 추천 단어 (저장 안 함, 미리보기)
  POST /api/sentence        : 회화 문장 첨삭 + 저장 (mode 태그)
  POST /api/toeic/words     : 토익 빈출 단어 추천 (저장 안 함)
  POST /api/toeic/question  : 토익 Part 5 문제 생성
  POST /api/toeic/answer    : Part 5 풀이 결과 저장
  POST /api/opic/question   : 오픽 질문 생성
  POST /api/opic/answer     : 오픽 답변 첨삭 + 저장
  GET  /api/review?kind=words|sentences : 복습 카드 데이터
  GET  /api/quiz            : 오늘 복습할 단어(SRS)
  POST /api/quiz/answer     : 퀴즈 채점 → 복습 일정 갱신
  POST /api/chat            : AI 회화 응답

실행:  python app.py  (기본 http://127.0.0.1:5000)
"""

import hmac
import os
import random
import socket
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, Response, render_template, request, jsonify, redirect

import db
import ai_feedback

load_dotenv()

app = Flask(__name__)
if os.path.dirname(db.DB_PATH):
    os.makedirs(os.path.dirname(db.DB_PATH), exist_ok=True)
db.init_db()


# ---------------------------------------------------------------------------
# 접근 보호 — APP_PASSWORD 를 설정하면 모든 화면/API 에 비밀번호가 걸린다.
# 인터넷에 배포할 때 필수: 없으면 누구나 내 기록을 바꾸고 AI 키를 쓸 수 있다.
# ---------------------------------------------------------------------------
PUBLIC_PATHS = ("/healthz", "/static/")


@app.before_request
def require_password():
    password = os.getenv("APP_PASSWORD", "")
    if not password or request.path.startswith(PUBLIC_PATHS):
        return None
    auth = request.authorization
    if auth and hmac.compare_digest((auth.password or "").encode(), password.encode()):
        return None
    return Response(
        "비밀번호가 필요합니다.", 401,
        {"WWW-Authenticate": 'Basic realm="English World", charset="UTF-8"'},
    )


@app.route("/healthz")
def healthz():
    """배포 플랫폼 헬스 체크용."""
    return jsonify({"ok": True})

# 하루 학습 목표 (회화 모드)
WORDS_GOAL = 5
SENTENCES_GOAL = 3


def _ai_context():
    """모든 화면에서 공통으로 쓰는 AI 상태 표시 값."""
    return {
        "using_real_ai": ai_feedback.is_using_real_ai(),
        "provider_label": ai_feedback.current_provider_label(),
    }


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------
def _greeting(hour):
    if 5 <= hour < 12:
        return "좋은 아침이에요"
    if 12 <= hour < 18:
        return "좋은 오후예요"
    if 18 <= hour < 23:
        return "오늘 하루도 수고했어요"
    return "늦은 시간까지 열공 중이네요"


@app.route("/")
def home():
    """홈 — 학습 모드 선택 + 오늘 학습 요약 + 주간 활동."""
    now = datetime.now()
    summary = db.get_today_mode_summary()
    week = db.get_week_activity()
    return render_template(
        "home.html",
        summary=summary,
        today_total=week[-1]["count"],
        week=week,
        week_max=max([d["count"] for d in week] + [1]),
        stats=db.get_stats(),
        greeting=_greeting(now.hour),
        today_label=f"{now.month}월 {now.day}일 {'월화수목금토일'[now.weekday()]}요일",
        due_count=db.count_due_words(),
        **_ai_context(),
    )


@app.route("/vocab")
def vocab():
    """단어 암기 모드 — 단어 추가/추천 + 단어장 + 오늘 단어 + 복습 현황."""
    return render_template(
        "vocab.html",
        items=db.get_today_items(mode="vocab"),
        due_count=db.count_due_words(),
        wordbook=db.wordbook_stats(),
        **_ai_context(),
    )


@app.route("/toeic")
def toeic():
    return render_template(
        "toeic.html",
        items=db.get_today_items(mode="toeic"),
        **_ai_context(),
    )


@app.route("/opic")
def opic():
    return render_template("opic.html", **_ai_context())


@app.route("/talk")
def talk():
    counts = db.get_today_counts(mode="talk")
    items = db.get_today_items(mode="talk")
    return render_template(
        "talk.html",
        counts=counts,
        items=items,
        words_goal=WORDS_GOAL,
        sentences_goal=SENTENCES_GOAL,
        today=db.today_str(),
        **_ai_context(),
    )


@app.route("/chat")
def chat_redirect():
    """예전 주소 호환 — 회화 모드로 통합되었다."""
    return redirect("/talk")


@app.route("/history")
def history():
    return render_template(
        "history.html",
        history=db.get_history(limit_days=60),
        stats=db.get_stats(),
    )


@app.route("/review")
def review():
    return render_template("review.html")


@app.route("/quiz")
def quiz():
    return render_template("quiz.html", due_count=db.count_due_words())


# ---------------------------------------------------------------------------
# 공용 API — 단어 / 문장 (mode 태그와 함께 저장)
# ---------------------------------------------------------------------------
@app.route("/api/word", methods=["POST"])
def api_word():
    """단어 분석 후 저장."""
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip()
    mode = (data.get("mode") or "talk").strip()
    if not word:
        return jsonify({"error": "단어를 입력해 주세요."}), 400

    # 같은 단어를 두 번 저장하지 않는다 (퀴즈에 중복 출제되는 것을 방지)
    existing = db.find_word(word)
    if existing:
        return jsonify({
            "duplicate": True,
            "error": f"'{existing['word']}'는 {existing['date']}에 이미 저장한 단어예요.",
            "id": existing["id"],
        }), 409

    # 분석에 필요한 값이 함께 오면 그대로 저장 (추천 단어를 담을 때),
    # 없으면 AI 로 분석한다.
    if data.get("meaning"):
        analysis = {
            "meaning": data.get("meaning", ""),
            "pronunciation": data.get("pronunciation", ""),
            "example": data.get("example", ""),
            "example_kr": data.get("example_kr", ""),
        }
    else:
        try:
            analysis = ai_feedback.explain_word(word)
        except Exception as e:
            return jsonify({"error": f"단어 분석 중 오류: {e}"}), 500

    try:
        word_id = db.add_word(
            word=word,
            meaning=analysis["meaning"],
            pronunciation=analysis.get("pronunciation", ""),
            example=analysis.get("example", ""),
            example_kr=analysis.get("example_kr", ""),
            mode=mode,
        )
    except Exception as e:
        return jsonify({"error": f"단어 저장에 실패했습니다: {e}"}), 500

    return jsonify({"id": word_id, "word": word, **analysis,
                    "counts": db.get_today_counts(mode=mode)})


@app.route("/api/word/<int:word_id>", methods=["DELETE"])
def api_delete_word(word_id):
    """단어 삭제 (오타·중복 정리용)."""
    try:
        deleted = db.delete_word(word_id)
    except Exception as e:
        return jsonify({"error": f"삭제에 실패했습니다: {e}"}), 500
    if not deleted:
        return jsonify({"error": "해당 단어를 찾을 수 없습니다."}), 404
    return jsonify({"id": word_id, "deleted": True})


@app.route("/api/wordbook/pull", methods=["POST"])
def api_wordbook_pull():
    """단어장에서 새 단어 N개를 오늘 학습 목록으로 가져온다."""
    data = request.get_json(silent=True) or {}
    count = data.get("count") or 10
    try:
        pulled = db.pull_wordbook(int(count))
    except Exception as e:
        return jsonify({"error": f"단어장에서 가져오지 못했습니다: {e}"}), 500
    return jsonify({
        "pulled": pulled,
        "stats": db.wordbook_stats(),
        "due_count": db.count_due_words(),
    })


@app.route("/api/recommend-words", methods=["POST"])
def api_recommend_words():
    """오늘의 추천 단어 (미리보기 — 저장은 사용자가 선택)."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "일상생활").strip()
    try:
        words = ai_feedback.recommend_words(topic=topic, count=WORDS_GOAL)
    except Exception as e:
        return jsonify({"error": f"추천 중 오류: {e}"}), 500
    return jsonify({"topic": topic, "words": words,
                    "fallback": ai_feedback.consume_fallback_flag()})


@app.route("/api/sentence", methods=["POST"])
def api_sentence():
    """회화 문장 첨삭 후 저장."""
    data = request.get_json(silent=True) or {}
    sentence = (data.get("sentence") or "").strip()
    mode = (data.get("mode") or "talk").strip()
    if not sentence:
        return jsonify({"error": "문장을 입력해 주세요."}), 400

    try:
        result = ai_feedback.get_feedback(sentence)
    except Exception as e:
        return jsonify({"error": f"첨삭 중 오류: {e}"}), 500

    try:
        sid = db.add_sentence(
            original=sentence,
            corrected=result["corrected"],
            feedback=result["feedback"],
            meaning=result.get("meaning", ""),
            score=result["score"],
            mode=mode,
        )
    except Exception as e:
        return jsonify({"error": f"문장 저장에 실패했습니다: {e}"}), 500

    return jsonify({"id": sid, "original": sentence, **result,
                    "counts": db.get_today_counts(mode=mode)})


# ---------------------------------------------------------------------------
# TOEIC API
# ---------------------------------------------------------------------------
@app.route("/api/toeic/words", methods=["POST"])
def api_toeic_words():
    """토익 빈출 단어 추천 (미리보기 — 담으면 /api/word 로 저장)."""
    data = request.get_json(silent=True) or {}
    level = str(data.get("level") or "600").strip()
    try:
        words = ai_feedback.recommend_toeic_words(level=level, count=WORDS_GOAL)
    except Exception as e:
        return jsonify({"error": f"추천 중 오류: {e}"}), 500
    return jsonify({"level": level, "words": words,
                    "fallback": ai_feedback.consume_fallback_flag()})


@app.route("/api/toeic/question", methods=["POST"])
def api_toeic_question():
    """토익 Part 5 문제 1개 생성."""
    data = request.get_json(silent=True) or {}
    recent = data.get("recent") or []  # 같은 문제 반복 방지용 최근 문제 목록
    try:
        q = ai_feedback.generate_part5_question(recent_questions=recent)
    except Exception as e:
        return jsonify({"error": f"문제 생성 중 오류: {e}"}), 500
    return jsonify({**q, "fallback": ai_feedback.consume_fallback_flag()})


@app.route("/api/toeic/answer", methods=["POST"])
def api_toeic_answer():
    """Part 5 풀이 결과를 날짜별 기록에 저장."""
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    choices = data.get("choices") or []
    my_answer = data.get("my_answer")
    correct_answer = data.get("correct_answer")
    if not question or len(choices) != 4 or my_answer is None or correct_answer is None:
        return jsonify({"error": "문제 정보가 올바르지 않습니다."}), 400

    is_correct = int(my_answer) == int(correct_answer)
    try:
        qid = db.add_toeic_quiz(
            question=question,
            choices=choices,
            my_answer=int(my_answer),
            correct_answer=int(correct_answer),
            explanation=(data.get("explanation") or "").strip(),
            is_correct=is_correct,
        )
    except Exception as e:
        return jsonify({"error": f"풀이 저장에 실패했습니다: {e}"}), 500
    return jsonify({"id": qid, "is_correct": is_correct})


@app.route("/api/toeic/wrong")
def api_toeic_wrong():
    """다시 풀어볼 토익 오답 문제 목록."""
    return jsonify({"questions": db.get_wrong_toeic(limit=20)})


# ---------------------------------------------------------------------------
# OPIC API
# ---------------------------------------------------------------------------
@app.route("/api/opic/question", methods=["POST"])
def api_opic_question():
    """오픽 주제별 질문 생성."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "자기소개").strip()
    try:
        q = ai_feedback.opic_question(topic)
    except Exception as e:
        return jsonify({"error": f"질문 생성 중 오류: {e}"}), 500
    return jsonify({"topic": topic, **q,
                    "fallback": ai_feedback.consume_fallback_flag()})


@app.route("/api/opic/answer", methods=["POST"])
def api_opic_answer():
    """오픽 답변 첨삭 + 저장."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    question = (data.get("question") or "").strip()
    answer = (data.get("answer") or "").strip()
    if not question or not answer:
        return jsonify({"error": "질문과 답변이 모두 필요합니다."}), 400

    try:
        result = ai_feedback.opic_feedback(question, answer)
    except Exception as e:
        return jsonify({"error": f"첨삭 중 오류: {e}"}), 500

    try:
        oid = db.add_opic_answer(
            topic=topic,
            question=question,
            answer=answer,
            corrected=result["corrected"],
            feedback=result["feedback"],
            model_answer=result.get("model_answer", ""),
            score=result["score"],
        )
    except Exception as e:
        return jsonify({"error": f"답변 저장에 실패했습니다: {e}"}), 500

    return jsonify({"id": oid, "answer": answer, **result})


# ---------------------------------------------------------------------------
# 복습 / 퀴즈 / 챗봇 API
# ---------------------------------------------------------------------------
@app.route("/api/review")
def api_review():
    kind = request.args.get("kind", "words")
    if kind not in ("words", "sentences"):
        kind = "words"
    return jsonify({"kind": kind, "cards": db.get_review_items(kind)})


@app.route("/api/quiz")
def api_quiz():
    """오늘 복습할 단어 목록 (객관식 보기 4개 포함)."""
    words = db.get_due_words(limit=20)
    for w in words:
        choices = db.get_distractors(w["id"], count=3) + [w["word"]]
        random.shuffle(choices)
        w["choices"] = choices
    return jsonify({"words": words})


@app.route("/api/quiz/answer", methods=["POST"])
def api_quiz_answer():
    """퀴즈 채점 결과로 SRS 일정 갱신."""
    data = request.get_json(silent=True) or {}
    word_id = data.get("id")
    correct = bool(data.get("correct"))
    if word_id is None:
        return jsonify({"error": "단어 id가 필요합니다."}), 400
    try:
        result = db.update_word_review(int(word_id), correct)
    except Exception as e:
        return jsonify({"error": f"갱신 실패: {e}"}), 500
    return jsonify({"id": word_id, **result, "due_count": db.count_due_words()})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    history = data.get("history") or []
    topic = (data.get("topic") or "").strip()
    if not history:
        return jsonify({"error": "메시지가 비어 있습니다."}), 400
    try:
        reply = ai_feedback.chat_reply(history, topic)
    except Exception as e:
        return jsonify({"error": f"대화 생성 중 오류: {e}"}), 500
    return jsonify({"reply": reply})


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "요청한 API 를 찾을 수 없습니다."}), 404
    return render_template("error.html", code=404,
                           message="찾으시는 페이지가 없어요. 주소를 다시 확인해 주세요."), 404


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500
    return render_template("error.html", code=500,
                           message="잠시 문제가 생겼어요. 잠시 후 다시 시도해 주세요."), 500


def _lan_ip():
    """같은 와이파이에서 접속할 수 있는 이 PC 의 IP 를 알아낸다."""
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
    # 같은 와이파이에 공개(0.0.0.0)할 때는 디버거를 꺼서 원격 코드 실행 위험을 막는다
    debug = os.getenv("FLASK_DEBUG", "0" if host == "0.0.0.0" else "1") == "1"

    # 참고: 한국어 Windows 콘솔(cp949)은 이모지를 출력하지 못하므로 텍스트만 쓴다
    print()
    print("  [English World] 시작!")
    print(f"  PC에서 : http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        ip = _lan_ip()
        if ip:
            print(f"  폰에서 : http://{ip}:{port}  (같은 와이파이에서 접속)")
    print()

    app.run(host=host, port=port, debug=debug)
