// Trace PC 앱 화면 틀 — 왼쪽 메뉴 접기 · ← → · 창 버튼 · 과제 목록. 출처 보기 · 연결 확인이 같이 쓴다 (10/12)
window.TraceShell = (function () {
  const $ = id => document.getElementById(id);

  async function call(method, path, body, json) {
    const opt = { method, headers: { "X-Trace-Local": "1" } };
    if (json) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(json); }
    else if (body) opt.body = body;
    const r = await fetch(path, opt);
    let d = {};
    try { d = await r.json(); } catch (e) { d = { message: `응답을 읽지 못했습니다 (HTTP ${r.status})` }; }
    if (!r.ok) throw Object.assign(new Error(d.message || `HTTP ${r.status}`), { code: r.status, data: d });
    return d;
  }
  function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function hm(iso) { const m = String(iso || "").match(/T(\d{2}):(\d{2})/); return m ? `${m[1]}:${m[2]}` : ""; }
  function md(iso) { const m = String(iso || "").match(/^\d{4}-(\d{2})-(\d{2})/); return m ? `${+m[1]}/${+m[2]}` : ""; }
  function icon(d) { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("viewBox", "0 0 24 24"); s.innerHTML = d; return s; }
  function svgFile() { return icon('<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/>'); }

  // ── 왼쪽 메뉴 접기 · 위 줄 ──
  const RAIL = "trace.rail";
  function railTitle(on) {
    const t = on ? "메뉴 펴기" : "메뉴 접기";
    $("b-rail").title = t; $("b-rail").setAttribute("aria-label", t); $("b-rail").setAttribute("aria-expanded", String(!on));
  }
  // 과제 하나의 단계: 출처 보기 → 연결 확인 → 내역서. ← → 는 브라우저 기록이 아니라 "이 과제의" 앞 · 다음 단계로 간다
  const STEPS = [["source", "/source", "출처 보기"], ["confirm", "/confirm", "연결 확인"], ["report", "/export", "내역서"]];
  const stepUrl = (s, wid) => s[1] + "?work=" + encodeURIComponent(wid);

  function init(opt) {
    opt = opt || {};
    const i = STEPS.findIndex(s => s[0] === opt.step);
    const prev = opt.wid && i > 0 ? STEPS[i - 1] : null, next = opt.wid && i >= 0 && i < STEPS.length - 1 ? STEPS[i + 1] : null;
    [[$("b-back"), prev, "이전 단계"], [$("b-fwd"), next, "다음 단계"]].forEach(([b, s, t]) => {
      b.disabled = !s;
      b.title = s ? `${t}: ${s[2]}` : (t === "이전 단계" ? "이 과제의 첫 단계입니다" : "이 과제의 마지막 단계입니다");
      b.onclick = () => { if (s) location.href = stepUrl(s, opt.wid); };
    });
    // 단계 점은 이 과제가 실제로 어디까지 했는지로 칠한다 (연결 확인을 끝낸 과제는 출처 보기에서 봐도 연결 확인이 ●)
    if (opt.wid) call("GET", "/local/stage?work_id=" + encodeURIComponent(opt.wid)).then(r => {
      const at = STEPS.findIndex(s => s[0] === r.stage);
      document.querySelectorAll(".steps [data-s]").forEach(sp => {
        const k = STEPS.findIndex(s => s[0] === sp.dataset.s);
        if (sp.dataset.s === opt.step) return;
        sp.classList.toggle("done", k < i || k < at || (sp.dataset.s === "report" && r.report_made));   // 지금 화면 앞 단계는 늘 ●
      });
    }).catch(() => {});
    // 위 줄 단계 이름도 누르면 그 과제의 그 단계로 (지금 단계 · 기록은 빼고)
    document.querySelectorAll(".steps [data-s]").forEach(sp => {
      const s = STEPS.find(x => x[0] === sp.dataset.s);
      if (!s || !opt.wid || s[0] === opt.step) return;
      sp.classList.add("step-go"); sp.tabIndex = 0; sp.setAttribute("role", "link"); sp.title = `${s[2]}(으)로`;
      sp.onclick = () => location.href = stepUrl(s, opt.wid);
      sp.onkeydown = e => { if (e.key === "Enter") sp.onclick(); };
    });
    try {                                                   // 처음 그릴 때는 움직이지 않게 (기억해 둔 상태로 바로)
      if (localStorage.getItem(RAIL) === "1") {
        document.querySelector(".side").style.transition = "none";
        $("app").classList.add("rail"); railTitle(true);
        requestAnimationFrame(() => requestAnimationFrame(() => document.querySelector(".side").style.transition = ""));
      }
    } catch (e) {}
    $("b-rail").onclick = () => {
      const on = $("app").classList.toggle("rail");
      railTitle(on);
      try { localStorage.setItem(RAIL, on ? "1" : "0"); } catch (e) {}
    };
    // 창 버튼 — 앱(pywebview)에서 window_control 을 열어 주면 동작. 브라우저에선 아무것도 안 함
    document.querySelectorAll(".win button").forEach(b => b.onclick = () => {
      const api = window.pywebview && window.pywebview.api;
      if (api && api.window_control) api.window_control(b.dataset.w);
    });
  }

  // ── 왼쪽 과제 목록 · 위 줄 과제 이름. 과제를 누르면 /go → 그 과제가 지금 있는 단계 화면 (보던 화면 그대로가 아님) ──
  async function loadWorks(wid, opt) {
    opt = opt || {};
    let pc = [];
    try { pc = (await call("GET", "/local/source/works")).works; } catch (e) {}
    let mine = null;
    try {
      const s = await call("GET", "/local/state");
      if (s.logged_in) {
        const d = await call("GET", "/local/works");
        mine = d.works;
        $("me").innerHTML = "";
        const av = el("div", "av", (s.user.name || "?").slice(0, 1));
        const t = el("div"); t.append(el("span", null, s.user.name || ""), el("small", null, s.user.email || ""));
        $("me").append(av, t);
      }
    } catch (e) { mine = null; }
    if (!mine) {
      $("me").innerHTML = "";
      const a = el("a", "nav", null); a.href = "/login"; a.append(el("span", "t", "로그인하면 과제 이름이 보입니다"));
      $("me").append(a);
    }
    // 내 과제는 기록이 없어도 보임 (새 과제를 만들면 바로 왼쪽에 생겨야 함 · 10/13)
    const works = mine ? mine : pc.map(w => ({ id: w.id, title: w.id, pc_sessions: w.pc_sessions }));
    const box = $("works"); box.textContent = "";
    works.forEach(w => {
      const a = el("a", "nav" + (w.id === wid ? " on" : ""));
      a.href = "/go?work=" + encodeURIComponent(w.id);
      a.title = w.title;
      a.append(svgFile(), el("span", "t", w.title));
      box.append(a);
    });
    if (!works.length) box.append(el("div", "hint", "이 PC 에 기록한 과제가 없습니다"));
    const me = works.find(w => w.id === wid);
    if ($("c-work")) $("c-work").textContent = me ? me.title : (wid || "과제");
    if (!wid && works.length && !opt.stay) location.replace("/go?work=" + encodeURIComponent(works[0].id));
    return works;
  }

  return { call, el, hm, md, icon, svgFile, init, loadWorks };
})();
