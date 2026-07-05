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
# 3-1) TOEIC — 빈출 단어 추천
# ===========================================================================
_TOEIC_WORDS_PROMPT = (
    "You are a TOEIC vocabulary coach for a Korean learner. "
    "Recommend frequently-tested TOEIC words appropriate for the learner's target score. "
    "Prefer business/office/travel contexts that actually appear on the TOEIC test. "
    "Return ONLY a JSON object: "
    '{ "words": [ {"word": ..., "meaning": (Korean), "pronunciation": ..., '
    '"example": (English, TOEIC-style), "example_kr": (Korean)} ] }. '
    "Give exactly the requested number of words. No text outside the JSON."
)


def recommend_toeic_words(level="600", count=5):
    """토익 목표 점수(600/800/900)에 맞는 빈출 단어 추천.

    반환형은 recommend_words 와 동일: [{word, meaning, pronunciation, example, example_kr}]
    """
    level = str(level or "600").strip()
    count = int(max(1, min(10, count)))

    if is_using_real_ai():
        try:
            user = f"목표 점수: {level} / 개수: {count}"
            data = _chat_json(_TOEIC_WORDS_PROMPT, user)
            cleaned = []
            for w in data.get("words", [])[:count]:
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

    return _MOCK_TOEIC_WORDS[:count]


# ===========================================================================
# 3-2) TOEIC — Part 5 문제 생성
# ===========================================================================
_PART5_PROMPT = (
    "You are a TOEIC test writer. Create ONE realistic TOEIC Part 5 "
    "(incomplete sentence) question testing grammar or vocabulary. "
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "question": the sentence with a blank written as "___" ,\n'
    '  "choices": an array of exactly 4 answer options (strings),\n'
    '  "answer": the index (0-3) of the correct option,\n'
    '  "explanation": a concise explanation IN KOREAN of why the answer is correct '
    "and why the others are wrong.\n"
    "Do not add any text outside the JSON."
)


def generate_part5_question(recent_questions=None):
    """토익 Part 5 문제 1개 생성: {question, choices[4], answer, explanation}."""
    if is_using_real_ai():
        try:
            user = "Create one new TOEIC Part 5 question."
            if recent_questions:
                recent = "\n".join(str(q) for q in list(recent_questions)[-5:])
                user += f" Avoid repeating these recent questions:\n{recent}"
            data = _chat_json(_PART5_PROMPT, user)
            question = str(data.get("question", "")).strip()
            choices = [str(c).strip() for c in data.get("choices", [])][:4]
            answer = int(data.get("answer", 0))
            if question and len(choices) == 4 and 0 <= answer <= 3:
                return {
                    "question": question,
                    "choices": choices,
                    "answer": answer,
                    "explanation": str(data.get("explanation", "")).strip(),
                }
        except Exception:
            pass

    return _part5_mock(recent_questions)


# ===========================================================================
# 3-3) OPIC — 질문 생성
# ===========================================================================
_OPIC_QUESTION_PROMPT = (
    "You are an OPIc (Oral Proficiency Interview - computer) examiner. "
    "Create ONE realistic OPIc question for the given survey topic, "
    "in the style of the actual Korean OPIc test (friendly interviewer 'Eva'). "
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "question": the OPIc question in English (2-4 sentences, conversational),\n'
    '  "question_kr": the Korean translation of the question.\n'
    "Do not add any text outside the JSON."
)


def opic_question(topic="자기소개"):
    """오픽 주제별 질문 1개 생성: {question, question_kr}."""
    topic = (topic or "자기소개").strip()

    if is_using_real_ai():
        try:
            data = _chat_json(_OPIC_QUESTION_PROMPT, f"Survey topic: {topic}")
            q = str(data.get("question", "")).strip()
            if q:
                return {
                    "question": q,
                    "question_kr": str(data.get("question_kr", "")).strip(),
                }
        except Exception:
            pass

    return _opic_question_mock(topic)


