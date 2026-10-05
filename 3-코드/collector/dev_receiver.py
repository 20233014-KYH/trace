"""
dev_receiver.py — API 계약 ③ 을 그대로 구현한 참고 서버 (Flask · 메모리 + jsonl)

A 가 진짜 Backend 를 만들 때 "서버가 해야 할 일" 의 기준. DB 대신 dict, 인증 없음, 앵커는 흉내.
  python dev_receiver.py            # http://127.0.0.1:5000/api

하는 일 (계약 3절):
  POST /api/works/<w>/sessions            세션 등록 (멱등)
  POST /api/sessions/<id>/events          batch 수신 → core/chain.py 로 체인 재계산 → chain_head 대조 → received_at 기록 → 지연 판정
  POST /api/sessions/<id>/end             루트 재계산 · 대조 · 봉인 · (흉내) 앵커 pending
  GET  /api/sessions/<id>                 core/derive.py 로 session.json 구조 반환 (화면용)
  POST /api/sessions/<id>/context         AI 대화 기록 (9/28: 모든 세션 · 항목 64KB · 요청 1MB 넘으면 413)
  GET  /api/sessions/<id>/context         AI 대화 기록 읽기
  GET  /api/sessions/<id>/events          원본 이벤트
  GET  /api/health
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import chain as C          # noqa: E402
from core.derive import derive       # noqa: E402

KST = timezone(timedelta(hours=9))
LATE_SEC = 5 * 60                    # 이벤트 시각 vs 수신 시각 차이가 이보다 크면 "지연 수신"
DATA = os.path.normpath(os.path.join(HERE, "../data/received"))
os.makedirs(DATA, exist_ok=True)

app = Flask(__name__)
SESS: dict[str, dict] = {}           # id → {meta, events[], ids set, head, chain_len, batches[], integrity_ok}


def now():
    return datetime.now(KST)


def sess(sid, create=False):
    s = SESS.get(sid)
    if s is None and create:
        s = SESS[sid] = {"meta": {"id": sid}, "events": [], "ids": set(), "head": C.GENESIS, "chain_len": 0,
                         "batches": [], "integrity_ok": True, "sealed": None, "last_heartbeat_at": None}
    return s


def persist(sid, evs):
    with open(os.path.join(DATA, f"{sid}.jsonl"), "a", encoding="utf-8") as f:
        for e in evs:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


@app.get("/api/health")
def health():
    return jsonify(ok=True, sessions=len(SESS))


@app.post("/api/works/<work>/sessions")
def create_session(work):
    b = request.get_json(force=True)
    s = sess(b["id"], create=True)
    existed = "work_id" in s["meta"]
    s["meta"].update({"work_id": work, "device": b.get("device"), "started_at": b.get("started_at")})
    print(f"← session {b['id'][:8]}…  work={work}  {'(이미 있음)' if existed else ''}")
    return jsonify(id=b["id"], work_id=work, started_at=b.get("started_at")), 200 if existed else 201


@app.post("/api/sessions/<sid>/events")
def events(sid):
    b = request.get_json(force=True)
    s = sess(sid, create=True)
    received_at = now()
    accepted, dup, late = [], 0, 0
    for e in b.get("events", []):
        if e["id"] in s["ids"]:
            dup += 1
            continue
        s["ids"].add(e["id"])
        if e["type"] == "heartbeat":                       # 저장 안 함 — 마지막 시각만
            s["last_heartbeat_at"] = e["ts"]
            continue
        s["events"].append(e)
        accepted.append(e)
        # 서버가 같은 함수로 재계산 (클라이언트의 'h' 는 참고만)
        s["head"] = C.next_hash(s["head"], e)
        s["chain_len"] += 1
        if e.get("h") and e["h"] != s["head"]:
            s["integrity_ok"] = False
        try:
            if (received_at - datetime.fromisoformat(e["ts"])).total_seconds() > LATE_SEC:
                late += 1
        except ValueError:
            pass
    persist(sid, accepted)
    verified = (b.get("chain_head") == s["head"]) and s["integrity_ok"]
    if b.get("chain_head") and not verified:
        s["integrity_ok"] = False
    s["batches"].append({"received_at": received_at.isoformat(timespec="seconds"), "n": len(accepted), "late": late, "verified": verified})
    print(f"← batch {len(b.get('events', []))}건 (저장 {len(accepted)}, 중복 {dup}, 지연 {late})  "
          f"head {s['head'][:8]}… {'일치' if verified else '불일치 ⚠'}")
    return jsonify(accepted=len(accepted), duplicates=dup, last_id=accepted[-1]["id"] if accepted else None,
                   verified=verified, server_head=s["head"], received_at=received_at.isoformat(timespec="seconds"))


@app.post("/api/sessions/<sid>/end")
def end(sid):
    b = request.get_json(force=True)
    s = sess(sid)
    if not s:
        return jsonify(error="not_found"), 404
    rows, root = C.build(s["events"])
    verified = (root == b.get("root")) and s["integrity_ok"]
    late_batches = sum(1 for x in s["batches"] if x["late"])
    s["sealed"] = {"ended_at": b.get("ended_at"), "sealed_at": now().isoformat(timespec="seconds"), "root": root,
                   "verified": verified, "late_batches": late_batches,
                   "anchor": {"status": "pending", "provider": "opentimestamps", "submitted_at": now().isoformat(timespec="seconds")}}
    print(f"← end  chain {len(rows)}건  root {root[:12]}…  {'검증됨' if verified else '불일치 ⚠ (client ' + str(b.get('root', ''))[:12] + '…)'}  지연 배치 {late_batches}")
    if not verified:
        return jsonify(error="chain_mismatch", server_root=root, client_root=b.get("root"), **s["sealed"]), 409
    return jsonify(id=sid, **s["sealed"])


@app.post("/api/sessions/<sid>/context")
def context(sid):
    s = sess(sid)
    if not s:
        return jsonify(error="not_found"), 404
    if (request.content_length or 0) > 1024 * 1024:
        return jsonify(error="too_large", message="한 요청은 1MB 까지입니다"), 413
    items = request.get_json(force=True).get("items", [])
    if any(len((it.get("text") or "").encode("utf-8")) > 64 * 1024 for it in items):
        return jsonify(error="too_large", message="한 항목은 64KB 까지입니다"), 413
    s.setdefault("context", []).extend(items)
    with open(os.path.join(DATA, f"{sid}.context.jsonl"), "a", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"← context {len(items)}건  {', '.join(i.get('kind', '?') for i in items[:5])}")
    return jsonify(accepted=len(items))


@app.get("/api/sessions/<sid>/context")
def get_context(sid):
    """실제 서버(server/app.py)에는 9/21 에 들어갔는데 여기엔 없었다 → 계약 4절대로 맞춤 (10/3)"""
    s = sess(sid)
    if not s:
        return jsonify(error="not_found"), 404
    return jsonify(items=sorted(s.get("context", []), key=lambda i: i.get("ts") or ""))


@app.get("/api/sessions/<sid>")
def get_session(sid):
    s = sess(sid)
    if not s or not s["events"]:
        return jsonify(error="not_found"), 404
    out = derive(s["events"])
    out.update({"work_id": s["meta"].get("work_id"),
                "sealed_at": (s["sealed"] or {}).get("sealed_at"),
                "anchor": (s["sealed"] or {}).get("anchor", {}).get("status", "none"),
                "integrity_ok": s["integrity_ok"], "late_batches": sum(1 for x in s["batches"] if x["late"])})
    return jsonify(out)


@app.get("/api/sessions/<sid>/events")
def get_events(sid):
    s = sess(sid)
    if not s:
        return jsonify(error="not_found"), 404
    after, limit = request.args.get("after"), int(request.args.get("limit", 500))
    evs = s["events"]
    if after:
        idx = next((i for i, e in enumerate(evs) if e["id"] == after), -1)
        evs = evs[idx + 1:]
    page = evs[:limit]
    return jsonify(events=page, next=page[-1]["id"] if len(evs) > limit else None)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    print("Trace dev server  http://127.0.0.1:5000/api  (계약 ③ 참고 구현 · 메모리 저장)")
    app.run(host="127.0.0.1", port=5000, debug=False)
