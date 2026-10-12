"""
statement_pdf.py — AI 활용 내역서 1장 PDF (기획서 10절 "요약 1장" · 7절 표)

  render(내역서, 링크주소) → PDF bytes      ← app.py 의 GET /api/share/<token>/pdf 가 부른다

★ 캔버스 "Trace 화면 뼈대" 6 · 내역서 v3 (ReportA3 · ReportB3) 를 그대로 옮긴다 (10/12 김용현).
   보드는 794×1123px(A4) HTML 이라 px × 0.75 = pt 로 크기·간격을 그대로 쓴다. 색은 보드의 값 그대로.
   머리 → 투명성 한 줄 → 글을 쓴 과정 | 언제 작업했나 → ① 어떻게 썼나 ② 질문 흐름 ③ 결과물에 들어간 것 ④ 학생 설명 → QR (맨 아래)
   보드와 다른 곳은 1차 확정 보드(Freeze)의 뒤 결정을 따른 것뿐: 빨강 이름 "가져온 그대로" → "AI 답과 같음" (10/12)
★ PDF 는 학생이 과제와 함께 내는 종이 한 장이다. 교수는 이걸 훑고, 근거가 궁금할 때만 링크(QR)를 연다. 늘 한 장.
★ 점수·퍼센트·등급을 쓰지 않는다 (원칙 1). 횟수·글자 수·분·시각·원문 발췌만.

글꼴: Pretendard (server/fonts · SIL OFL 1.1 — 같이 둔 Pretendard-LICENSE.txt). Render(리눅스)엔 한글 글꼴이 없어서 넣어 둔다.
"""
import io
import os
import re
from datetime import date
from xml.sax.saxutils import escape

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import paragraph as _rl_para

HERE = os.path.dirname(os.path.abspath(__file__))
pdfmetrics.registerFont(TTFont("PR", os.path.join(HERE, "fonts", "Pretendard-Regular.ttf")))
pdfmetrics.registerFont(TTFont("PRS", os.path.join(HERE, "fonts", "Pretendard-SemiBold.ttf")))   # 600 · 650
pdfmetrics.registerFont(TTFont("PRB", os.path.join(HERE, "fonts", "Pretendard-Bold.ttf")))       # 700

X = 0.75                                    # 보드 px → pt
C = colors.HexColor
INK, T52, T71, T3F = C("#18181b"), C("#52525b"), C("#71717a"), C("#3f3f46")
FAINT, LINE, CHIP, BOX = C("#a1a1aa"), C("#e4e4e7"), C("#f4f4f5"), C("#fafafa")
DOT_LINE, SEP = C("#d4d4d8"), "#d4d4d8"
OK_TXT, OK_DOT, BAD = "#15803d", "#16a34a", "#d44c47"
RED_BG, BLUE_BG, NONE_TXT = "#fdecec", "#eaf0fd", "#f7f7f7"
NONE_BG = C("#f0f0f0")                      # 보드 rgba(24,24,27,.06) 를 흰 바탕 위 색으로
DASH = C("#3e63dd")                         # 보고 씀 = 파랑 점선 밑줄 (이 색의 밑줄만 점선으로 그린다)

TOOL = {"chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini", "perplexity": "Perplexity", "wrtn": "뤼튼"}
# 결과물 문장 묶음 — 이름 (1차 확정 10/12) · 보드의 견본 모양
RESULT = [("ai", "AI 답과 같음", "red"), ("other", "다른 곳에서 옴", "red"), ("edited", "붙여넣고 고침", "blue"),
          ("viewed", "보고 씀", "dash"), ("none", "출처 기록 없음", "none")]
