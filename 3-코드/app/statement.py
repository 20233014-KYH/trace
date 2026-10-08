"""
statement.py — 학생 PC 의 "내역서 만들기" 화면 (docs/api.md 10절 · 10/8)

  python app/statement.py                 # 브라우저에 화면이 뜬다 (http://127.0.0.1:5079)
  python app/statement.py --config 내설정.json

★ 왜 PC 에서 도나 ★
  AI 질문·답 원문과 과제 파일은 학생 PC 에만 있다 (서버엔 해시만). 그래서 연결 찾기(core/match.py)도 PC 에서 하고,
  학생이 "맞다"로 고른 연결의 원문 · 학생이 가리지 않은 질문만 서버로 보낸다. "아니다"는 해시·위치만 간다.

  ① 로그인 (서버 /api/auth/login → 토큰은 data/auth.json 에 · 기록기도 나중에 이 파일을 쓰면 된다)
  ② 과제 고르기 (내 과제 목록 + 이 PC 에 있는 그 과제의 기록 수)
  ③ 과제 파일(.docx) 고르기 → 이 PC 의 AI 답·붙여넣기 기록과 문장마다 연결 제안
  ④ 제안마다 맞다 / 아니다 · 질문 가리기 · 한 줄 설명 → 서버에 내역서 만들기 → 교수에게 보낼 링크

화면은 같은 폴더의 statement.html 한 장. 이 서버는 127.0.0.1 에서만 듣는다.
"""
import argparse
import glob
import io
import json
import os
import platform
import sys
import threading
import uuid
import webbrowser

import requests
from flask import Flask, abort, jsonify, request, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from core import match as M                    # noqa: E402  연결 제안 (박상진)
from core.docx import doc_body                 # noqa: E402
from core.texthash import sha256_text          # noqa: E402

PORT = 5079                                     # 기록기 브리지는 5077
app = Flask(__name__)
설정 = {}                                        # main() 이 채운다: server, data_dir
분석들 = {}                                      # 분석 id → 서버로 보낼 때 필요한 것 (원문은 이 PC 메모리에만)


# ─────────────── 이 PC 의 로컬 서버를 남이 부르지 못하게 ───────────────
@app.before_request
def 로컬만():
    """① Host 가 127.0.0.1:포트 가 아니면 거절 (DNS 리바인딩 — 다른 사이트가 이 주소를 자기 이름으로 부르는 것)
    ② 바꾸는 요청엔 X-Trace-Local 머리가 있어야 함 (다른 사이트의 폼·스크립트는 이 머리를 붙이려면 허락을 받아야 하는데, 허락하지 않는다)"""
    if request.host not in (f"127.0.0.1:{PORT}", f"localhost:{PORT}"):
        abort(403)
    if request.method != "GET" and request.headers.get("X-Trace-Local") != "1":
        abort(403)


# ─────────────── 서버 · 토큰 ───────────────
def _auth_path():
    return os.path.join(설정["data_dir"], "auth.json")


def _auth():
    try:
        a = json.load(open(_auth_path(), encoding="utf-8"))
        return a if a.get("server") == 설정["server"] else {}
    except (OSError, ValueError):
        return {}


def _서버(방법, 경로, **kw):
    """학생 대신 인터넷 서버를 부른다. (코드, JSON)"""
    머리 = kw.pop("headers", {})
    t = _auth().get("token")
    if t:
        머리["Authorization"] = f"Bearer {t}"
    try:
        r = requests.request(방법, 설정["server"].rstrip("/") + 경로, headers=머리, timeout=90, **kw)
    except requests.RequestException as e:
        return 502, {"error": "server_unreachable", "message": f"서버에 연결하지 못했습니다 ({type(e).__name__}). 무료 서버는 처음 깨울 때 1분쯤 걸립니다."}
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"error": "bad_response", "message": f"서버 응답을 읽지 못했습니다 (HTTP {r.status_code})"}


# ─────────────── 이 PC 의 기록 ───────────────
def _jsonl(pattern):
    out = []
    for p in sorted(glob.glob(os.path.join(설정["data_dir"], pattern))):
        with open(p, encoding="utf-8") as f:
            out += [json.loads(l) for l in f if l.strip()]
    return out


def _과제별_세션():
    """events-*.jsonl 의 session_start → {work_id: {세션 id, ...}}"""
    out = {}
    for e in _jsonl("events-*.jsonl"):
        if e.get("type") == "session_start" and e.get("work_id"):
            out.setdefault(e["work_id"], set()).add(e["session_id"])
    return out


