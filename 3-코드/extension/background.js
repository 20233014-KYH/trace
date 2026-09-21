// background.js — 탭이 바뀔 때마다 도메인을 수집기 다리(127.0.0.1:5077)에 알린다.
// 서버 주소·세션 id·로그인은 모른다. 수집기가 받아서 체인에 넣고 서버로 보낸다.
// 보내는 것: {type:"tab", domain, title}  — URL 전체·페이지 내용은 보내지 않는다.

const BRIDGE = "http://127.0.0.1:5077";
let last = null;            // 같은 도메인 연속 전환은 한 번만
let status = { recording: false, mode: null };

async function refreshStatus() {
  try {
    const r = await fetch(BRIDGE + "/status");
    status = r.ok ? await r.json() : { recording: false, mode: null };
  } catch { status = { recording: false, mode: null }; }
  chrome.storage.session.set({ status });
  return status;
}

function domainOf(url) {
  // http(s) 가 아닌 내부 페이지(새 탭 · chrome://)는 "" — 수집기가 "AI 탭에서 나갔다"로 알 수 있게 빈 도메인도 보낸다
  try { const u = new URL(url); return u.protocol.startsWith("http") ? u.hostname.replace(/^www\./, "") : ""; }
  catch { return ""; }
}

async function report(tab) {
  if (!tab || !tab.url) return;
  const domain = domainOf(tab.url);
  if (domain === last) return;
  last = domain;
  const ev = { type: "tab", domain, title: domain ? (tab.title || "").slice(0, 80) : "(브라우저 내부 페이지)" };
  try {
    const r = await fetch(BRIDGE + "/event", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(ev) });
    console.log("[Trace] tab →", domain, r.status);
  } catch (e) {
    console.log("[Trace] 수집기 꺼짐 — tab 이벤트 버림", domain);
  }
}

// 활성 탭이 바뀜
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  report(tab);
});
// 같은 탭에서 주소가 바뀜 (SPA 포함)
chrome.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (info.url || info.status === "complete") if (tab.active) report(tab);
});
// 창(브라우저 창) 포커스가 바뀜
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;
  const [tab] = await chrome.tabs.query({ active: true, windowId }).catch(() => []);
  report(tab);
});

// content.js 가 보내는 맥락 (Learn 모드에서만 다리가 받아준다)
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "context") {
    fetch(BRIDGE + "/context", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items: msg.items }) })
      .then((r) => sendResponse({ ok: r.ok, status: r.status })).catch(() => sendResponse({ ok: false }));
    return true;
  }
  if (msg?.type === "status") { refreshStatus().then(sendResponse); return true; }
});

chrome.alarms?.create?.("status", { periodInMinutes: 0.5 });
chrome.alarms?.onAlarm?.addListener(() => refreshStatus());
refreshStatus();
