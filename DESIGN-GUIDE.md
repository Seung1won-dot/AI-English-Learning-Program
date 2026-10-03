# 디자인 가이드 (AI 티 없는 화면 만들기)

이 파일이 있는 폴더에서 화면(UI)을 만들 때 따르는 기준입니다.
클로드 코드 같은 AI 코딩 도구가 이 파일을 읽고 같은 기준으로 개발하도록 만들어졌습니다.
다른 PC에서도 이 파일을 프로젝트 폴더에 두고 아래 순서대로 준비하면 같은 방식으로 작업할 수 있습니다.

클로드에게 디자인을 맡기면 매번 비슷한 화면이 나옵니다. 같은 글꼴, 보라색 그라데이션, 카드 안의 카드.
이 가이드는 그 기본값을 벗어나기 위해 스킬 두 개를 설치하고, 디자인 기준을 파일로 남기고, 검사 명령으로 확인하는 순서를 담았습니다.

---

## AI에게 주는 작업 규칙 (화면을 만들 때마다 적용)

1. 화면이나 스타일(HTML, CSS, 컴포넌트) 파일을 만들거나 고치기 전에 이 폴더의 `DESIGN.md`를 먼저 읽고, 거기 적힌 색과 글꼴을 그대로 쓴다.
2. `DESIGN.md`가 없으면 화면을 만들기 전에 `/impeccable init`으로 기준 파일을 먼저 만들자고 안내한다. 기준이 없으면 AI는 학습된 기본값인 무난한 화면으로 되돌아간다.
3. 아래 다섯 가지는 쓰지 않는다.
   - Inter, Roboto, 시스템 기본 글꼴
   - 보라나 파랑 계열 그라데이션 배경
   - 카드 안에 카드를 넣는 구조
   - 색 있는 배경 위의 회색 본문
   - 튕기는 바운스 효과
4. 다 만든 뒤 위 다섯 항목을 하나씩 점검하고 결과를 알려 준다.
5. 마지막에 `npx --yes impeccable@latest detect <검사할 폴더>`를 실행해 지적 항목을 고치고, 아무것도 나오지 않을 때까지 반복한다.

---

## 새 PC에서 준비하기

### 복사해서 바로 시작하는 프롬프트: 설치부터 검증까지 AI에게 맡기기

```
역할: 디자인 스킬 두 개의 설치와 연결 검증을 맡는 담당
맥락: 이 프로젝트에는 아직 디자인 스킬이 설치되지 않았을 수 있고, 화면을 만들면 AI가 만든 티가 나는 상태입니다
입력: <운영체제와 셸, 예: macOS zsh>, <기술 스택, 예: HTML과 CSS만 사용>, <목표 한 줄, 예: 랜딩 페이지를 AI 티 없이 만들고 싶다>
작업: 아래 네 단계를 순서대로 진행하세요.
1. 설치 여부 확인: `node --version`을 실행해 22.12 이상인지 확인하고, `.claude/skills` 폴더에 design-taste-frontend와 impeccable이 이미 있는지 확인하세요. 이미 있으면 다시 설치하지 말고 상태만 보고하세요.
2. 미설치 시 설치: 프로젝트 루트에서 `npx --yes skills@latest add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend" --agent claude-code --yes --copy`를 실행한 뒤, `npx --yes impeccable@latest install --providers=claude --scope=project`를 실행하세요.
3. 연결 검증: `ls .claude/skills`로 폴더 두 개를 확인하고, 아무 CSS나 HTML 파일 하나를 대상으로 `npx --yes impeccable@latest detect <파일경로>`를 실제로 실행해 출력이 나오는지 확인하세요.
4. 마지막에 두 스킬이 각각 무엇을 하는 도구이고 앞으로 어떻게 쓰면 되는지, 개발을 처음 하는 사람도 이해할 수 있는 말로 5줄 이내로 설명하세요.
제약: 기존 파일과 설정을 덮어쓰거나 지우지 마세요. `npm install -g`는 사용하지 마세요. .env와 API 키가 들어 있는 파일은 읽지도 출력하지도 마세요. 이미 설치된 항목은 중복 설치하지 마세요.
출력: 실제로 실행한 명령 목록, 확인된 Node 버전, 새로 생긴 폴더와 파일, 남아 있는 오류를 정리해 주세요.
검증: `ls .claude/skills`에 design-taste-frontend와 impeccable 두 폴더가 보이고, `npx --yes impeccable@latest detect <파일경로>`가 오류 없이 끝나야 합니다. 하나라도 실패하면 완료로 보고하지 말고 실패한 명령과 원인, 다음 조치를 알려주세요.
```

### Quick Start

- 공식 사이트: tasteskill.dev · impeccable.style
- 공식 GitHub: Leonxlnx/taste-skill · pbakaus/impeccable

작업할 프로젝트 폴더로 이동한 다음, 아래 두 줄을 터미널에 차례로 붙여넣으세요. 스킬 두 개를 이 프로젝트에 설치하는 명령입니다.

```bash
npx --yes skills@latest add https://github.com/Leonxlnx/taste-skill \
  --skill "design-taste-frontend" --agent claude-code --yes --copy
