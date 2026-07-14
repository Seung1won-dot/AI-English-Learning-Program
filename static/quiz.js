// quiz.js — 단어 퀴즈 (간격 반복 SRS · 객관식/주관식)

let words = [];
let idx = 0;
let correctCount = 0;
let answered = false;
let quizMode = localStorage.getItem("quizMode") || "choice"; // choice | typing

const quizEmpty = document.getElementById("quizEmpty");
const quizCard = document.getElementById("quizCard");
const quizDone = document.getElementById("quizDone");
const quizCount = document.getElementById("quizCount");
const quizScore = document.getElementById("quizScore");
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
const modeChoiceBtn = document.getElementById("modeChoice");
const modeTypingBtn = document.getElementById("modeTyping");

function show(el, on = true) { el.classList.toggle("hidden", !on); }
function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

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
}

function setMode(mode) {
  quizMode = mode;
  localStorage.setItem("quizMode", mode);
  applyModeButtons();
  if (!answered && words.length > 0) renderQuestion();
}

modeChoiceBtn.addEventListener("click", () => setMode("choice"));
modeTypingBtn.addEventListener("click", () => setMode("typing"));

// ---- 퀴즈 로딩/출제 ----
async function loadQuiz() {
  const res = await fetch("/api/quiz");
  const data = await res.json();
  words = data.words || [];
  idx = 0;
  correctCount = 0;
  show(quizDone, false);
  if (words.length === 0) {
    show(quizEmpty, true);
    show(quizCard, false);
  } else {
    show(quizEmpty, false);
    show(quizCard, true);
    renderQuestion();
  }
}

function renderQuestion() {
  answered = false;
  const w = words[idx];
  quizMeaning.textContent = w.meaning;
  quizCount.textContent = `${idx + 1} / ${words.length}`;
  quizScore.textContent = `맞은 개수 ${correctCount}`;
  show(quizResult, false);

  if (quizMode === "choice" && (w.choices || []).length >= 2) {
    show(quizForm, false);
    quizChoices.innerHTML = w.choices.map((c) =>
      `<button class="quiz-choice" data-word="${esc(c)}">${esc(c)}</button>`).join("");
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
  quizVerdict.textContent = correct ? (note ? `✅ 정답! ${note}` : "✅ 정답!") : "❌ 아쉬워요";
  quizVerdict.className = "quiz-verdict " + (correct ? "ok" : "no");
  quizAnswer.innerHTML =
    `<b>${esc(w.word)}</b> ${esc(w.pronunciation || "")} ${window.speakBtn(w.word)}` +
    `<span class="qa-mean"> — ${esc(w.meaning)}</span>`;
  quizExample.innerHTML = w.example
    ? `“${esc(w.example)}” ${window.speakBtn(w.example)}<br><span>${esc(w.example_kr || "")}</span>`
    : "";
  show(quizForm, false);
  // 객관식 보기는 색칠(정답/오답)이 보이도록 남겨둔다 — 다음 문제에서 새로 그림
  show(quizResult, true);
  quizScore.textContent = `맞은 개수 ${correctCount}`;

  // SRS 일정 갱신
  try {
    await fetch("/api/quiz/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: w.id, correct }),
    });
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
    grade(true, "(오타 주의 — 철자를 확인하세요)");
  } else {
    grade(false);
  }
  quizInput.disabled = true;
});

// ---- 객관식 선택 ----
quizChoices.addEventListener("click", (e) => {
  const btn = e.target.closest(".quiz-choice");
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
});

quizNext.addEventListener("click", () => {
  idx++;
  if (idx >= words.length) finish();
  else renderQuestion();
});

function finish() {
  show(quizCard, false);
  show(quizDone, true);
  quizDoneText.textContent = `${words.length}문제 중 ${correctCount}개 정답!`;
}

document.getElementById("quizReload").addEventListener("click", loadQuiz);

applyModeButtons();
loadQuiz();