KIND_LOOK = {"exact": "red", "similar": "red", "edited": "blue", "viewed": "dash"}
USAGE = [("learn", "이해·자료 찾기"), ("fix", "고치기·검토"), ("write", "작성")]
옛쓰임 = {"understand": "learn", "find": "learn", "review": "fix", "polish": "fix"}     # 10/12 전 내역서는 다섯 칸 → 셋으로
MAX_Q, MAX_EX = 3, 3
# ③ 예시로 뽑지 않을 문장 — 전화번호 · 이메일 같은 개인 정보
_사적 = re.compile(r"(?<!\d)01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)|[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

W, H = A4
ML, MT = 56 * X, 44 * X                     # 보드 padding 44px 56px
CW = W - 2 * ML
QR = 56 * X
FOOT_H = 14 * X + QR                        # QR 칸 (border-top + padding-top 14px + QR 56px)


# reportlab 밑줄은 실선뿐 → 보고 씀 파랑(#3e63dd) 밑줄만 점선으로 (보드: underline dashed · 1.5px · offset 4px)
_원래선 = _rl_para._do_line


def _점선(tx, x1, y1, x2, y2, nlw, nsc):
    if nsc == DASH:
        c = tx._canvas
        c.saveState()
        c.setDash(2.2, 1.6)
        c.setLineWidth(nlw)
        c.setStrokeColor(nsc)
        c.line(x1, y1, x2, y2)
        c.restoreState()
    else:
        _원래선(tx, x1, y1, x2, y2, nlw, nsc)


_rl_para._do_line = _점선


def _st(px, font="PR", color=INK, lh=1.5, **kw):
    return ParagraphStyle(f"s{px}{font}{lh}{kw}", fontName=font, fontSize=px * X, leading=px * X * lh, textColor=color,
                          wordWrap="CJK", **kw)


S = {
    "brand": _st(12, "PRS", T52, 1.3),
    "title": _st(24, "PRB", INK, 1.25),
    "sub": _st(12.5, "PR", T71, 1.4),
    "trans": _st(11.5, "PR", T52, 1.6),
    "h12": _st(12, "PRS", INK, 1.3),
    "pn": _st(20, "PRB", INK, 1.15),
    "pns": _st(11, "PR", T71, 1.35),
    "secn": _st(12, "PRS", FAINT, 1.35),
    "h2": _st(14, "PRS", INK, 1.35),
    "note": _st(11.5, "PR", T71, 1.45),
    "noter": _st(10.5, "PR", T71, 1.45, alignment=2),
    "step": _st(12, "PR", INK, 1.5),
    "ex": _st(12, "PR", T3F, 1.75),
    "qab": _st(11.5, "PRS", T71, 1.45),
    "qat": _st(12.5, "PR", INK, 1.65),
    "box": _st(12, "PR", T3F, 1.45),
    "foot": _st(11, "PR", T71, 1.7),
}


def P(markup, style):
    return Paragraph(markup, S[style])


def E(t):
    return escape(str(t or "")).replace("\n", "<br/>")


def _cut(t, n):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _md(iso, 요일=False):
    """2026-10-06T… → 10/6 (화) — 보드 날짜 꼴 (앞 0 없음)"""
    if not iso or len(iso) < 10:
        return ""
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return f"{m}/{d}" + (f" ({'월화수목금토일'[date(y, m, d).weekday()]})" if 요일 else "")


def _mins(v):
    v = round(v or 0)
    return (f"{v // 60}시간 {v % 60}분" if v % 60 else f"{v // 60}시간") if v >= 60 else f"{v}분"


def _hm(v):
    v = round(v or 0)
    return f"{v // 60}:{v % 60:02d}"


def _멈춘시간(s):
    """10분 안쪽이면 초까지 (1분 27초) — 옛 요약엔 pause_seconds 가 없어 분으로"""
    초 = s.get("pause_seconds")
    if 초 is None:
        return _mins(s.get("pause_minutes"))
    if 초 < 600:
        return f"{초 // 60}분 {초 % 60}초" if 초 >= 60 else f"{초}초"
    return _mins(초 / 60)


def _도구(d):
    out = []
    for t in d.get("tools") or []:
        이름 = TOOL.get(str(t.get("tool", "")).lower(), t.get("tool") or "AI")
        out.append(이름 + (f" ({', '.join(t['models'])})" if t.get("models") else ""))
    return " · ".join(out) or "기록된 AI 없음"


def _쓰임수(uc):
    out = {}
    for k, n in (uc or {}).items():
        out[옛쓰임.get(k, k)] = out.get(옛쓰임.get(k, k), 0) + n
    return out


def _표(rows, widths, style=()):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")] + [(k, (0, 0), (-1, -1), 0) for k in
                          ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")] + list(style)))
    return t


class 선(Flowable):
    """가로줄 (보드 border-top 1px)"""
    def __init__(self, color, w=1 * X):
        super().__init__()
        self.color, self.w = color, w

    def wrap(self, aw, ah):
        self.width = aw
        return aw, self.w

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.w)
        self.canv.line(0, 0, self.width, 0)


