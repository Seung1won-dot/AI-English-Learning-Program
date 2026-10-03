// review.js — 플래시카드 복습
// 공통 유틸(getJSON, show …)은 common.js 에 있다.

let cards = [];
let idx = 0;

const tabs = document.querySelectorAll(".tab");
const loadingEl = document.getElementById("reviewLoading");
const emptyMsg = document.getElementById("emptyMsg");
const cardEl = document.getElementById("card");
const cardFace = cardEl.querySelector(".flashcard-inner");
const controls = document.getElementById("controls");
const flashFront = document.getElementById("flashFront");
const flashBack = document.getElementById("flashBack");
const flashAnswer = document.getElementById("flashAnswer");
const flashExtra = document.getElementById("flashExtra");
const flashSpeak = document.getElementById("flashSpeak");
const progress = document.getElementById("progress");

async function loadCards(kind) {
  show(emptyMsg, false);
  show(cardEl, false);
  show(controls, false);
  show(loadingEl, true);
  try {
    const data = await getJSON(`/api/review?kind=${kind}`);
    cards = data.cards || [];
  } catch (e) {
    cards = [];
    toast(e.message, "error");
  }
  idx = 0;
  show(loadingEl, false);
  const has = cards.length > 0;
  show(emptyMsg, !has);
  show(cardEl, has);
  show(controls, has);
  if (has) render();
}

function render() {
  const c = cards[idx];
  flashFront.textContent = c.front;
  flashAnswer.textContent = c.back;
  flashExtra.textContent = c.extra || "";
  flashSpeak.dataset.text = c.back;
  show(flashBack, false);
  show(flashFront, true);
  progress.textContent = `${idx + 1} / ${cards.length}`;
}

function flip() {
  const backHidden = flashBack.classList.contains("hidden");
  show(flashBack, backHidden);
  show(flashFront, !backHidden);
  cardFace.classList.remove("turning");
  void cardFace.offsetWidth;          // 애니메이션 재시작
  cardFace.classList.add("turning");
}

function move(step) {
  if (!cards.length) return;
  idx = (idx + step + cards.length) % cards.length;
  render();
}

cardFace.addEventListener("click", flip);
document.getElementById("nextBtn").addEventListener("click", () => move(1));
document.getElementById("prevBtn").addEventListener("click", () => move(-1));

tabs.forEach((t) => {
  t.addEventListener("click", () => {
    tabs.forEach((x) => { x.classList.remove("active"); x.setAttribute("aria-selected", "false"); });
    t.classList.add("active");
    t.setAttribute("aria-selected", "true");
    loadCards(t.dataset.kind);
  });
});

// 키보드: 스페이스/Enter=뒤집기, 좌우=이동
document.addEventListener("keydown", (e) => {
  if (cards.length === 0 || cardEl.classList.contains("hidden")) return;
  if (e.target.matches("input, textarea, select")) return;
  const onButton = e.target.matches("button") && e.target !== document.body;
  if ((e.code === "Space" || (e.key === "Enter" && e.target === cardFace)) && !onButton) { e.preventDefault(); flip(); }
  else if (e.key === "ArrowRight") move(1);
  else if (e.key === "ArrowLeft") move(-1);
});

loadCards("words");
