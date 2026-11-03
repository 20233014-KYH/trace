// 중간발표 전체 (1 ~ 11장 · 자료 출처) — 4 ~ 8장은 박상진 부탁으로 김용현이 만듦 (11/3)
const pptxgen = require("pptxgenjs");
const fs = require("fs"), path = require("path");
const FIGMA_URL = "https://www.figma.com/proto/7vUUX1TAiLuxEVJnePvymH/Trace-%EC%A4%91%EA%B0%84%EC%A0%90%EA%B2%80-%E2%80%94-%ED%99%94%EB%A9%B4-%C2%B7-%ED%94%84%EB%A1%9C%ED%86%A0%ED%83%80%EC%9E%85";   // 피그마 프로토타입 재생 링크 (박상진 11/3 · 보기 권한 공개 · 열면 바로 ▶) · 10장
const FIGMA_LABEL = "figma.com · Trace 중간점검 — 화면 · 프로토타입";   // 화면에 보이는 글 (주소가 길어서) · 누르면 FIGMA_URL
const IMG = (fs.existsSync(path.join(__dirname, "img")) ? path.join(__dirname, "img") : "/Users/yonghyeonkim/dev/trace/deck/img") + "/";
const out = process.argv[2];

const FONT = "Apple SD Gothic Neo";
const INK = "37352F", MUTED = "787774", LINE = "E3E2DE", SOFT = "F7F7F5";
const ACCENT = "1F5E8C", ACCENT_BG = "EAF1F7";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.title = "Trace 중간발표";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "TITLE_ONLY",
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.35, w: 9, h: 0.6,
      fontFace: FONT, fontSize: 26, bold: true, color: INK, valign: "top", align: "left", margin: 0 }, text: "" } },
    // 오른쪽 위: 로고 점 셋 (앱 아이콘과 같은 모티프) + 이름
    { image: { x: 8.3, y: 0.145, w: 0.33, h: 0.11, path: IMG + "dots.png" } },
    { text: { text: "Trace", options: { x: 8.66, y: 0.1, w: 0.45, h: 0.2, fontFace: FONT, fontSize: 9, bold: true, color: "9B9A95", margin: 0, valign: "middle" } } },
    { line: { x: 9.13, y: 0.13, w: 0, h: 0.14, line: { color: "D9D8D3", width: 0.75 } } },
  ],
  slideNumber: { x: 9.23, y: 0.1, w: 0.3, h: 0.2, fontFace: FONT, fontSize: 9, color: "9B9A95", align: "left", margin: 0 },
});

// 제목 위 작은 섹션 표시 — 요구 항목 번호 · 이름 (교수가 어디가 무슨 항목인지 바로 찾게)
const sec = (slide, n, name) => slide.addText([{ text: n, options: { bold: true, color: ACCENT } }, { text: "   " + name, options: { color: "9B9A95" } }],
  { isTextBox: true, fontFace: FONT, x: 0.5, y: 0.1, w: 6, h: 0.2, fontSize: 9, margin: 0, valign: "middle", charSpacing: 0.5 });
const T = (slide, text, o) => slide.addText(text, Object.assign({ isTextBox: true, fontFace: FONT, margin: 0, color: INK }, o));
const card = (slide, x, y, w, h, fill, name) =>
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name });

// ───────── 1장 표지 ─────────
{
  const s = pres.addSlide();
  s.background = { color: INK };
  const COPY = "E5484D", COPY_BG = "FDECEC", EDIT = "3E63DD", EDIT_BG = "EAF0FD", BAR = "E3E2DE";   // 앱 출처 보기 색 (app/shell.css)
  // 로고 (앱 아이콘 = 상진 10/13) + 이름
  s.addImage({ path: IMG + "app-icon.png", x: 0.6, y: 1.5, w: 0.92, h: 0.92 });
  T(s, "Trace", { x: 1.68, y: 1.46, w: 4, h: 0.95, fontSize: 54, bold: true, color: "FFFFFF", valign: "middle", objectName: "cover-title" });
  T(s, "AI 사용 내역 공개,\n손 대신 기록으로", { x: 0.6, y: 2.68, w: 4.7, h: 0.9, fontSize: 24, color: "FFFFFF", valign: "top", paraSpaceAfter: 2 });
  T(s, "창의프로젝트1 · 중간 설계 발표 · 김용현 · 박상진", { x: 0.6, y: 4.65, w: 5.4, h: 0.3, fontSize: 12, color: "C9C8C3" });

  // 그래픽: 왼쪽 출처(AI 답 · 웹 글) → 오른쪽 보고서 문장마다 색 — "문장마다 어디서 왔는지"
  const src = [
    ["ChatGPT", "AI 답", 1.25, COPY],
    ["Claude", "AI 답", 2.35, EDIT],
    ["웹 글", "복사해 붙임", 3.45, "C9C8C3"],
  ];
  // 보고서 카드
  const dx = 7.25, dy = 0.95, dw = 2.2, dh = 3.75;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: dx, y: dy, w: dw, h: dh, rectRadius: 0.08, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" },
    shadow: { type: "outer", color: "000000", opacity: 0.35, blur: 12, offset: 4, angle: 90 } });
  T(s, "보고서.docx", { x: dx + 0.18, y: dy + 0.14, w: 1.6, h: 0.22, fontSize: 9, bold: true, color: INK });
  // 문장 줄: [폭, 색 배경, 밑줄 색] — 색 = 어디서 왔는지
  const lines = [[1.8, null], [1.6, COPY_BG, COPY], [1.75, COPY_BG, COPY], [1.2, null], [1.7, null], [1.55, EDIT_BG, EDIT], [1.8, null], [1.35, null],
                 [1.7, "F4F3EF", "9B9A95"], [1.6, null], [1.1, null]];
  const lineY = {};
  lines.forEach(([w, bg, c], k) => {
    const y = dy + 0.55 + k * 0.28;
    if (bg) s.addShape(pres.shapes.RECTANGLE, { x: dx + 0.14, y: y - 0.06, w: w + 0.08, h: 0.2, fill: { color: bg }, line: { color: bg } });
    s.addShape(pres.shapes.RECTANGLE, { x: dx + 0.18, y: y + 0.01, w, h: 0.06, fill: { color: c || BAR }, line: { color: c || BAR } });
    if (c && !lineY[c]) lineY[c] = y + 0.04;
  });
  // 출처 말풍선 + 잇는 선
  src.forEach(([name, kind, y, c]) => {
    const bx = 5.35, bw = 1.25, bh = 0.62, cy = y + bh / 2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y, w: bw, h: bh, rectRadius: 0.1, fill: { color: "4A4843" }, line: { color: c, width: 1.25 } });
    s.addShape(pres.shapes.OVAL, { x: bx + 0.12, y: cy - 0.07, w: 0.14, h: 0.14, fill: { color: c }, line: { color: c } });
    T(s, [{ text: name, options: { bold: true, color: "FFFFFF", breakLine: true } }, { text: kind, options: { color: "C9C8C3", fontSize: 8.5 } }],
      { x: bx + 0.34, y, w: bw - 0.38, h: bh, fontSize: 10, valign: "middle" });
    const ty = lineY[c === "C9C8C3" ? "9B9A95" : c];
    s.addShape(pres.shapes.LINE, { x: bx + bw, y: cy, w: dx + 0.14 - (bx + bw), h: ty - cy, flipV: ty < cy,
      line: { color: c, width: 1.25, dashType: c === "C9C8C3" ? "dash" : "solid", endArrowType: "oval" } });
  });
  T(s, "문장마다 어디서 왔는지", { x: dx, y: dy + dh + 0.1, w: dw, h: 0.24, fontSize: 9.5, color: "9B9A95", align: "center" });
  s.addNotes("안녕하세요, 1조입니다. 저희는 AI를 허용한 과제에서 사용 내역을 자동으로 기록해 보여 주는 Trace를 기획했습니다. (약 10초)");
}

// ───────── 2장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("문제 정의: 대학은 이미 AI 사용 공개를 요구한다", { placeholder: "title" });
  sec(s, "01", "문제 정의 · 인사이트");

  // 숫자 두 개
  T(s, "56곳", { x: 0.5, y: 1.15, w: 1.9, h: 0.75, fontSize: 44, bold: true, objectName: "stat-56" });
  T(s, [{ text: "AI 가이드라인을 둔 대학", options: { breakLine: true } }, { text: "2년 전 30곳", options: { color: MUTED } }],
    { x: 2.45, y: 1.22, w: 2.3, h: 0.62, fontSize: 14, valign: "middle" });
  T(s, "32곳", { x: 5.0, y: 1.15, w: 1.9, h: 0.75, fontSize: 44, bold: true, color: ACCENT, objectName: "stat-32" });
  T(s, [{ text: "그중 과제에 AI 사용을", options: { breakLine: true } }, { text: "밝히라고 정한 곳" }],
    { x: 6.95, y: 1.22, w: 2.55, h: 0.62, fontSize: 14, valign: "middle" });
  T(s, "대교협 총장 설문 · 2026.2", { x: 0.5, y: 1.95, w: 9, h: 0.25, fontSize: 10, color: MUTED });

  // 카드 세 개
  const cards = [
    ["명지대", "2026.8 규정", "AI 허용 과제마다\n대화 로그 증빙서 필수"],
    ["고려대", "2025.9 수업 가이드라인", "AI 허용 · 출력을 고치지 않고\n그대로 넣기는 금지"],
    ["교육부 · 대교협", "2026.8.24 가이드라인 안내", "'투명성' — AI 사용 사실과\n과정을 공개"],
  ];
  const cw = 2.9, gap = 0.15, cy = 2.4, ch = 1.5;
  cards.forEach(([head, date, body], i) => {
    const x = 0.5 + i * (cw + gap);
    card(s, x, cy, cw, ch, SOFT, "case-" + i);
    T(s, head, { x: x + 0.2, y: cy + 0.18, w: cw - 0.4, h: 0.32, fontSize: 16, bold: true });
    T(s, date, { x: x + 0.2, y: cy + 0.5, w: cw - 0.4, h: 0.22, fontSize: 10, color: MUTED });
    T(s, body, { x: x + 0.2, y: cy + 0.78, w: cw - 0.4, h: 0.6, fontSize: 14, valign: "top" });
  });

  // 확인 방법
  card(s, 0.5, 4.15, 9, 0.85, ACCENT_BG, "how-checked");
  T(s, "확인 방법은?", { x: 0.75, y: 4.15, w: 1.5, h: 0.85, fontSize: 16, bold: true, color: ACCENT, valign: "middle" });
  T(s, [
    { text: "교수가 제출된 과제와 AI 대화 내역을 한 줄씩 대조", options: { breakLine: true } },
    { text: "연세대 AI 집단 부정행위(2025.11)도 교수가 학생 영상을 돌려 보며 적발", options: { color: MUTED, fontSize: 12 } },
  ], { x: 2.3, y: 4.15, w: 7.0, h: 0.85, fontSize: 14, valign: "middle" });

  s.addNotes("대학은 이미 AI 사용 공개를 요구하고 있습니다. 가이드라인을 둔 56곳 중 32곳이 과제에 사용 내역을 밝히라고 하고, 명지대 · 고려대와 교육부 가이드라인도 같은 방향입니다. 그런데 확인은 교수가 제출된 과제와 AI 대화 내역을 하나하나 대조하는 것뿐입니다. (약 20초)");
}

