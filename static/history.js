// history.js — 학습 기록 필터 (모드 + 날짜) · 단어 삭제
// 공통 유틸(show, deleteWord …)은 common.js 에 있다.

const datePicker = document.getElementById("datePicker");
const clearBtn = document.getElementById("clearDate");
const chips = document.querySelectorAll(".date-chip");
const dayCards = document.querySelectorAll(".day-card");
const noRecord = document.getElementById("noRecord");

let modeFilter = "all";   // all | vocab | toeic | opic | talk
let dateFilter = "";      // "" = 전체 날짜

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

    // 3) 항목이 하나도 안 남은 묶음(단어/문장/오픽/토익)은 제목까지 숨긴다
    card.querySelectorAll(".day-block").forEach((block) => {
      const visibleItems = Array.from(block.querySelectorAll(".mode-item"))
        .some((item) => item.style.display !== "none");
      block.style.display = visibleItems ? "" : "none";
    });

    card.style.display = cardHasVisible ? "" : "none";
    if (cardHasVisible) anyVisible = true;
  });

  chips.forEach((chip) => chip.classList.toggle("active", chip.dataset.date === dateFilter));
  show(noRecord, !anyVisible);
}

// ---- 모드 필터 ----
chipGroup(".mode-filter-tab", (tab) => {
  modeFilter = tab.dataset.mode;
  applyFilters();
});

// ---- 날짜 필터 ----
datePicker?.addEventListener("change", () => {
  dateFilter = datePicker.value || "";
  applyFilters();
});

clearBtn?.addEventListener("click", () => {
  dateFilter = "";
  if (datePicker) datePicker.value = "";
  applyFilters();
});

chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    dateFilter = dateFilter === chip.dataset.date ? "" : chip.dataset.date;  // 다시 누르면 해제
    if (datePicker) datePicker.value = dateFilter;
    applyFilters();
  });
});

// ---- 단어 삭제 (오타·중복 정리) ----
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".word-del");
  if (btn) deleteWord(btn, ".mode-item", applyFilters);
});
