# English World

화면(HTML/CSS/JS)을 만들거나 고칠 때는 아래 두 문서를 먼저 읽고 따른다.

@DESIGN.md
@DESIGN-GUIDE.md

- 공통 레이아웃은 `templates/base.html`, 아이콘은 `templates/_icons.html`(SVG 스프라이트), 공통 JS 유틸은 `static/common.js`.
- 검사: 페이지를 렌더링한 HTML 과 `static/` 에 `npx --yes impeccable@latest detect <폴더>` — 아무것도 안 나오면 통과.
- 테스트: `python -m pytest -q`
