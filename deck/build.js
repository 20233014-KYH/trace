// 데스크 크리틱 발표 자료 2장
const pptxgen = require("pptxgenjs");

// ── 제품 화면과 같은 색을 쓴다 ─────────────────────────
const INK="171717", PAPER="FAF9F7", WHITE="FFFFFF", PANEL="F2F0EC";
const BAR_NEG="BFBAB2", ZERO="D9D5CF";   // 증감 막대의 아래쪽과 0선
const MUTED_D="9A948C", MUTED_L="6F6A63", FAINT_L="9A948C";
const BAR="E8E4DE";
const ORANGE="C0603F", GREEN="2C6E49", GREEN_D="7FC49A";
const F = "맑은 고딕";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 인치
pres.author = "창의프로젝트1 2인 1팀";
pres.title  = "Trace — 데스크 크리틱";

const L = 0.7, CW = 11.93;              // 왼쪽 여백 · 본문 폭

// 편집 곡선 — 칸마다 늘고 준 양 (data/chain.json 의 실제 스냅샷)
// 위로 뻗으면 쓴 것, 아래로 뻗으면 지운 것. 30초에 한 칸.
const E1 = [0.0,0.444,-0.417,0.778,0.611,0.5,-0.306,-0.25,0.444,0.889,-0.278,1.0,0.889,0.667,0.583,0.556,-0.194,0.472,0.694,-0.194,-0.194,-0.389,-0.333,0.694,-0.222,-0.361,0.417,-0.444,-0.389,0.583,-0.139,-0.361,0.667,-0.333,-0.278,0.583,-0.278,-0.194,0.333,0.556,0.556,0.639,-0.083];
const Q1 = E1.map(() => false);
const E2 = [0.006,1.0,0.007,-0.003,0.004,0.007,0.006,0.004,0.01,0.008];
const Q2 = [false,true,false,false,false,false,false,false,false,false];

// 막대를 직접 그린다 (차트 기능보다 색을 칸마다 정확히 줄 수 있다)
function bars(slide, vals, pasted, x, y, w, h, gap, color) {
  const n = vals.length;
  const bw = (w - gap * (n - 1)) / n;
  const mid = y + h / 2;                     // 0 선. 위는 쓴 양, 아래는 지운 양
  slide.addShape(pres.ShapeType.rect, {
    x, y: mid - 0.005, w, h: 0.01,
    fill: { color: ZERO }, line: { type: "none" },
  });
  vals.forEach((v, i) => {
    const bh = Math.max(0.02, Math.abs(v) * (h / 2));
    slide.addShape(pres.ShapeType.rect, {
      x: x + i * (bw + gap), y: v >= 0 ? mid - bh : mid, w: bw, h: bh,
      fill: { color: pasted[i] ? ORANGE : (v >= 0 ? color : BAR_NEG) },
      line: { type: "none" },
    });
  });
}

/* ══════════════════════════════════════════════════
   1장 — 무엇을 만들었나
   ══════════════════════════════════════════════════ */
const s1 = pres.addSlide();
s1.background = { color: PAPER };

s1.addText("TRACE", { x:L, y:0.38, w:1.6, h:0.3, isTextBox:true, margin:0,
  fontFace:F, fontSize:12, bold:true, color:INK, charSpacing:4 });
s1.addText("창작 과정 증명 서비스 · 창의프로젝트1 · 2인 1팀 · 2026.09.15", {
  x:2.25, y:0.38, w:8, h:0.3, isTextBox:true, margin:0,
  fontFace:F, fontSize:11, color:FAINT_L });

s1.addText("결과물만 보고는 구분할 수 없다.\n과정의 기록은 그렇지 않다.", {
  x:L, y:0.9, w:CW, h:1.45, isTextBox:true, margin:0,
  fontFace:F, fontSize:34, bold:true, color:INK, lineSpacing:44 });

s1.addText("기록이 작성된 뒤 고쳐지지 않았다는 사실만 보증한다. AI 사용 여부는 판정하지 않는다.", {
  x:L, y:2.42, w:9.6, h:0.32, isTextBox:true, margin:0,
  fontFace:F, fontSize:13, color:MUTED_L });

// 데이터 흐름 5단계
const steps = [["01","작성 · 웹 에디터"],["02","30초마다 스냅샷"],["03","SHA-256 해시 체인"],
               ["04","chain.json 저장"],["05","검증 화면"]];