npx --yes impeccable@latest install --providers=claude --scope=project
```

Windows PowerShell에서는 줄 끝의 `\`가 동작하지 않으므로 첫 명령을 한 줄로 입력합니다.

```powershell
npx --yes skills@latest add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend" --agent claude-code --yes --copy
npx --yes impeccable@latest install --providers=claude --scope=project
```

성공하면 `design-taste-frontend (copied)`와 `Installed impeccable into: .claude (project)` 같은 줄이 보입니다.

설치가 됐는지 확인하는 명령입니다.

```bash
ls .claude/skills
```

`design-taste-frontend`와 `impeccable` 두 폴더 이름이 나오면 성공입니다.

### 이 가이드를 AI가 자동으로 읽게 하기

프로젝트 폴더의 `CLAUDE.md`에 아래 한 줄을 넣으면 클로드 코드가 대화를 시작할 때마다 이 파일을 함께 읽습니다. `CLAUDE.md`가 없으면 새로 만들면 됩니다.

```
@DESIGN-GUIDE.md
```

---

## 설치부터 검사까지 전체 흐름

### STEP 1. 준비물 확인: 2분

이 단계에서는 명령이 도중에 멈추지 않도록 Node.js 버전을 먼저 확인합니다. 두 스킬 모두 Node.js로 동작하고, 버전이 낮으면 설치가 실패합니다.

용어: Node.js는 컴퓨터에서 자바스크립트를 실행해 주는 프로그램입니다. 여기서는 설치 명령을 돌리는 데만 씁니다.

설치된 Node.js 버전을 확인하는 명령입니다.

```bash
node --version
```

`v22.12.0`처럼 v로 시작하는 숫자가 나오면 됩니다. 앞자리가 22보다 작거나 명령을 찾을 수 없다고 나오면 nodejs.org에서 LTS 버전을 먼저 설치하세요.

용어: 터미널은 명령어를 글로 입력하는 검은 창입니다. macOS는 터미널 앱, Windows는 PowerShell을 쓰면 됩니다.

### STEP 2. 스킬 두 개 설치: 3분

이 단계에서는 클로드에게 디자인 감각과 검사 능력을 붙입니다. 둘은 하는 일이 달라서 같이 설치해야 효과가 납니다.

먼저 작업할 프로젝트 폴더로 이동합니다. 폴더 안에서 명령을 실행해야 그 프로젝트에만 설치됩니다.

```bash
cd <프로젝트 폴더 경로>
```

첫 번째 스킬을 설치하는 명령입니다. 배치와 움직임의 기준을 바꿔서 평범한 화면에 머무르지 않게 합니다.

```bash
npx --yes skills@latest add https://github.com/Leonxlnx/taste-skill \
  --skill "design-taste-frontend" --agent claude-code --yes --copy
