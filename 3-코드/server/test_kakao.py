"""
test_kakao.py — 카카오 로그인 · 잇기 (10/15 · server/app.py "구글 · 카카오 로그인") — 카카오 쪽은 흉내 · 서버는 이 프로세스 안 · 임시 DB

  python 3-코드/server/test_kakao.py

확인하는 것:
  · 설정하면 kakao=true · start → 카카오 주소 (REST 키 · 돌아올 곳 · state) · callback → 127.0.0.1 의 /local/auth/kakao/done
  · 카카오가 이메일을 안 주면: 회원번호로 새 계정 (이메일 없음으로 보임 · 비밀번호 없음 · 이름 = 닉네임)
  · 확인된 이메일이면 같은 이메일 계정에 붙음 · 확인 안 된 이메일은 남의 계정에 안 붙음
  · 구글 쪽지로 카카오 callback 못 씀 · 잇기 (네이버 계정에 카카오) · 끊기 규칙 (남는 로그인 길이 있을 때만)
  · 진짜 코드 바꾸기: 토큰 주소에 보내는 것 · 사용자 정보는 그 토큰으로 · 이메일 확인 여부
"""
import json
import os
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
d = tempfile.mkdtemp(prefix="trace-kakao-")
os.environ["TRACE_DB_URL"] = "sqlite:///" + os.path.join(d, "server.db")
for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "KAKAO_CLIENT_ID", "KAKAO_CLIENT_SECRET"):
    os.environ.pop(k, None)
import app as A                                   # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    통과, 실패 = 통과 + bool(조건), 실패 + (not 조건)
    print(f"  {'✅' if 조건 else '❌'} {이름:<46} {설명}")


카카오가_줄_것 = {}


def 한_바퀴(s, mode=None, p="kakao"):
    r1 = s.get(f"/api/auth/{p}/start?pc=pc-state-0123456789abcdef&port=5079" + (f"&mode={mode}" if mode else ""))
    q = parse_qs(urlparse(r1.headers.get("Location", "")).query)
    r2 = s.get(f"/api/auth/{p}/callback?code=c&state={q['state'][0]}") if q.get("state") else None
    return r1, q, r2


def 표(r):
    return parse_qs(urlparse(r.headers["Location"]).query)["ticket"][0]


def 로그인(s, mode=None):
    _, _, r2 = 한_바퀴(s, mode)
    return s.post("/api/auth/kakao/claim", json={"ticket": 표(r2)}).get_json()


