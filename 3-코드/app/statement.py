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
from core.docx import doc_body, read_docx      # noqa: E402
from core.texthash import sha256_text          # noqa: E402
from core import settings                      # noqa: E402  기록기·알약과 같은 설정 파일 (10/13)
from core.version import VERSION, parse as parse_version  # noqa: E402  설치판 버전 (새 버전 알림)

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
@app.get("/make")
def page():
    """옛 내역서 만들기 한 장 — 캔버스에 없는 화면. / 는 홈(app/home.py)이 받고, 이 화면은 정리될 때까지 /make 로 남긴다 (10/13)"""
    return send_from_directory(HERE, "statement.html")


@app.get("/local/state")
def state():
    a = _auth()
    return jsonify(server=설정["server"], server_name=_서버_이름(), config=설정.get("config"),
                   server_local=settings.is_local(설정["server"]),
                   data_dir=설정["data_dir"], user=a.get("user"), logged_in=bool(a.get("token")),
                   version=VERSION, recording=_기록_중())


# ─────────────── 설치판 (v0.1 · 10/13) — 새 버전 알림 · 기록 시작 ───────────────
def _기록_중():
    """기록기가 켜져 있으면 확장 다리(5077)가 열려 있다"""
    import socket
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", 5077)) == 0


@app.get("/local/update")
def update():
    """인터넷 서버에 최신 설치판을 묻는다 (서버가 GitHub 릴리스를 읽어 둠). 시험 서버를 쓰는 중이어도 늘 인터넷 서버에."""
    try:
        r = requests.get(settings.INTERNET + "/app/latest", timeout=15)
        최신 = r.json() if r.ok else {}
    except (requests.RequestException, ValueError):
        최신 = {}
    v = 최신.get("version")
    return jsonify(current=VERSION, latest=v, newer=bool(v) and parse_version(v) > parse_version(VERSION),
                   download=settings.INTERNET.removesuffix("/api") + "/download", notes=최신.get("notes"))


@app.post("/local/record")
def start_record():
    """알약 + 기록기를 따로 띄운다 (설치판은 Trace.exe record · 저장소는 python app/pill.py)"""
    import subprocess
    if _기록_중():
        return jsonify(ok=True, already=True)
    명령 = [sys.executable, "record"] if settings.FROZEN else [sys.executable, os.path.join(HERE, "pill.py")]
    if 설정.get("config_arg"):
        명령 += ["--config", 설정["config_arg"]]
    subprocess.Popen(명령, cwd=ROOT, close_fds=True,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if settings.FROZEN else 0)
    return jsonify(ok=True, already=False)


def _서버_이름():
    """로그인 화면에 보여 줄 서버 — 다른 서버에 로그인하면 계정이 없어 '비밀번호가 틀렸다' 로만 보인다 (10/12 박상진 겪음)"""
    s = 설정["server"]
    if "127.0.0.1" in s or "localhost" in s:
        return f"이 PC 의 시험 서버 ({s})"
    return f"인터넷 서버 ({s.replace('https://', '').replace('/api', '')})"


@app.post("/local/login")
def login():
    b = request.get_json(force=True)
    코드, 답 = _서버("POST", "/auth/login", json={"email": (b.get("email") or "").strip(), "password": b.get("password", ""),
                                                 "device": f"내역서 화면 · {platform.node()}"})
    if 코드 == 401:
        # 서버는 '계정 없음' 과 '비밀번호 틀림' 을 일부러 구분하지 않는다 → 어느 서버에 물었는지라도 알려 준다
        답 = {**답, "message": f"{답.get('message', '이메일 또는 비밀번호가 맞지 않습니다')} — 로그인할 서버: {_서버_이름()}. "
                             f"다른 서버에서 가입했다면 설정 파일({os.path.basename(설정.get('config', 'config.json'))})의 server 를 확인하세요."}
    if 코드 != 200:
        return jsonify(답), 코드
    os.makedirs(설정["data_dir"], exist_ok=True)
    with open(_auth_path(), "w", encoding="utf-8") as f:            # data/ 는 .gitignore — 저장소에 안 올라간다
        json.dump({"server": 설정["server"], "token": 답["token"], "user": 답["user"]}, f, ensure_ascii=False)
    return jsonify(user=답["user"])


@app.post("/local/server")
def switch_server():
    """로그인 화면의 "인터넷 서버로 바꾸기" / "이 PC 의 시험 서버로" — 내 설정(~/trace-config.json)에 적는다.
    기록기·알약도 같은 파일을 읽으므로 다음에 켤 때 같은 서버로 간다 (켜져 있는 기록기는 다시 켜야 함)."""
    to = (request.get_json(force=True, silent=True) or {}).get("to")
    if to not in ("internet", "local"):
        return jsonify(error="bad_request", message="to 는 internet 또는 local"), 400
    설정["server"] = settings.INTERNET if to == "internet" else settings.LOCAL
    설정["config"] = settings.set_server(설정["server"])
    return jsonify(server=설정["server"], server_name=_서버_이름(), config=설정["config"])