class 칩줄(Flowable):
    """보드 .uc .chip — 110px × 28px · 둥글기 10px · 간격 5px. 0 이면 흰 바탕 + 테두리 · 흐린 글"""
    W_, H_, G_ = 110 * X, 28 * X, 5 * X

    def __init__(self, items):
        super().__init__()
        self.items = items

    def wrap(self, aw, ah):
        return len(self.items) * (self.W_ + self.G_), self.H_

    def draw(self):
        c = self.canv
        for i, (n, 이름) in enumerate(self.items):
            x = i * (self.W_ + self.G_)
            if n:
                c.setFillColor(CHIP)
                c.roundRect(x, 0, self.W_, self.H_, 10 * X, stroke=0, fill=1)
            else:
                c.setFillColor(colors.white)
                c.setStrokeColor(LINE)
                c.setLineWidth(X)
                c.roundRect(x + X / 2, X / 2, self.W_ - X, self.H_ - X, 10 * X, stroke=1, fill=1)
            y = self.H_ / 2 - 14 * X * 0.36
            c.setFont("PRB", 14 * X)
            c.setFillColor(INK if n else FAINT)
            c.drawString(x + 8 * X, y, str(n))
            nw = max(pdfmetrics.stringWidth(str(n), "PRB", 14 * X), 12 * X)
            c.setFont("PR", 12 * X)
            c.setFillColor(T52 if n else FAINT)
            c.drawString(x + 8 * X + nw + 5 * X, y + 0.3, 이름)


