"""
app.py — Trace Backend (A)

  python 3-코드/server/app.py          → http://127.0.0.1:5000/api

★ 이 파일은 dev_receiver.py 를 '옮긴' 것이다. 새로 짠 것이 아니다 ★
  · 엔드포인트·요청·응답의 모양을 한 글자도 바꾸지 않았다.
    B 의 수집기와 화면이 그 모양을 보고 만들어졌기 때문이다.
  · 바꾼 것은 저장하는 곳뿐이다:  메모리 dict  →  DB (server/db.py)
  · 해시는 core/chain.py 를 import 해서 쓴다. 여기서 다시 계산하지 않는다.
    두 곳에서 계산하면 영원히 안 맞는다. (계약 9절)

계약: docs/api.md
참고 구현: 3-코드/collector/dev_receiver.py  — 둘은 같은 응답을 내야 한다
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # 3-코드/ 를 경로에 넣어 core 를 쓴다

from core import chain as C          # noqa: E402  ★ 해시는 여기서만
from core.derive import derive       # noqa: E402
from core import llm                 # noqa: E402
import db                            # noqa: E402

KST = timezone(timedelta(hours=9))
LATE_SEC = 5 * 60                    # 이벤트 시각 vs 수신 시각 차이가 이보다 크면 "지연 수신"

app = Flask(__name__)
db.init()


def now():
    return datetime.now(KST)


def iso():
    return now().isoformat(timespec="seconds")


def 세션_가져오기(db세션, sid, create=False):
    s = db세션.get(db.Sess, sid)
    if s is None and create:
        s = db.Sess(id=sid, head=C.GENESIS, chain_len=0, integrity_ok=True, anchor_status="none")
        db세션.add(s)
    return s


def 이벤트들(db세션, sid):
    """저장된 이벤트를 받은 순서대로. derive·chain 이 쓸 원본 그대로 돌려준다."""
    행들 = (db세션.query(db.Event)
            .filter(db.Event.session_id == sid)
            .order_by(db.Event.seq).all())
    return [r.payload for r in 행들]


# ─────────────────────────── 계약 0 · 확인용 ───────────────────────────
@app.get("/api/health")
def health():
    with db.Session() as s:
        return jsonify(ok=True, sessions=s.query(db.Sess).count(), storage="db")


# ─────────────────────────── 계약 3 · 세션 ───────────────────────────
@app.post("/api/works/<work>/sessions")
def create_session(work):
    b = request.get_json(force=True)
    with db.Session() as d:
        s = 세션_가져오기(d, b["id"], create=True)
        existed = s.mode is not None
        장치 = b.get("device") or {}
        s.work_id, s.mode = work, b.get("mode")
        s.device_id = 장치.get("name")
        s.started_at = b.get("started_at")
        d.commit()
    print(f"← session {b['id'][:8]}…  work={work} mode={b.get('mode')}  {'(이미 있음)' if existed else ''}")
    return jsonify(id=b["id"], work_id=work, mode=b.get("mode"),
                   started_at=b.get("started_at")), 200 if existed else 201


@app.post("/api/sessions/<sid>/events")
def events(sid):
    b = request.get_json(force=True)
    받은시각 = now()
    with db.Session() as d:
        s = 세션_가져오기(d, sid, create=True)
        기존 = {r.id for r in d.query(db.Event.id).filter(db.Event.session_id == sid).all()}
        seq = s.chain_len or 0
        저장, 중복, 지연 = 0, 0, 0
        마지막id = None

        for e in b.get("events", []):
            if e["id"] in 기존:                   # 멱등 — 오프라인 큐 재전송은 정상이다
                중복 += 1
                continue
            기존.add(e["id"])

            if e["type"] == "heartbeat":          # 저장 안 함 — 마지막 시각만 (계약 3절)
                s.last_heartbeat_at = e["ts"]
                continue

            s.head = C.next_hash(s.head, e)       # ★ 서버가 같은 함수로 재계산
            s.chain_len = (s.chain_len or 0) + 1
            seq += 1
            if e.get("h") and e["h"] != s.head:
                s.integrity_ok = False

            d.add(db.Event(session_id=sid, id=e["id"], seq=seq, ts=e["ts"], type=e["type"],
                           payload=e, h=e.get("h"), server_h=s.head,
                           received_at=받은시각.isoformat(timespec="seconds")))
            저장 += 1
            마지막id = e["id"]

            try:
                if (받은시각 - datetime.fromisoformat(e["ts"])).total_seconds() > LATE_SEC:
                    지연 += 1
            except ValueError:
                pass

        verified = (b.get("chain_head") == s.head) and bool(s.integrity_ok)
        if b.get("chain_head") and not verified:
            s.integrity_ok = False

        d.add(db.Batch(session_id=sid, chain_head=b.get("chain_head"), chain_len=b.get("chain_len"),
                       n=저장, late=지연, verified=verified,
                       received_at=받은시각.isoformat(timespec="seconds")))
        머리 = s.head
        d.commit()

    print(f"← batch {len(b.get('events', []))}건 (저장 {저장}, 중복 {중복}, 지연 {지연})  "
          f"head {머리[:8]}… {'일치' if verified else '불일치 ⚠'}")
    return jsonify(accepted=저장, duplicates=중복, last_id=마지막id,
                   verified=verified, server_head=머리,
                   received_at=받은시각.isoformat(timespec="seconds"))


@app.post("/api/sessions/<sid>/end")
def end(sid):
    b = request.get_json(force=True)
    with db.Session() as d:
        s = 세션_가져오기(d, sid)
        if not s:
            return jsonify(error="not_found"), 404

        rows, root = C.build(이벤트들(d, sid))       # ★ 전체를 처음부터 다시 계산
        verified = (root == b.get("root")) and bool(s.integrity_ok)
        늦은배치 = d.query(db.Batch).filter(db.Batch.session_id == sid, db.Batch.late > 0).count()

        s.ended_at = b.get("ended_at")
        s.sealed_at = iso()
        s.root, s.verified = root, verified
        s.anchor_status, s.anchor_submitted_at = "pending", iso()
        봉인 = {"ended_at": s.ended_at, "sealed_at": s.sealed_at, "root": root,
                "verified": verified, "late_batches": 늦은배치,
                "anchor": {"status": "pending", "provider": "opentimestamps",
                           "submitted_at": s.anchor_submitted_at}}
        d.commit()

    print(f"← end  chain {len(rows)}건  root {root[:12]}…  "
          f"{'검증됨' if verified else '불일치 ⚠ (client ' + str(b.get('root',''))[:12] + '…)'}  지연 배치 {늦은배치}")
    if not verified:
        return jsonify(error="chain_mismatch", server_root=root,
                       client_root=b.get("root"), **봉인), 409
    return jsonify(id=sid, **봉인)


@app.get("/api/sessions/<sid>")
def get_session(sid):
    with db.Session() as d:
        s = 세션_가져오기(d, sid)
        evs = 이벤트들(d, sid) if s else []
        if not s or not evs:
            return jsonify(error="not_found"), 404
        늦은배치 = d.query(db.Batch).filter(db.Batch.session_id == sid, db.Batch.late > 0).count()
        out = derive(evs)                            # ★ B 의 함수 그대로
        out.update({"work_id": s.work_id, "mode": s.mode, "sealed_at": s.sealed_at,
                    "anchor": s.anchor_status or "none",
                    "integrity_ok": bool(s.integrity_ok), "late_batches": 늦은배치})
    return jsonify(out)


@app.get("/api/sessions/<sid>/events")
def get_events(sid):
    after, limit = request.args.get("after"), int(request.args.get("limit", 500))
    with db.Session() as d:
        if not 세션_가져오기(d, sid):
            return jsonify(error="not_found"), 404
        evs = 이벤트들(d, sid)
    if after:
        idx = next((i for i, e in enumerate(evs) if e["id"] == after), -1)
        evs = evs[idx + 1:]
    page = evs[:limit]
    return jsonify(events=page, next=page[-1]["id"] if len(evs) > limit else None)


# ─────────────────────────── 계약 5 · Learn ───────────────────────────
def _learn만(d, sid):
    """Proof 세션이면 (응답, 코드), Learn 이면 (세션, None)."""
    s = 세션_가져오기(d, sid)
    if not s:
        return jsonify(error="not_found"), 404
    if s.mode != "learn":
        return jsonify(error="proof_session", message="Proof 세션에는 맥락·AI 를 쓰지 않습니다"), 403
    return s, None


@app.post("/api/sessions/<sid>/context")
def context(sid):
    b = request.get_json(force=True)
    with db.Session() as d:
        s, 코드 = _learn만(d, sid)
        if 코드:
            return s, 코드
        n = 0
        for it in b.get("items", []):
            메타 = it.get("meta") or {}
            d.add(db.Context(id=it.get("id") or str(uuid.uuid4()), session_id=sid,
                             ts=it.get("ts"), source=it.get("source"), kind=it.get("kind"),
                             text=(it.get("text") or "")[:500], meta=메타))
            n += 1
        d.commit()
    print(f"← context {n}건  (Learn)")
    return jsonify(accepted=n)


@app.get("/api/sessions/<sid>/report")
def get_report(sid):
    """없으면 이때 만든다 — 학생이 열 때 (계약 5절 · 9/21 결정). 안 보는 세션엔 AI 비용 0."""
    with db.Session() as d:
        s, 코드 = _learn만(d, sid)
        if 코드:
            return s, 코드
        r = d.get(db.Report, sid)
        if r and r.body:
            return jsonify(status="ready", **r.body, generated_at=r.generated_at,
                           provider=r.provider, runs=r.runs)
    return make_report(sid)


@app.post("/api/sessions/<sid>/report")
def make_report(sid):
    with db.Session() as d:
        s, 코드 = _learn만(d, sid)
        if 코드:
            return s, 코드
        r = d.get(db.Report, sid) or db.Report(session_id=sid, runs=0, chat_turns=0)
        if (r.runs or 0) >= 3:
            return jsonify(error="rate_limited", message="리포트는 세션당 3회까지"), 429
        evs = 이벤트들(d, sid)
        맥락 = [{"kind": c.kind, "text": c.text, "source": c.source}
                for c in d.query(db.Context).filter(db.Context.session_id == sid).all()]
        try:
            몸, 공급자 = llm.report(derive(evs), 맥락)     # 학생 이름·계정은 보내지 않는다
        except Exception as e:
            return jsonify(error="ai_failed", message=str(e)), 502
        r.body, r.generated_at, r.provider = 몸, iso(), 공급자
        r.runs = (r.runs or 0) + 1
        d.add(r)
        d.commit()
        결과 = dict(몸)
        생성, 프로바이더, 횟수 = r.generated_at, r.provider, r.runs
    return jsonify(status="ready", **결과, generated_at=생성, provider=프로바이더, runs=횟수)


@app.post("/api/sessions/<sid>/chat")
def chat(sid):
    b = request.get_json(force=True)
    with db.Session() as d:
        s, 코드 = _learn만(d, sid)
        if 코드:
            return s, 코드
        r = d.get(db.Report, sid) or db.Report(session_id=sid, runs=0, chat_turns=0)
        if (r.chat_turns or 0) >= 30:
            return jsonify(error="rate_limited", message="Side Chat 은 세션당 30턴까지"), 429
        try:
            답 = llm.chat(b.get("selection", ""), b.get("question", ""))
        except Exception as e:
            return jsonify(error="ai_failed", message=str(e)), 502
        r.chat_turns = (r.chat_turns or 0) + 1
        d.add(r)
        # 대화도 맥락으로 남는다 — 리포트의 '추가 학습' 에 반영 (계약 5절)
        d.add(db.Context(id=str(uuid.uuid4()), session_id=sid, ts=iso(), source="chat", kind="chat",
                         text=f"Q: {b.get('question','')[:200]} / A: {답[:300]}", meta={}))
        턴 = r.chat_turns
        d.commit()
    return jsonify(answer=답, turns=턴)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    print(f"Trace Backend  http://127.0.0.1:5000/api   저장: {db.DB_URL}")
    print("  계약: docs/api.md   ·  참고 구현과 같은 응답을 내야 합니다")
    app.run(host="127.0.0.1", port=5000, debug=False)