// ───────── 3장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("인사이트: 학생은 기준을 모르고, 감시를 걱정한다", { placeholder: "title" });
  sec(s, "01", "문제 정의 · 인사이트");

  // 질문 4개 = 칸 4개 · 칸마다 Q(실제 설문 문항) · A(고른 답) → 결론 하나 (11/3 김용현 안: 1 · 23 · 4 → 1 · 2 · 3 · 4)
  const gap = 0.12, cw = (9 - gap * 3) / 4, cy = 1.15, ch = 3.55, dh = 0.8;
  const cols = [
    ["59%", "AI 사용을 밝힐 때\n어려운 점은?", "\"어디까지 밝혀야\n할지 모르겠다\"", "1위 · 여러 개 고름", "기준이 없다", "내역서가 기준 양식"],
    ["59%", "이런 도구,\n언제 켜겠나요?", "\"받는 쪽이\n요구하면\"", "1위 · 여러 개 고름", "요구받으면 켠다", "교수가 요구하고\n    학생이 쓴다"],
    ["44%", "켜기 꺼려지는\n이유는?", "\"감시받는 느낌\"", "1위 · 여러 개 고름", "감시가 걱정이다", "원문은 학생 PC에만"],
    ["94%", "AI 초안을\n그대로 내는 건?", "\"그냥 내면\n안 된다\"", "밝히면 된다 50%\n쓰면 안 된다 44%", "그냥 내면 안 된다", "표시하고 고칠 기회"],
  ];
  cols.forEach(([num, q, a, sub, find, act], i) => {
    const x = 0.5 + i * (cw + gap), ix = x + 0.18, iw = cw - 0.32;
    card(s, x, cy, cw, ch, SOFT, "insight-" + i);
    T(s, num, { x: ix, y: cy + 0.15, w: iw, h: 0.6, fontSize: 34, bold: true, color: ACCENT });
    T(s, [{ text: "Q. ", options: { bold: true, color: ACCENT } }, { text: q.replace("\n", "\n     "), options: { color: MUTED } }],
      { x: ix, y: cy + 0.82, w: iw, h: 0.42, fontSize: 10.5, valign: "top" });
    T(s, [{ text: "A. ", options: { bold: true, color: ACCENT } }, { text: a.replace("\n", "\n     "), options: { bold: true } }],
      { x: ix, y: cy + 1.3, w: iw, h: 0.5, fontSize: 12.5, valign: "top" });
    T(s, sub, { x: ix, y: cy + 1.86, w: iw, h: 0.42, fontSize: 9.5, color: MUTED, valign: "top" });
    card(s, x + 0.12, cy + ch - dh - 0.12, cw - 0.24, dh, ACCENT_BG, "decide-" + i);
    T(s, [{ text: find, options: { color: ACCENT, breakLine: true } }, { text: "→ " + act, options: { bold: true, color: ACCENT } }],
      { x: x + 0.22, y: cy + ch - dh - 0.12, w: cw - 0.4, h: dh, fontSize: 11.5, valign: "middle", paraSpaceAfter: 2 });
  });

  T(s, "Trace 학생 설문 2026.10 · 응답 34명 · 59% = 20명 · 44% = 15명 · 94% = 32명 · 공학·컴퓨터 18명, 2학년 19명으로 치우침 → 경향만",
    { x: 0.5, y: 4.9, w: 9, h: 0.25, fontSize: 10, color: MUTED });

  s.addNotes("학생 설문에서 59%가 \"어디까지 밝혀야 할지 모르겠다\"고 해서, 기준 양식인 내역서를 만들었습니다. 켜는 이유 1위가 \"받는 쪽이 요구하면\"이라 교수가 요구하고 학생이 쓰는 구조로 만들었고, \"감시받는 느낌\"이 걸림돌이라 원문은 학생 PC에만 둡니다. 그리고 94%가 AI 초안을 그냥 내면 안 된다고 해서, AI 답 그대로인 문장을 표시하고 제출 전에 고칠 수 있게 했습니다. (약 30초)");
}

// ───────── 4장 서비스 콘셉트 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("서비스 콘셉트: 잡지 않고, 제출 전에 고치게 한다", { placeholder: "title" });
  sec(s, "02", "서비스 기획");
  const flow = [
    ["기록", "평소처럼 AI와 과제\n원문은 학생 PC에만"],
    ["출처 보기", "문장마다 어느 AI 답 ·\n웹 글에서 왔는지"],
    ["제출 전 다듬기", "AI 답 그대로인 문장과\n표절 의심(출처 없는 웹 글)을\n학생이 직접 고침"],
    ["공개", "교수에게\n내역서 링크 한 장"],
  ];
  flow.forEach(([h, d], i) => {
    const x = 0.5 + i * 2.33, w = 2.05, hl = i === 2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.05, w, h: 1.2, rectRadius: 0.08, fill: { color: hl ? ACCENT_BG : SOFT }, line: { color: hl ? ACCENT : SOFT, width: hl ? 1.5 : 0.75 } });
    s.addShape(pres.shapes.OVAL, { x: x + 0.14, y: 1.17, w: 0.28, h: 0.28, fill: { color: ACCENT }, line: { color: ACCENT } });
    T(s, String(i + 1), { x: x + 0.14, y: 1.17, w: 0.28, h: 0.28, fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
    T(s, h, { x: x + 0.5, y: 1.17, w: w - 0.55, h: 0.28, fontSize: 13, bold: true, color: hl ? ACCENT : INK, valign: "middle" });
    T(s, d, { x: x + 0.14, y: 1.52, w: w - 0.2, h: 0.68, fontSize: 10, color: MUTED, valign: "top" });
    if (i < 3) s.addShape(pres.shapes.LINE, { x: x + w + 0.03, y: 1.65, w: 0.22, h: 0, line: { color: INK, width: 1.5, endArrowType: "triangle" } });
  });
  // 누가 쓰나
  card(s, 0.5, 2.55, 2.85, 2.8, SOFT, "who");
  T(s, "누가 쓰나", { x: 0.68, y: 2.65, w: 2.5, h: 0.28, fontSize: 13, bold: true });
  [["교수", "요구하는 사람", "AI 허용 과제에 사용 내역 요구\n설치 없이 내역서 링크 · QR만 연다"],
   ["학생", "쓰는 사람", "평소처럼 과제를 하고\n제출 전에 직접 고친다"]].forEach(([who, role, d], k) => {
    const y = 3.05 + k * 1.12;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.62, y, w: 2.61, h: 1.0, rectRadius: 0.06, fill: { color: "FFFFFF" }, line: { color: LINE, width: 0.75 } });
    T(s, [{ text: who + "  ", options: { bold: true, color: ACCENT } }, { text: role, options: { color: MUTED, fontSize: 9.5 } }], { x: 0.76, y: y + 0.1, w: 2.4, h: 0.26, fontSize: 12 });
    T(s, d, { x: 0.76, y: y + 0.4, w: 2.42, h: 0.52, fontSize: 10, valign: "top" });
  });
  // 카피킬러 + Trace — 교수님 피드백 (10/28) "카피킬러와 합쳐 고쳐 쓰게"
  T(s, "카피킬러 + Trace: 서로 못 보는 걸 본다", { x: 3.6, y: 2.55, w: 5.9, h: 0.28, fontSize: 13, bold: true });
  T(s, [{ text: "교수님 피드백  ", options: { bold: true, color: ACCENT } }, { text: "잡는 데서 끝내지 말고 학생이 고쳐 쓰며 배우게(교육적 가치) · 카피킬러 같은 점검과 합쳐서", options: { color: INK, breakLine: true } },
         { text: "→ 카피킬러가 못 보는 '과정'은 Trace가 보고, 고쳐 쓰는 건 학생이 직접", options: { color: MUTED } }],
    { x: 3.6, y: 2.85, w: 5.9, h: 0.38, fontSize: 9.5 });
  const cw = [1.55, 2.0, 2.35], cx0 = 3.6, ty = 3.3, rh = 0.47;
  [["", "카피킬러", "Trace (제출 전 다듬기)"]].concat([
    ["무엇과 비교", "세상 문서 DB와\n결과물만", "학생이 실제로 본 AI 답 ·\n웹 글과 과정까지"],
    ["웹 글을 GPT로\n바꿔 쓰면", "어절이 끊겨\n놓치기 쉬움", "복사 → GPT → 붙여넣기가\n남아 'AI 답 그대로'"],
    ["기록 밖에서 본\n논문 · 웹", "잡음", "못 잡음 → 카피킬러에 맡김"],
    ["보여 주는 것", "표절률 %", "문장마다 출처 →\n학생이 직접 고침"],
  ]).forEach((r, i) => {
    const y = i === 0 ? ty : ty + 0.3 + (i - 1) * rh, h = i === 0 ? 0.28 : rh - 0.04;
    if (i > 0) s.addShape(pres.shapes.LINE, { x: cx0, y: y - 0.02, w: 5.9, h: 0, line: { color: LINE, width: 0.75 } });
    let x = cx0;
    r.forEach((t, k) => {
      if (k === 2) s.addShape(pres.shapes.RECTANGLE, { x: x - 0.06, y, w: cw[2] + 0.02, h, fill: { color: ACCENT_BG }, line: { color: ACCENT_BG } });
      T(s, t, { x, y, w: cw[k] - 0.1, h, fontSize: i === 0 ? 10.5 : (k === 0 ? 9.5 : 9.5), bold: i === 0 || k === 0,
        color: i === 0 ? (k === 2 ? ACCENT : INK) : (k === 0 ? MUTED : (k === 2 ? INK : MUTED)), valign: "middle" });
      x += cw[k];
    });
  });
  s.addNotes([
    "Trace는 AI 사용을 잡아내는 도구가 아니라, 학생이 제출 전에 스스로 고치게 하고 그 과정을 공개하는 도구입니다.",
    "흐름은 네 단계입니다. 평소처럼 AI와 과제를 하면 기록되고, 출처 보기에서 문장마다 어느 AI 답에서 왔는지 보고, 제출 전에 AI 답과 똑같은 문장이나 출처 없이 붙인 웹 글, 곧 표절 의심 문장을 직접 고치거나 인용을 단 뒤, 교수에게 내역서 링크 한 장으로 공개합니다.",
    "교수님 피드백은 두 가지였습니다. 잡는 데서 끝내지 말고 학생이 고쳐 쓰며 배우게 하라는 교육적 가치, 그리고 카피킬러 같은 점검과 합치라는 것입니다. 카피킬러는 세상 문서와 결과물만 비교해서, 웹 글을 GPT로 바꿔 쓰면 놓치기 쉽습니다. Trace는 학생이 실제로 본 AI 답과 웹 글, 그리고 복사 → GPT → 붙여넣기 과정까지 봅니다. 반대로 기록 밖에서 본 글은 카피킬러가 잡습니다. 그래서 둘은 서로 못 보는 걸 보는 짝이고, Trace는 점수 대신 학생이 제출 전에 직접 고치게 합니다. (약 30초)",
    "",
    "질문 대비",
    "· 그래서 글 실력이 느나? → 아직 확인 못 함. 지금 말할 수 있는 건 '어디를 왜 고쳐야 하는지 알려 주고, 학생이 직접 고치게 한다'까지. 효과는 12주 테스트에서 학생 반응으로 봄.",
    "· 카피킬러와 실제로 연동하나? → 지금은 연동하지 않음. 학생이 같은 보고서를 카피킬러에도 돌리는 식으로 함께 씀. Trace는 카피킬러가 못 보는 '과정'을 맡음.",
    "· 표절 기준은? → 교육부 연구윤리 지침의 표절 정의 '출처 표시 없이 활용' — 출처 없이 붙인 웹 글을 다듬을 곳으로 보여 줌.",
  ].join("\n"));
}

