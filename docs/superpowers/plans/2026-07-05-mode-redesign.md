# English World 2.0 — 목적별 학습 모드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 첫 화면에서 TOEIC/OPIC/회화 모드를 고르고, 모드별 전용 학습 + 날짜별 모드 태그 기록을 제공한다.

**Architecture:** 기존 Flask 단일 앱 구조 유지. `db.py`에 mode 컬럼과 2개 신규 테이블 추가, `ai_feedback.py`에 모드별 AI 함수 4개 추가(모두 목업 폴백), `app.py`에 라우트/API 추가. 템플릿은 페이지당 1개 유지, JS는 페이지당 1개.

**Tech Stack:** Python Flask, SQLite, OpenAI/Groq SDK, 바닐라 JS, Web Speech API, pytest

**스펙:** `docs/superpowers/specs/2026-07-05-mode-redesign-design.md`

---

### Task 1: DB 계층 — mode 컬럼 + 신규 테이블

**Files:** Modify `db.py`, Create `tests/test_db.py`

- [ ] `init_db()`에 마이그레이션 추가:
  - `_ensure_column(conn, "words", "mode", "TEXT NOT NULL DEFAULT 'talk'")`
  - `_ensure_column(conn, "sentences", "mode", "TEXT NOT NULL DEFAULT 'talk'")`
  - `opic_answers(id, created_at, date, topic, question, answer, corrected, feedback, model_answer, score)` 테이블
  - `toeic_quiz_log(id, created_at, date, question, choices(JSON TEXT), my_answer, correct_answer, explanation, is_correct INTEGER)` 테이블 + date 인덱스
- [ ] `add_word(..., mode="talk")`, `add_sentence(..., mode="talk")` 파라미터 추가
- [ ] `add_opic_answer(topic, question, answer, corrected, feedback, model_answer, score) -> id`
- [ ] `add_toeic_quiz(question, choices:list, my_answer, correct_answer, explanation, is_correct) -> id`
- [ ] `get_history(limit_days=60)` 반환에 `opic`/`toeic` 리스트 포함 (choices는 json.loads 복원)
- [ ] `get_today_counts()` → `{words, sentences, opic, toeic}` / 모드별 오늘 카운트용 `get_today_mode_summary()` 추가
- [ ] `get_stats()` → `total_opic`, `total_toeic` 추가 (학습일·스트릭 계산에 신규 테이블 날짜 포함)
- [ ] pytest: 임시 DB로 저장/조회/마이그레이션 검증 → 커밋

### Task 2: AI 계층 — 모드별 함수 4개 (목업 폴백 포함)

**Files:** Modify `ai_feedback.py`

- [ ] `recommend_toeic_words(level="600", count=5)` — 토익 빈출 단어, 기존 recommend_words와 동일 반환형. 목업: 토익 단어 하드코딩 목록
- [ ] `generate_part5_question(recent_questions=None)` — `{question, choices[4], answer(0-3), explanation}` JSON. 목업: 하드코딩 문제 풀에서 순환
- [ ] `opic_question(topic)` — `{question, question_kr}`. 목업: 주제별 하드코딩 질문
- [ ] `opic_feedback(question, answer)` — `{corrected, feedback, model_answer, score}`. 목업: `_feedback_mock` 재활용 + 모범답변 안내문
- [ ] 커밋

### Task 3: 라우트 — 모드 페이지 + API

**Files:** Modify `app.py`, Create `tests/test_app.py`

- [ ] `GET /` → `home.html` (모드 선택 + 오늘 요약)
- [ ] `GET /toeic`, `GET /opic`, `GET /talk` (기존 index 로직은 /talk로 이동), `GET /chat` → `/talk` 리다이렉트
- [ ] `POST /api/word`, `/api/sentence`에 `mode` 필드 수용 (기본 'talk')
- [ ] `POST /api/toeic/words` `{level}` → 추천 단어 / `POST /api/toeic/question` → 문제 / `POST /api/toeic/answer` `{question, choices, my_answer, correct_answer, explanation}` → 채점 저장
- [ ] `POST /api/opic/question` `{topic}` / `POST /api/opic/answer` `{topic, question, answer}` → 첨삭+저장
- [ ] `GET /history`에 모드 필터 데이터 전달
- [ ] pytest: Flask test client로 목업 모드 API 검증 → 커밋

### Task 4: 화면 — 홈/토익/오픽/회화/기록 + 디자인 리프레시

**Files:** Create `templates/home.html`, `templates/toeic.html`, `templates/opic.html`, `static/toeic.js`, `static/opic.js`; Rename-ish `templates/index.html`→`templates/talk.html` (챗봇 통합); Modify `templates/history.html`, `static/history.js`, `static/style.css`, 나머지 템플릿 nav 통일

- [ ] `style.css`: 오프화이트 배경(#faf9f6), 모드 색 변수(`--toeic:#3b82f6, --opic:#10b981, --talk:#f97362`), 모드 카드/뱃지 스타일
- [ ] `home.html`: 3개 모드 카드(오늘 진행 표시) + 하단 기록/복습/퀴즈 링크
- [ ] `toeic.html` + `toeic.js`: 레벨 선택 → 단어 추천 담기(mode='toeic'), Part5 문제 풀기 UI
- [ ] `opic.html` + `opic.js`: 주제 선택 → 질문 → 타이핑/🎤음성(webkitSpeechRecognition, 미지원 시 버튼 숨김) → 첨삭 결과 + 모범답변
- [ ] `talk.html`: 기존 오늘학습(단어+문장) + 챗봇 탭 통합, app.js/chat.js 재사용 (mode='talk' 전달)
- [ ] `history.html`: 모드 필터 탭(전체/TOEIC/OPIC/회화), 모드 뱃지, 오픽/토익 항목 표시
- [ ] 전 템플릿 nav: 홈 / TOEIC / OPIC / 회화 / 기록 / 복습 / 퀴즈 → 커밋

### Task 5: text.MD + README 갱신

- [ ] `text.MD` 작성 (기술 선택 이유, 아키텍처, 요청 흐름, SRS, Web Speech API, AI 폴백, DB 스키마, 파일별 역할)
- [ ] `README.md` 모드 구조 반영 → 커밋

### Task 6: 검증

- [ ] `python -m pytest` 전체 통과
- [ ] 서버 실행 → 전 페이지 200 확인, 목업 모드에서 토익/오픽 흐름 동작 확인 → 커밋
