# -*- coding: utf-8 -*-
"""Trace 문서 PDF 공용 서식

build_plan.py (분업 가이드) 와 build_proposal.py (기획안) 가 같이 쓴다.
서식을 한 곳에서 고치면 두 문서가 같이 바뀐다.

★ 한글은 Monaco 글꼴에 글리프가 없어 빈칸으로 나온다.
  MONO 는 영문·기호에만 쓰고, 한글 강조는 색으로 한다. (실제로 겪은 문제다)
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, HRFlowable, CondPageBreak)

pdfmetrics.registerFont(TTFont("KR",  "/System/Library/Fonts/Supplemental/AppleGothic.ttf"))
pdfmetrics.registerFont(TTFont("KRS", "/System/Library/Fonts/Supplemental/AppleMyungjo.ttf"))
pdfmetrics.registerFont(TTFont("MONO", "/System/Library/Fonts/Monaco.ttf"))

INK    = colors.HexColor("#171717")
MUTED  = colors.HexColor("#6f6a63")
FAINT  = colors.HexColor("#9a948c")
RULE   = colors.HexColor("#e0dcd6")
PAPER  = colors.HexColor("#faf9f7")
PANEL  = colors.HexColor("#f2f0ec")
ORANGE = colors.HexColor("#c0603f")
GREEN  = colors.HexColor("#2c6e49")
BLUE   = colors.HexColor("#2d5a8a")
RED    = colors.HexColor("#a32020")

W, H = A4
M = 46
CW = W - 2 * M          # 본문 폭 503pt


def _S(name, **kw):
    base = dict(name=name, fontName="KR", fontSize=9.6, leading=16,
                textColor=INK, spaceAfter=0)
    base.update(kw)
    return ParagraphStyle(**base)


st = {
    "h1":    _S("h1", fontName="KRS", fontSize=21, leading=28, spaceAfter=4),
    "h2":    _S("h2", fontName="KRS", fontSize=14.5, leading=21, spaceAfter=7),
    "h3":    _S("h3", fontSize=10.8, leading=17, spaceAfter=4),
    "body":  _S("body", spaceAfter=7),
    "muted": _S("muted", textColor=MUTED, fontSize=9, leading=15, spaceAfter=6),
    "small": _S("small", textColor=MUTED, fontSize=8.3, leading=13.5, spaceAfter=4),
    "lead":  _S("lead", fontSize=11, leading=18.5, spaceAfter=9),
    "label": _S("label", fontSize=7.8, leading=12, textColor=FAINT, spaceAfter=3),
    "cell":  _S("cell", fontSize=8.6, leading=13.6),
    "cellm": _S("cellm", fontSize=8.6, leading=13.6, textColor=MUTED),
    "code":  _S("code", fontName="MONO", fontSize=8.6, leading=14),
    "quote": _S("quote", fontSize=9.4, leading=16, textColor=MUTED, spaceAfter=6),
}


def P(t, s="body"):
    return Paragraph(t, st[s])


def sp(h):
    return Spacer(1, h)


def rule(c=RULE, th=0.6):
    return HRFlowable(width="100%", thickness=th, color=c, spaceBefore=6, spaceAfter=9)


def code_block(lines, note=None):
    """영문·기호만 넣는 코드 상자 (한글 금지 — MONO 에 글리프가 없다)"""
    inner = "<br/>".join(l.replace(" ", "&nbsp;") for l in lines)
    t = Table([[Paragraph(inner, st["code"])]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), PANEL),
        ("BOX",          (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 11), ("RIGHTPADDING",  (0, 0), (-1, -1), 11),
        ("TOPPADDING",   (0, 0), (-1, -1), 9),  ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    out = [t]
    if note:
        out += [sp(3), P(note, "small")]
    return out + [sp(10)]


def callout(title, body, color=INK, bg=PANEL):
    inner = [Paragraph(f'<font color="{color.hexval()}">{title}</font>', st["h3"]),
             Paragraph(body, st["muted"])]
    t = Table([[inner]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), bg),
        ("LINEBEFORE",   (0, 0), (0, -1), 2.2, color),
        ("LEFTPADDING",  (0, 0), (-1, -1), 13), ("RIGHTPADDING",  (0, 0), (-1, -1), 13),
        ("TOPPADDING",   (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return [t, sp(11)]


def box(title, rows, color=INK, bg=PANEL, label_w=118):
    """구조 그림용 네모 상자. rows = [(왼쪽 라벨, 설명), …]

    ★ ASCII 그림을 안 쓰는 이유 — 한글은 MONO 글꼴에 글리프가 없어 빈칸이 된다.
      그래서 그림을 표로 그린다."""
    inner = []
    if title:                       # 제목이 없으면 빈 줄을 만들지 않는다
        inner.append([Paragraph(f'<font color="{color.hexval()}">{title}</font>',
                                st["h3"]), ""])
    for 라벨, 설명 in rows:
        inner.append([Paragraph(f'<b>{라벨}</b>', st["cell"]),
                      Paragraph(설명, st["cellm"])])
    t = Table(inner, colWidths=[label_w, CW - label_w - 26])
    스타일 = [
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",  (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if title:
        스타일 += [("SPAN", (0, 0), (1, 0)),
                   ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE)]
    t.setStyle(TableStyle(스타일))
    outer = Table([[t]], colWidths=[CW])
    outer.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), bg),
        ("BOX",          (0, 0), (-1, -1), 1.0, color),
        ("LEFTPADDING",  (0, 0), (-1, -1), 13), ("RIGHTPADDING",  (0, 0), (-1, -1), 13),
        ("TOPPADDING",   (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return [outer]


def arrow(label):
    return [sp(4), Paragraph(f'<para align="center"><font color="{FAINT.hexval()}">'
                             f'↓&nbsp;&nbsp;{label}</font></para>', st["small"]), sp(4)]


def table(header, rows, widths, aligns=None, first_bold=True, shade=None):
    data = [[Paragraph(f'<font color="{FAINT.hexval()}">{h}</font>', st["label"])
             for h in header]]
    for r in rows:
        data.append([Paragraph(c, st["cell"] if (i == 0 and first_bold) else st["cellm"])
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("LINEBELOW",   (0, 0), (-1, 0), 0.9, INK),
        ("LINEBELOW",   (0, 1), (-1, -2), 0.5, RULE),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",  (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if aligns:
        for i, a in enumerate(aligns):
            if a:                       # None 은 건너뛴다 (reportlab 이 거부한다)
                style.append(("ALIGN", (i, 0), (i, -1), a))
    for r in (shade or []):
        style.append(("BACKGROUND", (0, r), (-1, r), PANEL))
    t.setStyle(TableStyle(style))
    return [t, sp(12)]


def make_doc(path, title, header_right):
    """머리말·꼬리말이 붙은 A4 문서 틀을 만든다."""
    def page_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, W, H, stroke=0, fill=1)
        canvas.setFont("KRS", 8.5); canvas.setFillColor(FAINT)
        canvas.drawString(M, H - 30, "T R A C E")
        canvas.setFont("KR", 8)
        canvas.drawRightString(W - M, H - 30, header_right)
        canvas.setStrokeColor(RULE); canvas.setLineWidth(0.6)
        canvas.line(M, H - 38, W - M, H - 38)
        canvas.setFont("KR", 8); canvas.setFillColor(FAINT)
        canvas.drawCentredString(W / 2, 26, str(doc.page))
        canvas.restoreState()

    doc = BaseDocTemplate(path, pagesize=A4,
                          leftMargin=M, rightMargin=M, topMargin=52, bottomMargin=44,
                          title=title, author="Trace 팀")
    frame = Frame(M, 44, CW, H - 52 - 44, id="body",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=page_bg)])
    return doc
