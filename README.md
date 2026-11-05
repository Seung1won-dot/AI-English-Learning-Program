# English World — AI 영어 학습 트래커

TOEIC · OPIC · 영어 회화 · 단어 암기 중 학습 목적에 맞는 모드를 골라 공부하고, 날짜별로 기록하고, 간격 반복으로 복습하는 개인 영어 학습 웹 프로그램입니다.

| 항목 | 내용 |
|---|---|
| 기간 | 2026.06 ~ 현재 |
| 역할 | 개인 프로젝트 (기획 · 개발 전부) |
| 기술 스택 | Python Flask · OpenAI/Groq API · SQLite · HTML/CSS/JS · Web Speech API |
| 디자인 | [DESIGN.md](DESIGN.md) "공책(Notebook)" — 눈이 편한 미색 종이/따뜻한 다크, 잉크 블루 강조색 하나, Pretendard + Noto Serif KR |
| 배포 | Procfile(gunicorn) · Dockerfile 준비됨 — [배포하기](docs/배포.md) |

## 목차

- [스크린샷](#스크린샷)
- [주요 기능](#주요-기능)
- [시작하기](#시작하기)
- [프로젝트 구조](#프로젝트-구조)
- [더 읽을거리](#더-읽을거리)
- [앞으로 개선하고 싶은 것](#앞으로-개선하고-싶은-것)

## 스크린샷

<table>
  <tr>
    <td width="50%" valign="top"><b>홈 — 학습 모드 선택</b><br>모드 카드 + 오늘 학습 요약<br><img src="docs/screenshots/01_home.png" alt="홈"></td>
    <td width="50%" valign="top"><b>TOEIC</b><br>빈출 단어 + Part 5<br><img src="docs/screenshots/02_toeic.png" alt="TOEIC"></td>
  </tr>
  <tr>
    <td valign="top"><b>OPIC</b><br>질문 → 말하기 → AI 첨삭<br><img src="docs/screenshots/03_opic.png" alt="OPIC"></td>
    <td valign="top"><b>회화</b><br>오늘 학습 + AI 프리토킹<br><img src="docs/screenshots/04_talk.png" alt="회화"></td>
  </tr>
  <tr>
    <td valign="top"><b>학습 기록</b><br>날짜별 · 모드별 필터<br><img src="docs/screenshots/05_history.png" alt="학습 기록"></td>
    <td valign="top"><b>단어 퀴즈</b><br>간격 반복(SRS)으로 모든 모드의 단어 통합 복습<br><img src="docs/screenshots/06_quiz.png" alt="퀴즈"></td>
  </tr>
</table>

## 주요 기능

| 화면 | 할 수 있는 것 |
|---|---|
| 홈 `/` | 단어 암기 / TOEIC / OPIC / 회화 중 오늘 공부할 모드 선택, 모드별 오늘 학습량 요약 |
| 단어 암기 `/vocab` | 단어를 입력하면 AI가 뜻·발음·예문 정리 · 주제별 AI 추천 단어 · **내 단어장**(PDF로 적재해 두고 매일 5/10/20개씩 가져오기) |
| TOEIC `/toeic` | 목표 점수(600/800/900)별 빈출 단어 · AI가 내는 **Part 5** 4지선다 + 한국어 해설 · 틀린 문제만 다시 푸는 **오답노트** |
| OPIC `/opic` | 서베이 주제별 실전 유형 질문 + 음성 재생 · 타이핑 또는 **말하기**(브라우저 음성인식)로 답변 · 교정문·피드백·점수·모범답변 |
| 회화 `/talk` | 단어 정리 · 영어 문장 **첨삭**(교정·피드백·한글뜻·점수) · 주제별 **AI 프리토킹**(실수에 한국어 교정) |
| 학습 기록 `/history` | 날짜별 + 모드별 필터, 항목 삭제, 통계(단어·문장·오픽·토익·학습일·**연속 학습일**) |
| 복습 `/review` · 퀴즈 `/quiz` | 플래시카드 · **SRS 퀴즈**(맞히면 1→3→7→14→30일, 틀리면 오늘 다시) · 객관식/주관식 선택, 주관식은 1글자 오타까지 인정 |

- **발음 듣기** — 단어·문장·정답·AI 답변 옆 스피커 버튼으로 원어민 발음 재생 (브라우저 음성합성, 무료)
- **중복 방지** — 같은 단어는 다시 저장되지 않고 안내가 나옵니다
- **AI 키가 없어도 동작** — 규칙기반 목업으로 돌아가고, 무료 Groq 키를 넣으면 실제 AI로 자동 전환됩니다 → [무료AI설정.md](docs/무료AI설정.md)
- **폰에서도 사용** — 같은 와이파이에서 접속하고, "홈 화면에 추가"로 앱처럼 설치(PWA)
- **단축키** — 퀴즈·Part 5는 `1`~`4` 선택 / `Enter` 다음, 플래시카드는 `Space` 뒤집기 / `←` `→` 이동, 문장 첨삭은 `Ctrl`+`Enter` 제출

## 시작하기

### 사전 요구사항

- Python 3.9 이상 (Docker 이미지는 Python 3.11 기준)
- (선택) AI 키 — `.env.example` 을 `.env` 로 복사해 `GROQ_API_KEY`(무료) 또는 `OPENAI_API_KEY` 하나만 채웁니다. 비워 두면 목업 모드로 동작합니다.

### 가장 쉬운 방법 (Windows)

`시작하기.bat` 을 더블클릭하면 서버가 켜지고 브라우저가 자동으로 열립니다. 콘솔에 표시되는 `http://192.168.x.x:5000` 주소로 같은 와이파이의 폰에서도 접속할 수 있습니다.

### 터미널로 실행

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

```bash
python app.py
```

브라우저에서 http://127.0.0.1:5000 으로 접속합니다. 포트는 `PORT`, 같은 와이파이 공개는 `HOST=0.0.0.0` 으로 바꿉니다. 자세한 단계는 [실행가이드.md](docs/실행가이드.md)에 있습니다.

### PDF 단어장 적재 (선택)

표 형식(No/영단어/뜻/예문) PDF를 내 단어장에 넣습니다. `pdfplumber` 가 필요합니다.

```bash
pip install pdfplumber
```

```bash
python scripts/import_wordbook.py "내단어장.pdf"
```

### 테스트

```bash
python -m pytest -q
```

AI 키 없이 목업 모드 + 임시 DB 로 DB 계층과 전체 API 를 검증합니다.

### 배포

`Procfile`(gunicorn)과 `Dockerfile` 이 준비되어 있습니다. 공개 서버라면 `APP_PASSWORD`·`SECRET_KEY` 를 꼭 설정하고, `DB_PATH` 를 영구 디스크로 지정하세요. 환경변수 목록과 플랫폼별 방법은 [docs/배포.md](docs/배포.md)에 있습니다.

## 프로젝트 구조

```text
AI-English-Learning-Program/
├─ app.py             Flask 서버 (페이지 라우트 + API)
├─ db.py              SQLite 저장/조회/통계/복습 (데이터 계층)
├─ ai_feedback.py     AI 기능 (첨삭/단어/토익 문제/오픽 질문·첨삭) + 목업
├─ templates/         base(공통 레이아웃) · _macros · _icons(SVG) + 화면별 템플릿
├─ static/            style.css · common.js(공통 유틸) + 페이지별 JS · PWA manifest
├─ scripts/           import_wordbook.py (PDF 단어장 적재)
├─ tests/             pytest (DB / API 검증)
├─ docs/              실행가이드 · 무료AI설정 · 배포 · 프로젝트설명 · 기술 선택(text.MD) · API/DB · 스크린샷
├─ DESIGN.md          디자인 시스템 (색·글꼴·컴포넌트 규칙)
├─ Procfile · Dockerfile  배포 설정
└─ 시작하기.bat        Windows 더블클릭 실행
```

## 더 읽을거리

- [docs/프로젝트설명.md](docs/프로젝트설명.md) — 프로젝트 구조, 동작 원리, 학습 루틴
- [docs/text.MD](docs/text.MD) — 기술 선택 이유
- [docs/실행가이드.md](docs/실행가이드.md) — 처음 실행하는 사람을 위한 단계별 안내
- [docs/무료AI설정.md](docs/무료AI설정.md) — 무료 Groq 키 설정
- [docs/배포.md](docs/배포.md) — 환경변수, Render/Railway, Docker 배포
- [docs/API_및_DB.md](docs/API_및_DB.md) — 페이지·API 목록과 DB 스키마
- [docs/트러블슈팅.md](docs/트러블슈팅.md) — "학습 기록이 가끔 사라지던 문제" 해결 기록 (commit 누락, WAL 모드, 에러 처리)
- [DESIGN.md](DESIGN.md) · [DESIGN-GUIDE.md](DESIGN-GUIDE.md) — 디자인 시스템

## 앞으로 개선하고 싶은 것

- ~~단어 퀴즈(객관식) 채점 모드~~ — 완료 (2026-07)
- ~~토익 오답 다시 풀기~~ — 완료 (2026-07)
- 틀린 문법 유형별 통계
- 학습 알림 / 목표 달성 뱃지
- 문장·오픽 답변도 간격 반복 복습에 편입
