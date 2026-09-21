// =============================================
// Trace - 프런트엔드
//   화면은 "받은 것을 그리기만" 한다.
//   지표 계산은 전부 서버(app.py 의 summarize)가 한다.
//
//   데이터 구조 :  작품 > 파일 > 세션 > 스냅샷
// =============================================

const SNAPSHOT_INTERVAL = 30;   // 초

const $ = (id) => document.getElementById(id);

let workId    = null;
let sessionId = null;
let timer     = null;
let lastText  = "";

// events : 지난 스냅샷 이후의 변화량. 서버로 보내고 나면 0으로 되돌린다.
// totals : 세션을 시작한 뒤의 누적. 화면에 보여주는 값이라 초기화하지 않는다.
//          (둘을 같이 쓰면 30초마다 화면 숫자가 0으로 돌아가 버린다)
let events = blankEvents();
let totals = blankEvents();

function blankEvents() {
  return { typed: 0, deleted: 0, pasted: 0, undo: 0 };
}

// ---------------------------------------------
// 보기 좋게 다듬는 함수들
// ---------------------------------------------
function dur(sec) {
  if (!sec) return "0분";
  const h = Math.floor(sec / 3600);
  const m = Math.round((sec % 3600) / 60);
  if (h && m) return h + "시간 " + m + "분";
  if (h) return h + "시간";
  return m + "분";
}

function day(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return (d.getMonth() + 1) + "/" + d.getDate();
}

