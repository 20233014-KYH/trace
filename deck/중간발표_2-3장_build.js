// 중간발표 2 · 3장 (문제 정의 · 인사이트) — 김용현
const pptxgen = require("pptxgenjs");
const out = process.argv[2];

const FONT = "Apple SD Gothic Neo";
const INK = "37352F", MUTED = "787774", LINE = "E3E2DE", SOFT = "F7F7F5";
const ACCENT = "1F5E8C", ACCENT_BG = "EAF1F7";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.title = "Trace 중간발표 — 문제 정의";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "TITLE_ONLY",
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.35, w: 9, h: 0.6,
      fontFace: FONT, fontSize: 26, bold: true, color: INK, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});

const T = (slide, text, o) => slide.addText(text, Object.assign({ isTextBox: true, fontFace: FONT, margin: 0, color: INK }, o));
const card = (slide, x, y, w, h, fill, name) =>
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name });

// ───────── 2장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("대학은 이미 AI 사용 공개를 요구한다", { placeholder: "title" });

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
    ["한양대 한 수업", "2026.10 · 수강생 전언", "GPT 질문 내역 전부 제출\n복붙하면 감점"],
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
    { text: "교수가 보고서와 대화 캡처를 한 줄씩 대조", options: { breakLine: true } },
    { text: "연세대 AI 집단 부정행위(2025.11)도 교수가 학생 영상을 돌려 보며 적발", options: { color: MUTED, fontSize: 12 } },
  ], { x: 2.3, y: 4.15, w: 7.0, h: 0.85, fontSize: 14, valign: "middle" });

  s.addNotes("가이드라인을 둔 대학 56곳 중 32곳이 과제에 AI 사용을 밝히라고 합니다. 명지대는 과제마다 대화 로그를 내야 하고, 한양대 한 수업은 복붙하면 감점입니다. 그런데 확인은 교수가 캡처를 한 줄씩 대조하는 게 전부입니다. (약 20초)");
}

// ───────── 3장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("학생 34명이 말해 준 것", { placeholder: "title" });

  const cw = 2.9, gap = 0.15, cy = 1.15, ch = 3.55, dh = 0.8;
  const cols = [
    { stats: [["20명", "\"어디까지 밝혀야 할지\n모르겠다\"", "밝히기 어려운 점 1위"]], decide: "기준이 없다\n→ 내역서가 기준 양식" },
    { stats: [["20명", "\"받는 쪽이 요구하면\"", "켜는 이유 1위"], ["15명", "\"감시받는 느낌\"", "꺼리는 이유 1위"]], decide: "교수가 요건으로 거는 길\n→ 원문은 학생 PC에" },
    { stats: [["15명", "\"AI 초안을 그대로 내기\"는\n쓰면 안 된다", "밝히면 된다 17명 · 그냥 내도 된다 2명"]], decide: "그대로 낸 곳을\n→ 제출 전 다듬기" },
  ];
  cols.forEach((c, i) => {
    const x = 0.5 + i * (cw + gap);
    card(s, x, cy, cw, ch, SOFT, "insight-" + i);
    let y = cy + 0.2;
    c.stats.forEach(([num, line, sub]) => {
      const two = c.stats.length > 1;
      T(s, num, { x: x + 0.2, y, w: cw - 0.4, h: two ? 0.5 : 0.65, fontSize: two ? 28 : 36, bold: true, color: ACCENT });
      y += two ? 0.52 : 0.7;
      const lh = line.includes("\n") ? 0.5 : 0.27;
      T(s, line, { x: x + 0.2, y, w: cw - 0.4, h: lh, fontSize: 14, bold: true });
      y += lh + 0.02;
      T(s, sub, { x: x + 0.2, y, w: cw - 0.4, h: 0.25, fontSize: 12, color: MUTED });
      y += two ? 0.32 : 0.3;
    });
    card(s, x + 0.15, cy + ch - dh - 0.15, cw - 0.3, dh, ACCENT_BG, "decide-" + i);
    T(s, c.decide, { x: x + 0.3, y: cy + ch - dh - 0.15, w: cw - 0.6, h: dh, fontSize: 14, bold: true, color: ACCENT, valign: "middle" });
  });

  T(s, "Trace 학생 설문 · 2026.10 · 34명 · 공학 · 컴퓨터 18명, 2학년 19명으로 치우침 → 경향만 봄",
    { x: 0.5, y: 4.9, w: 9, h: 0.25, fontSize: 10, color: MUTED });

  s.addNotes("학생 34명에게 물었더니, 가장 어려운 건 '어디까지 밝혀야 할지 모르겠다'였습니다. 켜는 이유 1위는 '요구하면', 꺼리는 이유 1위는 '감시받는 느낌'이었고, AI 초안을 그대로 내는 건 학생들도 안 된다고 봤습니다. 그래서 교수가 요구하는 길로, 원문은 PC에 두고, 제출 전에 다듬게 했습니다. (약 22초)");
}

pres.writeFile({ fileName: out }).then(f => console.log("wrote", f));
