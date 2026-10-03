// toeic.js — TOEIC 모드 (빈출 단어 추천 + Part 5 문제 풀기)
// 공통 유틸(postJSON, show, esc, wordCard …)은 common.js 에 있다.

// =========================================================
// 빈출 단어
// =========================================================
let level = "600";

const recommendBtn = document.getElementById("toeicRecommendBtn");
const wordError = document.getElementById("toeicWordError");
const recommendBox = document.getElementById("toeicRecommendBox");
const recommendList = document.getElementById("toeicRecommendList");
const wordFallback = document.getElementById("toeicWordFallback");
const wordList = document.getElementById("toeicWordList");
const wordCount = document.getElementById("toeicCount");
const wordEmpty = document.getElementById("toeicEmpty");

chipGroup(".level-chip", (chip) => { level = chip.dataset.level; });

function refreshCount() {
  const n = wordList.querySelectorAll(".word-item").length;
  wordCount.textContent = n;
  show(wordEmpty, n === 0);
}

recommendBtn.addEventListener("click", async () => {
  show(wordError, false);
  setBusy(recommendBtn, true, "추천 받는 중...");
  try {
    const data = await postJSON("/api/toeic/words", { level });
    show(wordFallback, !!data.fallback);
    recommendList.innerHTML = recommendChips(data.words);
    recommendList._words = data.words;
    show(recommendBox, true);
  } catch (e) {
    showError(wordError, e.message);
  } finally {
    setBusy(recommendBtn, false);
  }
});

recommendList.addEventListener("click", async (e) => {
  const chip = e.target.closest(".recommend-chip");
  if (!chip || chip.classList.contains("picked")) return;
  const w = recommendList._words[Number(chip.dataset.i)];
  markChip(chip, true);
  try {
    const data = await postJSON("/api/word", { ...w, mode: "toeic" });
    wordList.insertAdjacentHTML("afterbegin", wordCard(data, { deletable: true }));
    refreshCount();
    toast(`'${data.word}' 담음`);
  } catch (err) {
    markChip(chip, false);
    showError(wordError, err.message);
  }
});

wordList.addEventListener("click", (e) => {
  const btn = e.target.closest(".word-del");
  if (btn) deleteWord(btn, ".word-item", refreshCount);
});

// =========================================================
// Part 5 문제
// =========================================================
const startBtn = document.getElementById("p5StartBtn");
const retryBtn = document.getElementById("p5RetryBtn");
const retryBadge = document.getElementById("p5RetryBadge");
const nextBtn = document.getElementById("p5NextBtn");
const loading = document.getElementById("p5Loading");
const p5Error = document.getElementById("p5Error");
const p5Fallback = document.getElementById("p5Fallback");
const box = document.getElementById("p5Box");
const questionEl = document.getElementById("p5Question");
const choicesEl = document.getElementById("p5Choices");
const explainBox = document.getElementById("p5Explain");
const verdictEl = document.getElementById("p5Verdict");
const explainText = document.getElementById("p5ExplainText");
const scoreEl = document.getElementById("p5Score");

let current = null;           // 현재 문제
const recentQuestions = [];   // 같은 문제 반복 방지
let solved = 0, correct = 0;  // 이번 세션 점수
let retryQueue = [];          // 오답 다시 풀기 큐 (비어 있으면 새 문제 모드)

const LABELS = ["A", "B", "C", "D"];

function setNextLabel(text) {
  nextBtn.innerHTML = `${esc(text)} ${icon("arrow-right")}`;
}

function renderQuestion(q, isRetry = false) {
  current = q;
  questionEl.textContent = q.question;
  choicesEl.innerHTML = q.choices.map((c, i) => `
    <button type="button" class="choice p5-choice" data-i="${i}">
      <span class="p5-label">${LABELS[i]}</span><span>${esc(c)}</span>
    </button>`).join("");
  show(retryBadge, isRetry);
  show(explainBox, false);
  show(nextBtn, false);
  show(box, true);
  delete choicesEl.dataset.answered;   // 새 문제 → 답변 잠금 해제
}