```

성공하면 `✓ design-taste-frontend (copied)`와 함께 `→ ./.claude/skills/design-taste-frontend` 경로가 표시됩니다.

두 번째 스킬을 설치하는 명령입니다. 디자인 기준을 만들고 어긋난 곳을 잡아냅니다.

```bash
npx --yes impeccable@latest install --providers=claude --scope=project
```

성공하면 `Installed impeccable into: .claude (project)`와 `Installed hooks into: .claude`가 나오고, 마지막에 `/impeccable init`을 실행하라는 안내가 붙습니다.

용어: 스킬은 AI에게 미리 읽히는 작업 지침서 파일입니다. 설치하면 대화할 때마다 AI가 알아서 참고합니다.

설치가 끝나면 클로드 코드를 완전히 종료했다가 다시 켜세요. 새로 켜야 방금 넣은 스킬을 읽습니다.

### STEP 3. 디자인 기준 만들기: 5분

이 단계가 이 가이드에서 가장 중요합니다. 스킬만 설치하고 여기서 멈추면 결과가 거의 바뀌지 않습니다. 참고할 기준이 없으면 AI는 학습된 기본값인 무난한 화면으로 되돌아가기 때문입니다.

클로드 코드를 켠 상태에서 아래를 입력하세요. 이 프로젝트의 디자인 기준을 만드는 명령입니다.

```
/impeccable init
```

실행하면 이 화면이 브랜드용인지 제품용인지 묻고, 대상 독자와 색, 글꼴, 분위기를 차례로 물어봅니다. 답을 마치면 `PRODUCT.md`와 `DESIGN.md` 파일이 만들어집니다.

이제 이 두 파일이 기준점이 됩니다. 다음부터는 대화창을 새로 열어도 AI가 매번 이 파일을 읽고 같은 기준으로 작업합니다.

기준을 정할 때 아래 프롬프트를 그대로 붙여넣으면 색과 글꼴을 함께 정할 수 있습니다.

```
내 브랜드는 <브랜드 한 줄 설명>이고, 주 고객은 <고객층>입니다.
경쟁사와 겹치지 않는 방향으로 아래를 정해 주세요.
1. 주조색 한 가지와 배경색, 본문 글자색을 정하고 각각 왜 그 색인지 한 줄로 설명
2. 제목용 글꼴과 본문용 글꼴을 각각 하나씩 추천 (Inter, Roboto, 시스템 기본 글꼴은 제외)
3. 이 브랜드에서 절대 쓰지 말아야 할 시각 요소 세 가지
결과를 DESIGN.md에 반영해 주세요.
```

용어: `DESIGN.md`는 색과 글꼴 같은 디자인 규칙을 적어 둔 메모 파일입니다. AI가 화면을 만들 때마다 이 파일을 먼저 읽습니다.

### STEP 4. AI 티 다섯 가지 알아두기: 3분

이 단계에서는 무엇을 피해야 하는지 눈에 익혀 둡니다. AI가 만든 티는 취향 문제가 아니라 거의 정해진 목록으로 나타나서, 알고 있으면 지시할 때 바로 짚어낼 수 있습니다.

| 자주 나오는 기본값 | 대신 요청할 것 |
|---|---|
| 글꼴이 늘 Inter나 시스템 기본값 | 브랜드에 맞는 글꼴을 골라 지정 |
| 보라에서 파랑으로 흐르는 그라데이션 | 의도해서 정한 주조색 한 가지 |
| 카드 안에 카드, 그 안에 또 카드 | 여백과 선으로 나눈 납작한 구조 |
| 색 있는 배경 위에 회색 글자 | 배경과 대비를 확보한 본문 색 |
| 튕기는 바운스 효과 | 짧고 자연스럽게 멈추는 움직임 |

화면을 만들 때 아래처럼 요청하면 위 다섯 가지를 미리 막을 수 있습니다.

```
<만들 화면 설명>을 만들어 주세요.
DESIGN.md의 색과 글꼴을 그대로 쓰고, 아래는 쓰지 마세요.
- Inter, Roboto, 시스템 기본 글꼴
- 보라나 파랑 계열 그라데이션 배경
- 카드 안에 카드를 넣는 구조
- 색 있는 배경 위의 회색 본문
- 튕기는 바운스 효과
다 만든 뒤 위 다섯 항목을 하나씩 점검하고 결과를 알려 주세요.
```

### STEP 5. 검사로 확인하기: 3분

이 단계에서는 눈대중 대신 검사 명령으로 확인합니다. 규칙 60개를 기계가 자동으로 확인하기 때문에 놓친 곳이 글로 나옵니다.

만든 파일을 검사하는 명령입니다. `<검사할 폴더>` 자리에 실제 폴더 이름을 넣으세요.

```bash
npx --yes impeccable@latest detect <검사할 폴더>
```

문제가 있으면 아래처럼 어떤 규칙에 걸렸는지와 이유가 함께 나옵니다.

```
src/slop.html
  [overused-font] Primary font: inter
    → Inter는 너무 많이 쓰여 개성이 사라진 글꼴입니다.
  [ai-color-palette] Purple/violet accent colors detected
    → 보라 계열은 AI가 만든 화면의 가장 뚜렷한 신호입니다.

