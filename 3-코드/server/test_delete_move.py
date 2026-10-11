"""
test_delete_move.py — 과제 지우기 · 기록 지우기 · 기록 옮기기 · 잠깐 멈춤 (10/10 박상진 요청)

  python 3-코드/server/app.py                 # 다른 창에서 서버를 켜고 (시험용 SQLite 권장)
  python 3-코드/server/test_delete_move.py
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

BASE = f"http://127.0.0.1:{os.environ.get('TRACE_PORT', '5000')}/api"
통과, 실패 = 0, 0


def 호출(경로, 몸=None, 토큰=None, 방법=None):
    머리 = {"Content-Type": "application/json"}
    if 토큰:
        머리["Authorization"] = f"Bearer {토큰}"
    요청 = urllib.request.Request(BASE + 경로, data=json.dumps(몸).encode() if 몸 is not None else None, headers=머리,
                                  method=방법 or ("POST" if 몸 is not None else "GET"))
    try:
        with urllib.request.urlopen(요청, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}
    except urllib.error.URLError as e:
        sys.exit(f"\n  서버에 연결하지 못했습니다 ({e.reason}). 먼저 켜 주세요:  python 3-코드/server/app.py\n")


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✅' if 조건 else '❌'} {이름:<32} {설명}")


def 사람(이름):
    몸 = {"email": f"{이름}{uuid.uuid4().hex[:8]}@test.kr", "password": "테스트비번12345", "name": 이름}
    호출("/auth/signup", 몸)
    return 호출("/auth/login", {"email": 몸["email"], "password": 몸["password"]})[1]["token"]


def 기록하기(wid, 토큰, 멈춤=False):
    """기록기 흉내 — 질문·답 하나 (멈춤=True 면 21:10~21:24 잠깐 멈춤). (세션 id, 답 이벤트 id, 답 글)"""
    sid = str(uuid.uuid4())
    호출(f"/works/{wid}/sessions", {"id": sid, "started_at": "2026-10-10T21:00:00+09:00"}, 토큰=토큰)
    답 = "캘빈 회로는 ATP와 NADPH로 이산화탄소를 고정한다." + uuid.uuid4().hex[:4]
    evs = [{"ts": "2026-10-10T21:00:00+09:00", "type": "session_start"},
           {"ts": "2026-10-10T21:05:00+09:00", "type": "ai_msg", "tool": "chatgpt", "role": "answer", "len": len(답), "hash": sha256_text(답)}]
    if 멈춤:
        evs += [{"ts": "2026-10-10T21:10:00+09:00", "type": "pause_start"}, {"ts": "2026-10-10T21:24:00+09:00", "type": "pause_end"}]
    evs.append({"ts": "2026-10-10T21:40:00+09:00", "type": "session_end"})
    prev = C.GENESIS
    for i, e in enumerate(evs):
        e["id"] = f"evt_{i + 1:06d}"
        prev = C.next_hash(prev, e)
        e["h"] = prev
    호출(f"/sessions/{sid}/events", {"events": evs, "chain_head": prev})
    코드, r = 호출(f"/sessions/{sid}/end", {"ended_at": evs[-1]["ts"], "root": prev})
    return sid, evs[1]["id"], 답, r.get("verified")


def main():
    print(f"\n  지우기 · 옮기기 · 멈춤 검사 — {BASE}\n  " + "─" * 70)
    갑, 을 = 사람("갑"), 사람("을")
    w1 = 호출("/works", {"title": "과제 하나"}, 토큰=갑)[1]["id"]
    w2 = 호출("/works", {"title": "과제 둘"}, 토큰=갑)[1]["id"]
    w을 = 호출("/works", {"title": "을의 과제"}, 토큰=을)[1]["id"]

    # ① 잠깐 멈춤
    s1, a1, 답1, ok = 기록하기(w1, 갑, 멈춤=True)
    검사("1 멈춤이 든 기록도 서버 기록과 일치", ok is True, "pause_start · pause_end 가 체인에 들어감")
    r = 호출(f"/works/{w1}/summary", 토큰=갑)[1]
    검사("2 기록 시간에서 멈춘 시간 뺌", r.get("minutes") == 26.0 and r.get("pause_minutes") == 14.0 and r.get("pauses") == 1,
         f"기록 {r.get('minutes')}분 · 멈춤 {r.get('pause_minutes')}분")
    검사("3 멈춘 시작·끝 시각", r["by_session"][0]["pauses"] == [{"start": "2026-10-10T21:10:00+09:00", "end": "2026-10-10T21:24:00+09:00"}], "")

    # ② 기록 옮기기 — 과제 하나에서 켰는데 사실은 과제 둘
    s2, a2, 답2, _ = 기록하기(w1, 갑)
    코드, r = 호출(f"/sessions/{s2}", {"work_id": w2}, 토큰=갑, 방법="PATCH")
    검사("4 기록 옮기기", 코드 == 200 and r.get("work_id") == w2, f"HTTP {코드}")
    코드, r = 호출(f"/works/{w2}/statements", {"messages": [{"session_id": s2, "event_id": a2, "text": 답2}]}, 토큰=갑)
    검사("5 옮긴 기록으로 내역서 = 검증됨 ★", 코드 == 201 and r.get("verified") is True, f"{r.get('problems')}")
    코드, _ = 호출(f"/sessions/{s2}", {"work_id": w을}, 토큰=갑, 방법="PATCH")
    검사("6 남의 과제로는 못 옮김", 코드 == 400, f"HTTP {코드}")
    코드, _ = 호출(f"/sessions/{s2}", {"work_id": w을}, 토큰=을, 방법="PATCH")
    검사("7 남의 기록은 못 옮김", 코드 == 404, f"HTTP {코드}")

    # ③ 기록 하나 지우기
    s3, *_ = 기록하기(w1, 갑)
    코드, _ = 호출(f"/sessions/{s3}", 토큰=을, 방법="DELETE")
    검사("8 남의 기록은 못 지움", 코드 == 404, f"HTTP {코드}")
    코드, r = 호출(f"/sessions/{s3}", 토큰=갑, 방법="DELETE")
    검사("9 기록 지우기", 코드 == 200 and r.get("deleted_at"), "")
    r = 호출(f"/works/{w1}/summary", 토큰=갑)[1]
    검사("10 요약: 지운 기록 1개 · 숫자엔 안 들어감", len(r.get("deleted_sessions", [])) == 1 and r.get("sessions") == 1, "")
    코드, _ = 호출(f"/sessions/{s3}/events", {"events": [{"id": "evt_000099", "ts": "2026-10-10T22:00:00+09:00", "type": "keys"}]})
    검사("11 지운 기록에 더 보내면 410", 코드 == 410, f"HTTP {코드} (되살아나지 않게)")
    코드, r = 호출(f"/sessions/{s3}/events")
    검사("12 지운 기록의 이벤트는 없음", r.get("events") == [], "")

    # ④ 과제 지우기 — 이미 낸 링크는 "지운 기록입니다"
    코드, st = 호출(f"/works/{w1}/statements", {"messages": [{"session_id": s1, "event_id": a1, "text": 답1}]}, 토큰=갑)
    sh = 호출(f"/statements/{st['id']}/share", {}, 토큰=갑)[1]
    코드, _ = 호출(f"/works/{w1}", 토큰=을, 방법="DELETE")
    검사("13 남의 과제는 못 지움", 코드 == 404, f"HTTP {코드}")
    코드, r = 호출(f"/works/{w1}", 토큰=갑, 방법="DELETE")
    검사("14 과제 지우기", 코드 == 200 and r.get("deleted_at"), f"기록 {r.get('sessions')}개")
    코드, r = 호출(f"/share/{sh['token']}")
    검사("15 링크: 지운 기록입니다 ★", 코드 == 410 and "지운 기록" in r.get("message", "") and "links" not in r,
         f"HTTP {코드} · “{r.get('message')}”")
    코드, _ = 호출(f"/share/{sh['token']}/pdf")
    검사("16 지운 과제는 PDF 도 없음", 코드 == 404, f"HTTP {코드}")
    목록 = 호출("/works", 토큰=갑)[1]
    검사("17 내 과제 목록에서 빠짐", all(w["id"] != w1 for w in 목록) and any(w["id"] == w2 for w in 목록), "")
    코드, _ = 호출(f"/works/{w1}/sessions", {"id": str(uuid.uuid4()), "started_at": "2026-10-12T10:00:00+09:00"})
    검사("18 지운 과제에 새 기록 안 받음", 코드 == 410, f"HTTP {코드}")
    코드, _ = 호출(f"/sessions/{s1}/events")
    검사("19 지운 과제의 이벤트도 지워짐", 호출(f"/sessions/{s1}/events")[1].get("events") == [], "")

    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
