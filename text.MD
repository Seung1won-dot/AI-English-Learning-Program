# 📖 text.MD — English World 프로젝트 완전 이해 가이드

> 이 문서는 **English World가 어떤 기술을, 왜, 어떻게 사용했는지**를 처음 보는 사람도
> 이해할 수 있도록 세세하게 설명합니다. 코드를 열어보기 전에 이 문서를 먼저 읽으면
> 프로젝트 전체가 한눈에 들어옵니다.

---

## 1. 이 프로젝트는 무엇인가?

**English World**는 영어를 스스로 공부하기 위해 만든 개인용 웹 학습 프로그램입니다.
학습 목적이 뚜렷하게 3가지라서, 첫 화면에서 모드를 골라 시작합니다.

| 모드 | 목적 | 핵심 기능 |
|------|------|----------|
| 📘 **TOEIC** | 토익 점수 | 목표 점수별 빈출 단어 추천 + Part 5 문제 풀이 |
| 🎤 **OPIC** | 오픽 등급 | 실전 유형 질문 → 말하기/타이핑 답변 → AI 첨삭 + 모범답변 |
| 💬 **회화** | 실전 영어 회화 | 단어 암기 + 문장 첨삭 + AI 프리토킹 |

어떤 모드로 공부하든 **모든 기록은 날짜별로 저장**되고, 기록 화면에서
모드별로 걸러 볼 수 있습니다. 외운 단어는 **간격 반복(SRS) 퀴즈**로 다시 나옵니다.

---

## 2. 전체 그림 (아키텍처)

이 앱은 흔히 말하는 **"서버 렌더링 + JSON API 혼합"** 구조입니다.

```
[브라우저]
   │  ① 페이지 요청 (GET /toeic)
   ▼
[Flask 서버: app.py]  ──②──▶  [templates/*.html]  Jinja2로 HTML 완성
   │                              (서버가 화면의 뼈대를 만들어 보냄)
   ▼
[브라우저가 HTML + static/*.js 를 받음]
   │  ③ 버튼 클릭 → JS의 fetch()가 JSON API 호출 (POST /api/toeic/question)
   ▼
[Flask 서버: app.py]
   ├──④──▶ [ai_feedback.py]  AI(Groq/OpenAI)에게 문제/첨삭 요청
   └──⑤──▶ [db.py]           SQLite에 학습 기록 저장/조회
   │  ⑥ JSON 응답 ({"question": ..., "choices": [...]})
   ▼
[브라우저 JS가 받은 JSON으로 화면을 동적으로 갱신]
```

**왜 이 구조인가?**
- 처음 페이지는 서버(Jinja2)가 만들어 주므로 **로딩이 빠르고 구조가 단순**합니다.
- 공부 중 상호작용(단어 추가, 문제 풀기, 첨삭)은 **페이지 새로고침 없이** JS의
  `fetch()`로 처리해서 학습 흐름이 끊기지 않습니다.
- React 같은 프레임워크 없이도 이 규모(페이지 7개)에서는 충분하며,
  빌드 도구 없이 파일만 수정하면 바로 반영됩니다.

---

## 3. 기술 선택과 이유 (트레이드오프)

### Python + Flask (백엔드)
- **왜?** Flask는 "마이크로 프레임워크"라서 `app.py` 파일 하나로 서버가 시작됩니다.
  라우트(주소) 하나 = 함수 하나라는 단순한 구조여서 학습용/개인용 프로젝트에 딱 맞습니다.
- **대안과 비교:**
  - *Django*: 관리자 페이지·ORM·인증까지 다 내장된 대형 프레임워크. 이 프로젝트에는
    과합니다(로그인도 없는 1인용 앱).
  - *FastAPI*: 비동기와 자동 문서화가 강점이지만, 이 앱은 동시 사용자 1명이라
    비동기가 이점이 없습니다.
- **어떻게 쓰나:** `@app.route("/toeic")` 데코레이터로 URL과 함수를 연결하고,
  `render_template()`으로 HTML을, `jsonify()`로 JSON을 돌려줍니다.

