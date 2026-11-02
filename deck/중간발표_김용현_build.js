// 중간발표 2 · 3장 (문제 정의 · 인사이트) — 김용현
const pptxgen = require("pptxgenjs");
const out = process.argv[2];

const FONT = "Apple SD Gothic Neo";
const INK = "37352F", MUTED = "787774", LINE = "E3E2DE", SOFT = "F7F7F5";
const ACCENT = "1F5E8C", ACCENT_BG = "EAF1F7";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.title = "Trace 중간발표 — 김용현 장";
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

// ───────── 1장 표지 ─────────
{
  const s = pres.addSlide();
  s.background = { color: INK };
  T(s, "Trace", { x: 0.6, y: 1.35, w: 6, h: 0.9, fontSize: 54, bold: true, color: "FFFFFF", objectName: "cover-title" });
  T(s, "AI 사용 내역 공개, 손 대신 기록으로", { x: 0.6, y: 2.25, w: 7, h: 0.5, fontSize: 24, color: "FFFFFF" });
  T(s, "AI 답과 참고한 글을 어떻게 썼는지 기록하고,\n제출 전에 그대로 가져온 곳을 학생이 다듬게 한 뒤,\n교수에게 한 장으로 공개합니다.",
    { x: 0.6, y: 2.95, w: 6.6, h: 0.95, fontSize: 13, color: "C9C8C3" });
  T(s, "창의프로젝트1 · 중간 설계 발표 · 김용현 · 박상진", { x: 0.6, y: 4.65, w: 6.5, h: 0.3, fontSize: 12, color: "C9C8C3" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.75, y: 3.2, w: 1.6, h: 1.6, rectRadius: 0.08, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" }, objectName: "qr-slot" });
  T(s, "피그마 QR\n(링크 받으면\n바꾸기)", { x: 7.75, y: 3.2, w: 1.6, h: 1.6, fontSize: 11, color: MUTED, align: "center", valign: "middle" });
  T(s, "프로토타입", { x: 7.75, y: 4.85, w: 1.6, h: 0.25, fontSize: 10, color: "C9C8C3", align: "center" });
  s.addNotes("AI를 허용하는 수업에서, 대화 내역 제출을 대신하는 Trace입니다. (약 10초)");
}

// ───────── 2장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("문제 정의: 대학은 이미 AI 사용 공개를 요구한다", { placeholder: "title" });

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
    { text: "교수가 보고서와 대화 캡처를 한 줄씩 대조", options: { breakLine: true } },
    { text: "연세대 AI 집단 부정행위(2025.11)도 교수가 학생 영상을 돌려 보며 적발", options: { color: MUTED, fontSize: 12 } },
  ], { x: 2.3, y: 4.15, w: 7.0, h: 0.85, fontSize: 14, valign: "middle" });

  s.addNotes("가이드라인을 둔 대학 56곳 중 32곳이 과제에 AI 사용을 밝히라고 합니다. 명지대는 과제마다 대화 로그를 내야 하고, 고려대는 AI 출력을 고치지 않고 그대로 넣는 걸 금지합니다. 그런데 확인은 교수가 캡처를 한 줄씩 대조하는 게 전부입니다. (약 20초)");
}

