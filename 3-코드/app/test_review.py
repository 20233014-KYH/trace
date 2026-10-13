"""
test_review.py — 돌아보기(app/review.py)를 녹화 시험 자료로. 서버는 흉내.

  python app/test_review.py

확인하는 것: 로그인 안 하면 401 · 이번 학기에 질문이 모두 잡힘 · 쓰임새 합 = 질문 수 · 찾은 것은 규칙대로 (조건 맞을 때만 · 최대 3)
            · 목표 담기 · 해냈어요 · 빼기 · 잘못된 목표 거절 · 점수 · 퍼센트 · PC 경로 없음
"""
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_source as T                          # noqa: E402
ST = T.ST
검사 = T.검사


def main():
    print("\n  돌아보기 검사 — 녹화 시험 자료 · 서버 흉내\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-rv-")
    옛 = dict(ST.출처._기록)
    try:
        T.학생_PC(data)
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
        import review as R
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        검사("로그인 안 했으면 401", c.get("/local/review", **HOST).status_code == 401)
        works = [{"id": f"W-{k}", "title": k} for k in T.CASES]
        ST.출처._기록["auth"] = lambda: {"token": "t"}
        ST.출처._기록["server"] = lambda 방법, 경로, **kw: (200, {"works": works}) if 경로 == "/me" else (404, {})
        검사("화면 열림", c.get("/review", **HOST).status_code == 200)
        d = c.get("/local/review?period=term", **HOST).json
        모든질문 = R._질문들({w["id"]: w["title"] for w in works})
        검사("이번 학기 · 질문이 모두 잡힘 (기록 켜기 전 대화는 뺌)", d["questions"] == len(모든질문) > 0, f"질문 {d['questions']}")
        검사("쓰임새 합 = 질문 수 · 주별 합 = 질문 수", sum(d["usage"].values()) == d["questions"]
             and sum(w["learn"] + w["fix"] + w["write"] for w in d["weeks"]) == d["questions"])
        대화 = R._대화(모든질문)
        한번 = sum(1 for v in 대화.values() if len(v) == 1)
        keys = [t["key"] for t in d["tips"]]
        검사("찾은 것: 대화 절반 넘게 한 번 묻고 끝날 때만 '되묻기'", ("followup" in keys) == (len(대화) >= 2 and 한번 * 2 > len(대화)),
             f"대화 {len(대화)} · 한 번 {한번}")
        검사("찾은 것: 작성 > 고치기·검토 일 때만 '검토 맡기기'", ("review" in keys) == (d["usage"]["write"] > 0 and d["usage"]["fix"] < d["usage"]["write"]))
        검사("찾은 것은 최대 3 · 사실 · 해 볼 것이 있음", len(d["tips"]) <= 3 and all(t["fact"] and t["todo"] for t in d["tips"]))
        txt = json.dumps(d, ensure_ascii=False)
        검사("점수 · 퍼센트 · PC 경로 없음", not re.search(r"score|grade|\d+\s?%|점수:", txt) and data.replace("\\", "\\\\") not in txt)

        P = lambda body: c.post("/local/review/goal", json=body, headers=H, **HOST)
        검사("잘못된 목표 거절", P({"key": "x", "action": "add"}).status_code == 400 and P({"key": "review", "action": "jump"}).status_code == 400)
        P({"key": "followup", "action": "add"}); P({"key": "followup", "action": "add"})
        g = c.get("/local/review?period=term", **HOST).json["goals"]
        검사("목표 담기 (두 번 눌러도 하나) · 담은 뒤 기록이 없으면 '다음 과제부터'", len(g) == 1 and g[0]["key"] == "followup" and g[0]["after"] is None
             and g[0]["before"] is not None)
        P({"key": "followup", "action": "done"})
        검사("해냈어요", c.get("/local/review", **HOST).json["goals"][0]["done"] is True)
        P({"key": "followup", "action": "remove"})
        검사("목표 빼기 · 이 PC data/goals.json 에만", c.get("/local/review", **HOST).json["goals"] == []
             and json.load(open(os.path.join(data, "goals.json"), encoding="utf-8")) == [])
        print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    finally:
        ST.출처._기록.clear(); ST.출처._기록.update(옛)
        shutil.rmtree(data, ignore_errors=True)
    return T.실패 == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(0 if main() else 1)