@app.post("/local/signup")
def signup():
    """처음 쓰는 사람 — 지금 화면이 보는 서버에 계정을 만들고 바로 로그인한다 (전엔 명령어로만 가입할 수 있었음)"""
    b = request.get_json(force=True)
    코드, 답 = _서버("POST", "/auth/signup", json={"email": (b.get("email") or "").strip(), "password": b.get("password", ""),
                                                  "name": (b.get("name") or "").strip() or None})
    if 코드 != 201:
        return jsonify(답), 코드
    return login()


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
        원본 = f.read()                                        # 출처 보기를 켜면 내역서 만들 때 다시 읽는다 (이 PC 메모리에만)
        title, body = doc_body(io.BytesIO(원본), name=f.filename)
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

    # 연결 확인(app/confirm.py · 박상진)에서 고른 것: link → 맞다 · no → 아니다 · unsure → 잘 모르겠음 (10/12)
    # 붙여넣기 기록이 있는 연결은 연결 확인이 묻지 않고 자동으로 넣는다 → 여기서도 "맞다"로 채워 둔다
    확인 = 연결확인._읽기(wid)
    옮김 = {"link": "confirmed", "no": "rejected", "unsure": "unsure"}
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
                          pasted=bool(s.get("paste")),
                          preset="confirmed" if s.get("paste") else 옮김.get(확인.get(연결확인.key_of(s["text"], a["hash"]))))
            elif s["label"] == "web":
                칸["source"] = (s.get("paste") or {}).get("source", "")
            문단.append(칸)
        화면.append(문단)
    분석들[aid] = {"work_id": wid, "file": f.filename, "links": 제안,
                  "docx": 원본, "records": (기록, events, context)}
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
            continue                                            # 고르지 않은·잘 모르겠음 제안은 원문을 보내지 않는다 (개수만 아래 unsure)
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
    보류 = sum(1 for k in 분석["links"] if 고름.get(k) not in ("confirmed", "rejected"))   # 잘 모르겠음 + 안 고름
    출처자료 = _출처_보기(분석, 고름, 가림, messages) if b.get("with_source") else None
    body = {"explain_use": (b.get("explain_use") or "").strip()[:150] or None,      # v3 질문 두 칸 (10/10)
            "explain_check": (b.get("explain_check") or "").strip()[:150] or None,
            "ai_scope": (b.get("ai_scope") or "").strip() or None,                   # 학생이 넣었을 때만
            "unsure": 보류,                                                           # 판단 보류 개수만 (원문 없음)
            "show_process": bool(b.get("with_process")),                               # 작업 과정 탭 — 켰을 때만 (기본 끔)
            "source": 출처자료,                                                         # 출처 보기 — 켰을 때만 (기본 끔 · 10/11)
            "messages": [{"session_id": s, "event_id": e, "text": m["text"], "model": m.get("model") or None}
                         for (s, e), m in messages.items() if (s, e) not in redactions],
            "links": links,
            "redactions": [{"session_id": s, "event_id": e} for (s, e) in redactions]}
    코드, 답 = _서버("POST", f"/works/{분석['work_id']}/statements", json=body)
    return jsonify(답), 코드


def _출처_보기(분석, 고름, 가림, messages):
    """교수 링크 출처 보기 (10/11 박상진 · 기본 끔 — 학생이 켰을 때만). PC 출처 보기(source.build)와 같은 자료에
    학생의 고름을 입힌다: 아니다 → 출처 없음 · 잘 모르겠음/안 고름 → 보류 표시 · 가린 질문 → 빼고 "가림".
    질문·답(참고만 한 것 포함) 원문은 messages 에 더해 서버가 체인 해시로 맞춰 본다. 보고서 전문은 맞춰 볼 해시가 없다."""
    기록, events, context = 분석["records"]
    b = 출처.build(read_docx(io.BytesIO(분석["docx"])), 기록, events, context)
    # source.build 의 문장 순서 = link_document 의 (문단, 문장) 순서 = 이 화면의 키 "p.s"
    자리 = {k: f"{pi}.{si}" for pi, p in enumerate(b["paragraphs"]) for si, k in enumerate(p["sents"])}
    문장 = []
    for x in b["sentences"]:
        x = {k: v for k, v in x.items() if k in ("k", "p", "text", "kind", "group", "q", "sents", "paste", "proc")}
        d = 고름.get(자리.get(x["k"]))
        if "q" in x:
            if d == "rejected":                       # 학생이 아니라고 함 → 출처 없음으로 (원래 제안은 보여 주지 않는다)
                x = {k: v for k, v in x.items() if k in ("k", "p", "text")} | {"kind": "none", "group": "none", "rejected": True}
            elif d != "confirmed":
                x["unsure"] = True
        문장.append(x)
    질문 = []
    for q in b["questions"]:
        r = q.get("refs", {})
        qid = f"{r['q']['session_id']}/{r['q']['event_id']}" if "q" in r else None
        숨김 = qid in 가림
        for 역, 글 in (("q", None if 숨김 else q.get("question")), ("a", "".join(t["t"] for t in q.get("answer") or []) or None)):
            if 역 in r and 글 is not None:            # 원문을 서버가 맞춰 보게 messages 에 (같은 것은 한 번만)
                원 = next((m for m in 기록 if m.get("event_id") == r[역]["event_id"] and m["session_id"] == r[역]["session_id"]), None)
                if 원:
                    messages[(원["session_id"], 원["event_id"])] = 원
        질문.append({"n": q["n"], "tool": q.get("tool"), "model": q.get("model"), "ts": q.get("ts"),
                     "question": None if 숨김 else q.get("question"), "hidden": 숨김,
                     "question_hash": None if 숨김 else (r.get("q") or {}).get("hash"),
                     "answer": q.get("answer"), "answer_hash": (r.get("a") or {}).get("hash"),
                     "uses": [k for k in q.get("uses", []) if not 문장[k].get("rejected")], "paras": q.get("paras")})
    return {"file": 분석["file"], "title": b["title"], "paragraphs": b["paragraphs"], "sentences": 문장, "questions": 질문}


