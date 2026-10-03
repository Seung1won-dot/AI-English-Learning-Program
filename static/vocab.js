// vocab.js — 단어 암기 모드 (단어 추가 + 주제별 AI 추천 + 단어장 + 삭제)
// 공통 유틸(postJSON, show, esc, wordCard …)은 common.js 에 있다.

const wordInput = document.getElementById("wordInput");
const wordBtn = document.getElementById("wordBtn");
const recommendBtn = document.getElementById("recommendBtn");
const wordError = document.getElementById("wordError");
const wordFallback = document.getElementById("wordFallback");
const wordLoading = document.getElementById("wordLoading");
const wordList = document.getElementById("wordList");
const recommendBox = document.getElementById("recommendBox");
const recommendList = document.getElementById("recommendList");
const todayCount = document.getElementById("todayCount");
const emptyHint = document.getElementById("emptyHint");

let topic = "일상생활";
chipGroup(".topic-chip", (chip) => { topic = chip.dataset.topic; });

function refreshCount() {
  const n = wordList.querySelectorAll(".word-item").length;
  todayCount.textContent = n;
  show(emptyHint, n === 0);
}

async function addWord(payload) {
  show(wordError, false);
  show(wordLoading, true);
  setBusy(wordBtn, true, "정리 중...");
  try {
    const data = await postJSON("/api/word", { ...payload, mode: "vocab" });
    wordList.insertAdjacentHTML("afterbegin", wordCard(data, { deletable: true }));
    wordInput.value = "";
    refreshCount();
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

// ---- 주제별 AI 추천 ----
recommendBtn.addEventListener("click", async () => {
  show(wordError, false);
  setBusy(recommendBtn, true, "추천 받는 중...");
  try {
    const data = await postJSON("/api/recommend-words", { topic });
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
  const ok = await addWord(w);
  if (!ok) markChip(chip, false);   // 중복 등으로 실패하면 되돌린다
});

// ---- 내 단어장에서 가져오기 ----
const wbPullBtn = document.getElementById("wbPullBtn");
if (wbPullBtn) {
  const wbCount = document.getElementById("wbCount");
  const wbRemaining = document.getElementById("wbRemaining");
  const wbAdded = document.getElementById("wbAdded");
  const wbBar = document.getElementById("wbBar");
  const wbError = document.getElementById("wbError");
  const wbDone = document.getElementById("wbDone");
  let exhausted = false;

  wbPullBtn.addEventListener("click", async () => {
    show(wbError, false);
    setBusy(wbPullBtn, true, "가져오는 중...");
    try {
      const data = await postJSON("/api/wordbook/pull", { count: Number(wbCount.value) });
      data.pulled.forEach((w) => wordList.insertAdjacentHTML("afterbegin", wordCard(w, { deletable: true })));
      refreshCount();
      wbRemaining.textContent = data.stats.remaining;
      wbAdded.textContent = data.stats.added;
      wbBar.style.width = data.stats.total
        ? Math.round((data.stats.added / data.stats.total) * 100) + "%" : "100%";
      if (data.pulled.length) toast(`${data.pulled.length}개 단어를 가져왔어요`);
      if (data.stats.remaining === 0) { exhausted = true; show(wbDone, true); }
    } catch (e) {
      showError(wbError, e.message);
    } finally {
      setBusy(wbPullBtn, false);
      if (exhausted) wbPullBtn.disabled = true;   // 소진됨 — 버튼 비활성 유지
    }
  });
}

// ---- 단어 삭제 ----
wordList.addEventListener("click", (e) => {
  const btn = e.target.closest(".word-del");
  if (btn) deleteWord(btn, ".word-item", refreshCount);
});