// ───────── 3장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("인사이트: 학생은 기준을 모르고, 감시를 걱정한다", { placeholder: "title" });

  // 칸마다 Q(실제 설문 문항) · A(고른 답) — "59% 가 무엇을 고른 59% 인지" 바로 보이게 (11/2 김용현 안)
  const cw = 2.9, gap = 0.15, cy = 1.15, ch = 3.55, dh = 0.75;
  const cols = [
    { stats: [["59%", "AI 사용을 밝힐 때 어려운 점은?", "\"어디까지 밝혀야 할지\n모르겠다\"", "1위 · 여러 개 고름"]],
      decide: "기준이 없다\n→ 내역서가 기준 양식" },
    { stats: [["59%", "이런 도구, 언제 켜겠나요?", "\"받는 쪽이 요구하면\"", ""], ["44%", "켜기 꺼려지는 이유는?", "\"감시받는 느낌\"", ""]],
      decide: "교수가 요건으로 거는 길\n→ 원문은 학생 PC에" },
    { stats: [["94%", "AI 초안을 그대로 내는 건?", "\"그냥 내면 안 된다\"", "밝히면 된다 50% · 쓰면 안 된다 44%"]],
      decide: "그대로 낸 곳은\n→ 공개하고, 다듬게" },
  ];
  cols.forEach((c, i) => {
    const x = 0.5 + i * (cw + gap), two = c.stats.length > 1;
    card(s, x, cy, cw, ch, SOFT, "insight-" + i);
    let y = cy + 0.18;
    c.stats.forEach(([num, q, a, sub]) => {
      T(s, num, { x: x + 0.2, y, w: cw - 0.4, h: two ? 0.45 : 0.62, fontSize: two ? 26 : 36, bold: true, color: ACCENT });
      y += two ? 0.47 : 0.68;
      T(s, [{ text: "Q.  ", options: { bold: true, color: ACCENT } }, { text: q, options: { color: MUTED } }],
        { x: x + 0.2, y, w: cw - 0.4, h: 0.24, fontSize: 11 });
      y += 0.26;
      const ah = a.includes("\n") ? 0.48 : 0.27;          // 두 줄 답은 둘째 줄을 A. 뒤에 맞춤
      T(s, [{ text: "A.  ", options: { bold: true, color: ACCENT } }, { text: a.replace("\n", "\n      "), options: { bold: true } }],
        { x: x + 0.2, y, w: cw - 0.4, h: ah, fontSize: 13, valign: "top" });
      y += ah + 0.03;
      if (sub) { T(s, sub, { x: x + 0.2, y, w: cw - 0.4, h: 0.22, fontSize: 10, color: MUTED }); y += 0.25; }
      y += two ? 0.12 : 0.05;
    });
    card(s, x + 0.15, cy + ch - dh - 0.15, cw - 0.3, dh, ACCENT_BG, "decide-" + i);
    T(s, c.decide, { x: x + 0.3, y: cy + ch - dh - 0.15, w: cw - 0.6, h: dh, fontSize: 14, bold: true, color: ACCENT, valign: "middle" });
  });

  T(s, "Trace 학생 설문 2026.10 · 응답 34명 · 59% = 20명 · 44% = 15명 · 94% = 32명 · 공학·컴퓨터 18명, 2학년 19명으로 치우침 → 경향만",
    { x: 0.5, y: 4.9, w: 9, h: 0.25, fontSize: 10, color: MUTED });

  s.addNotes("학생 설문에서 AI 사용을 밝힐 때 어려운 점을 물었더니 59%가 '어디까지 밝혀야 할지 모르겠다'고 했습니다. 이런 도구를 언제 켜겠냐는 질문엔 59%가 '받는 쪽이 요구하면', 꺼려지는 이유는 44%가 '감시받는 느낌'이었습니다. 그리고 AI 초안을 그냥 내도 된다는 학생은 6%뿐이었습니다. 그래서 교수가 요구하는 길로, 원문은 PC에 두고, 그대로 낸 곳은 공개하고 다듬게 했습니다. (약 25초)");
}

// ───────── 9장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("시스템 설계: 원문은 학생 PC에 남는다", { placeholder: "title" });
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
  T(s, [{ text: "학생 PC", options: { bold: true } }, { text: "  윈도우 · 맥 · Python", options: { color: MUTED, fontSize: 10 } }], { x: 0.7, y: 1.2, w: 3.4, h: 0.3, fontSize: 14 });
  row(0.65, 1.55, 3.45, "FE", FE, "앱 화면", "기록 · 출처 보기 · 다듬기 · 제출 (pywebview)");
  row(0.65, 2.27, 3.45, "BE", BE, "기록기 · 브라우저 확장", "AI 대화 · 복사/붙여넣기 · Word 변화 · 키 횟수");
  row(0.65, 2.99, 3.45, "BE", BE, "출처 잇기 · 제출 전 다듬기", "문장 ↔ AI 답 연결 (core/match.py)");
  row(0.65, 3.71, 3.45, "DB", DB, "원문 보관 — PC에만", "AI 답 · 학생 글 원문 (개인정보 먼저 가림)", true);
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
  T(s, "해시 · 내역서 · 링크\n원문 없음", { x: 5.56, y: 3.95, w: 1.8, h: 0.5, fontSize: 10, color: MUTED });
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
  // 흐름 설명
  const flows = [["1", "기록 중", "서버엔 해시만"], ["2", "제출 때", "학생이 고른 원문만 · 서버가 해시로 조작 확인"], ["3", "교수", "비밀 링크로 읽기만"]];
  const fw = [2.2, 4.3, 2.3]; let fx = 0.5;
  flows.forEach(([n, a, b], i) => {
    num(fx, 4.78, n);
    T(s, [{ text: a + "  ", options: { bold: true } }, { text: b, options: { color: MUTED } }], { x: fx + 0.36, y: 4.75, w: fw[i] - 0.4, h: 0.34, fontSize: 11, valign: "middle" });
    fx += fw[i] + 0.1;
  });
  s.addNotes("AI 답과 학생 글의 원문은 기록하는 순간 학생 PC에만 저장됩니다. 서버에는 해시만 가고, 제출할 때 학생이 고른 원문이 오면 서버가 해시로 다시 계산해 바뀐 게 없는지 확인합니다. 교수는 계정 없이 링크로 읽기만 합니다. (약 25초)\n\n질문 대비: 해시 = 글의 지문, 원문 없이도 나중에 온 글이 기록 때와 같은지 확인. 서버가 해외(싱가포르) → 실제 수업 전 국외 이전 동의 문구.");
}

