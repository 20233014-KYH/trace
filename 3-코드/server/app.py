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
import functools
import os
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # 3-코드/ 를 경로에 넣어 core 를 쓴다

from core import chain as C          # noqa: E402  ★ 해시는 여기서만
from core.derive import derive       # noqa: E402
from core.texthash import sha256_text  # noqa: E402  ★ 원문 해시도 여기서만 (내역서 검증)
from core.summary import work_summary  # noqa: E402  요약 숫자 — 체인 이벤트로 센다
import db                            # noqa: E402

KST = timezone(timedelta(hours=9))
LATE_SEC = 5 * 60                    # 이벤트 시각 vs 수신 시각 차이가 이보다 크면 "지연 수신"

app = Flask(__name__)
# Render 는 앞단(프록시)이 https 를 받고 우리에겐 http 로 넘긴다. 이걸 안 하면 교수용 링크가 http:// 로 만들어진다
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
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


# ─────────────────────────── 인증 (계약 1절) ───────────────────────────
#
# ★ 지금은 '켜져 있지만 강제하지 않는다' ★
#   B 의 수집기는 아직 토큰을 안 보낸다. 여기서 401 을 던지기 시작하면
#   10/7 관통 테스트가 그대로 깨진다.
#   그래서 기본값은 끔. 수집기가 토큰을 보내게 되면 그때 켠다.
#
#       TRACE_REQUIRE_AUTH=1 python server/app.py
#
#   토큰이 오면 꺼져 있어도 확인하고 g.user 에 담는다. 그래야 켜기 전에
#   "제대로 붙었나"를 미리 볼 수 있다.

인증_강제 = os.environ.get("TRACE_REQUIRE_AUTH", "0") == "1"


def 토큰_사용자(d):
    """Authorization: Bearer <token> 을 보고 사용자를 찾는다. 없으면 None."""
    머리 = request.headers.get("Authorization", "")
    if not 머리.startswith("Bearer "):
        return None
    t = d.get(db.Token, 머리[7:].strip())
    if not t:
        return None
    t.last_used_at = now().replace(tzinfo=None)
    return d.get(db.User, t.user_id)


def 로그인_필요(f):
    """★ 사람 화면용 주소(과제 목록·과제·/me)는 언제나 로그인이 필요하다 (10/7 · 배포 전)

    전엔 TRACE_REQUIRE_AUTH=1 일 때만 막아서, 로그인 없이도 과제 목록 → 과제(이름 추측 가능) → 세션 id
    → 기록(창 이름 포함)이 줄줄이 읽혔다. 인터넷에 올리면 누구나 학생 기록을 보게 된다.
    기록기가 쓰는 주소(세션·이벤트·봉인·맥락)는 여기 안 걸린다 — 기록기가 아직 토큰을 안 보내서.
    그쪽은 TRACE_REQUIRE_AUTH 로 나중에 막는다."""
    @functools.wraps(f)
    def 감싼것(*a, **kw):
        with db.Session() as d:
            u = 토큰_사용자(d)
            d.commit()
            g.user_id = u.id if u else None
            g.user_name = u.name if u else None
        if not g.user_id:
            return jsonify(error="unauthorized", message="로그인이 필요합니다"), 401
        return f(*a, **kw)
    return 감싼것


@app.post("/api/auth/signup")
def signup():
    """★ 계약에 없던 것을 더했다 (9/21, A).
    로그인만 있으면 계정을 만들 방법이 없다. B 에게 알렸다."""
    b = request.get_json(force=True)
    이메일 = (b.get("email") or "").strip().lower()
    비번 = b.get("password") or ""
    if not 이메일 or len(비번) < 8:
        return jsonify(error="bad_request",
                       message="이메일과 8자 이상 비밀번호가 필요합니다"), 400
    with db.Session() as d:
        if d.query(db.User).filter(db.User.email == 이메일).first():
            return jsonify(error="conflict", message="이미 있는 이메일입니다"), 409
        u = db.User(id=str(uuid.uuid4()), email=이메일,
                    password_hash=generate_password_hash(비번),   # ★ 원문은 저장하지 않는다
                    name=b.get("name") or 이메일.split("@")[0],
                    created_at=now().replace(tzinfo=None))
        d.add(u)
        d.commit()
        결과 = {"id": u.id, "name": u.name}
    print(f"← signup {이메일}")
    return jsonify(id=결과["id"], name=결과["name"]), 201