class 막대(Flowable):
    """언제 작업했나 — 보드 .tl: 날짜 62px | 막대(8px · 둥글기 4 · #f4f4f5 · 구간 #18181b) | 52px h:mm · 간격 8px.
    시각 축 9시~24시 (보드 눈금 12·15·18·21시) — 그 밖 시각이 있으면 3시간 단위로 넓힌다"""
    def __init__(self, days):
        super().__init__()
        self.days = days[-7:]
        분 = lambda iso: int(iso[11:13]) * 60 + int(iso[14:16])
        lo = min([9 * 60] + [분(g["start"]) for x in self.days for g in x["segments"]])
        hi = max([24 * 60] + [분(g["end"]) for x in self.days for g in x["segments"]])
        self.lo, self.hi = (lo // 180) * 180, min(24 * 60, -(-hi // 180) * 180)
        self.분 = 분

    def wrap(self, aw, ah):
        self.width = aw
        self.row = 13 * X + 5 * X              # 줄 높이(11px 글) + 줄 사이 5px
        return aw, self.row * len(self.days) + 12 * X

    def draw(self):
        c = self.canv
        lw, rw, gap = 62 * X, 52 * X, 8 * X
        bx, bw = lw + gap, self.width - lw - rw - 2 * gap
        span = self.hi - self.lo
        top = self.row * len(self.days) + 12 * X
        for i, x in enumerate(self.days):
            y = top - (i + 1) * self.row + 5 * X
            c.setFont("PR", 11 * X)
            c.setFillColor(T71)
            c.drawString(0, y + 1, _md(x["date"], 요일=True))
            c.drawRightString(self.width, y + 1, _hm(x["minutes"]))
            c.setFillColor(CHIP)
            c.roundRect(bx, y + 1.5, bw, 8 * X, 4 * X, stroke=0, fill=1)
            c.setFillColor(INK)
            for g in x["segments"]:
                a = bx + bw * (max(self.분(g["start"]), self.lo) - self.lo) / span
                b = bx + bw * (min(self.분(g["end"]), self.hi) - self.lo) / span
                c.roundRect(a, y + 1.5, max(b - a, 1.5), 8 * X, min(4 * X, max(b - a, 1.5) / 2), stroke=0, fill=1)
        c.setFont("PR", 10 * X)
        c.setFillColor(FAINT)
        for h in range(self.lo + 180, self.hi, 180):
            c.drawCentredString(bx + bw * (h - self.lo) / span, 1, f"{h // 60}시")


class 흐름(Flowable):
    """질문 흐름 — 보드 .step: 점 7px(#18181b) · 사이 세로줄 1px × 9px(#d4d4d8) · 글 12px/1.5 · 점 칸 18px + 간격 8px"""
    def __init__(self, items):
        super().__init__()
        self.paras = [P(m, "step") for m in items]

    def wrap(self, aw, ah):
        self.width = aw
        self.hs = [p.wrap(aw - 26 * X, ah)[1] for p in self.paras]
        self.height = sum(self.hs) + 9 * X * (len(self.paras) - 1)
        return aw, self.height

    def draw(self):
        c = self.canv
        y = self.height
        for i, (p, h) in enumerate(zip(self.paras, self.hs)):
            y -= h
            p.drawOn(c, 26 * X, y)
            c.setFillColor(INK)
            c.circle(5 * X + 3.5 * X, y + h - 5 * X - 3.5 * X, 3.5 * X, stroke=0, fill=1)
            if i + 1 < len(self.paras):
                c.setStrokeColor(DOT_LINE)
                c.setLineWidth(X)
                c.line(8.5 * X, y, 8.5 * X, y - 9 * X)
                y -= 9 * X


class 견본(Flowable):
    """결과물에 들어간 것 — 보드 .cnt: 11px 견본(둥글기 3) + "이름 수" · 간격 6px 14px · 보고 씀은 '밑줄' 글자에 파랑 점선"""
    def __init__(self, items):
        super().__init__()
        self.items = items                     # [(look, "이름 수")]

    def _w(self, look, t):
        w = pdfmetrics.stringWidth(t, "PR", 12 * X)
        return w + (pdfmetrics.stringWidth("밑줄", "PR", 12 * X) + 5 * X if look == "dash" else 16 * X)

    def wrap(self, aw, ah):
        self.width, x, rows = aw, 0, 1
        for look, t in self.items:
            w = self._w(look, t)
            if x and x + w > aw:
                rows, x = rows + 1, 0
            x += w + 14 * X
        self.height = rows * 18 * X
        return aw, self.height

    def draw(self):
        c = self.canv
        x, y = 0, self.height - 13 * X
        for look, t in self.items:
            w = self._w(look, t)
            if x and x + w > self.width:
                x, y = 0, y - 18 * X
            c.setFont("PR", 12 * X)
            c.setFillColor(T52)
            if look == "dash":
                mw = pdfmetrics.stringWidth("밑줄", "PR", 12 * X)
                c.drawString(x, y, "밑줄")
                c.saveState()
                c.setDash(2.2, 1.6)
                c.setStrokeColor(DASH)
                c.setLineWidth(1.5 * X)
                c.line(x, y - 3 * X, x + mw, y - 3 * X)
                c.restoreState()
                c.setFillColor(T52)
                c.drawString(x + mw + 5 * X, y, t)
            else:
                if look == "none":
                    c.setFillColor(NONE_BG)
                    c.setStrokeColor(LINE)
                    c.setLineWidth(X)
                    c.roundRect(x, y - 1.5, 11 * X, 11 * X, 3 * X, stroke=1, fill=1)
                else:
                    c.setFillColor(C(RED_BG if look == "red" else BLUE_BG))
                    c.roundRect(x, y - 1.5, 11 * X, 11 * X, 3 * X, stroke=0, fill=1)
                c.setFillColor(T52)
                c.drawString(x + 16 * X, y, t)
            x += w + 14 * X


def _상자(cells, widths, pad=(7, 10), extra=()):
    """보드의 연회색 상자 — 바탕 #fafafa · 테두리 1px #e4e4e7 · 둥글기 8px"""
    t = Table([cells], colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, -1), BOX),
                           ("BOX", (0, 0), (-1, -1), X, LINE), ("ROUNDEDCORNERS", [8 * X] * 4),
                           ("TOPPADDING", (0, 0), (-1, -1), pad[0] * X), ("BOTTOMPADDING", (0, 0), (-1, -1), pad[0] * X),
                           ("LEFTPADDING", (0, 0), (-1, -1), pad[1] * X), ("RIGHTPADDING", (0, 0), (-1, -1), pad[1] * X)]
                          + list(extra)))
    return t


