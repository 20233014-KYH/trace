# -*- coding: utf-8 -*-
"""교수님 템플릿(창의프로젝트_서비스계획수립-1.pptx)을 우리 프로젝트 내용으로 채운다."""
import copy as _copy
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.oxml.ns import qn

SRC = "/Users/yonghyeonkim/Downloads/창의프로젝트_서비스계획수립-1.pptx"
OUT = "창의프로젝트_서비스계획수립_Trace.pptx"

prs = Presentation(SRC)
S1, S2, S3 = prs.slides[0], prs.slides[1], prs.slides[2]

def shp(slide, name):
    for s in slide.shapes:
        if s.name == name: return s
    raise KeyError(name)

def table(slide):
    for s in slide.shapes:
        if s.has_table: return s.table
    raise KeyError("table")

def fill_tf(tf, lines, size=None, space_after=2):
    """템플릿 run 의 서식(글꼴·색)을 유지한 채 내용만 바꾼다."""
    p0 = tf.paragraphs[0]
    proto = None
    if p0.runs:
        el = p0.runs[0]._r.find(qn('a:rPr'))
        if el is not None: proto = _copy.deepcopy(el)
    tf.clear()
    tf.word_wrap = True
    for i, line in enumerate(lines):
        gap = space_after
        if isinstance(line, tuple):          # ("문장", 아래여백)
            line, gap = line
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        r = p.add_run(); r.text = line
        if proto is not None:
            old = r._r.find(qn('a:rPr'))
            if old is not None: r._r.remove(old)
            r._r.insert(0, _copy.deepcopy(proto))
        if size: r.font.size = Pt(size)

def fill(slide, name, lines, size=None, space_after=2):
    fill_tf(shp(slide, name).text_frame, lines, size, space_after)

def cell(tb, r, c, lines, size=9.5):
    fill_tf(tb.cell(r, c).text_frame, lines, size, space_after=1)

def add_row(tb):
    tr = _copy.deepcopy(tb._tbl.tr_lst[-1])
    tb._tbl.append(tr)
    for c in range(len(tb.columns)):
        tb.cell(len(tb.rows) - 1, c).text_frame.clear()

# ══════════════════════════════════════════════════════════
# 1쪽 — 문제 발견 및 정의와 기반 문헌
# ══════════════════════════════════════════════════════════
fill(S1, "직사각형 12", ["창의프로젝트   서비스 계획 수립:  김용현 · [팀원 이름]"])
fill(S1, "직사각형 7", ["문제를 뒷받침하는 자료"])

fill(S1, "직사각형 5", [
    "대상 ·  컴퓨터로 배우고 과제를 만드는 학습자, 그리고 이를 지도하는 교육자",
    "상황 ·  학습이나 제작을 마친 뒤, 그 과정을 돌아보려 할 때",
    "제약 ·  결과물만 남고 과정은 사라진다. AI 를 쓰면 막힌 지점조차 남지 않는다",
    "학습자 ·  무엇을 배웠고 어디서 막혔는지 확인할 수 없다",
    "교육자 ·  학습이 어디서 일어났는지 볼 수 없다",
], size=14, space_after=6)

fill(S1, "직사각형 6", [
    "확인된 사실 ·  LLM 으로 쓴 집단은 자기 글을 기억하지 못했다 (78%, 동료심사 전 공개본)",
    "팀의 추정 ·  과정을 되돌아보게 하면 그 손실을 줄일 수 있다 → RQ1 로 검증 예정",
    "이번 범위 ·  컴퓨터에서 일어난 학습 · 제작 과정의 ‘기록과 회고’ 에 한정한다.",
    "                    이해도 측정과 AI 사용 여부 판정은 범위 밖에 둔다",
], size=12, space_after=4)

t1 = table(S1)
cell(t1, 1, 1, ["MIT Media Lab (2025) — 54명 EEG 실험",
                "LLM · 검색 · 무도구 세 집단의 에세이 작성 비교"], 9.5)
cell(t1, 1, 2, ["LLM 집단은 뇌 연결성이 가장 약했다.",
                "78% 가 자기 글을 한 구절도 인용 못 함",
                "→ 회고가 불가능하다"], 9)
cell(t1, 2, 1, ["Vanderbilt University (2023.08) — Turnitin",
                "AI 탐지기 비활성화 공지와 그 근거"], 9.5)
cell(t1, 2, 2, ["탐지 · 금지로 푸는 방식은 한계에 부딪혔다.",
                "과정을 남기는 접근이 따로 필요하다"], 9)
cell(t1, 3, 1, ["박재완 교수 인터뷰 (2026.09.16)",
                "학생 · 교강사 인터뷰 8~10명 진행 예정"], 9.5)
cell(t1, 3, 2, ["교육 현장의 문제로 확인.",
                "‘과정에 대한 가치’ 가 핵심이라는 지적",
                "(학습자 측은 아직 미검증)"], 9)

fill(S1, "직사각형 10", [
    "“컴퓨터로 배우고 만드는 학습자와 이를 지도하는 교육자는, 학습이 끝난 뒤 그 과정을 돌아보려 할 때,",
    "결과물만 남고 과정은 기록되지 않기 때문에, 무엇을 배웠고 어디서 막혔는지 확인할 수 없다.”",
], size=17.5, space_after=3)

