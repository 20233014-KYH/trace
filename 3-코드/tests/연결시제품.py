"""
연결시제품.py — 결과물(Word) 문장 ↔ AI 답 연결 시제품 + 시험. pytest 없이 그냥 실행.

  python tests/연결시제품.py                      # 시험 두 개를 다 돌림 → 정답과 비교 → 색칠한 HTML 두 장
  python tests/연결시제품.py --case match_rec      # 하나만
  python tests/연결시제품.py --docx 내보고서.docx  # 이미 있는 Word 파일로 (과정 기록·정답 비교 없음)

시험 (tests/fixtures/<case>):
  match      만든 보고서 · 글자 비교만 (과정 기록 없음) — 실제 ChatGPT 답 3개 · 문장 12개 · 기준을 이 자료로 맞춤
  match3     세 번째 · 경제 · 실제 ChatGPT 답 3개 · 문장 14개 — 0.35 → 0.30 확인용 (같은 주제 직접 쓴 문장 3 · 많이 고친 문장 4)
  match_rec  녹화 시험 · 실제 기록기 + 실제 ChatGPT 답 2개 + 실제 Word — 복사·붙여넣기 기록으로 "고침 / 보고 씀" 을 가름
             기준을 손대지 않고 처음 돌린 결과를 그대로 낸다 (새 자료 확인용)
  각 폴더: ai_answers.jsonl · report_truth.json · (있으면) report.docx · events.jsonl · context.jsonl

색 (10/5 결정): 그대로 = 빨강 · 붙여넣고 고침 = 파랑 · AI 답 보고 씀 = 보라 · 출처 기록 없음 = 연두.
[글자로 표시] 버튼으로 글자 라벨도 볼 수 있다 (적록 색약). 점수는 화면에 내지 않는다 (원칙 1).
이 화면은 "제안" — 실제 서비스에선 학생이 맞다/아니다를 고른다.

Word 파일은 파이썬 기본 기능(zipfile)으로 쓰고 읽는다 — 설치할 것 없음.
"""
import argparse
import html
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import match as M          # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
CASES = ["match", "match_rec", "match3", "match_mix"]
LABEL = {"exact": "그대로", "edited": "고침", "viewed": "보고 씀", "none": "기록 없음"}


# ───────────── Word (.docx) 쓰기·읽기 — zipfile 만 ─────────────
def write_docx(path, title, paragraphs):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = f'<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>{esc(title)}</w:t></w:r></w:p>'
    body += "".join(f'<w:p><w:r><w:t xml:space="preserve">{esc(p)}</w:t></w:r></w:p>' for p in paragraphs)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + body + '</w:body></w:document>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", doc)


