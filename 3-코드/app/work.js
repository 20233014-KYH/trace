// 과제 카드 하나 그리기 — 홈 · 새 과제 미리 보기가 같이 쓴다 (캔버스 홈 A 카드) · 10/13
window.TraceWork = (function () {
  const T = window.TraceShell, el = T.el;
  const STEPS = [["record", "기록"], ["source", "출처 보기"], ["confirm", "연결 확인"], ["report", "내역서"]];
  const ICON = {
    cal: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    more: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    bell: '<path d="M10.27 21a2 2 0 0 0 3.46 0"/><path d="M3.26 15.33A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.67C19.41 13.96 18 12.5 18 8A6 6 0 0 0 6 8c0 4.5-1.41 5.96-2.74 7.33"/>',
  };
  const DAYS = ["일", "월", "화", "수", "목", "금", "토"];

  // 마감 "2026-10-15T23:59" → {text:"10/15 (목) 23:59 마감 · D-2", soon: 하루 이내, days}
  function due(v) {
    if (!v) return null;
    const d = new Date(v.length === 10 ? v + "T23:59" : v); if (isNaN(d)) return null;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const day = new Date(d); day.setHours(0, 0, 0, 0);
    const n = Math.round((day - today) / 864e5);
    const hm = v.length > 10 ? ` ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}` : "";
    const left = n > 0 ? ` · D-${n}` : n === 0 ? " · 오늘" : " · 지남";
    return { text: `${d.getMonth() + 1}/${d.getDate()} (${DAYS[d.getDay()]})${hm} 마감${left}`, soon: n <= 1 && n >= 0, days: n };
  }
  function day(iso) { const d = new Date(iso); return isNaN(d) ? "" : `${d.getMonth() + 1}/${d.getDate()} (${DAYS[d.getDay()]})`; }

  function steps(box, at, made) {                                   // 기록 → 출처 보기 → 연결 확인 → 내역서
    box.textContent = "";
    const i = STEPS.findIndex(s => s[0] === at);
    STEPS.forEach(([k, name], j) => {
      if (j) box.append(el("em"));
      const done = made || (i >= 0 && j < i);
      const s = el("span", done ? "done" : j === i ? "cur" : ""); s.append(el("i"), document.createTextNode(name)); box.append(s);
    });
  }

  function facts(box, f, wait) {
    box.textContent = "";
    if (!f) { if (wait) box.append(el("span", "wait", wait)); return; }
    [[f.questions, "질문"], [f.answers, "결과물에 들어간 답"], [f.linked, "이어진 문장"]].forEach(([n, t]) => {
      if (n == null) return;
      const s = el("span"); s.append(el("b", null, String(n)), document.createTextNode(t)); box.append(s);
    });
    if (wait) box.append(el("span", "wait", wait));
  }

  // o = {id?, title, href?, settings?, due?, last?, badge:[글, 색], stage, made, facts, wait, warn?, button:[글, 주소, 진하게] | null, onButton?}
  function card(c, o) {
    c.textContent = ""; c.className = "card wk" + (o.old ? " old" : "");
    const h = el("div", "h");
    const tt = el(o.href ? "a" : "div", "tt", o.title); if (o.href) tt.href = o.href;
    const b = el("span", "badge " + (o.badge ? o.badge[1] : "outline"), o.badge ? o.badge[0] : "…");
    h.append(tt, b);
    if (o.settings) { const m = el("a", "iconbtn"); m.href = o.settings; m.title = "과제 설정"; m.setAttribute("aria-label", "과제 설정"); m.append(T.icon(ICON.more)); h.append(m); }
    const dd = due(o.due);
    const meta = el("span", "meta" + (dd && dd.soon ? " soon" : ""));
    meta.append(T.icon(ICON.cal), el("span", null, dd ? dd.text : o.last ? `${day(o.last)} 마지막 기록` : "마감 없음"));
    const st = el("div", "st"); steps(st, o.stage, o.made);
    const fb = el("div", "facts"); facts(fb, o.facts, o.wait);
    c.append(h, meta, st, fb);
    if (o.warn) { const w = el("div", "warn"); w.append(T.icon(ICON.bell), el("span", null, o.warn)); c.append(w); }
    const ft = el("div", "ft");
    if (o.button) {
      const a = el("a", "btn btn-sm " + (o.button[2] ? "btn-default" : "btn-outline"), o.button[0]); a.href = o.button[1];
      if (o.onButton) a.onclick = e => { e.preventDefault(); o.onButton(a); };
      ft.append(a);
    }
    c.append(ft);
    return { badge: b, steps: st, facts: fb, ft };
  }

  const two = n => String(n).padStart(2, "0");
  const clock = s => `${two(Math.floor(s / 3600))}:${two(Math.floor(s / 60) % 60)}:${two(s % 60)}`;
  function dur(s) { if (s == null) return ""; const h = Math.floor(s / 3600), m = Math.round(s / 60) % 60; return h ? `${h}시간 ${m}분` : `${Math.max(1, m)}분`; }
  function hm(iso) { const d = new Date(iso); return isNaN(d) ? "" : `${two(d.getHours())}:${two(d.getMinutes())}`; }

  // 기록 시작 — 알약을 켠다. 이미 켜져 있으면 그 말을 보여 줌
  async function startRecording(wid, btn, say) {
    if (btn) btn.setAttribute("aria-disabled", "true");
    try { const r = await T.call("POST", "/local/record/start", null, { work_id: wid }); say(r.message, true); setTimeout(() => location.reload(), 2500); }
    catch (e) { say(e.message, false); if (btn) btn.removeAttribute("aria-disabled"); }
  }

  return { card, due, day, steps, facts, clock, dur, hm, startRecording, ICON };
})();