async function loadQuestion() {
  // 오답 복습 중이면 큐에서 먼저 꺼낸다
  if (retryQueue.length > 0) {
    renderQuestion(retryQueue.shift(), true);
    setNextLabel(retryQueue.length > 0 ? `다음 오답 (${retryQueue.length}개 남음)` : "다음 문제");
    return;
  }

  show(p5Error, false);
  show(p5Fallback, false);
  show(loading, true);
  startBtn.disabled = true;
  nextBtn.disabled = true;
  try {
    const q = await postJSON("/api/toeic/question", { recent: recentQuestions });
    recentQuestions.push(q.question);
    if (recentQuestions.length > 10) recentQuestions.shift();
    renderQuestion(q, false);
    setNextLabel("다음 문제");
    startBtn.textContent = "새 문제 받기";
    show(p5Fallback, !!q.fallback);
  } catch (e) {
    showError(p5Error, e.message);
  } finally {
    show(loading, false);
    startBtn.disabled = false;
    nextBtn.disabled = false;
  }
}

async function loadWrongQuestions() {
  show(p5Error, false);
  setBusy(retryBtn, true, "불러오는 중...");
  try {
    const data = await getJSON("/api/toeic/wrong");
    retryQueue = (data.questions || []).map((q) => ({
      question: q.question,
      choices: q.choices,
      answer: q.correct_answer,
      explanation: q.explanation,
    }));
    if (retryQueue.length === 0) {
      toast("다시 풀 오답이 없어요. 틀린 문제를 다시 맞히면 목록에서 빠집니다.");
      return;
    }
    loadQuestion();
  } catch (e) {
    showError(p5Error, e.message);
  } finally {
    setBusy(retryBtn, false);
  }
}

startBtn.addEventListener("click", () => { retryQueue = []; loadQuestion(); });
retryBtn.addEventListener("click", loadWrongQuestions);
nextBtn.addEventListener("click", loadQuestion);

async function answer(my) {
  if (!current || choicesEl.dataset.answered) return;
  choicesEl.dataset.answered = "1";

  const ok = my === current.answer;
  solved += 1;
  if (ok) correct += 1;

  // 보기 색칠 + 잠금
  choicesEl.querySelectorAll(".p5-choice").forEach((b, i) => {
    b.disabled = true;
    if (i === current.answer) b.classList.add("correct");
    else if (i === my && !ok) b.classList.add("wrong");
  });

  verdictEl.innerHTML = ok
    ? `${icon("circle-check")}정답이에요`
    : `${icon("circle-x")}아쉬워요. 정답은 ${LABELS[current.answer]}. ${esc(current.choices[current.answer])}`;
  verdictEl.className = "verdict " + (ok ? "ok" : "no");
  explainText.textContent = current.explanation || "";
  show(explainBox, true);
  show(nextBtn, true);
  nextBtn.focus({ preventScroll: true });
  scoreEl.textContent = `${correct} / ${solved}`;

  // 풀이 결과 저장 (실패해도 학습 흐름은 계속)
  try {
    await postJSON("/api/toeic/answer", {
      question: current.question,
      choices: current.choices,
      my_answer: my,
      correct_answer: current.answer,
      explanation: current.explanation || "",
    });
  } catch (err) {
    toast("풀이 저장 실패: " + err.message, "error");
  }
}

choicesEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".p5-choice");
  if (btn) answer(Number(btn.dataset.i));
});

// 키보드: 1~4 = 보기 선택
document.addEventListener("keydown", (e) => {
  if (box.classList.contains("hidden") || e.target.matches("input, textarea, select")) return;
  const n = Number(e.key);
  if (n >= 1 && n <= 4) answer(n - 1);
});