### SQLite (데이터베이스)
- **왜?** 서버 설치가 필요 없는 **파일 하나짜리 DB**(`learning.db`)입니다. Python에
  `sqlite3` 모듈이 내장되어 있어 의존성도 없습니다. 1인용 학습 기록에는 최적입니다.
- **대안과 비교:** MySQL/PostgreSQL은 별도 서버 프로세스를 돌려야 하고 계정/네트워크
  설정이 필요합니다. 다중 사용자 서비스로 키울 때 갈아타면 됩니다.
- **신뢰성 장치 (기록이 사라지지 않도록):**
  1. **컨텍스트 매니저** — 모든 DB 작업을 `with get_conn() as conn:`으로 감싸
     정상 종료 시 `commit()`, 예외 시 `rollback()`이 **자동으로** 일어납니다.
     (개발 초기에 commit 누락으로 기록이 사라지는 버그를 겪고 만든 구조입니다.)
  2. **WAL 저널 모드** — 쓰기 도중 프로그램이 죽어도 DB 파일이 깨지지 않도록
     `PRAGMA journal_mode=WAL`을 켭니다.
  3. **조용한 실패 금지** — 저장이 실패하면 사용자에게 명확한 에러 메시지를 돌려줍니다.

### Jinja2 템플릿 + 바닐라 JS (프론트엔드)
- **왜?** 페이지 골격은 서버에서 Jinja2(`{{ 변수 }}`, `{% for %}`)로 채우고,
  동적인 부분만 페이지별 JS 파일(`toeic.js`, `opic.js` 등)이 담당합니다.
- **대안과 비교:** React/Vue는 컴포넌트 재사용과 복잡한 상태 관리가 강점이지만,
  npm/빌드 체인이 따라옵니다. 이 규모에서는 순수 JS가 더 단순하고 빠릅니다.
- **패턴:** 모든 JS는 같은 패턴을 씁니다 —
  `postJSON(url, payload)` 헬퍼로 API 호출 → 받은 JSON으로 `insertAdjacentHTML` 등
  DOM 갱신 → 에러는 빨간 에러 박스에 표시. XSS를 막기 위해 사용자/AI 텍스트는
  반드시 `esc()` 함수로 이스케이프한 뒤 HTML에 넣습니다.

### Groq / OpenAI API (AI 기능)
- **왜 Groq?** Groq는 **무료 티어**로 Llama 모델을 쓸 수 있고, OpenAI SDK와
  **호환되는 API**를 제공합니다. 그래서 같은 `openai` 파이썬 라이브러리에
  `base_url`만 Groq 주소로 바꿔 그대로 사용합니다. (코드 중복 없음)
- **3단계 폴백 구조** — `ai_feedback.py`의 모든 AI 함수는 이렇게 동작합니다:
  ```
  1) GROQ_API_KEY 있음   → Groq (무료)
  2) OPENAI_API_KEY 있음 → OpenAI (유료)
  3) 키 없음 / API 실패  → 규칙 기반 목업 (프로그램은 절대 멈추지 않음)
  ```
  **왜?** API 키가 없어도, 인터넷이 끊겨도, 무료 한도를 넘어도 앱이 죽지 않고
  기본 기능(하드코딩된 단어/문제, 간단한 문법 점검)으로 계속 돌아가게 하기 위해서입니다.
- **JSON 모드:** AI에게 "반드시 JSON으로만 답하라"고 시키고
  (`response_format={"type": "json_object"}`), 파이썬에서 `json.loads()`로 바로
  파싱합니다. 자유 텍스트를 파싱하는 것보다 훨씬 안정적입니다.
- **프롬프트 설계:** 각 기능마다 시스템 프롬프트에 (1) AI의 역할(토익 출제자,
  오픽 코치...), (2) 응답 JSON의 정확한 키 목록, (3) "피드백은 반드시 한국어"
  같은 제약을 명시합니다. AI 응답은 믿지 않고 항상 검증합니다
  (보기 4개인지, 점수가 0~100인지 확인 후 사용).

