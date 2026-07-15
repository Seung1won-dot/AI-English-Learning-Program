// vocab.js — 단어 암기 모드 (단어 추가 + 주제별 AI 추천 + 삭제)

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
const topicChips = document.querySelectorAll(".topic-chip");

let topic = "일상생활";

topicChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    topicChips.forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    topic = chip.dataset.topic;
  });
});

function wordCard(w) {
  const ex = w.example
    ? `<div class="word-ex">&ldquo;${esc(w.example)}&rdquo;<br><span>${esc(w.example_kr)}</span></div>`
    : "";
  return `<div class="word-item" data-word-id="${w.id}">
    <div class="word-head"><b>${esc(w.word)}</b><span class="pron">${esc(w.pronunciation)}</span>${window.speakBtn(w.word)}<button class="word-del" data-id="${w.id}" title="단어 삭제">✕</button></div>
    <div class="word-mean">${esc(w.meaning)}</div>${ex}</div>`;
}

function refreshCount() {
  const n = wordList.querySelectorAll(".word-item").length;
  todayCount.textContent = `${n}개`;
  show(emptyHint, n === 0);
}

async function addWord(payload) {
  wordError.classList.add("hidden");
  show(wordLoading, true);
  wordBtn.disabled = true;
  try {
    const data = await postJSON("/api/word", { ...payload, mode: "vocab" });
    wordList.insertAdjacentHTML("afterbegin", wordCard(data));
    wordInput.value = "";
    refreshCount();
    return true;
  } catch (e) {
    wordError.textContent = e.message;
    show(wordError, true);
    return false;
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

// ---- 주제별 AI 추천 ----
recommendBtn.addEventListener("click", async () => {
  wordError.classList.add("hidden");
  recommendBtn.disabled = true;
  recommendBtn.textContent = "추천 받는 중...";
  try {
    const data = await postJSON("/api/recommend-words", { topic });
    show(wordFallback, !!data.fallback);
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
    recommendBtn.textContent = "AI 추천 받기";
  }
});

recommendList.addEventListener("click", async (e) => {
  const chip = e.target.closest(".recommend-chip");
  if (!chip || chip.classList.contains("picked")) return;
  const w = recommendList._words[Number(chip.dataset.i)];
  chip.classList.add("picked");
  chip.querySelector("em").textContent = "✓ 담음";
  const ok = await addWord(w);
  if (!ok) {
    chip.classList.remove("picked");
    chip.querySelector("em").textContent = "+ 담기";
  }
});

// ---- 단어 삭제 ----
wordList.addEventListener("click", async (e) => {
  const btn = e.target.closest(".word-del");
  if (!btn) return;
  const item = btn.closest(".word-item");
  const word = item?.querySelector("b")?.textContent || "이 단어";
  if (!confirm(`'${word}'를 삭제할까요? 퀴즈·복습 목록에서도 빠집니다.`)) return;

  btn.disabled = true;
  try {
    const res = await fetch(`/api/word/${btn.dataset.id}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "삭제에 실패했습니다.");
    }
    item.remove();
    refreshCount();
  } catch (err) {
    btn.disabled = false;
    wordError.textContent = err.message;
    show(wordError, true);
  }
});
