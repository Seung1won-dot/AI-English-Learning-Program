// opic.js — OPIC 모드 (질문 받기 → 타이핑/음성 답변 → AI 첨삭)
// 공통 유틸(postJSON, show, esc …)은 common.js 에 있다.

// ---- 요소 ----
const topicChips = document.querySelectorAll(".opic-chip");
const questionBtn = document.getElementById("opicQuestionBtn");
const qLoading = document.getElementById("opicQLoading");
const qError = document.getElementById("opicQError");
const questionBox = document.getElementById("opicQuestionBox");
const qText = document.getElementById("opicQText");
const qKr = document.getElementById("opicQKr");
const qSpeak = document.getElementById("opicQSpeak");

const answerCard = document.getElementById("opicAnswerCard");
const micBtn = document.getElementById("micBtn");
const micHint = document.getElementById("micHint");
const answerInput = document.getElementById("opicAnswer");
const submitBtn = document.getElementById("opicSubmitBtn");
const aLoading = document.getElementById("opicALoading");
const aError = document.getElementById("opicAError");

const resultBox = document.getElementById("opicResult");
const scoreEl = document.getElementById("opicScore");
const correctedEl = document.getElementById("opicCorrected");
const feedbackEl = document.getElementById("opicFeedback");
const modelBlock = document.getElementById("opicModelBlock");
const modelEl = document.getElementById("opicModel");
const corrSpeak = document.getElementById("opicCorrSpeak");
const modelSpeak = document.getElementById("opicModelSpeak");
const retryBtn = document.getElementById("opicRetryBtn");

let topic = "자기소개";
let currentQuestion = "";

// ---- 주제 선택 ----
chipGroup(".opic-chip", (chip) => { topic = chip.dataset.topic; });

// ---- 질문 받기 ----
questionBtn.addEventListener("click", async () => {
  show(qError, false);
  show(qLoading, true);
  setBusy(questionBtn, true, "질문 만드는 중...");
  try {
    const data = await postJSON("/api/opic/question", { topic });
    show(document.getElementById("opicQFallback"), !!data.fallback);
    currentQuestion = data.question;
    qText.textContent = data.question;
    qKr.textContent = data.question_kr || "";
    qSpeak.dataset.text = data.question;
    show(questionBox, true);
    show(answerCard, true);
    show(resultBox, false);
    answerInput.value = "";
    questionBtn.dataset.idle = "다른 질문 받기";
    // 실전처럼 질문을 읽어준다
    if (window.speakText) window.speakText(data.question);
  } catch (e) {
    showError(qError, e.message);
  } finally {
    show(qLoading, false);
    setBusy(questionBtn, false);
  }
});

// ---- 음성 인식 (Web Speech API — 무료, 키 불필요) ----
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizing = false;
let recognition = null;

if (SpeechRecognition) {
  show(micBtn, true);
  micHint.textContent = "버튼을 누르고 영어로 말하면 글로 받아 적어줍니다.";

  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.continuous = true;   // 말이 끊겨도 계속 듣기

  recognition.onresult = (event) => {
    let text = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) text += event.results[i][0].transcript + " ";
    }
    if (text) {
      answerInput.value = (answerInput.value + " " + text).trim();
    }
  };
  recognition.onerror = (event) => {
    stopRecognition();
    if (event.error === "not-allowed") {
      micHint.textContent = "마이크 권한이 거부되었어요. 타이핑으로 답해 주세요.";
    } else if (event.error !== "aborted") {
      micHint.textContent = "음성 인식에 문제가 생겼어요. 다시 시도하거나 타이핑해 주세요.";
    }
  };
  recognition.onend = () => {
    if (recognizing) stopRecognition();
  };
} else {
  micHint.textContent = "이 브라우저는 음성 인식을 지원하지 않아요 (Chrome/Edge 권장). 타이핑으로 답해 주세요.";
}

function startRecognition() {
  recognizing = true;
  micBtn.classList.add("recording");
  micBtn.querySelector(".mic-label").textContent = "녹음 끝내기";
  recognition.start();
}
function stopRecognition() {
  recognizing = false;
  micBtn.classList.remove("recording");
  micBtn.querySelector(".mic-label").textContent = "말로 답하기";
  try { recognition.stop(); } catch (e) { /* 이미 멈춤 */ }
}

micBtn.addEventListener("click", () => {
  if (recognizing) stopRecognition();
  else startRecognition();
});

// ---- 첨삭 받기 ----
submitBtn.addEventListener("click", async () => {
  const answer = answerInput.value.trim();
  show(aError, false);
  if (!currentQuestion) { showError(aError, "먼저 질문을 받아 주세요."); return; }
  if (!answer) { showError(aError, "답변을 말하거나 입력해 주세요."); answerInput.focus(); return; }
  if (recognizing) stopRecognition();

  show(aLoading, true);
  setBusy(submitBtn, true, "검토 중...");
  try {
    const data = await postJSON("/api/opic/answer", {
      topic, question: currentQuestion, answer,
    });
    scoreEl.textContent = data.score;
    scoreEl.className = "score-pill " + scoreClass(data.score);
    correctedEl.textContent = data.corrected;
    corrSpeak.dataset.text = data.corrected;
    feedbackEl.textContent = data.feedback;
    modelEl.textContent = data.model_answer || "";
    modelSpeak.dataset.text = data.model_answer || "";
    show(modelBlock, Boolean(data.model_answer));
    show(resultBox, true);
    resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    showError(aError, e.message);
  } finally {
    show(aLoading, false);
    setBusy(submitBtn, false);
  }
});

// ---- 같은 주제 다시 연습 ----
retryBtn.addEventListener("click", () => {
  answerInput.value = "";
  show(resultBox, false);
  answerInput.focus();
});