### Web Speech API (음성 — 무료, 키 불필요)
- **발음 듣기(TTS):** 브라우저 내장 `speechSynthesis`로 단어/문장/모범답변을
  원어민 음성으로 읽어줍니다. (`static/tts.js`)
- **말로 답하기(STT):** OPIC 모드에서 `SpeechRecognition`(Chrome/Edge 내장)으로
  말한 내용을 텍스트로 받아 적습니다. 오픽은 말하기 시험이라 실전처럼 연습할 수
  있습니다. **미지원 브라우저에서는 마이크 버튼을 숨기고** 타이핑으로 자연스럽게
  폴백합니다.
- **왜?** 별도 음성 API(구글 STT 등)는 유료 + 키 관리가 필요합니다. 브라우저 내장
  기능이면 공짜에 설정도 필요 없습니다.

### pytest (테스트)
- `tests/test_db.py` — 임시 DB 파일로 저장/조회/마이그레이션 검증
- `tests/test_app.py` — Flask의 **test client**로 실제 서버를 띄우지 않고 API 호출을
  시뮬레이션. AI 키를 지워 **목업 모드로 강제**하므로 테스트가 빠르고 공짜입니다.
- 실행: `python -m pytest`

---

## 4. 파일별 역할

```
english world/
├─ app.py            # ① Flask 서버 — 모든 URL(라우트)과 API의 입구
├─ db.py             # ② 데이터 계층 — SQLite 저장/조회/통계/SRS. app.py만 이 파일을 부름
├─ ai_feedback.py    # ③ AI 계층 — 프롬프트, Groq/OpenAI 호출, 목업 폴백
├─ learning.db       # SQLite 데이터 파일 (git에는 안 올림)
├─ .env              # API 키 (비밀 — git에는 안 올림), .env.example 참고
├─ requirements.txt  # 파이썬 의존성 (Flask, python-dotenv, openai, pytest)
│
├─ templates/        # 화면 (Jinja2 HTML)
│   ├─ home.html     #   / — 모드 선택 홈
│   ├─ toeic.html    #   /toeic — 빈출 단어 + Part 5
│   ├─ opic.html     #   /opic — 질문/답변/첨삭
│   ├─ talk.html     #   /talk — 오늘 학습 + AI 프리토킹 (탭)
│   ├─ history.html  #   /history — 날짜별·모드별 기록
│   ├─ review.html   #   /review — 플래시카드
│   └─ quiz.html     #   /quiz — SRS 단어 퀴즈
│
├─ static/           # 브라우저에서 실행되는 파일
│   ├─ style.css     #   전체 디자인 (모드 색상 변수 포함)
│   ├─ tts.js        #   🔊 발음 듣기 (모든 페이지 공용)
│   ├─ app.js        #   회화 모드 — 단어/문장 학습
│   ├─ chat.js       #   회화 모드 — AI 챗봇
│   ├─ toeic.js      #   TOEIC 모드 — 단어 추천 + Part 5
│   ├─ opic.js       #   OPIC 모드 — 질문/음성인식/첨삭
│   ├─ history.js    #   기록 — 모드/날짜 필터
│   ├─ review.js     #   플래시카드 뒤집기/이동
│   └─ quiz.js       #   퀴즈 채점 + SRS 갱신
│
└─ tests/            # pytest 테스트
    ├─ test_db.py
    └─ test_app.py
```

**계층이 한 방향으로만 흐르는 것**이 핵심입니다:
`템플릿/JS → app.py(라우트) → db.py / ai_feedback.py`.
db.py는 ai_feedback.py를 모르고, ai_feedback.py는 db.py를 모릅니다.
그래서 한 파일을 고쳐도 다른 파일이 깨지지 않습니다.

---

## 5. 데이터 설계 (DB 스키마)