// ───────── 10장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("DB 설계: 지금 테이블에 2가지만 더한다", { placeholder: "title" });
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

  // 줄기: 학생 → 과제 → 기록 한 번 → 기록 이벤트
  box(0.5, 1.15, 1.95, 0.85, "users", "학생", "이메일 · 구글/카카오 계정 번호");
  box(2.8, 1.15, 1.95, 0.85, "works", "과제", "제목 · 허용 범위 메모");
  box(5.1, 1.15, 1.95, 0.85, "sessions", "기록 한 번", "해시 사슬 처음 · 끝 · 봉인");
  box(7.4, 1.15, 2.1, 0.85, "events", "기록 이벤트", "종류 · 시각 · 원문 대신 해시");
  [[2.45, 2.8], [4.75, 5.1], [7.05, 7.4]].forEach(([a, b]) => { line(a, 1.42, b - a, 0, true); lab(a + 0.02, 1.16, "1 : N"); });

  // 다음 단계: 모아 보기
  box(0.5, 2.55, 1.95, 0.85, "assignments", "", "30명 모아 보기 · 다음 단계", { next: true });
  line(2.45, 2.97, 0.17, 0, false, { dash: true, color: MUTED });
  line(2.62, 1.8, 0, 1.17, false, { dash: true, color: MUTED });
  line(2.62, 1.8, 0.18, 0, true, { dash: true, color: MUTED });

  // 과제 → 내역서
  line(3.775, 2.0, 0, 0.55, true); lab(3.85, 2.15, "1 : N");
  box(2.8, 2.55, 2.35, 1.6, "statements", "내역서", "요약 숫자 · 학생 설명 두 개\n원문이 기록과 맞는지");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.92, y: 3.6, w: 2.11, h: 0.42, rectRadius: 0.05, fill: { color: ACCENT_BG }, line: { color: NEW, width: 1 } });
  T(s, [{ text: "retain_until  ", options: { bold: true } }, { text: "보관 기간 · 새로" }], { x: 3.02, y: 3.6, w: 2.0, h: 0.42, fontSize: 11, color: NEW, valign: "middle" });

  // 내역서 → 딸린 표 5개
  const kids = [
    ["messages", "보여 준 원문", "학생이 고른 질문 · 답만 · 해시로 확인"],
    ["links", "출처 결정", "이 문장 ← 이 AI 답 (맞다 / 아니다)"],
    ["redactions", "가린 것", "어느 기록인지만 · 내용은 안 옴"],
    ["shares", "교수 링크", "토큰 · 만료 · 학생이 끊을 수 있음"],
    ["checks", "제출 전 다듬기 · 새로", "처리 → \"다듬음 N\" · 원문 없음"],
  ];
  const kx = 5.65, kw = 3.85, kh = 0.4, kg = 0.08, ky0 = 2.4;
  line(5.15, 3.35, 0.3, 0, false); lab(5.17, 3.1, "1 : N");
  line(5.45, ky0 + kh / 2, 0, (kids.length - 1) * (kh + kg), false);
  kids.forEach(([n, ko, sub], i) => {
    const y = ky0 + i * (kh + kg), isNew = n === "checks";
    line(5.45, y + kh / 2, kx - 5.45, 0, true, { color: isNew ? NEW : INK });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: kx, y, w: kw, h: kh, rectRadius: 0.05, fill: { color: isNew ? ACCENT_BG : "FFFFFF" }, line: { color: isNew ? NEW : LINE, width: isNew ? 1.5 : 1 } });
    T(s, [{ text: n + "  ", options: { bold: true, color: isNew ? NEW : INK } }, { text: ko + "   ", options: { color: isNew ? NEW : INK } }, { text: sub, options: { color: MUTED, fontSize: 9.5 } }],
      { x: kx + 0.12, y, w: kw - 0.2, h: kh, fontSize: 11, valign: "middle" });
  });

  T(s, [{ text: "파랑 = 새로 더함 · 점선 = 다음 단계", options: { color: MUTED } }, { text: "   그림에서 뺀 것: 로그인 보조 표 3개 (tokens · devices · login_tickets) · batches · contexts", options: { color: MUTED } }],
    { x: 0.5, y: 4.95, w: 9, h: 0.25, fontSize: 10 });
  s.addNotes("학생 아래 과제, 과제 아래 기록이 쌓이는데, 기록 이벤트에는 원문 대신 해시만 있습니다. 학생이 내역서를 만들면 그때 고른 원문, 출처 결정, 가린 것, 교수 링크가 내역서에 붙습니다. 여기에 다듬기 결과를 세는 checks와 보관 기간 두 가지만 더하면 됩니다. 30명 모아 보기는 다음 단계입니다. (약 25초)\n\n질문 대비: 토큰을 JWT 말고 DB에 둔 이유 = 학생 기록이라 '이 기기 연결 끊기'가 돼야 함 (server/db.py). 교수가 원문을 어떻게 보나 = 학생이 고른 질문·답만 messages에 오고 서버가 해시로 확인. 가린 건 = 어느 기록인지만 남고 내용은 안 옴.");
}

