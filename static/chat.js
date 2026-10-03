// chat.js — AI 회화 챗봇 (프리토킹 탭을 처음 열 때 window.startChat() 으로 시작)
// 공통 유틸(postJSON, show, esc …)은 common.js 에 있다.

let messages = [];      // [{role, content}]
let chatTopic = "";

const chatLog = document.getElementById("chatLog");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatSend = document.getElementById("chatSend");
const chatError = document.getElementById("chatError");

// AI 답변 끝의 "📝 교정" 줄은 분리해서 따로 보여준다
const FIX_MARK = "📝";

function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = "bubble " + (role === "user" ? "me" : "ai");

  if (role === "assistant") {
    const i = text.indexOf(FIX_MARK);
    const reply = (i >= 0 ? text.slice(0, i) : text).trim();
    const fix = i >= 0 ? text.slice(i + FIX_MARK.length).trim() : "";
    div.innerHTML =
      `<div class="bubble-main">${esc(reply)}` +
      (fix ? `<div class="bubble-fix">${icon("pen")}<span>${esc(fix)}</span></div>` : "") +
      `</div>${window.speakBtn(reply)}`;
  } else {
    div.textContent = text;
  }
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addTyping() {
  const div = document.createElement("div");
  div.className = "bubble ai";
  div.id = "typingBubble";
  div.innerHTML = `<span class="typing">AI 가 답을 쓰는 중…</span>`;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}
function removeTyping() {
  document.getElementById("typingBubble")?.remove();
}

async function askAI() {
  return postJSON("/api/chat", { history: messages, topic: chatTopic });
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text || chatSend.disabled) return;
  show(chatError, false);

  addBubble("user", text);
  messages.push({ role: "user", content: text });
  chatInput.value = "";
  chatSend.disabled = true;
  addTyping();

  try {
    const data = await askAI();
    removeTyping();
    addBubble("assistant", data.reply);
    messages.push({ role: "assistant", content: data.reply });
  } catch (err) {
    removeTyping();
    showError(chatError, err.message);
  } finally {
    chatSend.disabled = false;
    chatInput.focus();
  }
});

// 주제 선택 — 바꾸면 대화 초기화 + AI 가 먼저 말 걸기
chipGroup("#tab-chat .topic-chip", (chip) => {
  chatTopic = chip.dataset.topic;
  messages = [];
  chatLog.innerHTML = "";
  greet();
});

// 시작 인사 (AI 가 먼저 한마디)
async function greet() {
  chatSend.disabled = true;
  addTyping();
  messages.push({ role: "user", content: "(Start the conversation with a short greeting and a question.)" });
  try {
    const data = await askAI();
    removeTyping();
    messages.pop(); // 시작 트리거 메시지는 기록에서 제거
    addBubble("assistant", data.reply);
    messages.push({ role: "assistant", content: data.reply });
  } catch (e) {
    removeTyping();
    messages.pop();
    showError(chatError, e.message);
  } finally {
    chatSend.disabled = false;
    chatInput.focus();
  }
}

window.startChat = greet;
