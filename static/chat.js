// chat.js — AI 회화 챗봇

let history = [];       // [{role, content}]
let topic = "";

const chatLog = document.getElementById("chatLog");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatSend = document.getElementById("chatSend");
const chatError = document.getElementById("chatError");
const topicChips = document.querySelectorAll(".topic-chip");

function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
function show(el, on = true) { el.classList.toggle("hidden", !on); }

function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = "bubble " + (role === "user" ? "me" : "ai");

  // AI 답변에서 📝 교정 줄을 분리해 표시
  if (role === "assistant" && text.includes("📝")) {
    const i = text.indexOf("📝");
    const reply = text.slice(0, i).trim();
    const fix = text.slice(i).trim();
    div.innerHTML =
      `<span class="bubble-text">${esc(reply)}</span> ${window.speakBtn(reply)}` +
      `<div class="bubble-fix">${esc(fix)}</div>`;
  } else if (role === "assistant") {
    div.innerHTML = `<span class="bubble-text">${esc(text)}</span> ${window.speakBtn(text)}`;
  } else {
    div.innerHTML = `<span class="bubble-text">${esc(text)}</span>`;
  }
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addTyping() {
  const div = document.createElement("div");
  div.className = "bubble ai typing";
  div.id = "typingBubble";
  div.textContent = "...";
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}
function removeTyping() {
  document.getElementById("typingBubble")?.remove();
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatError.classList.add("hidden");

  addBubble("user", text);
  history.push({ role: "user", content: text });
  chatInput.value = "";
  chatSend.disabled = true;
  addTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history, topic }),
    });
    const data = await res.json();
    removeTyping();
    if (!res.ok) throw new Error(data.error || "오류가 발생했습니다.");
    addBubble("assistant", data.reply);
    history.push({ role: "assistant", content: data.reply });
  } catch (err) {
    removeTyping();
    chatError.textContent = err.message;
    show(chatError, true);
  } finally {
    chatSend.disabled = false;
    chatInput.focus();
  }
});

// 주제 선택
topicChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    topicChips.forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    topic = chip.dataset.topic;
    // 주제 바꾸면 대화 초기화 + AI 가 먼저 말 걸기
    history = [];
    chatLog.innerHTML = "";
    greet();
  });
});

// 시작 인사 (AI 가 먼저 한마디)
async function greet() {
  chatSend.disabled = true;
  addTyping();
  history.push({ role: "user", content: "(Start the conversation with a short greeting and a question.)" });
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history, topic }),
    });
    const data = await res.json();
    removeTyping();
    history.pop(); // 시작 트리거 메시지는 기록에서 제거
    if (res.ok) {
      addBubble("assistant", data.reply);
      history.push({ role: "assistant", content: data.reply });
    }
  } catch (e) {
    removeTyping();
    history.pop();
  } finally {
    chatSend.disabled = false;
    chatInput.focus();
  }
}

greet();