def _칸(n, title, note, body, last=False):
    """보드 .sec — border-top 1px #e4e4e7 · padding 13px 0 · 번호 28px + 간격 12px · h2 14px/650 + 설명 11.5px · 아래 8px"""
    head = P(E(title) + (f"<font name='PR' size='{11.5 * X}' color='#71717a'>&nbsp;&nbsp;{E(note)}</font>" if note else ""), "h2")
    t = _표([[P(str(n), "secn"), "", [head, Spacer(1, 8 * X)] + body]], [28 * X, 12 * X, CW - 40 * X])
    return [선(LINE), Spacer(1, 13 * X), t] + ([] if last else [Spacer(1, 13 * X)])


def _qr(url, size):
    w = QrCodeWidget(url)
    x1, y1, x2, y2 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    d.add(w)
    return d


def render(d, url):
    """d = _내역서_내용(교수용) + work · author · expires_at. url = 교수 확인 링크."""
    buf = io.BytesIO()
    # 틀 안쪽 여백 0 — reportlab 기본(6pt)이 있으면 보드의 56px 왼쪽 끝과 어긋난다
    doc = BaseDocTemplate(buf, pagesize=A4, title=f"AI 활용 내역서 · {(d.get('work') or {}).get('title') or ''}", author="Trace")
    틀 = Frame(ML, MT + FOOT_H + 8, CW, H - 2 * MT - FOOT_H - 8, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    s = d.get("summary") or {}
    ai = s.get("ai") or {}
    links = d.get("links") or []
    out = []

    # ── 머리 (보드: 브랜드 12px · 제목 24px/700 · 학생 줄 12.5px · 투명성 줄 11.5px · padding-bottom 12px · 검정 줄) ──
    sub = [d["author"]] if d.get("author") else []
    if s.get("sessions"):
        a, b = _md(s.get("first_at")), _md(s.get("last_at"))
        sub.append(f"{a if a == b else f'{a} – {b}'} · 기록 {s['sessions']}번 · {_mins(s.get('minutes'))}")
    probs = d.get("problems") or []
    일치 = (f"<font color='{BAD}'>●&nbsp;서버 기록과 다릅니다 ({len(probs)}개)</font>" if probs
            else f"<font color='{OK_DOT}' size='{8 * X}'>●</font>&nbsp;<font color='{OK_TXT}'>서버 기록과 일치</font>")
    멈춤 = f"잠깐 멈춤 {s.get('pauses', 0)}번 · {_멈춘시간(s)}" if s.get("pauses") else "멈춤 없음"
    지운 = len(s.get("deleted_sessions") or [])
    점 = f"&nbsp;&nbsp;<font color='{SEP}'>·</font>&nbsp;&nbsp;"
    줄 = 점.join([일치, E(_도구(d)), E(멈춤), f"가림 {d['redacted']}곳" if d.get("redacted") else "가림 없음",
                f"지운 기록 {지운}개" if 지운 else "지운 기록 없음"])
    out += [_표([[P("AI 활용 내역서 · Trace", "brand")], [Spacer(1, 4 * X)],
                 [P(E((d.get("work") or {}).get("title") or "제목 없는 과제"), "title")], [Spacer(1, 3 * X)],
                 [P(E(" · ".join(sub)), "sub")], [Spacer(1, 10 * X)], [P(줄, "trans")]], [CW]),
            Spacer(1, 12 * X), 선(INK)]

    # ── 글을 쓴 과정 | 언제 작업했나 (보드 padding 13px · 200px | 나머지 · 간격 22px) ──
    if s:
        p = s.get("pastes") or {}
        왼 = [P("글을 쓴 과정", "h12"), Spacer(1, 8 * X)]
        for i, (v, k) in enumerate(((f"{s.get('typed', 0):,}자", "키보드로 친 글자"),
                                    (f"{p.get('chars', 0):,}자", f"붙여넣은 글자 · AI {p.get('from_ai_chars', 0):,} · 다른 곳 "
                                     f"{p.get('from_other_chars', 0):,}" + (f" · 출처 기록 없음 {p['unknown_chars']:,}" if p.get("unknown_chars") else "")),
                                    (f"{s.get('deleted', 0):,}자", "지운 글자"))):
            왼 += ([Spacer(1, 7 * X)] if i else []) + [P(v, "pn"), P(E(k), "pns")]
        days = s.get("days") or []
        오른 = [P(f"언제 작업했나 <font name='PR' size='{11 * X}' color='#71717a'>· {len(days)}일 · 기록 {s.get('sessions', 0)}번</font>", "h12"),
                Spacer(1, 8 * X)] + ([막대(days)] if days else [P("작업 시간 기록이 없습니다.", "note")])
        out += [Spacer(1, 13 * X), _표([[왼, "", 오른]], [200 * X, 22 * X, CW - 222 * X]), Spacer(1, 13 * X)]

    # ── ① 어떻게 썼나 ──
    답들 = {(l.get("answer") or {}).get("text") for l in links if l.get("answer") and l.get("kind") != "viewed"}
    쓰임 = len(답들)                                   # 글이 들어간 답 — "보고 씀"은 글이 들어간 게 아니다 (보드 A: 0)
    질문수, 답수 = ai.get("questions", 0), ai.get("answers", 0)
    도구별 = " · ".join(f"{TOOL.get(str(t).lower(), t)} {n}" for t, n in (ai.get("tools") or {}).items())
    body = []
    if d.get("ai_scope"):                             # 교수 안내 — 학생이 넣었을 때만 (보드 B · padding 7px 10px)
        안 = CW - 40 * X
        body += [_상자([P("교수 안내", "h12"), P(E(d["ai_scope"]), "box"), P("학생이 넣었을 때만", "noter")],
                       [66 * X, 안 - 66 * X - 110 * X, 110 * X], extra=[("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
                 Spacer(1, 8 * X)]
    uc = d.get("usage_counts")
    if uc:
        uc = _쓰임수(uc)
        body += [칩줄([(uc.get(k, 0), 이름) for k, 이름 in USAGE]), Spacer(1, 8 * X),
                 P(E("쓰임새는 규칙으로 나누고 학생이 확인" + (f" · {도구별}" if 도구별 else "")), "note")]
    else:                                             # 예전 내역서 (쓰임새 수를 안 보냄)
        body += [P(E(f"질문은 {질문수}번 했고, 그중 답 {쓰임}개의 글이 결과물에 들어갔습니다."), "step")]
        if 도구별:
            body.append(P(E(f"도구별 질문 · {도구별}"), "note"))
    out += _칸(1, "어떻게 썼나", f"AI 에 한 질문 {질문수} · 결과물에 글이 들어간 답 {쓰임} · 참고만 {max(답수 - 쓰임, 0)}", body)

    # ── ② 질문 흐름 ──
    flow = d.get("flow")
    note = "학생이 고른 대표 흐름"
    if flow is None:                                  # 예전 내역서 — 결과물에 글이 들어간 질문을 시간 순으로
        flow, 본 = [], set()
        for l in sorted(links, key=lambda l: ((l.get("answer") or {}).get("ts") or "")):
            q = l.get("question") or {}
            if q.get("text") and q["text"] not in 본:
                본.add(q["text"])
                flow.append({"text": q["text"], "tool": (l.get("answer") or {}).get("tool"), "usage": None, "used": True})
        note = "결과물에 글이 들어간 질문 · 시간 순"
    flow = flow[:MAX_Q]
    이름 = dict(USAGE)
    items = []
    for f in flow:
        꼬리 = " · ".join(x for x in (이름.get(옛쓰임.get(f.get("usage"), f.get("usage"))),
                                     TOOL.get(str(f.get("tool", "")).lower(), f.get("tool")),
                                     "" if f.get("ok", True) else "⚠ 기록 당시와 다름") if x)
        items.append(f'"{E(_cut(f["text"], 70))}"' + (f" <font color='#71717a'>· {E(꼬리)}</font>" if 꼬리 else ""))
    if items:
        n, k = sum(1 for f in flow if f.get("used")), len(flow)
        몇 = {3: "세", 2: "두"}.get(k, "")
        끝 = ((f"{몇} 질문 모두" if 몇 else "이 질문은") + " 답의 글이 결과물에 들어가지 않음" if n == 0
              else (f"{몇} 답 모두" if 몇 else "이 답은") + " 결과물에 글이 들어감 — 아래 3" if n == k
              else f"{k}개 중 {n}개는 답의 글이 결과물에 들어감 — 아래 3")
        body = [흐름(items), Spacer(1, 7 * X), P(E(끝), "note")]
    else:
        body = [P("학생이 고른 질문이 없습니다.", "note")]
    out += _칸(2, "질문 흐름", note, body)

    # ── ③ 결과물에 들어간 것 ──
    rc = d.get("result_counts")
    if not rc:                                        # 예전 내역서 — 학생이 확인한 연결로만
        k = [l.get("kind") for l in links]
        rc = {"ai": k.count("exact") + k.count("similar"), "edited": k.count("edited"), "viewed": k.count("viewed")}
    칸들 = [(look, f"{name} {rc[key]}") for key, name, look in RESULT
            if rc.get(key) is not None and not (key == "other" and not rc[key])]
    body = [견본(칸들)]
    후보 = [l for l in links if len((l.get("result") or {}).get("text") or "") >= 20 and not _사적.search(l["result"]["text"])]
    고른 = sorted(sorted(후보, key=lambda l: -len(l["result"]["text"]))[:MAX_EX], key=후보.index)

    def 칠(l, n):
        look, t = KIND_LOOK.get(l.get("kind"), "none"), E(_cut(l["result"]["text"], n))
        if look == "dash":
            return f"<u color='#3e63dd' width='{1.5 * X}' offset='{-4 * X}'>{t}</u>"
        return f"<span backColor='{RED_BG if look == 'red' else BLUE_BG if look == 'blue' else NONE_TXT}'>{t}</span>"
    if len(고른) == 1:                                 # 한 문장 — 어느 질문의 답을 어떻게 (보드 A)
        l = 고른[0]
        q = (l.get("question") or {}).get("text")
        번호 = next((i + 1 for i, f in enumerate(flow) if q and f.get("text") == q), None)
        a = l.get("answer") or {}
        출처 = f"질문 {번호} 의 답" if 번호 else f"{TOOL.get(str(a.get('tool', '')).lower(), a.get('tool') or 'AI')} 답"
        how = {"viewed": "을 보고 씀", "edited": "을 붙여넣고 고침"}.get(l.get("kind"), "과 같음")
        body += [Spacer(1, 8 * X), P(칠(l, 110) + f" <font color='#71717a'>— {E(출처)}{how} (학생 확인)</font>", "ex")]
    elif 고른:                                        # 여러 문장 — 이어 쓰고 문단 범위 (보드 B)
        문단 = sorted({(l["result"].get("location") or {}).get("paragraph") for l in 고른} - {None})
        범위 = (f"문단 {문단[0]}" if len(문단) == 1 else f"문단 {문단[0]}~{문단[-1]}") + " · " if 문단 else ""
        body += [Spacer(1, 8 * X), P(" ".join(칠(l, 80) for l in 고른) + f" <font color='#71717a'>— {범위}나머지는 링크에서</font>", "ex")]
    남은 = []
    if d.get("rejected"):
        남은.append(f"Trace가 제안했지만 학생이 \"아니다\"라고 고른 연결 {d['rejected']}개")
    if d.get("unsure"):
        남은.append(f"학생이 판단을 보류한 제안 {d['unsure']}개 (원문은 보내지 않음)")
    if 남은:
        body += [Spacer(1, 4 * X), P(E("  ·  ".join(남은)), "note")]
    out += _칸(3, "결과물에 들어간 것", f"보고서 {rc['total']}문장" if rc.get("total") else f"학생이 확인한 연결 {len(links)}곳", body)

    # ── ④ 학생 설명 (보드 .qa: 상자 둘 · 간격 8px · padding 8px 12px · 12.5px/1.65) ──
    qa = []
    for i, (q, a) in enumerate((("AI 를 어디에 썼고, 무엇은 직접 했나요?", d.get("explain_use")),
                                ("AI 답을 고르거나 고칠 때 어떻게 확인했나요?", d.get("explain_check")))):
        qa += ([Spacer(1, 8 * X)] if i else []) + [_상자([[P(E(q), "qab"), Spacer(1, 2 * X), P(E(a or "학생이 쓰지 않음"), "qat")]],
                                                        [CW - 40 * X], pad=(8, 12))]
    out += _칸(4, "학생 설명", "", qa, last=True)

    # ── QR (맨 아래 · 보드 margin-top:auto · border-top 1px · padding-top 14px · QR 56px · 글 11px/1.7) ──
    근거 = ("출처 보기와 " if d.get("source") else "") + f"질문 {질문수}개 전체"
    글 = [P(f"<font name='PRS' color='#18181b'>근거 보기</font> — {E(근거)} · {E(url)}", "foot"),
         P("작업 중 기록된 그대로이며 점수나 판정은 없습니다. 출처 기록 없음은 직접 썼다는 뜻이 아니고, "
           "다른 기기에서 쓴 AI 는 기록되지 않습니다.", "foot")]
    qr = _qr(url, QR)

    def 바닥(canvas, _doc):
        canvas.saveState()
        y0 = MT
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(X)
        canvas.line(ML, y0 + FOOT_H, W - ML, y0 + FOOT_H)
        renderPDF.draw(qr, canvas, ML, y0)
        tw = CW - QR - 14 * X
        hs = [p.wrap(tw, 200)[1] for p in 글]
        y = y0 + QR / 2 + sum(hs) / 2
        for p, h in zip(글, hs):
            y -= h
            p.drawOn(canvas, ML + QR + 14 * X, y)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="v3", frames=[틀], onPage=바닥)])
    doc.build(out)
    return buf.getvalue()
