"""
test_home.py — 홈 · 로그인 화면(app/home.py)을 녹화 시험 자료로. 서버 없이 돈다 (서버 응답은 흉내).

  python app/test_home.py

확인하는 것:
  · / 는 로그인했으면 홈, 아니면 로그인 화면 · 홈 화면도 로그인 안 했으면 로그인으로 · 옛 화면은 /make
  · 홈 목록 = 서버 내 과제 + 이 PC 기록 수 · 주인 없는 기록은 알림으로 · 서버가 401 이면 로그인으로
  · 과제 카드 = 지금 단계 · 숫자(질문 · 결과물에 들어간 답 · 이어진 문장) · 다음 화면 주소
  · 기록기가 꺼져 있으면 지금 상태 없음 · 점수·퍼센트 없음
"""
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_source as T                          # noqa: E402  학생 PC 만들기 · 같은 자료
ST = T.ST
검사 = T.검사


def CF_경로(wid):
    import confirm as CF
    return CF._경로(wid)


def main():
    print("\n  홈 · 로그인 화면 검사 — 녹화 시험 자료 · 서버 흉내\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-home-")
    옛 = dict(ST.출처._기록)
    try:
        T.학생_PC(data)
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
        import home as H
        H.BRIDGE = "http://127.0.0.1:9/status"                       # 기록기 꺼짐
        c = ST.app.test_client()
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        loc = lambda r: r.headers.get("Location", "")

        # ── 로그인 안 함 ──
        검사("/ → 로그인 화면", loc(c.get("/", **HOST)).endswith("/login"))
        검사("홈도 로그인 안 했으면 로그인으로", loc(c.get("/home", **HOST)).endswith("/login"))
        r = c.get("/login", **HOST)
        검사("로그인 화면 열림 (이메일 · 가입 · 어느 서버)", r.status_code == 200 and all(t in r.get_data(as_text=True) for t in ("이메일", "가입하기", "/local/state")))
        검사("옛 내역서 만들기 화면은 /make", c.get("/make", **HOST).status_code == 200)
        검사("/local/home 은 401", c.get("/local/home", **HOST).status_code == 401)

        # ── 로그인함 (서버 흉내) ──
        works = [{"id": "W-match_view", "title": "보고 고쳐 친 과제", "ai_scope": None},
                 {"id": "W-match_web", "title": "웹 붙여넣기 과제", "ai_scope": None},
                 {"id": "W-없음", "title": "이 PC 기록 없는 과제", "ai_scope": None}]
        응답 = {"/me": (200, {"works": works})}
        ST.출처._기록["auth"] = lambda: {"token": "t", "user": {"name": "시험 학생", "email": "s@example.test"}}
        ST.출처._기록["server"] = lambda 방법, 경로, **kw: 응답.get(경로, (404, {}))
        ST.출처._기록["statement_exists"] = lambda w: False
        검사("/ → 홈", loc(c.get("/", **HOST)).endswith("/home"))
        검사("처음이면 홈 대신 준비 점검(/welcome) · 화면 열림", loc(c.get("/home", **HOST)).endswith("/welcome")
             and c.get("/welcome", **HOST).status_code == 200)
        from core import prefs
        prefs.save(data, {"onboarded": True})
        r = c.get("/home", **HOST)
        검사("홈 화면 열림", r.status_code == 200 and "내 과제" in r.get_data(as_text=True))
        # 앱을 새로 켰을 때 — PC 에 남겨 둔 마지막 과제 목록으로 홈을 먼저 (무료 서버가 자다 깨는 10~20초 · 10/15)
        검사("남겨 둔 목록이 없으면 ?cached=1 은 404 (화면은 서버 답을 기다림)", c.get("/local/home?cached=1", **HOST).status_code == 404)
        ST._me_남기기("t", {"works": works[:2]})
        부름 = []
        옛서버 = ST.출처._기록["server"]
        ST.출처._기록["server"] = lambda 방법, 경로, **kw: (부름.append(경로), 옛서버(방법, 경로, **kw))[1]
        cd = c.get("/local/home?cached=1", **HOST)
        검사("남겨 둔 목록이 있으면 서버를 안 묻고 바로 · 토큰은 지문만 저장", cd.status_code == 200 and len(cd.json["works"]) == 2 and not 부름
             and '"t"' not in open(ST._me_파일(), encoding="utf-8").read())
        ST.출처._기록["server"] = 옛서버
        옛auth = ST.출처._기록["auth"]
        ST.출처._기록["auth"] = lambda: {"token": "다른-계정"}
        검사("다른 계정이면 남겨 둔 목록을 안 씀", c.get("/local/home?cached=1", **HOST).status_code == 404)
        ST.출처._기록["auth"] = 옛auth
        d = c.get("/local/home", **HOST).json
        검사("프로필 칸: 서버에 없는 칸은 로그인 때 것 그대로", d["user"] == {"name": "시험 학생", "email": "s@example.test"})
        응답["/me"] = (200, {"works": works, "name": "새 이름", "email": "new@example.test"})
        검사("프로필 칸: 서버의 이름 · 이메일 (10/15)", c.get("/local/home", **HOST).json["user"] == {"name": "새 이름", "email": "new@example.test"})
        응답["/me"] = (200, {"works": works})
        검사("내 과제 = 서버 목록 + 이 PC 기록 수", [w["id"] for w in d["works"]][:2] != [] and
             {w["id"]: w["pc_sessions"] for w in d["works"]}["W-없음"] == 0 and
             {w["id"]: w["pc_sessions"] for w in d["works"]}["W-match_view"] > 0)
        검사("기록 있는 과제가 먼저 (최근 기록 순)", d["works"][-1]["id"] == "W-없음")
        검사("주인 없는 기록 = 내 목록에 없는 이 PC 기록", {o["id"] for o in d["orphans"]} == {f"W-{k}" for k in T.CASES} - {"W-match_view", "W-match_web"})
        검사("기록기 꺼짐 → 지금 상태 없음", d["recording"] is None)
        검사("기록 상태만 묻는 주소 (화면이 3초마다) · 기록기 꺼짐 → null", c.get("/local/recording", **HOST).json == {"recording": None})

        카드 = c.get("/local/home/card?work_id=W-match_view", **HOST).json
        검사("카드: 지금 단계 · 다음 화면", 카드["stage"] == "source" and 카드["go"] == "/source?work=W-match_view" and 카드["report_made"] is False)
        f = 카드["facts"]
        검사("카드 숫자: 질문 수 · 확인한 연결만 (연결 확인 전이면 붙여넣기 기록 있는 것만)",
             f["questions"] > 0 and f["answers"] is not None and f["linked"] is not None and f["answers"] <= f["linked"], str(f))
        txt = c.get("/local/home", **HOST).get_data(as_text=True) + str(카드)
        검사("점수·퍼센트 없음 · PC 경로 없음", not re.search(r"ratio|score|\d+\s?%", txt) and data.replace("\\", "\\\\") not in txt)
        ST.출처._기록["statement_exists"] = lambda w: True
        카드 = c.get("/local/home/card?work_id=W-match_view", **HOST).json
        검사("내역서 만든 과제 → 내역서 화면", 카드["stage"] == "report" and 카드["report_made"] is True and 카드["go"].startswith("/export"))

        # ── 새 과제 · 과제 설정 · 과제 상세 (캔버스 1-1 · 2) ──
        print("\n  ━━ 새 과제 · 과제 상세")
        import work as WK
        보냄 = []
        def 서버(방법, 경로, **kw):
            보냄.append((방법, 경로, kw.get("json")))
            if 방법 == "POST" and 경로 == "/works":
                return 201, {"id": kw["json"]["id"], "title": kw["json"]["title"]}
            if 방법 == "PATCH":
                return 200, {"ok": True}
            if 방법 == "GET" and 경로.startswith("/works/W-match_view"):
                return 200, {"id": "W-match_view", "title": "보고 고쳐 친 과제", "ai_scope": "개념 이해만 허용",
                             "sessions": [{"id": s, "sealed": True} for s in ST._과제별_세션()["W-match_view"]]}
            return 응답.get(경로, (404, {}))
        ST.출처._기록["server"] = 서버
        ST.출처._기록["statement_exists"] = lambda w: False
        P =lambda path, body: c.post(path, json=body, headers={"X-Trace-Local": "1"}, **HOST)
        검사("새 과제 · 과제 상세 · 과제 설정 화면 열림", all(c.get(u, **HOST).status_code == 200 for u in ("/new", "/work?work=W-match_view", "/work/settings?work=W-match_view")))
        검사("이름 없으면 거절 · 마감 모양 검사", P("/local/work/create", {"title": " "}).status_code == 400
             and P("/local/work/create", {"title": "a", "due": "내일"}).status_code == 400 and not 보냄)
        r = P("/local/work/create", {"title": "새 시험 과제", "course": "창의프로젝트", "due": "2026-10-15T23:59", "ai_scope": "개념 이해만"})
        새 = r.json.get("id", "")
        검사("새 과제: 서버엔 이름 · AI 규칙만 (이 PC 만의 id W-…)", r.status_code == 201 and re.fullmatch(r"W-[0-9a-f]{10}", 새)
             and 보냄[-1] == ("POST", "/works", {"id": 새, "title": "새 시험 과제", "ai_scope": "개념 이해만"}))
        검사("과목 · 마감은 이 PC 에만 (data/work-<id>.json)", WK.meta(새).get("course") == "창의프로젝트" and WK.meta(새)["due"] == "2026-10-15T23:59")
        검사("기록 없는 과제를 누르면 과제 상세로", loc(c.get(f"/go?work={새}", **HOST)) == f"/work?work={새}")
        r = P("/local/work/save", {"work_id": 새, "title": "고친 이름", "course": "", "due": ""})
        검사("과제 설정 저장: 이름은 서버로 · 마감 지움은 PC", r.status_code == 200 and 보냄[-1][0] == "PATCH" and 보냄[-1][2]["title"] == "고친 이름"
             and WK.meta(새)["due"] == "")
        검사("잘못된 과제 id 거절", P("/local/work/save", {"work_id": "../x", "title": "a"}).status_code == 400)
        d = c.get("/local/work?work_id=W-match_view", **HOST).json
        s0 = d["sessions"][0] if d["sessions"] else {}
        검사("과제 상세: 기록 줄 = 이 PC 기록 · 서버 일치 · 질문 · 붙여넣기 · 시간",
             len(d["sessions"]) == len(ST._과제별_세션()["W-match_view"]) and s0.get("sealed") is True
             and s0.get("questions", 0) > 0 and s0.get("active_sec") is not None, str(s0))
        검사("과제 상세: 단계 · 다음 화면 · AI 규칙 · 기록된 문서 이름만 (PC 경로 없음)",
             d["stage"] == "source" and d["go"] == "/source?work=W-match_view" and d["work"]["ai_scope"] == "개념 이해만 허용"
             and d["docs"] and set(d["docs"][0]) == {"name", "exists"} and data.replace("\\", "\\\\") not in json.dumps(d))
        WK.설정["bridge"] = lambda: {"work_id": "W-다른것", "session_id": "x"}
        r = P("/local/record/start", {"work_id": 새})
        검사("이미 다른 기록이 켜져 있으면 기록 시작 안 함", r.status_code == 409 and "이미" in r.json["message"])
        WK.설정["bridge"] = lambda: None

        # ── 과제 삭제 · 기록 하나 지우기 · 옮기기 (캔버스 Delete · 10/15) ──
        print("\n  ━━ 과제 삭제 · 기록 하나 지우기 · 옮기기")
        보냄2 = []
        def 서버2(방법, 경로, **kw):
            if 방법 in ("DELETE", "PATCH"):
                보냄2.append((방법, 경로, kw.get("json")))
                return (502, {"message": "서버 꺼짐"}) if 경로.endswith("W-match_web") else (200, {"ok": True})
            if 방법 == "GET" and 경로.startswith("/works/"):
                w = 경로.split("/")[-1]
                return 200, {"id": w, "title": {"W-match_view": "보고 고쳐 친 과제", "W-match_web": "웹 붙여넣기 과제"}.get(w, "새 시험 과제"), "sessions": []}
            return 서버(방법, 경로, **kw)
        ST.출처._기록["server"] = 서버2
        G = lambda w: c.get(f"/local/work/delete-info?work_id={w}", **HOST).json
        P2 = lambda 주소, body: c.post(주소, json=body, headers={"X-Trace-Local": "1"}, **HOST)
        D = lambda body: P2("/local/work/delete", body)
        줄 = lambda sid: [x for p in ("events-*.jsonl", "context-*.jsonl", "ai-messages-*.jsonl") for x in ST._jsonl(p) if x.get("session_id") == sid]
        i = G(새)
        검사("기록 없는 과제: 기록 0 · 한 번 확인으로 지움", i["sessions"] == 0 and not i["recording"]
             and D({"work_id": 새}).status_code == 200 and 보냄2[-1][:2] == ("DELETE", f"/works/{새}") and not os.path.exists(WK._경로(새)))
        WK.설정["bridge"] = lambda: {"work_id": "W-다른것", "session_id": "x"}
        검사("기록 창이 켜져 있으면 못 지움 · 못 옮김 (다른 과제를 기록 중이어도)", G("W-match_view")["recording"]
             and D({"work_id": "W-match_view"}).status_code == 409
             and P2("/local/session/delete", {"work_id": "W-match_proc", "session_id": "S-match_proc"}).status_code == 409
             and P2("/local/session/move", {"work_id": "W-match_proc", "session_id": "S-match_proc", "to": "W-match_mix"}).status_code == 409)
        WK.설정["bridge"] = lambda: None
        검사("다른 과제의 기록은 못 건드림 · 잘못된 id 거절",
             P2("/local/session/delete", {"work_id": "W-match_view", "session_id": "S-match_proc"}).status_code == 404
             and P2("/local/session/delete", {"work_id": "../x", "session_id": "S-match_proc"}).status_code == 400)
        # 기록 하나만 지우기 — 내역서 파일(export-…) 은 그대로
        내역서 = os.path.join(data, "export-W-match_proc.json"); open(내역서, "w", encoding="utf-8").write('{"made": {"statement_id": "st1"}}')
        r = P2("/local/session/delete", {"work_id": "W-match_proc", "session_id": "S-match_proc"})
        검사("이 기록만 지우기: 서버 · 이 PC 그 기록 줄만 · 내역서는 그대로", r.status_code == 200 and r.json["lines"] > 0 and not 줄("S-match_proc")
             and 보냄2[-1][:2] == ("DELETE", "/sessions/S-match_proc") and os.path.exists(내역서), str(r.json))
        # 옮기기 — 기록 파일은 그대로 (체인 해시) · moved.json 으로 과제가 바뀜
        전 = len(줄("S-match_app"))
        r = P2("/local/session/move", {"work_id": "W-match_app", "session_id": "S-match_app", "to": "W-match_mix"})
        검사("다른 과제로 옮기기: 서버 PATCH · 이 PC 에선 옮긴 과제에 보임 · 기록 줄은 그대로", r.status_code == 200
             and 보냄2[-1] == ("PATCH", "/sessions/S-match_app", {"work_id": "W-match_mix"})
             and "S-match_app" in ST._과제별_세션()["W-match_mix"] and "W-match_app" not in ST._과제별_세션() and len(줄("S-match_app")) == 전)
        검사("같은 과제로는 안 옮김", P2("/local/session/move", {"work_id": "W-match_mix", "session_id": "S-match_app", "to": "W-match_mix"}).status_code == 400)
        r = D({"work_id": "W-match_web"})
        검사("서버가 못 지우면 이 PC 기록도 그대로", r.status_code == 502 and "W-match_web" in ST._과제별_세션())
        다른 = len(ST._과제별_세션().get("W-match_rec", ()))
        r = D({"work_id": "W-match_view"})
        검사("과제 지우기: 서버 · 이 PC 기록 줄 · 연결 확인 · 내보내기 파일 (이름 입력 없음)", r.status_code == 200 and r.json["lines"] > 0
             and not 줄("S-match_view") and "W-match_view" not in ST._과제별_세션() and not os.path.exists(CF_경로("W-match_view")), str(r.json))
        r = D({"work_id": "W-match_mix"})
        검사("옮겨 온 기록도 그 과제와 함께 지워짐 · 옮김 표에서도 빠짐", r.status_code == 200 and not 줄("S-match_app")
             and "S-match_app" not in (ST.safefile.read_json(os.path.join(data, "moved.json"), {}) or {}))
        검사("다른 과제 기록은 그대로", len(ST._과제별_세션().get("W-match_rec", ())) == 다른 > 0)
        ST.출처._기록["server"] = lambda 방법, 경로, **kw: 응답.get(경로, (404, {}))

        응답["/me"] = (401, {"error": "unauthorized"})
        검사("서버가 토큰을 거절하면 401 (화면은 로그인으로)", c.get("/local/home", **HOST).status_code == 401)
        print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    finally:
        ST.출처._기록.clear(); ST.출처._기록.update(옛)
        shutil.rmtree(data, ignore_errors=True)
    return T.실패 == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(0 if main() else 1)