def read_docx(path):
    """→ [(style, text)] 문단마다. Word 가 글자를 여러 조각(run)으로 나눠 저장해도 이어 붙인다."""
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>|<w:p/>", x, re.S):
        style = (re.search(r'<w:pStyle w:val="([^"]+)"', p) or [None, ""])[1]
        p = re.sub(r"<w:tab/>", "\t", p)
        p = re.sub(r"<w:br/>", "\n", p)
        text = html.unescape("".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", p, re.S)))
        if text.strip():
            out.append((style, text.strip()))
    return out


# ───────────── 색칠한 화면 (HTML 한 장) ─────────────
def render(path, title, linked, answers, rec=False):
    data = {"title": title, "paras": linked, "answers": {a["id"]: a for a in answers},
            "rec": any(s.get("paste") is not None for p in linked for s in p) or rec}
    for para in data["paras"]:
        for s in para:
            for k in [k for k in s if k.startswith("_")]:
                del s[k]                     # 점수는 화면으로 보내지 않는다
    counts = {k: sum(s["label"] == k for p in linked for s in p) for k in LABEL}
    page = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__N_EXACT__", str(counts["exact"])).replace("__N_EDITED__", str(counts["edited"])).replace("__N_NONE__", str(counts["none"])).replace("__N_VIEWED__", str(counts["viewed"]))
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>결과물 출처 보기</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/variable/pretendardvariable.min.css">
<style>
:root{--ink:#18191b;--sub:#5f6368;--faint:#9aa0a6;--line:#ececee;--bg:#f6f6f7;--paper:#fff;--well:#f6f6f7;
  --exact:#e5484d;--exact-t:#fdecec;--exact-s:#f9d3d4;
  --edited:#3e63dd;--edited-t:#eaf0fd;--edited-s:#d3defa;
  --viewed:#8e4ec6;--viewed-t:#f4ecfb;--viewed-s:#e6d4f8;
  --none:#5c9a1b;--none-t:#eff7e3;--none-s:#dcedc4}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.6 "Pretendard Variable","Pretendard","Malgun Gothic",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;letter-spacing:-.01em}
header{position:sticky;top:0;z-index:2;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.bar{max-width:1120px;margin:0 auto;padding:12px 16px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px}
.bar h1{font-size:14px;font-weight:650;margin:0}
.legend{display:flex;flex-wrap:wrap;gap:4px 16px;color:var(--sub);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:10px;height:10px;border-radius:3px;display:inline-block}
.legend em{font-style:normal;color:var(--faint);font-variant-numeric:tabular-nums}
.toggle{margin-left:auto;font:inherit;font-size:12px;color:var(--sub);background:none;border:1px solid var(--line);border-radius:6px;padding:3px 9px;cursor:pointer}
.toggle[aria-pressed="true"]{color:var(--ink);border-color:#d4d4d8;background:var(--well)}
main{max-width:1120px;margin:0 auto;padding:24px 16px 48px;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:24px}
@media (max-width:860px){main{grid-template-columns:1fr}}
.doc{background:var(--paper);border-radius:12px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 0 0 1px var(--line);padding:36px 40px}
@media (max-width:600px){.doc{padding:24px 20px}}
.doc h2{font-size:17px;font-weight:650;margin:0 0 20px;letter-spacing:-.02em}
.doc p{margin:0 0 16px;font-size:14px;line-height:1.95}
.s{border-radius:3px;padding:2px 1px;cursor:pointer;transition:background .12s;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.s.exact{background:var(--exact-t)}.s.exact:hover,.s.exact.sel{background:var(--exact-s)}
.s.edited{background:var(--edited-t)}.s.edited:hover,.s.edited.sel{background:var(--edited-s)}
.s.viewed{background:var(--viewed-t)}.s.viewed:hover,.s.viewed.sel{background:var(--viewed-s)}
.s.none{background:var(--none-t)}.s.none:hover,.s.none.sel{background:var(--none-s)}
.s:focus-visible{outline:2px solid var(--ink);outline-offset:1px}
.tags .s::after{content:attr(data-l);font-size:10.5px;font-weight:600;margin-left:4px;vertical-align:1px}
.tags .s.exact::after{color:var(--exact)}.tags .s.edited::after{color:var(--edited)}.tags .s.viewed::after{color:var(--viewed)}.tags .s.none::after{color:var(--none)}
.side{position:sticky;top:72px;align-self:start;max-height:calc(100vh - 92px);overflow:auto;
  background:var(--paper);border-radius:12px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 0 0 1px var(--line);padding:22px 22px}
@media (max-width:860px){.side{position:static;max-height:none}}
.kind{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;margin:0 0 4px}
.kind i{width:8px;height:8px;border-radius:50%}
.meta{font-size:11.5px;color:var(--faint);margin:0 0 16px}
.lab{font-size:11px;font-weight:600;color:var(--faint);margin:16px 0 6px}
.q{font-size:12.5px;color:var(--sub);margin:0}
.well{background:var(--well);border-radius:8px;padding:11px 13px;font-size:13px;line-height:1.8}
.well .hit{border-radius:3px;padding:1px 0}
.empty{color:var(--sub);font-size:12.5px;line-height:1.8;margin:0}
.empty p{margin:0 0 10px}
.empty b{color:var(--ink);font-weight:600}
</style></head>
<body>
<header><div class="bar">
  <h1>결과물 출처 보기</h1>
  <div class="legend">
    <span><i style="background:var(--exact)"></i>AI 답 그대로 <em>__N_EXACT__</em></span>
    <span><i style="background:var(--edited)"></i>붙여넣고 고침 <em>__N_EDITED__</em></span>
    <span><i style="background:var(--viewed)"></i>AI 답 보고 씀 <em>__N_VIEWED__</em></span>
    <span><i style="background:var(--none)"></i>출처 기록 없음 <em>__N_NONE__</em></span>
  </div>
  <button class="toggle" id="tg" aria-pressed="false">글자로 표시</button>
</div></header>
<main>
  <article class="doc" id="doc"></article>
  <aside class="side" id="side"><div class="empty">
    <p>문장을 누르면 이어지는 AI 답의 질문과 원문이 여기에 보입니다.</p>
    <p><b>붙여넣고 고침</b>과 <b>AI 답 보고 씀</b>은 글자가 아니라 복사·붙여넣기 기록으로 가릅니다.</p>
    <p><b>출처 기록 없음</b>은 직접 썼다는 뜻이 아니라, 이어지는 AI 답을 찾지 못했다는 뜻입니다. 휴대폰 같은 다른 기기는 기록되지 않습니다.</p>
    <p>이 표시는 <b>제안</b>입니다. 학생이 맞다 / 아니다를 고르고, 점수는 어디에도 나오지 않습니다.</p>
  </div></aside>
</main>
<script>
const D = __DATA__;
const L = {exact: "그대로", edited: "고침", viewed: "보고 씀", none: "기록 없음"};
const K = {exact: "AI 답 그대로", edited: "붙여넣고 고침", viewed: "AI 답 보고 씀", none: "출처 기록 없음"};
const hm = (ts) => ts ? ts.slice(11, 16) : "";
// 붙여넣기 기록 한 줄 — 과정 기록이 없는 시험(D.rec=false)에선 안 보여 준다
const pasteLine = (s) => !D.rec ? "" : s.paste
  ? `<p class="lab">붙여넣기 기록</p><p class="q">${hm(s.paste.copied_at)} ${esc(s.paste.domain || "AI")} 에서 복사 → ${hm(s.paste.pasted_at)} ${esc(s.paste.where || "문서")}에 붙여넣음</p>`
  : `<p class="lab">붙여넣기 기록</p><p class="q">없음 — ${s.label === "exact" ? "글자는 같지만 붙여넣지 않고 입력함" : "AI 답을 보고 다시 썼거나 옮겨 친 것으로 보임 (어느 쪽인지는 가리지 않음)"}</p>`;
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const doc = document.getElementById("doc"), side = document.getElementById("side"), tg = document.getElementById("tg");
doc.innerHTML = `<h2>${esc(D.title)}</h2>` + D.paras.map((p, pi) =>
  `<p>${p.map((s, si) => `<span class="s ${s.label}" data-p="${pi}" data-s="${si}" data-l="${L[s.label]}" title="${K[s.label]}" tabindex="0">${esc(s.text)}</span>`).join(" ")}</p>`).join("");
tg.onclick = () => { const on = doc.classList.toggle("tags"); tg.setAttribute("aria-pressed", on); };   // 색을 구분하기 어려운 사람용
function show(el) {
  document.querySelectorAll(".s.sel").forEach((x) => x.classList.remove("sel"));
  el.classList.add("sel");
  const s = D.paras[+el.dataset.p][+el.dataset.s];
  const head = `<p class="kind"><i style="background:var(--${s.label})"></i>${K[s.label]}</p>`;
  if (s.label === "none") {
    side.innerHTML = head + `<p class="meta">이어지는 AI 답을 찾지 못했습니다</p><p class="lab">결과물</p><div class="well">${esc(s.text)}</div>`;
  } else {
    const a = D.answers[s.answer];
    const hl = esc(a.text.replace(/\*\*/g, "")).replace(esc(s.ai_text), (m) => `<span class="hit" style="background:var(--${s.label}-s)">${m}</span>`);
    side.innerHTML = head + `<p class="meta">${esc(a.tool)}${a.model ? " · " + esc(a.model) : ""}</p>
      <p class="lab">질문</p><p class="q">${esc(a.question || "")}</p>
      <p class="lab">결과물</p><div class="well">${esc(s.text)}</div>
      <p class="lab">AI 답 원문</p><div class="well">${hl}</div>` + pasteLine(s);
  }
  if (innerWidth <= 860) side.scrollIntoView({behavior: "smooth", block: "start"});   // 좁은 화면: 아래로 내려 보여 줌
}
doc.addEventListener("click", (e) => { const el = e.target.closest(".s"); if (el) show(el); });
doc.addEventListener("keydown", (e) => { if (e.key === "Enter") { const el = e.target.closest(".s"); if (el) show(el); } });
</script>
</body></html>
"""


def jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if os.path.exists(path) else None


def doc_body(docx):
    """Word → (제목, [본문 문단])"""
    paras = read_docx(docx)
    heads = [i for i, (st, t) in enumerate(paras) if st.lower() in ("title", "heading1", "제목")]
    if not heads and paras and len(paras[0][1]) <= 60 and not re.search(r"[.!?。]$", paras[0][1]):
        heads = [0]                          # 제목 서식이 없으면(한국어 Word 는 이름이 다름): 첫 줄이 짧고 마침표가 없으면 제목
    title = paras[heads[0]][1] if heads else os.path.basename(docx)
    return title, [t for i, (st, t) in enumerate(paras) if i not in heads]


def run_case(case, out):
    fx = os.path.join(FIXTURES, case)
    answers = jsonl(os.path.join(fx, "ai_answers.jsonl"))
    truth = json.load(open(os.path.join(fx, "report_truth.json"), encoding="utf-8"))
    docx = os.path.join(fx, "report.docx")
    if not os.path.exists(docx):             # 만든 보고서: 정답 문장으로 Word 를 만든다
        docx = os.path.join(out, f"{case}.docx")
        write_docx(docx, truth["title"], [" ".join(s["text"] for s in p) for p in truth["paragraphs"]])
    events, context = jsonl(os.path.join(fx, "events.jsonl")), jsonl(os.path.join(fx, "context.jsonl"))
    pasted = M.pasted_from_ai(events, context or []) if events is not None else None

    title, body = doc_body(docx)
    linked = M.link_document(body, answers, pasted)

    flat = [s for p in truth["paragraphs"] for s in p]
    got = [s for p in linked for s in p]
    print(f"━━ {case} · 문장 {len(got)}개 (정답 {len(flat)}개) · 과정 기록 {'있음 · AI 답에서 붙여넣기 ' + str(len(pasted)) + '번' if pasted is not None else '없음'}")
    print(f"   기준: 그대로 ≥ {M.EXACT_RATIO} · 이어짐 ≥ {M.EDIT_COVER} · 두 문장 ≥ {M.PAIR_GAIN}배\n")
    hit = 0
    for t, g in zip(flat, got):
        same = g["label"] == t["label"] and (t["label"] == "none" or (g["answer"] == t.get("src") and list(g["sents"]) == t.get("sents")))
        if "pasted" in t and pasted is not None:
            same = same and (g["paste"] is not None) == t["pasted"]
        hit += same
        where = f"{g['answer'] or '':3} {'' if g['sents'] is None else str(list(g['sents'])):7}"
        print(f"  {'✓' if same else '✗'} 정답 {LABEL[t['label']]:5} 결과 {LABEL[g['label']]:5} {where} {'붙임' if g.get('paste') else '    '}  {t['how']}")
        if not same:
            print(f"      └ {g['text'][:60]}")
    by = {k: (sum(1 for t, g in zip(flat, got) if t['label'] == k and g['label'] == k), sum(t['label'] == k for t in flat)) for k in LABEL}
    print(f"\n  맞음 {hit}/{len(flat)} · " + " · ".join(f"{LABEL[k]} {v[0]}/{v[1]}" for k, v in by.items() if v[1]))
    print("  (맞음 = 표시 + AI 답 + 칠할 문장 위치 + 붙여넣기 기록 유무까지 같음)\n")
    render(os.path.join(out, f"{case}.html"), title, linked, answers, rec=pasted is not None)
    need = truth.get("expect_at_least", len(flat))     # 알려진 한계가 있는 시험은 정답 파일에 최소 개수를 적어 둔다
    if need < len(flat):
        print(f"  (알려진 한계: {need}/{len(flat)} 이상이면 통과 — {truth.get('_expect', '')})\n")
    return hit >= need and len(flat) == len(got)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=CASES, help="시험 하나만 (없으면 전부)")
    ap.add_argument("--docx", help="이미 있는 Word 파일 (과정 기록·정답 없이 글자 비교만)")
    ap.add_argument("--answers", default=os.path.join(FIXTURES, "match", "ai_answers.jsonl"), help="--docx 와 같이 쓸 AI 답")
    ap.add_argument("--edit-cover", type=float, help="이어짐 기준을 바꿔서 돌려 보기 (실험용 · 기본은 core/match.py 값)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "data", "연결시제품"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.edit_cover is not None:
        M.EDIT_COVER = a.edit_cover

    if a.docx:
        answers = jsonl(a.answers)
        title, body = doc_body(a.docx)
        path = os.path.join(a.out, "내보고서.html")
        render(path, title, M.link_document(body, answers), answers)
        print(f"화면: {path}")
        return
    results = {c: run_case(c, a.out) for c in ([a.case] if a.case else CASES)}
    print("화면: " + " · ".join(os.path.join(a.out, f"{c}.html") for c in results))
    print(" · ".join(f"{c} {'✓' if ok else '✗'}" for c, ok in results.items()))
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