@app.post("/local/share")
def share():
    b = request.get_json(force=True)
    코드, 답 = _서버("POST", f"/statements/{b.get('statement_id')}/share",
                     json={"expires_in_days": int(b.get("days") or 14)})
    return jsonify(답), 코드


# ─────────────── 출처 보기 · 연결 확인 · 내보내기 (캔버스 4 · 5-1 · 7 · 박상진 · app/source.py · confirm.py · export.py) — 같은 기록 읽기를 쓴다 ───────────────
import source as 출처                            # noqa: E402
import confirm as 연결확인                        # noqa: E402
from urllib.parse import quote                  # noqa: E402
_내역서_있음 = set()                              # 한 번 확인되면 다시 묻지 않음


def _내역서_있나(wid):
    """왼쪽 과제를 누르면 그 과제가 어디까지 왔는지 보고 그 단계로 보낸다 — 그중 "내역서를 만들었나".
    로그인 안 했거나 서버가 늦으면 None (모름 → PC 기록만으로 판단). 화면 넘김이 늦지 않게 4초만 기다린다"""
    if wid in _내역서_있음:
        return True
    t = _auth().get("token")
    if not t:
        return None
    try:
        r = requests.get(설정["server"].rstrip("/") + f"/works/{quote(wid, safe='')}/statements/latest",
                         headers={"Authorization": f"Bearer {t}"}, timeout=4)
    except requests.RequestException:
        return None
    if r.status_code == 200:
        _내역서_있음.add(wid)
        return True
    return False if r.status_code == 404 else None


import export as 내보내기                         # noqa: E402  캔버스 7 · app/export.py
출처.init(_jsonl, _과제별_세션, lambda: 설정["data_dir"], _내역서_있나,
          server=lambda *a, **kw: _서버(*a, **kw), auth=lambda: _auth(), made=_내역서_있음.add,
          source_data=lambda *a: _출처_보기(*a))      # 교수 링크 출처 보기 자료 (김용현 #44) — 내보내기도 같은 것을 씀
app.register_blueprint(출처.bp)
app.register_blueprint(연결확인.bp)
app.register_blueprint(내보내기.bp)
import home as 홈                                 # noqa: E402  캔버스 홈 A · 로그인 (/ → /home · /login)
import work as 과제                               # noqa: E402  캔버스 1-1 새 과제 · 과제 설정 · 2 과제 상세
app.register_blueprint(홈.bp)
app.register_blueprint(과제.bp)
import options as 설정화면                         # noqa: E402  캔버스 곁가지 · 설정 6칸 (10/13)
app.register_blueprint(설정화면.bp)
import review as 돌아보기                          # noqa: E402  캔버스 곁가지 · 돌아보기 v2 (10/13)
app.register_blueprint(돌아보기.bp)
과제.설정.update(bridge=홈._기록기, config=lambda: 설정.get("config"))


def main():
    global PORT
    ap = argparse.ArgumentParser(description="Trace — 내역서 만들기 (학생 PC)")
    ap.add_argument("--config", help="설정 파일 (기본: 내 설정 ~/trace-config.json → 없으면 collector/config.json · 기록기와 같음)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    cfg, 설정["config"] = settings.load(a.config)
    설정["config_arg"] = a.config
    설정["server"] = cfg.get("server", settings.LOCAL)
    설정["data_dir"] = os.path.normpath(os.path.join(ROOT, "collector", cfg.get("data_dir", "../data")))
    PORT = a.port
    주소 = f"http://127.0.0.1:{PORT}/"
    print(f"Trace 내역서 만들기  {주소}\n  서버 {설정['server']}\n  설정 {설정['config']}\n  기록 {설정['data_dir']}\n  끄려면 Ctrl+C")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(주소)).start()
    app.run(host="127.0.0.1", port=PORT, debug=False)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