@app.post("/api/auth/login")
def login():
    b = request.get_json(force=True)
    이메일 = (b.get("email") or "").strip().lower()
    with db.Session() as d:
        u = d.query(db.User).filter(db.User.email == 이메일).first()
        # ★ "이메일이 없다" 와 "비번이 틀렸다" 를 구분해서 알려주지 않는다.
        #   구분해 주면 어떤 이메일이 가입되어 있는지 알아낼 수 있다.
        if not u or not check_password_hash(u.password_hash, b.get("password") or ""):
            return jsonify(error="unauthorized", message="이메일 또는 비밀번호가 맞지 않습니다"), 401
        t = db.Token(token=secrets.token_urlsafe(32), user_id=u.id,
                     device=(b.get("device") or "")[:100],
                     created_at=now().replace(tzinfo=None))
        d.add(t)
        d.commit()
        답 = {"token": t.token, "user": {"id": u.id, "name": u.name}}
    print(f"← login {이메일}")
    return jsonify(답)


@app.post("/api/auth/logout")
def logout():
    """이 기기 연결 끊기. 토큰 한 줄을 지운다."""
    머리 = request.headers.get("Authorization", "")
    if not 머리.startswith("Bearer "):
        return jsonify(error="bad_request", message="토큰이 없습니다"), 400
    with db.Session() as d:
        t = d.get(db.Token, 머리[7:].strip())
        if t:
            d.delete(t)
            d.commit()
    return jsonify(ok=True)


@app.get("/api/me")
@로그인_필요
def me():
    if not g.user_id:
        return jsonify(error="unauthorized", message="로그인이 필요합니다"), 401
    with db.Session() as d:
        works = d.query(db.Work).filter(db.Work.user_id == g.user_id).all()
        답 = {"id": g.user_id, "name": g.user_name,
              "works": [{"id": w.id, "title": w.title, "ai_scope": w.ai_scope} for w in works]}
    return jsonify(답)


# ─────────────────────────── Work (계약 2절) ───────────────────────────
@app.post("/api/works")
@로그인_필요
def create_work():
    b = request.get_json(force=True)
    범위 = b.get("ai_scope")                      # 교수가 허용한 범위 메모 (선택). 서버는 이걸로 판단하지 않는다
    if 범위 is not None and not isinstance(범위, str):
        return jsonify(error="bad_request", message="ai_scope 는 글자(메모)여야 합니다"), 400
    with db.Session() as d:
        w = db.Work(id=b.get("id") or str(uuid.uuid4()), user_id=g.user_id,
                    title=b.get("title") or "제목 없음", ai_scope=범위,
                    created_at=now().replace(tzinfo=None))
        d.add(w)
        d.commit()
        답 = {"id": w.id, "title": w.title, "ai_scope": w.ai_scope,
              "created_at": w.created_at.isoformat(timespec="seconds")}
    print(f"← work 만듦 {답['id'][:8]}…  {답['title']}")
    return jsonify(답), 201


@app.get("/api/works")
@로그인_필요
def list_works():
    with db.Session() as d:
        q = d.query(db.Work)
        if g.user_id:
            q = q.filter(db.Work.user_id == g.user_id)
        목록 = []
        for w in q.all():
            세션들 = d.query(db.Sess).filter(db.Sess.work_id == w.id).all()
            마지막 = max((s.started_at for s in 세션들 if s.started_at), default=None)
            목록.append({"id": w.id, "title": w.title, "ai_scope": w.ai_scope,
                         "sessions": len(세션들), "last_at": 마지막})
    return jsonify(목록)


