// common.js — 모든 화면이 함께 쓰는 유틸 (API 호출 · 표시 · 아이콘 · 토스트 · 테마)

// 네트워크가 끊겼을 때 브라우저 기본 영어 메시지("Failed to fetch") 대신 한국어로 안내한다
async function request(url, options, fallbackMsg) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (e) {
    throw new Error("서버에 연결하지 못했어요. 인터넷 연결이나 서버 상태를 확인해 주세요.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) throw new Error("비밀번호 확인이 필요해요. 페이지를 새로고침해 주세요.");
    throw new Error(data.error || fallbackMsg);
  }
  return data;
}

function postJSON(url, payload) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }, "오류가 발생했습니다.");
}

function getJSON(url) {
  return request(url, undefined, "불러오지 못했습니다.");
}

function show(el, on = true) { if (el) el.classList.toggle("hidden", !on); }

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : s;
  return d.innerHTML;
}

function scoreClass(s) { return s >= 80 ? "good" : s >= 60 ? "mid" : "low"; }

// 아이콘 스프라이트(_icons.html) 참조
function icon(name, cls = "") {
  return `<svg class="ic ${cls}" aria-hidden="true" viewBox="0 0 24 24"><use href="#i-${name}"/></svg>`;
}
window.icon = icon;

// 오류 메시지 박스 표시
function showError(el, msg) {
  if (!el) return;
  el.textContent = msg;
  show(el, true);
}

// 버튼 로딩 상태 — 스피너 + 비활성화, 끝나면 원래 내용 복원
function setBusy(btn, busy, label) {
  if (!btn) return;
  if (busy) {
    if (!btn.dataset.idle) btn.dataset.idle = btn.innerHTML;
    btn.disabled = true;
    btn.classList.add("busy");
    btn.textContent = label || "처리 중...";
  } else {
    btn.disabled = false;
    btn.classList.remove("busy");
    if (btn.dataset.idle) btn.innerHTML = btn.dataset.idle;
    delete btn.dataset.idle;
  }
}

// 짧은 알림 (저장 완료 등)
function toast(msg, type = "ok") {
  const root = document.getElementById("toastRoot");
  if (!root) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `${icon(type === "error" ? "alert" : "check")}<span>${esc(msg)}</span>`;
  root.appendChild(el);
  requestAnimationFrame(() => el.classList.add("in"));
  setTimeout(() => {
    el.classList.remove("in");
    setTimeout(() => el.remove(), 250);
  }, 3500);
}
window.toast = toast;

// 단어 행 HTML (템플릿의 word_row 매크로와 같은 구조)
function wordCard(w, { deletable = false } = {}) {
  const ex = w.example
    ? `<div class="row-sub">&ldquo;${esc(w.example)}&rdquo;<span>${esc(w.example_kr)}</span></div>`
    : "";
  const del = deletable
    ? `<button type="button" class="icon-btn danger word-del" data-id="${w.id}" title="단어 삭제" aria-label="단어 삭제">${icon("trash")}</button>`
    : "";
  return `<li class="row word-item fresh" data-word-id="${w.id}">
    <div class="row-body">
      <div class="row-title"><b>${esc(w.word)}</b><span class="pron">${esc(w.pronunciation)}</span></div>
      <div class="row-text">${esc(w.meaning)}</div>${ex}
    </div>
    <div class="row-actions">${window.speakBtn(w.word)}${del}</div></li>`;
}

// 추천 단어 칩 목록
function recommendChips(words) {
  return words.map((w, i) => `
    <button type="button" class="recommend-chip" data-i="${i}">
      <b>${esc(w.word)}</b><span>${esc(w.meaning)}</span><em>${icon("plus")}담기</em>
    </button>`).join("");
}

function markChip(chip, picked) {
  chip.classList.toggle("picked", picked);
  chip.querySelector("em").innerHTML = picked ? `${icon("check")}담음` : `${icon("plus")}담기`;
}

// 단어 삭제 (확인 → DELETE → 성공 시 콜백)
async function deleteWord(btn, itemSelector, onDone) {
  const item = btn.closest(itemSelector);
  const word = item?.querySelector("b")?.textContent || "이 단어";
  if (!confirm(`'${word}'를 삭제할까요? 퀴즈·복습 목록에서도 빠집니다.`)) return;
  btn.disabled = true;
  try {
    const res = await fetch(`/api/word/${btn.dataset.id}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "삭제에 실패했습니다.");
    }
    item.classList.add("leaving");
    setTimeout(() => { item.remove(); onDone && onDone(); }, 160);
    toast(`'${word}' 삭제됨`);
  } catch (err) {
    btn.disabled = false;
    toast(err.message, "error");
  }
}

// 칩 그룹 — 하나만 활성화
function chipGroup(selector, onPick) {
  const chips = document.querySelectorAll(selector);
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => { c.classList.remove("active"); c.setAttribute("aria-pressed", "false"); });
      chip.classList.add("active");
      chip.setAttribute("aria-pressed", "true");
      onPick(chip);
    });
  });
}

// ---- 밝은/어두운 화면 전환 ----
(function () {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  const root = document.documentElement;
  const systemLight = () => window.matchMedia("(prefers-color-scheme: light)").matches;
  const isLight = () => (root.dataset.theme ? root.dataset.theme === "light" : systemLight());
  const paint = () => { btn.innerHTML = icon(isLight() ? "moon" : "sun"); };
  btn.addEventListener("click", () => {
    const next = isLight() ? "dark" : "light";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) { /* 저장 불가 시 이번 방문만 적용 */ }
    paint();
  });
  paint();
})()
