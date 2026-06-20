"""
ai_feedback.py — AI 기능 (문장 첨삭 / 단어 분석 / 단어 추천)

AI 제공자를 다음 우선순위로 자동 선택한다.
  1) GROQ_API_KEY 가 있으면  → Groq (무료, Llama 모델)
  2) OPENAI_API_KEY 가 있으면 → OpenAI (유료)
  3) 둘 다 없으면           → 규칙기반/간이 목업
=> 키가 없어도 프로그램은 그대로 돌아간다.

Groq 는 OpenAI 와 호환되는 API 라서, 같은 openai SDK 에
base_url 만 바꿔 그대로 사용한다.
"""

import os
import re
import json

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# ---------------------------------------------------------------------------
# 제공자 선택 / 공통 호출
# ---------------------------------------------------------------------------
def _select_provider():
    """현재 사용할 제공자를 (이름, 키, base_url, 기본모델) 로 반환. 없으면 (None, ...)."""
    if not _OPENAI_AVAILABLE:
        return (None, "", None, "")

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        return ("groq", groq_key, GROQ_BASE_URL, os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        return ("openai", openai_key, None, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    return (None, "", None, "")


def is_using_real_ai():
    return _select_provider()[0] is not None


def current_provider_label():
    name = _select_provider()[0]
    return {"groq": "Groq (무료 AI)", "openai": "OpenAI"}.get(name)


def _chat_json(system_prompt, user_content):
    """AI 에 JSON 응답을 요청해 dict 로 반환. 키가 없으면 RuntimeError."""
    name, api_key, base_url, model = _select_provider()
    if name is None:
        raise RuntimeError("AI 키가 설정되어 있지 않습니다.")

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


# ===========================================================================
# 1) 회화 문장 첨삭
# ===========================================================================
_SENTENCE_PROMPT = (
    "You are a friendly English writing tutor for a Korean learner. "
    "The learner gives you one English sentence. "
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "corrected": the corrected, natural version of the sentence (English),\n'
    '  "feedback": a short encouraging explanation IN KOREAN of what was fixed and why,\n'
    '  "meaning": the Korean translation of the corrected sentence,\n'
    '  "score": an integer 0-100 rating the original sentence.\n'
    "Do not add any text outside the JSON."
)


def get_feedback(sentence):
    """문장 첨삭 결과 {corrected, feedback, meaning, score} 반환."""
    sentence = (sentence or "").strip()
    if not sentence:
        raise ValueError("빈 문장은 첨삭할 수 없습니다.")

    if is_using_real_ai():
        try:
            data = _chat_json(_SENTENCE_PROMPT, sentence)
            return {
                "corrected": str(data.get("corrected", sentence)).strip() or sentence,
                "feedback": str(data.get("feedback", "")).strip() or "피드백을 생성하지 못했습니다.",
                "meaning": str(data.get("meaning", "")).strip(),
                "score": int(max(0, min(100, int(data.get("score", 70))))),
            }
        except Exception:
            result = _feedback_mock(sentence)
            result["feedback"] = "(AI 연결 실패로 자동 점검 결과로 대체) " + result["feedback"]
            return result

    return _feedback_mock(sentence)


# ===========================================================================
# 2) 단어 분석 (뜻 / 발음 / 예문)
# ===========================================================================
_WORD_PROMPT = (
    "You are an English vocabulary tutor for a Korean learner. "
    "The user gives you ONE English word or short phrase. "
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "meaning": the Korean meaning(s) of the word (concise),\n'
    '  "pronunciation": IPA or simple pronunciation (e.g. /ˈæp.əl/),\n'
    '  "example": one natural English example sentence using the word,\n'
    '  "example_kr": the Korean translation of that example.\n'
    "Do not add any text outside the JSON."
)


def explain_word(word):
    """단어 분석 결과 {meaning, pronunciation, example, example_kr} 반환."""
    word = (word or "").strip()
    if not word:
        raise ValueError("빈 단어는 분석할 수 없습니다.")

    if is_using_real_ai():
        try:
            data = _chat_json(_WORD_PROMPT, word)
            return {
                "meaning": str(data.get("meaning", "")).strip() or "(뜻을 가져오지 못했습니다)",
                "pronunciation": str(data.get("pronunciation", "")).strip(),
                "example": str(data.get("example", "")).strip(),
                "example_kr": str(data.get("example_kr", "")).strip(),
            }
        except Exception:
            return _word_mock(word)

    return _word_mock(word)


# ===========================================================================
# 3) 단어 추천 (오늘의 단어)
# ===========================================================================
_RECOMMEND_PROMPT = (
    "You are an English vocabulary coach for a Korean learner. "
    "Recommend useful English words for the given topic and level. "
    "Return ONLY a JSON object: "
    '{ "words": [ {"word": ..., "meaning": (Korean), "pronunciation": ..., '
    '"example": (English), "example_kr": (Korean)} ] }. '
    "Give exactly the requested number of words. No text outside the JSON."
)


def recommend_words(topic="일상생활", count=5):
    """주제에 맞는 단어 count개 추천. [{word, meaning, pronunciation, example, example_kr}]."""
    topic = (topic or "일상생활").strip()
    count = int(max(1, min(10, count)))

    if is_using_real_ai():
        try:
            user = f"주제: {topic} / 개수: {count} / 난이도: 초중급"
            data = _chat_json(_RECOMMEND_PROMPT, user)
            words = data.get("words", [])
            cleaned = []
            for w in words[:count]:
                cleaned.append({
                    "word": str(w.get("word", "")).strip(),
                    "meaning": str(w.get("meaning", "")).strip(),
                    "pronunciation": str(w.get("pronunciation", "")).strip(),
                    "example": str(w.get("example", "")).strip(),
                    "example_kr": str(w.get("example_kr", "")).strip(),
                })
            cleaned = [w for w in cleaned if w["word"]]
            if cleaned:
                return cleaned
        except Exception:
            pass

    return _recommend_mock(count)


# ===========================================================================
# 4) AI 회화 챗봇
# ===========================================================================
_CHAT_SYSTEM = (
    "You are a friendly English conversation partner for a Korean learner. "
    "Have a natural, encouraging conversation in ENGLISH. "
    "Keep your replies short (1-3 sentences) and ask a follow-up question to keep "
    "the conversation going. Use simple, everyday English suitable for an "
    "intermediate learner. "
    "If the learner's last message has a notable grammar or word-choice mistake, "
    "AFTER your reply add a new line starting with '📝' and briefly correct it IN KOREAN "
    "(show the natural English version). If there is no notable mistake, do not add the 📝 line."
)


def chat_reply(history, topic=""):
    """회화 챗봇 응답(텍스트)을 반환한다.

    history: [{"role": "user"|"assistant", "content": "..."}, ...]
    topic:   대화 주제 (선택)
    """
    if is_using_real_ai():
        try:
            system = _CHAT_SYSTEM
            if topic:
                system += f" The conversation topic is: {topic}."
            messages = [{"role": "system", "content": system}]
            # 최근 12개만 보내 토큰 절약
            for m in history[-12:]:
                role = "assistant" if m.get("role") == "assistant" else "user"
                messages.append({"role": role, "content": str(m.get("content", ""))})

            name, api_key, base_url, model = _select_provider()
            client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return _chat_mock(history, topic)

    return _chat_mock(history, topic)


def _chat_mock(history, topic):
    last = history[-1]["content"] if history else ""
    return (
        f"(목업 모드 — AI 키를 넣으면 실제 대화가 됩니다) "
        f"Nice! You said: \"{last}\". Can you tell me more?"
    )


# ===========================================================================
# 목업 (AI 키 없이도 동작 — 품질은 낮지만 프로그램은 멈추지 않는다)
# ===========================================================================
def _feedback_mock(sentence):
    notes = []
    score = 100
    corrected = sentence.strip()

    if corrected and corrected[0].islower():
        corrected = corrected[0].upper() + corrected[1:]
        notes.append("문장은 대문자로 시작해야 해요.")
        score -= 8
    if corrected and corrected[-1] not in ".?!":
        corrected += "."
        notes.append("문장 끝에는 마침표가 필요해요.")
        score -= 8
    new_corrected = re.sub(r"\bi\b", "I", corrected)
    if new_corrected != corrected:
        notes.append("1인칭 'I'는 항상 대문자예요.")
        corrected = new_corrected
        score -= 8
    if not notes:
        notes.append("문법과 표현이 자연스러워요. 좋아요! 👍")

    return {
        "corrected": corrected,
        "feedback": " ".join(notes),
        "meaning": "",  # 목업은 번역 불가 (AI 키를 넣으면 한글뜻이 채워집니다)
        "score": max(0, min(100, score)),
    }


def _word_mock(word):
    return {
        "meaning": "(목업 모드 — AI 키를 넣으면 뜻이 자동으로 채워집니다)",
        "pronunciation": "",
        "example": "",
        "example_kr": "",
    }


# 목업용 기본 추천 단어 (AI 없이도 추천 버튼이 동작하도록)
_MOCK_WORDS = [
    {"word": "improve", "meaning": "향상시키다", "pronunciation": "/ɪmˈpruːv/",
     "example": "I want to improve my English.", "example_kr": "나는 영어를 향상시키고 싶다."},
    {"word": "schedule", "meaning": "일정, 예정하다", "pronunciation": "/ˈskedʒ.uːl/",
     "example": "Let's schedule a meeting.", "example_kr": "회의 일정을 잡자."},
    {"word": "available", "meaning": "이용 가능한", "pronunciation": "/əˈveɪ.lə.bəl/",
     "example": "Are you available tomorrow?", "example_kr": "내일 시간 괜찮아?"},
    {"word": "decision", "meaning": "결정", "pronunciation": "/dɪˈsɪʒ.ən/",
     "example": "It was a hard decision.", "example_kr": "그건 어려운 결정이었다."},
    {"word": "experience", "meaning": "경험", "pronunciation": "/ɪkˈspɪə.ri.əns/",
     "example": "It was a great experience.", "example_kr": "그것은 멋진 경험이었다."},
    {"word": "recommend", "meaning": "추천하다", "pronunciation": "/ˌrek.əˈmend/",
     "example": "Can you recommend a good book?", "example_kr": "좋은 책 추천해줄래?"},
]


def _recommend_mock(count):
    return _MOCK_WORDS[:count]
