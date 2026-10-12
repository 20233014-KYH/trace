"""
statement_pdf.py — AI 활용 내역서 1장 PDF (기획서 10절 "요약 1장" · 7절 표)

  render(내역서, 링크주소) → PDF bytes      ← app.py 의 GET /api/share/<token>/pdf 가 부른다

★ PDF 는 학생이 과제와 함께 내는 종이 한 장이다. 교수는 이걸 훑고, 근거가 궁금할 때만 링크(QR)를 연다.
★ v3 (10/10 박상진): 투명성 한 줄 · 글을 쓴 과정(키보드로 친 글자 · 붙여넣은 글자 AI/다른 곳 · 지운 글자 + 날짜별 막대)
   · 학생 질문 두 개 · 교수 규칙은 학생이 넣었을 때만 · "말하는 것/않는 것" 대신 QR 옆 두 줄
★ v3 배치 (10/12 박상진 · 캔버스 ReportA3/B3): ① 어떻게 썼나 ② 질문 흐름 ③ 결과물에 들어간 것 ④ 학생 설명.
   연결 하나하나의 표("과제 속 AI 답")는 빼고 링크로 — 연결이 많으면 두 장이 넘어갔다. 늘 한 장.
   ③ 의 문장 수는 PC 가 보낸 result_counts (출처 보기와 같은 묶음 · 없으면 확인된 연결로만)
★ 점수·퍼센트·등급을 쓰지 않는다 (원칙 1). 횟수·글자 수·분·시각·원문 발췌만.

글꼴: Pretendard (server/fonts · SIL OFL 1.1 — 같이 둔 Pretendard-LICENSE.txt). Render(리눅스)엔 한글 글꼴이 없어서 넣어 둔다.
"""
import io
import os
import re
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
# 색 규칙 (화면 출처 보기 결정 C 와 같게 · 10/12): 일치·유사 빨강 · 붙여넣고 고침 파랑 · 보고 씀 파랑 (화면에선 점선 밑줄)
KIND = {"exact": ("일치", "#e5484d"), "similar": ("유사", "#e5484d"), "edited": ("붙여넣고 고침", "#3e63dd"),
        "viewed": ("보고 씀", "#3e63dd")}
# ③ 예시로 뽑지 않을 문장 — 전화번호 · 이메일 같은 개인 정보 (보고서 본문엔 있어도 내역서 예시로 크게 내세우지 않음)
_사적 = re.compile(r"(?<!\d)01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)|[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
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


def _멈춘시간(s):
    """10분 안쪽이면 초까지 (1분 27초) — 옛 요약엔 pause_seconds 가 없어 분으로"""
    초 = s.get("pause_seconds")
    if 초 is None:
        return _mins(s.get("pause_minutes"))
    if 초 < 600:
        return f"{초 // 60}분 {초 % 60}초" if 초 >= 60 else f"{초}초"
    return _mins(초 / 60)


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


def _sec(n, title, note, body):
    """번호 칸 + 제목 · 회색 설명 + 내용 (v3 번호 매긴 칸)"""
    head = PM(f"<font name='PRB' size='10'>{escape(title)}</font>"
              + (f"  <font color='#a3a29e' size='7.6'>{escape(note)}</font>" if note else ""), "memo")
    t = Table([[P(str(n), "cellm"), [head, Spacer(1, 4)] + body]], colWidths=[22, CW - 22])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return [t, HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=8, spaceAfter=8)]


# 결과물 문장 묶음 (화면 색 결정 C · 10/12 이름) — 칸 이름 · 색
RESULT = [("ai", "AI 답과 같음", "#e5484d"), ("other", "다른 곳에서 옴", "#e5484d"), ("edited", "붙여넣고 고침", "#3e63dd"),
          ("viewed", "보고 씀", None), ("none", "출처 기록 없음", "#a1a1aa")]
MAX_Q = 3             # 질문 흐름 — 한 장에 넣는 질문 수
# v3 ① 질문 쓰임새 (PC app/export.py 쓰임새 와 같은 키 · 순서)
USAGE = [("learn", "이해·자료 찾기"), ("fix", "고치기·검토"), ("write", "작성")]
옛쓰임 = {"understand": "learn", "find": "learn", "review": "fix", "polish": "fix"}     # 10/12 전 내역서는 다섯 칸 → 셋으로 합쳐 그림


def _쓰임수(uc):
    out = {}
    for k, n in (uc or {}).items():
        out[옛쓰임.get(k, k)] = out.get(옛쓰임.get(k, k), 0) + n
    return out


