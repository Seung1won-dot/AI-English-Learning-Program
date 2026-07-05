// toeic.js — TOEIC 모드 (빈출 단어 추천 + Part 5 문제 풀기)

async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "오류가 발생했습니다.");
  return data;
}

function show(el, on = true) { el.classList.toggle("hidden", !on); }

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : s;
  return d.innerHTML;
}

// =========================================================
// 빈출 단어
// =========================================================
let level = "600";

const levelChips = document.querySelectorAll(".level-chip");
const recommendBtn = document.getElementById("toeicRecommendBtn");
const wordError = document.getElementById("toeicWordError");
const recommendBox = document.getElementById("toeicRecommendBox");
const recommendList = document.getElementById("toeicRecommendList");
const wordList = document.getElementById("toeicWordList");

levelChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    levelChips.forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    level = chip.dataset.level;
  });
});

function wordCard(w) {
  const ex = w.example
    ? `<div class="word-ex">&ldquo;${esc(w.example)}&rdquo;<br><span>${esc(w.example_kr)}</span></div>`
    : "";
  return `<div class="word-item">
    <div class="word-head"><b>${esc(w.word)}</b><span class="pron">${esc(w.pronunciation)}</span>${window.speakBtn(w.word)}</div>
    <div class="word-mean">${esc(w.meaning)}</div>${ex}</div>`;
}

recommendBtn.addEventListener("click", async () => {
  wordError.classList.add("hidden");
  recommendBtn.disabled = true;
  recommendBtn.textContent = "추천 받는 중...";
  try {
    const data = await postJSON("/api/toeic/words", { level });
    recommendList.innerHTML = data.words.map((w, i) => `
      <button class="recommend-chip" data-i="${i}">
        <b>${esc(w.word)}</b> <span>${esc(w.meaning)}</span> <em>+ 담기</em>
      </button>`).join("");
    recommendList._words = data.words;
    show(recommendBox, true);
  } catch (e) {
    wordError.textContent = e.message;
    show(wordError, true);
  } finally {
    recommendBtn.disabled = false;
    recommendBtn.textContent = "✨ 빈출 단어 추천 받기";
  }
});

recommendList.addEventListener("click", async (e) => {
  const chip = e.target.closest(".recommend-chip");
  if (!chip || chip.classList.contains("picked")) return;
  const w = recommendList._words[Number(chip.dataset.i)];
  chip.classList.add("picked");
  chip.querySelector("em").textContent = "✓ 담음";
  try {
    const data = await postJSON("/api/word", { ...w, mode: "toeic" });
    wordList.insertAdjacentHTML("afterbegin", wordCard(data));
  } catch (err) {
    chip.classList.remove("picked");
    chip.querySelector("em").textContent = "+ 담기";
    wordError.textContent = err.message;
    show(wordError, true);
  }
});

// =========================================================
// Part 5 문제
// =========================================================
const startBtn = document.getElementById("p5StartBtn");
const nextBtn = document.getElementById("p5NextBtn");
const loading = document.getElementById("p5Loading");
const p5Error = document.getElementById("p5Error");
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

const LABELS = ["A", "B", "C", "D"];

async function loadQuestion() {
  p5Error.classList.add("hidden");
  show(loading, true);
  startBtn.disabled = true;
  try {
    current = await postJSON("/api/toeic/question", { recent: recentQuestions });
    recentQuestions.push(current.question);
    if (recentQuestions.length > 10) recentQuestions.shift();

    questionEl.textContent = current.question;
    choicesEl.innerHTML = current.choices.map((c, i) => `
      <button class="p5-choice" data-i="${i}">
        <span class="p5-label">(${LABELS[i]})</span> ${esc(c)}
      </button>`).join("");
    show(explainBox, false);
    show(nextBtn, false);
    show(box, true);
    delete choicesEl.dataset.answered;   // 새 문제 → 답변 잠금 해제
    startBtn.textContent = "새 문제 받기";
  } catch (e) {
    p5Error.textContent = e.message;
    show(p5Error, true);
  } finally {
    show(loading, false);
    startBtn.disabled = false;
  }
}

startBtn.addEventListener("click", loadQuestion);
nextBtn.addEventListener("click", loadQuestion);

choicesEl.addEventListener("click", async (e) => {
  const btn = e.target.closest(".p5-choice");
  if (!btn || !current || choicesEl.dataset.answered) return;
  choicesEl.dataset.answered = "1";

  const my = Number(btn.dataset.i);
  const ok = my === current.answer;
  solved += 1;
  if (ok) correct += 1;

  // 보기 색칠 + 잠금
  choicesEl.querySelectorAll(".p5-choice").forEach((b, i) => {
    b.disabled = true;
    if (i === current.answer) b.classList.add("correct");
    else if (i === my && !ok) b.classList.add("wrong");
  });

  verdictEl.textContent = ok ? "⭕ 정답이에요!" : `❌ 아쉬워요. 정답은 (${LABELS[current.answer]}) ${current.choices[current.answer]}`;
  verdictEl.className = "p5-verdict " + (ok ? "ok" : "no");
  explainText.textContent = current.explanation || "";
  show(explainBox, true);
  show(nextBtn, true);
  scoreEl.textContent = `이번 세션 ${correct} / ${solved}`;

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
    p5Error.textContent = "풀이 저장 실패: " + err.message;
    show(p5Error, true);
  }
});
