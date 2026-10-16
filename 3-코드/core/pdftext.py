"""
pdftext.py — PDF 결과물 본문 읽기 (출처 보기 · 연결 확인 · 내보내기 · 10/15)

학생이 Word · 한글로 쓰고 PDF 로 내보낸 결과물을 출처 보기에 넣을 수 있게. read_docx 와 같은 모양 [(style, text)] 문단마다.
PDF 에는 "문단" 이 없고 화면 폭에서 끊긴 줄만 있다 → 줄을 다시 문단으로 묶는다:
  · 빈 줄 · 쪽이 바뀜(앞 줄이 문장으로 끝났을 때) → 새 문단
  · 앞 줄이 문장 끝(. ! ? 。 …)으로 끝남 · 앞 줄이 그 쪽의 보통 줄보다 눈에 띄게 짧음 · 이 줄이 번호 · 글머리표로 시작 → 새 문단
  · 아니면 앞 줄에 이어 붙임 (한국어는 띄어쓰기에서 줄이 넘어가서 사이에 빈칸 하나)
  · 쪽 번호만 있는 줄("3" · "- 3 -" · "3 / 10")은 뺀다
글자 서식(제목 서식)은 PDF 에 없어서 style 은 "" — 제목 · 소제목은 출처 보기가 짧은 첫 줄 · 번호로 시작하는 짧은 줄로 알아본다.
★ 쓰는 과정(친 글자 · 붙여넣은 자리)은 PDF 에 없다 — 원본 Word 를 기록했을 때 그 기록과 문장 글자로 잇는다.
"""
import io
import re

_끝 = re.compile(r"[.!?。…:;\"'”’」』]$")             # 괄호는 뺌 — "나가노(ナガノ)" 다음 줄 "의 만화" 처럼 문장 중간일 수 있음
# 번호 · 글머리표로 시작하는 줄 = 새 문단. 한글 번호("가." "다.")는 뺌 — 글자 중간에서 넘어간 문장 끝 "다." 와 구별이 안 됨 (10/15)
_머리 = re.compile(r"^\s*(?:\d{1,2}(?:[.)]|\.\d+[.)]?)\s|[-•·▪■□◦●○※▶►✓]\s?|[①-⑳]|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.\s|\(\d{1,2}\)\s)")
_쪽번호 = re.compile(r"^\s*[-–—]?\s*\d{1,4}\s*(?:/\s*\d{1,4})?\s*[-–—]?\s*$")


def read_pdf(path_or_file):
    """→ [("", 문단)] · 글자가 없는 PDF(스캔한 그림)면 []"""
    from pypdf import PdfReader
    r = PdfReader(path_or_file)
    out, 지금 = [], []          # 지금 = [(줄, 끝에 빈칸이 있었나)]

    def 끊기():
        if 지금:
            t = ""
            for i, (l, 빈칸) in enumerate(지금):
                if i:
                    앞 = 지금[i - 1]
                    # 한글은 Word 가 글자 중간에서도 줄을 넘긴다 — 그땐 줄 끝에 빈칸이 없다 ("발열이" / "다.") → 붙임.
                    # 단어 사이에서 넘어가면 빈칸이 남는다 ("콘텐츠 ") → 빈칸. 빈칸을 안 남기는 PDF 도 있어 한글끼리만 붙인다
                    붙임 = not 앞[1] and _한글(앞[0][-1:]) and _한글(l[:1])
                    t += "" if 붙임 else " "
                t += l
            if t.strip():
                out.append(("", t.strip()))
            지금.clear()

    for page in r.pages:
        # 글자 순서는 "배치" 모드로 — 기본 모드는 양쪽 정렬한 줄의 앞 조각을 다른 데로 빼먹었다 ("과도한 발열이" 다음 "다. 발열은" 이 사라짐 · 10/15)
        # 다만 배치 모드는 줄 끝 빈칸을 지운다 → 기본 모드의 같은 줄(끝 6글자)에서 "단어 사이에서 넘어갔나" 를 가져온다
        끝빈칸 = {}
        for l in (page.extract_text() or "").replace("\r", "").split("\n"):
            k = re.sub(r"\s", "", l)[-6:]
            if k:
                끝빈칸[k] = l.endswith(" ")
        try:
            배치 = page.extract_text(extraction_mode="layout") or ""
        except Exception:                                           # noqa: BLE001  옛 pypdf · 깨진 쪽 → 기본 모드
            배치 = page.extract_text() or ""
        줄들 = []
        for l in 배치.replace("\r", "").split("\n"):
            # 표의 한 행: 칸 사이가 8칸 이상 벌어짐 (양쪽 정렬로 벌어진 단어 사이는 2~6칸) → 칸마다 따로 (Word 가 표를 읽는 것처럼)
            칸들 = [c for c in re.split(r"[  ]{8,}", l.strip()) if c.strip()]
            if len(칸들) > 1:
                줄들.append(("", False))
                for c in 칸들:
                    줄들 += [(re.sub(r"[ \t ]+", " ", c).strip(), False), ("", False)]
                continue
            l = re.sub(r"[ \t ]+", " ", l).strip()
            줄들.append((l, 끝빈칸.get(re.sub(r"\s", "", l)[-6:], False)))
        길이 = sorted(len(l) for l, _ in 줄들 if len(l) >= 8)
        보통 = 길이[len(길이) * 3 // 4] if 길이 else 0            # 이 쪽에서 꽉 찬 줄의 길이쯤
        if 지금 and _끝.search(지금[-1][0]):                      # 쪽이 바뀜 — 앞 쪽 끝이 문장 끝이면 새 문단
            끊기()
        for l, 빈칸 in 줄들:
            if not l:
                끊기()
                continue
            if _쪽번호.match(l):
                continue
            if 지금 and (_끝.search(지금[-1][0]) or _머리.match(l) or (보통 and len(지금[-1][0]) < 보통 * 0.6)):
                끊기()
            지금.append((l, 빈칸))
    끊기()
    return out


def _한글(c):
    return bool(c) and "가" <= c <= "힣"


def is_pdf(raw):
    return raw[:5] == b"%PDF-"


def read_doc(raw):
    """과제 파일 바이트 → [(style, text)] — PDF 면 read_pdf, 아니면 Word(.docx)"""
    if is_pdf(raw):
        return read_pdf(io.BytesIO(raw))
    from core.docx import read_docx
    return read_docx(io.BytesIO(raw))