def _칩(items):
    """[(수, 이름)] → 같은 너비 칩 한 줄 (캔버스 ReportA3 · .uc 110px 를 A4 로 줄인 크기). 숫자 칸 너비를 고정해 이름이 줄 맞음.
    0 인 칩은 흐리게 테두리만"""
    칸, 틈, 수칸 = 82, 4, 11
    cells, widths, style = [], [], [("VALIGN", (0, 0), (-1, -1), "MIDDLE")] + [
        (k, (0, 0), (-1, -1), 0) for k in ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")]
    for i, (n, 이름) in enumerate(items):
        색 = "#18181b" if n else "#a3a29e"
        안 = Table([[PM(f"<font name='PRB' size='10' color='{색}'>{n}</font>", "cell"),
                    PM(f"<font color='{'#52525b' if n else '#a3a29e'}'>{escape(이름)}</font>", "cell")]],
                  colWidths=[수칸 + 6, 칸 - 수칸 - 6], rowHeights=[20])
        안.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 6),
                               ("LEFTPADDING", (1, 0), (1, 0), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (1, 0), (1, 0), 1.5),   # 작은 이름 글자를 숫자와 같은 줄(밑선)에
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("ROUNDEDCORNERS", [7, 7, 7, 7])]
                              + ([("BACKGROUND", (0, 0), (-1, -1), SOFT)] if n else [("BOX", (0, 0), (-1, -1), 0.6, LINE)])))
        cells += [안, ""]
        widths += [칸, 틈]
    t = Table([cells[:-1]], colWidths=widths[:-1], hAlign="LEFT")
    t.setStyle(TableStyle(style))
    return t
MAX_EX = 2            # 결과물에 들어간 것 — 보여 주는 문장 예


