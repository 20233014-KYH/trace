"""
test_demo.py — 늘 열리는 견본 주소 (/demo · /demo/pdf). DB 를 안 쓴다.

  python 3-코드/server/test_demo.py           # 서버를 켜지 않아도 된다 (Flask 시험 클라이언트)
"""
import os
import sys

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
    r = c.get("/demo")
    검사("1 /demo → /s/demo", r.status_code == 302 and r.headers["Location"].endswith("/s/demo"), r.status_code)
    r = c.get("/demo/pdf")
    검사("2 /demo/pdf → PDF 주소", r.status_code == 302 and r.headers["Location"].endswith("/api/share/demo/pdf"), r.status_code)
    r = c.get("/s/demo")
    검사("3 화면 열림", r.status_code == 200 and "학생이 공유한 AI 활용 기록" in r.get_data(as_text=True), r.status_code)
    r = c.get("/api/share/demo")
    d = r.get_json() or {}
    검사("4 견본 데이터", r.status_code == 200 and d.get("work", {}).get("title") and d.get("expires_at"), r.status_code)
    검사("5 공유 링크와 같은 머리 (검색·저장 안 됨)", r.headers.get("X-Robots-Tag", "").startswith("noindex"), "")
    try:
        import reportlab  # noqa: F401
        r = c.get("/api/share/demo/pdf")
        검사("6 견본 PDF", r.status_code == 200 and r.data[:4] == b"%PDF", r.status_code)
    except ImportError:
        print("  - 6 reportlab 없음 — PDF 는 건너뜀")
    검사("7 다른 토큰은 여전히 404", c.get("/api/share/demo2").status_code == 404, "")
    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