// ───────── 5장 핵심 기능 · 개발 범위 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("핵심 기능과 개발 범위", { placeholder: "title" });
  sec(s, "02", "서비스 기획");
  const feats = [
    ["기록", "AI 대화 · 복사/붙여넣기 · Word 글 변화 · 키 횟수", "원문은 학생 PC에만, 서버엔 해시만"],
    ["출처 보기", "과제 문장마다 어디서 왔는지", "AI 답과 일치 및 유사 · 고침 · 참고함 · 다른 곳"],
    ["제출 전 다듬기", "AI 답과 (거의) 같은 문장 · 출처 없는 웹 글만", "[다듬기] → Word에서 그 문장 선택 — 고치는 건 학생"],
    ["내역서 · 교수 링크", "학생이 고른 것만 PDF 한 장 + 링크 · QR", "기록과 일치 확인 · 고친 문장 수는 발표 뒤"],
  ];
  feats.forEach(([h, a, b], i) => {
    const x = 0.5 + (i % 2) * 4.55, y = 1.0 + Math.floor(i / 2) * 1.42, w = 4.45;
    card(s, x, y, w, 1.3, SOFT, "feat-" + i);
    s.addShape(pres.shapes.OVAL, { x: x + 0.16, y: y + 0.14, w: 0.3, h: 0.3, fill: { color: ACCENT }, line: { color: ACCENT } });
    T(s, String(i + 1), { x: x + 0.16, y: y + 0.14, w: 0.3, h: 0.3, fontSize: 12, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
    T(s, h, { x: x + 0.56, y: y + 0.13, w: w - 0.7, h: 0.32, fontSize: 14, bold: true, valign: "middle" });
    T(s, [{ text: a, options: { breakLine: true } }, { text: b, options: { color: MUTED } }], { x: x + 0.56, y: y + 0.5, w: w - 0.7, h: 0.66, fontSize: 10.5, valign: "top", paraSpaceAfter: 3 });
  });
  // 개발 범위
  card(s, 0.5, 3.95, 9.0, 1.3, ACCENT_BG, "scope");
  T(s, "개발 범위", { x: 0.68, y: 4.03, w: 3, h: 0.3, fontSize: 13, bold: true, color: ACCENT });
  const scope = [
    ["대상", "AI를 허용한 학부 과제"],
    ["운영체제", "윈도우 · 맥 (Apple 칩)"],
    ["AI", "ChatGPT · Claude · Gemini 웹\nChatGPT · Claude 데스크톱 앱"],
    ["결과물", "Word · PDF 보고서"],
    ["보여 주는 것", "기록된 사실만\n점수 · 확률 판정 없음"],
  ];
  const sw5 = [1.55, 1.6, 2.3, 1.45, 1.75];
  let sx = 0.68;
  scope.forEach(([k, v], i) => {
    T(s, k, { x: sx, y: 4.4, w: sw5[i] - 0.1, h: 0.22, fontSize: 9.5, bold: true, color: MUTED });
    T(s, v, { x: sx, y: 4.63, w: sw5[i] - 0.1, h: 0.7, fontSize: 10.5, valign: "top" });
    sx += sw5[i];
  });
  s.addNotes([
    "핵심 기능은 네 가지입니다. 기록, 문장마다 어디서 왔는지 보여 주는 출처 보기, AI 답과 같거나 거의 같은 문장, 출처 없는 웹 글을 학생이 제출 전에 직접 고치는 다듬기, 그리고 학생이 고른 것만 교수에게 보내는 내역서와 링크입니다.",
    "범위는 AI를 허용한 학부 과제, 윈도우와 맥, ChatGPT · Claude · Gemini, Word와 PDF 보고서입니다. 점수나 확률로 판정하지 않고 기록된 사실만 보여 줍니다. (약 25초)",
    "",
    "질문 대비",
    "· 왜 표절률 · AI 확률을 안 내나? → 기획서 원칙 1. 과제 교수의 규칙은 '대화 내역 제출 · 복붙 감점'이지 표절률이 아님. 확률은 직접 쓴 학생도 걸림 → 사실(어디서 왔나)만.",
    "· 웹 글은 왜 출처 표시만 보나? → 교육부 연구윤리 지침의 표절 정의가 '출처 표시 없이 활용'. 출처를 달면 표절이 아님.",
  ].join("\n"));
}

// ───────── 5장 (이어서) 다듬기 기준과 근거 — 교수님 피드백: 검증된 기준 · 자료를 코드로 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("제출 전 다듬기: 검증된 기준을 코드로", { placeholder: "title" });
  sec(s, "02", "서비스 기획");
  const cw = [2.05, 2.95, 2.95, 1.05], x0 = 0.5;
  const rows = [
    ["무엇을", "근거", "Trace에서", "상태"],
    ["출처 없이 붙인 글 짚기", "교육부 연구윤리 지침 표절 정의\n'적절한 출처 표시 없이 활용'", "웹 글에 따옴표 · [1] · 주소 · '출처:'가\n없으면 다듬을 곳으로", "✓ 지금"],
    ["짧은 말은 넘기기", "카피킬러 기본 기준 6어절\n(지침 원문엔 숫자 없음)", "6어절 이상 문장만 다듬을 곳으로", "✓ 지금"],
    ["그대로 쓸 땐 인용", "직접 인용 = 큰따옴표 + 출처\n(대학 연구윤리 안내)", "[인용 달기] — 따옴표 · 출처 다는 법 안내", "발표 뒤"],
    ["내 말로 고쳐 쓰는 법", "바꿔 쓰기 절차 — 이해 → 원문 덮고 쓰기\n→ 원문과 대조 (Purdue OWL)", "[다듬기] — 세 단계를 옆에 띄움", "발표 뒤"],
    ["단어만 바꾼 문장 알리기", "바꿔 쓰기 유형 (Barrón-Cedeño 외 2013)\n한국어 형태소 분석 Kiwi (2024)", "\"단어만 바뀜 — 문장 구조는 AI 답 그대로\"", "발표 뒤"],
    ["가짜 참고문헌 확인", "AI 인용 중 가짜 GPT-3.5 55% · GPT-4 18%\n(Walters · Wilder 2023)", "Crossref API에 참고문헌 목록만 조회\n(학생 글은 안 나감)", "발표 뒤"],
  ];
  rows.forEach((r, i) => {
    const head = i === 0, y = head ? 0.98 : 1.3 + (i - 1) * 0.5, h = head ? 0.28 : 0.46;
    if (!head) s.addShape(pres.shapes.RECTANGLE, { x: x0, y, w: 9.0, h, fill: { color: i % 2 ? SOFT : "FFFFFF" }, line: { color: i % 2 ? SOFT : "FFFFFF" } });
    let x = x0 + 0.1;
    r.forEach((t, k) => {
      const now = k === 3 && t.startsWith("✓");
      T(s, t, { x, y, w: cw[k] - 0.12, h, fontSize: head ? 10 : (k === 0 ? 10.5 : 9.5), bold: head || k === 0 || now,
        color: head ? MUTED : (k === 3 ? (now ? ACCENT : MUTED) : (k === 1 ? MUTED : INK)), valign: "middle" });
      x += cw[k];
    });
  });
  // 왜 교육적인가
  card(s, 0.5, 4.38, 9.0, 0.98, ACCENT_BG, "why-edu");
  T(s, "왜 교육적인가", { x: 0.68, y: 4.45, w: 2, h: 0.26, fontSize: 12, bold: true, color: ACCENT });
  T(s, [
    { text: "규칙을 알려 주기만 해도 표절이 3분의 2 줄었다 ", options: { bold: true } }, { text: "— 겁을 줘서가 아니라 알게 돼서 (Dee · Jacob 2012, 대학생 1,200편 무작위 실험)", options: { color: MUTED, breakLine: true } },
    { text: "피드백과 스스로 점검하기가 글의 질을 높인다 ", options: { bold: true } }, { text: "(Graham 외 2011, 초·중·고 메타분석)  →  Trace는 점수 대신 이유와 고치는 법을 준다", options: { color: MUTED } },
  ], { x: 0.68, y: 4.72, w: 8.7, h: 0.58, fontSize: 9.5, valign: "top", paraSpaceAfter: 3 });
  s.addNotes([
    "교수님 피드백대로, 다듬기의 기준은 저희가 정한 게 아니라 검증된 기준과 연구에서 가져와 코드로 옮겼습니다.",
    "지금 들어간 건 두 가지입니다. 교육부 지침의 표절 정의대로 출처 없이 붙인 글을 짚고, 카피킬러 기본값인 6어절보다 짧은 말은 넘깁니다. 발표 뒤에는 인용 다는 법과 바꿔 쓰기 절차를 버튼 옆에 띄우고, 단어만 바꾼 문장을 알리고, AI가 지어낸 참고문헌을 Crossref API로 확인합니다.",
    "교육적 근거도 있습니다. 규칙을 알려 주기만 해도 표절이 3분의 2 줄었고, 그 이유는 겁이 아니라 알게 돼서였습니다. 그래서 Trace는 점수 대신 이유와 고치는 법을 줍니다. (약 30초)",
    "",
    "질문 대비",
    "· 그래서 글 실력이 느나? → Trace로는 아직 확인 못 함. 근거는 비슷한 개입(규칙 안내 · 피드백)의 연구 결과까지 (Graham 보고서는 초·중·고 대상). 12주 테스트에서 학생이 실제로 고친 문장 수로 봄.",
    "· 6어절이 법적 기준인가? → 아님. 지침 원문엔 숫자가 없고, 6어절은 카피킬러 기본값 (미국 일부는 6단어, 서울대 2008 지침은 '두 문장'). 그래서 '기준 이름과 출처'를 같이 보여 줌.",
    "· 단어만 바꾼 걸 어떻게 아나? → 출처 잇기가 이미 그 AI 답을 찾은 문장만 형태소로 다시 비교 (어순 · 조사만 다르면 '단어만 바뀜'). 판정이 아니라 안내.",
    "· Crossref에 뭐가 나가나? → 참고문헌 목록 줄만. 학생 본문은 안 나감 (원칙: 학생 글을 밖으로 보내지 않음).",
  ].join("\n"));
}