const sw = 2.24, sg = 0.18;
steps.forEach(([n, label], i) => {
  const x = L + i * (sw + sg);
  s1.addShape(pres.ShapeType.roundRect, { x, y:3.0, w:sw, h:0.78,
    fill:{ color: PANEL }, line:{ type:"none" }, rectRadius:0.06 });
  s1.addText(n, { x:x+0.16, y:3.09, w:0.5, h:0.22, isTextBox:true, margin:0,
    fontFace:F, fontSize:9.5, color:FAINT_L, charSpacing:1 });
  s1.addText(label, { x:x+0.16, y:3.33, w:sw-0.3, h:0.32, isTextBox:true, margin:0,
    fontFace:F, fontSize:12, bold:true, color:INK });
});

// 두 장의 편집 곡선
const cw = 5.765, cy = 4.1, ch = 2.28;
[[L, "데모 1 — 처음부터 쓴 글", "1시간 1분 · 붙여넣기 0% · 되돌리기 71회",
  "43칸 중 20칸에서 글이 줄었다 · 한 칸 최대 ±36자", E1, Q1, 0.02],
 [L+cw+0.4, "데모 2 — 붙여넣기가 많은 글", "5분 · 붙여넣기 95% · 되돌리기 0회",
  "10칸 중 1칸, 그것도 붙여넣기 한 번 · 한 칸 최대 +1,180자", E2, Q2, 0.07]
].forEach(([cx, title, stat, axis, vals, pst, gap]) => {
  s1.addShape(pres.ShapeType.roundRect, { x:cx, y:cy, w:cw, h:ch,
    fill:{ color: PANEL }, line:{ type:"none" }, rectRadius:0.06 });
  s1.addText(title, { x:cx+0.28, y:cy+0.16, w:cw-0.56, h:0.3, isTextBox:true, margin:0,
    fontFace:F, fontSize:13.5, bold:true, color:INK });
  s1.addText(stat, { x:cx+0.28, y:cy+0.48, w:cw-0.56, h:0.26, isTextBox:true, margin:0,
    fontFace:F, fontSize:10.5, color:MUTED_L });
  bars(s1, vals, pst, cx+0.28, cy+0.86, cw-0.56, 1.02, gap, INK);
  s1.addText(axis, { x:cx+0.28, y:cy+1.95, w:cw-0.56, h:0.24, isTextBox:true, margin:0,
    fontFace:F, fontSize:9.5, color:"7A756E" });
});

s1.addText([
  { text:"한 칸이 30초다. 위로 뻗으면 쓴 것, 아래로 뻗으면 지운 것. ", options:{ color:MUTED_L } },
  { text:"주황 막대", options:{ color:ORANGE, bold:true } },
  { text:" 하나가 밖에서 들어온 1,180자다. 분량은 둘 다 1,100자 남짓인데 시간은 열두 배 차이다.", options:{ color:MUTED_L } },
], { x:L, y:6.52, w:CW, h:0.28, isTextBox:true, margin:0, fontFace:F, fontSize:11.5 });

s1.addText([
  { text:"증명한다", options:{ color:GREEN, bold:true } },
  { text:"  기록이 작성된 뒤 고쳐지지 않았다는 사실      ", options:{ color:INK } },
  { text:"증명하지 않는다", options:{ color:ORANGE, bold:true } },
  { text:"  본인이 직접 했는지, 무엇이 AI인지, 대리 작업", options:{ color:MUTED_L } },
], { x:L, y:6.88, w:CW, h:0.3, isTextBox:true, margin:0, fontFace:F, fontSize:12 });

s1.addNotes(
`[1장 · 약 2분 30초]

저희 팀은 창작 과정을 증명하는 서비스를 만들고 있습니다. 이름은 Trace입니다.

출발점은 이겁니다. 결과물만 보고는 사람이 만들었는지 알 수 없게 됐습니다. 그런데 과정은 다릅니다. 1시간짜리 작업의 기록은 1시간을 써야 생깁니다.

저희는 AI를 탐지하지 않습니다. 탐지기는 오탐으로 이미 신뢰를 잃었고, 판단의 책임을 기계가 지는 순간 같은 길을 가게 됩니다. 저희가 보증하는 건 딱 하나, 기록이 작성된 뒤에 고쳐지지 않았다는 사실입니다.

가운데 다섯 칸이 이번 주에 구현한 데이터 흐름입니다. 브라우저에서 글을 쓰면 30초마다 내용의 해시를 계산해서 서버로 보냅니다. 내용 자체는 보내지 않습니다. 서버는 이전 해시를 재료에 넣어 새 해시를 만들고 chain.json에 쌓습니다. 이전 해시를 넣기 때문에 중간을 고치면 검증이 틀어집니다. 검증 화면은 저장된 재료로 해시를 다시 계산해서 파일에 적힌 값과 비교합니다.

아래 두 장이 오늘 보여드리고 싶은 장면입니다. 막대 한 칸이 30초입니다. 위로 뻗으면 그 30초 동안 쓴 것, 아래로 뻗으면 지운 것입니다.

왼쪽은 한 시간 동안 직접 쓴 기록입니다. 위아래로 톱니처럼 오갑니다. 43칸 가운데 20칸에서 글이 줄었습니다. 썼다가 지우고 다시 쓴 흔적이고, 되돌리기가 71번 있었습니다.

오른쪽은 5분 만에 끝난 기록입니다. 주황색 막대 하나가 1,180자를 한 번에 붙여넣은 겁니다. 그 뒤로는 거의 움직이지 않습니다. 줄어든 칸은 10칸 중 1칸뿐이고 되돌리기는 0번입니다.

분량은 둘 다 1,100자 정도로 비슷합니다. 시간은 열두 배 차이가 납니다.

여기서 저희는 어느 쪽이 AI인지 말하지 않습니다. 그건 보시는 분이 판단하실 일입니다. 저희는 판단할 재료만 드립니다.`);

