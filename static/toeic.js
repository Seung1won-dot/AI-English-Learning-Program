// toeic.js — TOEIC 모드 (Part 5 유형별 풀이 · 오답 복습 · 빈출 어휘)
// 공통 유틸(postJSON, show, esc, wordCard …)은 common.js 에 있다.

const LABELS = ["A", "B", "C", "D"];

// =========================================================
// Part 5
// =========================================================
const section = document.getElementById("part5");
const startBtn = document.getElementById("p5StartBtn");
const reviewBtn = document.getElementById("p5ReviewBtn");
const dueEl = document.getElementById("p5Due");
const solvedEl = document.getElementById("p5Solved");
const nextBtn = document.getElementById("p5NextBtn");
const p5Error = document.getElementById("p5Error");
const box = document.getElementById("p5Box");
const reviewDone = document.getElementById("p5ReviewDone");
const tagsEl = document.getElementById("p5Tags");
const questionEl = document.getElementById("p5Question");
const choicesEl = document.getElementById("p5Choices");
const explainBox = document.getElementById("p5Explain");
const verdictEl = document.getElementById("p5Verdict");
const explainText = document.getElementById("p5ExplainText");
const scoreEl = document.getElementById("p5Score");

let category = section.dataset.startCategory || "";
let level = "";
let current = null;
let mode = "practice";        // practice | review
let reviewQueue = [];
const recent = [];            // 최근에 푼 문제 id (반복 방지)
let solved = 0, correct = 0;

chipGroup(".cat-chip", (chip) => { category = chip.dataset.cat; if (mode === "practice" && current) loadQuestion(); });
chipGroup(".lv-chip", (chip) => { level = chip.dataset.lv; if (mode === "practice" && current) loadQuestion(); });

function tags(q) {
  const out = [];
  if (mode === "review") out.push(`<span class="tag warn">오답 복습${reviewQueue.length ? ` · ${reviewQueue.length}개 남음` : ""}</span>`);
  if (q.category) out.push(`<span class="tag">${esc(q.category)}</span>`);
  if (q.level_label) out.push(`<span class="tag">${esc(q.level_label)}</span>`);
  return out.join("");
}

function render(q) {
  current = q;
  tagsEl.innerHTML = tags(q);
  questionEl.textContent = q.question;
  choicesEl.innerHTML = q.choices.map((c, i) => `
    <button type="button" class="choice p5-choice" data-i="${i}">
      <span class="p5-label">${LABELS[i]}</span><span>${esc(c)}</span>
    </button>`).join("");
  delete choicesEl.dataset.answered;
  show(explainBox, false);
  show(nextBtn, false);
  show(reviewDone, false);
  show(box, true);
}

async function loadQuestion() {
  show(p5Error, false);
  mode = "practice";
  setBusy(startBtn, true, "불러오는 중...");
  try {
    const q = await postJSON("/api/toeic/question", { category, level, recent });
    render(q);
    startBtn.dataset.idle = "새 문제";
  } catch (e) {
    showError(p5Error, e.message);
  } finally {
    setBusy(startBtn, false);
  }
}

async function startReview() {
  show(p5Error, false);
  setBusy(reviewBtn, true, "불러오는 중...");
  try {
    const data = await getJSON("/api/toeic/review");
    reviewQueue = data.questions || [];
    if (!reviewQueue.length) {
      show(box, false);
      show(reviewDone, true);
      return;
    }
    mode = "review";
    render(reviewQueue.shift());
  } catch (e) {
    showError(p5Error, e.message);
  } finally {
    setBusy(reviewBtn, false);
  }
}

function next() {
  if (mode === "review") {
    if (reviewQueue.length) render(reviewQueue.shift());
    else { mode = "practice"; show(box, false); show(reviewDone, true); toast("오늘 오답 복습을 마쳤어요"); }
  } else {
    loadQuestion();
  }
}

startBtn.addEventListener("click", loadQuestion);
reviewBtn.addEventListener("click", startReview);
nextBtn.addEventListener("click", next);

