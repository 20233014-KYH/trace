// 제목 줄 없는 앱 창 (Trace.exe · 10/13) — 화면에 그린 ─ □ ✕ 버튼 · 위 줄 두 번 눌러 최대화 · 오른쪽 · 아래 가장자리로 크기 바꾸기
// 브라우저(개발용)에서는 pywebview 가 없어서 아무것도 안 함. 버튼은 class="win" 안의 data-w="min|max|close"
(function () {
  const api = () => window.pywebview && window.pywebview.api;
  // 맥 앱 창 (10/14): 맥 표준 창 버튼(빨강 · 노랑 · 초록)을 왼쪽 위에 쓴다 — 오른쪽 ─ □ ✕ 는 숨기고, 왼쪽 위에 버튼 자리를 비운다.
  // 버튼은 trace_app._맥_창 이 위 줄(44px) 가운데에 놓는다. 앱 창(WKWebView)엔 "Safari/" 가 없어서 브라우저(개발용)와 가린다
  const MAC = /Macintosh/.test(navigator.userAgent) && !/Safari\//.test(navigator.userAgent);
  if (MAC) {
    document.documentElement.classList.add("mac");
    const st = document.createElement("style");
    st.textContent = ".mac .win{display:none!important}.mac .drag{right:0!important}"
      + ".mac .brand{padding-left:84px!important}"                                  // 로고 줄 = 창 버튼 오른쪽부터
      + ".mac .rail .side{padding-top:var(--bar,44px)}.mac .rail .brand{padding-left:9px!important}"   // 접으면 버튼 줄을 비우고 한 줄 아래
      + ".mac .rail .top{padding-left:24px}";                                       // 접은 메뉴(56px)보다 넓은 버튼 끝이 ← 와 안 겹치게
    (document.head || document.documentElement).append(st);
  }
  function call(name, ...a) { const x = api(); return x && x[name] ? x[name](...a) : null; }

  // □ 최대화 ↔ ⧉ 이전 크기로 (10/14) — 최대화 상태면 겹친 네모로 바꿔 그린다
  const ICON = { max: '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
                 restore: '<rect x="5" y="9" width="10" height="10" rx="1.5"/><path d="M9 9V6.5A1.5 1.5 0 0 1 10.5 5h7A1.5 1.5 0 0 1 19 6.5v7a1.5 1.5 0 0 1-1.5 1.5H15"/>' };
  function setMax(on) {
    document.querySelectorAll('.win [data-w="max"]').forEach(b => {
      const svg = b.querySelector("svg"); if (svg) svg.innerHTML = on ? ICON.restore : ICON.max;
      const t = on ? "이전 크기로" : "최대화"; b.title = t; b.setAttribute("aria-label", t);
    });
  }
  async function toggleMax() { const r = await call("window_control", "max"); if (typeof r === "boolean") setMax(r); }

  function bind() {
    document.querySelectorAll(".win [data-w]").forEach(b => { b.onclick = () => b.dataset.w === "max" ? toggleMax() : call("window_control", b.dataset.w); });
    document.querySelectorAll(".pywebview-drag-region").forEach(r => {
      r.addEventListener("dblclick", e => { if (!e.target.closest("button, a, input, select, textarea, .steps, .seg")) toggleMax(); });
    });
    // 페이지를 옮기면 새로 그려져 □ 로 돌아가니 지금 상태를 묻는다 (pywebview 가 준비된 뒤)
    const ask = () => { const r = call("is_maximized"); if (r && r.then) r.then(v => setMax(!!v)); };
    if (api()) ask(); else window.addEventListener("pywebviewready", ask, { once: true });
    if (MAC) return;                    // 맥 창은 가장자리 크기 조절 · 초록 버튼(확대)을 맥이 그대로 준다
    // 가장자리 크기 바꾸기 — 제목 줄 없는 창은 윈도우가 크기 조절 테두리를 안 줘서 직접 (오른쪽 · 아래 · 오른쪽 아래)
    [["r", "position:fixed;top:0;right:0;width:6px;height:100vh;cursor:ew-resize"],
     ["b", "position:fixed;left:0;bottom:0;width:100vw;height:6px;cursor:ns-resize"],
     ["rb", "position:fixed;right:0;bottom:0;width:14px;height:14px;cursor:nwse-resize"]].forEach(([k, css]) => {
      const h = document.createElement("div"); h.style.cssText = css + ";z-index:9999"; h.dataset.edge = k;
      h.addEventListener("mousedown", e => {
        if (!api()) return;
        e.preventDefault();
        const sx = e.screenX, sy = e.screenY, w0 = window.outerWidth, h0 = window.outerHeight;
        let raf = 0, w = w0, hh = h0;
        const move = ev => {
          if (k.includes("r")) w = Math.max(1024, w0 + ev.screenX - sx);
          if (k.includes("b")) hh = Math.max(640, h0 + ev.screenY - sy);
          if (!raf) raf = requestAnimationFrame(() => { raf = 0; call("resize_to", w, hh); });
        };
        const up = () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
        window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
      });
      document.body.append(h);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
})();
