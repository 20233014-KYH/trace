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
    "대상 ·  과제 · 공모전 · 외주 결과물을 컴퓨터로 만들어 제출하는 사람",
    "상황 ·  제출 직후 “AI로 만든 것 아니냐”는 의심을 받는 순간",
    "불편 ·  결백해도 내놓을 자료가 없다. 초고와 수정 흔적은 본인 PC 에만 남는다",
    "대응 ·  타임랩스 · 초안 캡처를 보내지만 “그것도 만들 수 있다”로 끝난다",
    "영향 ·  오탐은 되돌리기 어렵다. 학점 · 수상 · 다음 의뢰가 걸려 있다",
], size=14.5, space_after=6)

fill(S1, "직사각형 6", [
    "확인된 사실 ·  탐지기 오탐은 이미 측정됐고, 기관이 사용을 중단할 만큼 컸다",
    "팀의 추정 ·  오탐 경험이 제출자의 행동을 바꾼다 → 인터뷰로 검증 예정",
    "이번 범위 ·  컴퓨터에서 만든 결과물의 ‘제작 과정 기록’ 에 한정한다.",
    "                    AI 사용 여부 판정은 범위 밖에 둔다",
], size=12.5, space_after=4)

t1 = table(S1)
cell(t1, 1, 1, ["Liang, W. et al. (2023)", "비영어권 TOEFL 에세이로 GPT 탐지기 오탐률 측정"], 9.5)
cell(t1, 1, 2, ["비영어권 작성자가 오탐 대상이 된다.", "우리 팀과 국내 사용자가 그 대상에 속한다"], 9.5)
cell(t1, 2, 1, ["Vanderbilt University (2023.08) — Turnitin", "AI 탐지기 비활성화 공지와 그 근거"], 9.5)
cell(t1, 2, 2, ["기관이 탐지를 포기할 만큼 오탐 비용이 크다.", "‘탐지로 푸는 방식’ 이 이미 한계에 부딪혔다"], 9.5)
cell(t1, 3, 1, ["박재완 교수 인터뷰 (2026.09.16)", "커미션 작가 · 학생 인터뷰 8~10명 진행 예정"], 9.5)
cell(t1, 3, 2, ["교육 현장에 실제 수요가 있음을 확인.", "작가군의 수요는 아직 미검증 (팀의 가설)"], 9.5)

fill(S1, "직사각형 10", [
    "“컴퓨터로 결과물을 만들어 제출하는 사람은, 제출 이후 AI 사용을 의심받는 상황에서",
    "과정 기록이 본인 기기에만 남고 언제든 고칠 수 있다는 제약 때문에, 결백을 보일 수 없다.”",
], size=19, space_after=3)

fill(S1, "직사각형 11", [
    "Liang, W. et al. (2023). GPT detectors are biased against non-native English writers. Patterns 4(7), Cell Press.   ·   "
    "Vanderbilt University (2023.08.16). Guidance on AI Detection and Why We’re Disabling Turnitin’s AI Detector. vanderbilt.edu/brightspace",
    "박재완 교수 인터뷰 (2026.09.16, 대면)   ·   통계 인용은 각 문헌의 조사 대상·기간을 그대로 따랐으며, 팀이 추가 가공한 수치는 없음",
], size=9.5, space_after=1)
print("1쪽 완료")

# ══════════════════════════════════════════════════════════
# 2쪽 — 유사사례의 한계와 Research Questions
# ══════════════════════════════════════════════════════════
fill(S2, "직사각형 11", ["창의프로젝트   서비스 계획 수립:  김용현 · [팀원 이름]"])

t2 = table(S2)
cell(t2, 1, 1, ["Grammarly Authorship — Google 문서에서 글 쓰는 학생  ·  Turnitin Clarity — 기관이 계약한 학생",
                "Procreate 타임랩스 — 해당 앱으로 그리는 작가"], 9.5)
cell(t2, 1, 2, ["셋 다 ‘특정 도구 안에서’ 만 동작한다. 여러 앱(문서 · 편집 · 코드)을",
                "오가며 만드는 우리 대상에는 그대로 적용되지 않는다"], 9.5)
cell(t2, 2, 1, ["Authorship — 타이핑 · 붙여넣기 · AI 요청을 문장 단위로 구분해 색으로 표시하고 과정을 재생",
                "타임랩스 — 작업 화면을 영상으로 녹화"], 9.5)
cell(t2, 2, 2, ["‘출처를 구분해 보여준다’ 는 방식은 유효하다. 우리는 이를 도구에",
                "상관없이 적용하고, 기록 자체의 위조 방지를 더한다"], 9.5)
