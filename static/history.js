// history.js — 학습 기록 필터 (모드 + 날짜)

const datePicker = document.getElementById("datePicker");
const clearBtn = document.getElementById("clearDate");
const chips = document.querySelectorAll(".date-chip");
const dayCards = document.querySelectorAll(".day-card");
const noRecord = document.getElementById("noRecord");
const modeTabs = document.querySelectorAll(".mode-filter-tab");

let modeFilter = "all";   // all | toeic | opic | talk
let dateFilter = "";      // "" = 전체 날짜

function show(el, on = true) { el.classList.toggle("hidden", !on); }

// 모드 + 날짜 조건을 한꺼번에 적용한다.
function applyFilters() {
  let anyVisible = false;

  dayCards.forEach((card) => {
    // 1) 날짜 조건
    if (dateFilter && card.dataset.date !== dateFilter) {
      card.style.display = "none";
      return;
    }

    // 2) 모드 조건 — 항목 단위로 보이기/숨기기
    let cardHasVisible = false;
    card.querySelectorAll(".mode-item").forEach((item) => {
      const hit = modeFilter === "all" || item.dataset.mode === modeFilter;
      item.style.display = hit ? "" : "none";
      if (hit) cardHasVisible = true;
    });

    // 3) 항목이 하나도 안 남은 블록(단어/문장/오픽/토익 묶음)은 제목까지 숨긴다
    card.querySelectorAll(".day-block").forEach((block) => {
      const visibleItems = Array.from(block.querySelectorAll(".mode-item"))
        .some((item) => item.style.display !== "none");
      block.style.display = visibleItems ? "" : "none";
    });

    card.style.display = cardHasVisible ? "" : "none";
    if (cardHasVisible) anyVisible = true;
  });

  // 날짜 칩 활성화 표시
  chips.forEach((chip) => chip.classList.toggle("active", chip.dataset.date === dateFilter));
  show(noRecord, !anyVisible);
}

// ---- 모드 필터 ----
modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    modeTabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    modeFilter = tab.dataset.mode;
    applyFilters();
  });
});

// ---- 날짜 필터 ----
if (datePicker) {
  datePicker.addEventListener("change", () => {
    dateFilter = datePicker.value || "";
    applyFilters();
  });
}

clearBtn?.addEventListener("click", () => {
  dateFilter = "";
  if (datePicker) datePicker.value = "";
  applyFilters();
});

chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    dateFilter = chip.dataset.date;
    if (datePicker) datePicker.value = dateFilter;
    applyFilters();
    document.querySelector(`.day-card[data-date="${dateFilter}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
