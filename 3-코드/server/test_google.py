"""
test_google.py — 구글 로그인 (10/15 · server/app.py "구글 로그인") — 구글 쪽은 흉내 · 서버는 이 프로세스 안 · DB 는 임시 SQLite

  python 3-코드/server/test_google.py

확인하는 것:
  · 설정이 없으면 버튼을 안 살림 (providers google=false · start 는 안내 화면)
  · start → 구글 주소 (client_id · 돌아올 곳 · PKCE S256 · 서명한 state) · 이상한 pc/port 거절
  · callback → 127.0.0.1:<port> 로만 돌려보냄 · 한 번 쓰는 표 → claim → 토큰 → /me
  · 표는 한 번만 · 2분 지나면 안 됨 · state 를 고치면 거절 · 이메일 확인 안 된 구글 계정 거절
  · 같은 이메일로 먼저 가입한 계정에 붙음 (비밀번호 로그인도 그대로) · 구글로만 가입하면 비밀번호 로그인 안 됨
"""
import base64
import hashlib
import json
import os
import sys
import tempfile
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
d = tempfile.mkdtemp(prefix="trace-google-")
os.environ["TRACE_DB_URL"] = "sqlite:///" + os.path.join(d, "server.db")
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)
import app as A                                   # noqa: E402
import db                                         # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    통과, 실패 = 통과 + bool(조건), 실패 + (not 조건)
    print(f"  {'✅' if 조건 else '❌'} {이름:<46} {설명}")


def b64(x):
    return base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip("=")


구글이_줄_것 = {}
받은_것 = []


def 가짜_구글(code, 검증값, 돌아올_곳, 설정):
    """진짜 _구글_코드_바꾸기 대신 — 받은 code · PKCE 검증값을 남기고, 정해 둔 사람을 돌려준다"""
    받은_것.append((code, 검증값, 돌아올_곳))
    return dict(구글이_줄_것)


def 한_바퀴(s, pc="pc-state-0123456789abcdef", port="5079", code="code-1"):
    """start → (구글) → callback. (start 응답, callback 응답)"""
    r1 = s.get(f"/api/auth/google/start?pc={pc}&port={port}")
    q = parse_qs(urlparse(r1.headers.get("Location", "")).query)
    r2 = s.get("/api/auth/google/callback?" + f"code={code}&state={q.get('state', [''])[0]}") if q.get("state") else None
    return r1, q, r2