cell(t2, 3, 1, ["Authorship — 자기 에디터 밖의 작업은 보지 못하고, 기록을 봉인하는 장치가 없다",
                "타임랩스 — “그것도 만들 수 있다”는 반론에 무력"], 9.5)
cell(t2, 3, 2, ["미해결 문제 = ① 도구를 가리지 않는 수집  ② 만든 사람도 나중에",
                "고칠 수 없는 기록  ③ 제3자가 30초 안에 확인하는 화면"], 9.5)

fill(S2, "직사각형 5", [
    "차별점:  “기존 사례는 자기 도구 안의 글만 다루고 기록의 위조를 막지 못하므로,",
    "우리는 도구에 상관없이 과정을 수집하고 해시 체인으로 봉인해 제3자가 확인하는 방식을 제안한다.”",
], size=16, space_after=3)

fill(S2, "직사각형 7", [
    "RQ1 ·  해시 체인으로 봉인한 과정 기록은, 타임랩스 · 초안 제출보다",
    ("          검증자가 제작 과정을 더 신뢰하게 만드는가?", 10),
    "RQ2 ·  앱 전환 · 클립보드 · 파일 변화만으로, 외부에서 들어온 분량과",
    ("          시점을 앱 종류와 무관하게 식별할 수 있는가?", 10),
    "RQ3 ·  ‘AI 이후의 편집량’ 을 함께 보여주면, 교수가 과제의 학습 과정을",
    "          결과물만 볼 때보다 더 정확히 판단하는가?",
], size=11.5, space_after=1)

fill(S2, "직사각형 9", [
    "RQ1  지표 — 검증자가 ‘믿을 수 있다’고 답한 비율 · 결론까지 걸린 시간",
    ("          방법 — 같은 결과물을 타임랩스본 / 증명서본으로 나눠 제3자 10명에게 제시·비교", 10),
    "RQ2  지표 — 외부 유입 구간 식별 재현율 · 오탐률",
    ("          방법 — Word · PPT · Photoshop · VSCode 에서 붙여넣기 시나리오 각 20회 실행", 10),
    "RQ3  지표 — 교수의 판단과 실제 작성 방식의 일치율",
    "          방법 — 과정 기록 있음 / 없음 두 조건으로 과제 20건 평가 비교",
], size=10, space_after=1)

fill(S2, "직사각형 10", [
    "출처: Grammarly Authorship (grammarly.com/authorship) · Turnitin Clarity · Procreate 타임랩스 — 각 제품의 공개 문서 기준.",
    "‘기록 위조 방지가 없다’ 는 공개 문서에 서명 · 재검증 기능이 없다는 점에 근거한 팀의 판단이며, 별도 실험으로 확인한 사실은 아님.",
], size=9.5, space_after=1)
print("2쪽 완료")

# ══════════════════════════════════════════════════════════
# 3쪽 — 제안 서비스, 아키텍처와 핵심 기술 테스트
# ══════════════════════════════════════════════════════════
fill(S3, "직사각형 24", ["창의프로젝트   서비스 계획 수립:  김용현 · [팀원 이름]"])

fill(S3, "직사각형 5", ["PC 애플리케이션(상주 수집기) + 웹 서비스(검증 화면)   ·   이번 학기 프로토타입은 웹부터 구현"], size=16)

fill(S3, "직사각형 7", [
    "컴퓨터로 결과물을 만드는 사람에게, 쓰던 도구를 바꾸지 않고 제작 과정을 남겨 “이 기록은 만든 뒤 고쳐지지 않았다”를 제3자에게 보인다.",
    "핵심 기능  ① 도구를 가리지 않는 과정 수집 (RQ2)   ② 해시 체인 봉인과 재검증 (RQ1)   ③ 외부 유입 이후의 편집량 표시 (RQ3)",
], size=13.5, space_after=2)

fill(S3, "직사각형 9", [
    "창작자는 쓰던 도구에서 그대로 작업하고, 수집기는 앱 · 파일 · 클립보드의 변화만 관측해 해시로 바꿔 서버에 보낸다.",
    "내용 자체는 전송하지 않는다. 검증자는 공유 링크로 들어와, 저장된 재료로 다시 계산한 값과 파일에 적힌 값을 비교한다.",
], size=12.5, space_after=1)

for name, lines in [
    ("직사각형 10", ["창작자", "쓰던 도구에서 작업"]),
    ("직사각형 11", ["수집기 (PC 상주)", "앱 · 파일 · 클립보드 관측"]),
    ("직사각형 12", ["검증 서버 (Flask)", "해시 체인 계산 · 재검증"]),
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
