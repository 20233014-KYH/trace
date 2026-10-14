"""
version.py — 설치판 버전 (v0.1 · 10/13)

릴리스 태그(v0.1.0)와 같아야 한다 — 빌드(packaging/build.py)가 다르면 멈춘다.
내역서 화면이 서버 /api/app/latest 와 비교해 "새 버전" 을 띄운다.
"""
VERSION = "0.1.9"


def parse(v):
    """'v0.1.10' → (0, 1, 10) · 못 읽으면 ()"""
    try:
        return tuple(int(x) for x in str(v).lstrip("vV").split("-")[0].split("."))
    except ValueError:
        return ()