fill(S1, "직사각형 11", [
    "MIT Media Lab (2025). Your Brain on ChatGPT: Accumulation of Cognitive Debt when Using an AI Assistant for Essay Writing Task. arXiv:2506.08872 — 54명 대상, 동료심사 전 공개본   ·   "
    "Vanderbilt University (2023.08.16). Guidance on AI Detection and Why We’re Disabling Turnitin’s AI Detector.",
    "박재완 교수 인터뷰 (2026.09.16, 대면)   ·   통계는 각 문헌의 조사 대상·기간을 그대로 인용했으며, 팀이 추가 가공한 수치는 없음",
], size=9.5, space_after=1)

print("1쪽 완료")

# ══════════════════════════════════════════════════════════
# 2쪽 — 유사사례의 한계와 Research Questions
# ══════════════════════════════════════════════════════════
fill(S2, "직사각형 11", ["창의프로젝트   서비스 계획 수립:  김용현 · [팀원 이름]"])

t2 = table(S2)
cell(t2, 1, 1, ["Grammarly Authorship — Google 문서에서 글 쓰는 학생  ·  Turnitin Clarity — 기관이 계약한 학생",
                "Google 문서 버전 기록 — 같은 문서를 쓰는 모든 사람"], 9.5)
cell(t2, 1, 2, ["앞 둘은 ‘특정 도구 안’ 에서만 동작한다. 버전 기록은 도구를 가리지 않지만",
                "글에만 해당한다. 여러 앱을 오가며 배우는 학습자에게는 셋 다 부족하다"], 9.5)
cell(t2, 2, 1, ["Authorship — 타이핑 · 붙여넣기 · AI 요청을 문장 단위로 구분해 표시하고 과정을 재생",
                "버전 기록 — 저장 시점마다 문서 전체를 보관"], 9.5)
cell(t2, 2, 2, ["‘출처를 구분해 보여준다’ 는 방식은 유효하다. 다만 셋 다 교육자에게",
                "보고하는 형태이고, 학습자가 스스로 돌아보는 화면은 없다"], 9.5)
cell(t2, 3, 1, ["Authorship — 자기 에디터 밖은 보지 못하고 기록을 봉인하는 장치가 없다",
                "버전 기록 — 남아는 있으나 읽을 수 있는 형태가 아니어서 실제로 회고에 쓰이지 않는다"], 9.5)
cell(t2, 3, 2, ["미해결 문제 = ① 도구를 가리지 않는 수집  ② 학습자 본인이 돌아볼 수 있는 형태",
                "③ 필요할 때만 제3자에게 보이는, 고칠 수 없는 기록"], 9.5)

fill(S2, "직사각형 5", [
    "차별점:  “기존 사례는 기록을 남기더라도 학습자가 되돌아볼 형태로 주지 않으므로,",
    "우리는 도구에 상관없이 과정을 모아 스스로 회고하게 하고, 필요할 때만 봉인해 증명하는 방식을 제안한다.”",
], size=15.5, space_after=3)

fill(S2, "직사각형 7", [
    "RQ1 ·  과정 기록을 되돌아보게 하면, 학습자가 자신이 막혔던 지점을",
    ("          결과물만 볼 때보다 더 많이 찾아내는가?  (Learn)", 10),
    "RQ2 ·  앱 전환 · 클립보드 · 파일 변화만으로, 어디서 막혀 AI 로 넘어갔는지를",
    ("          도구와 무관하게 식별할 수 있는가?  (수집)", 10),
    "RQ3 ·  과정 기록을 함께 제출하면, 교육자가 학습이 일어난 지점을",
    "          결과물만 볼 때보다 더 정확히 판단하는가?  (Proof)",
], size=11.5, space_after=1)

fill(S2, "직사각형 9", [
    "RQ1  지표 — 회고에서 지목한 ‘막힌 지점’ 수 · 실제 기록과의 일치율",
    ("          방법 — 같은 학생 20명에게 기록 없이 회고 / 기록 보며 회고를 교차 실시", 10),
    "RQ2  지표 — 외부 유입 구간 식별 재현율 · 오탐률",
    ("          방법 — Word · PPT · Photoshop · VSCode 에서 붙여넣기 시나리오 각 20회 실행", 10),
    "RQ3  지표 — 교육자의 판단과 실제 작성 과정의 일치율",
    "          방법 — 과정 기록 있음 / 없음 두 조건으로 과제 20건 평가 비교",
], size=10, space_after=1)

fill(S2, "직사각형 10", [
    "출처: Grammarly Authorship (grammarly.com/authorship) · Turnitin Clarity · Google 문서 버전 기록 — 각 제품의 공개 문서 기준.",
    "‘학습자용 회고 화면이 없다’ · ‘기록 봉인 장치가 없다’ 는 공개 문서에 해당 기능이 없다는 점에 근거한 팀의 판단이며, 별도 실험으로 확인한 사실은 아님.",
], size=9.5, space_after=1)
print("2쪽 완료")

