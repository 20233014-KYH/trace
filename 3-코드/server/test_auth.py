"""
test_auth.py — 계약 1·2절(인증 · Work)이 제대로 도는지.

  python 3-코드/server/app.py          # 다른 창에서 서버를 켜고
  python 3-코드/server/test_auth.py

검사 11개. 특히 두 가지를 본다:
  · 비밀번호를 원문으로 저장하지 않는가   ★ 사고 나면 제일 크게 터지는 곳
  · 남의 Work 를 볼 수 있는가             ★ 학생 기록 서비스에서 치명적
"""
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
import uuid

BASE = f"http://127.0.0.1:{os.environ.get('TRACE_PORT', '5000')}/api"   # 맥은 5000 = AirPlay → TRACE_PORT=5050
HERE = os.path.dirname(os.path.abspath(__file__))

통과, 실패 = 0, 0


def 호출(경로, 몸=None, 토큰=None, 방법=None):
    머리 = {"Content-Type": "application/json"}
    if 토큰:
        머리["Authorization"] = f"Bearer {토큰}"
    자료 = json.dumps(몸).encode() if 몸 is not None else None
    요청 = urllib.request.Request(BASE + 경로, data=자료,
                                  method=방법 or ("POST" if 몸 is not None else "GET"),
                                  headers=머리)
    try:
        with urllib.request.urlopen(요청, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        본문 = e.read()
        try:
            return e.code, json.loads(본문)
        except ValueError:                           # 없는 주소(404·405)면 Flask 가 HTML 을 돌려준다
            return e.code, {"_html": 본문[:80].decode("utf-8", "replace")}
    except urllib.error.URLError as e:
        print(f"\n  서버에 연결하지 못했습니다 ({e.reason}).")
        print("  다른 창에서 먼저 켜 주세요:  python 3-코드/server/app.py\n")
        sys.exit(1)


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    if 조건:
        통과 += 1
        print(f"  ✅ {이름:<26} {설명}")
    else:
        실패 += 1
        print(f"  ❌ {이름:<26} {설명}")


def main():
    print()
    print(f"  인증 · Work 검사 — {BASE}")
    print("  " + "─" * 66)

    꼬리 = uuid.uuid4().hex[:8]
    갑 = {"email": f"a{꼬리}@test.kr", "password": "테스트비번12345", "name": "갑"}
    을 = {"email": f"b{꼬리}@test.kr", "password": "테스트비번12345", "name": "을"}

    코드, _ = 호출("/auth/signup", 갑)
    검사("1 가입", 코드 == 201, f"HTTP {코드}")

    코드, _ = 호출("/auth/signup", 갑)
    검사("2 같은 이메일 거부", 코드 == 409, f"HTTP {코드} (409 여야 함)")

    코드, 답 = 호출("/auth/signup", {"email": f"c{꼬리}@test.kr", "password": "짧음"})
    검사("3 짧은 비번 거부", 코드 == 400, f"HTTP {코드}")

    코드, 답 = 호출("/auth/login", {"email": 갑["email"], "password": "틀린비번12345"})
    검사("4 틀린 비번 거부", 코드 == 401, f"HTTP {코드}")
    검사("5 어느 쪽이 틀렸는지 안 알려줌",
         "없" not in 답.get("message", "") and "이메일 또는" in 답.get("message", ""),
         f"“{답.get('message')}”")

    코드, 답 = 호출("/auth/login", {"email": 갑["email"], "password": 갑["password"]})
    갑토큰 = 답.get("token")
    검사("6 로그인", 코드 == 200 and 갑토큰, f"토큰 {str(갑토큰)[:12]}…")

    # ★ 비밀번호가 원문으로 저장되지 않았나 — DB 를 직접 열어 본다
    db경로 = os.path.join(HERE, "trace.db")
    원문저장 = False
    if os.path.exists(db경로):
        con = sqlite3.connect(db경로)
        r = con.execute("SELECT password_hash FROM users WHERE email=?", (갑["email"],)).fetchone()
        원문저장 = bool(r) and 갑["password"] in (r[0] or "")
        해시앞 = (r[0] or "")[:20] if r else "(없음)"
        con.close()
    검사("7 비번 원문 저장 안 함", not 원문저장, f"저장된 값: {해시앞}…")

    코드, 답 = 호출("/me", 토큰=갑토큰)
    검사("8 내 정보", 코드 == 200 and 답.get("name") == "갑", f"HTTP {코드} · {답.get('name')}")

    코드, _ = 호출("/me")
    검사("9 토큰 없이 /me 막힘", 코드 == 401, f"HTTP {코드}")

    코드, 답 = 호출("/works", {"title": "갑의 과제", "ai_scope": "코드 설명·디버깅만 허용"}, 토큰=갑토큰)
    갑작품 = 답.get("id")
    검사("10 Work 만들기 (ai_scope 메모)", 코드 == 201 and 답.get("ai_scope") == "코드 설명·디버깅만 허용",
         f"HTTP {코드} · {답.get('title')}")

    코드, 답 = 호출("/works", {"title": "메모가 숫자", "ai_scope": 42}, 토큰=갑토큰)
    검사("11 ai_scope 가 글자가 아니면 거부", 코드 == 400, f"HTTP {코드}")

    # ★ 남의 Work 가 보이나
    호출("/auth/signup", 을)
    _, 답 = 호출("/auth/login", {"email": 을["email"], "password": 을["password"]})
    을토큰 = 답.get("token")
    코드, 답 = 호출(f"/works/{갑작품}", 토큰=을토큰)
    검사("12 남의 Work 못 봄", 코드 == 404, f"HTTP {코드} (404 여야 함)")

    코드, 목록 = 호출("/works", 토큰=을토큰)
    검사("13 목록에도 안 보임", 코드 == 200 and all(w["id"] != 갑작품 for w in 목록),
         f"을의 Work {len(목록)}개")

    # ★ 과제가 있는 상태에서 /me — 옛 코드는 여기서 w.mode 를 읽다가 500 이 났다 (과제가 0개일 땐 안 드러남)
    코드, 답 = 호출("/me", 토큰=갑토큰)
    검사("15 /me 의 과제 목록에 ai_scope", 코드 == 200 and 답.get("works") and "ai_scope" in 답["works"][0],
         f"HTTP {코드} · 과제 {len(답.get('works') or [])}개")

    코드, 답 = 호출(f"/works/{갑작품}", {"ai_scope": "자료 조사만 허용"}, 토큰=갑토큰, 방법="PATCH")
    검사("16 PATCH 로 메모 고치기", 코드 == 200 and 답.get("ai_scope") == "자료 조사만 허용", f"HTTP {코드}")

    코드, _ = 호출(f"/works/{갑작품}", {"title": "가로채기"}, 토큰=을토큰, 방법="PATCH")
    검사("17 남의 Work 는 못 고침", 코드 == 404, f"HTTP {코드} (404 여야 함)")

    # ★ 배포 전 (10/7): 로그인 없이 과제를 훑어 세션 id 를 알아내는 길이 막혀야 한다
    코드, _ = 호출("/works")
    검사("18 토큰 없이 과제 목록 막힘", 코드 == 401, f"HTTP {코드} (401 여야 함)")
    코드, _ = 호출(f"/works/{갑작품}")
    검사("19 토큰 없이 과제 조회 막힘", 코드 == 401, f"HTTP {코드} (401 여야 함)")

    코드, _ = 호출("/auth/logout", {}, 토큰=갑토큰)
    코드2, _ = 호출("/me", 토큰=갑토큰)
    검사("14 로그아웃하면 토큰 죽음", 코드 == 200 and 코드2 == 401, f"로그아웃 {코드} · 그 뒤 /me {코드2}")

    print("  " + "─" * 66)
    print(f"  {통과}개 통과, {실패}개 실패")
    print()
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