### words — 외운 단어
| 컬럼 | 설명 |
|------|------|
| id, created_at, date | 번호 / 저장 시각 / 날짜(YYYY-MM-DD) |
| word, meaning, pronunciation | 단어, 한글 뜻, 발음기호 |
| example, example_kr | 영어 예문, 예문 해석 |
| **box, next_review** | 간격 반복(SRS) 단계와 다음 복습일 |
| **mode** | 'toeic' \| 'opic' \| 'talk' — 어느 모드에서 외웠는지 |

### sentences — 공부한 문장
| 컬럼 | 설명 |
|------|------|
| original, corrected | 내가 쓴 문장, AI 교정문 |
| feedback, meaning, score | 피드백(한국어), 한글 뜻, 점수(0~100) |
| **mode** | 모드 태그 |

### opic_answers — 오픽 답변 연습
| 컬럼 | 설명 |
|------|------|
| topic, question | 서베이 주제, 오픽 질문 |
| answer | 내 답변 (타이핑 또는 음성 인식 결과) |
| corrected, feedback, model_answer, score | 교정문, 피드백, **모범답변**, 점수 |

### toeic_quiz_log — 토익 Part 5 풀이 기록
| 컬럼 | 설명 |
|------|------|
| question, choices | 문제(빈칸 문장), 보기 4개(**JSON 문자열**로 저장) |
| my_answer, correct_answer | 내가 고른 번호, 정답 번호 (0~3) |
| explanation, is_correct | 해설(한국어), 정답 여부 |

**설계 포인트**
- **mode 컬럼 방식**: 단어를 모드별로 테이블을 나누지 않고 태그 컬럼 하나로
  구분했습니다. 그래야 SRS 퀴즈/플래시카드가 **모든 모드의 단어를 한 번에** 다룰 수
  있고, 기록 화면 필터도 단순해집니다.
- **마이그레이션**: 테이블 구조를 바꿀 때 기존 데이터를 지키기 위해
  `_ensure_column()` 함수가 "컬럼이 없으면 ALTER TABLE로 추가"합니다. 예전 DB 파일을
  그대로 써도 기존 기록은 자동으로 mode='talk'로 분류됩니다.
- **choices를 JSON으로 저장**: SQLite에는 배열 타입이 없어서 보기 4개를
  `json.dumps()`로 문자열화해 저장하고, 읽을 때 `json.loads()`로 복원합니다.

---

## 6. 핵심 알고리즘 — 간격 반복(SRS, Leitner 시스템)

단어 퀴즈(`/quiz`)는 **에빙하우스 망각곡선**에 근거한 라이트너(Leitner) 박스
방식을 씁니다.

```
박스:      1 → 2 → 3 → 4  → 5
복습 간격: 1일  3일  7일  14일  30일

- 퀴즈에서 맞히면: 박스 +1 (복습 간격이 길어짐)
- 틀리면:          박스 1로 리셋 + 오늘 다시 출제
```

구현은 `db.py`의 `update_word_review()`에 있습니다. 매일 퀴즈에 들어가면
`next_review <= 오늘`인 단어만 골라 출제하므로, **외운 단어는 점점 뜸하게,
헷갈리는 단어는 자주** 만나게 됩니다. TOEIC 모드에서 담은 단어도 자동으로
이 시스템에 편입됩니다.

---

## 7. 학습 모드는 어떻게 동작하나 (요청 흐름 따라가기)

### 예시 1: TOEIC — Part 5 문제 풀기
1. `/toeic`에서 "문제 받기" 클릭 → `toeic.js`가 `POST /api/toeic/question` 호출
   (같은 문제 반복 방지를 위해 최근 문제 목록도 함께 보냄)
2. `app.py` → `ai_feedback.generate_part5_question()` → Groq에게 "토익 출제자"
   프롬프트로 JSON 문제 요청 → 검증 후 반환
3. 사용자가 보기를 클릭하면 JS가 정답을 채점해 색으로 표시 + 해설을 보여주고,
   `POST /api/toeic/answer`로 풀이 결과를 `toeic_quiz_log`에 저장
4. 저장된 기록은 `/history`에서 날짜별로, "📘 TOEIC" 필터로 볼 수 있음