// ───────── 11장 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("개발 계획: 이미 돌아가는 것 위에 더한다", { placeholder: "title" });
  // 일정
  const steps = [["지금 · 11/1", "v0.1.14\n다듬기까지 돌아감"], ["발표 뒤 2주", "다듬음 N · 내역서 한 줄\n실제 수업 전 필수 3개"], ["12주", "실제 학생 · 교수\n사용 테스트"], ["13주", "테스트 결과로\n고치기"], ["14주", "최종 발표"]];
  const sw = 1.7, sg = 0.125;
  s.addShape(pres.shapes.LINE, { x: 0.6, y: 1.32, w: 8.8, h: 0, line: { color: LINE, width: 2 } });
  steps.forEach(([a, b], i) => {
    const x = 0.5 + i * (sw + sg), now = i === 0;
    s.addShape(pres.shapes.OVAL, { x: x + 0.02, y: 1.22, w: 0.2, h: 0.2, fill: { color: now ? ACCENT : "FFFFFF" }, line: { color: now ? ACCENT : MUTED, width: 1.5 } });
    T(s, a, { x, y: 1.5, w: sw, h: 0.26, fontSize: 12, bold: true, color: now ? ACCENT : INK });
    T(s, b, { x, y: 1.78, w: sw, h: 0.48, fontSize: 10, color: MUTED, valign: "top" });
  });
  // 지금 돌아가는 것 + 역할
  card(s, 0.5, 2.5, 3.55, 2.3, SOFT, "now");
  T(s, "지금 돌아가는 것", { x: 0.7, y: 2.6, w: 3.2, h: 0.3, fontSize: 14, bold: true });
  T(s, [
    { text: "✓ 윈도우 · 맥 기록기 · 크롬 확장", options: { breakLine: true } },
    { text: "✓ 출처 잇기 · 해시 사슬 · 서버", options: { breakLine: true } },
    { text: "✓ 내역서 PDF · 교수 링크 · 로그인", options: { breakLine: true } },
    { text: "✓ 제출 전 다듬기 (11/1)", options: { bold: true, color: ACCENT } },
  ], { x: 0.7, y: 2.95, w: 3.25, h: 1.1, fontSize: 12, paraSpaceAfter: 3, valign: "top" });
  T(s, [
    { text: "김용현  ", options: { bold: true } }, { text: "서버 · 교수 화면 · 다듬기", options: { color: MUTED, breakLine: true } },
    { text: "박상진  ", options: { bold: true } }, { text: "기록기 · 확장 · 작성 모양", options: { color: MUTED } },
  ], { x: 0.7, y: 4.15, w: 3.25, h: 0.55, fontSize: 11, valign: "top" });
  // 예상 문제 → 해결
  T(s, "예상 문제 → 해결", { x: 4.3, y: 2.55, w: 5.2, h: 0.3, fontSize: 14, bold: true });
  const probs = [
    ["말을 다 바꿔 쓴 문장은 출처를 못 잇는다", "\"출처 기록 없음\"으로 둠 · 단정 안 함"],
    ["작성 모양 연구는 영어 · 실험실 결과", "한글로 직접 쓰기 vs 옮겨 치기를 시험"],
    ["설치 오류 · 서버 주인 확인 · 해외 서버", "실제 수업 전 필수 3개로 고침"],
    ["\"감시받는 느낌\" (설문 44%)", "동의 화면 · 원문은 PC에 · 언제든 멈춤"],
  ];
  probs.forEach(([p, f], i) => {
    const y = 2.92 + i * 0.47;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.3, y, w: 5.2, h: 0.4, rectRadius: 0.05, fill: { color: "FFFFFF" }, line: { color: LINE, width: 1 } });
    T(s, p, { x: 4.42, y, w: 2.75, h: 0.4, fontSize: 10.5, bold: true, valign: "middle" });
    T(s, "→ " + f, { x: 7.2, y, w: 2.25, h: 0.4, fontSize: 10, color: ACCENT, valign: "middle" });
  });
  s.addNotes("기록, 출처 잇기, 내역서까지 이미 동작하고, 이번 주에 제출 전 다듬기도 들어갔습니다. 발표 뒤 2주는 다듬은 수 세기와 실제 수업 전에 꼭 고칠 세 가지, 12주에는 실제 학생과 교수에게 써 보게 합니다. 가장 큰 한계는 말을 다 바꿔 쓴 문장인데, 이건 '직접 썼다'고 단정하지 않고 '출처 기록 없음'으로 둡니다. (약 30초)");
}

