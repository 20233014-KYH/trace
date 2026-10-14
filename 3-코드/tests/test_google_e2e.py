"""
test_google_e2e.py — 구글 로그인 · 잇기를 PC 앱 ↔ 서버 한 바퀴로 (10/15) — 구글만 흉내, 나머지는 진짜 코드 (한 프로세스 · 임시 DB)

  python 3-코드/tests/test_google_e2e.py

PC 앱 [Google 로 계속하기] → (브라우저) 서버 start → 구글 → 서버 callback → (브라우저) PC 앱 done → PC 앱이 서버 claim · link
브라우저가 하는 일(주소 따라가기)만 이 시험이 대신한다.
  ① 네이버 이메일로 가입 · 로그인 → 설정 › 계정 [Google 계정 잇기] → 구글로 로그인하면 네이버 계정
  ② 처음 보는 구글 계정 → 새 계정
"""
import json
import os
import shutil
import sys
import tempfile
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
d = tempfile.mkdtemp(prefix="trace-google-e2e-")
os.environ["TRACE_DB_URL"] = "sqlite:///" + os.path.join(d, "server.db")
os.environ.update(GOOGLE_CLIENT_ID="cid.apps.googleusercontent.com", GOOGLE_CLIENT_SECRET="비밀-시험")
sys.path[:0] = [os.path.join(ROOT, "server"), os.path.join(ROOT, "app"), ROOT]
import app as 서버앱                               # noqa: E402  server/app.py
import test_source as T                           # noqa: E402  app 시험 도구 (PC 앱 statement)
ST = T.ST
검사 = T.검사

구글 = {}
서버앱._구글_코드_바꾸기 = lambda code, v, r, s: dict(구글)       # 구글 토큰 주소만 흉내
s = 서버앱.app.test_client()


class 응답:
    def __init__(self, r):
        self.status_code, self._r = r.status_code, r

    def json(self):
        return self._r.get_json()


def 서버로(방법, 경로, **kw):
    """PC 앱의 _서버 자리 — 인터넷 서버 대신 이 프로세스의 서버로 (토큰은 PC 앱의 auth.json 에서)"""
    머리 = kw.pop("headers", {}) or {}
    t = ST._auth().get("token")
    if t:
        머리["Authorization"] = f"Bearer {t}"
    kw.pop("timeout", None)
    r = s.open("/api" + 경로, method=방법, headers=머리, **kw)
    return r.status_code, (r.get_json() or {})


def 브라우저(c, H, 주소):
    """PC 앱이 연 주소를 브라우저처럼 따라간다: 서버 start → (구글 흉내: code 붙여 callback) → PC 앱 done"""
    u = urlparse(주소)
    r = s.get(u.path + "?" + u.query)                                   # 서버 start → 구글로 302
    state = dict(x.split("=", 1) for x in urlparse(r.headers["Location"]).query.split("&"))["state"]
    r = s.get(f"/api/auth/google/callback?code=c&state={state}")       # 구글이 돌려보냄 → 서버 → PC 앱으로 302
    돌아감 = urlparse(r.headers.get("Location", ""))
    if 돌아감.netloc != f"127.0.0.1:{ST.PORT}":
        return r
    return c.get(돌아감.path + "?" + 돌아감.query, **H)                  # PC 앱 done


def main():
    print("\n  구글 로그인 · 잇기 한 바퀴 (PC 앱 ↔ 서버 · 구글만 흉내)\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-google-e2e-pc-")
    옛 = (ST._서버, ST.webbrowser.open, dict(ST.설정))
    열림 = []
    try:
        ST.설정.update(server="http://test/api", data_dir=data)
        ST._서버 = 서버로
        ST.webbrowser.open = 열림.append
        c = ST.app.test_client()
        H = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        L = {"X-Trace-Local": "1"}
        검사("PC 로그인 화면 Google 버튼 살아남", c.get("/local/auth/providers", **H).json == {"google": True})

        # ① 네이버 이메일 계정 → 잇기 → 구글로 로그인하면 그 계정
        r = c.post("/local/signup", json={"email": "yh@naver.com", "password": "네이버비번1234", "name": "네이버계정"}, headers=L, **H)
        네이버 = r.json["user"]["id"]
        st = c.post("/local/auth/google/start", json={"mode": "link"}, headers=L, **H).json["state"]
        구글.update(sub="g-1", email="yh.kim@gmail.com", email_verified=True, name="김구글")
        r = 브라우저(c, H, 열림[-1])
        검사("잇기: 브라우저에 '이었어요' · 설정 화면이 끝난 걸 앎", r.status_code == 200 and "이었어요" in r.get_data(as_text=True)
             and c.get(f"/local/auth/google/status?state={st}", **H).json["done"] is True)
        a = c.get("/local/settings", **H).json["account"]
        검사("설정 › 계정: Google 이어짐 · 비밀번호 그대로", a["google"] is True and a["password"] is True and a["email"] == "yh@naver.com")
        c.post("/local/logout", json={}, headers=L, **H)
        st = c.post("/local/auth/google/start", json={}, headers=L, **H).json["state"]
        r = 브라우저(c, H, 열림[-1])
        auth = json.load(open(os.path.join(data, "auth.json"), encoding="utf-8"))
        검사("로그아웃 뒤 Google 로 로그인 → 네이버 계정", r.status_code == 200 and auth["user"]["id"] == 네이버
             and c.get(f"/local/auth/google/status?state={st}", **H).json["done"] is True)

        # ② 처음 보는 구글 계정 → 새 계정 (구글로만)
        c.post("/local/logout", json={}, headers=L, **H)
        구글.update(sub="g-2", email="new.student@gmail.com", name="새학생")
        c.post("/local/auth/google/start", json={}, headers=L, **H)
        브라우저(c, H, 열림[-1])
        a = c.get("/local/settings", **H).json["account"]
        검사("처음 보는 구글 계정 → 새 계정 (비밀번호 없음)", a["email"] == "new.student@gmail.com" and a["password"] is False and a["google"] is True)
    finally:
        ST._서버, ST.webbrowser.open = 옛[0], 옛[1]
        ST.설정.clear()
        ST.설정.update(옛[2])
        shutil.rmtree(data, ignore_errors=True)
        shutil.rmtree(d, ignore_errors=True)
    print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    return 1 if T.실패 else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main())