// ───────── 6장 사용자 경험 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("사용자 경험: 교수는 링크만 열고, 학생은 평소처럼 쓴다", { placeholder: "title" });
  sec(s, "03", "사용자 경험 설계");
  T(s, [{ text: "User Flow   ", options: { bold: true, color: INK } }, { text: "주황 = 교수 · 파랑 = 학생 · 굵은 파랑 = 새로 더한 제출 전 다듬기", options: { color: MUTED } }],
    { x: 0.5, y: 0.95, w: 9, h: 0.24, fontSize: 10 });
  s.addImage({ path: IMG + "user-flow-crop.png", x: 0.6, y: 1.22, w: 8.8, h: 8.8 / 2.569 });
  const scen = [
    ["교수 · AI 허용 과목", "공지에 'Trace 내역서 첨부' → 학생이 낸 링크 열기\n→ 맨 위 한 줄만 보고, 궁금한 학생만 상세", "C0502A"],
    ["학생 이서연", "기록 켜고 ChatGPT와 보고서 → 다듬을 곳 3개\n→ 웹 글 1개 인용 · AI 답 2개 직접 고침 → 링크 제출", ACCENT],
  ];
  scen.forEach(([h, t, c], i) => {
    const x = 0.5 + i * 4.55, y = 4.72, w = 4.45;
    card(s, x, y, w, 0.75, SOFT, "scen-" + i);
    T(s, [{ text: h, options: { bold: true, color: c, breakLine: true } }, { text: t, options: { color: INK, fontSize: 9.5 } }],
      { x: x + 0.14, y, w: w - 0.24, h: 0.75, fontSize: 10.5, valign: "middle" });
  });
  s.addNotes([
    "사용 흐름입니다. 위가 교수, 아래가 학생입니다.",
    "교수는 계정도 설치도 없습니다. 공지에 'Trace 내역서 첨부'라고 적고, 학생이 낸 링크를 열어 맨 위 한 줄만 보면 됩니다.",
    "학생 이서연은 기록을 켜고 평소처럼 ChatGPT와 보고서를 씁니다. 제출 전에 출처 보기에서 다듬을 곳 3개를 보고, 웹 글 하나는 인용을 달고, AI 답 두 문장은 직접 고친 뒤 링크를 냅니다. 다듬을 곳이 없으면 바로 제출로 갑니다. (약 25초)",
  ].join("\n"));
}

// ───────── 6장 (이어서) 와이어프레임 ①② ─────────
[
  // 11/3 박상진: 10/19 와이어프레임 → 지금 앱 화면 (피그마 프로토타입과 같은 그림 · 2-디자인/피그마 넣을 화면)
  ["와이어프레임 ① 처음 한 번 · 홈", [
    ["scr-welcome.png", 1.6, "처음 한 번", "무엇을 기록하고 무엇은 안 하는지 먼저 보여 줌\n원문은 내 PC에만 · 교수에겐 내가 고른 것만"],
    ["scr-home.png", 1.6, "홈", "쓰는 법 4단계 · 과제마다 '다음 할 일' 버튼 하나\n마감 순 · 카드마다 4단계 진행 표시"]]],
  ["와이어프레임 ② 다듬기 · 교수 링크", [
    ["scr-refine.png", 1.6, "출처 보기 · 제출 전 다듬기", "문장마다 어디서 왔는지 색으로 · [다듬을 곳]만 모아 보기\n[다듬기] → 기록이 켜지고 Word에서 그 문장 선택"],
    ["scr-prof.png", 1.6, "교수 링크 (내역서)", "학생이 고른 것만, 숫자와 사실만\n'AI 답과 일치 및 유사 N · 다른 곳 M' · 서버 기록과 일치"]]],
].forEach(([title, two], si) => {
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText(title, { placeholder: "title" });
  sec(s, "03", "사용자 경험 설계");
  two.forEach(([f, r, h, d], i) => {
    const cx = 0.5 + i * 4.6, cy = 1.0, bw = 4.4, bh = 2.9;
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: cy, w: bw, h: bh, fill: { color: SOFT }, line: { color: LINE, width: 0.75 } });
    const iw = Math.min(bw, bh * r), ih = iw / r;
    s.addImage({ path: IMG + f, x: cx + (bw - iw) / 2, y: cy + (bh - ih) / 2, w: iw, h: ih });
    T(s, h, { x: cx, y: 4.05, w: bw, h: 0.3, fontSize: 14, bold: true });
    T(s, d, { x: cx, y: 4.4, w: bw, h: 0.75, fontSize: 10.5, color: MUTED, valign: "top" });
  });
  T(s, "11/3 · 앱 v0.1.17 실제 화면 — 피그마 프로토타입과 같은 그림", { x: 0.5, y: 5.25, w: 9, h: 0.22, fontSize: 9.5, color: MUTED });
  s.addNotes("(말 없이 넘김 — 화면만 보여 줌. 시간이 남으면: " + (si === 0
    ? "처음 켤 때 무엇을 기록하고 무엇은 안 하는지부터 보여 줘 감시처럼 느끼지 않게 했고, 홈은 과제마다 다음 할 일 버튼 하나만 둡니다.)"
    : "다듬을 곳만 모아 보고, [다듬기]를 누르면 기록이 켜진 채 Word에서 그 문장이 선택됩니다. 교수 링크는 학생이 고른 것만 보여 줍니다.)"));
});

// ───────── 프로토타입 — 피그마 링크 · 직접 써 보고 고친 것 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("UI/UX 프로토타입", { placeholder: "title" });
  sec(s, "04", "UI/UX 프로토타입");
  card(s, 0.5, 1.0, 4.6, 4.35, ACCENT_BG, "figma");
  T(s, "피그마 프로토타입", { x: 0.7, y: 1.12, w: 4.2, h: 0.32, fontSize: 15, bold: true, color: ACCENT });
  T(s, FIGMA_URL ? [{ text: FIGMA_LABEL, options: { hyperlink: { url: FIGMA_URL, tooltip: "피그마 프로토타입 열기" } } }] : "피그마 링크 자리 (박상진에게 받으면 넣기)",
    { x: 0.7, y: 1.5, w: 4.2, h: 0.5, fontSize: 11, color: FIGMA_URL ? ACCENT : "C0502A", valign: "top" });
  T(s, "화면 11개 · ★ 핵심 (지금 앱 화면 그대로)", { x: 0.7, y: 2.0, w: 4.2, h: 0.26, fontSize: 11.5, bold: true });
  const tile = (x, y, id, name, star, c) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.74, h: 0.62, rectRadius: 0.05, fill: { color: "FFFFFF" }, line: { color: star ? c : LINE, width: star ? 1.5 : 0.75 } });
    T(s, [{ text: (star ? "★ " : "") + id, options: { bold: true, color: c, fontSize: 9, breakLine: true } }, { text: name, options: { fontSize: 8.5, color: INK } }],
      { x: x + 0.04, y, w: 0.68, h: 0.62, align: "center", valign: "middle" });
  };
  const flow = (y, label, c, arr) => {
    if (label) T(s, label, { x: 0.7, y: y - 0.26, w: 1, h: 0.22, fontSize: 10, bold: true, color: c });
    arr.forEach(([id, name, star], k) => {
      const x = 0.7 + k * 0.86;
      tile(x, y, id, name, star, c);
      if (k < arr.length - 1) s.addShape(pres.shapes.LINE, { x: x + 0.75, y: y + 0.31, w: 0.1, h: 0, line: { color: MUTED, width: 1, endArrowType: "triangle" } });
    });
  };
  flow(2.58, "학생", ACCENT, [["F-0", "처음 한 번"], ["F-1", "홈", 1], ["F-2", "과제 상세"], ["F-2a", "기록\n다시 보기"]]);
  flow(3.3, "", ACCENT, [["F-3", "출처 보기", 1], ["F-3a", "다듬기", 1], ["F-4", "연결 확인"], ["F-5", "내보내기"]]);
  flow(4.28, "교수", "C0502A", [["P-1", "내역서 요약", 1], ["P-2", "출처 보기", 1]]);
  T(s, "보는 법: 위 링크를 열고 ▶ — 버튼을 누르면 다음 화면", { x: 0.7, y: 4.98, w: 4.2, h: 0.3, fontSize: 9.5, color: MUTED });
  // 직접 써 보고 고친 것
  card(s, 5.35, 1.0, 4.15, 4.35, SOFT, "selftest");
  T(s, "직접 과제 하나를 써 보고 고친 것", { x: 5.53, y: 1.1, w: 3.9, h: 0.28, fontSize: 13, bold: true });
  T(s, "11/2 · 맥 · ChatGPT 앱 · Word 보고서", { x: 5.53, y: 1.38, w: 3.9, h: 0.22, fontSize: 9.5, color: MUTED });
  const fixes = [
    ["ChatGPT 앱의 긴 보고서 답이 기록에서 빠짐", "답 안의 제목에서 멈추던 읽기를 고침", "v0.1.16"],
    ["맥 Word에 직접 친 글이 '기록 없음'으로 뜸", "맥 키 입력도 Word로 알아보게 고침", "v0.1.17"],
    ["그대로 붙인 글이 엉뚱한 답에 '고쳐 씀'으로 이어짐", "원래 답이 없으면 'AI에서 그대로 붙여넣음'으로", "v0.1.17"],
  ];
  fixes.forEach(([p, f, v], i) => {
    const y = 1.72 + i * 1.0;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.48, y, w: 3.9, h: 0.88, rectRadius: 0.05, fill: { color: "FFFFFF" }, line: { color: LINE, width: 0.75 } });
    T(s, p, { x: 5.6, y: y + 0.1, w: 3.0, h: 0.32, fontSize: 10, bold: true, valign: "middle" });
    T(s, "→ " + f, { x: 5.6, y: y + 0.42, w: 3.0, h: 0.32, fontSize: 9.5, color: ACCENT, valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.6, y: y + 0.1, w: 0.68, h: 0.24, rectRadius: 0.12, fill: { color: ACCENT_BG }, line: { color: ACCENT, width: 0.75 } });
    T(s, v, { x: 8.6, y: y + 0.1, w: 0.68, h: 0.24, fontSize: 9, bold: true, color: ACCENT, align: "center", valign: "middle" });
  });
  T(s, "팀 안에서 해 본 것 → 실제 학생 · 교수 테스트는 12주", { x: 5.53, y: 4.82, w: 3.9, h: 0.4, fontSize: 9.5, color: MUTED, valign: "middle" });
  s.addNotes([
    "프로토타입은 피그마 링크로 보실 수 있습니다. 지금 앱 화면 그대로 학생 화면 아홉 개, 교수 화면 두 개를 이었고, 별 표시가 핵심 화면입니다.",
    "오른쪽은 저희가 직접 과제를 하나 써 보며 찾은 문제 세 개로, v0.1.16과 v0.1.17에서 고쳤습니다. (약 20초)",
  ].join("\n"));
}

