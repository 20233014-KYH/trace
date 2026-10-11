"""
statement_pdf.py — AI 활용 내역서 1장 PDF (기획서 10절 "요약 1장" · 7절 표)

  render(내역서, 링크주소) → PDF bytes      ← app.py 의 GET /api/share/<token>/pdf 가 부른다

★ PDF 는 학생이 과제와 함께 내는 종이 한 장이다. 교수는 이걸 훑고, 근거가 궁금할 때만 링크(QR)를 연다.
★ v3 (10/10 박상진): 투명성 한 줄 · 글을 쓴 과정(키보드로 친 글자 · 붙여넣은 글자 AI/다른 곳 · 지운 글자 + 날짜별 막대)
   · 학생 질문 두 개 · 교수 규칙은 학생이 넣었을 때만 · "말하는 것/않는 것" 대신 QR 옆 두 줄
★ 점수·퍼센트·등급을 쓰지 않는다 (원칙 1). 횟수·글자 수·분·시각·원문 발췌만.

글꼴: Pretendard (server/fonts · SIL OFL 1.1 — 같이 둔 Pretendard-LICENSE.txt). Render(리눅스)엔 한글 글꼴이 없어서 넣어 둔다.
"""
import io
import os
from xml.sax.saxutils import escape

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing, Line, Rect, String
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
# 색 규칙 (10/10 박상진): 일치·유사 빨강 · 붙여넣고 고침 그대로 · 보고 씀 = 파랑 (화면에선 점선 밑줄)
KIND = {"exact": ("일치", "#d44c47"), "similar": ("유사", "#d44c47"), "edited": ("붙여넣고 고침", "#cb7a1a"),
        "viewed": ("보고 씀", "#337ea9")}
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


def _도구(d):
    """ChatGPT (gpt-5-6) · Claude — 내역서에 담긴 원문 기준. 모델은 PC 가 보낸 참고값"""
    out = []
    for t in d.get("tools") or []:
        이름 = TOOL.get(str(t.get("tool", "")).lower(), t.get("tool") or "AI")
        out.append(이름 + (f" ({', '.join(t['models'])})" if t.get("models") else ""))
    return " · ".join(out) or "기록된 AI 없음"


