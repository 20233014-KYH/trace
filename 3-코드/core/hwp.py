"""
hwp.py — 한글(.hwpx · .hwp) 본문 읽기 (11/18 · 최종 발표 전 "한글 읽기")

출처 보기 · 내역서가 Word(.docx) · PDF 처럼 한글 보고서도 문단마다 읽게 한다. read_docx 와 같은 모양 [(style, text)] 을 돌려준다.

  .hwpx  새 형식 = zip 안 XML (Contents/section0.xml …). 파이썬 기본 기능만 — 문단 <hp:p> 의 글자 <hp:t>
         표 칸 안 문단은 따로 한 문단 (Word 표 칸처럼)
  .hwp   예전 형식(한글 5.x) = OLE 묶음 파일. BodyText/Section0 … 을 (압축이면) 풀어 문단 글자 레코드(HWPTAG_PARA_TEXT = 67)만 모은다
         olefile (BSD 라이선스) 만 쓴다 — pyhwp 는 AGPL 이라 앱에 넣으면 Trace 전체를 AGPL 로 공개해야 해서 쓰지 않음
         암호를 건 문서 · 배포용 문서는 본문이 암호화돼 있어 못 읽음 → 알려 줌

글자 안의 조종 문자: 줄바꿈(10) → 줄바꿈 · 문단 끝(13) → 끝 · 묶음 빈칸(30 · 31) → 빈칸 · 표 · 그림 · 각주 같은 개체(8글자 자리)는 건너뜀.
"""
import io
import re
import struct
import zipfile
import zlib
from xml.etree import ElementTree as ET

OLE_SIG = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
TAG_PARA_TEXT = 67                                   # HWPTAG_BEGIN(16) + 51
# 1 글자 자리 조종 문자 — 나머지(1~31 중 여기 없는 것)는 8 글자(16바이트) 자리 개체 (표 · 그림 · 각주 · 필드 …)
_한칸 = {0: "", 10: "\n", 13: "", 24: "-", 25: " ", 26: " ", 27: " ", 28: " ", 29: " ", 30: " ", 31: " "}


class HwpError(ValueError):
    """읽을 수 없는 한글 파일 (암호 · 배포용 · 깨짐) — 화면에 그대로 보여 줄 말"""


def is_hwpx(raw):
    if raw[:2] != b"PK":
        return False
    try:
        names = zipfile.ZipFile(io.BytesIO(raw)).namelist()
    except zipfile.BadZipFile:
        return False
    return any(re.match(r"Contents/section\d+\.xml$", n) for n in names)


def is_hwp(raw):
    return raw[:8] == OLE_SIG


# ─────────────── .hwpx ───────────────
def read_hwpx(raw):
    """→ [(style, text)] 문단마다 (빈 문단 뺌)"""
    z = zipfile.ZipFile(io.BytesIO(raw))
    secs = sorted((n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n)),
                  key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    out = []
    for n in secs:
        root = ET.fromstring(z.read(n))
        for p in root.iter():
            if _이름(p.tag) != "p":
                continue
            t = _문단글(p).strip()
            if t:
                out.append(("", t))
    return out


def _이름(tag):
    return tag.rsplit("}", 1)[-1]


def _문단글(p):
    """이 문단의 글자만 — 안에 든 표 칸 문단(hp:p)은 따로 세므로 들어가지 않는다"""
    parts = []

    def walk(el):
        for c in el:
            k = _이름(c.tag)
            if k == "p":                              # 표 칸 · 글상자 안 문단 — 따로
                continue
            if k == "t":
                parts.append(c.text or "")
                for g in c:                           # <hp:t>앞<hp:lineBreak/>뒤</hp:t> · 탭 등
                    gk = _이름(g.tag)
                    parts.append("\n" if gk == "lineBreak" else "\t" if gk == "tab" else " " if gk in ("nbSpace", "fwSpace") else "")
                    parts.append(g.tail or "")
                continue
            walk(c)
    walk(p)
    return "".join(parts)


# ─────────────── .hwp (한글 5.x) ───────────────
def read_hwp(raw):
    """→ [(style, text)] 문단마다 (빈 문단 뺌)"""
    try:
        import olefile
    except ImportError as e:                          # 설치판엔 들어 있음 (requirements-build)
        raise HwpError("한글(.hwp) 파일을 읽을 준비가 안 됐어요 (olefile 없음)") from e
    try:
        o = olefile.OleFileIO(io.BytesIO(raw))
    except Exception as e:                            # noqa: BLE001 — 깨진 파일은 olefile 이 여러 오류를 냄 (OSError · ValueError …)
        raise HwpError("한글(.hwp) 파일을 열지 못했어요 — 파일이 깨졌을 수 있어요") from e
    if not o.exists("FileHeader"):
        raise HwpError("한글(.hwp) 파일이 아니에요")
    head = o.openstream("FileHeader").read()
    if not head.startswith(b"HWP Document File"):
        raise HwpError("한글(.hwp) 파일이 아니에요")
    속성 = struct.unpack("<I", head[36:40])[0]
    if 속성 & 0x2:
        raise HwpError("암호를 건 한글 파일이라 읽지 못해요 — 암호를 풀어 저장한 뒤 열어 주세요")
    if 속성 & 0x4:
        raise HwpError("배포용 한글 문서라 읽지 못해요 — 일반 문서로 저장한 뒤 열어 주세요")
    압축 = bool(속성 & 0x1)
    secs = sorted((e for e in o.listdir() if len(e) == 2 and e[0] == "BodyText" and re.match(r"Section\d+$", e[1])),
                  key=lambda e: int(e[1][7:]))
    out = []
    for e in secs:
        data = o.openstream(e).read()
        if 압축:
            try:
                data = zlib.decompress(data, -15)
            except zlib.error as err:
                raise HwpError("한글(.hwp) 본문을 풀지 못했어요 — 파일이 깨졌을 수 있어요") from err
        for t in _문단_글들(data):
            t = t.strip()
            if t:
                out.append(("", t))
    return out


def _문단_글들(data):
    """레코드들 → 문단 글자 레코드(PARA_TEXT)마다 글"""
    i, n = 0, len(data)
    while i + 4 <= n:
        h = struct.unpack_from("<I", data, i)[0]
        i += 4
        tag, size = h & 0x3FF, (h >> 20) & 0xFFF
        if size == 0xFFF:                             # 큰 레코드 — 크기가 뒤 4바이트에
            if i + 4 > n:
                break
            size = struct.unpack_from("<I", data, i)[0]
            i += 4
        if tag == TAG_PARA_TEXT:
            yield _글(data[i:i + size])
        i += size


def _글(b):
    """UTF-16LE 문단 글 → 조종 문자를 풀고 개체 자리(8 글자)는 건너뜀"""
    out, k, m = [], 0, len(b) // 2
    while k < m:
        c = b[2 * k] | (b[2 * k + 1] << 8)
        if c >= 32:
            j = k
            while j < m and (b[2 * j] | (b[2 * j + 1] << 8)) >= 32:
                j += 1
            out.append(b[2 * k:2 * j].decode("utf-16-le", "replace"))
            k = j
        elif c in _한칸:
            out.append(_한칸[c])
            k += 1
        else:
            k += 8
    return "".join(out)


def read_hangul(raw):
    """.hwpx · .hwp 바이트 → [(style, text)]"""
    if is_hwpx(raw):
        return read_hwpx(raw)
    if is_hwp(raw):
        return read_hwp(raw)
    raise HwpError("한글 파일이 아니에요")