// ───────── 9장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("시스템 설계: 원문은 학생 PC에 남는다", { placeholder: "title" });
  sec(s, "05", "시스템 설계");
  const FE = ACCENT, BE = "4A4A46", DB = "2E7D5B";
  // 범례
  [["FE", FE, "Frontend"], ["BE", BE, "Backend"], ["DB", DB, "Database"]].forEach(([k, c, name], i) => {
    const x = 6.55 + i * 1.0;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 0.47, w: 0.36, h: 0.22, rectRadius: 0.05, fill: { color: c }, line: { color: c } });
    T(s, k, { x, y: 0.47, w: 0.36, h: 0.22, fontSize: 9, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
    T(s, name, { x: x + 0.4, y: 0.47, w: 0.6, h: 0.22, fontSize: 9, color: MUTED, valign: "middle" });
  });
  const chip = (x, y, k, c) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.36, h: 0.22, rectRadius: 0.05, fill: { color: c }, line: { color: c } });
    T(s, k, { x, y, w: 0.36, h: 0.22, fontSize: 9, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
  };
  const row = (x, y, w, k, c, head, sub, hl) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.62, rectRadius: 0.06, fill: { color: "FFFFFF" }, line: { color: hl ? ACCENT : LINE, width: hl ? 1.5 : 0.75 } });
    chip(x + 0.12, y + 0.12, k, c);
    T(s, head, { x: x + 0.56, y: y + 0.07, w: w - 0.65, h: 0.27, fontSize: 12, bold: true });
    T(s, sub, { x: x + 0.56, y: y + 0.33, w: w - 0.65, h: 0.24, fontSize: 10, color: MUTED });
  };
  // 학생 PC
  card(s, 0.5, 1.1, 3.75, 3.45, SOFT, "pc");
  T(s, [{ text: "학생 PC", options: { bold: true } }, { text: "  설치형 앱 · 윈도우 · 맥", options: { color: MUTED, fontSize: 10 } }], { x: 0.7, y: 1.2, w: 3.4, h: 0.3, fontSize: 14 });
  row(0.65, 1.55, 3.45, "FE", FE, "앱 화면", "기록 · 출처 보기 · 다듬기 · 제출");
  row(0.65, 2.27, 3.45, "BE", BE, "기록기 · 브라우저 확장", "AI 대화 · 복사/붙여넣기 · Word 글 · 키 횟수");
  row(0.65, 2.99, 3.45, "BE", BE, "출처 잇기 · 제출 전 다듬기", "과제 문장 ↔ AI 답 연결");
  row(0.65, 3.71, 3.45, "DB", DB, "원문 보관 — PC에만", "AI 대화 · 과제 글 원문 (개인정보 먼저 가림)", true);
  // 서버
  card(s, 4.95, 1.1, 2.45, 2.1, SOFT, "server");
  T(s, [{ text: "서버", options: { bold: true } }, { text: "  Flask · Render", options: { color: MUTED, fontSize: 10 } }], { x: 5.12, y: 1.2, w: 2.2, h: 0.3, fontSize: 14 });
  chip(5.12, 1.58, "BE", BE);
  T(s, [
    { text: "구글 · 카카오 로그인", options: { breakLine: true } },
    { text: "해시로 조작 확인", options: { breakLine: true } },
    { text: "내역서 PDF", options: { breakLine: true } },
    { text: "교수 링크 (읽기만)" },
  ], { x: 5.56, y: 1.55, w: 1.8, h: 1.5, fontSize: 12, paraSpaceAfter: 4, valign: "top" });
  // DB
  card(s, 4.95, 3.55, 2.45, 1.0, SOFT, "db");
  chip(5.12, 3.68, "DB", DB);
  T(s, "Supabase · PostgreSQL", { x: 5.56, y: 3.65, w: 1.8, h: 0.28, fontSize: 12, bold: true });
  T(s, "해시 · 내역서 · 링크\n원문은 학생이 고른 대화만", { x: 5.56, y: 3.95, w: 1.8, h: 0.5, fontSize: 10, color: MUTED });
  // 교수
  card(s, 8.05, 1.1, 1.45, 1.35, ACCENT_BG, "prof");
  T(s, "교수", { x: 8.2, y: 1.2, w: 1.2, h: 0.3, fontSize: 14, bold: true, color: ACCENT });
  chip(8.2, 1.58, "FE", FE);
  T(s, "브라우저로\n링크만 · 계정 없음", { x: 8.2, y: 1.88, w: 1.25, h: 0.5, fontSize: 10, color: INK });
  // 화살표 + 번호
  const arrow = (x, y, w, h, opt = {}) => s.addShape(pres.shapes.LINE, Object.assign({ x, y, w, h, line: { color: INK, width: 1.5, endArrowType: "triangle" } }, opt));
  const num = (x, y, n) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: 0.28, h: 0.28, fill: { color: ACCENT }, line: { color: ACCENT } });
    T(s, n, { x, y, w: 0.28, h: 0.28, fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
  };
  arrow(4.25, 1.8, 0.7, 0); num(4.46, 1.52, "1");
  arrow(4.25, 2.7, 0.7, 0); num(4.46, 2.42, "2");
  arrow(7.4, 1.8, 0.65, 0); num(7.58, 1.52, "3");
  s.addShape(pres.shapes.LINE, { x: 6.175, y: 3.2, w: 0, h: 0.35, line: { color: INK, width: 1.5, beginArrowType: "triangle", endArrowType: "triangle" } });
  // 데이터 흐름 (오른쪽 아래)
  card(s, 7.6, 2.75, 1.9, 1.8, ACCENT_BG, "flow");
  T(s, "데이터 흐름", { x: 7.72, y: 2.83, w: 1.75, h: 0.28, fontSize: 11.5, bold: true, color: ACCENT });
  [["1", "기록 중", "서버엔 해시(글 지문)만"], ["2", "제출 때", "고른 원문만 · 지문으로 확인"], ["3", "교수", "링크로 읽기만"]].forEach(([n, a, b], i) => {
    const y = 3.18 + i * 0.44;
    num(7.72, y, n);
    T(s, [{ text: a, options: { bold: true, breakLine: true } }, { text: b, options: { color: MUTED, fontSize: 9 } }], { x: 8.06, y: y - 0.04, w: 1.42, h: 0.42, fontSize: 10, valign: "top" });
  });
  // 기술 스택 — 앱 구현 / 윈도우 구현 / 맥 구현 (칸마다 알약 · 조각마다 [글, "b" 굵게 | "m" 흐리게])
  const pw = parts => parts.reduce((w, [t]) => w + [...t].reduce((n, ch) => n + (/[\u3131-\uD79D]/.test(ch) ? 0.118 : ch === " " ? 0.035 : 0.068), 0), 0) + 0.24;
  const pill = (x, y, parts) => {
    const w = pw(parts);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.22, rectRadius: 0.11, fill: { color: "FFFFFF" }, line: { color: LINE, width: 0.75 } });
    T(s, parts.map(([t, k]) => ({ text: t, options: k === "b" ? { bold: true } : { color: MUTED } })),
      { x, y, w, h: 0.22, fontSize: 9, align: "center", valign: "middle", margin: 0 });
    return w;
  };
  const cols = [
    ["앱 구현", 3.6, [[["Python", "b"], [" 프로그램 하나", "m"]], [["화면", "b"], [" = 앱 안의 HTML 창", "m"]]],
                     [[["설치", "b"], [" = 윈도우 exe · 맥 dmg", "m"]], [["업데이트", "b"], [" = 앱 안에서", "m"]]]],
    ["윈도우 구현", 2.6, [[["Word ← ", "m"], ["COM", "b"]]], [[["AI 앱 ← ", "m"], ["UI Automation", "b"]]]],
    ["맥 구현", 2.6, [[["Word ← ", "m"], ["AppleScript", "b"]]], [[["AI 앱 ← ", "m"], ["손쉬운 사용 API", "b"]]]],
  ];
  let cx = 0.5;
  cols.forEach(([head, w, r1, r2]) => {
    card(s, cx, 4.68, w, 0.78, SOFT, "stack-" + head);
    T(s, head, { x: cx + 0.14, y: 4.72, w: w - 0.2, h: 0.22, fontSize: 10, bold: true, color: ACCENT });
    [r1, r2].forEach((row, ri) => {
      let px = cx + 0.14;
      row.forEach(parts => { px += pill(px, 4.97 + ri * 0.25, parts) + 0.08; });
    });
    cx += w + 0.1;
  });
  s.addNotes([
    "다음은 시스템 설계도입니다. Trace는 웹사이트가 아니라 학생 PC에 까는 앱입니다. Word나 ChatGPT 앱처럼 브라우저 밖까지 읽어야 해서, 아래처럼 윈도우와 맥을 따로 만들었습니다.",
    "왼쪽 학생 PC에서 AI와 나눈 대화와 보고서 글을 기록하는데, 이 글은 학생 컴퓨터에만 저장됩니다. ① 기록하는 동안 서버에는 글의 지문인 해시만 갑니다. ② 제출할 때 학생이 고른 대화만 서버로 가고, 서버가 지문을 비교해 기록과 같은지 확인합니다. ③ 교수는 계정 없이 링크로 읽기만 합니다. (약 30초)",
    "",
    "그림 풀이 (물으면)",
    "· FE / BE / DB = 화면(Frontend) / 뒤에서 일하는 부분(Backend) / 저장소(Database)",
    "· 해시 = 글마다 만드는 64자리 지문. 지문만으론 글을 알 수 없지만, 같은 글인지는 확인됨",
    "· Flask = 서버 프로그램 (Python) · Render = 서버를 올려 둔 곳 · Supabase = 인터넷 DB (PostgreSQL)",
    "· 학생 PC '원문 보관' vs 서버 밑 DB → PC 쪽은 앱 폴더의 파일 (같은 컴퓨터라 한 상자) · 서버 DB는 인터넷 DB (서버는 Render, DB는 Supabase — 서로 다른 곳이라 따로 그리고 화살표로 이음). 서버 DB의 원문은 학생이 내역서에 고른 대화뿐 (12장 messages)",
    "· 개인정보 먼저 가림 = 이메일 · 전화번호 · 주민번호 · 카드번호 · API 키는 PC에 저장하기 전에 가림",
    "",
    "질문 대비",
    "· 해시가 뭔가? → 글의 지문 같은 64자리 값. 해시만 보고 원래 글은 알 수 없음. 기록마다 앞 해시와 사슬처럼 이어서, 하나라도 빼거나 바꾸면 끝값이 달라짐.",
    "· 개인정보는? → 이메일 · 전화번호 · 주민번호 · 카드번호 · API 키는 PC에 저장하기 전에 가림.",
    "· 화면은 뭘로? → 앱 안에 HTML 창을 띄움 (pywebview 라이브러리). React 같은 프레임워크 없이 HTML · JS.",
    "· 업데이트는? → 처음만 내려받아 설치. 그 뒤엔 앱이 직접 받아 바꿈 (맥 '열지 않음' · 윈도우 'PC 보호' 경고를 매번 안 보게).",
    "· 배포는? → 버전 태그 하나 → GitHub Actions가 exe · dmg 함께 빌드. 맥은 같은 인증서로 서명해야 업데이트해도 권한이 안 풀림.",
    "· COM / UI Automation / 손쉬운 사용이 뭔가? → 운영체제가 주는 '다른 앱 글 읽기' 기능. 그래서 맥은 처음에 권한을 허락받음.",
    "· 키로거 아닌가요? → 어떤 키인지는 저장 안 함. 앱별로 10초마다 '친 횟수 · 지운 횟수'만.",
    "· 학생이 PC 원문을 고쳐서 내면? → 기록 때 해시가 이미 서버에 있어서 '기록과 다름'으로 표시됨.",
    "· 기록을 꺼 두고 쓰면? → 그 부분은 '출처 기록 없음'. 직접 썼다고도, 베꼈다고도 단정하지 않음.",
    "· 윈도우 · 맥 기능 차이? → v0.1.17에서 다듬기 문장 고르기 · ChatGPT 앱 읽기까지 맞춤. 남은 차이: 맥은 Apple 칩만 (인텔 맥 미지원).",
    "· 그럼 웹으로는 못 하나? → 웹 AI 대화만 볼 거면 확장으로 됨. 하지만 Word에서 친 글 · 데스크톱 AI 앱 · 앱 사이 붙여넣기는 못 봄 → 출처를 이을 수 없음.",
    "· 설치가 번거롭지 않나? → exe/dmg 하나 · 자동 업데이트(서버 /api/app/latest). 설치 오류는 실제 수업 전에 먼저 고침 (13장).",
    "· 서버가 해외(싱가포르)인데? → 실제 수업 전에 국외 이전 동의 문구를 동의 화면에 넣음 (실제 수업 전 보완 · 13장).",
  ].join("\n"));
}

