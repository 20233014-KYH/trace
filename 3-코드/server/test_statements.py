"""
test_statements.py — AI 활용 내역서(docs/api.md 10절)가 제대로 도는지.

  python 3-코드/server/app.py               # 다른 창에서 서버를 켜고
  python 3-코드/server/test_statements.py

기록기 흉내를 낸다: 과제 → 세션 → ai_msg(해시만) 이벤트 → 봉인. 그다음 학생이 원문을 골라 내역서를 만든다.
특히 세 가지를 본다:
  · 기록 당시 글을 그대로 내면 "검증됨", 한 글자라도 고치면 "조작됨"으로 잡히나   ★ 이 기능의 이유
  · "아니다"로 고른 연결의 결과물 원문이 서버에 남지 않나                            ★ 원칙: 확인 전엔 밖으로 안 나감
  · 남의 과제로 내역서를 만들거나 공유 링크를 끊을 수 없나
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import chain as C                     # noqa: E402
from core.texthash import sha256_text           # noqa: E402

BASE = f"http://127.0.0.1:{os.environ.get('TRACE_PORT', '5000')}/api"   # 맥은 5000 = AirPlay → TRACE_PORT=5050

통과, 실패 = 0, 0


def 호출(경로, 몸=None, 토큰=None, 방법=None, 날것=None):
    머리 = {"Content-Type": "application/json"}
    if 토큰:
        머리["Authorization"] = f"Bearer {토큰}"
    자료 = 날것 if 날것 is not None else (json.dumps(몸).encode() if 몸 is not None else None)
    요청 = urllib.request.Request(BASE + 경로, data=자료, headers=머리,
                                  method=방법 or ("POST" if 자료 is not None else "GET"))
    try:
        with urllib.request.urlopen(요청, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        본문 = e.read()
        try:
            return e.code, json.loads(본문)
        except ValueError:
            return e.code, {"_html": 본문[:80].decode("utf-8", "replace")}
    except urllib.error.URLError as e:
        print(f"\n  서버에 연결하지 못했습니다 ({e.reason}).")
        print("  다른 창에서 먼저 켜 주세요:  python 3-코드/server/app.py\n")
        sys.exit(1)


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    if 조건:
        통과 += 1
        print(f"  ✅ {이름:<34} {설명}")
    else:
        실패 += 1
        print(f"  ❌ {이름:<34} {설명}")


def 사람(꼬리, 이름):
    몸 = {"email": f"{이름}{꼬리}@test.kr", "password": "테스트비번12345", "name": 이름}
    호출("/auth/signup", 몸)
    _, 답 = 호출("/auth/login", {"email": 몸["email"], "password": 몸["password"]})
    return 답.get("token")


def 기록하기(wid, 글들, 봉인=True):
    """기록기 흉내. 글들 = [(role, text)] → ai_msg 이벤트에는 해시만 넣는다. (세션 id, {role+순번: 이벤트 id})"""
    sid = str(uuid.uuid4())
    호출(f"/works/{wid}/sessions", {"id": sid, "started_at": "2026-10-08T14:00:00+09:00",
                                     "device": {"name": "TEST", "os": "win"}})
    이벤트들 = [{"id": "evt_000001", "ts": "2026-10-08T14:00:00+09:00", "type": "session_start"}]
    for i, (role, text) in enumerate(글들):
        이벤트들.append({"id": f"evt_{i + 2:06d}", "ts": f"2026-10-08T14:0{i + 1}:00+09:00", "type": "ai_msg",
                        "tool": "chatgpt", "conv": "c1", "turn": str(i // 2 + 1), "role": role,
                        "len": len(text), "hash": sha256_text(text)})
    이벤트들.append({"id": f"evt_{len(이벤트들) + 1:06d}", "ts": "2026-10-08T14:30:00+09:00", "type": "session_end"})
    prev = C.GENESIS
    for e in 이벤트들:
        prev = C.next_hash(prev, e)
        e["h"] = prev
    호출(f"/sessions/{sid}/events", {"events": 이벤트들, "chain_head": prev, "chain_len": len(이벤트들)})
    if 봉인:
        호출(f"/sessions/{sid}/end", {"ended_at": "2026-10-08T14:30:00+09:00", "root": prev})
    return sid, [e["id"] for e in 이벤트들 if e["type"] == "ai_msg"]


def main():
    print()
    print(f"  AI 활용 내역서 검사 — {BASE}")
    print("  " + "─" * 74)

    꼬리 = uuid.uuid4().hex[:8]
    갑, 을 = 사람(꼬리, "갑"), 사람(꼬리, "을")
    _, w = 호출("/works", {"title": "내역서 시험", "ai_scope": "자료 조사만 허용"}, 토큰=갑)
    wid = w["id"]

    질문 = "광합성의 명반응과 암반응 차이를 설명해 줘"
    답 = "명반응은 빛을 받아 ATP와 NADPH를 만들고, 암반응(캘빈 회로)은 그것으로 CO2를 고정해 포도당을 만듭니다."
    결과 = "명반응은 빛으로 ATP와 NADPH를 만들고, 캘빈 회로는 이를 써서 이산화탄소를 고정한다."
    sid, (q_id, a_id) = 기록하기(wid, [("question", 질문), ("answer", 답)])

    맞다 = {"answer_hash": sha256_text(답), "question_hash": sha256_text(질문), "result_hash": sha256_text(결과),
            "result_text": 결과, "location": {"file": "보고서.docx", "paragraph": 3},
            "kind": "edited", "origin": "suggested", "decision": "confirmed"}
    아니다 = {"answer_hash": sha256_text(답), "result_hash": sha256_text("다른 문단"), "result_text": "보내면 안 되는 글",
              "location": {"file": "보고서.docx", "paragraph": 7}, "kind": "edited", "origin": "suggested",
              "decision": "rejected"}
    원문 = [{"session_id": sid, "event_id": q_id, "text": 질문}, {"session_id": sid, "event_id": a_id, "text": 답}]

    # ① 그대로 내면 검증됨
    코드, r = 호출(f"/works/{wid}/statements", {"messages": 원문, "links": [맞다, 아니다]}, 토큰=갑)
    검사("1 내역서 만들기 (그대로)", 코드 == 201 and r.get("verified") is True, f"HTTP {코드} · 문제 {r.get('problems')}")
    st1 = r.get("id")
    검사("2 봉인된 세션 표시", r.get("sessions") == [{"id": sid, "sealed": True, "verified": True}],
         f"{r.get('sessions')}")

    # ② 답을 한 글자 고쳐 내면 조작됨 — 버리지 않고 표시
    고친원문 = [원문[0], {**원문[1], "text": 답.replace("포도당", "녹말")}]
    코드, r = 호출(f"/works/{wid}/statements", {"messages": 고친원문, "links": [맞다]}, 토큰=갑)
    이유 = {p.get("why") for p in r.get("problems", [])}
    검사("3 한 글자 고치면 조작됨 ★", 코드 == 201 and r.get("verified") is False and "hash_mismatch" in 이유,
         f"verified={r.get('verified')} · {sorted(이유)}")
    검사("4 고친 답을 가리킨 연결도 표시", "answer_not_verified" in 이유, "")

    # ③ 체인에 없는 이벤트 · 다른 과제의 세션
    코드, r = 호출(f"/works/{wid}/statements",
                  {"messages": [{"session_id": sid, "event_id": "evt_000001", "text": 질문}]}, 토큰=갑)
    검사("5 ai_msg 가 아닌 이벤트", {p["why"] for p in r.get("problems", [])} == {"not_in_chain"},
         f"{r.get('problems')}")
    _, w2 = 호출("/works", {"title": "다른 과제"}, 토큰=갑)
    sid2, (q2, _) = 기록하기(w2["id"], [("question", 질문), ("answer", 답)])
    코드, r = 호출(f"/works/{wid}/statements",
                  {"messages": [{"session_id": sid2, "event_id": q2, "text": 질문}]}, 토큰=갑)
    검사("6 다른 과제의 세션", {p["why"] for p in r.get("problems", [])} == {"not_in_work"}, f"{r.get('problems')}")

    # ④ 아직 봉인 안 한 세션
    sid3, (q3, _) = 기록하기(wid, [("question", "봉인 전 질문"), ("answer", "봉인 전 답")], 봉인=False)
    코드, r = 호출(f"/works/{wid}/statements",
                  {"messages": [{"session_id": sid3, "event_id": q3, "text": "봉인 전 질문"}]}, 토큰=갑)
    검사("7 봉인 전 세션은 검증 안 됨", r.get("verified") is False and
         {p["why"] for p in r.get("problems", [])} == {"session_not_sealed"}, f"{r.get('problems')}")

    # ⑤ 가림 — 가린 이벤트의 원문을 같이 보내면 거절
    코드, _ = 호출(f"/works/{wid}/statements",
                  {"messages": 원문, "redactions": [{"session_id": sid, "event_id": q_id}]}, 토큰=갑)
    검사("8 가린 원문을 같이 보내면 400", 코드 == 400, f"HTTP {코드}")
    코드, r = 호출(f"/works/{wid}/statements",
                  {"messages": 원문[1:], "links": [{**맞다, "question_hash": None}, 아니다],
                   "redactions": [{"session_id": sid, "event_id": q_id}], "sentence": "광합성 설명에 ChatGPT 답을 참고해 고쳐 씀"},
                  토큰=갑)
    검사("9 질문을 가리고 내역서", 코드 == 201 and r.get("verified") is True and r["counts"]["redactions"] == 1,
         f"HTTP {코드} · {r.get('problems')}")
    st_last = r.get("id")

    # ⑥ 남의 과제 · 로그인 없이
    코드, _ = 호출(f"/works/{wid}/statements", {"messages": 원문}, 토큰=을)
    검사("10 남의 과제로 못 만듦", 코드 == 404, f"HTTP {코드} (404 여야 함)")
    코드, _ = 호출(f"/works/{wid}/statements", {"messages": 원문})
    검사("11 로그인 없이 못 만듦", 코드 == 401, f"HTTP {코드}")
    코드, _ = 호출(f"/works/{wid}/statements", {"links": [{"decision": "maybe"}]}, 토큰=갑)
    검사("12 이상한 decision 거절", 코드 == 400, f"HTTP {코드}")
    큰글 = json.dumps({"messages": [{"session_id": sid, "event_id": a_id, "text": "가" * (2 * 1024 * 1024)}]}).encode()
    코드, _ = 호출(f"/works/{wid}/statements", 토큰=갑, 날것=큰글)
    검사("13 5MB 넘으면 413", 코드 == 413, f"HTTP {코드}")

    # ⑦ 최신 내역서 (학생용)
    코드, r = 호출(f"/works/{wid}/statements/latest", 토큰=갑)
    검사("14 최신 내역서 = 마지막 것", 코드 == 200 and r.get("id") == st_last, f"HTTP {코드}")
    글전부 = json.dumps(r, ensure_ascii=False)
    검사("15 '아니다' 원문은 안 남음 ★", "보내면 안 되는 글" not in 글전부 and r.get("rejected") == 1,
         f"rejected={r.get('rejected')}")
    코드, _ = 호출(f"/works/{wid}/statements/latest", 토큰=을)
    검사("16 남의 내역서 못 봄", 코드 == 404, f"HTTP {코드}")

    # ⑧ 공유 링크 (교수용 · 로그인 없음)
    코드, sh = 호출(f"/statements/{st1}/share", {"expires_in_days": 7}, 토큰=갑)
    검사("17 공유 링크 만들기", 코드 == 201 and sh.get("token"), f"HTTP {코드} · 만료 {sh.get('expires_at')}")
    코드, r = 호출(f"/share/{sh.get('token')}")
    링크 = (r.get("links") or [{}])[0]
    검사("18 교수가 로그인 없이 읽음", 코드 == 200 and r.get("work", {}).get("title") == "내역서 시험"
         and 링크.get("answer", {}).get("text") == 답 and 링크.get("result", {}).get("text") == 결과,
         f"HTTP {코드} · 연결 {len(r.get('links') or [])}개 · 허용 범위 “{r.get('ai_scope')}”")
    글전부 = json.dumps(r, ensure_ascii=False)
    검사("19 교수 화면에 '아니다' 원문 없음", "보내면 안 되는 글" not in 글전부 and "rejected_links" not in r
         and "messages" not in r, "")
    코드, _ = 호출(f"/statements/{st1}/share", {"expires_in_days": 365}, 토큰=갑)
    검사("20 만료 365일은 거절", 코드 == 400, f"HTTP {코드}")
    코드, _ = 호출(f"/statements/{st1}/share", {}, 토큰=을)
    검사("21 남의 내역서로 링크 못 만듦", 코드 == 404, f"HTTP {코드}")
    코드, _ = 호출(f"/shares/{sh['token']}", 토큰=을, 방법="DELETE")
    검사("22 남의 링크 못 끊음", 코드 == 404, f"HTTP {코드}")
    코드, _ = 호출(f"/shares/{sh['token']}", 토큰=갑, 방법="DELETE")
    코드2, _ = 호출(f"/share/{sh['token']}")
    검사("23 끊은 링크는 404", 코드 == 200 and 코드2 == 404, f"끊기 {코드} · 그 뒤 읽기 {코드2}")
    코드, _ = 호출("/share/nosuchtoken123")
    검사("24 없는 링크 404", 코드 == 404, f"HTTP {코드}")

    print("  " + "─" * 74)
    print(f"  {통과}개 통과, {실패}개 실패")
    print()
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
