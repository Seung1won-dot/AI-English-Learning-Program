"""
app.py — Flask 서버 진입점

화면
  GET  /          : 오늘 학습 (단어 5개 + 문장 3개 진행)
  GET  /history   : 날짜별 학습 기록 + 통계
  GET  /review    : 플래시카드 복습

API (JSON)
  POST /api/word            : 단어 분석 + 저장
  POST /api/recommend-words : 오늘의 추천 단어 (저장 안 함, 미리보기)
  POST /api/sentence        : 회화 문장 첨삭 + 저장
  GET  /api/review?kind=words|sentences : 복습 카드 데이터

실행:  python app.py  (기본 http://127.0.0.1:5000)
"""

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

import db
import ai_feedback

load_dotenv()

app = Flask(__name__)
db.init_db()

# 하루 학습 목표
WORDS_GOAL = 5
SENTENCES_GOAL = 3


@app.route("/")
def index():
    counts = db.get_today_counts()
    items = db.get_today_items()
    return render_template(
        "index.html",
        using_real_ai=ai_feedback.is_using_real_ai(),
        provider_label=ai_feedback.current_provider_label(),
        counts=counts,
        items=items,
        words_goal=WORDS_GOAL,
        sentences_goal=SENTENCES_GOAL,
        today=db.today_str(),
    )


@app.route("/api/word", methods=["POST"])
def api_word():
    """단어 분석 후 저장."""
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip()
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
        )
    except Exception as e:
        return jsonify({"error": f"단어 저장에 실패했습니다: {e}"}), 500

    return jsonify({"id": word_id, "word": word, **analysis,
                    "counts": db.get_today_counts()})


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
        )
    except Exception as e:
        return jsonify({"error": f"문장 저장에 실패했습니다: {e}"}), 500

    return jsonify({"id": sid, "original": sentence, **result,
                    "counts": db.get_today_counts()})


@app.route("/history")
def history():
    return render_template(
        "history.html",
        history=db.get_history(limit_days=60),
        stats=db.get_stats(),
        words_goal=WORDS_GOAL,
        sentences_goal=SENTENCES_GOAL,
    )


@app.route("/review")
def review():
    return render_template("review.html")


# ----- 단어 퀴즈 (간격 반복 SRS) -----
@app.route("/quiz")
def quiz():
    return render_template("quiz.html", due_count=db.count_due_words())


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


# ----- AI 회화 챗봇 -----
@app.route("/chat")
def chat():
    return render_template("chat.html", using_real_ai=ai_feedback.is_using_real_ai())


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


@app.route("/api/review")
def api_review():
    kind = request.args.get("kind", "words")
    if kind not in ("words", "sentences"):
        kind = "words"
    return jsonify({"kind": kind, "cards": db.get_review_items(kind)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
