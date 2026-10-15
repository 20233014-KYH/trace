"""
test_google.py — PC 앱 쪽 구글 로그인 (10/15 · statement.py /local/auth/*) — 서버 · 브라우저는 흉내

  python app/test_google.py

확인하는 것:
  · 서버가 구글을 켰을 때만 버튼을 살림 (서버가 없거나 늦으면 "준비 중" 그대로)
  · [Google 로 계속하기] → 브라우저로 서버 start (이 앱이 만든 state · 이 앱 포트)
  · 돌아오면 그 state 일 때만 표를 토큰으로 바꿔 로그인 (auth.json) · 같은 state 두 번 안 됨 · 모르는 state 는 서버를 안 부름
  · 서버가 표를 거절하면 로그인 화면에 그 까닭
"""
import json
import os
import shutil
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_source as T                          # noqa: E402
ST = T.ST
검사 = T.검사


def main():
    print("\n  PC 앱 구글 로그인 검사 — 서버 · 브라우저 흉내\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-google-pc-")
    옛 = (ST._서버, ST.webbrowser.open, dict(ST.설정))
    try:
        ST.설정.update(server="https://srv.example/api", data_dir=data)
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        부름, 열림, 서버답 = [], [], {"providers": (200, {"google": True}), "claim": (200, {"token": "tok-1", "user": {"id": "u1", "name": "김구글"}}),
                                   "link": (200, {"google": True}), "unlink": (200, {"google": False})}

        def 서버(방법, 경로, **kw):
            부름.append((방법, 경로, kw.get("json"), kw.get("timeout")))
            return {"/auth/providers": 서버답["providers"], "/auth/google/claim": 서버답["claim"], "/auth/google/link": 서버답["link"],
                    "/auth/google/unlink": 서버답["unlink"], "/me": 서버답.get("me", (404, {}))}.get(경로, (404, {}))
        ST._서버 = 서버
        ST.webbrowser.open = 열림.append

        검사("서버가 구글을 켰으면 버튼 살림 (8초만 기다림)", c.get("/local/auth/providers", **HOST).json == {"google": True}
             and 부름[-1][3] == 8)
        서버답["providers"] = (502, {"error": "server_unreachable"})
        검사("서버가 없으면 준비 중 그대로", c.get("/local/auth/providers", **HOST).json == {"google": False})

        r = c.post("/local/auth/google/start", headers=H, **HOST)
        st = r.json["state"]
        u = urlparse(열림[-1])
        q = parse_qs(u.query)
        검사("브라우저로 서버 start · 이 앱의 state · 포트", u.netloc == "srv.example" and u.path == "/api/auth/google/start"
             and q == {"pc": [st], "port": [str(ST.PORT)]} and len(st) >= 30, 열림[-1][:70])
        검사("X-Trace-Local 없이는 시작 못 함", c.post("/local/auth/google/start", **HOST).status_code == 403)
        검사("시작 직후 상태 = 아직", c.get(f"/local/auth/google/status?state={st}", **HOST).json == {"done": False, "error": None})

        n = len(부름)
        r = c.get("/local/auth/google/done?ticket=t-1&state=다른것", **HOST)
        검사("모르는 state 로 돌아오면 거절 · 서버도 안 부름", r.status_code == 400 and len(부름) == n and "다시 시도" in r.get_data(as_text=True))
        r = c.get(f"/local/auth/google/done?ticket=t-1&state={st}", **HOST)
        auth = json.load(open(os.path.join(data, "auth.json"), encoding="utf-8"))
        검사("돌아오면 표 → 토큰 · auth.json 에 로그인 · 브라우저엔 '로그인됐어요'",
             r.status_code == 200 and 부름[-1][:3] == ("POST", "/auth/google/claim", {"ticket": "t-1", "device": 부름[-1][2]["device"]})
             and auth == {"server": "https://srv.example/api", "token": "tok-1", "user": {"id": "u1", "name": "김구글"}}
             and "로그인됐어요" in r.get_data(as_text=True) and r.headers.get("Cache-Control") == "no-store")
        검사("로그인 화면이 끝난 걸 앎", c.get(f"/local/auth/google/status?state={st}", **HOST).json == {"done": True, "error": None})
        n = len(부름)
        검사("같은 state 두 번 안 됨", c.get(f"/local/auth/google/done?ticket=t-2&state={st}", **HOST).status_code == 400 and len(부름) == n)

        st2 = c.post("/local/auth/google/start", headers=H, **HOST).json["state"]
        서버답["claim"] = (401, {"error": "unauthorized", "message": "로그인 시간이 지났어요"})
        r = c.get(f"/local/auth/google/done?ticket=old&state={st2}", **HOST)
        검사("서버가 표를 거절하면 로그인 화면에 그 까닭", r.status_code == 400
             and c.get(f"/local/auth/google/status?state={st2}", **HOST).json == {"done": False, "error": "로그인 시간이 지났어요"})
        검사("로그인 화면에 Google 버튼 자리 (id=b-google)", 'id="b-google"' in c.get("/login", **HOST).get_data(as_text=True))

        # ── 잇기 (설정 › 계정 · 10/15) — 로그인한 사람만 · 표는 이 PC 의 토큰과 함께 /auth/google/link 로 ──
        os.remove(os.path.join(data, "auth.json"))
        검사("잇기는 로그인해야", c.post("/local/auth/google/start", json={"mode": "link"}, headers=H, **HOST).status_code == 401)
        검사("이상한 mode 거절", c.post("/local/auth/google/start", json={"mode": "admin"}, headers=H, **HOST).status_code == 400)
        json.dump({"server": "https://srv.example/api", "token": "tok-naver", "user": {"id": "u-naver", "name": "네이버계정"}},
                  open(os.path.join(data, "auth.json"), "w", encoding="utf-8"))
        st3 = c.post("/local/auth/google/start", json={"mode": "link"}, headers=H, **HOST).json["state"]
        q = parse_qs(urlparse(열림[-1]).query)
        검사("잇기: 서버 start 에 mode=link", q.get("mode") == ["link"] and q.get("pc") == [st3])
        r = c.get(f"/local/auth/google/done?ticket=lt-1&state={st3}", **HOST)
        auth = json.load(open(os.path.join(data, "auth.json"), encoding="utf-8"))
        검사("잇기: 돌아오면 /auth/google/link (로그인은 그대로 · 토큰 안 바뀜)",
             r.status_code == 200 and 부름[-1][:3] == ("POST", "/auth/google/link", {"ticket": "lt-1"}) and auth["token"] == "tok-naver"
             and "이었어요" in r.get_data(as_text=True) and c.get(f"/local/auth/google/status?state={st3}", **HOST).json["done"] is True)
        st4 = c.post("/local/auth/google/start", json={"mode": "link"}, headers=H, **HOST).json["state"]
        서버답["link"] = (409, {"error": "conflict", "message": "이 구글 계정은 기록이 있는 다른 Trace 계정에 이어져 있어요"})
        r = c.get(f"/local/auth/google/done?ticket=lt-2&state={st4}", **HOST)
        검사("잇기 거절되면 설정 화면에 그 까닭", r.status_code == 400
             and c.get(f"/local/auth/google/status?state={st4}", **HOST).json["error"].startswith("이 구글 계정은"))
        r = c.post("/local/account/google/unlink", json={}, headers=H, **HOST)
        검사("끊기 → 서버 /auth/google/unlink", r.status_code == 200 and 부름[-1][:2] == ("POST", "/auth/google/unlink"))
        서버답["me"] = (200, {"id": "u-naver", "name": "네이버계정", "email": "yh@naver.com", "works": []})
        w = c.get("/local/works", **HOST).json
        검사("왼쪽 아래 프로필 칸: /local/works 에 이메일 (10/15)", w["user"] == {"id": "u-naver", "name": "네이버계정", "email": "yh@naver.com"})
        html = c.get("/settings?tab=account", **HOST).get_data(as_text=True)
        검사("설정 화면에 잇기 · 끊기", "Google 계정 잇기" in html and "/local/account/google/unlink" in html)
    finally:
        ST._서버, ST.webbrowser.open = 옛[0], 옛[1]
        ST.설정.clear()
        ST.설정.update(옛[2])
        shutil.rmtree(data, ignore_errors=True)
    print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    return 1 if T.실패 else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main())