def main():
    print("\n  구글 로그인 검사 — 구글 흉내 · 임시 DB\n  " + "─" * 70)
    s = A.app.test_client()
    검사("설정 없으면 버튼 안 살림", s.get("/api/auth/providers").get_json() == {"google": False, "kakao": False})
    검사("설정 없으면 start 는 안내 화면 (503)", s.get("/api/auth/google/start?pc=pc-state-0123456789abcdef&port=5079").status_code == 503)

    os.environ.update(GOOGLE_CLIENT_ID="cid.apps.googleusercontent.com", GOOGLE_CLIENT_SECRET="비밀-시험")
    진짜, 옛_열기, 보낸 = A._구글_코드_바꾸기, A.urllib.request.urlopen, []

    class 답:                                    # 구글 토큰 주소 흉내 — 받은 몸통을 남기고 id_token 을 준다
        def __init__(self, c): self.c = c
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"id_token": "h." + b64(self.c) + ".sig"}).encode()
    import time
    좋은 = {"aud": "cid.apps.googleusercontent.com", "iss": "https://accounts.google.com", "exp": time.time() + 600, "sub": "1", "email": "a@b.c"}
    결과 = []
    try:
        for c in (좋은, {**좋은, "aud": "다른앱"}, {**좋은, "iss": "https://evil.example"}, {**좋은, "exp": time.time() - 1}):
            A.urllib.request.urlopen = lambda 요청, timeout=None, c=c: (보낸.append(요청), 답(c))[1]
            try:
                결과.append(진짜("코드", "검증값", "https://x/cb", A._구글_설정()) == c)
            except ValueError:
                결과.append("거절")
    finally:
        A.urllib.request.urlopen = 옛_열기
    몸 = parse_qs(보낸[0].data.decode())
    검사("코드 바꾸기: 받는 쪽 · 발급자 · 시간 다르면 거절 · 비밀 · PKCE 같이 보냄",
         결과 == [True, "거절", "거절", "거절"] and 보낸[0].full_url == A.구글_토큰 and 몸["code_verifier"] == ["검증값"]
         and 몸["client_secret"] == ["비밀-시험"] and 몸["grant_type"] == ["authorization_code"], f"{결과}")
    A._구글_코드_바꾸기 = 가짜_구글
    검사("설정하면 google=true", s.get("/api/auth/providers").get_json()["google"] is True)

    구글이_줄_것.update(sub="g-111", email="Kim@Gmail.com", email_verified=True, name="김구글")
    r1, q, r2 = 한_바퀴(s)
    검사("start → 구글 주소 · client_id · 돌아올 곳 · 계정 고르기",
         r1.status_code == 302 and r1.headers["Location"].startswith(A.구글_인증 + "?") and q["client_id"] == ["cid.apps.googleusercontent.com"]
         and q["redirect_uri"] == ["http://localhost/api/auth/google/callback"] and q["scope"] == ["openid email profile"]
         and q["prompt"] == ["select_account"], r1.headers.get("Location", "")[:60])
    검증값 = 받은_것[-1][1]
    검사("PKCE: S256 · callback 이 같은 검증값으로 바꿈",
         q["code_challenge_method"] == ["S256"] and len(검증값) == 43
         and q["code_challenge"] == [base64.urlsafe_b64encode(hashlib.sha256(검증값.encode()).digest()).decode().rstrip("=")])
    돌아감 = urlparse(r2.headers.get("Location", ""))
    dq = parse_qs(돌아감.query)
    검사("callback → 이 PC(127.0.0.1:5079) 로만 · 표 · 앱이 만든 state",
         r2.status_code == 302 and 돌아감.netloc == "127.0.0.1:5079" and 돌아감.path == "/local/auth/google/done"
         and dq["state"] == ["pc-state-0123456789abcdef"] and len(dq["ticket"][0]) >= 40, r2.headers.get("Location", "")[:70])
    r = s.post("/api/auth/google/claim", json={"ticket": dq["ticket"][0], "device": "시험"})
    tok = (r.get_json() or {}).get("token")
    me = s.get("/api/me", headers={"Authorization": f"Bearer {tok}"}).get_json() or {}
    검사("claim → 토큰 → /me (이름 · 이메일 소문자 · 로그인 방법)", r.status_code == 200 and me.get("name") == "김구글"
         and me.get("email") == "kim@gmail.com" and me.get("google") is True and me.get("password") is False, f"{me.get('email')}")
    검사("표는 한 번만", s.post("/api/auth/google/claim", json={"ticket": dq["ticket"][0]}).status_code == 401)
    검사("구글로만 가입한 계정은 비밀번호 로그인 안 됨",
         all(s.post("/api/auth/login", json={"email": "kim@gmail.com", "password": p}).status_code == 401 for p in ("", "!google", "x" * 8)))

    _, _, r2 = 한_바퀴(s, code="code-2")
    t2 = parse_qs(urlparse(r2.headers["Location"]).query)["ticket"][0]
    with db.Session() as x:
        x.get(db.LoginTicket, t2).created_at -= timedelta(minutes=3)
        x.commit()
    검사("2분 지난 표는 안 됨", s.post("/api/auth/google/claim", json={"ticket": t2}).status_code == 401)
    _, _, r2 = 한_바퀴(s, code="code-3")
    t3 = parse_qs(urlparse(r2.headers["Location"]).query)["ticket"][0]
    r = s.post("/api/auth/google/claim", json={"ticket": t3}).get_json()
    검사("다시 구글로 → 같은 계정", r["user"]["id"] == me["id"])

    r1, q, _ = 한_바퀴(s)
    본문, _, 서명 = q["state"][0].partition(".")
    값 = json.loads(base64.urlsafe_b64decode(본문 + "=" * (-len(본문) % 4)))
    고친 = b64({**값, "port": 8080}).rstrip("=") + "." + 서명
    늦은 = A._쪽지({**값, "exp": 0}, "비밀-시험")
    검사("state 를 고치거나(다른 포트) 10분 지나면 거절",
         s.get(f"/api/auth/google/callback?code=c&state={고친}").status_code == 400
         and s.get(f"/api/auth/google/callback?code=c&state={늦은}").status_code == 400)
    검사("구글에서 취소하면 안내 화면", s.get(f"/api/auth/google/callback?error=access_denied&state={q['state'][0]}").status_code == 400)
    검사("이상한 pc · port 거절 (127.0.0.1 밖으로 보낼 수 없음)",
         all(s.get(f"/api/auth/google/start?pc={pc}&port={port}").status_code == 400
             for pc, port in (("짧음", "5079"), ("pc-state-0123456789abcdef", "80"), ("pc-state-0123456789abcdef", "evil.com"),
                              ("pc-state-0123456789abcdef", "99999"), ("a/b?c=d&e=f-0123456789", "5079"))))

    구글이_줄_것.update(sub="g-222", email="nov@example.com", email_verified=False)
    _, _, r2 = 한_바퀴(s, code="code-4")
    검사("이메일 확인 안 된 구글 계정 거절", r2.status_code == 400)

    s.post("/api/auth/signup", json={"email": "Lee@Example.com", "password": "이메일비번1234", "name": "이메일가입"})
    구글이_줄_것.update(sub="g-333", email="lee@example.com", email_verified=True, name="구글이름")
    _, _, r2 = 한_바퀴(s, code="code-5")
    t5 = parse_qs(urlparse(r2.headers["Location"]).query)["ticket"][0]
    r = s.post("/api/auth/google/claim", json={"ticket": t5}).get_json()
    pw = s.post("/api/auth/login", json={"email": "lee@example.com", "password": "이메일비번1234"}).get_json() or {}
    검사("같은 이메일로 먼저 가입한 계정에 붙음 · 이름 그대로 · 비밀번호 로그인도 됨",
         r["user"]["id"] == (pw.get("user") or {}).get("id") and r["user"]["name"] == "이메일가입")
    구글이_줄_것.update(sub="g-999")
    _, _, r2 = 한_바퀴(s, code="code-6")
    검사("다른 구글 계정이 이미 붙은 이메일은 거절 (409)", r2.status_code == 409)

    print(f"  {'─' * 70}\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main())