// ───────── 10장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("DB 설계: 기록 줄기와 제출 줄기", { placeholder: "title" });
  sec(s, "06", "DB 설계");
  const NEW = ACCENT;
  const box = (x, y, w, h, name, ko, sub, opt = {}) => {
    const dash = opt.next;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06,
      fill: { color: opt.isNew ? ACCENT_BG : "FFFFFF" },
      line: { color: opt.isNew ? NEW : (dash ? MUTED : LINE), width: opt.isNew ? 1.5 : 1, dashType: dash ? "dash" : "solid" } });
    T(s, [{ text: name + "  ", options: { bold: true, color: dash ? MUTED : (opt.isNew ? NEW : INK) } }, { text: ko, options: { color: dash ? MUTED : INK } }],
      { x: x + 0.12, y: y + 0.06, w: w - 0.2, h: 0.28, fontSize: 12 });
    if (sub) T(s, sub, { x: x + 0.12, y: y + 0.34, w: w - 0.2, h: h - 0.4, fontSize: 10, color: MUTED, valign: "top" });
  };
  const line = (x, y, w, h, arrow, opt = {}) => s.addShape(pres.shapes.LINE, { x, y, w, h,
    line: Object.assign({ color: opt.color || INK, width: 1.25, dashType: opt.dash ? "dash" : "solid" }, arrow ? { endArrowType: "triangle" } : {}) });
  const lab = (x, y, t, c) => T(s, t, { x, y, w: 0.5, h: 0.2, fontSize: 10, bold: true, color: c || MUTED });

  // 두 줄기를 바탕 띠로 나눔 — 위 회색 = 기록 줄기 · 아래 초록 = 제출 줄기 (파랑은 '발표 뒤 구현' 뜻이라 띠에 안 씀)
  const REC = "5F5E5A", SUB = "2E7D5B";
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.38, y: 1.0, w: 9.24, h: 1.22, rectRadius: 0.08, fill: { color: "F4F3EF" }, line: { color: "F4F3EF" } });
  T(s, [{ text: "① 기록 줄기", options: { bold: true, color: REC } }, { text: "   기록하는 동안 쌓임 · 글 대신 해시만", options: { color: MUTED } }], { x: 0.52, y: 1.04, w: 6, h: 0.22, fontSize: 10 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.38, y: 2.36, w: 9.24, h: 2.64, rectRadius: 0.08, fill: { color: "EEF6F1" }, line: { color: "EEF6F1" } });
  T(s, [{ text: "② 제출 줄기", options: { bold: true, color: SUB, breakLine: true } }, { text: "내역서를 만들 때\n학생이 고른 것만", options: { color: MUTED, fontSize: 9.5 } }],
    { x: 0.52, y: 2.46, w: 2.1, h: 0.75, fontSize: 11, valign: "top" });

  // 줄기: 학생 → 과제 → 기록 한 번 → 기록 이벤트
  box(0.5, 1.3, 1.95, 0.8, "users", "학생", "이메일 · 구글/카카오 계정 번호");
  box(2.8, 1.3, 1.95, 0.8, "works", "과제", "제목 · 허용 범위 메모");
  box(5.1, 1.3, 1.95, 0.8, "sessions", "기록 한 번", "시작 · 끝 · 잠금 (조작 확인용)");
  box(7.4, 1.3, 2.1, 0.8, "events", "기록 이벤트", "종류 · 시각 · 원문 대신 해시");
  [[2.45, 2.8], [4.75, 5.1], [7.05, 7.4]].forEach(([a, b]) => { line(a, 1.57, b - a, 0, true); lab(a + 0.02, 1.31, "1 : N"); });

  // 과제 → 내역서
  line(3.775, 2.1, 0, 0.6, true); lab(3.85, 2.4, "1 : N");
  box(2.8, 2.7, 2.35, 1.6, "statements", "내역서", "요약 숫자 · 학생 설명 두 개\n원문이 기록과 맞는지");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.92, y: 3.75, w: 2.11, h: 0.42, rectRadius: 0.05, fill: { color: ACCENT_BG }, line: { color: NEW, width: 1 } });
  T(s, [{ text: "retain_until  ", options: { bold: true } }, { text: "보관 기간 · 발표 뒤" }], { x: 3.02, y: 3.75, w: 2.0, h: 0.42, fontSize: 11, color: NEW, valign: "middle" });

  // 내역서 → 딸린 표 5개
  const kids = [
    ["messages", "보여 준 원문", "학생이 고른 질문 · 답만 · 해시로 확인"],
    ["links", "출처 결정", "이 문장 ← 이 AI 답 (맞다 / 아니다)"],
    ["redactions", "가린 것", "어느 기록인지만 · 내용은 안 옴"],
    ["shares", "교수 링크", "토큰 · 만료 · 학생이 끊을 수 있음"],
    ["checks", "제출 전 다듬기 · 발표 뒤", "고친 문장 수만 셈 · 원문 없음"],
  ];
  const kx = 5.65, kw = 3.85, kh = 0.4, kg = 0.08, ky0 = 2.55;
  line(5.15, 3.5, 0.3, 0, false); lab(5.17, 3.25, "1 : N");
  line(5.45, ky0 + kh / 2, 0, (kids.length - 1) * (kh + kg), false);
  kids.forEach(([n, ko, sub], i) => {
    const y = ky0 + i * (kh + kg), isNew = n === "checks";
    line(5.45, y + kh / 2, kx - 5.45, 0, true, { color: isNew ? NEW : INK });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: kx, y, w: kw, h: kh, rectRadius: 0.05, fill: { color: isNew ? ACCENT_BG : "FFFFFF" }, line: { color: isNew ? NEW : LINE, width: isNew ? 1.5 : 1 } });
    T(s, [{ text: n + "  ", options: { bold: true, color: isNew ? NEW : INK } }, { text: ko + "   ", options: { color: isNew ? NEW : INK } }, { text: sub, options: { color: MUTED, fontSize: 9.5 } }],
      { x: kx + 0.12, y, w: kw - 0.2, h: kh, fontSize: 11, valign: "middle" });
  });

  T(s, [{ text: "파랑 = 설계에 넣음 · 구현은 발표 후 2주 안에", options: { color: MUTED } }],
    { x: 0.5, y: 5.1, w: 9, h: 0.25, fontSize: 10 });
  s.addNotes([
    "다음은 핵심 DB 설계도입니다. 윗줄은 기록할 때 쌓이는 표입니다. 학생 한 명이 과제 여러 개를, 과제 하나가 기록 여러 번을, 기록 한 번이 이벤트 여러 개를 가지고, 이벤트엔 글 대신 해시만 남습니다.",
    "아랫줄은 제출할 때 쓰는 표입니다. 학생이 내역서를 만들면 한 장이 생기고, 거기에 학생이 고른 대화 원문, 문장과 AI 답의 연결, 가린 기록, 교수 링크가 붙습니다. 파랑 두 개는 발표 후 2주 안에 만듭니다. (약 25초)",
    "",
    "아랫줄 표 풀이 (물으면)",
    "· statements 내역서 = '내역서 만들기'를 누르면 한 장. 요약 숫자 · 학생 설명 두 칸 · 원문이 기록과 맞는지. retain_until = 언제까지 보관 (예: 성적 이의 신청 기간까지)",
    "· messages = 학생이 보여 주기로 고른 대화 글 — 서버에 실제 글이 있는 유일한 곳, 지문으로 확인된 것만",
    "· links = '이 문장은 이 AI 답에서' 를 학생이 맞다 / 아니다로 확인한 기록",
    "· redactions = 학생이 가린 기록 — 내용은 안 오고 가렸다는 사실만",
    "· shares = 교수 링크 열쇠 · 만료 · 학생이 끊을 수 있음",
    "· checks = 제출 전에 고친 문장 수만 (원문 없음)",
    "",
    "질문 대비",
    "· 로그인 토큰을 왜 JWT 말고 DB(tokens)에 두나? → 학생 기록이라 '이 기기 연결 끊기'가 바로 돼야 함 (server/db.py).",
    "· 교수가 원문을 어떻게 보나? → 학생이 고른 질문 · 답만 messages에 오고, 서버가 해시로 확인한 뒤 보여 줌.",
    "· 그림에서 뺀 표? → 로그인 보조 3개(tokens · devices · login_tickets), batches(받은 묶음 기록), contexts(예전 기능 · 10/1부터 안 씀).",
  ].join("\n"));
}

