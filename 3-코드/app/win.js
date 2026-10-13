// 제목 줄 없는 앱 창 (Trace.exe · 10/13) — 화면에 그린 ─ □ ✕ 버튼 · 위 줄 두 번 눌러 최대화 · 오른쪽 · 아래 가장자리로 크기 바꾸기
// 브라우저(개발용)에서는 pywebview 가 없어서 아무것도 안 함. 버튼은 class="win" 안의 data-w="min|max|close"
(function () {
  const api = () => window.pywebview && window.pywebview.api;
  function call(name, ...a) { const x = api(); return x && x[name] ? x[name](...a) : null; }

  function bind() {
    document.querySelectorAll(".win [data-w]").forEach(b => { b.onclick = () => call("window_control", b.dataset.w); });
    document.querySelectorAll(".pywebview-drag-region").forEach(r => {
      r.addEventListener("dblclick", e => { if (!e.target.closest("button, a, input, select, textarea, .steps, .seg")) call("window_control", "max"); });
    });
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