function clock(iso) {
  return iso ? iso.slice(11, 16) : "-";
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ---------------------------------------------
// ① 판정
// ---------------------------------------------
function renderVerdict(o) {
  const box = $("verdict");

  if (o.work_count === 0) {
    box.className = "verdict none";
    box.innerHTML = "<h2>아직 기록이 없습니다</h2>" +
      "<p>작성 영역을 열고 기록을 시작해 보세요.</p>";
    return;
  }

  if (o.valid) {
    box.className = "verdict ok";
    box.innerHTML = "<h2>이 기록은 변조되지 않았습니다</h2>" +
      "<p>작품 " + o.work_count + "개 · 파일 " + o.file_count +
      "개의 모든 스냅샷이 해시 체인과 일치합니다.</p>";
  } else {
    box.className = "verdict bad";
    box.innerHTML = "<h2>기록이 사후에 수정되었습니다</h2>" +
      "<p>아래에 어느 지점에서 체인이 끊겼는지 표시했습니다.</p>";
  }
}

// ---------------------------------------------
// ② 한 줄 요약 - 규모 감각
// ---------------------------------------------
function renderOverview(o) {
  if (o.work_count === 0) { $("overview").innerHTML = ""; return; }

  const span = (day(o.first_at) === day(o.last_at))
    ? day(o.first_at)
    : day(o.first_at) + " ~ " + day(o.last_at);

  const cells = [
    ["기간",      span],
    ["작품",      o.work_count + "개"],
    ["파일",      o.file_count + "개"],
    ["작업 시간", dur(o.active_sec)],
    ["붙여넣기",  o.paste_ratio + "%"],
    ["공백",      o.gap_count ? o.gap_count + "구간" : "없음"],
  ];

  $("overview").innerHTML = '<div class="stats">' + cells.map(
    (c) => '<div class="stat"><span class="k">' + c[0] +
           '</span><span class="v">' + c[1] + "</span></div>"
  ).join("") + "</div>";
}

// ---------------------------------------------
// ③ 작품 카드
// ---------------------------------------------
function fileRows(work) {
  if (!work.files_summary.length) return "";

  // 가장 오래 작업한 파일을 100% 로 잡고 나머지를 비율로 그린다
  const max = Math.max(...work.files_summary.map((f) => f.active_sec), 1);

  return '<div class="files">' + work.files_summary.map((f) => {
    const pct = Math.max(2, Math.round(f.active_sec / max * 100));

    // 막대는 "이 파일에 쓴 시간"이다. 외부에서 들어온 것이 있으면
    // 막대를 물들이는 대신 이름 옆에 점 하나로 표시한다.
    // (막대 전체를 주황으로 칠하면 "이 파일이 전부 외부에서 왔다"로 읽힌다)
    const mark = f.pasted > 0
      ? '<i class="sw pastesw" title="밖에서 들어온 것 ' + f.pasted + '"></i>'
      : "";

    return '<div class="file-row">' +
      '<span class="file-name" title="' + esc(f.name) + '">' + mark + esc(f.name) + "</span>" +
      '<span class="file-track"><span class="file-fill" style="width:' + pct + '%"></span></span>' +
      '<span class="file-time">' + dur(f.active_sec) + "</span>" +
      "</div>";
  }).join("") + "</div>";
}

function sessionBlock(s) {
  const m = s.summary;
  if (!s.snapshots.length) return "";

  const max = Math.max(...s.snapshots.map((x) => x.chars), 1);

  // 공백이 시작되는 스냅샷 번호를 미리 모아 둔다
  const gapAt = {};
  m.gaps.forEach((g) => { gapAt[g.at_seq] = g.seconds; });

  const bars = s.snapshots.map((x) => {
    let cls = "bar-col";
    if (x.events.pasted > 0) cls = "bar-col paste";
    if (x.seq === s.broken_at) cls = "bar-col broken";

    const h = Math.max(2, Math.round(x.chars / max * 100));
    const gapMark = (gapAt[x.seq] !== undefined)
      ? '<div class="gap" title="' + dur(gapAt[x.seq]) + ' 공백"></div>'
      : "";

    return gapMark + '<div class="' + cls + '" style="height:' + h + '%" ' +
           'title="' + x.seq + "번 · " + x.chars + '"></div>';
  }).join("");

  const rows = s.snapshots.map((x) =>
    '<tr class="' + (x.seq === s.broken_at ? "row-broken" : "") + '">' +
      "<td>" + x.seq + "</td>" +
      '<td class="mono">' + clock(x.time) + "</td>" +
      "<td>" + x.chars + "</td>" +
      "<td>" + x.events.typed + "/" + x.events.deleted + "/" +
               x.events.pasted + "/" + x.events.undo + "</td>" +
      '<td class="mono">' + x.content_hash.slice(0, 12) + "</td>" +
      '<td class="mono">' + x.hash.slice(0, 12) + "</td>" +
    "</tr>"
  ).join("");

  const badge = s.valid
    ? '<span class="ok-badge">체인 일치</span>'
    : '<span class="fail-badge">' + s.broken_at + "번에서 끊김</span>";

  return '<div class="session">' +
    '<div class="session-head">' +
      "<h3>" + esc(s.file_name || "이름을 뺀 파일") + " · " + esc(s.label) + "</h3>" +
      '<div class="head-right">' +
        '<span class="muted" style="font-size:12.5px">' +
          day(s.snapshots[0].time) + " " + clock(s.snapshots[0].time) +
          " · " + dur(m.active_sec) + " 작업 · 스냅샷 " + m.snapshot_count + "개" +
        "</span>" + badge +
      "</div>" +
    "</div>" +
    '<div class="chart">' + bars + "</div>" +
    '<div class="axis">' +
      "<span>" + clock(s.snapshots[0].time) + "</span>" +
      '<span class="legend">' +
        '<span><i class="sw type"></i>입력</span>' +
        '<span><i class="sw pastesw"></i>붙여넣기</span>' +
        '<span><i class="sw gapsw"></i>공백</span>' +
      "</span>" +
      "<span>" + clock(s.snapshots[s.snapshots.length - 1].time) + "</span>" +
    "</div>" +
    '<button class="chain-toggle">▸ 스냅샷 체인 보기</button>' +
    '<div hidden><table class="chain">' +
      "<thead><tr><th>#</th><th>시각</th><th>양</th>" +
      "<th>입력/삭제/붙여넣기/되돌리기</th><th>내용 해시</th><th>체인 해시</th></tr></thead>" +
      "<tbody>" + rows + "</tbody>" +
    "</table></div>" +
  "</div>";
}

function workCard(w) {
  const m = w.summary;

  const badge = w.valid
    ? '<span class="ok-badge">체인 일치</span>'
    : '<span class="fail-badge">체인 끊김</span>';

  const excluded = m.excluded_count
    ? '<div class="excluded-note">작성자가 이 작품에서 파일 ' + m.excluded_count +
      "개를 뺐습니다. 뺀 파일의 이름과 내용은 공개되지 않습니다." +
      " (" + w.excluded.map((e) => day(e.at) + " " + clock(e.at)).join(", ") + ")</div>"
    : "";

  const root = w.root_hash
    ? '<div class="root"><b>작품 루트 해시</b> ' + w.root_hash +
      "<br>세션 " + m.session_count + "개의 마지막 해시를 이어 붙여 한 번 더 해싱한 값입니다. " +
      "증명서에 찍히고 외부 앵커에 고정되는 값이 이것입니다.</div>"
    : "";

  // 뺀 세션은 아래 목록에서도 빼고 보여준다
  const live = w.sessions.filter((s) => !s.excluded);

  return '<article class="work">' +
    '<div class="work-head">' +
      "<h2>" + esc(w.title) + "</h2>" +
      '<div class="head-right">' +
        '<span class="work-meta">' +
          day(m.first_at) + " ~ " + day(m.last_at) +
          " · " + dur(m.active_sec) +
          " · 파일 " + m.file_count + "개" +
          " · 세션 " + m.session_count + "개" +
        "</span>" + badge +
      "</div>" +
    "</div>" +
    fileRows(w) +
    excluded +
    root +
    live.map(sessionBlock).join("") +
  "</article>";
}

function renderWorks(works) {
  if (!works.length) { $("works").innerHTML = ""; return; }

  $("works").innerHTML = works.slice().reverse().map(workCard).join("");

  document.querySelectorAll(".chain-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const box = btn.nextElementSibling;
      box.hidden = !box.hidden;
      btn.textContent = box.hidden ? "▸ 스냅샷 체인 보기" : "▾ 스냅샷 체인 접기";
    });
  });
}