# ===========================================================================
# 3-4) OPIC — 답변 첨삭 + 모범답변
# ===========================================================================
_OPIC_FEEDBACK_PROMPT = (
    "You are an OPIc speaking coach for a Korean learner. "
    "You get an OPIc question and the learner's spoken answer (transcribed). "
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "corrected": the learner\'s answer rewritten in natural spoken English '
    "(keep their ideas, fix grammar and awkward wording),\n"
    '  "feedback": specific coaching IN KOREAN — what was good, what to fix, '
    "and one tip to sound more natural (strategy for a higher OPIc grade),\n"
    '  "model_answer": a model answer in natural spoken English (IM-AL level, 4-6 sentences, '
    "with a clear structure: direct answer, details, personal touch),\n"
    '  "score": an integer 0-100 rating the answer (fluency, grammar, detail).\n'
    "Do not add any text outside the JSON."
)


def opic_feedback(question, answer):
    """오픽 답변 첨삭: {corrected, feedback, model_answer, score}."""
    answer = (answer or "").strip()
    if not answer:
        raise ValueError("빈 답변은 첨삭할 수 없습니다.")

    if is_using_real_ai():
        try:
            user = f"Question: {question}\n\nLearner's answer: {answer}"
            data = _chat_json(_OPIC_FEEDBACK_PROMPT, user)
            return {
                "corrected": str(data.get("corrected", answer)).strip() or answer,
                "feedback": str(data.get("feedback", "")).strip() or "피드백을 생성하지 못했습니다.",
                "model_answer": str(data.get("model_answer", "")).strip(),
                "score": int(max(0, min(100, int(data.get("score", 70))))),
            }
        except Exception:
            result = _feedback_mock(answer)
            return {
                "corrected": result["corrected"],
                "feedback": "(AI 연결 실패로 자동 점검 결과로 대체) " + result["feedback"],
                "model_answer": "",
                "score": result["score"],
            }

    result = _feedback_mock(answer)
    return {
        "corrected": result["corrected"],
        "feedback": result["feedback"] + " (목업 모드 — AI 키를 넣으면 오픽 전략 피드백과 모범답변이 제공됩니다)",
        "model_answer": "",
        "score": result["score"],
    }


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
    "AFTER your reply add a new line starting with '📝' and briefly correct it. "
    "The correction MUST be written in KOREAN (한국어/한글) — never in Chinese, Japanese, "
    "or any other language. Show the natural English version inside the Korean explanation. "
    "If there is no notable mistake, do not add the 📝 line."
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


# 목업용 토익 빈출 단어 (AI 없이도 TOEIC 모드가 동작하도록)
_MOCK_TOEIC_WORDS = [
    {"word": "invoice", "meaning": "송장, 청구서", "pronunciation": "/ˈɪn.vɔɪs/",
     "example": "Please send the invoice by Friday.", "example_kr": "금요일까지 송장을 보내 주세요."},
    {"word": "itinerary", "meaning": "여행 일정표", "pronunciation": "/aɪˈtɪn.ə.rer.i/",
     "example": "The itinerary includes a factory tour.", "example_kr": "일정표에는 공장 견학이 포함되어 있다."},
    {"word": "quarterly", "meaning": "분기별의", "pronunciation": "/ˈkwɔːr.t̬ɚ.li/",
     "example": "The quarterly report is due next week.", "example_kr": "분기 보고서 마감이 다음 주다."},
    {"word": "reimburse", "meaning": "환급하다, 배상하다", "pronunciation": "/ˌriː.ɪmˈbɝːs/",
     "example": "The company will reimburse your travel expenses.", "example_kr": "회사가 출장비를 환급해 줄 것이다."},
    {"word": "comply", "meaning": "(규정을) 준수하다", "pronunciation": "/kəmˈplaɪ/",
     "example": "All staff must comply with the safety regulations.", "example_kr": "모든 직원은 안전 규정을 준수해야 한다."},
    {"word": "merger", "meaning": "합병", "pronunciation": "/ˈmɝː.dʒɚ/",
     "example": "The merger was announced yesterday.", "example_kr": "합병이 어제 발표되었다."},
    {"word": "warranty", "meaning": "품질 보증(서)", "pronunciation": "/ˈwɔːr.ən.t̬i/",
     "example": "The laptop comes with a two-year warranty.", "example_kr": "그 노트북은 2년 보증이 딸려 있다."},
    {"word": "postpone", "meaning": "연기하다", "pronunciation": "/poʊstˈpoʊn/",
     "example": "The meeting was postponed until Monday.", "example_kr": "회의가 월요일로 연기되었다."},
]


