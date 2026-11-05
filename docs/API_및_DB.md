# API와 DB 스키마

English World 서버([`app.py`](../app.py))가 제공하는 API와 SQLite 테이블([`db.py`](../db.py)) 구조를 정리한 문서입니다.

[← README로 돌아가기](../README.md)

## 페이지

| 경로 | 화면 |
|------|------|
| `/` | 모드 선택 홈 |
| `/vocab` | 단어 암기 모드 |
| `/toeic` | TOEIC 모드 |
| `/opic` | OPIC 모드 |
| `/talk` | 회화 모드 (`/chat` 은 예전 주소 호환용으로 `/talk` 로 이동) |
| `/history` | 학습 기록 |
| `/review` | 복습 (플래시카드) |
| `/quiz` | 단어 퀴즈 (SRS) |
| `/healthz` | 헬스 체크 (비밀번호 없이 접근 가능) |

## API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/word` | 단어 분석 + 저장 (`{word, mode}` 또는 추천 단어 객체) · 중복이면 409 |
| `DELETE` | `/api/word/<id>` | 단어 삭제 (오타·중복 정리) |
| `POST` | `/api/wordbook/pull` | `{count}` → 내 단어장에서 새 단어 N개를 오늘 학습 목록으로 가져오기 |
| `POST` | `/api/recommend-words` | `{topic}` → 추천 단어 목록 (저장 안 함) |
| `POST` | `/api/sentence` | `{sentence, mode}` → 교정/피드백/한글뜻/점수 + 저장 |
| `POST` | `/api/toeic/words` | `{level}` → 토익 빈출 단어 추천 (저장 안 함) |
| `POST` | `/api/toeic/question` | `{recent}` → Part 5 문제 (보기 4개 + 해설) |
| `POST` | `/api/toeic/answer` | 풀이 결과 저장 → `{is_correct}` |
| `GET`  | `/api/toeic/wrong` | 다시 풀어볼 오답 목록 (다시 맞히면 제외) |
| `POST` | `/api/opic/question` | `{topic}` → 오픽 질문 (영어 + 한국어 번역) |
| `POST` | `/api/opic/answer` | `{topic, question, answer}` → 첨삭/모범답변/점수 + 저장 |
| `GET`  | `/api/review?kind=words\|sentences` | 복습 카드 데이터 |
| `GET`  | `/api/quiz` | 오늘 복습할 단어(SRS) + 객관식 보기 4개 |
| `POST` | `/api/quiz/answer` | `{id, correct}` → 박스/다음 복습일 갱신 |
| `POST` | `/api/chat` | `{history, topic}` → AI 회화 응답 |

`/healthz`·`/static/`·`/login`·`/signup` 을 뺀 모든 경로는 로그인이 필요합니다 (화면은 `/login` 으로 이동, API 는 401). 모든 기록 테이블에 `user_id` 가 있어 계정마다 분리됩니다. 전체 API 목록은 `app.py` 맨 위 설명을 참고하세요.
`APP_PASSWORD` 를 설정하면 그 앞에 HTTP 기본 인증이 한 겹 더 걸립니다.

## DB 스키마

**words** — 외운 단어

| 컬럼 | 설명 |
|------|------|
| id, created_at, date | 식별/시각/날짜 |
| word, meaning, pronunciation | 단어, 한글뜻, 발음 |
| example, example_kr | 영어 예문, 예문 해석 |
| box, next_review | 간격 반복(SRS) 박스 단계 · 다음 복습일 |
| mode | 학습 모드 태그 (toeic/opic/talk/vocab) |

**sentences** — 공부한 회화 문장

| 컬럼 | 설명 |
|------|------|
| id, created_at, date | 식별/시각/날짜 |
| original, corrected | 내가 쓴 문장, AI 교정 |
| feedback, meaning, score | 피드백, 한글뜻, 점수 |
| mode | 학습 모드 태그 |

**opic_answers** — 오픽 답변 연습 (주제·질문·내답변·교정·피드백·모범답변·점수)

**toeic_quiz_log** — 토익 Part 5 풀이 기록 (문제·보기·내답·정답·해설·정오)

**wordbook** — 내 단어장 (PDF 등에서 일괄 적재해 두고 매일 조금씩 꺼내 외우는 풀)

| 컬럼 | 설명 |
|------|------|
| id | 식별 |
| word, meaning | 영어 단어(대소문자 무시 중복 불가), 한글 뜻 |
| example, example_kr | 영어 예문, 예문 해석 |
| added, added_at | 학습 목록으로 가져갔는지 여부, 가져간 날짜 |

기존 DB에 컬럼이 없으면 시작할 때 `ALTER TABLE` 로 자동 추가하므로(SRS·모드 컬럼), 예전 기록도 그대로 이어서 쓸 수 있습니다.
