// =============================================
// Trace - 프런트엔드
//   화면은 "받은 것을 그리기만" 한다.
//   지표 계산은 전부 서버(app.py 의 summarize)가 한다.
// =============================================

const SNAPSHOT_INTERVAL = 30;   // 초

const $ = (id) => document.getElementById(id);

let sessionId = null;
let timer     = null;
let lastText  = "";

// events : 지난 스냅샷 이후의 변화량. 서버로 보내고 나면 0으로 되돌린다.
// totals : 세션을 시작한 뒤의 누적. 화면에 보여주는 값이라 초기화하지 않는다.
//          (둘을 같이 쓰면 30초마다 화면 숫자가 0으로 돌아가 버린다)
let events    = blankEvents();
let totals    = blankEvents();

function blankEvents() {
  return { typed: 0, deleted: 0, pasted: 0, undo: 0 };
}

// ---------------------------------------------
// 표시용 도우미
// ---------------------------------------------
function dur(sec) {
  if (sec < 60) return Math.round(sec) + "초";
  const m = Math.round(sec / 60);
  if (m < 60) return m + "분";
  return Math.floor(m / 60) + "시간 " + (m % 60) + "분";
}

function clock(iso) {
  const d = new Date(iso);
  const p = (n) => String(n).padStart(2, "0");
  return p(d.getHours()) + ":" + p(d.getMinutes());
}

function day(iso) {
  const d = new Date(iso);
  return (d.getMonth() + 1) + "/" + d.getDate();
}

// ---------------------------------------------
// 판정 - 결론을 맨 위에
// ---------------------------------------------
function renderVerdict(o) {
  const box = $("verdict");

  if (o.session_count === 0) {
    box.className = "verdict none";
    box.innerHTML = "<h2>기록이 없습니다</h2>" +
      "<p>아래 작성 영역에서 기록을 시작할 수 있습니다.</p>";
    return;
  }

  if (o.valid) {
    box.className = "verdict ok";
    box.innerHTML = "<h2>이 기록은 변조되지 않았습니다</h2>" +
      "<p>" + o.session_count + "개 세션의 모든 스냅샷이 해시 체인과 일치합니다.</p>";
  } else {
    box.className = "verdict bad";
    box.innerHTML = "<h2>기록이 사후에 수정되었습니다</h2>" +
      "<p>아래에 어느 지점에서 체인이 끊겼는지 표시했습니다.</p>";
  }
}

// ---------------------------------------------
// 한 줄 요약 - 규모 감각
// ---------------------------------------------
function renderOverview(o) {
  if (o.session_count === 0) { $("overview").innerHTML = ""; return; }

  const span = (day(o.first_at) === day(o.last_at))
    ? day(o.first_at)
    : day(o.first_at) + " ~ " + day(o.last_at);

  const cells = [
    ["기간",      span],
    ["세션",      o.session_count + "개"],
    ["작업 시간", dur(o.active_sec)],
    ["공백",      o.gap_count ? o.gap_count + "구간 · " + dur(o.idle_sec) : "없음"],
    ["붙여넣기",  o.paste_ratio + "%"],
    ["되돌리기",  o.undo + "회"],
  ];

  $("overview").innerHTML = '<div class="stats">' + cells.map(
    (c) => '<div class="stat"><span class="k">' + c[0] +
           '</span><span class="v">' + c[1] + '</span></div>'
  ).join("") + '</div>';
}

// ---------------------------------------------
// 세션별 곡선과 근거
// ---------------------------------------------
function renderSessions(sessions) {
  if (sessions.length === 0) { $("sessions").innerHTML = ""; return; }

  $("sessions").innerHTML = sessions.slice().reverse().map(card).join("");

  document.querySelectorAll(".chain-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const box = btn.nextElementSibling;
      box.hidden = !box.hidden;
      btn.textContent = box.hidden ? "▸ 스냅샷 체인 보기" : "▾ 접기";
    });
  });
}