async function answer(my) {
  if (!current || choicesEl.dataset.answered) return;
  choicesEl.dataset.answered = "1";
  const ok = my === current.answer;
  solved += 1;
  if (ok) correct += 1;
  if (current.id) { recent.push(current.id); if (recent.length > 30) recent.shift(); }

  choicesEl.querySelectorAll(".p5-choice").forEach((b, i) => {
    b.disabled = true;
    if (i === current.answer) b.classList.add("correct");
    else if (i === my && !ok) b.classList.add("wrong");
  });
  verdictEl.innerHTML = ok
    ? `${icon("circle-check")}정답이에요`
    : `${icon("circle-x")}정답은 (${LABELS[current.answer]}) ${esc(current.choices[current.answer])}`;
  verdictEl.className = "verdict " + (ok ? "ok" : "no");
  explainText.textContent = current.explanation || "";
  show(explainBox, true);
  nextBtn.innerHTML = `${mode === "review" && !reviewQueue.length ? "복습 마치기" : "다음 문제"} ${icon("arrow-right")}`;
  show(nextBtn, true);
  nextBtn.focus({ preventScroll: true });
  scoreEl.textContent = `이번에 ${correct} / ${solved}`;

  try {
    const data = await postJSON("/api/toeic/answer", {
      id: current.id || "",
      question: current.question,
      choices: current.choices,
      my_answer: my,
      correct_answer: current.answer,
      explanation: current.explanation || "",
      source: mode,
    });
    if (data.due_p5 !== undefined) dueEl.textContent = data.due_p5;
    if (data.p5_solved !== undefined) solvedEl.textContent = data.p5_solved;
  } catch (err) {
    toast("풀이 저장 실패: " + err.message, "error");
  }
}

choicesEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".p5-choice");
  if (btn) answer(Number(btn.dataset.i));
});

document.addEventListener("keydown", (e) => {
  if (box.classList.contains("hidden") || e.target.matches("input, textarea, select")) return;
  const n = Number(e.key);
  if (n >= 1 && n <= 4) answer(n - 1);
});

if (section.dataset.startReview === "1") startReview();
else if (section.dataset.startCategory) loadQuestion();

// =========================================================
// 빈출 어휘
// =========================================================
let vocabLevel = (document.querySelector(".lvl-chip.active") || {}).dataset?.level || "800";

const dailyBtn = document.getElementById("dailyBtn");
const recommendBtn = document.getElementById("toeicRecommendBtn");
const wordError = document.getElementById("toeicWordError");
const recommendBox = document.getElementById("toeicRecommendBox");
const recommendList = document.getElementById("toeicRecommendList");
const wordList = document.getElementById("toeicWordList");
const wordCount = document.getElementById("toeicCount");
const wordEmpty = document.getElementById("toeicEmpty");

chipGroup(".lvl-chip", (chip) => { vocabLevel = chip.dataset.level; show(recommendBox, false); });

function refreshCount() {
  const n = wordList.querySelectorAll(".word-item").length;
  wordCount.textContent = n;
  show(wordEmpty, n === 0);
}

function paintProgress(level, progress) {
  const card = document.querySelector(`.lvl-chip[data-level="${level}"]`);
  if (!card || !progress) return;
  card.querySelector(".lvl-learned").textContent = progress.learned;
  card.querySelector(".meter-fill").style.width = `${Math.round((progress.learned / progress.total) * 100)}%`;
}

dailyBtn.addEventListener("click", async () => {
  show(wordError, false);
  setBusy(dailyBtn, true, "담는 중...");
  try {
    const data = await postJSON("/api/vocab/daily", { level: vocabLevel });
    if (!data.added.length) {
      toast(`${data.level}점대 어휘를 모두 담았어요. 다른 수준을 골라 보세요.`);
      return;
    }
    data.added.forEach((w) => wordList.insertAdjacentHTML("afterbegin", wordCard(w, { deletable: true })));
    refreshCount();
    paintProgress(data.level, data.progress);
    toast(`${data.added.length}개를 담았어요. 단어 퀴즈에서 바로 복습할 수 있어요.`);
  } catch (e) {
    showError(wordError, e.message);
  } finally {
    setBusy(dailyBtn, false);
  }
});

recommendBtn.addEventListener("click", async () => {
  show(wordError, false);
  setBusy(recommendBtn, true, "불러오는 중...");
  try {
    const data = await postJSON("/api/toeic/words", { level: vocabLevel });
    if (!data.words.length) {
      toast(`${data.level}점대 어휘를 모두 담았어요.`);
      show(recommendBox, false);
      return;
    }
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
    const card = document.querySelector(`.lvl-chip[data-level="${w.level}"] .lvl-learned`);
    if (card) card.textContent = Number(card.textContent) + 1;
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