/* ══════════════════════════════════════════════════
   2장 — 변한 것 / 막힌 것 / 정할 것
   ══════════════════════════════════════════════════ */
const s2 = pres.addSlide();
s2.background = { color: PAPER };

s2.addText("DESK CRITIC", { x:L, y:0.42, w:2.4, h:0.3, isTextBox:true, margin:0,
  fontFace:F, fontSize:11, bold:true, color:FAINT_L, charSpacing:3 });

s2.addText("변한 것, 막힌 것, 정해야 할 것", {
  x:L, y:0.82, w:CW, h:0.72, isTextBox:true, margin:0,
  fontFace:F, fontSize:32, bold:true, color:INK });

s2.addText("2주차 기준. 오른쪽 세 가지는 저희끼리 정할 수 없어 교수님 의견을 듣고 싶은 것들입니다.", {
  x:L, y:1.62, w:10.5, h:0.3, isTextBox:true, margin:0,
  fontFace:F, fontSize:12.5, color:MUTED_L });

const cardW = 3.77, cardGap = 0.31, cardY = 2.2, cardH = 3.35;
const cards = [
  [GREEN, "변한 것", [
    "주제를 ‘AI 탐지’가 아니라 과정 기록의 무결성으로 다시 잡음",
    "작성 → 스냅샷 → 해시 체인 → 검증까지 데이터가 한 바퀴 흐름. Flask + JSON, 약 1,500줄",
    "chain.json 한 글자를 고치면 검증이 실패 — 오늘 시연합니다",
    "작품 > 파일 > 세션 계층 도입. 증명서는 작품 하나에 한 장",
  ]],
  [ORANGE, "막힌 것", [
    "브라우저 밖 도구(Procreate 등)의 과정은 아직 못 잡음. 상주 수집기는 10주차 이후",
    "글은 방어가 얇음 — 화면을 보고 손으로 옮겨 적으면 붙여넣기로 기록되지 않음",
    "이벤트 카운트만으로 ‘탐색이 있는 과정’이 충분히 드러나는지 아직 미확인",
  ]],
  [INK, "정할 것", [
    "첫 사용자 — 커미션 작가(첫 매출)와 대학 과제(사용자 확보) 중 어디부터",
    "작성자 자기신고를 넣을지 — 판정하지 않으면서 AI 사용 시점을 드러내는 유일한 길",
    "외부 앵커(OpenTimestamps)를 이번 프로토타입 범위에 넣을지",
  ]],
];

cards.forEach(([dot, head, items], i) => {
  const x = L + i * (cardW + cardGap);
  s2.addShape(pres.ShapeType.roundRect, { x, y:cardY, w:cardW, h:cardH,
    fill:{ color: PANEL }, line:{ type:"none" }, rectRadius:0.05 });
  s2.addShape(pres.ShapeType.ellipse, { x:x+0.3, y:cardY+0.34, w:0.14, h:0.14,
    fill:{ color: dot }, line:{ type:"none" } });
  s2.addText(head, { x:x+0.54, y:cardY+0.24, w:cardW-0.8, h:0.34, isTextBox:true, margin:0,
    fontFace:F, fontSize:16, bold:true, color:INK });
  s2.addText(
    items.map((t, j) => ({
      text: t,
      options: { bullet:{ indent:13 }, breakLine: j < items.length-1 },
    })),
    { x:x+0.3, y:cardY+0.76, w:cardW-0.6, h:cardH-1.0, isTextBox:true, margin:0,
      valign:"top",                      // 없으면 글머리가 카드 한가운데로 뜬다
      fontFace:F, fontSize:11.5, color:MUTED_L, lineSpacing:17, paraSpaceAfter:10 });
});

// 하단 — 포지셔닝과 수익 구조
s2.addShape(pres.ShapeType.roundRect, { x:L, y:5.82, w:7.4, h:1.13,
  fill:{ color: INK }, line:{ type:"none" }, rectRadius:0.05 });
