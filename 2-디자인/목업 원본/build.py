"""
build.py — trace-mockbook.html 의 화면들을 PNG/PDF 로 뽑아 디자이너 전달 폴더 + zip 을 만든다.

  python build.py            # ../목업 PNG/ 와 "../목업 PNG (디자이너 전달용).zip" 생성
  python build.py s07 s11    # 일부 화면만 다시

필요: Chrome (기본 경로), Pillow (pip install pillow) — 아래 여백 자동 트림용
"""
import os, shutil, subprocess, sys, zipfile
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
HTML = HERE / "trace-mockbook.html"
OUT = HERE.parent / "목업 PNG"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCALE = 2  # 고해상도

# id, 출력 상대경로, 창 너비, 창 높이(넉넉히 — 아래 여백은 트림)
SCREENS = [
    ("overview", "00-전체흐름과-화면원칙.png",                 1600, 1900),
    ("s01", "1-시작/01-모드선택-기본Proof.png",                 1160, 900),
    ("s02", "1-시작/02-첫실행-수집항목동의.png",                1160, 1000),
    ("s03", "2-Proof기록/03-기록중-알약.png",                   1400, 900),
    ("s04", "2-Proof기록/04-알약hover-팝오버.png",             1400, 900),
    ("s05", "2-Proof기록/05-봉인확인.png",                     1400, 900),
    ("s06", "2-Proof기록/06-봉인완료-앵커대기.png",            1400, 900),
    ("s07", "3-내기록/07-한눈에-직접입력vs붙여넣기.png",       1400, 1960),
    ("s07b","3-내기록/07b-상세활동-펼침.png",                  1400, 2100),
    ("s08", "3-내기록/08-체인원본.png",                        1400, 1000),
    ("s09", "3-내기록/09-검증결과.png",                        1400, 800),
    ("s10", "4-증명서/10-내보내기옵션.png",                    1400, 900),
    ("s11", "4-증명서/11-증명서-A4한장.png",                   980, 1400),
    ("s12", "4-증명서/12-검증자웹-파일올려검증.png",           1260, 1300),
    ("s13", "5-Learn/13-Learn-기록중-알약-맥락수집.png",         1400, 900),
    ("s13b","5-Learn/13b-Learn-알약위-질문칸.png",              1400, 900),
    ("s13c","5-Learn/13c-Learn-물어보기-패널펼침.png",          1400, 900),
    ("s14", "5-Learn/14-Learn-타임라인-맥락패널.png",           1400, 1150),
    ("s15", "5-Learn/15-Learn-선택하면-툴바.png",              1400, 900),
    ("s15b","5-Learn/15b-Learn-SideChat-열림.png",              1400, 900),
    ("s16", "5-Learn/16-Learn-LearningSessionReport.png",       1400, 1150),
    ("s17", "5-Learn/17-Learn-수집설정.png",           1160, 1150),
]
PDFS = [("changes", "00-기획변화정리.pdf")]


def url(screen):
    return "file:///" + quote(str(HTML).replace("\\", "/"), safe="/:") + f"?screen={screen}"


def trim(png, bg=(243, 244, 247)):
    """아래쪽 배경색 여백 제거 (+ 여백 24px)."""
    try:
        from PIL import Image
    except ImportError:
        return
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    last = h - 1
    while last > 0 and all(abs(px[x, last][i] - bg[i]) < 4 for x in range(0, w, 16) for i in range(3)):
        last -= 1
    cut = min(h, last + 24 * SCALE)
    if cut < h:
        im.crop((0, 0, w, cut)).save(png)


def shoot(screen, rel, w, h):
    out = OUT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={w},{h}", f"--force-device-scale-factor={SCALE}",
                    f"--screenshot={out}", url(screen)], capture_output=True)
    trim(out)
    print("png ", rel)


def pdf(screen, rel):
    out = OUT / rel
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out}", url(screen)], capture_output=True)
    print("pdf ", rel)


def main():
    only = set(sys.argv[1:])
    if not only:
        shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(exist_ok=True)
    for s, rel, w, h in SCREENS:
        if not only or s in only:
            shoot(s, rel, w, h)
    for s, rel in PDFS:
        if not only or s in only:
            pdf(s, rel)
    z = OUT.parent / "목업 PNG (디자이너 전달용).zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(OUT))
    print("zip ", z.name)


if __name__ == "__main__":
    main()
