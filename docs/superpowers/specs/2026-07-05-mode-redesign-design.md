# English World 2.0 — 목적별 학습 모드 재설계

날짜: 2026-07-05
상태: 사용자 승인 완료

## 목표

영어 학습 목적이 **TOEIC / OPIC / 영어 회화** 3가지로 명확해짐에 따라,
첫 화면에서 학습 모드를 선택하고 모드별 전용 학습 기능을 제공하도록 재설계한다.
모든 학습 활동은 날짜별로 기록되며 모드별로 필터링할 수 있다.

## 화면 구조

| 경로 | 역할 |
|------|------|
| `/` | **모드 선택 홈** — TOEIC/OPIC/회화 3개 카드 + 오늘 학습 요약 + 기록/복습/퀴즈 바로가기 |
| `/toeic` | TOEIC 모드 — 빈출 단어 추천(레벨 600/800/900) + Part 5 문제 풀기 |
| `/opic` | OPIC 모드 — 주제별 오픽 질문 → 타이핑/음성 답변 → AI 첨삭 + 모범답변 |
| `/talk` | 회화 모드 — 기존 단어 외우기 + 문장 첨삭 + AI 회화 챗봇 통합 |
| `/history` | 날짜별 기록 — 전체/TOEIC/OPIC/회화 필터 탭, 모드 색상 뱃지 |
| `/review` | 플래시카드 복습 (유지) |
| `/quiz` | SRS 단어 퀴즈 (유지 — TOEIC 단어도 자동 편입) |

## 기능 상세

### TOEIC 모드
- **빈출 단어**: 목표 점수(600/800/900)를 고르면 AI가 빈출 단어 5개 추천 →
  담으면 `words` 테이블에 `mode='toeic'`으로 저장, 기존 SRS 퀴즈에 자동 편입.
- **Part 5 문제**: AI가 문법/어휘 4지선다 1문항 생성 → 사용자가 보기 선택 →
  정답/해설 표시, `toeic_quiz_log`에 저장. 연속으로 다음 문제 요청 가능.

### OPIC 모드
- 서베이 주제(자기소개/집/취미/여행/영화/운동/롤플레이 등)를 고르면 AI가 실제 오픽 유형 질문 1개 출제.
- 답변 입력: **타이핑** 또는 **🎤 음성 인식**(Web Speech API `SpeechRecognition`,
  en-US, 무료·키 불필요. 미지원 브라우저에서는 버튼 숨김 + 안내).
- AI 첨삭 결과: 교정문, 피드백(한국어), 점수(0~100), **모범답변**. `opic_answers`에 저장.

### 회화 모드
- 기존 index(단어 외우기 + 문장 첨삭 + 진행도)와 chat(AI 회화)을 `/talk` 하위 탭으로 통합.
- 신규 저장되는 단어/문장은 `mode='talk'`.

### 학습 기록
- 상단 필터 탭: 전체 / TOEIC / OPIC / 회화.
- 날짜별 항목에 모드 뱃지(색상) 표시. 오픽 답변·토익 문제 풀이도 함께 표시.
- 기존 통계(단어 수·문장 수·학습일·스트릭) 유지 + 오픽 답변 수·토익 문제 수 추가.

## 데이터 구조

- `words`, `sentences`에 `mode TEXT DEFAULT 'talk'` 컬럼 추가 (마이그레이션:
  `ALTER TABLE ... ADD COLUMN`, 기존 행은 기본값 'talk' — 데이터 유실 없음).
- 신규 테이블:
  - `opic_answers(id, created_at, date, topic, question, answer, corrected, feedback, model_answer, score)`
  - `toeic_quiz_log(id, created_at, date, question, choices, my_answer, correct_answer, explanation, is_correct)`
- AI 키 없으면 목업 폴백 유지 (기존 `ai_feedback.py` 패턴 그대로).

## AI 함수 (ai_feedback.py에 추가, 각각 목업 폴백 포함)

- `recommend_toeic_words(level, count)` — 토익 빈출 단어 추천
- `generate_part5_question()` — Part 5 문제 생성 (JSON: question, choices[4], answer, explanation)
- `opic_question(topic)` — 오픽 질문 생성
- `opic_feedback(question, answer)` — 첨삭 (corrected, feedback, model_answer, score)

## 디자인 방향

"차분하고 부담 없는 학습 노트" 스타일:
- 따뜻한 오프화이트 배경(#faf9f6 계열), 넉넉한 여백, 둥근 모서리 카드
- 모드별 포인트 색: TOEIC 파랑(#3b82f6), OPIC 초록(#10b981), 회화 코랄(#f97362)
  — 화면 전체는 무채색 기조, 색은 뱃지·버튼·카드 상단 스트립에만
- 큰 글자(기본 16px+), 부드러운 낮은 대비 그림자, 애니메이션 최소화

## text.MD 문서

프로젝트 루트에 생성. 내용:
- 기술 선택 이유 (Flask/SQLite/바닐라 JS — 대안 대비 트레이드오프)
- 전체 아키텍처 및 요청 흐름 (브라우저 → 라우트 → AI/DB → 응답)
- SRS(Leitner 간격 반복) 알고리즘 원리
- Web Speech API (음성인식 + TTS) 동작 원리
- AI 연동 구조 (Groq/OpenAI 자동 전환, 목업 폴백)
- DB 스키마와 파일별 역할, 초보자도 따라갈 수 있는 수준의 세세한 설명

## 에러 처리

- AI 실패 시 사용자에게 명확한 한국어 에러 메시지 (기존 패턴 유지)
- DB 저장은 컨텍스트 매니저 commit/rollback (기존 패턴 유지)
- 음성인식 미지원/권한 거부 시 타이핑으로 자연스럽게 폴백

## 테스트

- pytest + Flask test client 최소 도입: 목업 AI 모드에서 신규 API
  (toeic 단어/문제, opic 질문/첨삭, history 필터) 동작 검증
- 수동 검증: 서버 실행 후 전 화면 렌더링 확인