s2.addText("“위조 불가”가 아니라 — 위조 비용 = 실제 작업 비용", {
  x:L+0.34, y:5.99, w:6.8, h:0.36, isTextBox:true, margin:0,
  fontFace:F, fontSize:17, bold:true, color:WHITE });
s2.addText("1시간짜리 기록을 위조하려면 1시간을 써야 합니다. 그러면 그 상당 부분은 진짜 작업입니다.", {
  x:L+0.34, y:6.4, w:6.8, h:0.3, isTextBox:true, margin:0,
  fontFace:F, fontSize:11.5, color:MUTED_D });

s2.addText("수익 구조 — 기록은 무료, 증명서를 발급하고 검증받는 순간 받습니다", {
  x:8.45, y:5.88, w:4.18, h:0.3, isTextBox:true, margin:0,
  fontFace:F, fontSize:10.5, color:FAINT_L });
s2.addText([
  { text:"증명서 1건 500원", options:{ color:INK, bold:true } },
  { text:"\n작가 월 4,900원  ·  기관 학생 1인당 연 1,000원", options:{ color:MUTED_L } },
], { x:8.45, y:6.2, w:4.18, h:0.6, isTextBox:true, margin:0, fontFace:F, fontSize:11.5, lineSpacing:16 });

s2.addNotes(
`[2장 · 약 2분]

변한 것부터 말씀드리겠습니다.

가장 크게 바뀐 건 주제를 다시 잡은 겁니다. 처음에는 AI를 탐지하는 쪽으로 갔는데, 그 길은 오탐 책임을 저희가 떠안는 길이었습니다. 그래서 탐지가 아니라 과정 기록의 무결성으로 옮겼습니다.

이번 주에 데이터가 한 바퀴 도는 것까지 만들었습니다. Flask와 JSON 파일로 약 1,500줄입니다. 그리고 chain.json을 한 글자만 고치면 검증이 실패합니다. 잠시 뒤에 직접 고쳐서 빨간 화면이 뜨는 걸 보여드리겠습니다.

구조도 한 층 올렸습니다. 커미션 한 건이 러프, 선화, 채색 세 파일로 나뉘는데 파일마다 증명서가 나오면 의뢰인이 세 장을 받게 됩니다. 그래서 작품이라는 층을 만들고 증명서는 작품 하나에 한 장만 나오게 했습니다.

막힌 건 세 가지입니다.

첫째, 브라우저 밖에서 하는 작업은 아직 못 잡습니다. Procreate 같은 도구요. 상주 수집기를 만들어야 하는데 10주차 이후 일정입니다. 그래서 이번 프로토타입은 웹 에디터로 데이터 흐름만 증명합니다.

둘째, 글은 방어가 얇습니다. 화면에 띄워 놓고 손으로 옮겨 적으면 붙여넣기로 기록되지 않습니다. 이건 저희가 못 막는 부분이라 화면에도 그대로 적어 뒀습니다. 정확한 척하지 않는 게 이 서비스의 태도라고 생각합니다.

셋째, 이벤트 카운트만으로 탐색이 있는 과정이 충분히 드러나는지 아직 확인 못 했습니다. 9주차에 위조 실험으로 검증할 계획입니다.

마지막으로 정해야 할 것 세 가지를 여쭙고 싶습니다.

하나, 첫 사용자를 커미션 작가로 갈지 대학 과제로 갈지입니다. 작가 쪽은 돈을 낼 이유가 분명한데 모수가 작고, 대학 과제는 사용자는 많은데 본인이 돈을 내지 않습니다.

둘, 작성자가 직접 "이 부분은 AI 초안이다"라고 표시하게 할지입니다. 서비스가 판정하지 않으면서도 보는 사람의 질문에 답하는 유일한 길이라고 보는데, 기획안에 없던 기능이라 범위가 늘어납니다.

셋, 외부 앵커를 이번 프로토타입에 넣을지입니다. 넣으면 서버 운영자도 못 고친다는 걸 보여줄 수 있는데, 네트워크 변수 때문에 시연 중에 깨질 위험이 있습니다.

정리하면, 저희 포지션은 위조가 불가능하다는 게 아닙니다. 위조하는 비용이 실제로 작업하는 비용과 같아진다는 겁니다. 1시간짜리 기록을 위조하려면 1시간을 써야 하고, 그러면 그 상당 부분은 이미 진짜 작업입니다.

수익은 기록 자체는 무료로 두고, 증명서를 발급하고 검증받는 순간에 받는 구조로 잡았습니다.

이상입니다. 시연 보여드리겠습니다.`);

pres.writeFile({ fileName: "Trace_데스크크리틱.pptx" })
  .then(f => console.log("만들었습니다 ->", f));