// ───────── 11장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("개발 계획: 이미 돌아가는 것 위에 더한다", { placeholder: "title" });
  sec(s, "07", "개발 계획");
  const YH = ACCENT, SJ = "2E7D5B", BOTH = MUTED;
  const head = (x, y, t) => T(s, t, { x, y, w: 4, h: 0.28, fontSize: 13, bold: true });
  const dot = (x, y, c) => s.addShape(pres.shapes.OVAL, { x, y, w: 0.1, h: 0.1, fill: { color: c }, line: { color: c } });

  // ① 구현 일정 — 칸마다 할 일 · 점 색 = 맡은 사람
  head(0.5, 0.92, "구현 일정");
  T(s, [{ text: "●", options: { color: YH } }, { text: " 김용현   ", options: { color: MUTED } }, { text: "●", options: { color: SJ } }, { text: " 박상진   ", options: { color: MUTED } }, { text: "●", options: { color: BOTH } }, { text: " 함께", options: { color: MUTED } }],
    { x: 6.9, y: 0.94, w: 2.6, h: 0.24, fontSize: 9.5, align: "right" });
  const steps = [
    ["지금 · v0.1.17", [[BOTH, "윈도우 · 맥 모두"], [BOTH, "제출 전 다듬기까지 동작"]]],
    ["발표 뒤 2주", [[YH, "다듬기 안내 · 고친 문장 수"], [YH, "Crossref API 연동 · 참고문헌 확인"], [YH, "수업 전 보완 (설치 · 보안)"], [SJ, "꺼진 동안 바뀐 글 · 타이핑 패턴"]]],
    ["12 ~ 13주", [[BOTH, "한글(hwpx) 문서 읽기"], [YH, "단어만 바꾼 문장 알림 (Kiwi)"], [BOTH, "테스트 중 나온 오류 고치기"], [BOTH, "AI 답 연결 정확도 높이기"]]],
    ["14주", [[BOTH, "최종 버전 배포"]]],
  ];
  const sw = 2.2, sg = 0.067;
  s.addShape(pres.shapes.LINE, { x: 0.6, y: 1.42, w: 8.8, h: 0, line: { color: LINE, width: 2 } });
  steps.forEach(([a, items], i) => {
    const x = 0.5 + i * (sw + sg), now = i === 0;
    s.addShape(pres.shapes.OVAL, { x: x + 0.02, y: 1.32, w: 0.2, h: 0.2, fill: { color: now ? ACCENT : "FFFFFF" }, line: { color: now ? ACCENT : MUTED, width: 1.5 } });
    T(s, a, { x, y: 1.58, w: sw, h: 0.26, fontSize: 12, bold: true, color: now ? ACCENT : INK });
    items.forEach(([c, t], k) => {
      const y = 1.86 + k * 0.19;
      if (!now) dot(x + 0.02, y + 0.06, c);
      T(s, t, { x: now ? x : x + 0.17, y, w: sw - 0.17, h: 0.19, fontSize: 9.5, color: now ? MUTED : INK, valign: "middle" });
    });
  });

  // ② 역할 분담 (R&R) — 두 사람 나란히
  head(0.5, 2.7, "역할 분담 (R&R)");
  const people = [
    ["김용현", YH, "서버 · 교수용 내역서 · 다듬기",
      ["Flask 서버 · 구글/카카오 로그인", "조작 확인 · 내역서 PDF · 교수 링크", "맥 버전 (다듬기 · ChatGPT 앱) · 배포"],
      ["다듬기 안내 · Crossref API 연동", "내역서에 고친 문장 수 표시", "수업 전 보완 (설치 · 보안 · 동의)"]],
    ["박상진", SJ, "화면 · 기록기 · 출처 잇기",
      ["기록기 · 크롬 확장 (Word · AI 앱 · 웹)", "출처 잇기: 문장 ↔ AI 답 연결", "학생 앱 화면 전부 · 제출 전 다듬기"],
      ["기록 밖 변경을 출처 보기 · 내역서에", "타이핑 패턴 (직접 쓰기 vs 옮겨 치기)", "한글(hwpx) 읽기 — 윈도우"]],
  ];
  people.forEach(([name, c, role, done, todo], i) => {
    const x = 0.5 + i * 2.62, y = 3.03, w = 2.5;
    card(s, x, y, w, 2.37, SOFT, "rr-" + name);
    s.addShape(pres.shapes.RECTANGLE, { x, y: y + 0.12, w: 0.06, h: 0.55, fill: { color: c }, line: { color: c } });
    T(s, name, { x: x + 0.18, y: y + 0.1, w: w - 0.3, h: 0.3, fontSize: 14, bold: true });
    T(s, role, { x: x + 0.18, y: y + 0.4, w: w - 0.3, h: 0.24, fontSize: 10.5, bold: true, color: c });
    const list = (y0, label, arr, mark) => {
      T(s, label, { x: x + 0.18, y: y0, w: w - 0.3, h: 0.2, fontSize: 9, bold: true, color: MUTED });
      T(s, arr.map((t, k) => ({ text: mark + " " + t, options: k < arr.length - 1 ? { breakLine: true } : {} })),
        { x: x + 0.18, y: y0 + 0.21, w: w - 0.26, h: 0.62, fontSize: 9.5, paraSpaceAfter: 2, valign: "top" });
    };
    list(y + 0.78, "한 것", done, "✓");
    list(y + 1.62, "할 것", todo, "→");
  });

  // ③ 예상 기술 문제 → 해결
  head(5.85, 2.7, "예상 기술 문제 → 해결");
  const probs = [
    ["AI 답을 완전히 다른 말로 바꾸면 못 찾는다", "몇 단어 고친 문장은 지금도 찾음 · 완전히 바꾼 건 \"출처 기록 없음\""],
    ["한글(HWP) 문서는 아직 못 읽는다", "새 한글 형식(hwpx) 읽기 추가 · 그전엔 Word · PDF로"],
    ["ChatGPT 앱 등이 바뀌면 대화를 못 읽는다", "새 버전마다 자동 시험 · 앱 안에서 바로 업데이트"],
    ["타이핑 패턴 연구는 영어 · 실험실 기준이다", "한글로 직접 쓰기 vs 옮겨 치기를 직접 시험"],
  ];
  probs.forEach(([p, f], i) => {
    const y = 3.03 + i * 0.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.85, y, w: 3.65, h: 0.54, rectRadius: 0.05, fill: { color: "FFFFFF" }, line: { color: LINE, width: 1 } });
    T(s, p, { x: 5.97, y: y + 0.05, w: 3.45, h: 0.24, fontSize: 10.5, bold: true, valign: "middle" });
    T(s, "→ " + f, { x: 5.97, y: y + 0.28, w: 3.45, h: 0.22, fontSize: 9.5, color: ACCENT, valign: "middle" });
  });
  s.addNotes([
    "마지막으로 개발 계획입니다. 지금 버전 0.1.17로 윈도우와 맥 모두 다듬기까지 돌아갑니다. 발표 후 2주 동안 저는 고쳐 쓰는 법 안내와 가짜 참고문헌 확인을, 상진이는 기록을 꺼 둔 동안 바뀐 글 표시와 타이핑 패턴을 만듭니다. 12 ~ 13주에 실제로 써 보며 고치고, 14주에 최종 버전을 냅니다.",
    "역할은 제가 서버와 다듬기, 상진이가 화면과 기록기입니다. 예상 문제 중 가장 큰 건 AI 답을 완전히 다른 말로 바꿔 쓰면 못 찾는 건데, 베꼈다고 단정하지 않고 '출처 기록 없음'으로 둡니다. (약 35초)",
    "",
    "그림 풀이 (물으면)",
    "· 다듬기 안내 = [인용 달기] · [다듬기] 버튼 옆에 따옴표 · 출처 다는 법, 바꿔 쓰기 세 단계를 띄움 (6장)",
    "· Crossref API 연동 · 참고문헌 확인 = Crossref(논문 DOI를 관리하는 비영리 기관)의 무료 공개 API에 과제 참고문헌 목록만 조회해 실제 있는 문헌인지 확인. 학생 본문은 안 나감",
    "· 고친 문장 수 = 제출 전에 학생이 다듬거나 인용을 단 문장 수 → 교수 내역서에 숫자로",
    "· 한글(HWP)? → 설문 34명 중 13명이 한글 사용. 지금은 Word · PDF만 읽음. 12 ~ 13주에 새 한글 형식(hwpx) 읽기 추가 — 함께: 맥은 김용현, 윈도우는 박상진. 그전엔 PDF로 내보내면 출처 보기는 되지만, 한글에서 직접 쓰는 과정(문서 변화) 기록은 Word에서만 됨.",
    "· 수업 전 보완 = 윈도우 설치 오류 · 서버 주소 주인 확인 · 해외 서버 동의 문구",
    "· 단어만 바꾼 문장 알림 (Kiwi) = 한국어 형태소 분석으로 어순 · 조사만 바뀐 문장을 '단어만 바뀜'으로 알려 줌",
    "· AI 답 연결 정확도 = 나중에 물어본 답에 글자가 겹쳐 잘못 이어지는 경우 등을 고침",
    "",
    "질문 대비",
    "· 바꿔 쓴 문장은 왜 지금 못 잡나? → 글자 조각이 AI 답과 꽤 겹치면 '고쳐 씀 · 보고 씀'으로 이미 이음. 글자가 거의 안 겹치면 뜻 비교(임베딩) 모델이 필요한데, 설치 파일이 커지고 엉뚱한 답에 잇는 오류가 늘어서 정확도를 확인한 뒤 넣음. 과제에선 완전히 자기 말로 쓰는 게 교수가 바라는 쪽이기도 함.",
    "· 수업 전 보완이 뭔가? → ① 윈도우 설치 후 안 열림 ② 서버 기록 읽기 주소 3개에 주인 확인 ③ 국외(싱가포르) 서버 이전 동의 문구.",
    "· 기록 꺼진 동안 바뀐 글? → 기록을 다시 켰을 때 저장 파일을 비교해서, 그사이 바뀐 문단을 따로 표시.",
    "· 타이핑 패턴 근거? → Crossley 외 (EDM 2024): 키 입력 기록으로 직접 쓴 글과 옮겨 친 글을 99% 구분. 다만 영어 · 실험 환경이라 한글은 우리가 직접 시험 (출처 장).",
    "· 타이핑 패턴? → \"4분 동안 2초 넘게 멈춘 적 없음 · 고친 횟수 0 · 한 번에 1,100자\" 같은 사실만 보여 줌. 판정하지 않음.",
    "· AI 답 연결 정확도? → 나중에 물어본 답에 글자가 겹쳐 잘못 이어지는 경우 — 붙여넣은 시각보다 뒤에 나온 답에는 잇지 않게.",
  ].join("\n"));
}

