// 데스크 크리틱 소개 자료 2장 — 무엇을 만드는가만 말한다
const pptxgen = require("pptxgenjs");

// 제품 화면과 같은 색
const INK="171717", PAPER="FAF9F7", PANEL="F2F0EC", WHITE="FFFFFF";
const MUTED="6F6A63", FAINT="9A948C";
const ORANGE="C0603F", GREEN="2C6E49";
const BAR_NEG="BFBAB2", ZERO="D9D5CF";
const F = "맑은 고딕";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 인치
pres.author = "창의프로젝트1 2인 1팀";
pres.title  = "Trace — 창작 과정 증명 서비스";

const L = 0.75, CW = 11.83;

// 편집 곡선 — 칸마다 늘고 준 양 (data/chain.json 의 실제 스냅샷)
const E1 = [0.0,0.444,-0.417,0.778,0.611,0.5,-0.306,-0.25,0.444,0.889,-0.278,1.0,0.889,0.667,0.583,0.556,-0.194,0.472,0.694,-0.194,-0.194,-0.389,-0.333,0.694,-0.222,-0.361,0.417,-0.444,-0.389,0.583,-0.139,-0.361,0.667,-0.333,-0.278,0.583,-0.278,-0.194,0.333,0.556,0.556,0.639,-0.083];
const Q1 = E1.map(() => false);
const E2 = [0.006,1.0,0.007,-0.003,0.004,0.007,0.006,0.004,0.01,0.008];
const Q2 = [false,true,false,false,false,false,false,false,false,false];

function eyebrow(slide, text) {
  slide.addText("TRACE", { x:L, y:0.4, w:1.6, h:0.3, isTextBox:true, margin:0,
    fontFace:F, fontSize:12, bold:true, color:INK, charSpacing:4 });
  slide.addText(text, { x:L+1.55, y:0.4, w:9.5, h:0.3, isTextBox:true, margin:0,
    fontFace:F, fontSize:11, color:FAINT });
}

// 0선을 기준으로 위아래로 뻗는 막대
function bars(slide, vals, pasted, x, y, w, h, gap) {
  const n = vals.length;
  const bw = (w - gap * (n - 1)) / n;
  const mid = y + h / 2;
  slide.addShape(pres.ShapeType.rect, { x, y: mid - 0.005, w, h: 0.01,
    fill:{ color: ZERO }, line:{ type:"none" } });
  vals.forEach((v, i) => {
    const bh = Math.max(0.02, Math.abs(v) * (h / 2));
    slide.addShape(pres.ShapeType.rect, {
      x: x + i * (bw + gap), y: v >= 0 ? mid - bh : mid, w: bw, h: bh,
      fill:{ color: pasted[i] ? ORANGE : (v >= 0 ? INK : BAR_NEG) },
      line:{ type:"none" },
    });
  });
}

/* ═══════════════════════════════════════════
   1장 — 무엇을 만드는가
   ═══════════════════════════════════════════ */
const s1 = pres.addSlide();
s1.background = { color: PAPER };
eyebrow(s1, "창작 과정 증명 서비스 · 창의프로젝트1 · 2인 1팀");

s1.addText("결과물만 보고는 구분할 수 없다.\n과정의 기록은 그렇지 않다.", {
  x:L, y:1.25, w:CW, h:1.75, isTextBox:true, margin:0,
  fontFace:F, fontSize:40, bold:true, color:INK, lineSpacing:52 });

s1.addText("창작 과정을 30초마다 기록하고, 그 기록이 사후에 고쳐지지 않았음을 제3자가 확인하게 한다.", {
  x:L, y:3.15, w:CW, h:0.36, isTextBox:true, margin:0,
  fontFace:F, fontSize:15, color:MUTED });

// 데이터 흐름 다섯 칸
const steps = [["01","작성 · 웹 에디터"],["02","30초마다 스냅샷"],["03","SHA-256 해시 체인"],
               ["04","chain.json 저장"],["05","검증 화면"]];
const sw = 2.23, sg = 0.175;
steps.forEach(([n, label], i) => {
  const x = L + i * (sw + sg);
  s1.addShape(pres.ShapeType.roundRect, { x, y:3.95, w:sw, h:0.85,
    fill:{ color: PANEL }, line:{ type:"none" }, rectRadius:0.06 });
  s1.addText(n, { x:x+0.18, y:4.05, w:0.5, h:0.24, isTextBox:true, margin:0,
    fontFace:F, fontSize:10, color:FAINT, charSpacing:1 });
  s1.addText(label, { x:x+0.18, y:4.32, w:sw-0.34, h:0.34, isTextBox:true, margin:0,
    fontFace:F, fontSize:12.5, bold:true, color:INK });
});

// 증명한다 / 증명하지 않는다
const bw2 = (CW - 0.35) / 2;
[[L, GREEN, "증명한다", "기록이 작성된 뒤 고쳐지지 않았다는 사실"],
 [L+bw2+0.35, ORANGE, "증명하지 않는다", "본인이 직접 했는지, 무엇이 AI인지"]
].forEach(([x, dot, head, body]) => {
  s1.addShape(pres.ShapeType.roundRect, { x, y:5.35, w:bw2, h:1.45,
    fill:{ color: PANEL }, line:{ type:"none" }, rectRadius:0.05 });
  s1.addShape(pres.ShapeType.ellipse, { x:x+0.36, y:5.73, w:0.15, h:0.15,
    fill:{ color: dot }, line:{ type:"none" } });
  s1.addText(head, { x:x+0.62, y:5.62, w:bw2-0.9, h:0.36, isTextBox:true, margin:0,
    fontFace:F, fontSize:17, bold:true, color:INK });
  s1.addText(body, { x:x+0.36, y:6.12, w:bw2-0.7, h:0.34, isTextBox:true, margin:0,
    fontFace:F, fontSize:13.5, color:MUTED });
});