2 anti-patterns found.
```

고칠 곳이 없으면 아무 줄도 나오지 않고 그냥 끝납니다. 조용히 끝나면 통과라는 뜻입니다.

지적받은 내용을 그대로 고치라고 요청할 때 쓰는 프롬프트입니다.

```
`npx --yes impeccable@latest detect <검사할 폴더>`를 실행하고,
나온 항목을 하나씩 고쳐 주세요.
고칠 때마다 DESIGN.md의 색과 글꼴 기준을 지키고,
전부 고친 뒤 같은 명령을 다시 실행해서 아무 것도 나오지 않는지 확인해 주세요.
```

### STEP 6. 화면 보면서 다듬기: 선택

이 단계는 필수가 아닙니다. 코드 대신 화면을 직접 보면서 색과 간격을 고치고 싶을 때만 쓰세요.

Claude Design은 대화로 시안을 만들고, 요소를 눌러 글자와 간격을 직접 고칠 수 있는 도구입니다. 완성한 디자인은 클로드 코드로 넘겨 그대로 개발을 이어갈 수 있습니다.

용어: 디자인 시스템은 브랜드의 색과 글꼴, 버튼 모양을 한 벌로 묶어 둔 규칙 모음입니다.

- 유료 요금제인 Pro, Max, Team, Enterprise에서 쓸 수 있습니다. 무료 요금제에는 없습니다.
- 사용량은 채팅, 클로드 코드와 함께 계산됩니다. 한 곳에서 많이 쓰면 다른 곳이 줄어듭니다.
- 만든 결과는 PPTX, PDF, HTML로 내보낼 수 있습니다.
- Enterprise 요금제는 기본이 꺼짐 상태라 관리자가 조직 설정에서 켜야 합니다.

STEP 3에서 정한 색과 글꼴을 여기에도 그대로 넣으면 결과가 일관됩니다. 시작은 claude.ai/design에서 합니다.

---

## 자주 막히는 곳

| 증상 | 원인 | 해결 |
|---|---|---|
| `command not found: npx` | Node.js가 없음 | nodejs.org에서 LTS 버전 설치 후 터미널 재시작 |
| `Invalid agents: claude` | 도구 이름을 줄여 씀 | `--agent claude`가 아니라 `--agent claude-code`로 입력 |
| 스킬을 설치했는데 결과가 그대로 | STEP 3을 건너뜀 | `/impeccable init`으로 기준 파일을 먼저 만들기 |
| `/impeccable` 명령을 못 알아들음 | 재시작 전 | 클로드 코드를 완전히 종료했다 다시 켜기 |
| detect가 아무것도 출력하지 않음 | 문제가 없는 상태 | 정상입니다. 고칠 곳이 없으면 조용히 끝납니다 |
| Claude Design 메뉴가 안 보임 | 무료 요금제이거나 조직 설정이 꺼짐 | 유료 요금제로 변경, 회사 계정이면 관리자에게 요청 |

---

## 이 순서를 지켜야 하는 이유

스킬 설치는 시작일 뿐입니다. 설치만 하면 AI가 참고할 기준이 없어서 학습된 기본값으로 돌아갑니다. 기준을 파일로 남기는 STEP 3이 결과를 바꾸는 지점입니다.

검사 명령은 그 기준을 지켰는지 확인하는 마지막 관문입니다. 눈으로 보면 놓치지만 규칙 60개는 매번 같은 곳을 짚어냅니다.

정리하면 순서는 이렇습니다. 스킬 설치, 기준 작성, 화면 제작, 검사. 이 중 하나만 빠져도 AI 티가 남습니다.

---

## 공식 자료

- Taste Skill 공식 사이트: tasteskill.dev
- Taste Skill 저장소: github.com/Leonxlnx/taste-skill
- Impeccable 공식 사이트: impeccable.style
- Impeccable 저장소: github.com/pbakaus/impeccable
- Impeccable 검사 규칙 문서: impeccable.style/docs/detector
- Claude Design 제품 소개: claude.com/product/design
- Claude Design 시작하기: claude.ai/design
- Node.js 내려받기: nodejs.org
