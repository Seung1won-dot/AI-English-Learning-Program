---
name: Notebook
description: 오래 공부해도 눈이 편한 공책. 미색 종이 위 먹색 글자, 만년필 잉크 블루 하나.
colors:
  paper: "#f5f2eb"
  page: "#fcfaf6"
  page-hover: "#efebe3"
  field: "#f3efe7"
  rule: "#e3ddd1"
  rule-strong: "#d2cbbd"
  ink: "#2d2b27"
  ink-dim: "#676256"
  ink-faint: "#7d776b"
  pen: "#3c5a82"
  pen-hover: "#314b6d"
  sage: "#4b7a59"
  ochre: "#9a6b22"
  brick: "#ad4e3a"
  night: "#1c1b19"
  night-page: "#242320"
  night-ink: "#e7e1d5"
  night-pen: "#93b1d4"
typography:
  display: { fontFamily: "Noto Serif KR", fontSize: "28px", fontWeight: 700, lineHeight: 1.3 }
  title:   { fontFamily: "Pretendard", fontSize: "17px", fontWeight: 600, lineHeight: 1.3 }
  body:    { fontFamily: "Pretendard", fontSize: "15px", fontWeight: 400, lineHeight: 1.65 }
  label:   { fontFamily: "Pretendard", fontSize: "13px", fontWeight: 500, lineHeight: 1.4 }
  caption: { fontFamily: "Pretendard", fontSize: "12px", fontWeight: 500, lineHeight: 1.4 }
rounded: { xs: "4px", control: "10px", container: "14px", pill: "999px" }
spacing: { xs: "4px", sm: "8px", md: "12px", lg: "16px", xl: "24px", xxl: "40px" }
---

# Design System: Notebook (공책)

## Overview

**North Star: "책상 위의 공책"** — 오래 들여다봐도 눈이 피로하지 않은 화면.
형광처럼 번쩍이는 순백 대신 **따뜻한 미색 종이**, 순검정 대신 **부드러운 먹색 글자**를 쓴다.
강조색은 **만년필 잉크 블루** 하나뿐이고, 맞음·주의·틀림에만 세이지·황토·벽돌색을 쓴다.
밤에는 차가운 검정이 아닌 **따뜻한 짙은 회갈색** 위에 베이지 글자(청색광이 적은 톤).

## Colors

| 역할 | 라이트 | 다크 | 쓰임 |
|---|---|---|---|
| 바탕 paper | `#f5f2eb` | `#1c1b19` | 페이지 배경 |
| 면 page | `#fcfaf6` | `#242320` | 섹션(공책 한 장) |
| 입력칸 field | `#f3efe7` | `#1f1e1b` | input, textarea, 보기 |
| 줄 rule | `#e3ddd1` / `#d2cbbd` | `#34322e` / `#45423c` | 1px 구분선, 테두리 |
| 먹 ink | `#2d2b27` · `#676256` · `#7d776b` | `#e7e1d5` · `#aaa396` · `#958e81` | 본문 · 보조 · 자리표시자 |
| 잉크 블루 pen | `#3c5a82` | `#93b1d4` | 주요 버튼, 선택, 포커스, 진행 |
| 세이지 sage | `#4b7a59` | `#93c09f` | 정답, 저장됨, 높은 점수 |
| 황토 ochre | `#9a6b22` | `#d8b574` | 주의, 목업 모드, 중간 점수 |
| 벽돌 brick | `#ad4e3a` | `#e0917d` | 오답, 오류, 삭제 hover |

**Rules**
- **One Pen Rule.** 잉크 블루는 "누를 수 있는 것 / 지금 선택된 것"에만. 제목·장식에는 쓰지 않는다.
- 순백(`#fff`) 바탕과 순검정(`#000`) 글자는 쓰지 않는다. 본문 대비는 4.5:1 이상, 과한 대비는 피한다.
- 그라데이션 없음.

## Typography

- **Pretendard** — 본문, 버튼, 라벨. 한국어 가독성이 좋은 산세리프.
- **Noto Serif KR** — 페이지 제목, 영어 표제어(단어), 퀴즈·카드의 문제 글, 큰 숫자. 사전·공책 느낌.
- 단계: **28 / 17 / 15 / 13 / 12px**. 이 밖의 크기는 쓰지 않는다. 본문 줄간격 1.65.
- 숫자는 `tabular-nums` 로 폭을 맞춘다 (모노 글꼴 없음).

## Layout & Shape

- 한 열, 최대 폭 720px. 상단바 56px sticky, 아래 1px 줄.
- 섹션은 "공책 한 장": 면 색 + 1px 줄 + 14px 모서리 + 아주 옅은 그림자(라이트만). 카드 안에 카드 없음.
- 목록은 행(row) — 1px 줄로 나누고 hover 시 옅은 배경.
- 컨트롤 10px, 컨테이너 14px, 칩 pill.
- 움직임은 상태 변화에만, 160~220ms, `cubic-bezier(0.2, 0.8, 0.2, 1)`. 튕김·깜빡임 없음. `prefers-reduced-motion` 에서 끔.

## Components

- **Primary 버튼**: 잉크 블루 배경 + 흰 글자(다크는 짙은 글자). 36px, 13px 600.
- **Ghost 버튼**: 투명 + 1px 줄 + 보조 먹색. hover 시 면 hover 색.
- **아이콘 버튼**: 32px, 투명. 모든 아이콘 버튼은 `aria-label`·`title`.
- **칩**: pill, 1px 줄. 선택 = 잉크 블루 글자 + 옅은 잉크 배경 + 잉크 테두리.
- **보기(choice)**: 입력칸 색 면. 정답 = 세이지 테두리·옅은 배경, 오답 = 벽돌.
- **토스트**: 아래 가운데, 면 색, 1px 줄, 떠 있는 그림자. 3.5초.
- **아이콘**: `templates/_icons.html` 의 SVG 만 (24 viewBox, 1.75 stroke). 이모지 금지.

## Don'ts

- Inter·Roboto·시스템 기본 글꼴 금지.
- 보라/파랑 그라데이션 배경 금지. 그라데이션 자체 금지.
- 카드 안의 카드 금지. 색 있는 배경 위 회색 본문 금지.
- 바운스·깜빡이는 점 등 장식 애니메이션 금지.