// ---------------------------------------------
// 검증 - 서버에 물어보고 화면을 다시 그린다
// ---------------------------------------------
async function verify() {
  try {
    const res = await fetch("/api/verify");
    const data = await res.json();

    renderVerdict(data.overall);
    renderOverview(data.overall);
    renderWorks(data.works);
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

// 같은 작품 이름이면 같은 work_id 를 쓰도록, 제목에서 id 를 만든다.
// (실제 제품이라면 작품 목록에서 고르게 한다 — 여기서는 프로토타입이라 이름으로 잇는다)
function workIdFromTitle(title) {
  let h = 0;
  for (let i = 0; i < title.length; i++) {
    h = (h * 31 + title.charCodeAt(i)) % 1000000007;
  }
  return "w" + h;
}

async function sendSnapshot() {
  if (!sessionId) return;

  try {
    const res = await fetch("/api/snapshot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        work_id: workId,
        work_title: $("workTitle").value.trim(),
        file_name: $("fileName").value.trim() || "이름 없는 파일",
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

$("startBtn").addEventListener("click", () => {
  const title = $("workTitle").value.trim();
  if (!title) { setStatus("작품 이름을 적어 주세요", true); return; }

  workId = workIdFromTitle(title);
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
  setStatus("기록 중 — " + SNAPSHOT_INTERVAL + "초마다 저장합니다");

  timer = setInterval(sendSnapshot, SNAPSHOT_INTERVAL * 1000);
});

$("saveBtn").addEventListener("click", sendSnapshot);

$("stopBtn").addEventListener("click", async () => {
  await sendSnapshot();

  clearInterval(timer);
  timer = null;
  sessionId = null;

  editor.disabled = true;
  $("startBtn").disabled = false;
  $("saveBtn").disabled = true;
  $("stopBtn").disabled = true;

  setStatus("기록을 끝냈습니다");
  verify();
});

// 화면을 열면 바로 한 번 검증한다
verify();
