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
    // ← 갈 곳: 단계 화면이 아닌 곳(과제 상세 · 기록 다시 보기 · 설정 …)은 화면이 정한다 · 첫 단계(출처 보기)는 과제 상세로 (10/14 · 전엔 꺼져 있었음)
    const back = opt.back || (opt.wid && i === 0 ? ["/work?work=" + encodeURIComponent(opt.wid), "과제로"] : null);
    if (back) {
      const b = $("b-back"), [to, t] = Array.isArray(back) ? back : [back, "뒤로"];
      b.disabled = false; b.title = t; b.setAttribute("aria-label", t);
      b.onclick = () => typeof to === "function" ? to() : location.href = to;
    }
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
    // 창 버튼 · 위 줄 두 번 눌러 최대화 · 가장자리 크기 바꾸기는 /ui/win.js (제목 줄 없는 앱 창 · 10/13)
    새버전();
    바뀌었나();
  }

  // ── 새 버전 (10/14 · app/updater.py) — 왼쪽 메뉴 아래에 "새 버전 · 업데이트". 누르면 앱이 직접 받아 바꾸고 다시 연다
  //    (맥은 내려받기 화면에서 받을 때마다 "열지 않음" 이 떠서). 서버에 묻는 건 앱이 10분에 한 번만 (app/updater.최신)
  async function 새버전() {
    let u = null;                                  // 10분 기억은 앱(updater.최신)이 한다 — 업데이트 뒤 새로 켠 앱은 새로 물음
    try { u = await call("GET", "/local/update"); } catch (e) { return; }
    const side = document.querySelector(".side");
    if (!u || !u.newer || !side || side.querySelector(".upd")) return;
    const box = el("div", "upd"), t = el("span", "t", `새 버전 v${u.latest}`);
    const b = el("button", "btn btn-default btn-sm", u.can_install ? "업데이트" : "내려받기"); b.type = "button";
    b.title = u.can_install ? "Trace 가 새 버전을 받아 바꾸고 다시 열어요" : "내려받기 화면에서 받아 주세요";
    box.append(t, b);
    b.onclick = () => 바뀐것(u, false, t);
    const me = side.querySelector(".me");
    me ? side.insertBefore(box, me) : side.append(box);
  }

  // ── 바뀐 것 창 (10/14) — iOS 업데이트처럼 누르기 전에 무엇이 바뀌는지. 릴리스 글의 학생용 요약 (app/updater.요약)
  //    after=true 면 업데이트 뒤 처음 열 때 "v… 로 바뀌었어요" (한 번만)
  function 바뀐것(u, after, 줄) {
    const sum = u.summary || {}, v = after ? u.version : u.latest;
    const bg = el("div", "sheet-bg"), sh = el("div", "sheet");
    sh.setAttribute("role", "dialog"); sh.setAttribute("aria-modal", "true");
    sh.append(el("div", "eyebrow", after ? "업데이트 완료" : "새 버전"), el("h3", null, after ? `v${v} 로 바뀌었어요` : `v${v} 에서 바뀐 것`));
    if (sum.title) sh.append(el("p", "lead", sum.title));
    if (sum.items && sum.items.length) { const ul = el("ul"); sum.items.forEach(x => ul.append(el("li", null, x))); sh.append(ul); }
    else if (!sum.title) sh.append(el("p", "lead", "자세한 내용은 내려받기 화면에서 볼 수 있어요."));
    if (sum.record) { const r = el("div", "box rec"); r.append(el("b", null, "기록하는 것이 바뀌어요"), el("span", null, sum.record)); sh.append(r); }
    if (sum.todo) { const r = el("div", "box todo"); r.append(el("b", null, after ? "해 주세요" : "업데이트 뒤 할 일"), el("span", null, sum.todo)); sh.append(r); }
    if (!after && /Macintosh/.test(navigator.userAgent))
      sh.append(el("p", "note", "업데이트하면 Trace 가 잠깐 꺼졌다 다시 열려요. 맥은 설정 › 기록 의 권한이 꺼질 수 있어요 — [설정 열기] 로 다시 켜 주세요."));
    const msg = el("p", "note"), foot = el("div", "foot");
    const 닫기 = () => { bg.remove(); if (after) call("POST", "/local/update/seen", null, {}).catch(() => {}); };
    const later = el("button", "b", after ? "확인" : "나중에"); later.type = "button"; later.onclick = 닫기;
    foot.append(later);
    if (!after) {
      const go = el("button", "b dark", u.can_install ? "지금 업데이트" : "내려받기 화면 열기"); go.type = "button";
      go.onclick = async () => {
        if (!u.can_install) { window.open(u.download, "_blank"); 닫기(); return; }
        go.disabled = later.disabled = true;
        try { await call("POST", "/local/update/install", null, {}); }
        catch (e) { msg.textContent = e.message; go.disabled = later.disabled = false; return; }
        const 보기 = async () => {
          let p;
          try { p = await call("GET", "/local/update/progress"); } catch (e) { msg.textContent = "다시 여는 중…"; return; }
          msg.textContent = p.message + (p.state === "downloading" ? ` · ${p.pct}%` : "");
          if (줄) 줄.textContent = msg.textContent;
          if (p.state === "error") { go.disabled = later.disabled = false; return; }
          setTimeout(보기, 700);
        };
        보기();
      };
      foot.append(go);
    }
    sh.append(msg, foot); bg.append(sh);
    bg.onclick = e => { if (e.target === bg && !later.disabled) 닫기(); };
    document.addEventListener("keydown", function esc(e) { if (e.key === "Escape" && !later.disabled) { 닫기(); document.removeEventListener("keydown", esc); } });
    document.body.append(bg);
    (after ? later : sh.querySelector(".b.dark") || later).focus();
  }

  // 업데이트 뒤 처음 열었으면 한 번 보여 준다 (서버가 아니라 이 PC 의 update-seen.json 으로 앎)
  async function 바뀌었나() {
    let c;
    try { c = await call("GET", "/local/update/changes"); } catch (e) { return; }
    if (c.just_updated) 바뀐것(c, true);
  }

  // ── 왼쪽 과제 목록 · 위 줄 과제 이름. 과제를 누르면 /go → 그 과제가 지금 있는 단계 화면 (보던 화면 그대로가 아님) ──
  // 인터넷 서버(/me)는 1~2초 걸린다 → 지난번 목록을 먼저 그리고 본문도 바로 불러오게, 새 목록은 뒤에서 받아 다시 그림 (10/14)
  const 목록_키 = "trace.works.v1";
  function 기억(v) {
    try { if (v === undefined) return JSON.parse(sessionStorage.getItem(목록_키) || "null"); sessionStorage.setItem(목록_키, JSON.stringify(v)); }
    catch (e) { return null; }
  }
  async function fetchWorks() {
    let pc = [];
    try { pc = (await call("GET", "/local/source/works")).works; } catch (e) {}
    let mine = null, user = null;
    try {
      const s = await call("GET", "/local/state");
      if (s.logged_in) { mine = (await call("GET", "/local/works")).works; user = s.user; }
    } catch (e) { mine = null; }
    return { works: mine ? mine : pc.map(w => ({ id: w.id, title: w.id, pc_sessions: w.pc_sessions })), user: mine ? user : null };
  }
  function drawWorks(wid, d) {
    $("me").innerHTML = "";
    if (d.user) {
      const av = el("div", "av", (d.user.name || "?").slice(0, 1));
      const t = el("div"); t.append(el("span", null, d.user.name || ""), el("small", null, d.user.email || ""));
      $("me").append(av, t);
    } else {
      const a = el("a", "nav", null); a.href = "/login"; a.append(el("span", "t", "로그인하면 과제 이름이 보입니다"));
      $("me").append(a);
    }
    // 내 과제는 기록이 없어도 보임 (새 과제를 만들면 바로 왼쪽에 생겨야 함 · 10/13)
    const works = d.works, box = $("works"); box.textContent = "";
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
  }
  async function loadWorks(wid, opt) {
    opt = opt || {};
    const 옛 = 기억();
    const 새로 = fetchWorks().then(d => { 기억(d); drawWorks(wid, d); return d; });
    const d = 옛 && (!wid || 옛.works.some(w => w.id === wid)) ? (drawWorks(wid, 옛), 옛) : await 새로;
    if (!wid && d.works.length && !opt.stay) location.replace("/go?work=" + encodeURIComponent(d.works[0].id));
    return d.works;
  }

  return { call, el, hm, md, icon, svgFile, init, loadWorks };
})();
