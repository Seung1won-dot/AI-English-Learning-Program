// review.js — 플래시카드 복습

let cards = [];
let idx = 0;
let kind = "words";

const tabs = document.querySelectorAll(".tab");
const emptyMsg = document.getElementById("emptyMsg");
const cardEl = document.getElementById("card");
const controls = document.getElementById("controls");
const flashFront = document.getElementById("flashFront");
const flashBack = document.getElementById("flashBack");
const flashAnswer = document.getElementById("flashAnswer");
const flashExtra = document.getElementById("flashExtra");
const flashTip = document.getElementById("flashTip");
const progress = document.getElementById("progress");

function show(el, on = true) { el.classList.toggle("hidden", !on); }

async function loadCards(k) {
  kind = k;
  const res = await fetch(`/api/review?kind=${k}`);
  const data = await res.json();
  cards = data.cards || [];
  idx = 0;
  if (cards.length === 0) {
    show(emptyMsg, true);
    show(cardEl, false);
    show(controls, false);
  } else {
    show(emptyMsg, false);
    show(cardEl, true);
    show(controls, true);
    render();
  }
}

function render() {
  const c = cards[idx];
  flashFront.textContent = c.front;
  flashAnswer.textContent = c.back;
  flashExtra.textContent = c.extra || "";
  const speak = document.getElementById("flashSpeak");
  if (speak) speak.dataset.text = c.back;
  show(flashBack, false);
  show(flashFront, true);
  show(flashTip, true);
  progress.textContent = `${idx + 1} / ${cards.length}`;
}

function flip() {
  const backHidden = flashBack.classList.contains("hidden");
  show(flashBack, backHidden);
  show(flashFront, !backHidden);
  show(flashTip, !backHidden);
}

cardEl.addEventListener("click", flip);

document.getElementById("nextBtn").addEventListener("click", () => {
  idx = (idx + 1) % cards.length;
  render();
});
document.getElementById("prevBtn").addEventListener("click", () => {
  idx = (idx - 1 + cards.length) % cards.length;
  render();
});

tabs.forEach((t) => {
  t.addEventListener("click", () => {
    tabs.forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    loadCards(t.dataset.kind);
  });
});

// 키보드: 스페이스=뒤집기, 좌우=이동
document.addEventListener("keydown", (e) => {
  if (cards.length === 0) return;
  if (e.code === "Space") { e.preventDefault(); flip(); }
  else if (e.key === "ArrowRight") document.getElementById("nextBtn").click();
  else if (e.key === "ArrowLeft") document.getElementById("prevBtn").click();
});

loadCards("words");
