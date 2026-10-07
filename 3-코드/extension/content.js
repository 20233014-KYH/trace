// content.js — AI 사이트에서만 로드된다 (manifest 의 matches).
// 하는 일: 화면에 뜬 **AI 질문·답 원문**을 수집기 다리(127.0.0.1:5077)로 보낸다 — 복사하지 않은 답도.
// 수집기가 받아서 ① 가리고(API 키·개인정보) ② PC 에 저장하고 ③ 체인엔 해시만(ai_msg) 넣는다. 서버로 원문은 안 간다.
//
// 사이트마다 화면 구조가 달라서 "질문·답 덩어리를 찾는 법"만 사이트별(SITES)로 두고,
// 언제 보낼지는 공통 규칙: 글이 더 이상 안 바뀌면(질문 0.6초 · 답 2초) + 생성 중 표시가 없으면 보낸다.
// 같은 글은 한 번만 보낸다. 답을 다시 생성하면 바뀐 글을 또 보낸다(수집기가 같은 해시는 거른다).
//
// 사이트 구조가 바뀌면 SITES 의 셀렉터만 고치면 된다. 셀렉터가 하나도 안 맞으면 아무것도 안 보낸다(조용히 실패).

function localIso() {
  const d = new Date(), p = (n) => String(n).padStart(2, "0"), off = -d.getTimezoneOffset();
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}${off >= 0 ? "+" : "-"}${p(Math.floor(Math.abs(off) / 60))}:${p(Math.abs(off) % 60)}`;
}

const MAX_TEXT = 200000;                    // 한 메시지 상한(안전장치). 실제 답은 이보다 훨씬 짧다
const STABLE_MS = { question: 600, answer: 2000 };
// 이전 대화 = 이 페이지(대화)를 연 뒤 학생이 아직 아무것도 안 보냈을 때 뜬 메시지 (받은 시각 모름).
// 시간으로 자르지 않는다 — 실제 ChatGPT 는 열고 나서 몇 초 뒤에야 대화를 그린다 (10/4 실사이트 시험).
const UI_LINES = new Set(["Copy code", "코드 복사", "복사", "Copy", "Copied!", "복사됨", "Edit", "편집", "실행", "실행됨", "Run", "Ran"]);

// 속성 이름 끝이 같은 것 찾기 — ChatGPT 는 속성 이름 가운데에 바뀌는 글자를 넣는다 (예: data-markdown-talvt-render-state)
const attrEnd = (el, end) => { for (const a of el?.attributes || []) if (a.name.endsWith(end)) return a.value; return null; };

// ───────────── 사이트별: 질문·답 덩어리 찾기 ─────────────
function isBusyChatGPT(el) {
  const rs = attrEnd(el, "-render-state");                       // 없으면 null → 아래 generating() 로 판단
  let resp = null;
  for (let p = el.parentElement; p && resp === null; p = p.parentElement) resp = attrEnd(p, "-response-state");
  if (rs === null && resp === null) return undefined;
  return (rs !== null && rs !== "ready") || (resp !== null && resp !== "complete");
}
const SITES = [
  {
    tool: "ChatGPT",
    host: /(^|\.)chatgpt\.com$|(^|\.)chat\.openai\.com$/,
    messages: () => [...document.querySelectorAll("[data-message-author-role]")].map((el) => {
      const r = el.getAttribute("data-message-author-role");
      return {
        el, role: r === "user" ? "question" : r === "assistant" ? "answer" : null,
        id: el.getAttribute("data-message-id") || "",
        model: el.getAttribute("data-message-model-slug") || "",
        body: el.querySelector(".markdown") || el.querySelector(".whitespace-pre-wrap") || el,
        // 2026-10 화면: 답 덩어리에 *-render-state="ready", 답 묶음에 *-response-state="complete" 가 붙으면 생성 끝
        streaming: r === "assistant" ? isBusyChatGPT(el) : undefined,
      };
    }),
    generating: () => !!document.querySelector('[data-testid="stop-button"], .result-streaming'),
    conv: () => (location.pathname.match(/\/c\/([\w-]+)/) || [])[1] || "",
  },
  {
    tool: "Claude",
    host: /(^|\.)claude\.ai$/,
    messages: () => [...document.querySelectorAll('[data-testid="user-message"], [data-is-streaming]')].map((el) =>
      el.matches('[data-testid="user-message"]')
        ? { el, role: "question", body: el }
        : { el, role: "answer", body: el.querySelector(".font-claude-response, .font-claude-message") || el,
            streaming: el.getAttribute("data-is-streaming") === "true" }),
    generating: () => !!document.querySelector('[data-is-streaming="true"]'),
    conv: () => (location.pathname.match(/\/chat\/([\w-]+)/) || [])[1] || "",
  },
  {
    tool: "Gemini",
    host: /(^|\.)gemini\.google\.com$/,
    messages: () => [...document.querySelectorAll("user-query, model-response")].map((el) =>
      el.tagName.toLowerCase() === "user-query"
        ? { el, role: "question", body: el.querySelector(".query-text") || el }
        : { el, role: "answer", body: el.querySelector("message-content") || el.querySelector(".markdown") || el }),
    generating: () => false,                // 생성 중 표시를 못 찾으면 "2초 동안 안 바뀜" 만으로 판단
    conv: () => (location.pathname.match(/\/app\/([\w-]+)/) || [])[1] || "",
  },
];
const host = location.hostname.replace(/^www\./, "");
const site = SITES.find((s) => s.tool === globalThis.__TRACE_SITE) || SITES.find((s) => s.host.test(host)) || null;   // __TRACE_SITE: 시험용 강제 지정

// ───────────── 수집기 상태 · 보내기 ─────────────
let toggles = null;                          // null = 기록 중 아님 → 아무것도 안 보냄
async function loadToggles() {
  const s = await chrome.runtime.sendMessage({ type: "status" }).catch(() => null);
  toggles = s?.recording ? (s.capture || s.learn_context || {}) : null;   // learn_context = 옛 수집기 이름
}
loadToggles();
setInterval(loadToggles, 30000);

const on = (kind) => !!toggles && (kind === "ai_question" || kind === "ai_answer" ? toggles[kind] !== false : !!toggles[kind]);

function send(kind, text, meta = {}) {
  if (!on(kind) || !text) return false;
  const item = { id: crypto.randomUUID(), ts: localIso(), source: "browser", kind, text: text.slice(0, MAX_TEXT),
                 meta: { domain: host, url: location.origin + location.pathname, ...meta } };
  (globalThis.__traceSent ||= []).push(item);                     // 시험용 기록 (확장 안에서는 아무도 안 봄)
  chrome.runtime.sendMessage({ type: "context", items: [item] }).catch(() => {});
  console.debug("[Trace]", kind, meta.turn ?? "", text.length + "자", meta.history ? "(이전 대화)" : "");
  return true;
}

function clean(body) {
  return (body.innerText || "").split("\n").filter((l) => !UI_LINES.has(l.trim())).join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

// ───────────── 질문·답 덩어리 지켜보기 ─────────────
const seen = new Map();                      // key → {text, changedAt, firstAt, sent, history}
let navAt = Date.now(), lastPath = location.pathname, lastSendAt = 0;
const SEND_NAV_MS = 5000;                   // 보내고 5초 안에 주소가 바뀌면(새 대화의 첫 질문 → /c/id) 같은 대화로 본다

function scan() {
  if (!site) return false;
  if (location.pathname !== lastPath) { lastPath = location.pathname; if (Date.now() - lastSendAt > SEND_NAV_MS) navAt = Date.now(); }
  const now = Date.now(), conv = site.conv(), msgs = site.messages().filter((m) => m.role);
  let pending = false;
  msgs.forEach((m, i) => {
    const key = m.id || `${conv}|${i}|${m.role}`;
    let st = seen.get(key);
    const tail = i >= msgs.length - 3;
    if (st && st.sent && !tail) return;      // 이미 보냈고 끝부분이 아니면 다시 안 읽음 (긴 대화에서 가볍게)
    const text = clean(m.body);
    if (!st) {
      st = { text: "", changedAt: now, firstAt: now, sent: "",
             history: lastSendAt < navAt };
      seen.set(key, st);
    }
    if (text !== st.text) { st.text = text; st.changedAt = now; }
    if (!text || text === st.sent) return;
    const still = now - st.changedAt >= STABLE_MS[m.role];
    const busy = m.role === "answer" && (m.streaming ?? (i === msgs.length - 1 && site.generating()));
    if (!still || busy) { pending = true; return; }
    if (send(m.role === "question" ? "ai_question" : "ai_answer", text,
             { tool: site.tool, conv, turn: i + 1, model: m.model || "", history: st.history, msg_id: m.id || "" }))
      st.sent = text;
    else if (toggles) st.sent = text;         // 토글이 꺼진 항목은 다시 시도하지 않음
    else pending = true;                      // 기록 중이 아니면 나중에 다시
  });
  return pending;
}

// 진단 — 그 사이트의 localStorage 에 traceDebug=1 이 있을 때만 <html data-trace-debug> 에 상태를 적는다 (평소엔 아무것도 안 남김)
let DEBUG = false;
try { DEBUG = localStorage.getItem("traceDebug") === "1"; } catch {}
const dbg = { ver: chrome.runtime.getManifest?.().version, site: site?.tool || null, recording: null, scans: 0, msgs: 0, sent: 0, lastErr: "" };
function debugMark() { if (DEBUG) document.documentElement.setAttribute("data-trace-debug", JSON.stringify(dbg)); }
debugMark();

let timer = null, waitingSince = 0;
function schedule(ms = 400) {
  // 화면이 바뀔 때마다 다시 미룬다(생성 중엔 계속 바뀜). 단 3초 넘게 밀리면 한 번은 읽는다(끝없이 움직이는 화면 대비)
  if (!waitingSince) waitingSince = Date.now();
  if (Date.now() - waitingSince > 3000) ms = 0;
  clearTimeout(timer);
  timer = setTimeout(() => {
    waitingSince = 0;
    let more = false;
    try { more = scan(); } catch (e) { dbg.lastErr = String(e).slice(0, 200); }
    dbg.scans++; dbg.recording = !!toggles; dbg.msgs = seen.size; dbg.sent = (globalThis.__traceSent || []).length; debugMark();
    if (more) schedule(700);                                       // 아직 안 끝난 답이 있으면 계속 지켜봄
  }, ms);
}
if (site) {
  new MutationObserver(() => schedule()).observe(document.body, { childList: true, subtree: true, characterData: true });
  schedule(1500);
}

// 보낸 순간 기억 — "대화를 연 직후 뜬 메시지 = 이전 대화" 판단에서 내가 방금 보낸 질문을 빼려고
document.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) lastSendAt = Date.now(); }, true);
document.addEventListener("click", (e) => { if (e.target.closest?.("button, [role=button]")) lastSendAt = Date.now(); }, true);

// ───────────── 사이트 구조를 모르는 AI 사이트: 질문만 입력창으로 짐작 ─────────────
// "마지막으로 글자를 친 입력창"이 Enter·버튼 0.4초 뒤에 비어 있으면 '보낸 것'으로 본다. 답은 못 잡는다(복사 발췌만).
if (!site) {
  let lastEl = null, lastText = "";
  const editable = (el) => !!el && (el.tagName === "TEXTAREA" || el.isContentEditable);
  const textOf = (el) => ((el.value ?? el.innerText) || "").trim();
  document.addEventListener("input", (e) => { if (editable(e.target)) { lastEl = e.target; lastText = textOf(e.target); } }, true);
  const maybeSent = () => {
    const t = lastText;
    if (t.length < 2) return;
    setTimeout(() => {
      const now = lastEl && document.contains(lastEl) ? textOf(lastEl) : "";
      if (!now || now.length < t.length / 2) { send("ai_question", t, { tool: host }); lastText = ""; }
    }, 400);
  };
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" || e.shiftKey || e.isComposing) return;
    if (editable(document.activeElement)) { lastEl = document.activeElement; lastText = textOf(lastEl); maybeSent(); }
  }, true);
  document.addEventListener("click", (e) => { if (e.target.closest?.("button, [role=button]")) maybeSent(); }, true);
}

// ───────────── 그 밖의 맥락 (옛 Learn 항목 · 토글이 켜져 있을 때만) ─────────────
let selTimer = null;
document.addEventListener("selectionchange", () => {
  clearTimeout(selTimer);
  selTimer = setTimeout(() => {
    const t = (window.getSelection()?.toString() || "").trim();
    if (t.length >= 8 && t.length <= 200) send("selection", t);
  }, 800);
});
document.addEventListener("copy", () => {                       // 복사한 발췌 — 수집기의 copy 이벤트(길이·해시)와 같은 순간
  const t = (window.getSelection()?.toString() || "").trim();
  if (t) send("ai_answer_excerpt", t.slice(0, 2000));
});
