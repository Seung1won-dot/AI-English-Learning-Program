// tts.js — 발음 듣기 (브라우저 내장 음성합성, 무료·키 불필요)

function speakText(text) {
  if (!text || !("speechSynthesis" in window)) return;
  try {
    window.speechSynthesis.cancel();           // 이전 음성 중단
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  } catch (e) {
    /* 음성 미지원 브라우저는 조용히 무시 */
  }
}
window.speakText = speakText;

// 🔊 버튼은 동적으로 생기는 것도 있으므로 이벤트 위임으로 처리
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".speak-btn");
  if (btn) {
    e.stopPropagation();                        // 카드 뒤집기 등과 충돌 방지
    speakText(btn.dataset.text);
  }
});

// 🔊 버튼 HTML 을 만드는 헬퍼 (JS 에서 카드 생성 시 사용)
function speakBtn(text) {
  const safe = (text == null ? "" : String(text)).replace(/"/g, "&quot;");
  return `<button class="speak-btn" data-text="${safe}" title="발음 듣기">🔊</button>`;
}
window.speakBtn = speakBtn;
