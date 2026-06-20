// quiz.js — 단어 퀴즈 (간격 반복 SRS)

let words = [];
let idx = 0;
let correctCount = 0;
let answered = false;

const quizEmpty = document.getElementById("quizEmpty");
const quizCard = document.getElementById("quizCard");
const quizDone = document.getElementById("quizDone");
const quizCount = document.getElementById("quizCount");
const quizScore = document.getElementById("quizScore");
const quizMeaning = document.getElementById("quizMeaning");
const quizForm = document.getElementById("quizForm");
const quizInput = document.getElementById("quizInput");
const quizResult = document.getElementById("quizResult");
const quizVerdict = document.getElementById("quizVerdict");
const quizAnswer = document.getElementById("quizAnswer");
const quizExample = document.getElementById("quizExample");
const quizNext = document.getElementById("quizNext");
const quizDoneText = document.getElementById("quizDoneText");

function show(el, on = true) { el.classList.toggle("hidden", !on); }
function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

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
  quizInput.value = "";
  quizInput.disabled = false;
  show(quizResult, false);
  show(quizForm, true);
  quizInput.focus();
}

quizForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (answered) return;
  const w = words[idx];
  const guess = quizInput.value.trim().toLowerCase();
  if (!guess) return;
  const correct = guess === (w.word || "").trim().toLowerCase();
  answered = true;

  if (correct) correctCount++;
  quizVerdict.textContent = correct ? "✅ 정답!" : "❌ 아쉬워요";
  quizVerdict.className = "quiz-verdict " + (correct ? "ok" : "no");
  quizAnswer.innerHTML =
    `<b>${esc(w.word)}</b> ${esc(w.pronunciation || "")} ${window.speakBtn(w.word)}` +
    `<span class="qa-mean"> — ${esc(w.meaning)}</span>`;
  quizExample.innerHTML = w.example
    ? `“${esc(w.example)}” ${window.speakBtn(w.example)}<br><span>${esc(w.example_kr || "")}</span>`
    : "";
  quizInput.disabled = true;
  show(quizForm, false);
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

loadQuiz();