# ══════════════════════════════════════════════════════════
# 3쪽 — 제안 서비스, 아키텍처와 핵심 기술 테스트
# ══════════════════════════════════════════════════════════
fill(S3, "직사각형 24", ["창의프로젝트   서비스 계획 수립:  김용현 · [팀원 이름]"])

fill(S3, "직사각형 5", ["PC 애플리케이션(상주 수집기) + 웹 서비스(검증 화면)   ·   이번 학기 프로토타입은 웹부터 구현"], size=16)

fill(S3, "직사각형 7", [
    "컴퓨터로 배우고 만드는 사람에게, 쓰던 도구를 바꾸지 않고 과정을 남겨 ① 스스로 돌아보고 ② 필요할 때만 제3자에게 보일 수 있게 한다.",
    "핵심 기능  ① Learn — 과정 회고 화면 (RQ1)   ② 도구를 가리지 않는 수집 (RQ2)   ③ Proof — 해시 체인 봉인과 증명 (RQ3)",
], size=13.5, space_after=2)

fill(S3, "직사각형 9", [
    "학습자는 쓰던 도구에서 그대로 작업하고, 수집기는 앱 · 파일 · 클립보드의 변화만 관측해 해시로 바꿔 서버에 보낸다. 내용 자체는 전송하지 않는다.",
    "Learn 은 본인만 보는 회고 화면이고, Proof 는 봉인해 공유하는 증명 화면이다. 교육자는 Proof 를 열어 다시 계산한 값과 파일의 값을 비교한다.",
], size=12.5, space_after=1)

for name, lines in [
    ("직사각형 10", ["학습자 · 교육자", "쓰던 도구에서 작업 · 열람"]),
    ("직사각형 11", ["수집기 (PC 상주)", "앱 · 파일 · 클립보드 관측"]),
    ("직사각형 12", ["서버 (Flask)", "Learn 회고 · Proof 검증"]),
    ("직사각형 13", ["외부 앵커", "작품 루트 해시 고정"]),
    ("직사각형 14", ["chain.json", "해시 · 이벤트만 저장"]),
]:
    fill(S3, name, lines, size=13.5, space_after=1)
fill(S3, "직사각형 19", ["해시 · 이벤트"], size=11)
fill(S3, "직사각형 20", ["저장 · 조회"], size=11)

fill(S3, "직사각형 21", ["핵심 기술 2개 — 가장 불확실한 부분을 작은 실행 실험으로 검증했다"], size=19)

t3 = table(S3)
add_row(t3)
t3rows = [
    (["해시 체인 변조 감지", "(구현 완료)"],
     ["스냅샷 390건 체인에서 content_hash 1자를", "무작위 위치에 변조 후 재검증 · 10회 반복"],
     ["변조 위치 100% 지목 · 응답 1초 이내", "(실험 전에 설정)"],
     ["10 / 10 정확 지목 · 평균 0.2 ms", "출력: “에세이.docx 6번에서 끊김”"],
     ["변조된 1건만 표시된다. 검증 시 이전 해시를", "재계산값으로 바꾸면 이후 전체가 깨짐 — 수정 예정"]),
    (["도구 무관 외부 유입 감지", "(앱 전환 + 클립보드)"],
     ["Word · PPT · Photoshop · VSCode 에서", "AI 앱 → 붙여넣기 각 20회 · 대조군 20회"],
     ["유입 시점 · 분량 식별 90% 이상", "· 오탐 10% 이하"],
     ["미실시 — 10주차 수집기 구현 후 진행", "(이번 핀업에서는 결과 없음)"],
     ["앱 내장 AI(Copilot 등)는 클립보드를 거치지", "않아 탐지 불가 → 파일 변화량으로 간접 관측"]),
]
for i, cells in enumerate(t3rows, start=1):
    for c, lines in enumerate(cells):
        cell(t3, i, c, lines, 7.5)

# ── 아래쪽 여백 정리 : 표가 안내문·쪽번호를 덮지 않게 한다 ──
from pptx.util import Emu

shp(S3, "직사각형 21").top = Inches(6.50)          # "핵심 기술 2개" 제목을 위로
fill(S3, "직사각형 21", ["핵심 기술 2개 — 가장 불확실한 부분을 작은 실행 실험으로 검증했다"], size=17)
shp(S3, "직사각형 23").top = Inches(8.95)          # 하단 안내문을 아래로

for s in S3.shapes:
    if s.has_table:
        s.top = Inches(7.00)
        s.width = Inches(13.6)                     # 쪽번호(x=14.58)를 피한다
        tb = s.table
        for r in range(len(tb.rows)):
            tb.rows[r].height = Inches(0.30)
            for c in range(len(tb.columns)):
                cl = tb.cell(r, c)
                cl.margin_top = Inches(0.03); cl.margin_bottom = Inches(0.03)
        break

# 2쪽도 하단 출처를 조금 내려 RQ 와 떨어뜨린다
shp(S2, "직사각형 10").top = Inches(8.95)

prs.save(OUT)
print("3쪽 완료 ->", OUT)
