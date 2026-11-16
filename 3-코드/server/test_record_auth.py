"""
test_record_auth.py — 기록기 주소의 문지기 (11/16 · 수업 전 보완)

주인 있는 과제의 기록은 그 주인 토큰으로만 읽고 쓴다. 주인 없는 과제(로그인 안 하고 기록)는 예전처럼 받는다.

  python 3-코드/server/app.py                 # 다른 창에서 서버를 켜고 (시험용 SQLite 권장)
  python 3-코드/server/test_record_auth.py
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
    print(f"  {'✅' if 조건 else '❌'} {이름:<38} {설명}")


def 가입(이름):
    email, pw = f"ra{uuid.uuid4().hex[:8]}@test.kr", "기록문지기12345"
    호출("/auth/signup", {"email": email, "password": pw, "name": 이름})
    return 호출("/auth/login", {"email": email, "password": pw})[1]["token"]


def 이벤트(sid, n, prev=C.GENESIS):
    evs = []
    for i in range(n):
        e = {"id": f"evt_{uuid.uuid4().hex[:10]}", "session_id": sid, "ts": f"2026-11-16T10:0{i}:00+09:00",
             "type": "window", "app": "WINWORD.EXE", "title": "보고서.docx", "category": "doc"}
        prev = C.next_hash(prev, e)
        e["h"] = prev
        evs.append(e)
    return evs, prev


def main():
    print(f"\n  기록기 주소 문지기 — 서버 {BASE}\n  " + "─" * 70)
    나, 남 = 가입("주인"), 가입("남")
    wid = "W-" + uuid.uuid4().hex[:8]
    호출("/works", {"id": wid, "title": "주인 있는 과제"}, 나)
    sid = str(uuid.uuid4())
    코드, _ = 호출(f"/works/{wid}/sessions", {"id": sid, "started_at": "2026-11-16T10:00:00+09:00"}, 나)
    검사("1 주인은 세션을 만든다", 코드 == 201, f"HTTP {코드}")
    evs, head = 이벤트(sid, 3)
    코드, 답 = 호출(f"/sessions/{sid}/events", {"events": evs, "chain_head": head}, 나)
    검사("2 주인은 이벤트를 보낸다", 코드 == 200 and 답.get("verified") is True, f"HTTP {코드}")

    끼움, _ = 이벤트(sid, 1, head)
    코드, _ = 호출(f"/sessions/{sid}/events", {"events": 끼움}, None)
    검사("3 토큰 없이 이벤트 끼워 넣기 → 401", 코드 == 401, f"HTTP {코드}")
    코드, _ = 호출(f"/sessions/{sid}/events", {"events": 끼움}, 남)
    검사("4 남의 토큰으로 끼워 넣기 → 403", 코드 == 403, f"HTTP {코드}")
    코드, 답 = 호출(f"/sessions/{sid}/context", {"items": [{"kind": "ai_answer", "text": "가짜"}]}, 남)
    검사("5 남이 맥락 넣기 → 403", 코드 == 403, f"HTTP {코드}")
    코드, _ = 호출(f"/sessions/{sid}/end", {"ended_at": "2026-11-16T10:30:00+09:00", "root": head}, 남)
    검사("6 남이 봉인 → 403", 코드 == 403, f"HTTP {코드}")
    for 경로 in (f"/sessions/{sid}", f"/sessions/{sid}/events", f"/sessions/{sid}/context"):
        a, b = 호출(경로, None, None)[0], 호출(경로, None, 남)[0]
        검사(f"7 읽기 막음 {경로.split(sid)[-1] or '/'}", a == 401 and b == 403, f"토큰 없음 {a} · 남 {b}")
    코드, 답 = 호출(f"/sessions/{sid}", None, 나)
    검사("8 주인은 읽는다 · 체인 그대로", 코드 == 200 and 답.get("integrity_ok") is True, f"HTTP {코드}")

    남과제 = "W-" + uuid.uuid4().hex[:8]
    호출("/works", {"id": 남과제, "title": "남의 과제"}, 남)
    코드, _ = 호출(f"/works/{남과제}/sessions", {"id": sid, "started_at": "2026-11-16T10:00:00+09:00"}, 남)
    검사("9 남이 내 세션을 자기 과제로 옮기기 → 403", 코드 == 403, f"HTTP {코드}")
    코드, _ = 호출(f"/works/{wid}/sessions", {"id": str(uuid.uuid4()), "started_at": "2026-11-16T11:00:00+09:00"}, 남)
    검사("10 남이 내 과제에 세션 붙이기 → 403", 코드 == 403, f"HTTP {코드}")
    코드, 답 = 호출(f"/sessions/{sid}/end", {"ended_at": "2026-11-16T10:30:00+09:00", "root": head}, 나)
    검사("11 주인 봉인 = 검증됨 (끼워 넣기 실패)", 코드 == 200 and 답.get("verified") is True, f"HTTP {코드}")

    익명과제, 익명 = "W-" + uuid.uuid4().hex[:8], str(uuid.uuid4())
    코드, _ = 호출(f"/works/{익명과제}/sessions", {"id": 익명, "started_at": "2026-11-16T12:00:00+09:00"}, None)
    evs, head = 이벤트(익명, 2)
    코드2, 답 = 호출(f"/sessions/{익명}/events", {"events": evs, "chain_head": head}, None)
    검사("12 주인 없는 과제는 예전처럼 받음", 코드 == 201 and 코드2 == 200 and 답.get("verified") is True, f"HTTP {코드} · {코드2}")

    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
