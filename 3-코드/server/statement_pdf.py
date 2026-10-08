"""
statement_pdf.py — AI 활용 내역서 1장 PDF (기획서 10절 "요약 1장" · 7절 표)

  render(내역서, 링크주소) → PDF bytes      ← app.py 의 GET /api/share/<token>/pdf 가 부른다

★ PDF 는 학생이 과제와 함께 내는 종이 한 장이다. 교수는 이걸 훑고, 근거가 궁금할 때만 링크(QR)를 연다.
★ PDF 는 받은 사람이 고칠 수 있다 → 진짜는 링크 쪽이다. PDF 에 그렇게 적는다.
★ 점수·퍼센트·등급을 쓰지 않는다 (원칙 1). 횟수·글자 수·분·시각·원문 발췌만.

글꼴: Pretendard (server/fonts · SIL OFL 1.1 — 같이 둔 Pretendard-LICENSE.txt). Render(리눅스)엔 한글 글꼴이 없어서 넣어 둔다.
"""
import io
import os
from xml.sax.saxutils import escape

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
pdfmetrics.registerFont(TTFont("PR", os.path.join(HERE, "fonts", "Pretendard-Regular.ttf")))
pdfmetrics.registerFont(TTFont("PRB", os.path.join(HERE, "fonts", "Pretendard-SemiBold.ttf")))

# 디자인 기준 v2 와 같은 색 (server/static/share.html)
INK, MUTED, FAINT = colors.HexColor("#37352f"), colors.HexColor("#787774"), colors.HexColor("#a3a29e")
LINE, SOFT = colors.HexColor("#e9e9e7"), colors.HexColor("#f7f7f5")
OK, WARN, WARN_SOFT = colors.HexColor("#448361"), colors.HexColor("#d44c47"), colors.HexColor("#fbecea")
KIND = {"exact": ("일치", "#d44c47"), "similar": ("유사", "#d44c47"), "edited": ("붙여넣고 고침", "#337ea9"),
        "viewed": ("보고 씀", "#9065b0")}
TOOL = {"chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini", "perplexity": "Perplexity", "wrtn": "뤼튼"}

W, H = A4
M = 40
CW = W - 2 * M
MAX_ROWS = 8          # 한 장에 담는 연결 수 — 나머지는 "외 n곳 · 링크에서"


def _s(name, **kw):
    base = dict(name=name, fontName="PR", fontSize=9, leading=13.5, textColor=INK, wordWrap="CJK")
    base.update(kw)
    return ParagraphStyle(**base)


S = {
    "brand": _s("brand", fontName="PRB", fontSize=10),
    "meta": _s("meta", fontSize=7.8, leading=11, textColor=MUTED, alignment=2),
    "title": _s("title", fontName="PRB", fontSize=17, leading=23),
    "sub": _s("sub", fontSize=8.6, leading=12.5, textColor=MUTED),
    "h": _s("h", fontName="PRB", fontSize=10, leading=14),
    "k": _s("k", fontSize=7.8, leading=11, textColor=MUTED),
    "v": _s("v", fontName="PRB", fontSize=18, leading=22),
    "vs": _s("vs", fontSize=7.4, leading=10, textColor=FAINT),
    "cell": _s("cell", fontSize=8.2, leading=12),
    "cellm": _s("cellm", fontSize=7.6, leading=11, textColor=MUTED),
    "th": _s("th", fontSize=7.4, leading=10, textColor=MUTED),
    "small": _s("small", fontSize=7.6, leading=11, textColor=MUTED),
    "memo": _s("memo", fontSize=8.8, leading=13),
}


def P(text, style="cell"):
    """글자 그대로 (학생·AI 글은 전부 이걸로 — 안의 < > & 를 서식으로 해석하지 않게)"""
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), S[style])


def PM(markup, style="cell"):
    """서식(<br/> · <font>)이 든 글 — 안에 넣는 값은 부르는 쪽에서 escape() 한다"""
    return Paragraph(markup, S[style])


def _h(title, note=""):
    return PM(escape(title) + (f"  <font color='#a3a29e' size='7.4'>{escape(note)}</font>" if note else ""), "h")


def _cut(t, n):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _when(iso, date=True):
    if not iso or len(iso) < 16:
        return ""
    return f"{iso[:10]} {iso[11:16]}" if date else iso[11:16]


def _mins(v):
    v = round(v or 0)
    return f"{v // 60}시간 {v % 60}분" if v >= 60 else f"{v}분"