### 예시 2: OPIC — 말로 답하기
1. 주제 선택 → "질문 받기" → `POST /api/opic/question` → AI가 오픽 스타일 질문 생성
   → 화면 표시 + `speechSynthesis`가 질문을 읽어줌 (실전처럼)
2. 🎤 버튼 → `SpeechRecognition`(en-US)이 내 영어 발화를 텍스트로 변환해
   답변창에 채움 (수정하고 싶으면 타이핑으로 편집 가능)
3. "AI 첨삭 받기" → `POST /api/opic/answer` → `ai_feedback.opic_feedback()`이
   교정문/피드백/모범답변/점수를 JSON으로 받아 → `opic_answers`에 저장 + 화면 표시

### 예시 3: 회화 — AI 프리토킹
1. `/talk`의 "AI 프리토킹" 탭 → 주제 칩 선택 → AI가 먼저 인사(`greet()`)
2. 메시지를 보낼 때마다 **대화 내역 전체(최근 12개)**를 `POST /api/chat`으로 보냄
   — AI는 상태를 기억하지 못하므로 매번 문맥을 다시 줘야 합니다
3. 내 영어에 실수가 있으면 AI가 답변 끝에 `📝 한국어 교정`을 붙여줌

---

## 8. 디자인 원칙

"차분하고 부담 없는 학습 노트" 컨셉입니다. (`static/style.css`)

- **배경**: 따뜻한 오프화이트(`#faf9f6`) — 시험 앱 특유의 차가운 느낌 제거
- **모드 색**: CSS 변수로 정의 — TOEIC 파랑(`--toeic`), OPIC 초록(`--opic`),
  회화 코랄(`--talk`). 화면 전체는 무채색을 유지하고 색은 **뱃지·버튼·카드
  상단 스트립에만** 사용해 눈이 피로하지 않게 했습니다.
- **모드 뱃지**: 기록 화면에서 항목마다 작은 색 뱃지로 어느 모드 학습인지 표시

---

## 9. 실행 방법

```bash
# 최초 1회
pip install -r requirements.txt

# (선택) 무료 AI 켜기 — .env 파일에
GROQ_API_KEY=발급받은키        # https://console.groq.com 에서 무료 발급

# 실행
python app.py                  # → http://127.0.0.1:5000

# 테스트
python -m pytest
```

- AI 키가 없으면 **목업 모드**로 동작합니다 (하드코딩 단어/문제 + 간단 문법 점검).
- 키를 넣으면 자동으로 실제 AI로 전환됩니다. 코드는 안 바꿔도 됩니다.

> ⚠️ **주의**: `openai` 라이브러리 1.x와 `httpx` 0.28+ 조합은 충돌합니다
> (`unexpected keyword argument 'proxies'` 에러 → AI가 조용히 목업으로 폴백).
> `requirements.txt`대로 `openai>=2.0`을 설치하면 문제없습니다.

---

## 10. 이 프로젝트에서 배울 수 있는 것 (정리)

1. **계층 분리** — 라우트(app.py) / 데이터(db.py) / AI(ai_feedback.py)를 나누면
   각 파일이 작아지고, 테스트와 수정이 쉬워진다.
2. **폴백 설계** — 외부 서비스(AI API)는 언제든 실패한다. 실패해도 앱이 계속
   돌아가는 경로(목업)를 항상 준비한다.
3. **데이터를 지키는 습관** — commit/rollback 자동화, WAL 모드, 마이그레이션 함수.
   "데이터가 사라지는 버그"는 한 번 겪으면 이런 구조의 소중함을 알게 된다.
4. **AI에게 JSON으로 답하게 하기** — 자유 텍스트 파싱 대신 JSON 모드 + 응답 검증.
5. **브라우저 내장 기능 활용** — TTS/STT를 공짜로. 외부 API가 항상 답은 아니다.
6. **간격 반복(SRS)** — 학습 앱의 핵심 알고리즘을 30줄로 구현할 수 있다.
