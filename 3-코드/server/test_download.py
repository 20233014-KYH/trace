"""
test_download.py — 설치판 내려받기 (/download · /api/app/latest). DB 를 안 쓴다.

  python 3-코드/server/test_download.py       # 서버를 켜지 않아도 된다 (Flask 시험 클라이언트 · GitHub 에 묻지 않음)
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("TRACE_DB_URL", "sqlite://")    # 메모리 DB — .env 의 진짜 DB 를 건드리지 않는다
import app as 서버                                    # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 맞음, 덧붙임=""):
    global 통과, 실패
    통과, 실패 = 통과 + bool(맞음), 실패 + (not 맞음)
    print(f"  {'✓' if 맞음 else '✗'} {이름}  {'' if 맞음 else 덧붙임}")


def main():
    c = 서버.app.test_client()
    r = c.get("/download")
    검사("1 내려받기 화면", r.status_code == 200 and "Trace 설치하기" in r.get_data(as_text=True), r.status_code)

    서버._릴리스.update(at=time.time(), data={"version": "", "tag": None})          # 릴리스 없음
    r = c.get("/api/app/latest")
    검사("2 릴리스 없으면 404", r.status_code == 404 and r.get_json()["error"] == "no_release", r.status_code)

    견본 = {"version": "0.1.0", "tag": "v0.1.0", "published_at": "2026-10-13T04:00:00Z", "page": "https://github.com/x",
           "notes": "첫 시험판", "windows": {"name": "Trace-Setup-0.1.0.exe", "url": "https://github.com/x.exe", "size": 1},
           "extension": {"name": "Trace-0.1.0-extension.zip", "url": "https://github.com/x.zip", "size": 1}}
    서버._릴리스.update(at=time.time(), data=견본)
    r = c.get("/api/app/latest")
    d = r.get_json() or {}
    검사("3 최신 릴리스", r.status_code == 200 and d["version"] == "0.1.0" and d["windows"]["name"].endswith(".exe"), d)

    서버._릴리스.update(at=0)                                                     # 10분 지남 + GitHub 이 안 됨 → 전에 읽은 것
    본래 = 서버._github
    서버._github = lambda url, method="GET": (_ for _ in ()).throw(OSError("연결 안 됨"))
    r = c.get("/api/app/latest")
    검사("4 GitHub 이 안 되면 전에 읽은 것", r.status_code == 200 and r.get_json()["version"] == "0.1.0", r.status_code)

    # GitHub API 없이 웹 주소로 읽기 (10/14) — releases/latest 가 넘겨 주는 주소 · 파일 HEAD · 저장소의 notes
    def 가짜(url, method="GET"):
        if url.endswith("/releases/latest"):
            return 302, {"Location": "https://github.com/20233014-KYH/trace/releases/tag/v0.2.0"}, b""
        if url.endswith("Trace-Setup-0.2.0.exe") or url.endswith("Trace-0.2.0-mac.dmg"):
            return 302, {}, b""
        if "raw.githubusercontent.com" in url and url.endswith("v0.2.0.md"):
            return 200, {}, "맥 설치판\n- 둘째 줄".encode()
        return 404, {}, b""
    서버._github = 가짜
    d = 서버._릴리스_읽기()
    검사("6 웹 주소로 태그 · 파일 · 글", d["version"] == "0.2.0" and d["windows"]["url"].endswith("/v0.2.0/Trace-Setup-0.2.0.exe")
         and d["mac"]["name"] == "Trace-0.2.0-mac.dmg" and d["extension"] is None and d["notes"].startswith("맥 설치판"), d)
    서버._github = lambda url, method="GET": (302, {"Location": "https://github.com/20233014-KYH/trace/releases"}, b"")
    검사("7 릴리스가 없으면 version 빈칸 → 404", 서버._릴리스_읽기()["version"] == "", "")
    서버._github = 본래

    sys.path.insert(0, os.path.dirname(HERE))
    from core.version import parse
    검사("5 버전 비교", parse("v0.1.10") > parse("0.1.9") > parse("0.1.0") and parse("x") == (), "")
    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
