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
      decide: "교수가 요구할 때 켜는 도구\n→ 원문은 학생 PC에만" },
    { stats: [["94%", "AI 초안을 그대로 내는 건?", "\"그냥 내면 안 된다\"", "밝히면 된다 50% · 쓰면 안 된다 44%"]],
      decide: "AI 답 그대로인 문장은\n→ 표시하고, 고칠 기회를" },
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

  s.addNotes("학생 설문에서 AI 사용을 밝힐 때 어려운 점을 물었더니 59%가 '어디까지 밝혀야 할지 모르겠다'고 했습니다. 이런 도구를 언제 켜겠냐는 질문엔 59%가 '받는 쪽이 요구하면', 꺼려지는 이유는 44%가 '감시받는 느낌'이었습니다. 그리고 AI 초안을 그냥 내도 된다는 학생은 6%뿐이었습니다. 그래서 교수가 요구할 때 켜는 도구로 만들고, 원문은 학생 PC에만 두고, AI 답을 그대로 넣은 문장은 교수에게 표시하되 제출 전에 학생이 고칠 기회를 주기로 했습니다. (약 25초)");
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
  T(s, [{ text: "학생 PC", options: { bold: true } }, { text: "  설치형 앱 · 윈도우 · 맥", options: { color: MUTED, fontSize: 10 } }], { x: 0.7, y: 1.2, w: 3.4, h: 0.3, fontSize: 14 });
  row(0.65, 1.55, 3.45, "FE", FE, "앱 화면", "기록 · 출처 보기 · 다듬기 · 제출");
  row(0.65, 2.27, 3.45, "BE", BE, "기록기 · 브라우저 확장", "AI 대화 · 복사/붙여넣기 · Word 글 · 키 횟수");
  row(0.65, 2.99, 3.45, "BE", BE, "출처 잇기 · 제출 전 다듬기", "보고서 문장 ↔ AI 답 연결");
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
    "Trace는 웹사이트가 아니라 학생 PC에 까는 데스크톱 앱입니다. 왼쪽 아래 '앱 구현'처럼, Python 프로그램 하나에 기록기와 화면을 묶었고, 화면은 앱 안에 HTML 창으로 띄웁니다. 윈도우는 exe, 맥은 dmg로 한 번 설치하면, 그 뒤 새 버전은 앱 안에서 바로 받습니다. 앱으로 만든 이유는 Word나 ChatGPT 앱처럼 브라우저 밖까지 읽어야 해서인데, 이건 운영체제마다 방법이 달라 윈도우는 COM과 UI Automation, 맥은 AppleScript와 손쉬운 사용 API로 따로 구현했습니다.",
    "학생 PC에서는 기록기와 크롬 확장이 AI 대화, 복사와 붙여넣기, Word 글 변화, 키 누른 횟수를 모으고, 출처 잇기가 보고서 문장을 AI 답과 이어 줍니다. 이 원문은 PC에만 저장됩니다.",
    "① 기록하는 동안 서버엔 글의 지문인 해시만 갑니다. ② 제출할 때 학생이 고른 원문만 오고, 서버가 해시를 다시 계산해 기록 때와 같은지 확인합니다. ③ 교수는 계정 없이 링크로 읽기만 합니다. (약 60초)",
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
    "· 설치가 번거롭지 않나? → exe/dmg 하나 · 자동 업데이트(서버 /api/app/latest). 설치 오류는 실제 수업 전에 먼저 고침 (11장).",
    "· 서버가 해외(싱가포르)인데? → 실제 수업 전에 국외 이전 동의 문구를 동의 화면에 넣음 (실제 수업 전 보완 · 11장).",
  ].join("\n"));
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
  box(5.1, 1.15, 1.95, 0.85, "sessions", "기록 한 번", "시작 · 끝 · 잠금 (조작 확인용)");
  box(7.4, 1.15, 2.1, 0.85, "events", "기록 이벤트", "종류 · 시각 · 원문 대신 해시");
  [[2.45, 2.8], [4.75, 5.1], [7.05, 7.4]].forEach(([a, b]) => { line(a, 1.42, b - a, 0, true); lab(a + 0.02, 1.16, "1 : N"); });

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
    ["checks", "제출 전 다듬기 · 새로", "고친 문장 수만 셈 · 원문 없음"],
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

  T(s, [{ text: "파랑 = 새로 더함", options: { color: MUTED } }, { text: "   그림에서 뺀 것: 로그인 보조 표 3개 (tokens · devices · login_tickets) · batches · contexts", options: { color: MUTED } }],
    { x: 0.5, y: 4.95, w: 9, h: 0.25, fontSize: 10 });
  s.addNotes([
    "DB는 Supabase의 PostgreSQL이고, 크게 두 줄기입니다.",
    "윗줄은 기록 줄기입니다. users, 학생 한 명이 works, 과제를 여러 개 갖고, 과제 하나에 sessions, 기록을 켠 한 번 한 번이 쌓이고, 그 안에 events, 기록 이벤트가 쌓입니다. 그래서 모두 1 대 N입니다. 이벤트에는 언제, 무슨 종류인지와 해시만 있고 글은 없습니다. sessions에는 해시 사슬의 처음과 끝, 그리고 기록을 끝낼 때 봉인한 시각이 남아서, 나중에 이벤트가 빠지거나 바뀌었는지 확인할 수 있습니다.",
    "아랫줄은 제출 줄기입니다. 과제 하나로 statements, 내역서를 만듭니다. 내역서에는 요약 숫자와 학생이 직접 쓰는 설명 두 개, 'AI를 어디에 썼나', '어떻게 확인했나'가 들어갑니다.",
    "내역서 하나에 표 다섯 개가 붙습니다. messages는 학생이 고른 질문과 답 원문인데, 서버에 원문이 있는 곳은 여기 하나뿐이고 해시로 확인된 것만 들어옵니다. links는 '이 문장은 이 AI 답에서 왔다, 아니다'라는 학생의 결정, redactions는 학생이 가린 기록인데 어느 기록인지만 남고 내용은 안 옵니다. shares는 교수 링크로, 만료일이 있고 학생이 끊을 수 있습니다.",
    "지금 테이블에 새로 더하는 건 파랑 두 가지뿐입니다. checks는 제출 전 다듬기 결과를 세는 표로, 학생이 몇 문장을 직접 고쳤는지, 숫자만 남겨서 교수 내역서에 '제출 전에 몇 문장 고침'으로 보입니다. 원문은 남기지 않습니다. retain_until은 내역서를 언제까지 둘지, 예를 들어 성적 이의 신청 기간까지로 정하는 칸입니다. (약 50초)",
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
  const YH = ACCENT, SJ = "2E7D5B", BOTH = MUTED;
  const head = (x, y, t) => T(s, t, { x, y, w: 4, h: 0.28, fontSize: 13, bold: true });
  const dot = (x, y, c) => s.addShape(pres.shapes.OVAL, { x, y, w: 0.1, h: 0.1, fill: { color: c }, line: { color: c } });

  // ① 구현 일정 — 칸마다 할 일 · 점 색 = 맡은 사람
  head(0.5, 0.92, "구현 일정");
  T(s, [{ text: "●", options: { color: YH } }, { text: " 김용현   ", options: { color: MUTED } }, { text: "●", options: { color: SJ } }, { text: " 박상진   ", options: { color: MUTED } }, { text: "●", options: { color: BOTH } }, { text: " 함께", options: { color: MUTED } }],
    { x: 6.9, y: 0.94, w: 2.6, h: 0.24, fontSize: 9.5, align: "right" });
  const steps = [
    ["지금 · v0.1.17", [[BOTH, "윈도우 · 맥 모두"], [BOTH, "제출 전 다듬기까지 동작"]]],
    ["발표 뒤 2주", [[YH, "내역서에 고친 문장 수 표시"], [YH, "수업 전 보완 (설치 · 보안)"], [SJ, "기록 꺼진 동안 바뀐 글 표시"], [SJ, "타이핑 패턴 보기"]]],
    ["12 ~ 13주", [[BOTH, "테스트 중 나온 오류 고치기"], [BOTH, "AI 답 연결 정확도 높이기"]]],
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
      ["Flask 서버 · 구글/카카오 로그인", "조작 확인 · 내역서 PDF · 교수 링크", "제출 전 다듬기 · 맥 버전"],
      ["내역서에 고친 문장 수 표시", "수업 전 보완 (설치 · 보안 · 동의)"]],
    ["박상진", SJ, "화면 · 기록기 · 확장",
      ["윈도우 기록기 (Word · AI 앱)", "크롬 확장 (ChatGPT · Claude · Gemini)", "화면 디자인 반영"],
      ["기록 꺼진 동안 바뀐 글 표시", "타이핑 패턴 (직접 쓰기 vs 옮겨 치기)"]],
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
    ["바꿔 쓴 문장은 어느 AI 답인지 못 찾는다", "\"출처 기록 없음\"으로 두고, 베꼈다고 단정 안 함"],
    ["ChatGPT 앱 등이 바뀌면 대화를 못 읽는다", "새 버전마다 자동 시험 · 앱 안에서 바로 업데이트"],
    ["윈도우에서 설치 후 안 열리는 PC가 있다", "실제 수업 전에 먼저 고침"],
    ["타이핑 패턴 연구는 영어 · 실험실 기준이다", "한글로 직접 쓰기 vs 옮겨 치기를 우리가 시험"],
  ];
  probs.forEach(([p, f], i) => {
    const y = 3.03 + i * 0.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.85, y, w: 3.65, h: 0.55, rectRadius: 0.05, fill: { color: "FFFFFF" }, line: { color: LINE, width: 1 } });
    T(s, p, { x: 5.97, y: y + 0.05, w: 3.45, h: 0.24, fontSize: 10.5, bold: true, valign: "middle" });
    T(s, "→ " + f, { x: 5.97, y: y + 0.28, w: 3.45, h: 0.22, fontSize: 9.5, color: ACCENT, valign: "middle" });
  });
  s.addNotes([
    "구현 일정입니다. 지금 v0.1.17로 윈도우와 맥 모두 제출 전 다듬기까지 동작합니다. 발표 뒤 2주 동안 저는 학생이 제출 전에 몇 문장을 고쳤는지 교수 내역서에 보이게 하고, 실제 수업에 쓰기 전에 설치 오류와 보안을 보완합니다. 상진이는 기록을 꺼 둔 동안 바뀐 글을 따로 표시하고, 직접 쓴 글과 옮겨 친 글의 타이핑 패턴을 보이게 합니다. 12 ~ 13주에는 테스트에서 나온 오류를 고치고, 14주에 최종 버전을 냅니다.",
    "역할은 제가 서버와 교수용 내역서, 다듬기를, 상진이가 화면과 기록기, 크롬 확장을 맡습니다.",
    "예상 기술 문제 중 가장 큰 건, AI 답을 말을 다 바꿔 쓰면 어느 답에서 왔는지 못 찾는다는 겁니다. 이건 베꼈다고 단정하지 않고 '출처 기록 없음'으로 둡니다. 또 ChatGPT 앱이 업데이트되면 대화를 못 읽을 수 있는데, 실제로 이번 주에 한 번 겪어서, 새 버전마다 자동 시험을 돌리고 앱 안 업데이트로 바로 고쳤습니다. (약 45초)",
    "",
    "질문 대비",
    "· 수업 전 보완이 뭔가? → ① 윈도우 설치 후 안 열림 ② 서버 기록 읽기 주소 3개에 주인 확인 ③ 국외(싱가포르) 서버 이전 동의 문구.",
    "· 기록 꺼진 동안 바뀐 글? → 기록을 다시 켰을 때 저장 파일을 비교해서, 그사이 바뀐 문단을 따로 표시.",
    "· 타이핑 패턴? → \"4분 동안 2초 넘게 멈춘 적 없음 · 고친 횟수 0 · 한 번에 1,100자\" 같은 사실만 보여 줌. 판정하지 않음.",
    "· AI 답 연결 정확도? → 나중에 물어본 답에 글자가 겹쳐 잘못 이어지는 경우 — 붙여넣은 시각보다 뒤에 나온 답에는 잇지 않게.",
  ].join("\n"));
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
