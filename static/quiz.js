// quiz.js — 단어 퀴즈 (간격 반복 SRS · 객관식/주관식)
// 공통 유틸(postJSON, show, esc …)은 common.js 에 있다.

let words = [];
let idx = 0;
let correctCount = 0;
let answered = false;
let quizMode = "choice"; // choice | typing
try { quizMode = localStorage.getItem("quizMode") || "choice"; } catch (e) { /* 저장소 차단 */ }

const quizLoading = document.getElementById("quizLoading");
const quizEmpty = document.getElementById("quizEmpty");
const quizCard = document.getElementById("quizCard");
const quizDone = document.getElementById("quizDone");
const quizCount = document.getElementById("quizCount");
const quizScore = document.getElementById("quizScore");
const quizBar = document.getElementById("quizBar");
const quizMeaning = document.getElementById("quizMeaning");
const quizForm = document.getElementById("quizForm");
const quizInput = document.getElementById("quizInput");
const quizChoices = document.getElementById("quizChoices");
const quizResult = document.getElementById("quizResult");
const quizVerdict = document.getElementById("quizVerdict");
const quizAnswer = document.getElementById("quizAnswer");
const quizExample = document.getElementById("quizExample");
const quizNext = document.getElementById("quizNext");
const quizDoneText = document.getElementById("quizDoneText");
const quizDoneScore = document.getElementById("quizDoneScore");
const dueCount = document.getElementById("dueCount");
const modeChoiceBtn = document.getElementById("modeChoice");
const modeTypingBtn = document.getElementById("modeTyping");

// 편집거리(레벤슈타인) — 주관식 오타 허용 판정에 사용
function editDistance(a, b) {
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, (_, i) => [i, ...Array(n).fill(0)]);
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
  }
  return dp[m][n];
}

// ---- 모드 전환 ----
function applyModeButtons() {
  modeChoiceBtn.classList.toggle("active", quizMode === "choice");
  modeTypingBtn.classList.toggle("active", quizMode === "typing");
  modeChoiceBtn.setAttribute("aria-pressed", quizMode === "choice");
  modeTypingBtn.setAttribute("aria-pressed", quizMode === "typing");
}

function setMode(mode) {
  quizMode = mode;
  try { localStorage.setItem("quizMode", mode); } catch (e) { /* 이번 방문만 적용 */ }
  applyModeButtons();
  if (!answered && words.length > 0 && idx < words.length) renderQuestion();
}

modeChoiceBtn.addEventListener("click", () => setMode("choice"));
modeTypingBtn.addEventListener("click", () => setMode("typing"));

// ---- 퀴즈 로딩/출제 ----
async function loadQuiz() {
  show(quizDone, false);
  show(quizCard, false);
  show(quizEmpty, false);
  show(quizLoading, true);
  try {
    const data = await getJSON("/api/quiz");
    words = data.words || [];
  } catch (e) {
    words = [];
    toast(e.message, "error");
  }
  idx = 0;
  correctCount = 0;
  show(quizLoading, false);
  if (words.length === 0) {
    show(quizEmpty, true);
  } else {
    show(quizCard, true);
    renderQuestion();
  }
}

function renderQuestion() {
  answered = false;
  const w = words[idx];
  quizMeaning.textContent = w.meaning;
  quizCount.textContent = `${idx + 1} / ${words.length}`;
  quizScore.textContent = correctCount;
  quizBar.style.width = `${(idx / words.length) * 100}%`;
  show(quizResult, false);

  if (quizMode === "choice" && (w.choices || []).length >= 2) {
    show(quizForm, false);
    quizChoices.innerHTML = w.choices.map((c, i) =>
      `<button type="button" class="choice quiz-choice" data-word="${esc(c)}"><span class="key-hint">${i + 1}</span><span>${esc(c)}</span></button>`).join("");
    show(quizChoices, true);
  } else {
    show(quizChoices, false);
    quizInput.value = "";
    quizInput.disabled = false;
    show(quizForm, true);
    quizInput.focus();
  }
}

