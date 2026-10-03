---
name: Ender Chest
description: 어디서 열어도 같은 내용물이 보이는 나만의 상자. 흑요석 바탕에 엔더 청록 한 가지.
colors:
  obsidian: "#15161d"
  obsidian-raised: "#1c1d26"
  obsidian-hover: "#23242f"
  obsidian-sunken: "#101117"
  seam: "#2b2c39"
  seam-strong: "#3a3b4a"
  ink-light: "#e9e8f1"
  ink-light-dim: "#a3a1b8"
  ink-light-faint: "#8b89a0"
  ender: "#4fd1a5"
  ender-bright: "#62dcb3"
  ender-ink: "#0b1a15"
  ember: "#e5b85c"
  rose: "#f0708a"
  stone: "#f3f2f7"
  stone-raised: "#ffffff"
  stone-hover: "#e9e8f0"
  stone-sunken: "#ebeaf1"
  stone-seam: "#d9d7e3"
  stone-seam-strong: "#c3c1d0"
  ink-dark: "#1b1a24"
  ink-dark-dim: "#5d5b70"
  ink-dark-faint: "#6b6980"
  ender-deep: "#0a6e53"
  ender-deeper: "#085c45"
  ember-deep: "#8a5d06"
  rose-deep: "#c0244a"
  backdrop: "rgba(0, 0, 0, 0.55)"
  backdrop-light: "rgba(27, 26, 36, 0.45)"
typography:
  headline:
    fontFamily: "IBM Plex Sans KR, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "26px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "IBM Plex Sans KR, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "IBM Plex Sans KR, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "IBM Plex Sans KR, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
  data:
    fontFamily: "IBM Plex Mono, ui-monospace, Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  xs: "4px"
  control: "8px"
  container: "12px"
  thumb: "6px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.ender}"
    textColor: "{colors.ender-ink}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-primary-hover:
    backgroundColor: "{colors.ender-bright}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-light-dim}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-ghost-hover:
    backgroundColor: "{colors.obsidian-hover}"
    textColor: "{colors.ink-light}"
  button-icon:
    backgroundColor: "transparent"
    textColor: "{colors.ink-light-dim}"
    rounded: "{rounded.control}"
    size: "32px"
  input:
    backgroundColor: "{colors.obsidian-sunken}"
    textColor: "{colors.ink-light}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink-light-dim}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  chip-selected:
    textColor: "{colors.ender}"
  composer:
    backgroundColor: "{colors.obsidian-raised}"
    rounded: "{rounded.container}"
    padding: "12px"
  dialog:
    backgroundColor: "{colors.obsidian-raised}"
    textColor: "{colors.ink-light}"
    rounded: "{rounded.container}"
    padding: "20px"
  toast:
    backgroundColor: "{colors.obsidian-raised}"
    rounded: "{rounded.container}"
    padding: "10px 14px"
---

# Design System: Ender Chest

## Overview

**Creative North Star: "흑요석 상자 (The Obsidian Chest)"**

마인크래프트의 엔더 상자는 검은 흑요석 몸체에 청록빛 눈 하나가 박혀 있고, 어느 상자를 열어도 같은 내용물이 나온다. 이 앱의 화면도 그 물건처럼 만든다. 바탕은 보라 기미가 살짝 도는 검은 흑요석, 강조는 엔더 청록 한 가지뿐이다. 청록은 "지금 살아 있는 것"(실시간 연결, 주요 동작, 선택, 포커스)에만 쓰고, 나머지는 밝기 차이와 1px 이음선(seam)으로만 구분한다.

이 화면은 Operate 모드다. 사용자는 뭔가를 넣고 꺼내려고 왔지 화면을 감상하려고 오지 않았다. 그래서 카드 대신 가로선으로 나눈 납작한 목록, 이모지 대신 같은 굵기의 선 아이콘, 장식 대신 상태 표시를 택했다. 라이트 모드는 시스템 설정을 따르며, 같은 구조를 차가운 회백색 돌(stone) 위에 옮긴 것이다.

**Key Characteristics:**
- 흑요석 다크 기본, 시스템 설정에 따라 스톤 라이트 자동.
- 강조색은 엔더 청록 하나. 화면의 10% 이하.
- 카드 안의 카드 없음. 표면은 평평하고 1px 이음선으로 나눈다.
- 본문은 IBM Plex Sans KR, 숫자·코드성 데이터는 IBM Plex Mono.
- 움직임은 상태 변화에만, 160~220ms, 튕김 없음.

## Colors

