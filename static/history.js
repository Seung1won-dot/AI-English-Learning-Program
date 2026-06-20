// history.js — 학습 기록 날짜 필터

const datePicker = document.getElementById("datePicker");
const clearBtn = document.getElementById("clearDate");
const chips = document.querySelectorAll(".date-chip");
const dayCards = document.querySelectorAll(".day-card");
const noRecord = document.getElementById("noRecord");

// 기록이 있는 날짜 집합
const recordedDates = new Set(Array.from(dayCards).map((c) => c.dataset.date));

function show(el, on = true) { el.classList.toggle("hidden", !on); }

function filterByDate(date) {
  let matched = false;
  dayCards.forEach((card) => {
    const hit = card.dataset.date === date;
    card.style.display = hit ? "" : "none";
    if (hit) matched = true;
  });

  // 칩 활성화 표시
  chips.forEach((chip) => chip.classList.toggle("active", chip.dataset.date === date));

  // 선택한 날짜에 기록이 없을 때 안내
  show(noRecord, !matched);
}

function showAll() {
  dayCards.forEach((card) => (card.style.display = ""));
  chips.forEach((chip) => chip.classList.remove("active"));
  show(noRecord, false);
  if (datePicker) datePicker.value = "";
}

if (datePicker) {
  datePicker.addEventListener("change", () => {
    if (datePicker.value) filterByDate(datePicker.value);
    else showAll();
  });
}

clearBtn?.addEventListener("click", showAll);

chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    const d = chip.dataset.date;
    if (datePicker) datePicker.value = d;
    filterByDate(d);
    // 선택한 날짜 카드로 스크롤
    const card = document.querySelector(`.day-card[data-date="${d}"]`);
    card?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