# 목업용 Part 5 문제 풀 (AI 없이도 문제 풀기가 동작하도록)
_MOCK_PART5 = [
    {
        "question": "The marketing team completed the project ___ the deadline.",
        "choices": ["ahead of", "ahead", "forward", "advance"],
        "answer": 0,
        "explanation": "'ahead of the deadline'(마감보다 앞서)이 관용 표현입니다. ahead 단독은 전치사 목적어를 받을 수 없어요.",
    },
    {
        "question": "All employees are required to submit ___ timesheets by Friday.",
        "choices": ["they", "them", "their", "theirs"],
        "answer": 2,
        "explanation": "명사 timesheets 앞의 빈칸은 소유격 자리입니다. 따라서 their가 정답이에요.",
    },
    {
        "question": "The new printer works much more ___ than the old one.",
        "choices": ["efficient", "efficiently", "efficiency", "efficiencies"],
        "answer": 1,
        "explanation": "동사 works를 수식하는 부사 자리이므로 efficiently가 정답입니다. more ~ than 비교급 구조예요.",
    },
    {
        "question": "___ the heavy rain, the outdoor event proceeded as scheduled.",
        "choices": ["Because", "Despite", "Although", "However"],
        "answer": 1,
        "explanation": "빈칸 뒤가 명사구(the heavy rain)이므로 전치사 Despite가 정답입니다. Although는 절이 와야 해요.",
    },
    {
        "question": "Ms. Park will review the contract ___ she returns from the conference.",
        "choices": ["until", "as soon as", "so that", "in order to"],
        "answer": 1,
        "explanation": "'돌아오자마자 검토할 것'이라는 의미이므로 시간 접속사 as soon as가 자연스럽습니다.",
    },
]


def _part5_mock(recent_questions=None):
    """목업 Part 5 문제 — 최근에 낸 문제는 피해서 순환 출제한다."""
    recent = set(recent_questions or [])
    for q in _MOCK_PART5:
        if q["question"] not in recent:
            return dict(q)
    return dict(_MOCK_PART5[0])


# 목업용 오픽 질문 (주제별)
_MOCK_OPIC_QUESTIONS = {
    "자기소개": {
        "question": "Let's start the interview now. Tell me a little about yourself.",
        "question_kr": "이제 인터뷰를 시작할게요. 자기소개를 간단히 해 주세요.",
    },
    "집": {
        "question": "I would like to know where you live. Describe your home. What does it look like? Give me as many details as possible.",
        "question_kr": "사는 곳이 궁금해요. 집을 묘사해 주세요. 어떻게 생겼나요? 가능한 자세히 말해 주세요.",
    },
    "취미": {
        "question": "You indicated that you like watching movies. What kind of movies do you like? Why do you enjoy them?",
        "question_kr": "영화 보는 걸 좋아한다고 하셨네요. 어떤 영화를 좋아하나요? 왜 좋아하나요?",
    },
    "여행": {
        "question": "Tell me about a memorable trip you have taken. Where did you go, who did you go with, and what did you do there?",
        "question_kr": "기억에 남는 여행에 대해 말해 주세요. 어디로, 누구와 갔고, 거기서 뭘 했나요?",
    },
    "운동": {
        "question": "You said you go jogging. How often do you jog, and where do you usually go jogging?",
        "question_kr": "조깅을 한다고 하셨죠. 얼마나 자주, 주로 어디에서 조깅을 하나요?",
    },
    "영화": {
        "question": "Tell me about the last movie you watched. What was it about, and how did you like it?",
        "question_kr": "최근에 본 영화에 대해 말해 주세요. 어떤 내용이었고, 어땠나요?",
    },
    "롤플레이": {
        "question": "I'm sorry, but there is a problem. You bought a ticket for a concert, but you can't go. Call your friend and explain the situation, and suggest two alternatives.",
        "question_kr": "문제 상황입니다. 콘서트 티켓을 샀는데 갈 수 없게 됐어요. 친구에게 전화해 상황을 설명하고 대안 두 가지를 제안하세요.",
    },
}


def _opic_question_mock(topic):
    q = _MOCK_OPIC_QUESTIONS.get(topic)
    if q:
        return dict(q)
    return {
        "question": f"Tell me more about {topic}. Please describe it in as much detail as possible.",
        "question_kr": f"'{topic}'에 대해 더 말해 주세요. 가능한 자세히 설명해 주세요.",
    }