@app.get("/api/works/<wid>")
@로그인_필요
def get_work(wid):
    with db.Session() as d:
        w = d.get(db.Work, wid)
        if not w or w.user_id != g.user_id:        # 주인 없는 과제(기록기가 로그인 없이 만든 것)도 남은 못 본다 (10/8)
            return jsonify(error="not_found"), 404
        세션들 = []
        for s in d.query(db.Sess).filter(db.Sess.work_id == wid).all():
            n = d.query(db.Event).filter(db.Event.session_id == s.id).count()
            세션들.append({"id": s.id, "start": s.started_at, "end": s.ended_at,
                           "dur": None, "events": n, "sealed": bool(s.sealed_at)})
        답 = {"id": w.id, "title": w.title, "ai_scope": w.ai_scope, "sessions": 세션들}
    return jsonify(답)


@app.patch("/api/works/<wid>")
@로그인_필요
def update_work(wid):
    """제목·허용 범위 메모 고치기 — 내역서를 내기 직전에 고칠 수 있어야 한다 (계약 2절)."""
    b = request.get_json(force=True)
    if "ai_scope" in b and b["ai_scope"] is not None and not isinstance(b["ai_scope"], str):
        return jsonify(error="bad_request", message="ai_scope 는 글자(메모)여야 합니다"), 400
    with db.Session() as d:
        w = d.get(db.Work, wid)
        if not w or w.user_id != g.user_id:        # 주인 없는 과제(기록기가 로그인 없이 만든 것)도 남은 못 본다 (10/8)
            return jsonify(error="not_found"), 404
        if "title" in b:
            w.title = b["title"] or "제목 없음"
        if "ai_scope" in b:
            w.ai_scope = b["ai_scope"]
        d.commit()
        답 = {"id": w.id, "title": w.title, "ai_scope": w.ai_scope}
    return jsonify(답)


# ─────────────────────────── 계약 0 · 확인용 ───────────────────────────
@app.get("/api/health")
def health():
    with db.Session() as s:
        return jsonify(ok=True, sessions=s.query(db.Sess).count(), storage="db",
                       auth="required" if 인증_강제 else "optional")