s1.addNotes(
`[1장 · 약 1분]

저희는 창작 과정을 증명하는 서비스를 만듭니다. 이름은 Trace입니다.

결과물만 보고는 사람이 만들었는지 알 수 없게 됐습니다. 그런데 과정은 다릅니다. 한 시간짜리 작업의 기록은 한 시간을 써야 생깁니다.

동작은 간단합니다. 글을 쓰면 30초마다 내용의 해시를 계산해서 서버로 보냅니다. 내용 자체는 보내지 않습니다. 서버는 이전 해시를 재료에 넣어 새 해시를 만들고 사슬처럼 엮습니다. 이전 해시를 넣기 때문에 중간을 고치면 검증이 틀어집니다.

아래 두 칸이 저희 입장입니다. 저희가 보증하는 건 하나뿐입니다. 기록이 작성된 뒤에 고쳐지지 않았다는 사실.

AI인지 아닌지는 판정하지 않습니다. 탐지기는 오탐으로 이미 신뢰를 잃었고, 판단의 책임을 기계가 지는 순간 같은 길을 가게 됩니다.`);

/* ═══════════════════════════════════════════
   2장 — 그래서 무엇이 보이는가
   ═══════════════════════════════════════════ */
const s2 = pres.addSlide();
s2.background = { color: PAPER };
eyebrow(s2, "같은 글 1,100자를 만드는 두 가지 방법");

s2.addText("분량은 같다. 시간은 열두 배 차이가 난다.", {
  x:L, y:1.25, w:CW, h:0.85, isTextBox:true, margin:0,
  fontFace:F, fontSize:36, bold:true, color:INK });

s2.addText("막대 한 칸이 30초. 위로 뻗으면 쓴 것, 아래로 뻗으면 지운 것.", {
  x:L, y:2.2, w:CW, h:0.34, isTextBox:true, margin:0,
  fontFace:F, fontSize:14, color:MUTED });

const cw = (CW - 0.4) / 2, cy = 2.82, ch = 3.05;
[[L, "처음부터 쓴 글", "1시간 1분 · 붙여넣기 0% · 되돌리기 71회",
  "43칸 중 20칸에서 글이 줄었다 — 썼다 지우고 다시 쓴 흔적", E1, Q1, 0.022],
 [L+cw+0.4, "붙여넣기가 많은 글", "5분 · 붙여넣기 95% · 되돌리기 0회",
  "주황 막대 하나가 밖에서 들어온 1,180자", E2, Q2, 0.075]
].forEach(([cx, title, stat, axis, vals, pst, gap]) => {
  s2.addShape(pres.ShapeType.roundRect, { x:cx, y:cy, w:cw, h:ch,
    fill:{ color: PANEL }, line:{ type:"none" }, rectRadius:0.06 });
  s2.addText(title, { x:cx+0.34, y:cy+0.26, w:cw-0.68, h:0.36, isTextBox:true, margin:0,
    fontFace:F, fontSize:17, bold:true, color:INK });
  s2.addText(stat, { x:cx+0.34, y:cy+0.68, w:cw-0.68, h:0.3, isTextBox:true, margin:0,
    fontFace:F, fontSize:12, color:MUTED });
  bars(s2, vals, pst, cx+0.34, cy+1.18, cw-0.68, 1.35, gap);
  s2.addText(axis, { x:cx+0.34, y:cy+2.63, w:cw-0.68, h:0.28, isTextBox:true, margin:0,
    fontFace:F, fontSize:11, color:FAINT });
});

s2.addText([
  { text:"어느 쪽이 AI인지 우리는 말하지 않는다.", options:{ color:INK, bold:true } },
  { text:"  판단할 재료만 드린다.", options:{ color:MUTED } },
], { x:L, y:6.35, w:CW, h:0.4, isTextBox:true, margin:0, fontFace:F, fontSize:17 });

s2.addNotes(
`[2장 · 약 1분]

막대 한 칸이 30초입니다. 위로 뻗으면 그 30초 동안 쓴 것, 아래로 뻗으면 지운 것입니다.

왼쪽은 한 시간 동안 직접 쓴 기록입니다. 위아래로 톱니처럼 오갑니다. 43칸 가운데 20칸에서 글이 줄었습니다. 썼다가 지우고 다시 쓴 흔적입니다.

오른쪽은 5분 만에 끝난 기록입니다. 주황색 막대 하나가 1,180자를 한 번에 붙여넣은 겁니다. 그 뒤로는 거의 움직이지 않습니다.

분량은 둘 다 1,100자 정도로 비슷합니다. 시간은 열두 배 차이가 납니다.

여기서 저희는 어느 쪽이 AI인지 말하지 않습니다. 그건 보시는 분이 판단하실 일입니다. 저희는 판단할 재료만 드립니다.

이상입니다.`);

pres.writeFile({ fileName: "Trace_데스크크리틱.pptx" })
  .then(f => console.log("만들었습니다 ->", f));
