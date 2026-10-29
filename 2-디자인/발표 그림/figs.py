"""중간발표 그림 4개 (SVG). python3 figs.py <출력 폴더>"""
import sys, os
from html import escape as E

OUT = sys.argv[1]
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
LINE, SURF, PANEL = "#d9d8d3", "#ffffff", "#f4f3ef"
BLUE, BLUE_BG = "#2a78d6", "#e8f1fc"
ORANGE, ORANGE_BG = "#eb6834", "#fdeee7"


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}">\n'
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker></defs>\n'
            f'<rect width="{w}" height="{h}" fill="{SURF}"/>\n{body}</svg>\n')


def text(x, y, s, size=18, fill=INK, weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{E(s)}</text>\n'


def lines(x, y, rows, size=16, fill=INK, gap=None, anchor="start", weight=400):
    gap = gap or int(size * 1.45)
    return "".join(text(x, y + i * gap, r, size, fill, weight, anchor) for i, r in enumerate(rows))


def box(x, y, w, h, fill=SURF, stroke=LINE, dash=False, r=10, sw=1.5):
    d = ' stroke-dasharray="6 5"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>\n'


def arrow(x1, y1, x2, y2, dash=False, color=INK2):
    d = ' stroke-dasharray="6 5"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"{d} marker-end="url(#arr)"/>\n'


def path(d, dash=False, color=INK2):
    da = ' stroke-dasharray="6 5"' if dash else ""
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{da} marker-end="url(#arr)"/>\n'


# ───────────────────────── 1. User Flow ─────────────────────────
def user_flow():
    W, H = 1600, 760
    b = text(40, 52, "User Flow — 교수는 계정도 설치도 없다", 30, weight=700)
    b += text(40, 84, "파란 칸 = 학생 · 주황 칸 = 교수 · 점선 = 새로 만들 것 (v2.1 점검)", 17, INK2)
    # 레인
    lanes = [("교수", 120, ORANGE), ("학생", 330, BLUE)]
    for name, y, c in lanes:
        b += box(40, y, 1520, 190 if name == "교수" else 380, PANEL, PANEL, r=14)
        b += text(64, y + 38, name, 22, c, 700)
    BW, BH = 210, 92

    def step(x, y, n, title, sub, c, bg, dash=False):
        s = box(x, y, BW, BH, bg, c, dash, sw=2)
        s += text(x + 16, y + 32, f"{n}  {title}", 18, INK, 700)
        s += lines(x + 16, y + 58, sub, 14, INK2, 20)
        return s

    # 교수
    b += step(140, 170, "①", "과제 공지", ["AI 허용 · Trace 내역서 첨부", "복붙 감점 (Trace 밖 · LMS)"], ORANGE, ORANGE_BG)
    b += step(1080, 170, "⑦", "한 줄 요약 보기", ["그대로 3 · 고침 11 · 기록 없음 0", "모아 보기: 그대로 많은 순"], ORANGE, ORANGE_BG)
    b += step(1330, 170, "⑧", "궁금한 학생만", ["AI 답과 문장 나란히", "물어볼 곳 → 면담"], ORANGE, ORANGE_BG)
    # 학생
    y1 = 400
    b += step(140, y1, "②", "기록 시작", ["교수 링크 · 동의 화면", "무엇이 기록되고 안 되는지"], BLUE, BLUE_BG)
    b += step(390, y1, "③", "평소처럼 작업", ["AI 대화 · 복사 · Word 문서", "언제든 멈춤 · 다시 시작"], BLUE, BLUE_BG)
    b += step(640, y1, "④", "제출 전 점검", ["걸린 문장 · 원문 나란히", "기준 표시 · 참고문헌 확인"], BLUE, BLUE_BG, dash=True)
    b += step(890, y1, "⑥", "확인 · 가리기 · 제출", ["이어진 곳 맞다/아니다", "내역서 1장 + 링크 첨부"], BLUE, BLUE_BG)
    # 고쳐 쓰기 분기
    b += box(640, 560, BW, 120, SURF, BLUE, True, sw=2)
    b += text(656, 590, "⑤  고쳐 쓰기 (학생이 직접)", 17, INK, 700)
    b += lines(656, 618, ["[인용 달기] 출처 표시", "[다시 쓰기] 내 말로", "AI가 대신 고치지 않음"], 14, INK2, 20)
    # 화살표
    b += path(f"M245,262 L245,400")                     # ①→②
    b += arrow(350, y1 + 46, 388, y1 + 46)            # ②→③
    b += arrow(600, y1 + 46, 638, y1 + 46)            # ③→④
    b += arrow(745, y1 + BH, 745, 558, dash=True)     # ④→⑤
    b += path(f"M850,620 L870,620 L870,{y1+70} L888,{y1+70}", dash=True)  # ⑤→⑥
    b += arrow(850, y1 + 30, 888, y1 + 30)            # ④→⑥ (걸린 것 없음)
    b += text(870, y1 - 10, "걸린 것 없음", 13, MUTED, 400, "middle")
    b += path(f"M1100,{y1} L1100,330 L1185,330 L1185,264")  # ⑥→⑦
    b += arrow(1290, 216, 1328, 216)                  # ⑦→⑧
    b += text(1110, 352, "내역서 링크", 13, MUTED)
    # 비고
    b += text(140, 728, "교수는 Trace 웹에서 [모아 보기 만들기]도 할 수 있다 (선택 · 비밀 링크, 로그인 없음). 판정 · 점수는 어디에도 없다.", 15, INK2)
    return svg(W, H, b)


# ───────────────────────── 2. 아키텍처 ─────────────────────────
def architecture():
    W, H = 1600, 860
    b = text(40, 52, "시스템 구조 · 데이터 흐름 — 원문은 학생 PC에 남는다", 30, weight=700)
    b += text(40, 84, "실선 = 지금 돌아감 (v0.1.13) · 점선 = 새로 만들 것 (v2.1)", 17, INK2)

    # 학생 PC
    b += box(40, 120, 640, 690, PANEL, BLUE, sw=2, r=16)
    b += text(64, 160, "학생 PC", 24, BLUE, 700)
    b += text(170, 160, "Python · 윈도우 / 맥", 16, INK2)

    def comp(x, y, w, h, title, sub, dash=False, stroke=LINE):
        s = box(x, y, w, h, SURF, stroke, dash)
        s += text(x + 16, y + 30, title, 18, INK, 700)
        s += lines(x + 16, y + 56, sub, 14, INK2, 20)
        return s

    b += comp(64, 185, 280, 112, "브라우저 확장", ["ChatGPT · Claude 웹 대화", "활성 탭은 사이트 이름만"])
    b += comp(376, 185, 280, 112, "기록기", ["복사 · 붙여넣기 · Word/PPT 변화", "데스크톱 AI 앱 · 키 입력 횟수만"])
    b += comp(64, 335, 592, 92, "① 가리기 → ② 해시 체인", ["개인정보를 먼저 가리고, 가린 글의 해시를 사슬로 묶는다 (core/chain.py)"])
    b += comp(64, 465, 280, 112, "원문 보관 (PC에만)", ["AI 질문 · 답 원문", "복사한 글 · 문서 버전"], stroke=BLUE)
    b += comp(376, 465, 280, 112, "출처 잇기", ["문장 ↔ AI 답 (core/match.py)", "그대로 · 고침 · 기록 없음"])
    b += comp(376, 600, 280, 112, "점검 엔진", ["연속 일치 · 바꿔 쓰기 유형", "인용 표시 · kiwi (PC 안)"], dash=True)
    b += comp(64, 600, 280, 112, "앱 화면 (pywebview)", ["기록 · 점검 · 고쳐 쓰기", "확인 · 가리기 · 제출"])
    b += arrow(204, 297, 204, 333)
    b += arrow(516, 297, 516, 333)
    b += arrow(204, 427, 204, 463)
    b += arrow(344, 521, 374, 521)
    b += arrow(516, 577, 516, 598, dash=True)
    b += arrow(376, 656, 346, 656)

    # 서버
    b += box(820, 300, 360, 250, SURF, INK2, sw=2, r=16)
    b += text(844, 340, "서버", 24, INK, 700)
    b += text(910, 340, "Flask · Render (싱가포르)", 16, INK2)
    b += lines(844, 378, ["· 로그인 (구글 · 카카오)", "· 해시 다시 계산 → 조작 확인", "· 내역서 PDF (reportlab)", "· 교수 확인 링크 (읽기 전용)", "· 모아 보기 (만들 것)"], 17, INK, 30)

    # DB
    b += box(820, 640, 360, 130, SURF, INK2, sw=2, r=16)
    b += text(844, 680, "DB", 24, INK, 700)
    b += text(892, 680, "Supabase (PostgreSQL)", 16, INK2)
    b += lines(844, 714, ["기록 이벤트(해시) · 내역서 · 링크", "점검 처리 결과 (원문 없음)"], 16, INK2, 24)
    b += f'<line x1="1000" y1="550" x2="1000" y2="638" stroke="{INK2}" stroke-width="2" marker-end="url(#arr)" marker-start="url(#arr)"/>\n'

    # 교수
    b += box(1320, 300, 240, 140, ORANGE_BG, ORANGE, sw=2, r=16)
    b += text(1344, 340, "교수", 24, ORANGE, 700)
    b += lines(1344, 376, ["브라우저로 링크만", "계정 · 설치 없음"], 17, INK, 28)
    b += arrow(1180, 370, 1318, 370)
    b += text(1196, 358, "비밀 링크", 14, INK2)

    # 바깥
    b += box(1320, 120, 240, 110, SURF, LINE, r=16)
    b += text(1344, 158, "구글 · 카카오", 18, INK, 700)
    b += text(1344, 186, "로그인만", 15, INK2)
    b += path("M1180,330 L1250,330 L1250,175 L1318,175")
    b += box(820, 120, 360, 110, SURF, LINE, True, r=16)
    b += text(844, 158, "Crossref API", 18, INK, 700)
    b += text(844, 186, "참고문헌이 실제로 있는지", 15, INK2)

    # PC → 밖
    b += arrow(680, 175, 818, 175, dash=True)
    b += text(694, 163, "참고문헌 목록만", 14, INK2)
    b += arrow(680, 380, 818, 380)
    b += lines(694, 368, ["기록 중: 해시만"], 14, INK2)
    b += arrow(680, 470, 818, 470)
    b += lines(694, 440, ["제출 때: 학생이 고른", "원문만 (가린 뒤)"], 14, INK2, 18)

    b += text(40, 840, "학생 글 · AI 답 원문은 기록하는 순간 PC에만 저장된다. 서버는 해시로 조작 여부만 확인하고, 원문은 학생이 제출 때 고른 것만 받는다.", 15, INK2)
    return svg(W, H, b)


# ───────────────────────── 3. ERD ─────────────────────────
def erd():
    W, H = 1640, 1000
    b = text(40, 52, "ERD — 지금 테이블에 3가지만 더한다", 30, weight=700)
    b += text(40, 84, "회색 = 지금 있음 · 파란 칸 = 새로 더함 · 1 ── N = 하나가 여러 개를 가짐", 17, INK2)
    HD, RH, BW = 40, 26, 270
    pos = {}

    def table(key, x, y, name, rows, new=False, new_rows=()):
        h = HD + RH * (len(rows) + len(new_rows)) + 12
        c = BLUE if new else INK2
        s = box(x, y, BW, h, SURF, BLUE if new else LINE, sw=2 if new else 1.5, r=8)
        s += f'<rect x="{x}" y="{y}" width="{BW}" height="{HD}" rx="8" fill="{BLUE_BG if new else PANEL}"/>\n'
        s += f'<rect x="{x}" y="{y+HD-8}" width="{BW}" height="8" fill="{BLUE_BG if new else PANEL}"/>\n'
        s += text(x + 14, y + 27, name, 18, c if new else INK, 700)
        if new:
            s += text(x + BW - 14, y + 27, "새로", 14, BLUE, 700, "end")
        for i, r in enumerate(rows):
            s += text(x + 14, y + HD + 20 + i * RH, r, 14, INK2)
        for j, r in enumerate(new_rows):
            yy = y + HD + 20 + (len(rows) + j) * RH
            s += f'<rect x="{x+6}" y="{yy-17}" width="{BW-12}" height="{RH-2}" rx="4" fill="{BLUE_BG}"/>\n'
            s += text(x + 14, yy, r + "  (새로)", 14, BLUE, 700)
        pos[key] = (x, y, BW, h)
        return s

    b += table("users", 40, 130, "users 학생", ["id", "email · name", "google_sub · kakao_sub", "deleted_at"])
    b += table("auth", 40, 330, "tokens · devices · login_tickets", ["user_id", "로그인 토큰 · 기기 · 로그인 표"])
    b += table("assign", 370, 130, "assignments 모아 보기", ["id · title · memo", "submit_token 학생용", "view_token_hash 교수용", "org (비워 둠) · created_at"], new=True)
    b += table("works", 370, 400, "works 과제", ["id · user_id", "title · ai_scope", "deleted_at"], new_rows=["assignment_id"])
    b += table("sessions", 700, 130, "sessions 기록 한 번", ["id · work_id", "root · head (체인 끝)", "chain_len · integrity_ok", "sealed_at · verified"])
    b += table("events", 1030, 130, "events 기록 이벤트", ["session_id · id · seq", "type · ts", "payload (원문 대신 해시)", "server_h"])
    b += table("bc", 1310, 130, "batches · contexts", ["session_id", "받은 묶음 · 작업 맥락"])
    b += table("st", 700, 470, "statements 내역서", ["id · work_id · user_id", "summary · result_counts", "explain_use · explain_check", "verified · problems"], new_rows=["retain_until"])
    b += table("msg", 1030, 400, "messages 보여 준 원문", ["statement_id", "role · text (가린 글)", "hash · match"])
    b += table("links", 1310, 400, "links 출처 결정", ["statement_id", "answer_hash · result_hash", "kind · decision"])
    b += table("red", 1030, 600, "redactions 가린 것", ["statement_id · event_id", "(내용은 안 옴)"])
    b += table("share", 1310, 600, "shares 교수 링크", ["token · statement_id", "expires_at · revoked_at"])
    b += table("checks", 1030, 770, "checks 점검 · 고쳐 쓰기", ["statement_id · 문장 위치", "rule 기준 · value 잰 값", "action 인용/다시 씀/그대로"], new=True)

    def rel(a, bkey, side_a="r", side_b="l", dy_a=0, dy_b=0, color=INK2):
        ax, ay, aw, ah = pos[a]
        bx, by, bw, bh = pos[bkey]
        pa = {"r": (ax + aw, ay + ah / 2 + dy_a), "b": (ax + aw / 2 + dy_a, ay + ah), "l": (ax, ay + ah / 2 + dy_a)}[side_a]
        pb = {"l": (bx, by + bh / 2 + dy_b), "t": (bx + bw / 2 + dy_b, by), "r": (bx + bw, by + bh / 2 + dy_b)}[side_b]
        if side_a == "b" and side_b == "t":
            d = f"M{pa[0]},{pa[1]} L{pa[0]},{(pa[1]+pb[1])/2} L{pb[0]},{(pa[1]+pb[1])/2} L{pb[0]},{pb[1]}"
        else:
            mx = (pa[0] + pb[0]) / 2
            d = f"M{pa[0]},{pa[1]} L{mx},{pa[1]} L{mx},{pb[1]} L{pb[0]},{pb[1]}"
        s = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8"/>\n'
        s += text(pa[0] + (6 if side_a == "r" else 6), pa[1] - 6 if side_a != "b" else pa[1] + 18, "1", 14, color, 700)
        s += text(pb[0] - (16 if side_b == "l" else -6), pb[1] - 6 if side_b != "t" else pb[1] - 6, "N", 14, color, 700)
        return s

    b += rel("users", "auth", "b", "t")
    b += rel("users", "works", "r", "l", 20, -20)
    b += rel("assign", "works", "b", "t", 0, 0, BLUE)
    b += rel("works", "sessions", "r", "l", -30, 0)
    b += rel("sessions", "events", "r", "l")
    b += rel("works", "st", "r", "l", 20, 0)
    b += rel("st", "msg", "r", "l", -50, 0)
    b += rel("st", "red", "r", "l", 0, 0)
    b += rel("st", "checks", "r", "l", 50, 0, BLUE)
    # 그룹 묶음 선 (sessions → batches · contexts, statements → links · shares) 은 위로 넘기는 선
    sx, sy, sw_, sh = pos["sessions"]
    bx, by, bw_, bh = pos["bc"]
    b += f'<path d="M{sx+sw_/2},{sy} L{sx+sw_/2},112 L{bx+bw_/2},112 L{bx+bw_/2},{by}" fill="none" stroke="{INK2}" stroke-width="1.8"/>\n'
    b += text(sx + sw_ / 2 + 6, 128, "1", 14, INK2, 700) + text(bx + bw_ / 2 + 6, 128, "N", 14, INK2, 700)
    tx, ty, tw, th = pos["st"]
    for k in ("links", "share"):
        kx, ky, kw, kh = pos[k]
        b += f'<path d="M{tx+tw/2},{ty+th} L{tx+tw/2},730 L{1610},730 L{1610},{ky+kh/2} L{kx+kw},{ky+kh/2}" fill="none" stroke="{INK2}" stroke-width="1.8"/>\n'
        b += text(kx + kw + 4, ky + kh / 2 - 6, "N", 14, INK2, 700)
    b += text(tx + tw / 2 + 6, ty + th + 20, "1", 14, INK2, 700)
    b += lines(40, 860, ["더하는 것 3가지", "· assignments: 모아 보기. 교수 계정 대신 비밀 토큰이 열쇠", "· works.assignment_id · statements.retain_until (보관 기간)", "· checks: \"점검 후 고침 N곳\"을 센다. 원문 · 고친 문장은 넣지 않음 (PC에 남음)"], 16, INK2, 26)
    return svg(W, H, b)


# ───────────────────────── 4. 설문 막대 ─────────────────────────
def survey():
    W, H = 1600, 640
    b = text(40, 52, "학생 설문 34명 — 켜는 이유는 바깥에서, 걸림돌은 감시", 30, weight=700)
    b += text(40, 84, "2026.10 · 여러 개 고름 · 공학 · 컴퓨터 계열 18명, 2학년 19명으로 치우침 → 경향만", 17, INK2)
    sets = [
        (40, "켜는 이유", [("받는 쪽이 요구하면", 20), ("가산점 · 우대", 17), ("의심받았을 때 증명", 11), ("내가 먼저 보고 고를 수 있으면", 8), ("내역서 자동", 4)]),
        (820, "꺼리는 이유", [("감시받는 느낌", 15), ("AI 사용이 드러나 불리할까 봐", 9), ("다른 탭 · 메신저까지 기록될까 봐", 6), ("받는 쪽이 오해할까 봐", 6), ("꺼려지지 않는다", 5), ("설치 · 설정이 귀찮다", 5), ("컴퓨터가 느려질까 봐", 2)]),
    ]
    LABW, MAXW, BH, GAP = 290, 380, 30, 18
    scale = MAXW / 20
    for x0, title, rows in sets:
        b += text(x0, 140, title, 22, INK, 700)
        for i, (lab, n) in enumerate(rows):
            y = 170 + i * (BH + GAP)
            b += text(x0 + LABW - 14, y + 21, lab, 16, INK, 400, "end")
            w = n * scale
            col = BLUE if i == 0 else "#b9cfe9"
            # 4px 둥근 끝 · 바닥선 쪽은 각지게
            b += f'<path d="M{x0+LABW},{y} L{x0+LABW+w-4},{y} Q{x0+LABW+w},{y} {x0+LABW+w},{y+4} L{x0+LABW+w},{y+BH-4} Q{x0+LABW+w},{y+BH} {x0+LABW+w-4},{y+BH} L{x0+LABW},{y+BH} z" fill="{col}"/>\n'
            b += text(x0 + LABW + w + 10, y + 21, f"{n}명", 16, INK, 700 if i == 0 else 400)
        yb = 170 + len(rows) * (BH + GAP) - GAP + 6
        b += f'<line x1="{x0+LABW}" y1="162" x2="{x0+LABW}" y2="{yb}" stroke="{INK2}" stroke-width="1.5"/>\n'
    b += text(40, 600, "→ 교수가 요구하는 길(B2B)로 시작하고, 학생 화면은 감시처럼 보이지 않게 (무엇이 기록되고 안 되는지 · 언제든 멈춤 · 보내기 전에 고름)", 17, INK2)
    return svg(W, H, b)


os.makedirs(OUT, exist_ok=True)
for name, fn in [("1-user-flow", user_flow), ("2-architecture", architecture), ("3-erd", erd), ("4-survey", survey)]:
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(fn())
print("ok")
