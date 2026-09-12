# -*- coding: utf-8 -*-
"""팀원(B)용 온보딩 가이드 PDF 생성기"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, KeepTogether, HRFlowable,
                                CondPageBreak)

# ── 폰트 ────────────────────────────────────────────────
pdfmetrics.registerFont(TTFont("KR",  "/System/Library/Fonts/Supplemental/AppleGothic.ttf"))
pdfmetrics.registerFont(TTFont("KRS", "/System/Library/Fonts/Supplemental/AppleMyungjo.ttf"))
pdfmetrics.registerFont(TTFont("MONO", "/System/Library/Fonts/Monaco.ttf"))

# ── 색 (화면 설계와 같은 값) ────────────────────────────
INK    = colors.HexColor("#171717")
MUTED  = colors.HexColor("#6f6a63")
FAINT  = colors.HexColor("#9a948c")
RULE   = colors.HexColor("#e0dcd6")
PAPER  = colors.HexColor("#faf9f7")
PANEL  = colors.HexColor("#f2f0ec")
ORANGE = colors.HexColor("#c0603f")
GREEN  = colors.HexColor("#2c6e49")
RED    = colors.HexColor("#a32020")

W, H = A4
M = 46

def S(name, **kw):
    base = dict(name=name, fontName="KR", fontSize=9.6, leading=16,
                textColor=INK, spaceAfter=0)
    base.update(kw)
    return ParagraphStyle(**base)

st = {
    "h1":    S("h1", fontName="KRS", fontSize=21, leading=28, spaceAfter=4),
    "h2":    S("h2", fontName="KRS", fontSize=14.5, leading=21, spaceAfter=7),
    "h3":    S("h3", fontSize=10.8, leading=17, spaceAfter=4, textColor=INK),
    "body":  S("body", spaceAfter=7),
    "muted": S("muted", textColor=MUTED, fontSize=9, leading=15, spaceAfter=6),
    "small": S("small", textColor=MUTED, fontSize=8.3, leading=13.5, spaceAfter=4),
    "lead":  S("lead", fontSize=11, leading=18.5, spaceAfter=9),
    "label": S("label", fontSize=7.8, leading=12, textColor=FAINT, spaceAfter=3),
    "cell":  S("cell", fontSize=8.6, leading=14),
    "cellm": S("cellm", fontSize=8.6, leading=14, textColor=MUTED),
    "code":  S("code", fontName="MONO", fontSize=9, leading=15, textColor=INK),
}

def P(t, s="body"):   return Paragraph(t, st[s])
def sp(h):            return Spacer(1, h)
def rule(c=RULE, th=0.6): return HRFlowable(width="100%", thickness=th, color=c,
                                            spaceBefore=6, spaceAfter=9)

def cmd(text, note=None):
    """터미널에 칠 명령어 한 줄"""
    rows = [[Paragraph(text.replace(" ", "&nbsp;"), st["code"])]]
    t = Table(rows, colWidths=[W - 2*M - 14])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), PANEL),
        ("BOX",        (0,0), (-1,-1), 0.6, RULE),
        ("LEFTPADDING",(0,0), (-1,-1), 11), ("RIGHTPADDING",(0,0),(-1,-1), 11),
        ("TOPPADDING", (0,0), (-1,-1), 8),  ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    out = [t]
    if note:
        out += [sp(3), P(note, "small")]
    out += [sp(8)]
    return out

def callout(title, body, color=INK, bg=PANEL):
    inner = [Paragraph(f'<font color="{color.hexval()}">{title}</font>', st["h3"]),
             Paragraph(body, st["muted"])]
    t = Table([[inner]], colWidths=[W - 2*M])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), bg),
        ("LINEBEFORE",  (0,0), (0,-1), 2.2, color),
        ("LEFTPADDING", (0,0), (-1,-1), 13), ("RIGHTPADDING",(0,0),(-1,-1), 13),
        ("TOPPADDING",  (0,0), (-1,-1), 10), ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    return [t, sp(11)]

def table(header, rows, widths, aligns=None):
    data = [[Paragraph(f'<font color="{FAINT.hexval()}">{h}</font>', st["label"]) for h in header]]
    for r in rows:
        data.append([Paragraph(c, st["cell"]) if i == 0 else Paragraph(c, st["cellm"])
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("LINEBELOW",   (0,0), (-1,0), 0.9, INK),
        ("LINEBELOW",   (0,1), (-1,-2), 0.5, RULE),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING",(0,0),(-1,-1), 9),
        ("TOPPADDING",  (0,0), (-1,-1), 7), ("BOTTOMPADDING",(0,0),(-1,-1), 7),
    ]
    if aligns:
        for i, a in enumerate(aligns):
            style.append(("ALIGN", (i,0), (i,-1), a))
    t.setStyle(TableStyle(style))
    return [t, sp(12)]

def steps(items):
    """번호 붙은 체크 항목"""
    data = []
    for i, (head, sub) in enumerate(items, 1):
        num = Paragraph(f'<font color="{ORANGE.hexval()}">{i}</font>', st["h3"])
        body = [Paragraph(head, st["h3"])]
        if sub:
            body.append(Paragraph(sub, st["small"]))
        data.append([num, body])
    t = Table(data, colWidths=[16, W - 2*M - 16])
    t.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING",(0,0),(-1,-1), 0),
        ("TOPPADDING",  (0,0), (-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW",   (0,0), (-1,-2), 0.4, RULE),
    ]))
    return [t, sp(12)]

# ── 페이지 장식 ─────────────────────────────────────────
def page_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, W, H, stroke=0, fill=1)
    # 머리말
    canvas.setFont("KRS", 8.5); canvas.setFillColor(FAINT)
    canvas.drawString(M, H - 30, "T R A C E")
    canvas.setFont("KR", 8)
    canvas.drawRightString(W - M, H - 30, "팀원 작업 가이드 · 2026-09-13")
    canvas.setStrokeColor(RULE); canvas.setLineWidth(0.6)
    canvas.line(M, H - 38, W - M, H - 38)
    # 꼬리말
    canvas.setFont("KR", 8); canvas.setFillColor(FAINT)
    canvas.drawCentredString(W/2, 26, str(doc.page))
    canvas.restoreState()

# ══════════════════════════════════════════════════════
# 본문
# ══════════════════════════════════════════════════════
F = []

# ── 표지 ──
F += [sp(52)]
F += [P("창작 과정 증명 서비스", "label")]
F += [Paragraph('<font size="30">Trace</font>', st["h1"]), sp(2)]
F += [P("팀원 작업 가이드", "h2")]
F += [P("창의프로젝트1 · 2026-2학기 · 박재완 교수 · 2인 1팀", "muted")]
F += [rule(INK, 1.4)]
F += [P("이 문서 하나만 따라 하면 환경 설치부터 발표 준비까지 됩니다. "
        "명령어는 한 줄씩 나눠 뒀으니 <font color=\"#171717\">위에서부터 차례대로</font> "
        "복사해서 터미널에 붙여 넣으세요.", "lead")]
F += callout("처음이라면 여기부터",
    "① GitHub 초대 수락 → ② 환경 설치(10분) → ③ 실행해서 화면 확인 → "
    "④ CHANGES.md 읽기 → ⑤ 아래 5장 「내가 할 일」.<br/><br/>"
    "막히면 바로 A에게 연락하세요. 혼자 30분 이상 붙잡지 마세요.", ORANGE)

F += [sp(4), P("한눈에 보기", "label")]
F += table(["", "내용"], [
    ["이 서비스가 하는 일", "창작 과정을 기록해 두고, 그 기록이 <font color='#171717'>나중에 고쳐지지 않았음</font>을 제3자에게 보여준다"],
    ["하지 않는 일", "AI 사용 여부를 판정하지 않는다. 지표는 자료이지 결론이 아니다"],
    ["이번 주 과제 요건", "한 페이지 구현 · JSON 데이터가 화면에 나타날 것 · <font color='#171717'>데이터 흐름에 집중</font>"],
    ["기술 범위", "HTML/CSS/JS + Flask + JSON 파일 (강의자료 STEP 1). React·서버DB·배포는 범위 밖"],
    ["저장소", "github.com/20233014-KYH/trace"],
], [92, W - 2*M - 92])

# ── 1. 환경 설치 ──
F += [rule(), P("1. 환경 설치", "h2")]
F += [P("맥 기본 <font color=\"#171717\">터미널</font> 앱을 엽니다. "
        "Command(⌘) + Space 를 누르고 \"터미널\"이라고 치면 나옵니다.", "body")]

F += [sp(3), P("① GitHub 초대를 먼저 수락하세요", "h3")]
F += [P("초대장이 메일이나 GitHub 알림으로 갑니다. 안 보이면 아래 주소로 직접 들어가서 "
        "Accept invitation 을 누르세요. <font color=\"#a32020\">7일 뒤 만료됩니다.</font>", "muted")]
F += cmd("https://github.com/20233014-KYH/trace/invitations")

F += [P("② 파이썬 환경을 만듭니다", "h3")]
F += [P("Anaconda 가 깔려 있어야 합니다. 없으면 anaconda.com 에서 받으세요.", "muted")]
F += cmd("conda create -n cp python=3.11 -y")
F += cmd("conda activate cp", "성공하면 줄 맨 앞에 (cp) 가 붙습니다.")
F += cmd("pip install flask")

F += [P("③ 코드를 받습니다", "h3")]
F += cmd("mkdir -p ~/dev && cd ~/dev")
F += cmd("git clone https://github.com/20233014-KYH/trace.git")
F += cmd("cd trace")

F += [P("④ 데모 데이터를 만듭니다", "h3")]
F += cmd("python seed.py",
         "이걸 먼저 돌려야 화면에 뭔가 나옵니다. data/ 폴더는 GitHub 에 올리지 않기 때문입니다 "
         "(각자 로컬에서 계속 바뀌는 파일이라 같이 쓰면 매번 충돌이 납니다).")

F += [P("⑤ 서버를 켭니다", "h3")]
F += cmd("python app.py")
F += [P("브라우저 주소창에 <font name=\"MONO\">127.0.0.1:5000</font> 을 칩니다. "
        "끄고 싶으면 그 터미널에서 Control + C 입니다.", "body")]

F += callout("맥에서 자주 걸리는 것 두 가지",
    "<font color=\"#171717\">5000번 포트</font> — 이상한 화면이나 403이 뜨면 "
    "시스템 설정 → 일반 → AirDrop 및 Handoff → <font color=\"#171717\">AirPlay 수신기 끄기</font>.<br/><br/>"
    "<font color=\"#171717\">터미널 탭 두 개</font> — 서버를 켠 탭에는 명령어를 칠 수 없습니다. "
    "⌘T 로 새 탭을 열어서 쓰세요. \"서버 켜는 탭 1개 + 명령어 치는 탭 1개\"로 나눠 쓰면 편합니다.")

# ── 2. 잘 됐는지 확인 ──
F += [rule(), P("2. 잘 됐는지 확인", "h2")]
F += [P("화면에서 이 다섯 가지가 보이면 정상입니다.", "body")]
F += steps([
    ("맨 위에 초록 상자 — “이 기록은 변조되지 않았습니다”",
     "빨강이면 chain.json 이 고쳐진 것입니다. python seed.py 를 다시 돌리세요."),
    ("데모 1과 데모 2의 곡선이 확연히 다른가",
     "데모 1은 막대가 오르내리고, 데모 2는 한 번 크게 튄 뒤 평평합니다. 이게 이 서비스의 핵심 장면입니다."),
    ("데모 3 카드에 파일 띠가 세 줄",
     "러프 1시간 12분 / 선화 2시간 38분 / 채색 4시간 8분, 합계 7시간 58분."),
    ("러프.procreate 이름 앞에 주황 점",
     "밖에서 이미지가 1장 들어왔다는 표시입니다."),
    ("작품 루트 해시 64자리",
     "증명서에 찍히고 외부 앵커에 고정될 값입니다."),
])

F += callout("빨간 글씨가 떠도 고장이 아닙니다",
    "<font name=\"MONO\" size=\"8.4\">WARNING: This is a development server</font> — "
    "“연습용 서버지 실제 서비스용은 아니다”라는 안내입니다. 과제 범위에선 정상입니다.<br/>"
    "<font name=\"MONO\" size=\"8.4\">GET /favicon.ico 404</font> — "
    "브라우저가 탭 아이콘을 찾다가 없어서 나는 것입니다. 무시하세요.", MUTED)

# ── 3. 최근에 크게 바뀐 것 ──
F += [rule(), P("3. 최근에 크게 바뀐 것 — 작품 계층", "h2")]
F += [P("기록의 단위가 <font color=\"#171717\">세션에서 작품으로</font> 올라갔습니다. "
        "증명서는 이제 파일 하나가 아니라 <font color=\"#171717\">작품 하나에 한 장</font> 나옵니다.", "body")]
F += [P("커미션 한 건이 러프 · 선화 · 채색 세 파일로 나뉘는데, 파일마다 증명서가 따로 나오면 "
        "의뢰인이 세 장을 받고 “이게 다 같은 그림 맞나요?”를 되물어야 하기 때문입니다.", "muted")]

F += [sp(4), P("데이터 구조", "label")]
F += cmd("works > files > sessions > snapshots")
F += table(["층", "무엇인가"], [
    ["작품", "창작물 하나. <font color='#171717'>증명서는 여기에 한 장</font>"],
    ["파일", "그 작품을 만들며 건드린 파일들 (러프 / 선화 / 채색 …)"],
    ["세션", "한 번 앉아서 작업한 구간"],
    ["스냅샷", "30초마다 남긴 해시 한 줄. <font color='#171717'>여기 안쪽은 하나도 안 바뀌었습니다</font>"],
], [58, W - 2*M - 58])

F += callout("파일을 묶는 방법 — 작업 중에는 묻지 않습니다",
    "“이 파일은 이 작품 건가요?” 팝업을 매번 띄우면 사흘이면 반사적으로 누르게 되고, "
    "그러면 그 동의가 아무것도 증명하지 못합니다. 그래서 세 겹으로 거릅니다.<br/><br/>"
    "① 기록 시작에서 <font color=\"#171717\">볼 앱을 먼저 고른다</font> "
    "(브라우저·메신저는 기본 제외) → ② 그 안에서 열린 파일은 조용히 쌓인다 → "
    "③ 종료할 때 <font color=\"#171717\">한 번만</font> 확인한다.<br/><br/>"
    "뺀 파일은 이름도 내용도 공개하지 않지만, "
    "<font color=\"#171717\">“뺐다”는 사실과 시각은 기록에 남습니다.</font> "
    "공백 구간을 지우지 않고 빗금으로 남기는 것과 같은 원칙입니다.")

F += [P("자세한 내용은 저장소의 <font name=\"MONO\" size=\"8.6\">CHANGES.md</font> 에 있습니다. "
        "받자마자 한 번 읽어 주세요.", "body"), sp(6)]

F += [P("데모 세 개가 무엇을 보여주는가", "h3")]
F += table(["작품", "시간", "붙여넣기", "되돌리기", "곡선"], [
    ["데모 1 — 처음부터 쓴 글",     "1시간 1분",  "0%",  "71회", "오르내림"],
    ["데모 2 — 붙여넣기가 많은 글", "5분",        "95%", "0회",  "거의 직선"],
    ["데모 3 — 파일 세 개짜리 그림","7시간 58분", "0%",  "362회", "파일 3개"],
], [150, 62, 56, 54, W - 2*M - 322])
F += [P("데모 1과 2는 <font color=\"#171717\">같은 에세이.docx</font> 입니다. "
        "데모 2가 글자는 더 많은데 시간은 1/12 입니다. "
        "기획안 6.2의 그림 두 개(탐색이 있는 과정 / 없는 과정)를 데이터로 만든 것입니다.", "muted")]
F += [P("제목에 “AI”라는 말은 일부러 넣지 않았습니다. "
        "“붙여넣기가 많다”는 <font color=\"#171717\">관찰된 사실</font>이지만 "
        "“AI로 썼다”는 <font color=\"#171717\">판정</font>이기 때문입니다.", "muted"), sp(6)]

# ── 4. 내가 할 일 ──
F += [CondPageBreak(180), rule(), P("4. 내가 할 일 (B · 검증·기획 담당)", "h2")]
F += [P("기획안 11.3 역할 분담 기준입니다. 위에서부터 급한 순서입니다.", "muted")]

F += [sp(4), P("① 데모 두 개를 에디터로 직접 만들기  — 가장 급함", "h3")]
F += [P("지금 화면에 있는 데모는 <font color=\"#a32020\">전부 프로그램이 만든 가짜 숫자</font>입니다. "
        "발표에서 “이거 실제로 쓴 건가요?”라고 물으면 답할 수 없습니다. "
        "B가 직접 써서 진짜 기록으로 바꿔야 합니다.", "body")]
F += [P("절차", "label")]
F += steps([
    ("화면 아래 “▸ 작성 영역 열기”를 누른다", None),
    ("작품 이름에 <font color=\"#c0603f\">직접 쓴 글</font>, 파일 이름에 "
     "<font color=\"#c0603f\">에세이.docx</font> 를 넣고 “기록 시작”",
     "20분 동안 아무 주제로 직접 씁니다. 고쳐 쓰고 지우고 되돌리기(⌘Z)도 실제로 하세요. 그 흔적이 곡선이 됩니다."),
    ("“기록 종료”를 누른다", None),
    ("작품 이름을 <font color=\"#c0603f\">붙여넣은 글</font> 로 바꾸고 다시 “기록 시작”",
     "다른 문서에서 1,000자쯤을 통째로 붙여 넣고 2~3분만에 끝냅니다."),
    ("두 작품의 곡선이 눈에 띄게 다른지 확인한다",
     "다르지 않으면 다시 하세요. <font color=\"#171717\">이 두 장면이 발표의 핵심입니다.</font>"),
])
F += callout("만들고 나면 반드시 사본을 뜨세요",
    "data 폴더는 GitHub 에 올라가지 않습니다. 직접 만든 기록은 그 노트북에만 있고, "
    "한 번 날아가면 <font color=\"#a32020\">다시 만들 수 없습니다.</font> "
    "아래 명령어로 사본을 떠 두고, USB 나 메일로도 한 부 챙겨 두세요.", RED,
    colors.HexColor("#fdf2f2"))
F += cmd("cp data/chain.json data/chain.demo-good.json")
F += [P("망가뜨렸을 때 되돌리기", "label")]
F += cmd("cp data/chain.demo-good.json data/chain.json")

F += [sp(4), P("② 코드 흐름을 설명할 수 있게 되기", "h3")]
F += [P("기획안 11.4 기준입니다. “코드를 받아 쓰더라도 왜 그렇게 동작하는지 설명할 수 있어야 한다.” "
        "B가 맡은 부분은 <font name=\"MONO\" size=\"8.6\">static/script.js</font> 입니다.", "body")]
F += table(["설명할 것", "어디를 보면 되나"], [
    ["이벤트를 어떻게 세는가",
     "editor 의 paste · keydown · input 핸들러. 붙여넣기는 input 보다 먼저 일어나서 따로 잡는다"],
    ["왜 events 와 totals 를 나눴나",
     "events 는 지난 30초의 변화량이라 서버로 보내고 비운다. totals 는 세션 누적이라 화면에 계속 쌓인다"],
    ["화면에 어떻게 그려지는가",
     "verify() → fetch('/api/verify') → renderVerdict / renderOverview / renderWorks"],
    ["왜 프런트가 계산하지 않나",
     "판단 재료를 만드는 것은 서버(app.py 의 summarize)의 일이고, 화면은 받은 것을 그리기만 한다"],
], [122, W - 2*M - 122])

F += [P("③ 화면에 한계 문구가 남아 있는지 확인", "h3")]
F += [P("기획안 4.4가 “정확한 척하지 않는 것이 이 서비스의 태도”라고 못박았습니다. "
        "화면 맨 아래 이 두 문장이 지워지지 않았는지 발표 전에 확인하세요.", "muted")]
F += callout("보증하는 것 / 보증하지 않는 것",
    "<font color=\"#171717\">보증하는 것</font> — 기록이 작성된 뒤 고쳐지지 않았다는 사실.<br/>"
    "<font color=\"#171717\">보증하지 않는 것</font> — 본인이 직접 작업했는지 여부. "
    "AI 사용 여부를 판정하지 않습니다. 어떤 파일을 한 작품으로 묶을지는 작성자가 정합니다. "
    "해석은 보는 사람의 몫입니다.", GREEN, colors.HexColor("#f0f6f2"))

F += [P("④ 인터뷰 8~10명", "h3")]
F += [P("기획안 8.3 표를 실제 이름으로 채우는 일입니다. "
        "특히 <font color=\"#171717\">커미션 작가 3명</font> 섭외 경로를 회의 전에 정해 오세요.", "muted")]
F += table(["대상", "인원", "핵심 질문"], [
    ["커미션 작가 (X·크몽)", "3", "AI 의심을 받은 적 있나. 그때 뭘 보냈나. 500원이면 내겠나"],
    ["교양 글쓰기 담당 교수", "1", "탐지기를 쓰나. 오탐 소명은 어떻게 처리하나"],
    ["오탐 피해 학생", "1", "그때 무엇이 있었으면 소명이 됐을까"],
    ["AI를 공개적으로 쓰는 창작자", "1", "“AI 초안 + 편집” 증명서도 쓸 의향이 있나"],
    ["커미션 의뢰인", "1", "증명서가 있으면 더 내겠나"],
    ["또래 (대조군)", "2", "과제에 스스로 켤 의향이 있나. 감시로 느끼나"],
], [140, 34, W - 2*M - 174])

F += [P("⑤ 데스크 크리틱 3문장 + 리허설", "h3")]
F += [P("기획안 11.7 입니다. 발표는 아래 네 컷으로 갑니다. 순서대로 손에 익혀 두세요.", "muted")]
F += steps([
    ("작성 영역에서 글을 쓰고 저장한다",
     "개발자도구(F12) Network 탭을 열어 두면 snapshot 요청이 흐르는 게 보입니다."),
    ("화면 위 초록 — “이 기록은 변조되지 않았습니다”", None),
    ("data/chain.json 을 텍스트 편집기로 열어 아무 content_hash 의 첫 글자를 바꾸고 저장",
     "발표 전에 어느 줄을 고칠지 미리 정해 두세요. 데모 3보다 <font color=\"#171717\">데모 2</font>가 스냅샷이 적어서 찾기 쉽습니다."),
    ("“다시 검증”을 누른다 → 빨강",
     "어느 파일의 몇 번 스냅샷에서 끊겼는지까지 화면에 나옵니다."),
])
F += [P("이 네 컷이 “데이터 흐름”과 “사후 조작 불가”를 한 장면에 담습니다.", "muted"), sp(6)]

# ── 5. 회의에서 정할 것 ──
F += [CondPageBreak(180), rule(), P("5. 회의에서 정할 것", "h2")]
F += [P("A 혼자 정할 수 없는 것들입니다. 읽고 의견을 정해서 오세요.", "muted")]

F += [sp(3), P("① 작성자 자기신고를 넣을 것인가  — 기획안에 없던 기능", "h3")]
F += [P("붙여넣기 직후에 “어디서 가져왔나요?”를 묻고 (AI 초안 / 인용 / 내 예전 원고 / 표시 안 함), "
        "그 답을 체인에 묶어 나중에 못 고치게 하는 기능입니다.", "body")]
F += [P("찬성 근거 — “무엇이 AI인가”를 서비스가 판정하지 않으면서 보는 사람의 질문에 답하는 유일한 길입니다. "
        "기획안 4.3의 “AI 초안을 붙여넣고 편집 → 드러남 → AI 초안 + 편집도 정직한 증명서”를 화면으로 옮긴 것입니다.", "muted")]
F += [P("반대 근거 — 기획안에 없던 기능이라 범위가 늘어납니다. 화면 설계에는 이미 들어가 있어서, "
        "여기가 엎어지면 검증 화면 문구도 같이 바뀝니다.", "muted"), sp(6)]

F += [P("② 체인 검증을 기획안에 맞출 것인가", "h3")]
F += [P("기획안 4.2는 “중간 스냅샷 하나만 바꿔도 <font color=\"#171717\">이후가 전부 어긋난다</font>”고 "
        "되어 있는데, 지금 코드는 <font color=\"#171717\">고친 그 한 줄만</font> 깨집니다.", "body")]
F += cmd("prev = snap[\"hash\"]",
         "다시 계산한 값(expected)이 아니라 파일에 적힌 값을 이전 해시로 쓰기 때문입니다.")
F += [P("이 한 줄을 <font name=\"MONO\" size=\"8.6\">prev = expected</font> 로 바꾸면 기획안대로 됩니다. "
        "지금 화면 설계는 코드 쪽(한 줄만 깨짐)에 맞춰 그려 뒀습니다. "
        "<font color=\"#171717\">발표에서 질문받기 쉬운 지점이라</font> 어느 쪽으로 통일할지 정해야 합니다.", "muted"), sp(6)]

F += [P("③ 외부 앵커를 이번 프로토타입에 넣을 것인가", "h3")]
F += [P("넣지 않기를 권합니다. 네트워크 변수 때문에 시연 중 깨질 위험이 있습니다. "
        "로드맵에만 두고 화면에는 자리만 비워 두는 쪽입니다. "
        "다만 앵커가 없으면 “위조자가 이후 해시를 전부 다시 계산하면?”이라는 질문에 "
        "시연으로 답할 수 없다는 점은 알고 있어야 합니다.", "muted"), sp(4)]
F += [P("이 밖에 기획안 전문과 PPT의 <font color=\"#171717\">가격표가 서로 다릅니다.</font> "
        "발표 전에 통일해야 합니다. (증명서 1건 500원 / 1,000원, 작가 무제한 월 4,900원 / 8,900원, "
        "기관 좌석 연 1,000원 / 1인 10,000원)", "muted")]

# ── 6. 링크 ──
F += [CondPageBreak(330), rule(), P("6. 자주 쓸 것", "h2")]
F += table(["", "주소 · 명령어"], [
    ["저장소",        "<font name=\"MONO\" size=\"8.4\">github.com/20233014-KYH/trace</font>"],
    ["화면 설계 10장", "<font name=\"MONO\" size=\"8.4\">claude.ai/code/artifact/2a6bae09-b4f8-4e3f-913d-6acba501ebed</font>"],
    ["바뀐 점 설명",   "저장소의 <font name=\"MONO\" size=\"8.4\">CHANGES.md</font>"],
    ["프로젝트 전반",  "저장소의 <font name=\"MONO\" size=\"8.4\">HANDOFF.md</font>"],
    ["작업 올리기",    "<font name=\"MONO\" size=\"8.4\">git add -A</font> → "
                       "<font name=\"MONO\" size=\"8.4\">git commit -m \"...\"</font> → "
                       "<font name=\"MONO\" size=\"8.4\">git push</font>"],
    ["A가 올린 것 받기","<font name=\"MONO\" size=\"8.4\">git pull</font>"],
], [86, W - 2*M - 86])

F += callout("화면 설계와 코드는 일부러 다릅니다",
    "화면 설계는 <font color=\"#171717\">쓰던 도구 위에 떠 있는 상주 프로그램</font>(수집기 B, 로드맵 W10 이후)을 그린 것이고, "
    "이번 주 프로토타입은 강의자료 STEP 1 범위라 <font color=\"#171717\">웹 에디터</font>로 갑니다.<br/><br/>"
    "발표에서는 이렇게 말하면 됩니다 — “프로토타입은 웹 에디터로 데이터 흐름을 증명하고, "
    "제품은 툴 무관 수집기로 간다.” 기획안 4.1에 수집기 A(웹)와 B(데스크톱)가 이미 나뉘어 있습니다.")

F += [sp(6), P("막히면 혼자 붙잡지 말고 A에게 연락하세요. "
               "명령어를 친 화면을 그대로 캡처해서 보내 주면 제일 빠릅니다.", "muted")]

# ── 만들기 ──
doc = BaseDocTemplate("docs/Trace_팀원_작업가이드.pdf", pagesize=A4,
                      leftMargin=M, rightMargin=M, topMargin=52, bottomMargin=42,
                      title="Trace 팀원 작업 가이드", author="창의프로젝트1 2인 1팀",
                      subject="창작 과정 증명 서비스 — 팀원 온보딩")
frame = Frame(M, 42, W - 2*M, H - 52 - 42, id="f", leftPadding=0, rightPadding=0,
              topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=page_bg)])
doc.build(F)
print("만들었습니다 -> docs/Trace_팀원_작업가이드.pdf")
