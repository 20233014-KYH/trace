"""
test_record.py — 기록 다시 보기(app/record.py)를 녹화 시험 자료로. 서버 없이 돈다.

  python app/test_record.py                  # 검사
  python app/test_record.py --serve [포트]    # 같은 자료로 화면 띄우기 (기본 5092) → /record?work=W-match_web&session=S-match_web

확인하는 것:
  · 숫자 = 과제 상세와 같음 (질문 · 붙여넣기) · 줄은 시각 순 · 질문 · 답은 빠짐없이
  · 답 표시 = 출처 보기와 같음 (결과물에 이어진 답은 "참고만" 이 아님 · 이어지지 않은 답은 "참고만")
  · 붙여넣기 출처: AI 답 · 다른 곳 개수가 core/match 와 같음
  · 잠깐 멈춤 = 시각만 (줄 · 막대 · 멈춘 시간)
  · 문서 위치(PC 경로) · 점수 · 퍼센트가 응답에 없음 · 잘못된 id 거절
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


def 멈춤_넣기(data, sid, a, b):
    p = os.path.join(data, "events-2026-10-05.jsonl")
    with open(p, "a", encoding="utf-8") as f:
        for t, ts in (("pause_start", a), ("pause_end", b)):
            f.write(json.dumps({"id": f"evt_p{t}", "session_id": sid, "ts": ts, "type": t}, ensure_ascii=False) + "\n")


def main():
    print("\n  기록 다시 보기 검사 — 녹화 시험 자료\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-rec-")
    옛 = dict(ST.출처._기록)
    try:
        T.학생_PC(data)
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        from core import match as M
        G = lambda w, s: c.get(f"/local/record/detail?work_id={w}&session_id={s}", headers=H, **HOST)

        검사("화면 열림 · 과제 상세 기록 줄이 이 화면으로 이어짐", c.get("/record?work=W-match_web&session=S-match_web", **HOST).status_code == 200
             and "/record?work=" in open(os.path.join(HERE, "detail.html"), encoding="utf-8").read())
        검사("잘못된 id 거절 · 없는 기록 404", G("../x", "S-match_web").status_code == 400 and G("W-match_web", "S-없음").status_code == 404
             and G("W-match_web", "S-match_view").status_code == 404)

        for case in T.CASES:
            print(f"\n  ━━ {case}")
            wid, sid = f"W-{case}", f"S-{case}"
            r = G(wid, sid)
            if r.status_code != 200:
                검사("응답", False, str(r.json)); continue
            d = r.json
            msgs, events, context, _ = ST.출처.과제_기록(wid)
            evs = [e for e in events if e["session_id"] == sid]
            mine = [m for m in M.latest_messages(msgs) if m["session_id"] == sid]
            its = d["items"]
            가운데 = [x["ts"] for x in its if x["kind"] not in ("start", "end")]
            검사("줄은 시각 순 · 첫 줄 기록 시작", 가운데 == sorted(가운데) and its[0]["kind"] == "start"
                 and all(x["kind"] != "end" for x in its[:-1]))
            검사("숫자 = 과제 상세 (질문 · 붙여넣기)",
                 d["stats"]["questions"] == sum(1 for m in mine if m["role"] == "question") and d["stats"]["pastes"] == sum(1 for e in evs if e["type"] == "paste"),
                 f"질문 {d['stats']['questions']} · 붙여넣기 {d['stats']['pastes']}")
            검사("질문 · 답 줄 빠짐없이", sum(1 for x in its if x["kind"] in ("q", "a")) == len(mine) == len(d["lanes"]["ai"]))
            if d["linked"]:
                src = c.post("/local/source", data={"work_id": wid}, headers=H, **HOST).json
                쓰인답 = {q["refs"]["a"]["event_id"] for q in src["questions"] if q["uses"] and "a" in q.get("refs", {})}
                답줄 = {m["event_id"]: x for m, x in zip(sorted(mine, key=lambda m: m["ts"]), [x for x in its if x["kind"] in ("q", "a")])
                       if m["role"] == "answer"}
                맞음 = all((x["tag"] or {}).get("t") != "참고만" if eid in 쓰인답 else (x["tag"] or {}).get("c") in ("ref", "plain", None)
                         for eid, x in 답줄.items())
                검사("답 표시 = 출처 보기 (이어진 답 · 참고만)", 맞음, f"이어진 답 {len(쓰인답)}")
            붙 = [x for x in its if x["kind"] == "paste"]
            ai, 다른 = len(M.pasted_from_ai(evs, [c_ for c_ in context if c_["session_id"] == sid])), len(M.pasted_from_other(evs, [c_ for c_ in context if c_["session_id"] == sid]))
            검사("붙여넣기 출처 = core/match (AI 답 · 다른 곳)",
                 sum(1 for x in 붙 if (x["tag"] or {}).get("t") == "AI 답") == ai and sum(1 for x in 붙 if (x["tag"] or {}).get("t") == "다른 곳") == 다른,
                 f"AI 답 {ai} · 다른 곳 {다른} · 모두 {len(붙)}")
            txt = json.dumps(d, ensure_ascii=False)
            검사("PC 경로 · 점수 · 퍼센트 없음", data.replace("\\", "\\\\") not in txt and not re.search(r"ratio|score|cover|\d+\s?%", txt))

        print("\n  ━━ 잠깐 멈춤 · Word 글")
        evs = [e for e in ST.출처.과제_기록("W-match_view")[1]]
        a, b = evs[len(evs) // 2]["ts"], evs[len(evs) // 2 + 1]["ts"]
        멈춤_넣기(data, "S-match_view", a, b)
        d = G("W-match_view", "S-match_view").json
        p = [x for x in d["items"] if x["kind"] == "pause"]
        검사("멈춤 = 줄 하나 · 막대 · 시각만", len(p) == 1 and p[0]["tag"]["t"] == "시각만" and d["lanes"]["pause"] == [[a, b]]
             and d["stats"]["pause_sec"] == d["session"]["pause_sec"])
        검사("Word 글 = 문서 변화 줄 (match_view 는 doc_change 기록 있음) · 친 글자 수",
             any(x["kind"] == "word" for x in d["items"]) and d["stats"]["typed"] > 0, f"친 글자 {d['stats']['typed']}")
        d = G("W-match_proc", "S-match_proc").json
        검사("탐색기 등 과제 프로그램 아닌 키 입력은 빼고 셈",
             d["stats"]["typed"] == sum(e.get("count", 0) for e in T.L("match_proc", "events") if e["type"] == "keys" and e.get("category") == "work"))
        print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    finally:
        ST.출처._기록.clear(); ST.출처._기록.update(옛)
        shutil.rmtree(data, ignore_errors=True)
    return T.실패 == 0


def serve(port):
    data = tempfile.mkdtemp(prefix="trace-rec-")
    T.학생_PC(data)
    ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
    ST.PORT = port                                   # 로컬만() 이 Host 를 이 포트로 확인
    print(f"  http://127.0.0.1:{port}/record?work=W-match_web&session=S-match_web")
    try:
        ST.app.run(host="127.0.0.1", port=port, debug=False)
    finally:
        shutil.rmtree(data, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if "--serve" in sys.argv:
        i = sys.argv.index("--serve")
        serve(int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 5092)
    else:
        sys.exit(0 if main() else 1)
