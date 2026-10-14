"""
test_settings.py — 설정 화면(app/options.py · core/prefs.py)을 녹화 시험 자료로. 서버는 흉내.

  python app/test_settings.py

확인하는 것:
  · 설정값: 기본값(내역서 모두 켬 · 링크 14일) · 잘못된 값 거절 · 저장하면 이 PC data/settings.json 에만 · 깨진 파일이면 기본값
  · 내보내기가 설정 › 내역서 기본값을 처음 값으로 씀 (과제에서 고른 게 있으면 그게 먼저)
  · 계정: 이름 고치기 · 비밀번호 바꾸기는 서버로 · 지금 비번 틀림은 400 (화면이 로그인으로 튀지 않게)
  · 내 데이터: 과제별 크기 · PC 경로는 안 보냄 · 기록할 곳 목록 모양
  · 원문 기록을 끄는 설정은 없음 (끌 수 없음)
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_source as T                          # noqa: E402
ST = T.ST
검사 = T.검사


def main():
    print("\n  설정 화면 검사 — 녹화 시험 자료 · 서버 흉내\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-set-")
    옛 = dict(ST.출처._기록)
    try:
        T.학생_PC(data)
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
        from core import prefs
        import export as EX
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        P = lambda path, body: c.post(path, json=body, headers=H, **HOST)
        보냄 = []

        def 서버(방법, 경로, **kw):
            보냄.append((방법, 경로, kw.get("json")))
            if 경로 == "/me" and 방법 == "GET":
                return 200, {"name": "시험 학생", "email": "s@example.test", "works": [{"id": "W-match_view", "title": "보고 고쳐 친 과제"}]}
            if 경로 == "/me" and 방법 == "PATCH":
                return 200, {"name": kw["json"]["name"]}
            if 경로 == "/auth/password":
                return (200, {"ok": True}) if kw["json"]["password"] == "지금비밀번호1" else (401, {"message": "지금 비밀번호가 맞지 않습니다"})
            return 404, {}
        ST.출처._기록["auth"] = lambda: {"token": "t", "user": {"name": "시험 학생"}}
        ST.출처._기록["server"] = 서버

        검사("설정 화면 열림", c.get("/settings", **HOST).status_code == 200)
        d = c.get("/local/settings", **HOST).json
        검사("기본값: 내역서 모두 켬 · 링크 14일 · 쉬는 시간 5분 · 오른쪽 아래",
             d["prefs"]["with_source"] and d["prefs"]["with_process"] and d["prefs"]["mask_part"] and d["prefs"]["link_days"] == 14
             and d["prefs"]["idle_min"] == 5 and d["prefs"]["position"] == "br")
        검사("원문 기록을 끄는 설정은 없음", not any(k in d["prefs"] for k in ("ai_question", "ai_answer", "office", "capture", "mask")))
        검사("기록할 곳 5개 (크롬 · 엣지 · ChatGPT 앱 · Claude 앱 · Word) · 상태만",
             [x["key"] for x in d["checks"]] == ["chrome", "edge", "gptapp", "claudeapp", "word"] + (["keys"] if sys.platform == "darwin" else [])
             and all(x["state"] in ("ok", "missing", "none", "unknown") for x in d["checks"]))
        검사("계정: 이름 · 이메일 (서버 주소는 안 보냄)", d["account"] == {"name": "시험 학생", "email": "s@example.test"}
             and "server" not in json.dumps(d))
        w = d["data"]["works"]
        검사("내 데이터: 내 과제만 과제별 크기 · 나머지는 개수만 · PC 경로 없음",
             [x["id"] for x in w] == ["W-match_view"] and w[0]["bytes"] > 0 and w[0]["sessions"] == 1 and d["data"]["other"] == len(T.CASES) - 1
             and d["data"]["total"] >= w[0]["bytes"] and data.replace("\\", "\\\\") not in json.dumps(d))

        검사("잘못된 값 거절 (모르는 키 · 고를 수 없는 값 · 글자)", P("/local/settings", {"office": False}).status_code == 400
             and P("/local/settings", {"link_days": 90}).status_code == 400 and P("/local/settings", {"show_time": "no"}).status_code == 400
             and P("/local/settings", {"idle_min": True}).status_code == 400 and P("/local/settings", {}).status_code == 400)
        r = P("/local/settings", {"with_source": False, "link_days": 30, "position": "tl"})
        파일 = os.path.join(data, "settings.json")
        검사("저장: 이 PC data/settings.json 에 기본값과 다른 것만", r.status_code == 200 and r.json["prefs"]["link_days"] == 30
             and json.load(open(파일, encoding="utf-8")) == {"with_source": False, "link_days": 30, "position": "tl"})
        W = "W-match_mix"
        초안 = c.post("/local/export", data={"work_id": W}, headers=H, **HOST).json["draft"]
        검사("내보내기 처음 값 = 설정 (출처 보기 끔 · 30일)", 초안["with_source"] is False and 초안["days"] == 30 and 초안["with_process"] is True)
        P("/local/export/draft", {"work_id": W, "with_source": True})
        초안 = c.post("/local/export", data={"work_id": W}, headers=H, **HOST).json["draft"]
        검사("과제에서 고른 게 설정보다 먼저", 초안["with_source"] is True)
        open(파일, "w", encoding="utf-8").write("{깨짐")
        검사("설정 파일이 깨져도 기본값", prefs.load(data) == prefs.DEFAULTS)

        r = P("/local/account/name", {"name": "  "})
        r2 = P("/local/account/name", {"name": "새 이름"})
        검사("이름 고치기: 빈 이름 거절 · 서버로 · 왼쪽 아래 이름도", r.status_code == 400 and r2.status_code == 200
             and 보냄[-1] == ("PATCH", "/me", {"name": "새 이름"}))
        r = P("/local/account/password", {"password": "틀림", "new_password": "새비밀번호1234"})
        r2 = P("/local/account/password", {"password": "지금비밀번호1", "new_password": "짧음"})
        r3 = P("/local/account/password", {"password": "지금비밀번호1", "new_password": "새비밀번호1234"})
        검사("비밀번호: 지금 비번 틀림 400 · 짧으면 거절(서버 안 부름) · 맞으면 바뀜", r.status_code == 400 and r2.status_code == 400
             and r3.status_code == 200 and 보냄[-1][1] == "/auth/password")
        검사("X-Trace-Local 없으면 못 바꿈", c.post("/local/settings", json={"show_time": False}, **HOST).status_code == 403)
        print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    finally:
        ST.출처._기록.clear(); ST.출처._기록.update(옛)
        shutil.rmtree(data, ignore_errors=True)
    return T.실패 == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(0 if main() else 1)
