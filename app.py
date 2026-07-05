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

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect

import db
import ai_feedback

load_dotenv()

app = Flask(__name__)
db.init_db()

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
@app.route("/")
def home():
    """홈 — 학습 모드 선택 + 오늘 학습 요약."""
    return render_template(
        "home.html",
        summary=db.get_today_mode_summary(),
        today=db.today_str(),
        due_count=db.count_due_words(),
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


@app.route("/api/recommend-words", methods=["POST"])
def api_recommend_words():
    """오늘의 추천 단어 (미리보기 — 저장은 사용자가 선택)."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "일상생활").strip()
    try:
        words = ai_feedback.recommend_words(topic=topic, count=WORDS_GOAL)
    except Exception as e:
        return jsonify({"error": f"추천 중 오류: {e}"}), 500
    return jsonify({"topic": topic, "words": words})


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
    return jsonify({"level": level, "words": words})


@app.route("/api/toeic/question", methods=["POST"])
def api_toeic_question():
    """토익 Part 5 문제 1개 생성."""
    data = request.get_json(silent=True) or {}
    recent = data.get("recent") or []  # 같은 문제 반복 방지용 최근 문제 목록
    try:
        q = ai_feedback.generate_part5_question(recent_questions=recent)
    except Exception as e:
        return jsonify({"error": f"문제 생성 중 오류: {e}"}), 500
    return jsonify(q)


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
    return jsonify({"topic": topic, **q})


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
    """오늘 복습할 단어 목록."""
    return jsonify({"words": db.get_due_words(limit=20)})


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
