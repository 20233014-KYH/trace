// 과제 카드 하나 그리기 — 홈 · 새 과제 미리 보기가 같이 쓴다 (캔버스 홈 A 카드) · 10/13
window.TraceWork = (function () {
  const T = window.TraceShell, el = T.el;
  const STEPS = [["record", "기록"], ["source", "출처 보기"], ["confirm", "연결 확인"], ["report", "내역서"]];
  const ICON = {
    cal: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    more: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    edit: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>',
    trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
    move: '<path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>',
    warn: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
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
      // 단계에 번호 (10/31 · 캔버스 홈 v2.2 ②) — 처음 쓰는 학생이 "지금 몇 번째인지" 바로 알게
      const s = el("span", done ? "done" : j === i ? "cur" : ""); s.append(el("i", null, String(j + 1)), document.createTextNode(name)); box.append(s);
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
    c.textContent = ""; c.className = "card wk" + (o.next ? " home" : "") + (o.old ? " old" : "");
    const h = el("div", "h");
    const tt = el(o.href ? "a" : "div", "tt", o.title); if (o.href) tt.href = o.href;
    // badge: false = 배지 없음 (홈 — 단계 줄 · 다음 할 일과 같은 말이면 뺌 · 10/31)
    const b = o.badge === false ? null : el("span", "badge " + (o.badge ? o.badge[1] : "outline"), o.badge ? o.badge[0] : "…");
    h.append(tt); if (b) h.append(b);
    if (o.settings) {                                               // ⋯ = 과제 설정 · 과제 삭제 (캔버스 Delete · 10/15)
      const m = el("button", "iconbtn"); m.type = "button"; m.title = "더 보기"; m.setAttribute("aria-label", "과제 메뉴"); m.append(T.icon(ICON.more));
      m.onclick = e => { e.preventDefault(); workMenu(m, { id: o.id, settings: o.settings, recording: o.recording, onDeleted: o.onDeleted }); };
      h.append(m);
    }
    const dd = due(o.due);
    const meta = el("span", "meta" + (dd && dd.soon ? " soon" : ""));
    meta.append(T.icon(ICON.cal), el("span", null, dd ? dd.text : o.last ? `${day(o.last)} 마지막 기록` : "마감 없음"));
    const st = el("div", "st"); steps(st, o.stage, o.made);
    const fb = el("div", "facts"); facts(fb, o.facts, o.wait);
    c.append(h, meta, st);                                           // 마감 줄은 늘 둠 — 빼면 카드마다 단계 줄 높이가 달라짐 (10/31)
    if (!o.next) c.append(fb);                                       // 홈은 숫자 대신 "다음 할 일" 한 줄 (10/31)
    if (o.warn) { const w = el("div", "warn"); w.append(T.icon(ICON.bell), el("span", null, o.warn)); c.append(w); }
    const ft = el("div", o.next ? "nx" + (o.next.done ? " done" : "") : "ft");
    if (o.next) {
      const n = el("div", "todo");
      n.append(el("span", "k", o.next.done ? "다 했어요" : "다음 할 일"), el("b", null, o.next.text));
      ft.append(n);
    }
    if (o.button) {
      const a = el("a", "btn " + (o.next ? "" : "btn-sm ") + (o.button[2] ? "btn-default" : "btn-outline"), o.button[0]); a.href = o.button[1];
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

  // 기록 상태 지켜보기 — 기록 창(별도 창)에서 끄기 · 멈춤 · 다시 시작을 하면 이 창은 그대로 보여서 새로 읽을 일이 없었다
  // (10/14: 끈 뒤에도 "기록 중" 이 남다가 홈으로 가야 바뀜). 3초마다 상태만 묻고 바뀌면 onChange()
  function watchRecording(onChange) {
    const key = r => r ? `${r.work_id}|${r.session_id}|${!!r.paused}` : "";
    let last = null;
    const look = async () => {
      if (document.hidden) return;
      let r; try { r = (await T.call("GET", "/local/recording")).recording; } catch (e) { return; }
      const k = key(r);
      if (last !== null && k !== last) onChange(r);
      last = k;
    };
    look(); return setInterval(look, 3000);
  }

  // ── ⋯ 메뉴 (과제 설정 · 과제 삭제) ──
  function workMenu(anchor, o) {
    document.querySelectorAll(".menu").forEach(x => x.remove());
    const m = el("div", "menu"); m.setAttribute("role", "menu");
    const a = el("a", "mi"); a.href = o.settings; a.setAttribute("role", "menuitem"); a.append(T.icon(ICON.edit), document.createTextNode("과제 설정"));
    const d = el("button", "mi red"); d.type = "button"; d.setAttribute("role", "menuitem"); d.append(T.icon(ICON.trash), document.createTextNode("과제 삭제"));
    if (o.recording) { d.setAttribute("aria-disabled", "true"); d.title = "기록 중에는 지울 수 없어요"; }
    d.onclick = () => { m.remove(); deleteWork(o.id, o.onDeleted); };
    m.append(a, el("div", "sep"), d);
    document.body.append(m);
    const r = anchor.getBoundingClientRect();
    m.style.top = Math.min(r.bottom + 4, innerHeight - m.offsetHeight - 8) + "px";
    m.style.left = Math.max(8, r.right - m.offsetWidth) + "px";
    const 닫기 = e => { if (!m.contains(e.target) && e.target !== anchor) { m.remove(); document.removeEventListener("mousedown", 닫기, true); } };
    setTimeout(() => document.addEventListener("mousedown", 닫기, true));
    m.addEventListener("keydown", e => { if (e.key === "Escape") { m.remove(); anchor.focus(); } });
    a.focus();
  }

  // ── 확인 창 틀 (과제 삭제 · 기록 지우기 · 옮기기 같이 씀) ──
  function dialog() {
    const dim = el("div", "t-modal"), dlg = el("div", "dlg"); dlg.setAttribute("role", "dialog"); dlg.setAttribute("aria-modal", "true");
    dim.append(dlg); document.body.append(dim);
    const close = () => dim.remove();
    dim.addEventListener("mousedown", e => { if (e.target === dim) close(); });
    dim.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
    const err = el("div", "err"); err.hidden = true;
    return { dlg, close, err };
  }
  // 확인 창 — 제목 · 설명 줄들 · [취소] [빨간 버튼] → run() 이 성공하면 닫고 done()
  function confirmBox(title, lines, okText, run, done) {
    const { dlg, close, err } = dialog();
    dlg.append(el("h3", null, title));
    lines.filter(Boolean).forEach(l => dlg.append(typeof l === "string" ? el("div", "desc", l) : l));
    const acts = el("div", "acts"), no = el("button", "btn btn-outline", "취소"), yes = el("button", "btn btn-red", okText);
    no.type = yes.type = "button"; no.onclick = close;
    yes.onclick = async () => {
      yes.disabled = no.disabled = true; err.hidden = true;
      try { await run(); close(); try { ["trace.works.v1", "trace.home.v1"].forEach(k => sessionStorage.removeItem(k)); } catch (e) {} done(); }
      catch (e) { err.textContent = e.message; err.hidden = false; yes.disabled = no.disabled = false; }
    };
    acts.append(no, yes); dlg.append(err, acts); no.focus();
    return dlg;
  }
  function busy(message) {                                          // 기록 중 — 못 지움 · 못 옮김
    const { dlg, close } = dialog();
    const ok = el("button", "btn btn-default", "확인"); ok.type = "button"; ok.onclick = close;
    const acts = el("div", "acts"); acts.append(ok);
    dlg.append(el("h3", null, "기록 중에는 할 수 없어요"), el("div", "desc", message), acts); ok.focus();
  }

  // ── 과제 삭제 — 한 번 확인. 과제 · 기록 · 내역서(PDF · 교수 링크)까지 모두 (내역서가 없어지는 건 이때뿐 · 10/15) ──
  async function deleteWork(wid, onDone) {
    let i;
    try { i = await T.call("GET", "/local/work/delete-info?work_id=" + encodeURIComponent(wid)); }
    catch (e) { alert(e.message); return; }
    if (i.recording) return busy(i.recording_this ? "기록 창에서 작업을 마친 뒤 지워 주세요." : "다른 과제를 기록하는 중이에요. 기록 창에서 작업을 마친 뒤 지워 주세요.");
    const 무엇 = i.sessions ? `이 과제와 기록 ${i.sessions}번${i.report_made ? ", 내역서(PDF · 교수 링크)" : ""}까지 모두 지워져요. 되돌릴 수 없어요.`
                            : "기록이 하나도 없어서 바로 지워져요.";
    let 메모 = null;
    if (i.report_made) {
      메모 = el("div", "note"); 메모.append(T.icon(ICON.warn), el("span", null, "교수가 QR 을 열면 \"학생이 지운 기록입니다\" 라고만 보여요. 내려받아 저장해 둔 PDF 파일은 Trace 가 지울 수 없으니 직접 지워 주세요."));
    }
    confirmBox(`"${i.title}" 를 지울까요?`, [무엇, 메모], "삭제",
               () => T.call("POST", "/local/work/delete", null, { work_id: wid }), onDone || (() => { location.href = "/home"; }));
  }

  // ── 과제 여러 개 한 번에 삭제 (홈 › 선택 · 10/31) — 확인 한 번, 하나씩 차례로 지움. 몇 개 실패해도 지운 건 지운 대로 ──
  async function deleteWorks(works, onDone) {                         // works = [{id, title}]
    const ids = works.map(w => w.id);
    let 정보;
    try { 정보 = await Promise.all(ids.map(w => T.call("GET", "/local/work/delete-info?work_id=" + encodeURIComponent(w)))); }
    catch (e) { alert(e.message); return; }
    if (정보.some(i => i.recording)) return busy("기록 창에서 작업을 마친 뒤 지워 주세요.");
    const 목록 = el("div", "lst");
    정보.forEach((i, n) => {
      목록.append(el("div", "k", works[n].title || i.title), el("div", "v" + (i.sessions ? "" : " keep"), i.sessions ? `기록 ${i.sessions}번${i.report_made ? " · 내역서" : ""}` : "기록 없음"));
    });
    let 메모 = null;
    if (정보.some(i => i.report_made)) {
      메모 = el("div", "note"); 메모.append(T.icon(ICON.warn), el("span", null, "내역서가 있는 과제는 교수가 QR 을 열면 \"학생이 지운 기록입니다\" 라고만 보여요. 내려받아 둔 PDF 파일은 직접 지워 주세요."));
    }
    const 못함 = [];
    confirmBox(`과제 ${ids.length}개를 지울까요?`, ["과제와 기록, 내역서(PDF · 교수 링크)까지 모두 지워져요. 되돌릴 수 없어요.", 목록, 메모], `${ids.length}개 삭제`,
      async () => {
        못함.length = 0;
        for (const [n, w] of ids.entries()) {
          try { await T.call("POST", "/local/work/delete", null, { work_id: w }); }
          catch (e) { 못함.push(`"${works[n].title || 정보[n].title}" — ${e.message}`); }
        }
        if (못함.length === ids.length) throw new Error(못함[0]);
      }, () => onDone(못함));
  }

  // ── 기록 하나 — ⋯ 다른 과제로 옮기기 · 이 기록만 지우기 (내역서는 그대로 · 10/15) ──
  function sessionMenu(anchor, o) {                                 // o = {wid, sid, when, recording, onDone}
    document.querySelectorAll(".menu").forEach(x => x.remove());
    const m = el("div", "menu"); m.setAttribute("role", "menu");
    const mv = el("button", "mi"); mv.type = "button"; mv.append(T.icon(ICON.move), document.createTextNode("다른 과제로 옮기기"));
    const rm = el("button", "mi red"); rm.type = "button"; rm.append(T.icon(ICON.trash), document.createTextNode("이 기록만 지우기"));
    [mv, rm].forEach(b => { b.setAttribute("role", "menuitem"); if (o.recording) { b.setAttribute("aria-disabled", "true"); b.title = "기록 중에는 할 수 없어요"; } });
    mv.onclick = () => { m.remove(); o.recording ? busy("기록 창에서 작업을 마친 뒤 옮겨 주세요.") : moveSession(o); };
    rm.onclick = () => { m.remove(); o.recording ? busy("기록 창에서 작업을 마친 뒤 지워 주세요.") : deleteSession(o); };
    m.append(mv, el("div", "sep"), rm);
    document.body.append(m);
    const r = anchor.getBoundingClientRect();
    m.style.top = Math.min(r.bottom + 4, innerHeight - m.offsetHeight - 8) + "px";
    m.style.left = Math.max(8, r.right - m.offsetWidth) + "px";
    const 닫기 = e => { if (!m.contains(e.target) && e.target !== anchor) { m.remove(); document.removeEventListener("mousedown", 닫기, true); } };
    setTimeout(() => document.addEventListener("mousedown", 닫기, true));
    m.addEventListener("keydown", e => { if (e.key === "Escape") { m.remove(); anchor.focus(); } });
    mv.focus();
  }
  function deleteSession(o) {
    confirmBox(`${o.when} 기록을 지울까요?`,
      ["이 기록의 AI 질문·답 · 붙여넣기 · 글 변화가 이 PC 와 서버에서 지워져요. 되돌릴 수 없어요.",
       "내역서(PDF · 교수 링크)는 그대로예요. 이미 낸 내역서엔 \"지운 기록 1개\" 로만 남아요."],
      "지우기", () => T.call("POST", "/local/session/delete", null, { work_id: o.wid, session_id: o.sid }), o.onDone);
  }
  async function moveSession(o) {
    let works = [];
    try { works = (await T.call("GET", "/local/works")).works.filter(w => w.id !== o.wid); } catch (e) { alert(e.message); return; }
    if (!works.length) { alert("옮길 다른 과제가 없어요. 새 과제를 먼저 만들어 주세요."); return; }
    const sel = el("select"); sel.className = "sel";
    works.forEach(w => { const op = el("option", null, w.title); op.value = w.id; sel.append(op); });
    const f = el("div"), lb = el("label", null, "옮길 과제"); lb.htmlFor = sel.id = "mv-to"; f.append(lb, sel);
    const dlg = confirmBox(`${o.when} 기록을 다른 과제로 옮길까요?`,
      ["다른 과제를 고른 채 기록을 켰을 때 바로잡는 거예요. 서버의 확인값도 같이 옮겨져서 \"서버 기록과 일치\" 는 그대로예요.", f],
      "옮기기", () => T.call("POST", "/local/session/move", null, { work_id: o.wid, session_id: o.sid, to: sel.value }), o.onDone);
    dlg.querySelector(".btn-red").className = "btn btn-default";
    sel.focus();
  }

  return { card, due, day, steps, facts, clock, dur, hm, startRecording, watchRecording, workMenu, deleteWork, deleteWorks, sessionMenu, dialog, ICON };
})();
