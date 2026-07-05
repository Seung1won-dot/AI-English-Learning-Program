// app.js — 오늘 학습 화면 동작 (단어 추가/추천, 문장 첨삭)

const WORDS_GOAL = Number(document.body.dataset.wordsGoal) || 5;
const SENTS_GOAL = Number(document.body.dataset.sentsGoal) || 3;
const PAGE_MODE = document.body.dataset.mode || "talk";   // 학습 기록에 붙는 모드 태그

// ---- 공통 유틸 ----
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

function updateCounts(counts) {
  const wl = document.getElementById("wordCountLabel");
  const sl = document.getElementById("sentCountLabel");
  if (counts.words !== undefined) {
    wl.textContent = `${counts.words} / ${WORDS_GOAL}`;
    document.getElementById("wordBar").style.width =
      Math.min(100, (counts.words / WORDS_GOAL) * 100) + "%";
  }
  if (counts.sentences !== undefined) {
    sl.textContent = `${counts.sentences} / ${SENTS_GOAL}`;
    document.getElementById("sentBar").style.width =
      Math.min(100, (counts.sentences / SENTS_GOAL) * 100) + "%";
  }
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : s;
  return d.innerHTML;
}

// =========================================================
// 단어
// =========================================================
const wordInput = document.getElementById("wordInput");
const wordBtn = document.getElementById("wordBtn");
const recommendBtn = document.getElementById("recommendBtn");
const wordError = document.getElementById("wordError");
const wordLoading = document.getElementById("wordLoading");
const wordList = document.getElementById("wordList");
const recommendBox = document.getElementById("recommendBox");
const recommendList = document.getElementById("recommendList");

function wordCard(w) {
  const ex = w.example
    ? `<div class="word-ex">&ldquo;${esc(w.example)}&rdquo;<br><span>${esc(w.example_kr)}</span></div>`
    : "";
  return `<div class="word-item">
    <div class="word-head"><b>${esc(w.word)}</b><span class="pron">${esc(w.pronunciation)}</span>${window.speakBtn(w.word)}</div>
    <div class="word-mean">${esc(w.meaning)}</div>${ex}</div>`;
}

async function addWord(payload) {
  wordError.classList.add("hidden");
  show(wordLoading, true);
  wordBtn.disabled = true;
  try {
    const data = await postJSON("/api/word", { ...payload, mode: PAGE_MODE });
    wordList.insertAdjacentHTML("afterbegin", wordCard(data));
    updateCounts(data.counts);
    wordInput.value = "";
  } catch (e) {
    wordError.textContent = e.message;
    show(wordError, true);
  } finally {
    show(wordLoading, false);
    wordBtn.disabled = false;
  }
}

wordBtn.addEventListener("click", () => {
  const word = wordInput.value.trim();
  if (!word) { wordError.textContent = "단어를 입력해 주세요."; show(wordError, true); return; }
  addWord({ word });
});
wordInput.addEventListener("keydown", (e) => { if (e.key === "Enter") wordBtn.click(); });

// 추천 단어
recommendBtn.addEventListener("click", async () => {
  wordError.classList.add("hidden");
  recommendBtn.disabled = true;
  recommendBtn.textContent = "추천 받는 중...";
  try {
    const data = await postJSON("/api/recommend-words", { topic: "일상생활" });
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
    recommendBtn.textContent = "✨ AI 추천 단어";
  }
});

recommendList.addEventListener("click", (e) => {
  const chip = e.target.closest(".recommend-chip");
  if (!chip) return;
  const w = recommendList._words[Number(chip.dataset.i)];
  addWord(w);               // 추천 단어를 그대로 저장 (재분석 안 함)
  chip.classList.add("picked");
  chip.querySelector("em").textContent = "✓ 담음";
});

// =========================================================
// 문장
// =========================================================
const sentInput = document.getElementById("sentInput");
const sentBtn = document.getElementById("sentBtn");
const sentError = document.getElementById("sentError");
const sentLoading = document.getElementById("sentLoading");
const sentList = document.getElementById("sentList");

function scoreClass(s) { return s >= 80 ? "good" : s >= 60 ? "mid" : "low"; }

function sentCard(s) {
  const mean = s.meaning ? `<div class="sent-mean">🇰🇷 ${esc(s.meaning)}</div>` : "";
  return `<div class="sent-item">
    <div class="sent-top">
      <span class="score-pill ${scoreClass(s.score)}">${s.score}</span>
      <span class="corrected">${esc(s.corrected)}</span>${window.speakBtn(s.corrected)}
    </div>${mean}
    <div class="sent-fb">${esc(s.feedback)}</div></div>`;
}

sentBtn.addEventListener("click", async () => {
  const sentence = sentInput.value.trim();
  sentError.classList.add("hidden");
  if (!sentence) { sentError.textContent = "문장을 입력해 주세요."; show(sentError, true); return; }
  show(sentLoading, true);
  sentBtn.disabled = true;
  try {
    const data = await postJSON("/api/sentence", { sentence, mode: PAGE_MODE });
    sentList.insertAdjacentHTML("afterbegin", sentCard(data));
    updateCounts(data.counts);
    sentInput.value = "";
  } catch (e) {
    sentError.textContent = e.message;
    show(sentError, true);
  } finally {
    show(sentLoading, false);
    sentBtn.disabled = false;
  }
});
sentInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") sentBtn.click();
});