// ───────── 마무리 — 직접 확인 (QR) ─────────
{
  const s = pres.addSlide();
  s.background = { color: INK };
  s.addImage({ path: IMG + "app-icon.png", x: 0.6, y: 0.75, w: 0.62, h: 0.62 });
  T(s, "직접 확인해 보세요", { x: 1.38, y: 0.72, w: 6, h: 0.68, fontSize: 30, bold: true, color: "FFFFFF", valign: "middle" });
  T(s, "Trace는 지금 v0.1.17로 윈도우 · 맥에서 돌아갑니다", { x: 0.6, y: 1.5, w: 8, h: 0.3, fontSize: 13, color: "C9C8C3" });
  const qrs = [
    ["qr-demo.png", "교수 화면 데모", "설치 없이 바로 — 예시 내역서", "https://trace-server-8aa0.onrender.com/s/demo"],
    ["qr-download.png", "앱 내려받기", "윈도우 · 맥(Apple 칩) — 크롬 확장도", "https://trace-server-8aa0.onrender.com/download"],
  ];
  // QR 두 장 — 왼쪽 QR · 오른쪽 설명 (피그마 링크는 10장에만)
  qrs.forEach(([f, h, d, u], i) => {
    const x = 0.6 + i * 4.5, y = 2.2, w = 4.3, hh = 2.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: hh, rectRadius: 0.1, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" } });
    s.addImage({ path: IMG + f, x: x + 0.25, y: y + 0.3, w: 1.9, h: 1.9 });
    T(s, h, { x: x + 2.35, y: y + 0.45, w: 1.8, h: 0.34, fontSize: 17, bold: true });
    T(s, d.replace(" — ", "\n"), { x: x + 2.35, y: y + 0.85, w: 1.85, h: 0.6, fontSize: 10.5, color: MUTED, valign: "top" });
    T(s, [{ text: u.replace("https://", "").replace(".onrender.com", ".onrender.com\n"), options: { hyperlink: { url: u, tooltip: h } } }],
      { x: x + 2.35, y: y + 1.65, w: 1.85, h: 0.5, fontSize: 8.5, color: ACCENT, valign: "top" });
  });
  T(s, "첫 접속은 서버가 깨어나느라 30초쯤 걸릴 수 있어요", { x: 0.6, y: 4.82, w: 8.8, h: 0.24, fontSize: 9.5, color: "9B9A95" });
  T(s, "창의프로젝트1 · 1조 · 김용현 · 박상진", { x: 0.6, y: 5.25, w: 6, h: 0.24, fontSize: 10, color: "9B9A95" });
  s.addNotes("감사합니다. 교수 화면 데모는 설치 없이 QR로 바로 보실 수 있습니다. 질문 받겠습니다. (약 5초 · 발표 전에 데모 링크를 한 번 열어 서버를 깨워 두기)");
}

// ───────── 맨 뒤 · 자료 출처 (두 장) ─────────
{
  // 보이는 글자 = 그대로 복사해도 열리는 주소 · 눌러도 열림 (11/3 · 모두 열림 확인 · carnegie 는 브라우저로)
  const 출처 = [
    ["2장", "대교협 총장 설문 — 머니투데이, 「'AI로 과제 뚝딱'…골머리 앓는 대학들, 'AI 가이드라인' 속속 도입」 (2026.2.26)", "https://www.mt.co.kr/policy/2026/02/26/2026022610083850284"],
    ["2장", "명지대학교 생성형 AI 활용 가이드라인 (2026.8 제정)", "https://mju.ac.kr/mjukr/12491/subview.do"],
    ["2장", "고려대학교 인공지능 수업 가이드라인 (2025.9)", "https://ini.korea.ac.kr/assets/pdf/GenAIGuideline.pdf"],
    ["2장", "교육부 · 대교협 대학 AI 활용 윤리 가이드라인 — 교수신문, 「AI 윤리 '신호등' 세 개 섰다」 (2026.10.27)", "https://www.kyosu.net/news/articleView.html?idxno=211514"],
    ["2장", "연세대 중간고사 AI 집단 부정행위 — 뉴시스 (2025.11.10)", "https://mobile.newsis.com/view/NISX20251110_0003396613"],
    ["3장", "Trace 학생 설문 (2026.10.10 · 팀 자체 조사 · 응답 34명) — 폴더 안 「7-학생 설문 결과 34명」", "https://github.com/20233014-KYH/trace/tree/main/1-기획"],
    ["6장", "교육부 「연구윤리 확보를 위한 지침」 표절 정의 (출처 표시 없이 활용) — 명지대 연구윤리 안내", "https://www.mju.ac.kr/research/12477/subview.do"],
    ["6장", "카피킬러캠퍼스 사용자 매뉴얼 (기본 기준 6어절)", "https://lib.jnue.kr/lib/download/CopyKillerCampus_User_Manual.pdf"],
    ["6장", "연세대 연구윤리 FAQ (직접 인용은 큰따옴표로 표시)", "https://arch.yonsei.ac.kr/notice/download/7222/붙임4-1. 연구윤리FAQ_국문 (2).pdf?download=1"],
    ["6장", "Purdue OWL, Paraphrasing (바꿔 쓰기 절차)", "https://owl.purdue.edu/owl/research_and_citation/using_research/quoting_paraphrasing_and_summarizing/paraphrasing.html"],
    ["6장", "Barrón-Cedeño 외, 「Plagiarism Meets Paraphrasing」 (Computational Linguistics 2013)", "https://aclanthology.org/J13-4005/"],
    ["6장", "이민철, 「Kiwi: 통계적 언어 모델과 Skip-Bigram을 이용한 한국어 형태소 분석기 구현」 (한국디지털인문학회 2024)", "https://accesson.kr/kjdh/v.1/1/109/43508?lang=ko"],
    ["6장", "Walters · Wilder, 「Fabrication and errors in the bibliographic citations generated by ChatGPT」 (Scientific Reports 2023)", "https://doi.org/10.1038/s41598-023-41032-5"],
    ["6장", "Crossref REST API 문서 (query.bibliographic 로 참고문헌 찾기)", "https://www.crossref.org/documentation/retrieve-metadata/rest-api/"],
    ["6장", "Dee · Jacob, 「Rational Ignorance in Education: A Field Experiment in Student Plagiarism」 (J. Human Resources 2012)", "https://www.nber.org/papers/w15672"],
    ["6장", "Graham · Harris · Hebert, 「Informing Writing: The Benefits of Formative Assessment」 (Carnegie 2011)", "https://carnegie.org/publication/informing-writing-the-benefits-of-formative-assessment/"],
    ["11 ~ 13장", "Trace 코드 · DB 구조 · 릴리스 v0.1.17 (2026.11.2)", "https://github.com/20233014-KYH/trace"],
    ["13장", "Crossley 외, 직접 쓴 글과 옮겨 친 글의 키 입력 구분 (EDM 2024)", "https://www.educationaldatamining.org/EDM2024/proceedings/2024.EDM-short-papers.47/2024.EDM-short-papers.47.pdf"],
  ];
  [출처.slice(0, 9), 출처.slice(9)].forEach((쪽, pi) => {
    const s = pres.addSlide({ masterName: "TITLE_ONLY" });
    s.addText(`자료 출처 (${pi + 1}/2)`, { placeholder: "title" });
    쪽.forEach(([장, 무엇, 주소], i) => {
      const y = 1.0 + i * 0.47;
      T(s, 장, { x: 0.5, y, w: 0.85, h: 0.22, fontSize: 10, bold: true, color: ACCENT });
      T(s, 무엇, { x: 1.4, y, w: 8.1, h: 0.22, fontSize: 10.5 });
      T(s, [{ text: 주소, options: { hyperlink: { url: encodeURI(주소), tooltip: 주소 } } }], { x: 1.4, y: y + 0.21, w: 8.1, h: 0.2, fontSize: 9, color: MUTED });
    });
    s.addNotes("(발표하지 않는 장)");
  });
}

pres.writeFile({ fileName: out }).then(f => console.log("wrote", f));