def _qr(url, size=64):
    w = QrCodeWidget(url)
    x1, y1, x2, y2 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    d.add(w)
    return d


def render(d, url):
    """d = _내역서_내용(교수용) + work · author · expires_at. url = 교수 확인 링크."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=M - 6, bottomMargin=M - 6,
                            title=f"AI 활용 내역서 · {(d.get('work') or {}).get('title') or ''}", author="Trace")
    s = d.get("summary") or {}
    out = []

    # ── 머리 ──
    head = Table([[P("Trace  ·  AI 활용 내역서", "brand"),
                   PM(f"만든 시각 {escape(_when(d.get('created_at')))}<br/>내역서 번호 {escape(str(d.get('id', ''))[:8])}", "meta")]],
                 colWidths=[CW * 0.6, CW * 0.4])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    out += [head, HRFlowable(width="100%", thickness=1.4, color=INK, spaceAfter=10)]
    out.append(P((d.get("work") or {}).get("title") or "제목 없는 과제", "title"))
    sub = []
    if d.get("author"):
        sub.append(f"작성자 {d['author']} (계정 이름 · Trace가 신원을 확인하지 않음)")
    if s.get("sessions"):
        sub.append(f"{_when(s.get('first_at'))} – {_when(s.get('last_at'))} · 작업 기록 {s['sessions']}번")
    out += [Spacer(1, 3), P("  ·  ".join(sub), "sub"), Spacer(1, 9)]

    # ── 검증 한 줄 ──
    probs = d.get("problems") or []
    if probs:
        txt = (f"<b>확인되지 않은 항목이 {len(probs)}개 있습니다.</b> 내용은 링크에서 그대로 볼 수 있습니다. "
               "(기록 당시와 다른 원문 · 봉인 전 기록 등)")
        bg, dot = WARN_SOFT, WARN
    else:
        txt = ("<b>학생이 공유한 AI 질문·답은 작업하는 동안 기록된 그대로입니다.</b> "
               "기록할 때 남긴 해시와 받은 원문을 서버가 하나씩 다시 계산해 맞춰 봤습니다.")
        bg, dot = SOFT, OK
    v = Table([["●", Paragraph(txt, S["memo"])]], colWidths=[14, CW - 14])
    v.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("TEXTCOLOR", (0, 0), (0, 0), dot),
                           ("FONTNAME", (0, 0), (0, 0), "PR"), ("FONTSIZE", (0, 0), (0, 0), 8),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (0, 0), 8)]))
    out += [v, Spacer(1, 10)]

    # ── 허용 범위 · 학생 설명 ──
    memo = Table([[P("AI 허용 범위", "k"), P(d.get("ai_scope") or "적지 않음", "memo")],
                  [P("학생 설명", "k"), P(d.get("sentence") or "적지 않음", "memo")]], colWidths=[70, CW - 70])
    memo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    out += [memo, HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=6, spaceAfter=8)]

    # ── 센 숫자 ──
    if s:
        ai, p = s.get("ai") or {}, s.get("pastes") or {}
        tools = " · ".join(f"{TOOL.get(str(t).lower(), t)} {c}" for t, c in (ai.get("tools") or {}).items())
        cols = [("기록 시간", _mins(s.get("minutes")), f"자리 비움 {round(s.get('idle_minutes') or 0)}분 포함" if s.get("idle_minutes") else ""),
                ("AI에 한 질문", f"{ai.get('questions', 0)}번", tools),
                ("직접 입력", f"{s.get('typed', 0):,}자", f"지운 글자 {s.get('deleted', 0):,}자"),
                ("붙여넣기", f"{p.get('count', 0)}번",
                 f"{p.get('chars', 0):,}자 · AI 창 복사 {p.get('from_ai_count', 0)}번 · 출처 기록 없음 {p.get('unknown_count', 0)}번")]
        nums = Table([[[P(k, "k"), P(v, "v"), P(sm, "vs")] for k, v, sm in cols]], colWidths=[CW / 4] * 4)
        nums.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        out += [_h("작업 기록에서 센 숫자", "횟수·글자 수·시간만 — 점수나 비율은 내지 않습니다"),
                Spacer(1, 5), nums, HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=8, spaceAfter=8)]

    # ── 연결 ──
    links = d.get("links") or []
    out.append(_h("과제 속 AI 답", f"학생이 \"AI 답에서 왔다\"고 확인한 부분 {len(links)}곳"))
    out.append(Spacer(1, 5))
    if links:
        rows = [[P("#", "th"), P("과제에 쓴 글", "th"), P("모양", "th"), P("AI 답 · 질문", "th")]]
        for i, l in enumerate(links[:MAX_ROWS], 1):
            kind, color = KIND.get(l.get("kind"), ("", "#787774"))
            a, q, r = l.get("answer") or {}, l.get("question") or {}, l.get("result") or {}
            loc = r.get("location") or {}
            where = " · ".join(x for x in (loc.get("file"), f"{loc['paragraph']}번째 문단" if loc.get("paragraph") else "") if x)
            flag = "" if a.get("ok", True) and q.get("ok", True) else "<font color='#d44c47'>⚠ 기록 당시와 다름</font><br/>"
            src = f"{TOOL.get(str(a.get('tool', '')).lower(), a.get('tool') or 'AI')} · {'이전 대화' if a.get('history') else _when(a.get('ts'))}"
            rows.append([P(str(i), "cellm"),
                         [P(_cut(r.get("text"), 110)), P(where, "cellm")],
                         Paragraph(f"<font color='{color}'>●</font> {escape(kind)}", S["cell"]),
                         Paragraph(flag + escape(src) + (f"<br/><font color='#787774'>질문: {escape(_cut(q.get('text'), 60))}</font>" if q.get("text") else ""),
                                   S["cellm"])])
        t = Table(rows, colWidths=[16, CW * 0.5, 74, CW * 0.5 - 90], repeatRows=1)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                               ("LEFTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        out.append(t)
        if len(links) > MAX_ROWS:
            out += [Spacer(1, 3), P(f"외 {len(links) - MAX_ROWS}곳 — 전체는 링크에서 볼 수 있습니다.", "small")]
    else:
        out.append(P("학생이 확인한 연결이 없습니다.", "small"))
    extra = []
    if d.get("redacted"):
        extra.append(f"학생이 가린 항목 {d['redacted']}개 (내용은 오지 않았고 기록에는 남아 있음)")
    if d.get("rejected"):
        extra.append(f"Trace가 제안했지만 학생이 \"아니다\"라고 고른 연결 {d['rejected']}개")
    if extra:
        out += [Spacer(1, 4), P("  ·  ".join(extra), "small")]

    # ── 말하는 것 · 링크 ──
    out.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=10, spaceAfter=8))
    says = Table([[
        [P("이 내역서가 말하는 것", "h"), Spacer(1, 3),
         P("✓ 위 AI 질문·답은 작업하는 동안 기록된 글과 같다" if not probs else "✓ ⚠ 표시가 없는 AI 질문·답은 기록된 글과 같다", "small"),
         P("✓ 기록의 순서와 시각은 작업이 끝난 뒤 바뀌지 않았다", "small"),
         P("✓ 어느 부분이 어느 AI 답에서 왔는지는 학생이 직접 확인했다", "small")],
        [P("말하지 않는 것", "h"), Spacer(1, 3),
         P("× AI를 썼는지 안 썼는지에 대한 판정 (점수 없음)", "small"),
         P("× 휴대폰·다른 컴퓨터에서 쓴 AI (기록되지 않음)", "small"),
         P("× \"출처 기록 없음\" = 직접 썼다는 뜻이 아님", "small")],
    ]], colWidths=[CW / 2, CW / 2])
    says.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    out.append(says)

    link = Table([[_qr(url), [P("근거 보기 — 학생이 고른 AI 질문·답 원문과 과제 글을 나란히", "h"), Spacer(1, 2),
                             Paragraph(f"<font color='#337ea9'>{escape(url)}</font>", S["cell"]),
                             Spacer(1, 3),
                             P(f"링크는 {_when(d.get('expires_at'))}까지 열립니다. 이 PDF는 받은 사람이 고칠 수 있으니, "
                               "PDF와 링크의 내용이 다르면 링크가 원본입니다.", "small")]]],
                 colWidths=[74, CW - 74])
    link.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                              ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    out += [Spacer(1, 10), KeepTogether([link])]

    def 바닥(canvas, _doc):
        canvas.saveState()
        canvas.setFont("PR", 7)
        canvas.setFillColor(FAINT)
        canvas.drawString(M, 22, "Trace · 원문은 학생 PC에 있고, 학생이 고른 것만 링크로 공유됩니다")
        canvas.drawRightString(W - M, 22, f"{_doc.page}쪽")
        canvas.restoreState()

    doc.build(out, onFirstPage=바닥, onLaterPages=바닥)
    return buf.getvalue()