def _막대(days, width):
    """날짜별 작업 막대 — 하루 한 줄, 공통 시각 축(가장 이른 시각~가장 늦은 시각). 멈춘 동안은 빈 틈."""
    days = days[-7:]
    def 분(iso):
        return int(iso[11:13]) * 60 + int(iso[14:16])
    lo = min(분(g["start"]) for x in days for g in x["segments"])
    hi = max(분(g["end"]) for x in days for g in x["segments"])
    lo, hi = (lo // 60) * 60, min(24 * 60, -(-hi // 60) * 60)
    if hi <= lo:
        hi = lo + 60
    row, left, right = 13, 56, 58
    bw = width - left - right
    h = row * len(days) + 14
    dr = Drawing(width, h)
    for i, x in enumerate(days):
        y = h - 14 - (i + 1) * row + 3
        dr.add(String(0, y + 1, f"{x['date'][5:7]}/{x['date'][8:10]}", fontName="PR", fontSize=7.4, fillColor=MUTED))
        dr.add(Rect(left, y, bw, 7, fillColor=SOFT, strokeColor=None))
        for g in x["segments"]:
            a = left + bw * (max(분(g["start"]), lo) - lo) / (hi - lo)
            b = left + bw * (min(분(g["end"]), hi) - lo) / (hi - lo)
            dr.add(Rect(a, y, max(b - a, 1.2), 7, fillColor=colors.HexColor("#448361"), strokeColor=None))
        dr.add(String(width - right + 6, y + 1, _mins(x["minutes"]), fontName="PR", fontSize=7.4, fillColor=INK))
    for k in range(lo, hi + 1, 60 if hi - lo <= 8 * 60 else 120):          # 시각 눈금
        xk = left + bw * (k - lo) / (hi - lo)
        dr.add(String(xk - 6, h - 9, f"{k // 60:02d}시", fontName="PR", fontSize=6.6, fillColor=FAINT))
        dr.add(Line(xk, h - 12, xk, 2, strokeColor=LINE, strokeWidth=0.4))
    return dr


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
    out += [Spacer(1, 3), P("  ·  ".join(sub), "sub"), Spacer(1, 8)]

    # ── 투명성 한 줄: 서버 일치 · 도구(모델) · 멈춤 · 가림 · 지운 기록 ──
    probs = d.get("problems") or []
    일치 = (f"<font color='#d44c47'>● 서버 기록과 다릅니다 ({len(probs)}개)</font>" if probs
            else "<font color='#448361'>●</font> 서버 기록과 일치")
    ai = s.get("ai") or {}
    멈춤 = f"멈춤 {s.get('pauses', 0)}번 · {_mins(s.get('pause_minutes'))}" if s.get("pauses") else "멈춤 없음"
    지운 = len(s.get("deleted_sessions") or [])
    줄 = " &nbsp;·&nbsp; ".join([일치, escape(_도구(d)) + f" · 질문 {ai.get('questions', 0)}번", escape(멈춤),
                                f"가림 {d.get('redacted', 0)}", f"지운 기록 {지운}"])
    t = Table([[PM(줄, "memo")]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WARN_SOFT if probs else SOFT),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9)]))
    out += [t, Spacer(1, 8)]
    if d.get("ai_scope"):                                 # 교수 AI 규칙 — 학생이 넣었을 때만 (10/10)
        out += [PM(f"<font color='#787774'>교수 AI 규칙</font> &nbsp; {escape(d['ai_scope'])}", "memo"), Spacer(1, 6)]
    out.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=2, spaceAfter=8))

    # ── 글을 쓴 과정 ──
    if s:
        p = s.get("pastes") or {}
        cols = [("키보드로 친 글자", f"{s.get('typed', 0):,}자", f"기록 {_mins(s.get('minutes'))}"),
                ("붙여넣은 글자", f"{p.get('chars', 0):,}자",
                 f"AI {p.get('from_ai_chars', 0):,} · 다른 곳 {p.get('from_other_chars', 0):,} · 출처 기록 없음 {p.get('unknown_chars', 0):,}"),
                ("지운 글자", f"{s.get('deleted', 0):,}자", "")]
        nums = Table([[[P(k, "k"), P(v, "v"), P(sm, "vs")] for k, v, sm in cols]], colWidths=[CW * 0.3, CW * 0.42, CW * 0.28])
        nums.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        out += [_h("글을 쓴 과정", "횟수·글자 수·시간만 — 점수나 비율은 내지 않습니다"), Spacer(1, 5), nums]
        if s.get("days"):
            out += [Spacer(1, 6), _막대(s["days"], CW)]
            if len(s["days"]) > 7:
                out.append(P(f"최근 7일만 — 전체 {len(s['days'])}일은 링크에서", "small"))
        out.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=8, spaceAfter=8))

    # ── 학생 질문 두 개 ──
    qa = Table([[P("AI를 어디에 썼고, 무엇은 직접 했나요?", "k"), P(d.get("explain_use") or "학생이 쓰지 않음", "memo")],
                [P("AI 답을 고르거나 고칠 때 어떻게 확인했나요?", "k"), P(d.get("explain_check") or "학생이 쓰지 않음", "memo")]],
               colWidths=[150, CW - 150])
    qa.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    out += [_h("학생 설명"), Spacer(1, 4), qa, HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=4, spaceAfter=8)]

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
                         PM(f"<font color='{color}'>●</font> {escape(kind)}", "cell"),
                         PM(flag + escape(src) + (f"<br/><font color='#787774'>질문: {escape(_cut(q.get('text'), 60))}</font>" if q.get("text") else ""),
                            "cellm")])
        t = Table(rows, colWidths=[16, CW * 0.5, 74, CW * 0.5 - 90], repeatRows=1)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                               ("LEFTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        out.append(t)
        if len(links) > MAX_ROWS:
            out += [Spacer(1, 3), P(f"외 {len(links) - MAX_ROWS}곳 — 전체는 링크에서 볼 수 있습니다.", "small")]
    else:
        out.append(P("학생이 확인한 연결이 없습니다.", "small"))
    if d.get("rejected"):
        out += [Spacer(1, 4), P(f"Trace가 제안했지만 학생이 \"아니다\"라고 고른 연결 {d['rejected']}개", "small")]

    # ── QR 옆 두 줄 (10/10 · "말하는 것/않는 것" 대신) ──
    link = Table([[_qr(url), [PM(f"근거 보기 &nbsp;<font color='#337ea9'>{escape(url)}</font>", "cell"), Spacer(1, 3),
                             P("작업 중 기록된 그대로이며 점수나 판정은 없습니다. 출처 기록 없음은 직접 썼다는 뜻이 아니고, "
                               "다른 기기에서 쓴 AI 는 기록되지 않습니다.", "small"),
                             P(f"링크는 {_when(d.get('expires_at'))}까지 열립니다.", "small")]]],
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