# ─────────────── 화면 ───────────────
@app.get("/")
def page():
    return send_from_directory(HERE, "statement.html")


@app.get("/local/state")
def state():
    a = _auth()
    return jsonify(server=설정["server"], data_dir=설정["data_dir"], user=a.get("user"), logged_in=bool(a.get("token")))


@app.post("/local/login")
def login():
    b = request.get_json(force=True)
    코드, 답 = _서버("POST", "/auth/login", json={"email": b.get("email", ""), "password": b.get("password", ""),
                                                 "device": f"내역서 화면 · {platform.node()}"})
    if 코드 != 200:
        return jsonify(답), 코드
    os.makedirs(설정["data_dir"], exist_ok=True)
    with open(_auth_path(), "w", encoding="utf-8") as f:            # data/ 는 .gitignore — 저장소에 안 올라간다
        json.dump({"server": 설정["server"], "token": 답["token"], "user": 답["user"]}, f, ensure_ascii=False)
    return jsonify(user=답["user"])


@app.post("/local/logout")
def logout():
    _서버("POST", "/auth/logout", json={})
    try:
        os.remove(_auth_path())
    except OSError:
        pass
    return jsonify(ok=True)


@app.get("/local/works")
def works():
    코드, 답 = _서버("GET", "/me")
    if 코드 != 200:
        return jsonify(답), 코드
    pc = _과제별_세션()
    내것 = {w["id"] for w in 답.get("works", [])}
    return jsonify(
        works=[{**w, "pc_sessions": len(pc.get(w["id"], ()))} for w in 답.get("works", [])],
        # 이 PC 에 기록은 있는데 내 과제 목록엔 없는 것 = 기록기가 로그인 없이 만든 과제 (주인 없음)
        orphans=[{"id": k, "pc_sessions": len(v)} for k, v in sorted(pc.items()) if k not in 내것])


@app.post("/local/analyze")
def analyze():
    """과제 파일 + 이 PC 의 그 과제 기록 → 문장마다 연결 제안. 원문은 화면(같은 PC)으로만 간다."""
    wid, f = request.form.get("work_id", ""), request.files.get("file")
    if not wid or not f:
        return jsonify(error="bad_request", message="과제와 .docx 파일이 필요합니다"), 400
    try:
        title, body = doc_body(io.BytesIO(f.read()), name=f.filename)
    except Exception:
        return jsonify(error="bad_file", message="Word(.docx) 파일을 읽지 못했습니다"), 400

    세션 = _과제별_세션().get(wid, set())
    if not 세션:
        return jsonify(error="no_records", message="이 PC 에 이 과제의 기록이 없습니다 (기록기를 켠 PC 에서 열어 주세요)"), 404
    events = sorted((e for e in _jsonl("events-*.jsonl") if e.get("session_id") in 세션), key=lambda e: e.get("ts", ""))
    context = [c for c in _jsonl("context-*.jsonl") if c.get("session_id") in 세션]
    기록 = M.latest_messages([r for r in _jsonl("ai-messages-*.jsonl") if r.get("session_id") in 세션])
    기록.sort(key=lambda r: r.get("ts", ""))
    답들 = [r for r in 기록 if r.get("role") == "answer"]

    def 질문(ans):
        """이 답 바로 앞의 같은 세션·같은 도구 질문 (턴 번호는 도구마다 세는 법이 달라 시각 순서로)"""
        앞 = [r for r in 기록 if r.get("role") == "question" and r["session_id"] == ans["session_id"]
              and r.get("tool") == ans.get("tool") and r.get("ts", "") <= ans.get("ts", "")]
        return 앞[-1] if 앞 else None

    pasted = M.pasted_from_ai(events, context)
    others = M.pasted_from_other(events, context)
    proc = M.process_evidence(events, context)
    linked = M.link_document(body, [{"id": i, "text": r["text"]} for i, r in enumerate(답들)], pasted, others, proc)

    aid, 제안, 화면 = uuid.uuid4().hex, {}, []
    for pi, row in enumerate(linked):
        문단 = []
        for si, s in enumerate(row):
            칸 = {"text": s["text"], "label": s["label"]}
            if s["label"] in ("exact", "edited", "viewed") and s.get("answer") is not None:
                a = 답들[s["answer"]]
                q = 질문(a)
                k = f"{pi}.{si}"
                kind = ("exact" if s.get("full") else "similar") if s["label"] == "exact" else s["label"]
                제안[k] = {"answer": a, "question": q, "result": s["text"], "paragraph": pi + 1,
                           "kind": kind, "origin": "auto" if s.get("paste") else "suggested"}
                칸.update(key=k, kind=kind, ai_text=s.get("ai_text"),
                          answer={"text": a["text"], "tool": a.get("tool"), "ts": a.get("ts"), "history": a.get("history")},
                          question={"id": f"{q['session_id']}/{q['event_id']}", "text": q["text"], "ts": q.get("ts")} if q else None,
                          pasted=bool(s.get("paste")))
            elif s["label"] == "web":
                칸["source"] = (s.get("paste") or {}).get("source", "")
            문단.append(칸)
        화면.append(문단)
    분석들[aid] = {"work_id": wid, "file": f.filename, "links": 제안}
    return jsonify(id=aid, title=title, file=f.filename, paragraphs=화면, sessions=len(세션),
                   ai_messages=len(기록), answers=len(답들))


