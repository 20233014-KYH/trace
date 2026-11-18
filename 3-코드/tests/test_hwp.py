"""
test_hwp.py — 한글(.hwpx · .hwp) 읽기 (core/hwp.py · 11/18)

  python 3-코드/tests/test_hwp.py

.hwpx 는 zip + XML 이라 시험에서 직접 만든다. .hwp 는 한글 없이 만들 수 없어서 본문 레코드(문단 글자)를 바이트로 만들어
글자 풀기를 보고, 이 PC 의 다운로드 폴더에 .hwp 가 있으면 그것도 읽어 본다 (저장소엔 안 올림).
"""
import glob
import io
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import hwp                              # noqa: E402
from core.pdftext import read_doc                 # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✓' if 조건 else '✗'} {이름} {덧}")


NS = 'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'


def hwpx(*섹션):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        for i, x in enumerate(섹션):
            z.writestr(f"Contents/section{i}.xml", f"<hs:sec {NS}>{x}</hs:sec>")
    return b.getvalue()


def p(*runs):
    return "<hp:p>" + "".join(f"<hp:run><hp:t>{r}</hp:t></hp:run>" for r in runs) + "</hp:p>"


def 레코드(tag, body):
    n = len(body)
    if n < 0xFFF:
        return struct.pack("<I", tag | (n << 20)) + body
    return struct.pack("<I", tag | (0xFFF << 20)) + struct.pack("<I", n) + body


def 글(s):
    return s.encode("utf-16-le")


def main():
    print("\n  한글 파일 읽기\n  " + "─" * 60)
    표 = ("<hp:p><hp:run><hp:tbl><hp:tr><hp:tc><hp:subList>" + p("칸 하나") + "</hp:subList></hp:tc>"
          "<hp:tc><hp:subList>" + p("칸 둘") + "</hp:subList></hp:tc></hp:tr></hp:tbl></hp:run></hp:p>")
    raw = hwpx(p("보고서 제목") + p("첫 문단은 ", "두 조각으로 나뉨.") + "<hp:p><hp:run><hp:t>앞<hp:lineBreak/>뒤<hp:tab/>탭</hp:t></hp:run></hp:p>"
               + 표 + p(""), p("둘째 구역 문단."))
    ps = read_doc(raw)
    검사(".hwpx 문단 · 조각 이어 붙임 · 빈 문단 뺌", [t for _, t in ps][:2] == ["보고서 제목", "첫 문단은 두 조각으로 나뉨."], str(ps[:2]))
    검사(".hwpx 줄바꿈 · 탭", ("", "앞\n뒤\t탭") in ps)
    검사(".hwpx 표 칸은 따로 한 문단 (바깥 문단에 섞이지 않음)", ("", "칸 하나") in ps and ("", "칸 둘") in ps
         and not any("칸 하나" in t and t != "칸 하나" for _, t in ps))
    검사(".hwpx 구역(section) 순서대로", ps[-1] == ("", "둘째 구역 문단."))
    검사("Word · PDF 판별은 그대로 (zip 이라도 한글 아니면 docx 로)", not hwp.is_hwpx(b"PK\x03\x04garbage") and not hwp.is_hwp(b"%PDF-"))

    # .hwp 본문: 문단 머리(66) · 문단 글자(67) · 표 개체(8글자 자리) · 줄바꿈 · 문단 끝
    개체 = struct.pack("<H", 11) + b"\x00" * 12 + struct.pack("<H", 11)       # 표 (확장 조종 · 8글자)
    본문 = (레코드(66, b"\x00" * 24) + 레코드(67, 글("첫 줄") + struct.pack("<H", 10) + 글("둘째 줄") + struct.pack("<H", 13))
            + 레코드(66, b"\x00" * 24) + 레코드(67, 개체 + 글("표 뒤 글") + struct.pack("<H", 30) + 글("끝") + struct.pack("<H", 13))
            + 레코드(67, 글("긴 문단 " * 600)))
    t = list(hwp._문단_글들(본문))
    검사(".hwp 문단 글자 · 줄바꿈 · 문단 끝", t[0] == "첫 줄\n둘째 줄", repr(t[0]))
    검사(".hwp 표 · 그림 개체 자리는 건너뜀 · 묶음 빈칸", t[1] == "표 뒤 글 끝", repr(t[1]))
    검사(".hwp 큰 레코드(4KB 넘음)도", len(t) == 3 and t[2].startswith("긴 문단") and len(t[2]) == len("긴 문단 " * 600))
    try:
        hwp.read_hangul(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 600)
        검사("깨진 .hwp 는 알아들을 말로", False)
    except hwp.HwpError as e:
        검사("깨진 .hwp 는 알아들을 말로", "한글" in str(e), str(e))

    있는 = sorted(glob.glob(os.path.expanduser("~/Downloads/*.hwp")))[:3]
    for f in 있는:
        ps = read_doc(open(f, "rb").read())
        검사(f"이 PC 의 .hwp 읽힘 · {os.path.basename(f)[:20]}", len(ps) > 0 and all(t.strip() for _, t in ps), f"{len(ps)}문단")
    if not 있는:
        print("  · 다운로드 폴더에 .hwp 가 없어 실제 파일 시험은 건너뜀")
    print("  " + "─" * 60 + f"\n  {'✓ 통과' if not 실패 else '✗ 실패'}  ({통과}개 통과 · {실패}개 실패)\n")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
