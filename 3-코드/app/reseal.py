"""
reseal.py — 봉인이 빠진 기록을 서버에 다시 보낸다 (11/16 · v0.1.19)

v0.1.18 까지는 기록 창을 닫자마자 프로그램이 끝나, 서버가 조금 늦으면 마지막 기록 묶음 · 봉인(end)이 안 가고
"서버 확인 전" 으로 남았다 (PC 의 기록은 끝까지 멀쩡함 · 다시 보낼 목록 queue.jsonl 에도 안 남음).
앱이 켜질 때(로그인돼 있으면) · 로그인할 때 한 번, PC 에 끝까지(session_end) 있는 기록 중 서버에서 봉인이 안 된 것을 찾아
**PC 에 기록된 이벤트 그대로** 빠진 것만 보내고 봉인을 보낸다. 기록기가 원래 보냈어야 할 요청과 같다.

  · 내용은 바꾸지 않는다 — 서버가 체인을 처음부터 다시 셈 · 다르면 "서버 기록과 다름" 으로 남는다 (봉인은 됨)
  · 늦게 간 묶음은 서버가 "지연" 으로 표시한다 (숨기지 않음)
  · 남의 과제 · 로그인 안 함(401 · 403) · 지운 기록(410)은 건너뜀 · 한 번 봉인을 확인한 기록은 다시 묻지 않음 (data/sealed-ok.json)
  · 최근 30일 기록만 본다
"""
import glob
import json
import os
import sys
import threading
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import safefile                         # noqa: E402

묶음 = 200                                         # 한 번에 보내는 이벤트 수
최근_일 = 30
_잠금 = threading.Lock()


def 끝난_기록(data_dir, 최근=최근_일):
    """PC 의 events-*.jsonl → 끝까지 기록된 세션 {sid: {"work", "events", "started_at", "ended_at", "root"}} (최근 n일 · 하트비트 뺌)"""
    끝 = (datetime.now() - timedelta(days=최근)).strftime("%Y-%m-%d")
    세션 = {}
    for p in sorted(glob.glob(os.path.join(data_dir, "events-*.jsonl"))):
        if os.path.basename(p)[7:17] < 끝:
            continue
        with open(p, encoding="utf-8") as f:
            for l in f:
                if not l.strip():
                    continue
                try:
                    e = json.loads(l)
                except ValueError:
                    continue
                if e.get("type") == "heartbeat" or not e.get("session_id"):
                    continue
                세션.setdefault(e["session_id"], []).append(e)
    out = {}
    for sid, evs in 세션.items():
        시작 = next((e for e in evs if e.get("type") == "session_start"), None)
        if not 시작 or evs[-1].get("type") != "session_end" or not evs[-1].get("h"):
            continue
        out[sid] = {"work": 시작.get("work_id"), "events": evs, "started_at": 시작.get("ts"),
                    "ended_at": evs[-1].get("ts"), "root": evs[-1]["h"]}
    return out


def 다시_보내기(data_dir, 서버, 최근=최근_일):
    """서버(방법, 경로, json=) → (코드, 답) 는 로그인 토큰을 붙여 부르는 함수 (statement._서버).
    → [(세션 id, "sealed" | "verified" | "mismatch" | 건너뛴 까닭)] 손댄 것만"""
    if not _잠금.acquire(blocking=False):             # 앱 켤 때 · 로그인할 때가 겹치면 하나만
        return []
    try:
        기억경로 = os.path.join(data_dir, "sealed-ok.json")
        기억 = safefile.read_json(기억경로, [])
        기억 = set(기억 if isinstance(기억, list) else [])
        결과 = []
        for sid, s in 끝난_기록(data_dir, 최근).items():
            if sid in 기억:
                continue
            코드, 답 = 서버("GET", f"/sessions/{sid}")
            if 코드 == 200 and 답.get("sealed_at"):
                기억.add(sid)
                continue
            if 코드 in (401, 403, 410) or 코드 >= 500:     # 남의 기록 · 로그인 안 함 · 지움 · 서버가 아픔 → 다음에
                continue
            if 코드 == 404:                                # 서버에 이벤트가 하나도 없음 — 세션부터
                if not s["work"]:
                    continue
                c, _ = 서버("POST", f"/works/{s['work']}/sessions", json={"id": sid, "started_at": s["started_at"]})
                if c not in (200, 201):
                    결과.append((sid, f"session_{c}"))
                    continue
            evs, 실패 = s["events"], None
            for i in range(0, len(evs), 묶음):           # 이미 받은 것은 서버가 건너뜀(멱등) — 빠진 것만 새로 들어감
                조각 = evs[i:i + 묶음]
                c, _ = 서버("POST", f"/sessions/{sid}/events", json={"events": 조각, "chain_head": 조각[-1].get("h"),
                                                                 "chain_len": i + len(조각)})
                if c != 200:
                    실패 = f"events_{c}"
                    break
            if 실패:
                결과.append((sid, 실패))
                continue
            c, 답 = 서버("POST", f"/sessions/{sid}/end", json={"ended_at": s["ended_at"], "chain_len": len(evs), "root": s["root"]})
            if c == 200:
                기억.add(sid)
                결과.append((sid, "verified" if 답.get("verified") else "sealed"))
            elif c == 409:                                # 봉인은 됐지만 서버 기록과 다름 — 다시 해도 같다
                기억.add(sid)
                결과.append((sid, "mismatch"))
            else:
                결과.append((sid, f"end_{c}"))
        safefile.write_json(기억경로, sorted(기억))
        return 결과
    finally:
        _잠금.release()


def 뒤에서(data_dir, 서버, 기다림=3.0):
    """앱 화면을 막지 않게 따로 — 무료 서버가 자다 깨는 동안 기다려도 화면과 상관없다"""
    def 일():
        try:
            for sid, r in 다시_보내기(data_dir, 서버):
                print(f"  · 봉인 다시 보냄 {sid[:8]}… → {r}")
        except Exception as e:                           # noqa: BLE001 — 실패해도 앱은 그대로 (다음에 다시)
            print(f"  · 봉인 다시 보내기 실패 ({type(e).__name__}) — 다음에 다시")
    t = threading.Timer(기다림, 일)
    t.daemon = True
    t.start()
    return t