// ---- 채점 (공통) ----
async function grade(correct, note = "") {
  if (answered) return;
  answered = true;
  const w = words[idx];

  if (correct) correctCount++;
  quizVerdict.innerHTML = correct
    ? `${icon("circle-check")}정답${note ? ` <span class="hint" style="margin:0">${esc(note)}</span>` : ""}`
    : `${icon("circle-x")}아쉬워요`;
  quizVerdict.className = "verdict " + (correct ? "ok" : "no");
  quizAnswer.innerHTML =
    `<b>${esc(w.word)}</b><span class="pron">${esc(w.pronunciation || "")}</span>${window.speakBtn(w.word)}` +
    `<span class="qa-mean">${esc(w.meaning)}</span>`;
  quizExample.innerHTML = w.example
    ? `&ldquo;${esc(w.example)}&rdquo; ${window.speakBtn(w.example)}<span>${esc(w.example_kr || "")}</span>`
    : "";
  show(quizForm, false);
  // 객관식 보기는 색칠(정답/오답)이 보이도록 남겨둔다 — 다음 문제에서 새로 그림
  show(quizResult, true);
  quizScore.textContent = correctCount;
  quizBar.style.width = `${((idx + 1) / words.length) * 100}%`;
  quizNext.focus({ preventScroll: true });

  // SRS 일정 갱신
  try {
    const data = await postJSON("/api/quiz/answer", { id: w.id, correct });
    if (data.due_count !== undefined) dueCount.textContent = data.due_count;
  } catch (e) { /* 채점 실패해도 진행은 계속 */ }
}

// ---- 주관식 제출 ----
quizForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (answered) return;
  const w = words[idx];
  const guess = quizInput.value.trim().toLowerCase();
  if (!guess) return;
  const answer = (w.word || "").trim().toLowerCase();

  if (guess === answer) {
    grade(true);
  } else if (answer.length >= 4 && editDistance(guess, answer) === 1) {
    // 오타 1글자는 아는 것으로 인정하되 정확한 철자를 보여준다
    grade(true, "오타 주의 — 철자를 확인하세요");
  } else {
    grade(false);
  }
  quizInput.disabled = true;
});

// ---- 객관식 선택 ----
function pick(btn) {
  if (!btn || answered) return;
  const w = words[idx];
  const picked = btn.dataset.word.trim().toLowerCase();
  const answer = (w.word || "").trim().toLowerCase();
  // 정답/오답 색칠
  quizChoices.querySelectorAll(".quiz-choice").forEach((b) => {
    b.disabled = true;
    const bw = b.dataset.word.trim().toLowerCase();
    if (bw === answer) b.classList.add("correct");
    else if (bw === picked) b.classList.add("wrong");
  });
  grade(picked === answer);
}
quizChoices.addEventListener("click", (e) => pick(e.target.closest(".quiz-choice")));

function next() {
  idx++;
  if (idx >= words.length) finish();
  else renderQuestion();
}
quizNext.addEventListener("click", next);

// 키보드: 1~4 = 보기 선택, Enter = 다음 문제
document.addEventListener("keydown", (e) => {
  if (quizCard.classList.contains("hidden")) return;
  if (answered && e.key === "Enter" && e.target !== quizNext) { e.preventDefault(); next(); return; }
  if (e.target.matches("input, textarea")) return;
  const n = Number(e.key);
  if (!answered && n >= 1 && n <= 4 && !quizChoices.classList.contains("hidden")) {
    pick(quizChoices.querySelectorAll(".quiz-choice")[n - 1]);
  }
});

function finish() {
  show(quizCard, false);
  show(quizDone, true);
  quizDoneScore.textContent = `${correctCount} / ${words.length}`;
  const rate = Math.round((correctCount / words.length) * 100);
  quizDoneText.textContent = rate === 100
    ? "모두 맞혔어요. 다음 복습 간격이 늘어났습니다."
    : `정답률 ${rate}%. 틀린 단어는 오늘 다시 나옵니다.`;
}

document.getElementById("quizReload").addEventListener("click", loadQuiz);

applyModeButtons();
loadQuiz();