보라 기미가 도는 무채색 바탕 위에 청록 하나가 놓인, 절제된(Restrained) 팔레트.

### Primary
- **엔더 청록 Ender** (#4fd1a5): 주요 동작 버튼 배경, 선택된 칩, 실시간 연결 점, 포커스 링, 고정 아이콘. 라이트 모드에서는 대비를 위해 **깊은 엔더 Ender Deep** (#0a6e53)으로 바꾼다. hover 는 #62dcb3 / #085c45.
- **엔더 잉크 Ender Ink** (#0b1a15): 청록 버튼 위의 글자색. 라이트 모드 청록 버튼 위 글자는 흰색.

### Neutral (다크, 기본)
- **흑요석 Obsidian** (#15161d): 페이지 바탕.
- **솟은 흑요석 Obsidian Raised** (#1c1d26): 입력 영역(컴포저), 다이얼로그, 토스트처럼 바탕 위에 놓인 표면.
- **눌린 흑요석 Obsidian Sunken** (#101117): 표면 안의 입력칸, 코드, 썸네일 자리.
- **hover** (#23242f): 버튼·행 hover 배경.
- **이음선 Seam** (#2b2c39) / **굵은 이음선** (#3a3b4a): 구분선, 컨트롤 테두리 / 입력칸 hover 테두리.
- **밝은 잉크 Ink Light** (#e9e8f1) / **흐린 잉크** (#a3a1b8) / **옅은 잉크** (#8b89a0): 본문 / 보조 정보(출처·시각) / 자리표시자. 셋 다 바탕 대비 4.5:1 이상.

### Neutral (라이트)
- **스톤 Stone** (#f3f2f7) 바탕, **흰 스톤** (#ffffff) 표면, **눌린 스톤** (#ebeaf1), hover (#e9e8f0), 이음선 (#d9d7e3 / #c3c1d0).
- **어두운 잉크 Ink Dark** (#1b1a24) / 흐린 (#5d5b70) / 옅은 (#6b6980).

### Semantic
- **잉걸 Ember** (#e5b85c, 라이트 #8a5d06): 연결 중, 곧 만료(1시간 미만).
- **장미 Rose** (#f0708a, 라이트 #c0244a): 오프라인, 오류 토스트, 삭제·폐기 버튼 hover.
- **배경막 Backdrop** (rgba(0, 0, 0, 0.55), 라이트 rgba(27, 26, 36, 0.45)): 다이얼로그 뒤를 가리는 막. 드롭 오버레이는 바탕색 72% 의 **스크림**에 4px 흐림.

### Named Rules
**The One Ender Rule.** 청록은 살아 있는 것에만 쓴다: 주요 동작, 선택, 실시간, 포커스, 고정. 제목·장식·배경 그라데이션에는 절대 쓰지 않는다.
**The Tinted Grey Rule.** 보조 글자는 순수 회색이 아니라 바탕의 색조를 띤 회색(#a3a1b8, #5d5b70)이다. 색 있는 표면 위에 회색 글자를 올리지 않는다.

## Typography

**Display Font:** 없음. 제목도 본문 글꼴의 굵기 차이로만.
**Body Font:** IBM Plex Sans KR (fallback: Apple SD Gothic Neo, Malgun Gothic, sans-serif)
**Label/Mono Font:** IBM Plex Mono (fallback: ui-monospace, Menlo, Consolas)

**Character:** Plex 는 IBM 의 공학 도구 글꼴이다. 무뚝뚝하지 않지만 꾸미지도 않는다. 한글은 Sandoll 이 그린 KR 판이라 한글·라틴·숫자가 한 가족으로 보인다. Plex Mono 는 시각·용량·토큰 같은 데이터를 표처럼 정렬해 준다. Google Fonts 에서 받고, 서비스워커가 캐시한다.

### Hierarchy
- **Headline** (600, 26px, 1.2, -0.02em): 로그인 화면 제목 하나뿐.
- **Title** (600, 16px, 1.3, -0.01em): 상단바 이름, 다이얼로그 제목, 링크·파일 항목의 이름.
- **Body** (400, 15px, 1.55): 텍스트 항목 본문, 입력창, 안내 문장. 본문 폭은 720px 컨테이너 안(약 45~60자).
- **Label** (500, 13px, 1.4): 버튼, 칩, 폼 라벨, 그룹 이름("고정됨", "최근").
- **Data** (Mono 400, 12px, 1.4, tabular-nums): 시각, 파일 크기, 토큰, 단축키(kbd), 함수 주소. 한글이 섞이는 문구("6일 남음", "마지막 사용")는 Label 크기의 Sans 에 tabular-nums.

### Named Rules
**The Data in Mono Rule.** 모노 글꼴은 숫자와 코드성 데이터에만 쓴다. 문장, 버튼, 제목에는 쓰지 않는다. "기술적인 느낌"을 내려고 모노를 쓰는 것은 금지.
**The Weight Steps Rule.** 위계는 크기보다 굵기(400 → 500 → 600)와 색(잉크 → 흐린 잉크)으로 만든다. 26px 를 넘는 글자는 없다.

## Layout

- 한 열, 최대 폭 720px, 가운데 정렬. 좌우 여백 20px(모바일 16px).
- 상단바(56px)는 sticky. 아래 1px 이음선. 구성: 상자 마크 + 이름 + 연결 상태 / 검색 / 설정.
- 상단바 아래 순서: 컴포저(입력 표면) → 종류 필터 칩 한 줄 → 목록.
- 목록은 행(row)의 연속. 행 사이는 1px 이음선, 행 안쪽 세로 여백 14px. 행 구성: 종류 아이콘(32px 사각 자리) / 본문+메타 / 동작 버튼.
- 고정된 항목은 목록 맨 위에 "고정됨" 그룹, 나머지는 "최근" 그룹. 그룹 이름은 Label 크기의 흐린 잉크.
- 간격 척도: 4 / 8 / 12 / 16 / 24 / 40. 그룹 안은 촘촘하게(4~8), 그룹 사이는 넉넉하게(16~24), 제목 위가 아래보다 넓게.
- 반응형은 구조적으로: 600px 이하에서 동작 버튼이 항상 보이고(hover 없음), 검색칸이 좁아지며, 컴포저 툴바가 줄바꿈된다. 글자 크기는 고정.

## Elevation & Depth

평평함이 기본이다. 바탕(흑요석) 위에 솟은 표면(솟은 흑요석)을 한 단만 두고, 그 안에 눌린 입력칸을 둔다. 세 단의 밝기 차이와 1px 이음선이 깊이의 전부다. 그림자는 화면 위에 떠 있는 것에만 붙는다.

### Shadow Vocabulary
- **Floating** (`box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.5)`, 라이트 `rgba(27, 26, 36, 0.18)`): 다이얼로그, 토스트, 드롭 오버레이 안의 상자. 오프셋과 흐림이 있는 진짜 그림자.

### Named Rules
**The Flat Rule.** 목록 행, 컴포저, 칩, 버튼에는 그림자가 없다. 깊이는 밝기 단과 이음선으로만 낸다. 오프셋 0 의 색 있는 광채(glow)는 장식이므로 쓰지 않는다.

## Shapes

- 컨트롤(버튼, 입력칸, 아이콘 버튼, 세그먼트) 8px. 컨테이너(컴포저, 다이얼로그, 토스트, 드롭 상자) 12px. 칩과 상태 점은 완전한 원(pill). 썸네일 6px. 글 속 작은 조각(code, kbd, 스켈레톤 막대) 4px.
- 테두리는 전부 1px. 색 있는 굵은 왼쪽 테두리로 강조하지 않는다.
- 상자 마크: 모서리가 둥근 사각 몸체, 뚜껑 선, 가운데 청록 눈. 앱 아이콘과 상단바 마크가 같은 형태다.

## Components

### Buttons
- **Shape:** 8px 모서리, 높이 36px(아이콘 버튼 32px), Label 글꼴.
- **Primary:** 엔더 청록 배경 + 엔더 잉크 글자, 굵기 600, 패딩 8px 14px. 라이트는 깊은 엔더 + 흰 글자.
- **Hover / Focus:** hover 는 밝은 엔더(#62dcb3). `:active` 는 1px 아래로. `:focus-visible` 은 청록 2px 외곽선, 2px 띄움. 전환 160ms ease-out.
- **Ghost:** 투명 배경 + 1px 이음선 테두리 + 흐린 잉크. hover 시 배경 hover 색, 글자 잉크.
- **Icon:** 32px 정사각, 투명, 흐린 잉크. hover 시 배경 hover 색. 삭제·폐기는 hover 시 장미색. 모든 아이콘 버튼은 `aria-label` 과 `title` 을 가진다.
- **Disabled:** 불투명도 0.5, 커서 not-allowed.

### Chips (종류 필터)
- **Style:** pill, 1px 이음선 테두리, 흐린 잉크 글자, 패딩 4px 10px, Label 글꼴. 개수는 Mono 로 뒤에.
- **State:** 선택 = 청록 글자 + 청록 12% 배경 + 청록 테두리. hover = hover 배경. 키보드로 이동 가능(role="radiogroup").

### List Row (항목)
- 카드가 아니다. 행 위에 1px 이음선, 세로 패딩 14px, 배경 없음. hover 시 배경 hover 색(행 전체, 좌우로 8px 삐져나감).
- 왼쪽 32px 사각 자리에 종류 아이콘(텍스트·링크·이미지·파일). 이미지는 64px 썸네일이 자리를 대신한다.
- 본문: 텍스트는 8줄까지 보이고 넘치면 "펼치기". 링크는 제목(Title) + URL(흐린 잉크, 한 줄 말줄임). 파일은 이름(Title) + 크기(Data).
- 메타 줄: 출처 기기 · 시각 · 남은 기간. 12px 흐린 잉크, 시각만 Data(Mono). 1시간 미만이면 남은 기간이 잉걸색.
- 동작 버튼(복사·열기·다운로드·공유·고정·삭제)은 오른쪽 위. 데스크톱은 불투명도 0.55 로 있다가 행 hover/focus 시 1. 터치 기기는 항상 1.
- 고정된 행: 고정 아이콘이 청록으로 채워진다. 그 외 표시 없음.
- 새로 도착한 행(다른 기기에서 넣은 것)은 220ms 동안 위에서 4px 내려오며 나타난다. 이것이 이 화면의 유일한 연출이다.

### Composer (입력 표면)
- 솟은 흑요석 배경, 1px 이음선, 12px 모서리, 패딩 12px. 안에 투명 배경의 textarea(최소 2줄, 세로 늘림 가능)와 툴바.
- 표면이 `:focus-within` 이면 테두리가 청록으로 바뀐다(이것이 입력칸의 포커스 표시다).
- 툴바: 왼쪽에 "만료" 세그먼트(1시간·1일·7일·영구), 오른쪽에 파일 선택(Ghost, 클립 아이콘)과 넣기(Primary, Enter 아이콘). 600px 이하에서는 세그먼트가 한 줄을 다 쓰고 버튼 둘이 다음 줄 오른쪽에 붙는다.
- 세그먼트: pill 컨테이너(눌린 흑요석 배경) 안의 라디오. 선택은 solid hover 색 + 잉크 글자.

### Inputs / Fields
- **Style:** 눌린 흑요석 배경, 1px 이음선, 8px, 패딩 9px 12px, Body 글꼴. 라벨은 위에(Label, 흐린 잉크), 도움말은 아래에(Data 크기, 흐린 잉크).
- **Focus:** 테두리 청록 + 3px 청록 12% 링. 캐럿은 청록.
- **Search:** 왼쪽에 돋보기 아이콘, 오른쪽에 kbd `/`. 폭 220px. 600px 이하에서는 남는 폭을 채우되 최대 200px, kbd 숨김.

### Dialog (설정)
- `<dialog>`. 솟은 흑요석, 12px, 패딩 20px, Floating 그림자, 배경막 rgba(0,0,0,0.55). 폭 min(460px, 100vw - 32px).
- 머리: 제목(Title) + 닫기 아이콘 버튼. 구역(기기 이름, 기본 만료, 단축어 토큰)은 1px 이음선으로 나눈다. 꼬리: 로그아웃(Ghost) / 닫기(Primary).

### Toast
- 아래 가운데, 솟은 흑요석, 1px 이음선, 12px, Floating 그림자, Label 글꼴(13px 500), 왼쪽에 아이콘(확인=청록, 오류=장미). 오류는 테두리도 장미. 3.5초 후 사라진다. popover 로 띄워 다이얼로그 위에도 보인다.

### Empty / Loading
- 비어 있음: 큰 상자 마크(48px, 흐린 잉크) + "상자가 비어 있어요" + 넣는 방법 세 줄(아이콘 + 문장 + kbd). 가르치는 빈 화면.
- 로딩: 행 모양 스켈레톤 3개(이음선 색 막대, 1.2초 흐름). 가운데 스피너 없음.

### Menu (만료 연장)
- 메타 줄의 남은 기간은 점선 밑줄 버튼(`.meta-btn`). 누르면 바로 아래에 작은 메뉴: 솟은 흑요석, 1px 이음선, 8px, Floating 그림자, 항목은 아이콘 + 글자 13px, hover 배경 hover 색. 바깥 클릭·Esc 로 닫힌다.

### Banner (오프라인 · 오류)
- 칩 아래, 목록 위. 솟은 흑요석, 1px 이음선, 8px, 패딩 8px 12px, 13px 흐린 잉크. 아이콘은 잉걸(오프라인) 또는 장미(오류). 오류 배너는 오른쪽에 "다시 시도" Ghost 버튼. 한 번에 하나만 보인다.

### Row Editor (텍스트 편집)
- 본문 자리에 눌린 흑요석 textarea(최소 80px)와 그 아래 저장(Primary)·취소(Ghost)·단축키 힌트(12px 흐린 잉크). 다른 행은 그대로.

### Code Text
- 코드처럼 보이는 텍스트(두 줄 이상, 대부분의 줄에 괄호·대입·명령어)는 Plex Mono 13px, 눌린 흑요석 배경, 1px 이음선, 8px, 패딩 8px 10px, 가로 스크롤. 12줄까지 보이고 "펼치기".

### Keyboard Focus (행)
- 활성 행 하나만 Tab 순서에 들어간다. `:focus-visible` 이면 청록 2px 안쪽 외곽선 + hover 배경. j/k 로 옮기고 c·Enter·e·d·p·x 가 행의 버튼을 대신 누른다. 버튼 툴팁에 단축키를 괄호로 적는다.

### Favicon
- https 링크는 종류 슬롯에 사이트 파비콘(16px, 4px 모서리)을 시도하고, 못 받으면 링크 아이콘 그대로.

### Toast with action
- 토스트 오른쪽에 청록 글자 버튼 하나("되돌리기"). 배경 없음, hover 시 청록 12%. 삭제 유예 5초와 표시 시간이 같다.

### Meter (파일 용량)
- 6px 높이 pill 트랙(눌린 흑요석 + 1px 이음선) 위에 청록 채움. 아래에 "168.4 MB / 1 GB" 를 Data 글꼴로.

### Theme Segment
- 설정의 자동/다크/라이트 세그먼트는 만료 세그먼트와 같은 부품에 13px 아이콘(모니터·달·해)을 앞에 붙인 것. 라이트 고정은 `:root[data-theme='light']`, 다크 고정은 `data-theme='dark'` 가 시스템 라이트를 덮는다.

### Signature: 상자 마크
- 24px 상단바 마크와 512px 앱 아이콘이 같은 도형: 둥근 사각 몸체(솟은 흑요석, 굵은 이음선 테두리), 뚜껑 선, 가운데 청록 눈. 청록이 화면에 처음 등장하는 자리다.

## Do's and Don'ts

### Do:
- **Do** 모든 색을 `:root` 토큰으로 정의하고, 라이트 모드는 `prefers-color-scheme: light` 와 `:root[data-theme='light']` 두 곳에서 같은 토큰 값을 쓴다(둘은 항상 같게 유지).
- **Do** 아이콘은 `src/components/Icon.tsx` 의 SVG 만 쓴다(24 viewBox, 1.75 stroke, round cap). 새 아이콘도 같은 굵기로 그린다.
- **Do** 상태 전부를 갖춘다: hover, focus-visible, active, disabled, loading(스켈레톤), empty, error(토스트).
- **Do** 브라우저 기본 표면도 팔레트로 맞춘다: `::selection`, `caret-color`, `accent-color`, 스크롤바, 포커스 링, 밑줄 오프셋.
- **Do** 움직임은 `prefers-reduced-motion: reduce` 에서 전부 끈다.
- **Do** 새 화면을 만들기 전에 이 파일을 읽고, 끝나면 `npx --yes impeccable@latest detect src` 로 검사한다.

### Don't:
- **Don't** Inter, Roboto, 시스템 기본 글꼴을 쓰지 않는다. 글꼴은 IBM Plex Sans KR 과 IBM Plex Mono 뿐.
- **Don't** 보라·파랑 계열 그라데이션 배경을 쓰지 않는다. 그라데이션 자체를 쓰지 않는다.
- **Don't** 카드 안에 카드를 넣지 않는다. 목록 항목은 카드가 아니라 행이다.
- **Don't** 색 있는 배경 위에 회색 본문을 올리지 않는다.
- **Don't** 튕기는(bounce, overshoot) 이징을 쓰지 않는다. `cubic-bezier(0.2, 0.8, 0.2, 1)` 하나만.
- **Don't** 이모지를 아이콘 대신 쓰지 않는다.
- **Don't** 청록을 장식(제목 색, 배경 띠, 광채)에 쓰지 않는다.
- **Don't** 순수 검정(#000)과 순수 회색 보조 글자를 쓰지 않는다.