def main():
    print("\n  카카오 로그인 검사 — 카카오 흉내 · 임시 DB\n  " + "─" * 70)
    s = A.app.test_client()
    검사("설정 없으면 카카오 버튼 안 살림", s.get("/api/auth/providers").get_json() == {"google": False, "kakao": False})
    os.environ.update(KAKAO_CLIENT_ID="rest-key-123", KAKAO_CLIENT_SECRET="카카오-비밀")
    검사("설정하면 kakao=true (구글은 그대로 false)", s.get("/api/auth/providers").get_json() == {"google": False, "kakao": True})
    진짜_바꾸기 = A._카카오_코드_바꾸기                      # ⑥ 에서 씀
    A._카카오_코드_바꾸기 = lambda code, 돌아올_곳, 설정: dict(카카오가_줄_것)

    # ① 이메일 없이 (기본 동의 항목: 닉네임만)
    카카오가_줄_것.update(sub="1001", email=None, email_verified=False, name="용현")
    r1, q, r2 = 한_바퀴(s)
    돌아감 = urlparse(r2.headers.get("Location", ""))
    검사("start → 카카오 주소 · REST 키 · 돌아올 곳 · code", r1.status_code == 302 and r1.headers["Location"].startswith(A.카카오_인증 + "?")
         and q["client_id"] == ["rest-key-123"] and q["redirect_uri"] == ["http://localhost/api/auth/kakao/callback"]
         and q["response_type"] == ["code"] and "code_challenge" not in q, r1.headers["Location"][:60])
    검사("callback → 이 PC 의 /local/auth/kakao/done", 돌아감.netloc == "127.0.0.1:5079" and 돌아감.path == "/local/auth/kakao/done")
    r = s.post("/api/auth/kakao/claim", json={"ticket": 표(r2)}).get_json()
    K = {"Authorization": f"Bearer {r['token']}"}
    me = s.get("/api/me", headers=K).get_json()
    검사("이메일 없는 카카오 → 새 계정 (이메일 없음 · 비밀번호 없음 · 닉네임)", me["email"] is None and me["password"] is False
         and me["kakao"] is True and me["google"] is False and me["name"] == "용현", f"{me}")
    검사("다시 카카오로 → 같은 계정", 로그인(s)["user"]["id"] == me["id"])
    검사("비밀번호 로그인 안 됨 (자리 채움 이메일로도)", s.post("/api/auth/login", json={"email": "kakao-1001@kakao.trace", "password": "!kakao"}).status_code == 401)
    검사("끊기: 카카오로만 로그인하는 계정은 못 끊음", s.post("/api/auth/kakao/unlink", headers=K).status_code == 400)

    # ② 확인된 이메일 → 같은 이메일 계정에 붙음 · 확인 안 된 이메일은 안 붙음
    s.post("/api/auth/signup", json={"email": "park@daum.net", "password": "다음비번12345", "name": "박이메일"})
    카카오가_줄_것.update(sub="2002", email="Park@Daum.net", email_verified=True, name="박카카오")
    r = 로그인(s)
    pw = s.post("/api/auth/login", json={"email": "park@daum.net", "password": "다음비번12345"}).get_json()
    검사("확인된 이메일 → 같은 이메일 계정 (이름 그대로)", r["user"]["id"] == pw["user"]["id"] and r["user"]["name"] == "박이메일")
    s.post("/api/auth/signup", json={"email": "lee@nate.com", "password": "네이트비번1234", "name": "이네이트"})
    카카오가_줄_것.update(sub="3003", email="lee@nate.com", email_verified=False, name="남")
    r = 로그인(s)
    pw = s.post("/api/auth/login", json={"email": "lee@nate.com", "password": "네이트비번1234"}).get_json()
    me3 = s.get("/api/me", headers={"Authorization": f"Bearer {r['token']}"}).get_json()
    검사("확인 안 된 이메일은 남의 계정에 안 붙음 → 새 계정 (이메일 없음)", r["user"]["id"] != pw["user"]["id"] and me3["email"] is None)

    # ③ 구글 쪽지로 카카오 callback (같은 비밀이어도) 못 씀
    os.environ.update(GOOGLE_CLIENT_ID="cid", GOOGLE_CLIENT_SECRET="카카오-비밀")
    gq = parse_qs(urlparse(s.get("/api/auth/google/start?pc=pc-state-0123456789abcdef&port=5079").headers["Location"]).query)
    검사("구글 쪽지로 카카오 callback 못 씀", s.get(f"/api/auth/kakao/callback?code=c&state={gq['state'][0]}").status_code == 400)
    os.environ.pop("GOOGLE_CLIENT_ID")
    os.environ.pop("GOOGLE_CLIENT_SECRET")

    # ④ 잇기 — 네이버 이메일 계정에 카카오 (위 ① 의 카카오로만 만든 빈 계정에서 옮김)
    s.post("/api/auth/signup", json={"email": "yh@naver.com", "password": "네이버비번1234", "name": "네이버계정"})
    N = {"Authorization": "Bearer " + s.post("/api/auth/login", json={"email": "yh@naver.com", "password": "네이버비번1234"}).get_json()["token"]}
    카카오가_줄_것.update(sub="1001", email=None, email_verified=False, name="용현")
    _, _, r2 = 한_바퀴(s, "link")
    t = 표(r2)
    검사("잇기 표는 로그인에 못 씀", s.post("/api/auth/kakao/claim", json={"ticket": t}).status_code == 401)
    _, _, r2 = 한_바퀴(s, "link")
    r = s.post("/api/auth/kakao/link", json={"ticket": 표(r2)}, headers=N)
    검사("잇기: 네이버 계정에 카카오 (빈 계정에서 옮김 · 그 계정 로그인 끊김)", r.status_code == 200 and r.get_json() == {"kakao": True}
         and s.get("/api/me", headers=K).status_code == 401)
    검사("이제 카카오로 로그인하면 네이버 계정", 로그인(s)["user"]["name"] == "네이버계정")
    _, _, r2 = 한_바퀴(s, "link")
    검사("카카오 잇기 표를 구글 잇기에 못 씀", s.post("/api/auth/google/link", json={"ticket": 표(r2)}, headers=N).status_code == 400)
    r = s.post("/api/auth/kakao/unlink", headers=N)
    검사("끊기: 비밀번호 있는 계정은 끊김", r.status_code == 200 and s.get("/api/me", headers=N).get_json()["kakao"] is False)

    # ⑤ 비밀번호 없이 구글 + 카카오 둘 다 있으면 하나는 끊을 수 있음
    with A.db.Session() as x:
        u = x.query(A.db.User).filter(A.db.User.kakao_sub == "3003").one()
        u.google_sub = "g-9"
        x.commit()
    카카오가_줄_것.update(sub="3003")
    T3 = {"Authorization": f"Bearer {로그인(s)['token']}"}
    검사("비밀번호 없어도 구글이 남으면 카카오는 끊을 수 있음", s.post("/api/auth/kakao/unlink", headers=T3).status_code == 200
         and s.post("/api/auth/google/unlink", headers=T3).status_code == 400)

    # ⑥ 진짜 코드 바꾸기 — 카카오 응답만 흉내
    새, 옛_열기, 보낸 = A, A.urllib.request.urlopen, []

    class 답:
        def __init__(self, x): self.x = x
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(self.x).encode()

    def 열기(요청, timeout=None):
        보낸.append(요청)
        if 요청.full_url == 새.카카오_토큰:
            return 답({"access_token": "kat-1", "token_type": "bearer"})
        return 답({"id": 4004, "properties": {"nickname": "옛닉"},
                  "kakao_account": {"profile": {"nickname": "카카오닉"}, "email": "k@kakao.com", "is_email_valid": True, "is_email_verified": True}})
    새.urllib.request.urlopen = 열기
    try:
        c = 진짜_바꾸기("code-9", "https://x/api/auth/kakao/callback", ("rest-key-123", "카카오-비밀"))
    finally:
        새.urllib.request.urlopen = 옛_열기
    몸 = parse_qs(보낸[0].data.decode())
    검사("코드 바꾸기: 토큰 주소에 REST 키 · 비밀 · code · 돌아올 곳",
         몸 == {"grant_type": ["authorization_code"], "client_id": ["rest-key-123"], "client_secret": ["카카오-비밀"],
               "redirect_uri": ["https://x/api/auth/kakao/callback"], "code": ["code-9"]})
    검사("사용자 정보는 그 토큰으로 · 번호 · 이메일 확인 · 닉네임",
         보낸[1].full_url == 새.카카오_나 and 보낸[1].get_header("Authorization") == "Bearer kat-1"
         and c == {"sub": "4004", "email": "k@kakao.com", "email_verified": True, "name": "카카오닉"}, f"{c}")

    print(f"  {'─' * 70}\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main())
