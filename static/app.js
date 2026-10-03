// app.js — 회화 모드 "오늘 학습" 탭 (단어 추가/추천, 문장 첨삭)
// 공통 유틸(postJSON, show, esc, wordCard …)은 common.js 에 있다.

const WORDS_GOAL = Number(document.body.dataset.wordsGoal) || 5;
const SENTS_GOAL = Number(document.body.dataset.sentsGoal) || 3;
const PAGE_MODE = document.body.dataset.mode || "talk";   // 학습 기록에 붙는 모드 태그

function updateCounts(counts) {
  if (counts.words !== undefined) {
    document.getElementById("wordCountLabel").textContent = `${counts.words} / ${WORDS_GOAL}`;
    document.getElementById("wordBar").style.width =
      Math.min(100, (counts.words / WORDS_GOAL) * 100) + "%";
  }
  if (counts.sentences !== undefined) {
    document.getElementById("sentCountLabel").textContent = `${counts.sentences} / ${SENTS_GOAL}`;
    document.getElementById("sentBar").style.width =
      Math.min(100, (counts.sentences / SENTS_GOAL) * 100) + "%";
  }
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

async function addWord(payload) {
  show(wordError, false);
  show(wordLoading, true);
  setBusy(wordBtn, true, "정리 중...");
  try {
    const data = await postJSON("/api/word", { ...payload, mode: PAGE_MODE });
    wordList.insertAdjacentHTML("afterbegin", wordCard(data, { deletable: true }));
    updateCounts(data.counts);
    wordInput.value = "";
    toast(`'${data.word}' 저장됨`);
    return true;
  } catch (e) {
    showError(wordError, e.message);
    return false;
  } finally {
    show(wordLoading, false);
    setBusy(wordBtn, false);
  }
}

wordBtn.addEventListener("click", () => {
  const word = wordInput.value.trim();
  if (!word) { showError(wordError, "단어를 입력해 주세요."); wordInput.focus(); return; }
  addWord({ word });
});
wordInput.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.isComposing) wordBtn.click(); });

// 추천 단어
recommendBtn.addEventListener("click", async () => {
  show(wordError, false);
  setBusy(recommendBtn, true, "추천 받는 중...");
  try {
    const data = await postJSON("/api/recommend-words", { topic: "일상생활" });
    show(document.getElementById("wordFallback"), !!data.fallback);
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
  const ok = await addWord(w);   // 추천 단어를 그대로 저장 (재분석 안 함)
  if (!ok) markChip(chip, false); // 중복 등으로 실패하면 되돌린다
});

wordList.addEventListener("click", (e) => {
  const btn = e.target.closest(".word-del");
  if (btn) deleteWord(btn, ".word-item");
});

// =========================================================
// 문장
// =========================================================
const sentInput = document.getElementById("sentInput");
const sentBtn = document.getElementById("sentBtn");
const sentError = document.getElementById("sentError");
const sentLoading = document.getElementById("sentLoading");
const sentList = document.getElementById("sentList");

function sentCard(s) {
  const mean = s.meaning ? `<div class="row-sub">${esc(s.meaning)}</div>` : "";
  return `<li class="row sent-item fresh">
    <div class="row-body">
      <div class="row-title"><span class="score-pill ${scoreClass(s.score)}">${s.score}</span><span class="corrected">${esc(s.corrected)}</span></div>
      ${mean}<div class="row-sub">${esc(s.feedback)}</div>
    </div>
    <div class="row-actions">${window.speakBtn(s.corrected)}</div></li>`;
}

sentBtn.addEventListener("click", async () => {
  const sentence = sentInput.value.trim();
  show(sentError, false);
  if (!sentence) { showError(sentError, "문장을 입력해 주세요."); sentInput.focus(); return; }
  show(sentLoading, true);
  setBusy(sentBtn, true, "검토 중...");
  try {
    const data = await postJSON("/api/sentence", { sentence, mode: PAGE_MODE });
    sentList.insertAdjacentHTML("afterbegin", sentCard(data));
    updateCounts(data.counts);
    sentInput.value = "";
  } catch (e) {
    showError(sentError, e.message);
  } finally {
    show(sentLoading, false);
    setBusy(sentBtn, false);
  }
});
sentInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") sentBtn.click();
});
