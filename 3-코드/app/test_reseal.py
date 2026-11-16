"""
test_reseal.py — 봉인이 빠진 기록 다시 보내기 (app/reseal.py · 11/16)

  python 3-코드/server/app.py                 # 다른 창에서 서버를 켜고 (시험용 SQLite 권장)
  python 3-코드/app/test_reseal.py

v0.1.18 맥 실제 시험과 같은 모양을 만든다: PC 엔 session_end 까지 있는데 서버엔 ① 이벤트는 다 갔고 봉인만 없음
② 마지막 2건 + 봉인이 없음 ③ 세션째 없음. 그리고 ④ 남의 기록 ⑤ PC 기록이 서버와 다른 것.
"""
import json
import os
import sys
import tempfile
import uuid

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from core import chain as C                     # noqa: E402
import reseal as R                              # noqa: E402

BASE = f"http://127.0.0.1:{os.environ.get('TRACE_PORT', '5000')}/api"
통과, 실패 = 0, 0


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✅' if 조건 else '❌'} {이름:<44} {덧}")


def 사람(이름):
    email, pw = f"rs{uuid.uuid4().hex[:8]}@test.kr", "다시봉인12345"
    requests.post(BASE + "/auth/signup", json={"email": email, "password": pw, "name": 이름}, timeout=30)
    return requests.post(BASE + "/auth/login", json={"email": email, "password": pw}, timeout=30).json()["token"]


def 서버를(토큰):
    def 부름(방법, 경로, **kw):
        r = requests.request(방법, BASE + 경로, headers={"Authorization": f"Bearer {토큰}"}, timeout=30, **kw)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}
    return 부름


def 기록(sid, wid, n=6):
    evs, prev = [], C.GENESIS
    종류 = ["session_start"] + ["window"] * (n - 2) + ["session_end"]
    for i, t in enumerate(종류):
        e = {"id": f"evt_{i + 1:06d}", "session_id": sid, "ts": f"2026-11-16T16:{10 + i:02d}:00+09:00", "type": t}
        if t == "session_start":
            e["work_id"] = wid
        if t == "window":
            e.update(app="WINWORD.EXE", title=f"보고서 {i}", category="doc")
        prev = C.next_hash(prev, {k: v for k, v in e.items() if k != "h"})
        e["h"] = prev
        evs.append(e)
    evs.insert(3, {"id": "hb1", "session_id": sid, "ts": "2026-11-16T16:12:30+09:00", "type": "heartbeat"})   # 하트비트는 안 보냄
    return evs


def main():
    print(f"\n  봉인 다시 보내기 — 서버 {BASE}\n  " + "─" * 72)
    try:
        requests.get(BASE + "/health", timeout=30)
    except requests.RequestException:
        sys.exit("  서버를 먼저 켜 주세요:  python 3-코드/server/app.py")
    나, 남 = 사람("나"), 사람("남")
    S, 남S = 서버를(나), 서버를(남)
    wid = "W-" + uuid.uuid4().hex[:8]
    S("POST", "/works", json={"id": wid, "title": "봉인 시험"})
    data = tempfile.mkdtemp(prefix="trace-rs-")
    s1, s2, s3, s5 = (str(uuid.uuid4()) for _ in range(4))
    모두 = []
    for sid, 보낼 in ((s1, "봉인만 빠짐"), (s2, "끝 2건 빠짐"), (s3, "세션 없음"), (s5, "다름")):
        evs = 기록(sid, wid)
        모두 += evs
        보내기 = [e for e in evs if e["type"] != "heartbeat"]
        if 보낼 == "세션 없음":
            continue
        S("POST", f"/works/{wid}/sessions", json={"id": sid, "started_at": evs[0]["ts"]})
        if 보낼 == "끝 2건 빠짐":
            보내기 = 보내기[:-2]
        if 보낼 == "다름":
            보내기[1] = {**보내기[1], "title": "서버엔 다른 제목"}        # 서버엔 다른 글이 먼저 들어감
        S("POST", f"/sessions/{sid}/events", json={"events": 보내기})
    남과제, s4 = "W-" + uuid.uuid4().hex[:8], str(uuid.uuid4())
    남S("POST", "/works", json={"id": 남과제, "title": "남의 과제"})
    남S("POST", f"/works/{남과제}/sessions", json={"id": s4, "started_at": "2026-11-16T16:00:00+09:00"})
    모두 += 기록(s4, 남과제)
    끝안남 = 기록(str(uuid.uuid4()), wid)[:-1]                            # 아직 기록 중 (session_end 없음) — 건너뜀
    with open(os.path.join(data, "events-2026-11-16.jsonl"), "w", encoding="utf-8") as f:
        f.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in 모두 + 끝안남)
    결과 = dict(R.다시_보내기(data, S, 최근=3650))
    print("   ", {k[:8]: v for k, v in 결과.items()})
    상태 = lambda sid: S("GET", f"/sessions/{sid}")[1]                     # noqa: E731
    검사("① 봉인만 빠진 기록 → 봉인 · 서버 일치", 결과.get(s1) == "verified" and 상태(s1).get("sealed_at"))
    검사("② 끝 2건 빠진 기록 → 빠진 것만 보내고 봉인 · 일치", 결과.get(s2) == "verified"
         and len(S("GET", f"/sessions/{s2}/events")[1].get("events", [])) == 6)
    검사("③ 서버에 없던 기록 → 세션부터 만들고 봉인", 결과.get(s3) == "verified" and 상태(s3).get("sealed_at"))
    검사("④ 남의 기록은 건너뜀", s4 not in 결과 and not 남S("GET", f"/sessions/{s4}")[1].get("sealed_at"))
    검사("⑤ 서버와 다른 기록 → 봉인은 되지만 '다름' 그대로", 결과.get(s5) == "mismatch" and 상태(s5).get("integrity_ok") is False)
    검사("하트비트 · 기록 중인 세션은 안 보냄", "hb1" not in json.dumps(S("GET", f"/sessions/{s1}/events")[1]) and len(결과) == 4)
    두번째 = R.다시_보내기(data, S, 최근=3650)
    검사("한 번 확인한 기록은 다시 안 물음", 두번째 == [], str(두번째))
    print("  " + "─" * 72 + f"\n  {통과}개 통과, {실패}개 실패\n")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