function card(s) {
  const snaps = s.snapshots;
  const m = s.summary;
  if (!snaps.length) return "";

  const max = Math.max.apply(null, snaps.map((x) => x.chars).concat([1]));
  const gapAt = {};
  m.gaps.forEach((g) => { gapAt[g.at_seq] = g.seconds; });

  // 편집 곡선
  const bars = snaps.map((x) => {
    const h = Math.max(Math.round((x.chars / max) * 100), 2);
    let cls = "";
    if (x.events.pasted > 0) cls = "paste";
    if (x.seq === s.broken_at) cls = "broken";

    // 공백은 숨기지 않고 회색 틈으로 그린다
    const gapMark = (gapAt[x.seq] !== undefined)
      ? '<div class="gap" title="' + dur(gapAt[x.seq]) + ' 공백"></div>'
      : "";

    return gapMark + '<div class="bar-col ' + cls + '" style="height:' + h + '%" ' +
           'title="' + clock(x.time) + " · " + x.chars + '자"></div>';
  }).join("");

  // 근거 테이블
  const rows = snaps.map((x) =>
    '<tr class="' + (x.seq === s.broken_at ? "row-broken" : "") + '">' +
      "<td>" + x.seq + "</td>" +
      "<td>" + clock(x.time) + "</td>" +
      "<td>" + x.chars + "</td>" +
      "<td>" + x.events.typed + "/" + x.events.deleted + "/" +
               x.events.pasted + "/" + x.events.undo + "</td>" +
      '<td class="mono">' + x.hash.slice(0, 10) + "…</td>" +
    "</tr>"
  ).join("");

  const badge = s.valid
    ? '<span class="ok-badge">체인 유효</span>'
    : '<span class="fail-badge">' + s.broken_at + "번에서 끊김</span>";

  const meta = day(snaps[0].time) + " " + clock(snaps[0].time) +
               " · " + dur(m.active_sec) + " 작업 · " + m.final_chars + "자";

  return '<article class="card">' +
    '<div class="card-head">' +
      "<h3>" + s.label + "</h3>" +
      '<div class="head-right"><span class="muted">' + meta + "</span>" + badge + "</div>" +
    "</div>" +

    '<div class="chart">' + bars + "</div>" +
    '<div class="axis">' +
      "<span>" + clock(snaps[0].time) + "</span>" +
      '<span class="legend">' +
        '<i class="sw type"></i>입력' +
        '<i class="sw pastesw"></i>붙여넣기' +
        '<i class="sw gapsw"></i>공백' +
      "</span>" +
      "<span>" + clock(snaps[snaps.length - 1].time) + "</span>" +
    "</div>" +

    '<button class="chain-toggle">▸ 스냅샷 체인 보기</button>' +
    "<div hidden>" +
      '<table class="chain"><thead><tr>' +
        "<th>#</th><th>시각</th><th>글자</th>" +
        "<th>입력/삭제/붙여넣기/되돌리기</th><th>해시</th>" +
      "</tr></thead><tbody>" + rows + "</tbody></table>" +
    "</div>" +
  "</article>";
}

// ---------------------------------------------
// 서버에서 받아오기
// ---------------------------------------------
async function verify() {
  try {
    const res = await fetch("/api/verify");
    if (!res.ok) throw new Error("서버 응답 " + res.status);

    const data = await res.json();

    renderVerdict(data.overall);
    renderOverview(data.overall);
    renderSessions(data.sessions);

  } catch (e) {
    $("verdict").className = "verdict bad";
    $("verdict").innerHTML =
      "<h2>기록을 불러오지 못했습니다</h2><p>" + e.message + "</p>";
  }
}

// ---------------------------------------------
// 작성 영역 (작가용)
// ---------------------------------------------
$("toggleWriter").addEventListener("click", () => {
  const body = $("writerBody");
  body.hidden = !body.hidden;
  $("toggleWriter").textContent = body.hidden ? "▸ 작성 영역 열기" : "▾ 작성 영역 닫기";
});

const editor = $("editor");

// 붙여넣기는 input 보다 먼저 일어난다. 여기서 글자 수를 따로 잡는다.
editor.addEventListener("paste", (e) => {
  const t = (e.clipboardData || window.clipboardData).getData("text");
  events.pasted += t.length;
  totals.pasted += t.length;
  updateCounters();
});

editor.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
    events.undo += 1;
    totals.undo += 1;
    updateCounters();
  }
});

editor.addEventListener("input", (e) => {
  const now = editor.value;
  const diff = now.length - lastText.length;

  if (diff > 0) {
    // 붙여넣기로 늘어난 분량은 위에서 이미 셌다
    if (e.inputType !== "insertFromPaste") {
      events.typed += diff;
      totals.typed += diff;
    }
  } else if (diff < 0) {
    events.deleted += -diff;
    totals.deleted += -diff;
  }

  lastText = now;
  updateCounters();
});

function updateCounters() {
  $("counters").textContent =
    "입력 " + totals.typed + " · 삭제 " + totals.deleted +
    " · 붙여넣기 " + totals.pasted + " · 되돌리기 " + totals.undo;
}

$("startBtn").addEventListener("click", () => {
  sessionId = "s" + Date.now();

  editor.disabled = false;
  editor.value = "";
  lastText = "";
  events = blankEvents();
  totals = blankEvents();

  $("startBtn").disabled = true;
  $("saveBtn").disabled = false;
  $("stopBtn").disabled = false;

  editor.focus();
  updateCounters();

  timer = setInterval(sendSnapshot, SNAPSHOT_INTERVAL * 1000);
  setStatus("기록 중 — " + SNAPSHOT_INTERVAL + "초마다 자동 저장");
});

$("stopBtn").addEventListener("click", async () => {
  clearInterval(timer);
  timer = null;

  if (editor.value.trim() !== "") await sendSnapshot();

  editor.disabled = true;
  $("startBtn").disabled = false;
  $("saveBtn").disabled = true;
  $("stopBtn").disabled = true;
  sessionId = null;

  setStatus("기록 종료");
  verify();
});

$("saveBtn").addEventListener("click", sendSnapshot);

async function sendSnapshot() {
  if (!sessionId) return;

  try {
    const res = await fetch("/api/snapshot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        label: "직접 작성",
        content: editor.value,
        events: events,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      setStatus("저장 실패 — " + data.error, true);
      return;
    }

    events = blankEvents();   // totals 는 그대로 둔다
    updateCounters();
    setStatus("스냅샷 " + data.seq + "번 저장 · " + data.hash.slice(0, 12) + "…");
    verify();

  } catch (e) {
    // 서버가 꺼져 있으면 여기로 온다
    setStatus("서버에 닿지 못했습니다 — " + e.message, true);
  }
}

function setStatus(msg, isError) {
  $("statusText").textContent = msg;
  $("statusText").className = isError ? "fail" : "muted";
}

$("verifyBtn").addEventListener("click", verify);

verify();