// ───────── 맨 뒤 · 자료 출처 ─────────
{
  const s = pres.addSlide({ masterName: "TITLE_ONLY" });
  s.addText("자료 출처", { placeholder: "title" });
  // 보이는 글자 = 그대로 복사해도 열리는 주소 · 눌러도 열림 (11/2 · 모두 200 확인)
  const 출처 = [
    ["2장", "대교협 총장 설문 — 머니투데이, 「'AI로 과제 뚝딱'…골머리 앓는 대학들, 'AI 가이드라인' 속속 도입」 (2026.2.26)", "https://www.mt.co.kr/policy/2026/02/26/2026022610083850284"],
    ["2장", "명지대학교 생성형 AI 활용 가이드라인 (2026.8 제정)", "https://mju.ac.kr/mjukr/12491/subview.do"],
    ["2장", "고려대학교 인공지능 수업 가이드라인 (2025.9)", "https://ini.korea.ac.kr/assets/pdf/GenAIGuideline.pdf"],
    ["2장", "교육부 · 대교협 대학 AI 활용 윤리 가이드라인 — 교수신문, 「AI 윤리 '신호등' 세 개 섰다」 (2026.10.27)", "https://www.kyosu.net/news/articleView.html?idxno=211514"],
    ["2장", "연세대 중간고사 AI 집단 부정행위 — 뉴시스 (2025.11.10)", "https://mobile.newsis.com/view/NISX20251110_0003396613"],
    ["3장", "Trace 학생 설문 (2026.10.10 · 팀 자체 조사 · 응답 34명) — 폴더 안 「7-학생 설문 결과 34명」", "https://github.com/20233014-KYH/trace/tree/main/1-기획"],
    ["다듬기", "교육부 「연구윤리 확보를 위한 지침」 표절 정의 (출처 표시 없이 활용) — 명지대 연구윤리 안내", "https://www.mju.ac.kr/research/12477/subview.do"],
    ["9 ~ 11장", "Trace 코드 · DB 구조 · 릴리스 v0.1.17 (2026.11.2)", "https://github.com/20233014-KYH/trace"],
  ];
  출처.forEach(([장, 무엇, 주소], i) => {
    const y = 1.05 + i * 0.47;
    T(s, 장, { x: 0.5, y, w: 0.85, h: 0.22, fontSize: 10, bold: true, color: ACCENT });
    T(s, 무엇, { x: 1.4, y, w: 8.1, h: 0.22, fontSize: 10.5 });
    T(s, [{ text: 주소, options: { hyperlink: { url: encodeURI(주소), tooltip: 주소 } } }], { x: 1.4, y: y + 0.21, w: 8.1, h: 0.2, fontSize: 10, color: MUTED });
  });
  s.addNotes("(발표하지 않는 장) 4 ~ 8장(박상진)에 쓴 자료가 있으면 여기 더하기.");
}

pres.writeFile({ fileName: out }).then(f => console.log("wrote", f));
