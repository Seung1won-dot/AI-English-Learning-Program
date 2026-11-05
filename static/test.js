// test.js — Part 5 미니 모의고사 (시간 제한 · 한 번에 제출 · 문제별 해설)

const LABELS = ["A", "B", "C", "D"];
const setup = document.getElementById("testSetup");
const run = document.getElementById("testRun");
const result = document.getElementById("testResult");
const list = document.getElementById("testList");
const clock = document.getElementById("testClock");
const answeredEl = document.getElementById("testAnswered");
const totalEl = document.getElementById("testTotal");
const startBtn = document.getElementById("testStart");
const submitBtns = [document.getElementById("testSubmit"), document.getElementById("testSubmit2")];
const errorEl = document.getElementById("testError");

let count = 10;
let questions = [];
let answers = {};
let deadline = 0;
let startedAt = 0;
let timer = null;
let submitting = false;

chipGroup(".count-chip", (chip) => { count = Number(chip.dataset.count); });

function fmt(sec) {
  sec = Math.max(0, Math.round(sec));
  return `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;
}

function tick() {
  const left = (deadline - Date.now()) / 1000;
  clock.textContent = fmt(left);
  clock.classList.toggle("low", left <= 60);
  if (left <= 0) {
    clearInterval(timer);
    toast("시간이 끝나 자동으로 제출합니다");
    submit(true);
  }
}

function questionHTML(q, i) {
  return `<li class="surface test-q" data-id="${esc(q.id)}">
    <p class="test-num tnum">${i + 1}.</p>
    <p class="p5-question">${esc(q.question)}</p>
    <div class="choices" role="radiogroup" aria-label="${i + 1}번 보기">
      ${q.choices.map((c, j) => `<button type="button" class="choice test-choice" role="radio" aria-checked="false" data-j="${j}">
        <span class="p5-label">${LABELS[j]}</span><span>${esc(c)}</span></button>`).join("")}
    </div></li>`;
}

startBtn.addEventListener("click", async () => {
  show(errorEl, false);
  setBusy(startBtn, true, "문제 준비 중...");
  try {
    const data = await getJSON(`/api/toeic/test?count=${count}`);
    questions = data.questions;
    answers = {};
    list.innerHTML = questions.map(questionHTML).join("");
    totalEl.textContent = questions.length;
    answeredEl.textContent = "0";
    startedAt = Date.now();
    deadline = startedAt + data.limit_sec * 1000;
    show(setup, false);
    show(result, false);
    show(run, true);
    tick();
    timer = setInterval(tick, 1000);
    window.scrollTo({ top: 0 });
  } catch (e) {
    showError(errorEl, e.message);
  } finally {
    setBusy(startBtn, false);
  }
});

list.addEventListener("click", (e) => {
  const btn = e.target.closest(".test-choice");
  if (!btn) return;
  const item = btn.closest(".test-q");
  item.querySelectorAll(".test-choice").forEach((b) => {
    const on = b === btn;
    b.classList.toggle("selected", on);
    b.setAttribute("aria-checked", on ? "true" : "false");
  });
  answers[item.dataset.id] = Number(btn.dataset.j);
  answeredEl.textContent = Object.keys(answers).length;
});

async function submit(auto = false) {
  if (submitting) return;
  const unanswered = questions.length - Object.keys(answers).length;
  if (!auto && unanswered > 0 && !confirm(`아직 ${unanswered}문제를 안 풀었어요. 이대로 제출할까요? (안 푼 문제는 오답 처리)`)) return;
  submitting = true;
  clearInterval(timer);
  submitBtns.forEach((b) => setBusy(b, true, "채점 중..."));
  try {
    const data = await postJSON("/api/toeic/test", {
      answers: questions.map((q) => ({ id: q.id, choice: answers[q.id] ?? null })),
      seconds: Math.round((Date.now() - startedAt) / 1000),
    });
    renderResult(data);
  } catch (e) {
    toast(e.message, "error");
    if (!auto) timer = setInterval(tick, 1000);
  } finally {
    submitting = false;
    submitBtns.forEach((b) => setBusy(b, false));
  }
}
submitBtns.forEach((b) => b.addEventListener("click", () => submit(false)));

function renderResult(data) {
  show(run, false);
  show(result, true);
  const rate = Math.round((data.correct / data.total) * 100);
  document.getElementById("resScore").textContent = `${data.correct} / ${data.total}`;
  document.getElementById("resText").textContent =
    `정답률 ${rate}% · ${fmt(data.seconds)} 사용 (제한 ${fmt(data.limit_sec)}). ` +
    (rate >= 90 ? "실전 감각 좋아요." : rate >= 70 ? "틀린 유형만 다시 보면 됩니다." : "아래 해설을 읽고 오답 복습으로 이어 가세요.");
  document.getElementById("resCats").innerHTML = data.by_category
    .sort((a, b) => a.correct / a.total - b.correct / b.total)
    .map((c) => {
      const r = Math.round((c.correct / c.total) * 100);
      return `<li class="row cat-bar"><span class="cat-name">${esc(c.category)}</span>
        <span class="meter"><span class="meter-fill ${r < 60 ? "low" : ""}" style="width:${r}%"></span></span>
        <span class="tnum cat-num">${c.correct}/${c.total}</span></li>`;
    }).join("");
  document.getElementById("resList").innerHTML = data.results.map((q, i) => `
    <li class="surface test-q ${q.is_correct ? "" : "missed"}">
      <p class="test-num tnum">${i + 1}. <span class="tag">${esc(q.category)}</span>
        ${q.is_correct ? `<span class="tag ok">정답</span>` : `<span class="tag warn">${q.choice === null ? "안 풂" : "오답"}</span>`}</p>
      <p class="p5-question">${esc(q.question)}</p>
      <div class="choices">${q.choices.map((c, j) => `<div class="choice static ${j === q.answer ? "correct" : j === q.choice ? "wrong" : ""}">
        <span class="p5-label">${LABELS[j]}</span><span>${esc(c)}</span></div>`).join("")}</div>
      <p class="explain">${esc(q.explanation)}</p>
    </li>`).join("");
  window.scrollTo({ top: 0 });
}

document.getElementById("testAgain").addEventListener("click", () => {
  show(result, false);
  show(setup, true);
  window.scrollTo({ top: 0 });
});

// 시험 중에 페이지를 떠나려 하면 확인
window.addEventListener("beforeunload", (e) => {
  if (!run.classList.contains("hidden") && !submitting) { e.preventDefault(); e.returnValue = ""; }
});