# ─────────────────────────── 계약 3 · 세션 ───────────────────────────
@app.post("/api/works/<work>/sessions")
def create_session(work):
    b = request.get_json(force=True)
    with db.Session() as d:
        if d.get(db.Work, work) is None:
            # ★ 기록기는 과제를 따로 만들지 않고 config 의 work_id 로 바로 세션을 보낸다.
            #   SQLite 는 없는 과제를 가리키는 세션도 받아 주지만, PostgreSQL(Supabase) 은 외래키로 거절한다 (500).
            #   → 없으면 여기서 만들어 둔다. 토큰이 왔으면 그 사람 과제로. (10/4 Supabase 로 옮기다 발견)
            주인 = 토큰_사용자(d)
            d.add(db.Work(id=work, user_id=주인.id if 주인 else None, title=work,
                          created_at=now().replace(tzinfo=None)))
            d.flush()
        s = 세션_가져오기(d, b["id"], create=True)
        existed = s.work_id is not None              # 전에는 mode 로 판단했다. 이제 mode 가 없으니 work_id 로
        장치 = b.get("device") or {}
        s.work_id = work                             # 요청에 mode 가 와도 무시한다 (기록기가 아직 보낼 수 있음)
        s.device_id = 장치.get("name")
        s.started_at = b.get("started_at")
        d.commit()
    print(f"← session {b['id'][:8]}…  work={work}  {'(이미 있음)' if existed else ''}")
    return jsonify(id=b["id"], work_id=work,
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
        out.update({"work_id": s.work_id, "sealed_at": s.sealed_at,
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


# ─────────────────────────── 계약 4 · AI 대화 기록 ───────────────────────────
# 9/28 개정: 모드가 없어져 모든 세션에서 받는다 (전에는 Learn 세션만, Proof 면 403).
# Learn 의 리포트(/report)·Side Chat(/chat) 은 기능째 없어졌다.
항목_최대 = 64 * 1024          # 한 항목 글자 64KB (계약 4절)
요청_최대 = 1024 * 1024        # 한 요청 1MB


@app.post("/api/sessions/<sid>/context")
def context(sid):
    if (request.content_length or 0) > 요청_최대:
        return jsonify(error="too_large", message="한 요청은 1MB 까지입니다"), 413
    b = request.get_json(force=True)
    항목들 = b.get("items", [])
    for it in 항목들:
        if len((it.get("text") or "").encode("utf-8")) > 항목_최대:
            return jsonify(error="too_large", message=f"한 항목은 64KB 까지입니다 ({it.get('kind')})"), 413
    with db.Session() as d:
        if not 세션_가져오기(d, sid):
            return jsonify(error="not_found"), 404
        for it in 항목들:
            d.add(db.Context(id=it.get("id") or str(uuid.uuid4()), session_id=sid,
                             ts=it.get("ts"), source=it.get("source"), kind=it.get("kind"),
                             text=it.get("text") or "", meta=it.get("meta") or {}))   # 500자로 자르던 것 없앰
        d.commit()
    print(f"← context {len(항목들)}건")
    return jsonify(accepted=len(항목들))


@app.get("/api/sessions/<sid>/context")
def get_context(sid):
    with db.Session() as d:
        if not 세션_가져오기(d, sid):
            return jsonify(error="not_found"), 404
        항목 = [{"id": c.id, "ts": c.ts, "source": c.source, "kind": c.kind,
                 "text": c.text, "meta": c.meta or {}}
                for c in (d.query(db.Context)
                          .filter(db.Context.session_id == sid)
                          .order_by(db.Context.ts).all())]
    return jsonify(items=항목)


# ─────────────────────────── 10 · AI 활용 내역서 ───────────────────────────
#
# ★ "원문은 늦게 와도, 기록 당시 그대로인지 확인된다" (docs/api.md 10-1) ★
#   기록하는 동안 서버엔 해시만 왔다 (ai_msg.hash). 학생이 "내역서 만들기"를 누르면 고른 원문이 처음 온다.
#   서버는 sha256_text(원문) 을 체인 이벤트의 hash 와 비교한다. 같으면 그때 그 글, 다르면 나중에 바꾼 글.
#   다른 것도 버리지 않고 저장해 "조작됨"으로 보여 준다 — 숨기면 내역서를 믿을 이유가 없어진다.
#
#   도구·역할·시각은 학생이 보낸 값을 쓰지 않고 체인 이벤트의 값을 쓴다 (PC 가 보낸 숫자를 믿지 않음).

내역서_최대 = 5 * 1024 * 1024       # 한 요청 5MB
원문_최대 = 256 * 1024              # 원문 한 개 256KB (긴 AI 답)
공유_기본일, 공유_최대일 = 14, 90


def 내_과제(d, wid):
    """로그인한 사람의 과제만. 주인이 없는 과제(기록기가 로그인 없이 만든 것)도 거절한다 —
    과제 이름(W-1007 같은)은 추측할 수 있어서, 누구나 남의 기록으로 내역서를 만들 수 있게 되므로."""
    w = d.get(db.Work, wid)
    if not w or w.user_id != g.user_id:
        return None
    return w


def _쌍(x, 이름):
    """{session_id, event_id} 를 꺼낸다. 이벤트 id 는 세션 안에서만 고유하다 (events 기본키와 같은 이유)."""
    if not isinstance(x, dict) or not x.get("session_id") or not x.get("event_id"):
        raise ValueError(f"{이름} 마다 session_id 와 event_id 가 필요합니다")
    return str(x["session_id"]), str(x["event_id"])


def _과제_요약(d, wid):
    """과제의 세션 전부를 체인 이벤트로 센다 (core/summary.py). PC 가 보낸 숫자는 쓰지 않는다."""
    세션들 = d.query(db.Sess).filter(db.Sess.work_id == wid).all()
    return work_summary([({"id": s.id, "sealed": bool(s.sealed_at),
                           "verified": bool(s.verified) and bool(s.integrity_ok)}, 이벤트들(d, s.id))
                         for s in 세션들])


@app.get("/api/works/<wid>/summary")
@로그인_필요
def summary(wid):
    """내역서 맨 위 숫자. 작업 시간 · 입력 · 붙여넣기(출처 기록 없음 포함) · AI 질문·답 · 연결. 비율·점수는 없다."""
    with db.Session() as d:
        if not 내_과제(d, wid):
            return jsonify(error="not_found"), 404
        답 = _과제_요약(d, wid)
    return jsonify(work_id=wid, **답)


@app.post("/api/works/<wid>/statements")
@로그인_필요
def create_statement(wid):
    if (request.content_length or 0) > 내역서_최대:
        return jsonify(error="too_large", message="한 요청은 5MB 까지입니다"), 413
    b = request.get_json(force=True, silent=True)
    if not isinstance(b, dict):
        return jsonify(error="bad_request", message="JSON 이 필요합니다"), 400
    메시지들, 연결들, 가림들 = b.get("messages") or [], b.get("links") or [], b.get("redactions") or []
    if not all(isinstance(v, list) for v in (메시지들, 연결들, 가림들)):
        return jsonify(error="bad_request", message="messages · links · redactions 는 목록이어야 합니다"), 400
    for 이름 in ("ai_scope", "sentence"):
        if b.get(이름) is not None and not isinstance(b[이름], str):
            return jsonify(error="bad_request", message=f"{이름} 는 글자여야 합니다"), 400
    try:
        가림쌍 = {_쌍(r, "redactions") for r in 가림들}
        for m in 메시지들:
            _쌍(m, "messages")
            if not isinstance(m.get("text"), str) or not m["text"]:
                raise ValueError("messages 마다 text(원문)가 필요합니다")
            if len(m["text"].encode("utf-8", "surrogatepass")) > 원문_최대:
                return jsonify(error="too_large", message="원문 한 개는 256KB 까지입니다"), 413
            if _쌍(m, "messages") in 가림쌍:
                raise ValueError("가린 이벤트의 원문을 함께 보낼 수 없습니다")
        for l in 연결들:
            if not isinstance(l, dict) or l.get("decision") not in ("confirmed", "rejected"):
                raise ValueError("links 마다 decision 이 confirmed 또는 rejected 여야 합니다")
            if not l.get("answer_hash") or not l.get("result_hash"):
                raise ValueError("links 마다 answer_hash 와 result_hash 가 필요합니다")
    except ValueError as e:
        return jsonify(error="bad_request", message=str(e)), 400

    with db.Session() as d:
        w = 내_과제(d, wid)
        if not w:
            return jsonify(error="not_found"), 404
        세션들 = {s.id: s for s in d.query(db.Sess).filter(db.Sess.work_id == wid).all()}

        def 이벤트(sid, eid):
            return d.get(db.Event, (sid, eid)) if sid in 세션들 else None

        문제들, 쓰인세션 = [], set()
        st = db.Statement(id=str(uuid.uuid4()), work_id=wid, user_id=g.user_id,
                          created_at=now().isoformat(timespec="microseconds"),   # 같은 초에 두 번 만들어도 순서가 갈리게
                          ai_scope=b["ai_scope"] if "ai_scope" in b else w.ai_scope, sentence=b.get("sentence"))
        d.add(st)
        d.flush()

        # ① 원문 — 하나씩 체인과 맞춰 본다
        원문해시 = {}                                         # 서버가 계산한 해시 → role (연결 확인용, 맞은 것만)
        for m in 메시지들:
            sid, eid = _쌍(m, "messages")
            해시 = sha256_text(m["text"])
            e = 이벤트(sid, eid)
            p = e.payload if e else {}
            if sid not in 세션들:
                왜 = "not_in_work"                           # 이 과제의 세션이 아니다
            elif not e or e.type != "ai_msg":
                왜 = "not_in_chain"                          # 체인에 그런 AI 질문·답 이벤트가 없다
            elif p.get("hash") != 해시:
                왜 = "hash_mismatch"                         # 기록 당시 글과 다르다
            else:
                왜 = None
            if 왜:
                문제들.append({"session_id": sid, "event_id": eid, "why": 왜})
            else:
                원문해시[해시] = p.get("role")
                쓰인세션.add(sid)
            d.add(db.Message(statement_id=st.id, session_id=sid, event_id=eid,
                             tool=p.get("tool") if e else m.get("tool"), role=p.get("role") if e else m.get("role"),
                             ts=e.ts if e else m.get("ts"), text=m["text"], hash=해시,
                             history=bool(p.get("history")), match=왜 is None))

        # ② 연결 — "맞다"는 위에서 확인된 답을 가리켜야 한다. "아니다"는 원문을 받지 않는다
        for l in 연결들:
            맞다 = l["decision"] == "confirmed"
            결과 = l.get("result_text") if 맞다 and isinstance(l.get("result_text"), str) else None
            if 맞다:
                if 원문해시.get(l["answer_hash"]) != "answer":
                    문제들.append({"answer_hash": l["answer_hash"], "why": "answer_not_verified"})
                if l.get("question_hash") and 원문해시.get(l["question_hash"]) != "question":
                    문제들.append({"question_hash": l["question_hash"], "why": "question_not_verified"})
                if 결과 is not None and sha256_text(결과) != l["result_hash"]:
                    문제들.append({"result_hash": l["result_hash"], "why": "result_hash_mismatch"})
            d.add(db.Link(statement_id=st.id, answer_hash=l["answer_hash"],
                          question_hash=l.get("question_hash") if 맞다 else None,
                          result_hash=l["result_hash"], result_text=결과, location=l.get("location"),
                          kind=l.get("kind"), origin=l.get("origin"), decision=l["decision"],
                          decision_event_id=l.get("decision_event_id")))

        # ③ 가림 — 어느 이벤트인지만. 이 과제의 체인에 있어야 한다
        for sid, eid in sorted(가림쌍):
            if not 이벤트(sid, eid):
                문제들.append({"session_id": sid, "event_id": eid, "why": "redaction_not_in_chain"})
            d.add(db.Redaction(statement_id=st.id, session_id=sid, event_id=eid))

        # ④ 원문이 나온 세션은 봉인·검증돼 있어야 한다 (아직 기록 중이거나 체인이 어긋난 세션)
        세션상태 = []
        for sid in sorted(쓰인세션):
            s = 세션들[sid]
            봉인됨 = bool(s.sealed_at) and bool(s.verified) and bool(s.integrity_ok)
            세션상태.append({"id": sid, "sealed": bool(s.sealed_at), "verified": 봉인됨})
            if not 봉인됨:
                문제들.append({"session_id": sid, "why": "session_not_sealed" if not s.sealed_at else "session_not_verified"})

        st.problems, st.verified = 문제들, not 문제들
        st.summary = _과제_요약(d, wid)                   # 만들 당시 숫자를 함께 남긴다
        d.commit()
        답 = {"id": st.id, "work_id": wid, "created_at": st.created_at, "verified": st.verified,
              "problems": 문제들, "sessions": 세션상태,
              "counts": {"messages": len(메시지들),
                         "links_confirmed": sum(l["decision"] == "confirmed" for l in 연결들),
                         "links_rejected": sum(l["decision"] == "rejected" for l in 연결들),
                         "redactions": len(가림쌍)}}
    print(f"← 내역서 {답['id'][:8]}…  work={wid}  원문 {len(메시지들)} · 연결 {len(연결들)} · 가림 {len(가림쌍)}  "
          f"{'검증됨' if 답['verified'] else '문제 ' + str(len(문제들)) + '건 ⚠'}")
    return jsonify(답), 201


def _내역서_내용(d, st, 학생용):
    """내역서 하나를 화면용으로. 학생용이면 '아니다'·가림의 위치까지, 교수용이면 확인된 연결만."""
    메시지 = d.query(db.Message).filter(db.Message.statement_id == st.id).all()
    해시로 = {}
    for m in 메시지:
        해시로.setdefault(m.hash, m)
    연결 = d.query(db.Link).filter(db.Link.statement_id == st.id).order_by(db.Link.id).all()
    가림 = d.query(db.Redaction).filter(db.Redaction.statement_id == st.id).all()

    def 글(h):
        m = 해시로.get(h) if h else None
        # history = 이전 대화라 ts 는 '본 시각'이지 '받은 시각'이 아니다 → 화면이 그렇게 써야 한다
        return {"text": m.text, "tool": m.tool, "ts": m.ts, "history": bool(m.history), "ok": bool(m.match)} if m else None

    맞다 = [{"question": 글(l.question_hash), "answer": 글(l.answer_hash),
             "result": {"text": l.result_text, "location": l.location},
             "kind": l.kind, "origin": l.origin} for l in 연결 if l.decision == "confirmed"]
    out = {"id": st.id, "created_at": st.created_at, "ai_scope": st.ai_scope, "sentence": st.sentence,
           "verified": bool(st.verified), "problems": st.problems or [], "summary": st.summary, "links": 맞다,
           "rejected": sum(l.decision == "rejected" for l in 연결), "redacted": len(가림)}
    if not 학생용:
        # ★ 교수 화면엔 세션·이벤트 id 를 내보내지 않는다. 세션 id 를 알면 /sessions/<id>/events 로
        #   작업 기록 전체(창 이름 포함)를 읽을 수 있다 — 학생이 공유한 건 내역서뿐이다.
        out["problems"] = [{"why": p.get("why")} for p in out["problems"]]
        if out["summary"]:
            out["summary"] = {**out["summary"],
                              "by_session": [{k: v for k, v in s.items() if k != "id"}
                                             for s in out["summary"].get("by_session", [])]}
    if 학생용:
        out["rejected_links"] = [{"answer_hash": l.answer_hash, "result_hash": l.result_hash, "location": l.location}
                                 for l in 연결 if l.decision == "rejected"]
        out["redactions"] = [{"session_id": r.session_id, "event_id": r.event_id} for r in 가림]
        out["messages"] = [{"session_id": m.session_id, "event_id": m.event_id, "tool": m.tool, "role": m.role,
                            "ts": m.ts, "ok": bool(m.match)} for m in 메시지]
    return out


@app.get("/api/works/<wid>/statements/latest")
@로그인_필요
def latest_statement(wid):
    with db.Session() as d:
        if not 내_과제(d, wid):
            return jsonify(error="not_found"), 404
        st = (d.query(db.Statement).filter(db.Statement.work_id == wid)
              .order_by(db.Statement.created_at.desc(), db.Statement.id.desc()).first())
        if not st:
            return jsonify(error="not_found", message="아직 만든 내역서가 없습니다"), 404
        답 = _내역서_내용(d, st, 학생용=True)
        답["shares"] = [{"token": s.token, "expires_at": s.expires_at, "revoked_at": s.revoked_at}
                        for s in d.query(db.Share).filter(db.Share.statement_id == st.id).all()]
    return jsonify(답)


@app.post("/api/statements/<stid>/share")
@로그인_필요
def create_share(stid):
    b = request.get_json(force=True, silent=True) or {}
    일수 = b.get("expires_in_days", 공유_기본일)
    if not isinstance(일수, int) or isinstance(일수, bool) or not 1 <= 일수 <= 공유_최대일:
        return jsonify(error="bad_request", message=f"expires_in_days 는 1~{공유_최대일} 사이 정수입니다"), 400
    with db.Session() as d:
        st = d.get(db.Statement, stid)
        if not st or st.user_id != g.user_id:
            return jsonify(error="not_found"), 404
        지금 = now()
        sh = db.Share(token=secrets.token_urlsafe(24), statement_id=stid, created_at=지금.isoformat(timespec="seconds"),
                      expires_at=(지금 + timedelta(days=일수)).isoformat(timespec="seconds"))
        d.add(sh)
        d.commit()
        답 = {"token": sh.token, "path": f"/api/share/{sh.token}", "page": f"/s/{sh.token}",
              "url": request.host_url.rstrip("/") + f"/s/{sh.token}",      # 학생이 교수에게 보내는 주소
              "pdf_url": request.host_url.rstrip("/") + f"/api/share/{sh.token}/pdf",   # 과제와 함께 내는 1장
              "expires_at": sh.expires_at}
    print(f"← 공유 링크 만듦  내역서 {stid[:8]}…  {일수}일")
    return jsonify(답), 201


@app.delete("/api/shares/<token>")
@로그인_필요
def revoke_share(token):
    with db.Session() as d:
        sh = d.get(db.Share, token)
        st = d.get(db.Statement, sh.statement_id) if sh else None
        if not st or st.user_id != g.user_id:
            return jsonify(error="not_found"), 404
        if not sh.revoked_at:
            sh.revoked_at = iso()
            d.commit()
    return jsonify(ok=True)


def _공유_내용(token):
    """교수용 내역서 데이터. 없는 링크·끊은 링크·지난 링크는 None (어느 쪽인지 알려 주지 않는다)."""
    with db.Session() as d:
        sh = d.get(db.Share, token)
        if (not sh or sh.revoked_at
                or datetime.fromisoformat(sh.expires_at) < now()):
            return None
        st = d.get(db.Statement, sh.statement_id)
        w, u = d.get(db.Work, st.work_id), d.get(db.User, st.user_id)
        답 = _내역서_내용(d, st, 학생용=False)
        답["work"] = {"title": w.title if w else None}
        답["author"] = u.name if u else None            # 계정 이름 — Trace 가 신원을 확인하지는 않는다
        답["expires_at"] = sh.expires_at
    return 답


@app.get("/api/share/<token>")
def read_share(token):
    """교수 확인용 — 로그인 없음 · 읽기 전용. 없는 링크·끊은 링크·지난 링크는 똑같이 404 (어느 쪽인지 알려 주지 않는다)."""
    답 = _공유_내용(token)
    if 답 is None:
        return jsonify(error="not_found", message="없거나 끝난 링크입니다"), 404
    return jsonify(답)


@app.get("/api/share/<token>/pdf")
def share_pdf(token):
    """AI 활용 내역서 1장 PDF (기획서 10절). 학생이 과제와 함께 낸다. 안에 교수 확인 링크·QR 이 들어간다.
    링크를 아는 사람만 받는다 — 링크와 같은 열쇠. (server/statement_pdf.py)"""
    답 = _공유_내용(token)
    if 답 is None:
        return jsonify(error="not_found", message="없거나 끝난 링크입니다"), 404
    from urllib.parse import quote
    import statement_pdf                                   # reportlab · 글꼴은 PDF 를 처음 만들 때만 읽는다
    pdf = statement_pdf.render(답, request.host_url.rstrip("/") + f"/s/{token}")
    이름 = f"AI활용내역서_{(답['work']['title'] or '과제')[:40]}.pdf"
    return app.response_class(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f"inline; filename=\"statement.pdf\"; filename*=UTF-8''{quote(이름)}"})


@app.get("/s/<token>")
def share_page(token):
    """교수가 여는 화면. HTML 한 장이 /api/share/<token> 을 읽어 그린다 (server/static/share.html).
    토큰이 맞는지는 여기서 보지 않는다 — 화면이 API 를 부르고, 없으면 "볼 수 없는 링크"를 그린다."""
    return send_from_directory(os.path.join(HERE, "static"), "share.html")


@app.after_request
def 공유_머리(resp):
    """공유 링크는 주소 자체가 열쇠다. 다른 사이트로 새지 않게(Referer) · 검색에 안 잡히게 · 저장 안 되게."""
    if request.path.startswith(("/s/", "/api/share/")):
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    # ★ 맥은 5000 번을 AirPlay 수신 모드가 이미 쓰고 있다 ★
    #   우리 서버가 꺼져 있으면 AirPlay 가 대신 대답하고 403 을 돌려준다.
    #   수집기는 "서버가 있네" 하고 보냈다가 계속 거절당한다. 원인 찾기 어렵다.
    #   맥에서는 포트를 바꾸는 쪽이 낫다:  TRACE_PORT=5050 python server/app.py
    #   (윈도우는 이 문제가 없어 5000 그대로 쓰면 된다)
    PORT = int(os.environ.get("TRACE_PORT", "5000"))
    print(f"Trace Backend  http://127.0.0.1:{PORT}/api   저장: {db.DB_URL_SAFE}")
    print("  계약: docs/api.md   ·  참고 구현과 같은 응답을 내야 합니다")
    print(f"  인증: {'강제' if 인증_강제 else '선택 (TRACE_REQUIRE_AUTH=1 로 켬)'}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
