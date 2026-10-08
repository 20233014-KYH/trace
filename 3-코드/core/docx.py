"""
docx.py — Word(.docx) 본문 읽기. 파이썬 기본 기능(zipfile)만 — 설치할 것 없음.

tests/연결시제품.py(박상진)의 read_docx · doc_body 를 그대로 옮겼다 (이슈 #26-2 줄바꿈·탭 고침 포함).
학생 PC 의 내역서 화면(app/statement.py)도 같은 함수로 문단을 나눠야, 시험에서 맞춘 연결 결과와 화면 결과가 같다.
(연결시제품.py 도 이걸 import 하게 바꾸면 한 곳이 된다)
"""
import html
import os
import re
import zipfile


def read_docx(path_or_file):
    """→ [(style, text)] 문단마다. Word 가 글자를 여러 조각(run)으로 나눠 저장해도 이어 붙인다."""
    x = zipfile.ZipFile(path_or_file).read("word/document.xml").decode("utf-8")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>|<w:p/>", x, re.S):
        style = (re.search(r'<w:pStyle w:val="([^"]+)"', p) or [None, ""])[1]
        # 줄바꿈·탭은 글자 칸(<w:t>) 안으로 넣어야 아래에서 모인다 — 칸 밖에 넣으면 버려져서 두 문장이 붙었다 (이슈 #26-2)
        p = re.sub(r"<w:tab\s*/>", "<w:t>\t</w:t>", p)
        p = re.sub(r"<w:br\b[^>]*/>|<w:cr\s*/>", "<w:t>\n</w:t>", p)
        text = html.unescape("".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", p, re.S)))
        if text.strip():
            out.append((style, text.strip()))
    return out


def doc_body(path_or_file, name=None):
    """Word → (제목, [본문 문단]). 제목 서식이 없으면 첫 줄이 짧고 마침표가 없을 때 제목으로 본다."""
    paras = read_docx(path_or_file)
    heads = [i for i, (st, t) in enumerate(paras) if st.lower() in ("title", "heading1", "제목")]
    if not heads and paras and len(paras[0][1]) <= 60 and not re.search(r"[.!?。]$", paras[0][1]):
        heads = [0]
    fallback = name or (os.path.basename(path_or_file) if isinstance(path_or_file, str) else "문서")
    title = paras[heads[0]][1] if heads else fallback
    return title, [t for i, (st, t) in enumerate(paras) if i not in heads]