def render(d, url):
    """d = _내역서_내용(교수용) + work · author · expires_at. url = 교수 확인 링크.
    v3 (캔버스 6 · ReportA3/B3): 머리 · 투명성 한 줄 → 글을 쓴 과정 | 언제 작업했나 → ① 어떻게 썼나 → ② 질문 흐름
    → ③ 결과물에 들어간 것 → ④ 학생 설명 → QR. 연결 하나하나의 표는 PDF 에 넣지 않고 링크로 (늘 한 장)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=M - 6, bottomMargin=M - 6,
                            title=f"AI 활용 내역서 · {(d.get('work') or {}).get('title') or ''}", author="Trace")
    s = d.get("summary") or {}
    ai = s.get("ai") or {}
    links = d.get("links") or []
    out = []

    # ── 머리 ──
    out.append(P("AI 활용 내역서 · Trace", "brand"))
    out.append(P((d.get("work") or {}).get("title") or "제목 없는 과제", "title"))
    sub = []
    if d.get("author"):
        sub.append(f"{d['author']} (계정 이름 · Trace가 신원을 확인하지 않음)")
    if s.get("sessions"):
        sub.append(f"{_when(s.get('first_at'))[5:10].replace('-', '/')} – {_when(s.get('last_at'))[5:10].replace('-', '/')}"
                   f" · 기록 {s['sessions']}번 · {_mins(s.get('minutes'))}")
    sub.append(f"만든 시각 {_when(d.get('created_at'))} · 내역서 번호 {str(d.get('id', ''))[:8]}")
    out += [Spacer(1, 2), P("  ·  ".join(sub), "sub"), Spacer(1, 6)]

    # ── 투명성 한 줄: 서버 일치 · 도구(모델) · 멈춤 · 가림 · 지운 기록 ──
    probs = d.get("problems") or []
    일치 = (f"<font color='#d44c47'>● 서버 기록과 다릅니다 ({len(probs)}개)</font>" if probs
            else "<font color='#448361'>●</font> 서버 기록과 일치")
    멈춤 = f"잠깐 멈춤 {s.get('pauses', 0)}번 · {_멈춘시간(s)}" if s.get("pauses") else "멈춤 없음"   # 10분 안쪽은 초까지 (김용현 #43)
    지운 = len(s.get("deleted_sessions") or [])
    줄 = " &nbsp;·&nbsp; ".join([일치, escape(_도구(d)), escape(멈춤),
                                f"가림 {d['redacted']}곳" if d.get("redacted") else "가림 없음",
                                f"지운 기록 {지운}개" if 지운 else "지운 기록 없음"])
    out += [PM(줄, "small"), HRFlowable(width="100%", thickness=1.2, color=INK, spaceBefore=6, spaceAfter=8)]
    if d.get("ai_scope"):                                 # 교수 AI 규칙 — 학생이 넣었을 때만 (10/10)
        out += [PM(f"<font color='#787774'>교수 AI 규칙</font> &nbsp; {escape(d['ai_scope'])}", "memo"), Spacer(1, 6)]

    # ── 글을 쓴 과정 | 언제 작업했나 ──
    if s:
        p = s.get("pastes") or {}
        left = [PM("<font name='PRB'>글을 쓴 과정</font>", "memo"), Spacer(1, 4)]
        for v, k in ((f"{s.get('typed', 0):,}자", "키보드로 친 글자"),
                     (f"{p.get('chars', 0):,}자", f"붙여넣은 글자 · AI {p.get('from_ai_chars', 0):,} · 다른 곳 "
                      f"{p.get('from_other_chars', 0):,}" + (f" · 출처 기록 없음 {p['unknown_chars']:,}" if p.get("unknown_chars") else "")),
                     (f"{s.get('deleted', 0):,}자", "지운 글자")):
            left += [P(v, "v"), P(k, "vs"), Spacer(1, 3)]
        days = s.get("days") or []
        right = [PM(f"<font name='PRB'>언제 작업했나</font> <font color='#a3a29e' size='7.6'>· {len(days)}일 · 기록 {s.get('sessions', 0)}번</font>", "memo"),
                 Spacer(1, 6)]
        right += [_막대(days, CW * 0.66)] if days else [P("작업 시간 기록이 없습니다.", "small")]
        if len(days) > 7:
            right.append(P(f"최근 7일만 — 전체 {len(days)}일은 링크에서", "small"))
        top = Table([[left, right]], colWidths=[CW * 0.32, CW * 0.68])
        top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        out += [top, HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=6, spaceAfter=8)]

    # ── ① 어떻게 썼나 — 질문 쓰임새 칩 (PC 가 질문 글을 규칙으로 나눈 수) ──
    답들 = {(l.get("answer") or {}).get("text") for l in links if l.get("answer")}
    쓰임 = len(답들)
    질문수, 답수 = ai.get("questions", 0), ai.get("answers", 0)
    도구별 = " · ".join(f"{TOOL.get(str(t).lower(), t)} {n}" for t, n in (ai.get("tools") or {}).items())
    uc = d.get("usage_counts")
    if uc:
        uc = _쓰임수(uc)
        body = [_칩([(uc.get(k, 0), 이름) for k, 이름 in USAGE]),
                Spacer(1, 4), P("쓰임새는 질문 글의 낱말로 나눔 (규칙)" + (f" · {도구별}" if 도구별 else ""), "small")]
    else:                                                 # 예전 내역서 (쓰임새 수를 안 보냄)
        body = [P(f"질문은 {질문수}번 했고, 그중 답 {쓰임}개의 글이 결과물에 들어갔습니다.", "memo")]
        if 도구별:
            body.append(P(f"도구별 질문 · {도구별}", "small"))
    out += _sec(1, "어떻게 썼나", f"AI 에 한 질문 {질문수} · 결과물에 글이 들어간 답 {쓰임} · 참고만 {max(답수 - 쓰임, 0)}", body)

    # ── ② 질문 흐름 — 학생이 고른 대표 질문 (시간 순 · 최대 3) ──
    flow = d.get("flow")
    if flow is None:                                      # 예전 내역서 — 결과물에 글이 들어간 질문을 시간 순으로
        flow, 본 = [], set()
        for l in sorted(links, key=lambda l: ((l.get("answer") or {}).get("ts") or "")):
            q = l.get("question") or {}
            if q.get("text") and q["text"] not in 본:
                본.add(q["text"])
                flow.append({"text": q["text"], "tool": (l.get("answer") or {}).get("tool"), "usage": None, "used": True})
        flow = flow[:MAX_Q]
        note = "결과물에 글이 들어간 질문 · 시간 순"
    else:
        note = "학생이 고른 대표 흐름"
    이름 = dict(USAGE)
    body = []
    for f in flow[:MAX_Q]:
        꼬리 = " · ".join(x for x in (이름.get(옛쓰임.get(f.get("usage"), f.get("usage"))), TOOL.get(str(f.get("tool", "")).lower(), f.get("tool")),
                                     "" if f.get("ok", True) else "⚠ 기록 당시와 다름") if x)
        body.append(PM(f"<font color='#37352f'>●</font>&nbsp; \"{escape(_cut(f['text'], 64))}\""
                       + (f" <font color='#787774'>· {escape(꼬리)}</font>" if 꼬리 else ""), "memo"))
    if not body:
        body.append(P("학생이 고른 질문이 없습니다.", "small"))
    else:
        n = sum(1 for f in flow[:MAX_Q] if f.get("used"))
        k = len(flow[:MAX_Q])
        body.append(P(("세 질문" if k == 3 else f"질문 {k}개") + " 모두 답의 글이 결과물에 들어가지 않음" if n == 0
                      else f"{k}개 중 {n}개는 답의 글이 결과물에 들어감", "small"))
    out += _sec(2, "질문 흐름", note, body)

    # ── ③ 결과물에 들어간 것 — 문장 수 (PC 출처 보기와 같은 묶음) ──
    rc = d.get("result_counts")
    if not rc:                                            # 예전 내역서 (숫자를 안 보냄) — 학생이 확인한 연결로만
        k = [l.get("kind") for l in links]
        rc = {"ai": k.count("exact") + k.count("similar"), "edited": k.count("edited"), "viewed": k.count("viewed")}
    칸 = []
    for key, name, color in RESULT:
        n = rc.get(key)
        if n is None or (key == "other" and not n):
            continue
        표 = f"<u><font color='#3e63dd'>{escape(name)}</font></u>" if color is None else f"<font color='{color}'>■</font> {escape(name)}"
        칸.append(f"{표} <font name='PRB'>{n}</font>")
    body = [PM(" &nbsp;&nbsp; ".join(칸), "memo")]
    # 예시 = 학생이 확인한 연결 중 긴 문장 (제목 같은 짧은 줄 · 개인 정보가 든 문장은 뺌) — 보고서 순서대로
    후보 = [l for l in links if len((l.get("result") or {}).get("text") or "") >= 20 and not _사적.search(l["result"]["text"])]
    고른 = sorted(sorted(후보, key=lambda l: -len(l["result"]["text"]))[:MAX_EX], key=후보.index)
    예 = 고른
    for l in 예:
        kind, color = KIND.get(l.get("kind"), ("", "#787774"))
        a = l.get("answer") or {}
        도구 = TOOL.get(str(a.get("tool", "")).lower(), a.get("tool") or "AI")
        body.append(PM(f"<font color='{color}'>●</font>&nbsp; {escape(_cut(l['result']['text'], 80))} "
                       f"<font color='#787774'>— {escape(도구)} 답 · {escape(kind)} (학생 확인)</font>", "small"))
    남은 = []
    if d.get("rejected"):
        남은.append(f"Trace가 제안했지만 학생이 \"아니다\"라고 고른 연결 {d['rejected']}개")
    if d.get("unsure"):                                   # 연결 확인 "잘 모르겠음" — 개수만 (김용현 #43)
        남은.append(f"학생이 판단을 보류한 제안 {d['unsure']}개 (원문은 보내지 않음)")
    if 남은:
        body.append(P("  ·  ".join(남은), "small"))
    note = f"보고서 {rc['total']}문장" if rc.get("total") else f"학생이 확인한 연결 {len(links)}곳"
    out += _sec(3, "결과물에 들어간 것", note + " · 문장마다 출처는 링크에서", body)

    # ── ④ 학생 설명 ──
    qa = Table([[P("AI 를 어디에 썼고, 무엇은 직접 했나요?", "k")], [P(d.get("explain_use") or "학생이 쓰지 않음", "memo")],
                [P("AI 답을 고르거나 고칠 때 어떻게 확인했나요?", "k")], [P(d.get("explain_check") or "학생이 쓰지 않음", "memo")]],
               colWidths=[CW - 22])
    qa.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 2), (-1, 2), 6)]))
    out += _sec(4, "학생 설명", "", [qa])[:1]

    # ── QR 옆 두 줄 ──
    link = Table([[_qr(url), [PM(f"<font name='PRB'>근거 보기</font> — 문장마다 출처 · 질문 전체 &nbsp;<font color='#337ea9'>{escape(url)}</font>", "cell"),
                             Spacer(1, 3),
                             P("작업 중 기록된 그대로이며 점수나 판정은 없습니다. 출처 기록 없음은 직접 썼다는 뜻이 아니고, "
                               "다른 기기에서 쓴 AI 는 기록되지 않습니다.", "small"),
                             P(f"링크는 {_when(d.get('expires_at'))}까지 열립니다.", "small")]]],
                 colWidths=[74, CW - 74])
    link.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                              ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    out += [Spacer(1, 12), KeepTogether([link])]

    def 바닥(canvas, _doc):
        canvas.saveState()
        canvas.setFont("PR", 7)
        canvas.setFillColor(FAINT)
        canvas.drawString(M, 22, "Trace · 원문은 학생 PC에 있고, 학생이 고른 것만 링크로 공유됩니다")
        canvas.drawRightString(W - M, 22, f"{_doc.page}쪽")
        canvas.restoreState()

    doc.build(out, onFirstPage=바닥, onLaterPages=바닥)
    return buf.getvalue()
