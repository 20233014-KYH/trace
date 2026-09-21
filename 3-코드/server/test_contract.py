"""
test_contract.py — 내 서버가 계약(docs/api.md)대로 동작하는지 확인한다.

  python 3-코드/server/app.py            # 다른 창에서 서버를 먼저 켜고
  python 3-코드/server/test_contract.py  # 이걸 돌린다

  python 3-코드/server/test_contract.py --ref
      → 팀원분 참고 서버(dev_receiver.py)에 대고 돌린다. 둘의 응답이 같아야 한다.

검사 6개:
  1 health            서버가 살아 있나
  2 세션 만들기        201, 다시 보내면 200 (멱등)
  3 batch 정상         verified=true · server_head 가 PC 계산과 같은가
  4 batch 중복         같은 이벤트를 다시 보내면 duplicates 로 세고 저장 안 하나
  5 batch 조작         이벤트를 한 글자 고쳐 보내면 verified=false 로 잡나   ★ 핵심
  6 봉인·조회          root 일치 · session.json 구조가 나오나
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import chain as C          # noqa: E402

BASE = "http://127.0.0.1:5000/api"
FIX = os.path.join(os.path.dirname(HERE), "tests", "fixtures", "events_basic.jsonl")


def 호출(경로, 몸=None):
    자료 = json.dumps(몸).encode() if 몸 is not None else None
    요청 = urllib.request.Request(BASE + 경로, data=자료,
                                  method="POST" if 몸 is not None else "GET",
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(요청, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except urllib.error.URLError as e:
        print(f"\n  서버에 연결하지 못했습니다 ({e.reason}).")
        print("  다른 창에서 먼저 켜 주세요:  python 3-코드/server/app.py\n")
        sys.exit(1)


def 체인머리(이벤트들):
    prev = C.GENESIS
    for e in 이벤트들:
        if C.in_chain(e):
            prev = C.next_hash(prev, e)
    return prev


통과, 실패 = 0, 0


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    if 조건:
        통과 += 1
        print(f"  ✅ {이름:<22} {설명}")
    else:
        실패 += 1
        print(f"  ❌ {이름:<22} {설명}")


def main():
    이벤트 = [json.loads(l) for l in open(FIX, encoding="utf-8") if l.strip()]
    import uuid
    sid = "test-" + uuid.uuid4().hex[:12]

    print()
    print(f"  계약 준수 검사 — {BASE}")
    print("  " + "─" * 64)

    코드, 답 = 호출("/health")
    검사("1 health", 코드 == 200 and 답.get("ok"), f"세션 {답.get('sessions')}개 · 저장 {답.get('storage', '?')}")

    몸 = {"id": sid, "mode": "proof",
          "device": {"name": "테스트", "os": "mac", "collector_version": "0.4"},
          "started_at": 이벤트[0]["ts"]}
    코드1, _ = 호출("/works/W-TEST/sessions", 몸)
    코드2, _ = 호출("/works/W-TEST/sessions", 몸)
    검사("2 세션 만들기 (멱등)", 코드1 == 201 and 코드2 == 200, f"처음 {코드1} · 다시 {코드2}")

    절반 = len(이벤트) // 2
    앞, 뒤 = 이벤트[:절반], 이벤트[절반:]

    코드, 답 = 호출(f"/sessions/{sid}/events",
                    {"events": 앞, "chain_head": 체인머리(앞), "chain_len": len(앞)})
    검사("3 batch 정상", 답.get("verified") is True and 답.get("server_head") == 체인머리(앞),
         f"저장 {답.get('accepted')}건 · head {(답.get('server_head') or '')[:12]}…")

    코드, 답 = 호출(f"/sessions/{sid}/events",
                    {"events": 앞, "chain_head": 체인머리(앞), "chain_len": len(앞)})
    # ★ heartbeat 는 DB 에 저장하지 않으므로(계약 3절) 중복으로도 세어지지 않는다.
    #   그래서 기댓값은 len(앞) 이 아니라 'heartbeat 를 뺀 수' 다.
    #   메모리로 들고 있는 참고 서버는 heartbeat 까지 세므로 이 숫자 하나만 다르다.
    저장대상 = len([e for e in 앞 if e["type"] != "heartbeat"])
    검사("4 batch 중복 무시", 답.get("accepted") == 0 and 답.get("duplicates") == 저장대상,
         f"저장 {답.get('accepted')} · 중복 {답.get('duplicates')} (heartbeat 제외 {저장대상})")

    # ★ 조작 — 뒤쪽 이벤트 하나를 고쳐서 보낸다. chain_head 는 원본 기준으로 보낸다.
    고침 = [dict(e) for e in 뒤]
    바꾼곳 = None
    for e in 고침:
        if e["type"] == "keys":
            바꾼곳 = f"{e['id']} 의 입력 {e['count']} → 999"
            e["count"] = 999
            break
    코드, 답 = 호출(f"/sessions/{sid}/events",
                    {"events": 고침, "chain_head": 체인머리(이벤트), "chain_len": len(이벤트)})
    검사("5 batch 조작 탐지", 답.get("verified") is False, f"{바꾼곳} → verified={답.get('verified')}")

    # 조작된 세션은 봉인도 실패해야 한다
    코드, 답 = 호출(f"/sessions/{sid}/end",
                    {"ended_at": 이벤트[-1]["ts"], "chain_len": len(이벤트), "root": 체인머리(이벤트)})
    검사("6 봉인 (조작 세션)", 코드 == 409 and 답.get("verified") is False,
         f"HTTP {코드} · {답.get('error')}")

    # 깨끗한 세션으로 봉인·조회까지
    sid2 = "test-" + uuid.uuid4().hex[:12]
    호출("/works/W-TEST/sessions", {**몸, "id": sid2})
    호출(f"/sessions/{sid2}/events",
         {"events": 이벤트, "chain_head": 체인머리(이벤트), "chain_len": len(이벤트)})
    코드, 답 = 호출(f"/sessions/{sid2}/end",
                    {"ended_at": 이벤트[-1]["ts"], "chain_len": len(이벤트), "root": 체인머리(이벤트)})
    검사("7 봉인 (정상)", 코드 == 200 and 답.get("verified") is True,
         f"root {(답.get('root') or '')[:16]}…")

    코드, 답 = 호출(f"/sessions/{sid2}")
    필요 = ["segments", "typed", "deleted", "pastes", "undos", "chain", "root", "stats"]
    빠짐 = [k for k in 필요 if k not in 답]
    검사("8 조회 (session.json)", 코드 == 200 and not 빠짐,
         f"타자 {답.get('stats', {}).get('typed')}자 · 붙임 {len(답.get('pastes', []))}건"
         + (f" · 빠진 키 {빠짐}" if 빠짐 else ""))

    print("  " + "─" * 64)
    print(f"  {통과}개 통과, {실패}개 실패")
    print()
    return 1 if 실패 else 0


if __name__ == "__main__":
    if "--ref" in sys.argv:
        print("  (참고 서버 dev_receiver.py 에 대고 돌립니다)")
    sys.exit(main())
