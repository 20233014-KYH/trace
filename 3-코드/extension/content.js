// content.js — AI 사이트에서만 로드된다 (manifest 의 matches). Learn 모드 맥락 수집.
// 수집기와 같은 표기 — 현지 시각 + 시간대 (예: 2026-09-21T16:06:31+09:00). UTC 'Z' 로 보내면 로그를 눈으로 맞추기 어렵다
function localIso() {
  const d = new Date(), p = (n) => String(n).padStart(2, "0"), off = -d.getTimezoneOffset();
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}${off >= 0 ? "+" : "-"}${p(Math.floor(Math.abs(off) / 60))}:${p(Math.abs(off) % 60)}`;
}
// 보내는 것 (다리가 Learn 모드일 때만 받아준다 · Proof 면 403 으로 거절):
//   selection   — AI 로 넘어가기 직전 드래그한 글 ≤200자   (config.learn_context.selection 이 켜져 있을 때)
//   ai_question — 내가 AI 입력창에 보낸 질문 ≤500자        (ai_question)
// 답변 발췌(ai_answer_excerpt)는 "복사"로 잡힌다 — 수집기의 copy 이벤트가 길이·해시를 갖고, 원문은 여기서 보낸다.
// 아직 뼈대: 질문 감지는 사이트마다 입력창이 달라서 사이트별 셀렉터가 필요하다 (아래 TODO).

const MAX = { selection: 200, ai_question: 500, ai_answer_excerpt: 500 };
let toggles = null;

async function loadToggles() {
  const s = await chrome.runtime.sendMessage({ type: "status" }).catch(() => null);
  toggles = s?.mode === "learn" ? (s.learn_context || {}) : null;   // Proof 면 null → 아무것도 안 보냄
}
loadToggles();
setInterval(loadToggles, 30000);

function send(kind, text, meta = {}) {
  if (!toggles || !toggles[kind] || !text) return;
  const item = { id: crypto.randomUUID(), ts: localIso(), source: "browser", kind,
                 text: text.slice(0, MAX[kind] || 500), meta: { domain: location.hostname.replace(/^www\./, ""), ...meta } };
  chrome.runtime.sendMessage({ type: "context", items: [item] }).catch(() => {});
}

// ① 선택 텍스트 — 드래그가 멈추고 0.8초 뒤, 200자 이내만
let selTimer = null;
document.addEventListener("selectionchange", () => {
  clearTimeout(selTimer);
  selTimer = setTimeout(() => {
    const t = (window.getSelection()?.toString() || "").trim();
    if (t.length >= 8 && t.length <= MAX.selection) send("selection", t);
  }, 800);
});

// ② 답변 발췌 — 복사한 원문 (수집기의 copy 이벤트와 같은 순간)
document.addEventListener("copy", () => {
  const t = (window.getSelection()?.toString() || "").trim();
  if (t) send("ai_answer_excerpt", t);
});

// ③ AI 질문 — 사이트마다 입력창(textarea · contenteditable)과 보내는 방법(Enter · 버튼)이 다르다.
//    셀렉터를 사이트별로 두지 않고, "마지막으로 글자를 친 입력창"을 기억했다가 Enter 나 버튼 클릭 0.4초 뒤에
//    그 입력창이 비어 있으면 '보낸 것'으로 본다. ChatGPT · Claude · Gemini · 뤼튼 · Grok · DeepSeek · NotebookLM 공통.
let lastEl = null, lastText = "";
const editable = (el) => !!el && (el.tagName === "TEXTAREA" || el.isContentEditable);
const textOf = (el) => ((el.value ?? el.innerText) || "").trim();

document.addEventListener("input", (e) => {
  if (editable(e.target)) { lastEl = e.target; lastText = textOf(e.target); }
}, true);

function maybeSent() {
  const t = lastText;
  if (t.length < 2) return;
  setTimeout(() => {
    const now = lastEl && document.contains(lastEl) ? textOf(lastEl) : "";
    if (!now || now.length < t.length / 2) { send("ai_question", t); lastText = ""; }   // 비었거나 절반 아래로 줄었으면 보낸 것
  }, 400);
}
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.shiftKey || e.isComposing) return;
  if (editable(document.activeElement)) { lastEl = document.activeElement; lastText = textOf(lastEl); maybeSent(); }
}, true);
document.addEventListener("click", (e) => {
  if (e.target.closest && e.target.closest("button, [role=button]")) maybeSent();     // 보내기 버튼 (어느 사이트든)
}, true);