@app.post("/local/statement")
def make_statement():
    """학생의 고름 → 서버 POST /works/<id>/statements. "맞다"인 연결의 답·질문 원문만, 가린 질문은 위치만."""
    b = request.get_json(force=True)
    분석 = 분석들.get(b.get("analysis_id"))
    if not 분석:
        return jsonify(error="expired", message="분석이 없습니다. 과제 파일을 다시 골라 주세요"), 400
    고름 = b.get("decisions") or {}
    가림 = set(b.get("hide_questions") or [])
    messages, links, redactions = {}, [], {}
    for k, x in 분석["links"].items():
        d = 고름.get(k)
        if d not in ("confirmed", "rejected"):
            continue                                            # 고르지 않은 제안은 보내지 않는다
        a, q = x["answer"], x["question"]
        q_id = f"{q['session_id']}/{q['event_id']}" if q else None
        loc = {"file": 분석["file"], "paragraph": x["paragraph"]}
        if d == "confirmed":
            messages[(a["session_id"], a["event_id"])] = a
            if q and q_id in 가림:
                redactions[(q["session_id"], q["event_id"])] = True
            elif q:
                messages[(q["session_id"], q["event_id"])] = q
            links.append({"answer_hash": a["hash"], "question_hash": q["hash"] if q and q_id not in 가림 else None,
                          "result_hash": sha256_text(x["result"]), "result_text": x["result"], "location": loc,
                          "kind": x["kind"], "origin": x["origin"], "decision": "confirmed"})
        else:                                                   # 아니다 — 원문 없이 해시·위치만
            links.append({"answer_hash": a["hash"], "result_hash": sha256_text(x["result"]), "location": loc,
                          "kind": x["kind"], "origin": x["origin"], "decision": "rejected"})
    if not links:
        return jsonify(error="empty", message="맞다·아니다를 하나 이상 골라 주세요"), 400
    body = {"sentence": (b.get("sentence") or "").strip() or None,
            "messages": [{"session_id": s, "event_id": e, "text": m["text"]} for (s, e), m in messages.items()
                         if (s, e) not in redactions],
            "links": links,
            "redactions": [{"session_id": s, "event_id": e} for (s, e) in redactions]}
    코드, 답 = _서버("POST", f"/works/{분석['work_id']}/statements", json=body)
    return jsonify(답), 코드


@app.post("/local/share")
def share():
    b = request.get_json(force=True)
    코드, 답 = _서버("POST", f"/statements/{b.get('statement_id')}/share",
                     json={"expires_in_days": int(b.get("days") or 14)})
    return jsonify(답), 코드


def main():
    global PORT
    ap = argparse.ArgumentParser(description="Trace — 내역서 만들기 (학생 PC)")
    ap.add_argument("--config", default=os.path.join(ROOT, "collector", "config.json"), help="기록기 설정 (server · data_dir)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    설정["server"] = cfg.get("server", "http://127.0.0.1:5000/api")
    설정["data_dir"] = os.path.normpath(os.path.join(ROOT, "collector", cfg.get("data_dir", "../data")))
    PORT = a.port
    주소 = f"http://127.0.0.1:{PORT}/"
    print(f"Trace 내역서 만들기  {주소}\n  서버 {설정['server']}\n  기록 {설정['data_dir']}\n  끄려면 Ctrl+C")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(주소)).start()
    app.run(host="127.0.0.1", port=PORT, debug=False)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
