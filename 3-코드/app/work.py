"""
work.py — 새 과제 · 과제 설정 · 과제 상세 (캔버스 "Trace 화면 뼈대" 1-1 새 과제 · 과제 설정 · 2 과제 상세 · 10/13 박상진)

  /new                     → 새 과제 (이름만 필수 · 과목 · 마감 · 교수 AI 규칙은 선택) → [만들기] → 과제 상세에서 [기록 시작]
  /work/settings?work=…    → 같은 화면을 "과제 설정" 으로 ([저장])
  /work?work=…             → 과제 상세: 단계 · 이 과제의 기록 목록 · 기록된 과제 파일 · 교수 AI 규칙

어디에 두나:
  · 과제 이름 · 교수 AI 규칙(ai_scope) → 서버 (내역서 PDF 가 씀)
  · 과목 · 마감 → 이 PC data/work-<과제>.json (서버엔 칸이 없고, 홈 카드 정렬·마감 알림에만 씀)
  · 기록 목록 = 이 PC 기록(events) · "서버 일치" = 서버가 그 기록을 봉인했나 (GET /works/<id>)
"""
import glob
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from urllib.parse import quote

from flask import Blueprint, jsonify, request, send_from_directory

import source as S
import confirm as CF
import export as EX
from core import match as M, safefile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
bp = Blueprint("work", __name__)
_WID = re.compile(r"^[\w\-.]{1,64}$")
_DUE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$")
설정 = {}            # statement.py 가 채움: config(설정 파일 경로) · bridge(기록기 상태 함수)


@bp.get("/new")
def new_page():
    return send_from_directory(HERE, "newwork.html")


@bp.get("/work/settings")
def settings_page():
    return send_from_directory(HERE, "newwork.html")


@bp.get("/work")
def detail_page():
    return send_from_directory(HERE, "detail.html")


# ─────────────── 이 PC 에만 두는 것 (과목 · 마감) ───────────────
def _경로(wid):
    return os.path.join(S._기록["data_dir"](), f"work-{wid}.json")


def meta(wid):
    d = safefile.read_json(_경로(wid), {})
    return d if isinstance(d, dict) else {}


def _meta_쓰기(wid, d):
    safefile.write_json(_경로(wid), d, indent=1)


def _입력(b):
    """{title, course, due, ai_scope} 검사 → (값, 오류)"""
    title = (b.get("title") or "").strip()
    if not title:
        return None, "과제 이름을 넣어 주세요"
    if len(title) > 120:
        return None, "과제 이름은 120자까지예요"
    course = (b.get("course") or "").strip()[:60]
    due = (b.get("due") or "").strip()
    if due and not _DUE.match(due):
        return None, "마감 날짜 모양이 올바르지 않아요"
    scope = (b.get("ai_scope") or "").strip()
    if len(scope) > 2000:
        return None, "교수 AI 규칙은 2000자까지예요"
    return {"title": title, "course": course, "due": due, "ai_scope": scope or None}, None


@bp.post("/local/work/create")
def create():
    """json: {title, course?, due?, ai_scope?, start?} → 서버에 과제를 만들고(이 PC 만의 id W-…) 과목·마감은 PC 에 · start 면 기록 시작"""
    b = request.get_json(force=True, silent=True) or {}
    v, 오류 = _입력(b)
    if 오류:
        return jsonify(error="bad_request", message=오류), 400
    wid = "W-" + uuid.uuid4().hex[:10]
    코드, 답 = S._기록["server"]("POST", "/works", json={"id": wid, "title": v["title"], "ai_scope": v["ai_scope"]})
    if 코드 != 201:
        return jsonify(답), 코드
    _meta_쓰기(wid, {"course": v["course"], "due": v["due"], "created_at": datetime.now().astimezone().isoformat(timespec="seconds")})
    out = {"id": wid, "go": f"/work?work={quote(wid, safe='')}"}
    if b.get("start"):
        out["record"] = _기록_시작(wid)
    return jsonify(out), 201


@bp.post("/local/work/save")
def save():
    """과제 설정 [저장] — 이름 · 교수 AI 규칙은 서버, 과목 · 마감은 PC"""
    b = request.get_json(force=True, silent=True) or {}
    wid = b.get("work_id") or ""
    if not _WID.match(wid):
        return jsonify(error="bad_request", message="과제가 올바르지 않습니다"), 400
    v, 오류 = _입력(b)
    if 오류:
        return jsonify(error="bad_request", message=오류), 400
    코드, 답 = S._기록["server"]("PATCH", f"/works/{quote(wid, safe='')}", json={"title": v["title"], "ai_scope": v["ai_scope"]})
    if 코드 != 200:
        return jsonify(답), 코드
    m = meta(wid)
    m.update(course=v["course"], due=v["due"])
    _meta_쓰기(wid, m)
    return jsonify(ok=True, go=f"/work?work={quote(wid, safe='')}")


# ─────────────── 과제 삭제 · 기록 하나 지우기 · 옮기기 (캔버스 Delete · 10/15 박상진) ───────────────
# 자주 쓰는 것 = 기록 하나 (잘못 붙인 기록 → 옮기기 · 시험 삼아 켠 기록 → 이 기록만 지우기). 내역서(PDF · 교수 링크)는 그대로 —
#   이미 낸 내역서엔 서버가 "지운 기록 n개" 로 남긴다.
# 과제 전체 지우기 = 한 번 확인 · 과제 · 기록 · 내역서(PDF · 교수 링크)까지 모두. 내역서가 없어지는 건 이때뿐.
#   학생이 내려받아 저장한 PDF 파일은 Trace 가 어디 있는지 몰라 못 지운다 (화면이 알려 줌).
# 기록 창이 켜져 있으면 못 지움 · 못 옮김 — 기록기가 같은 기록 파일에 쓰는 중이라 줄을 지우면 깨질 수 있다.
_기록중_말 = "기록 중에는 지우거나 옮길 수 없어요. 기록 창에서 작업을 마친 뒤 해 주세요"


def _지울_것(wid):
    세션 = S._기록["sessions"]().get(wid, set())
    made = EX._읽기(wid).get("made") or {}
    return 세션, {"sessions": len(세션), "report_made": bool(made.get("statement_id")),
                 "shared": bool(made.get("url")) and made.get("expires_at", "") > datetime.now().astimezone().isoformat()}


def _이PC_기록_지우기(세션):
    """이 PC 기록 파일에서 그 기록들의 줄을 지운다 → 지운 줄 수. 옮김 표에서도 뺀다"""
    d = S._기록["data_dir"]()
    줄 = 0
    for 무늬 in ("events-*.jsonl", "context-*.jsonl", "ai-messages-*.jsonl"):
        for p in glob.glob(os.path.join(d, 무늬)):
            줄 += safefile.drop_lines(p, lambda r: r.get("session_id") in 세션)
    _옮김_고치기(lambda m: [m.pop(s, None) for s in 세션])
    return 줄


def _옮김_고치기(fn):
    p = os.path.join(S._기록["data_dir"](), "moved.json")
    with safefile.lock(p):
        m = safefile.read_json(p, {})
        m = m if isinstance(m, dict) else {}
        전 = dict(m)
        fn(m)
        if m != 전:
            safefile.write_json(p, m, indent=1)


@bp.get("/local/work/delete-info")
def delete_info():
    """과제 지우기 전에 {title, recording, recording_this, sessions, report_made, shared}"""
    wid = request.args.get("work_id", "")
    if not _WID.match(wid):
        return jsonify(error="bad_request"), 400
    코드, w = S._기록["server"]("GET", f"/works/{quote(wid, safe='')}")
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    rec = 설정["bridge"]()
    _, 것 = _지울_것(wid)
    있나 = S._기록.get("statement_exists")
    if 것["sessions"] and not 것["report_made"] and 있나:          # 서버에 물음 (최대 4초) — 기록이 있을 때만
        것["report_made"] = bool(있나(wid))
    return jsonify(title=(w.get("title") if 코드 == 200 else None) or wid, recording=bool(rec),
                   recording_this=bool(rec and rec.get("work_id") == wid), **것)


@bp.post("/local/work/delete")
def delete_work():
    """{work_id} — 서버 먼저 지우고(실패하면 PC 는 그대로) 이 PC 의 기록 · 과제 파일을 지운다"""
    b = request.get_json(force=True, silent=True) or {}
    wid = b.get("work_id", "")
    if not _WID.match(wid):
        return jsonify(error="bad_request"), 400
    if 설정["bridge"]():
        return jsonify(error="recording", message=_기록중_말), 409
    코드, 답 = S._기록["server"]("DELETE", f"/works/{quote(wid, safe='')}")
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    if 코드 not in (200, 404):                                     # 404 = 서버엔 없는 과제 (이 PC 기록만) → PC 만 지움
        return jsonify(error="server", message=(답 or {}).get("message") or "서버에서 지우지 못했어요. 이 PC 기록은 그대로예요"), 502
    세션, 줄, 것 = _이PC_과제_지우기(wid)
    return jsonify(ok=True, sessions=len(세션), lines=줄, report_made=것["report_made"])


def _이PC_과제_지우기(wid):
    """이 PC 에서 과제 하나 — 기록 줄 · 과제 · 연결 확인 · 내보내기 파일 · 찾은 문서 · 기억. (세션들, 지운 줄 수, 지울 것)"""
    세션, 것 = _지울_것(wid)
    줄 = _이PC_기록_지우기(세션)
    for p in (_경로(wid), CF._경로(wid), EX._경로(wid)):
        safefile.remove(p)
    찾은 = os.path.join(S._기록["data_dir"](), "docs-found.json")
    목록 = safefile.read_json(찾은, {})
    if isinstance(목록, dict) and 목록.pop(wid, None):
        safefile.write_json(찾은, 목록, indent=1)
    for 기억 in (S._파일, S._연_이름):
        기억.pop(wid, None)
    return 세션, 줄, 것


@bp.post("/local/account/delete")
def delete_account():
    """설정 › 내 데이터 › 계정 지우기 (10/15) — {password} 또는 (구글 · 카카오로만) {confirm: "계정 삭제"}.
    서버 먼저(과제마다 과제 지우기와 같은 규칙 · 계정은 지운 시각만) → 서버가 지운 과제들의 이 PC 기록 → 로그아웃.
    서버가 실패하면 이 PC 는 그대로. 다른 계정 · 로그인 없이 만든 기록은 안 건드린다"""
    if 설정["bridge"]():
        return jsonify(error="recording", message="기록 중에는 계정을 지울 수 없어요. 기록 창에서 작업을 마친 뒤 해 주세요"), 409
    b = request.get_json(force=True, silent=True) or {}
    코드, 답 = S._기록["server"]("POST", "/me/delete", json={k: b[k] for k in ("password", "confirm") if isinstance(b.get(k), str)})
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    if 코드 in (400, 403):                                           # 비밀번호 틀림 · 확인 글 틀림 — 화면이 로그인으로 튀지 않게 400
        return jsonify(error=(답 or {}).get("error") or "bad_request", message=(답 or {}).get("message") or "확인이 맞지 않아요"), 400
    if 코드 != 200:
        return jsonify(error="server", message=(답 or {}).get("message") or "서버에서 지우지 못했어요. 이 PC 기록은 그대로예요"), 502
    과제, 줄 = 0, 0
    for wid in 답.get("works") or []:
        if _WID.match(str(wid)):
            _, n, _ = _이PC_과제_지우기(str(wid))
            과제, 줄 = 과제 + 1, 줄 + n
    safefile.remove(os.path.join(S._기록["data_dir"](), "auth.json"))   # 로그아웃 (서버는 이 계정의 토큰을 모두 지웠다)
    return jsonify(ok=True, works=과제, lines=줄)


def _내_기록(b):
    """{work_id, session_id} 검사 → (wid, sid, 오류)"""
    wid, sid = b.get("work_id", ""), b.get("session_id", "")
    if not _WID.match(wid) or not _WID.match(sid):
        return None, None, (jsonify(error="bad_request"), 400)
    if sid not in S._기록["sessions"]().get(wid, set()):
        return None, None, (jsonify(error="not_found", message="이 과제의 기록이 아니에요"), 404)
    if 설정["bridge"]():
        return None, None, (jsonify(error="recording", message=_기록중_말), 409)
    return wid, sid, None


@bp.post("/local/session/delete")
def delete_session():
    """{work_id, session_id} — 기록 하나만. 서버(내용 지움 · 지운 사실만) → 이 PC 줄. 내역서(PDF · 링크)는 그대로"""
    wid, sid, 오류 = _내_기록(request.get_json(force=True, silent=True) or {})
    if 오류:
        return 오류
    코드, 답 = S._기록["server"]("DELETE", f"/sessions/{quote(sid, safe='')}")
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    if 코드 not in (200, 404):
        return jsonify(error="server", message=(답 or {}).get("message") or "서버에서 지우지 못했어요. 이 PC 기록은 그대로예요"), 502
    return jsonify(ok=True, lines=_이PC_기록_지우기({sid}))


@bp.post("/local/session/move")
def move_session():
    """{work_id, session_id, to} — 다른 과제로 옮기기. 서버(확인값 그대로 따라감) → 이 PC 옮김 표"""
    b = request.get_json(force=True, silent=True) or {}
    wid, sid, 오류 = _내_기록(b)
    if 오류:
        return 오류
    to = b.get("to", "")
    if not _WID.match(to) or to == wid:
        return jsonify(error="bad_request", message="옮길 과제를 골라 주세요"), 400
    코드, 답 = S._기록["server"]("PATCH", f"/sessions/{quote(sid, safe='')}", json={"work_id": to})
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    if 코드 == 400:
        return jsonify(error="bad_request", message="내 과제로만 옮길 수 있어요"), 400
    if 코드 not in (200, 404):                                     # 404 = 서버에 안 올라간 기록 → 이 PC 에서만
        return jsonify(error="server", message=(답 or {}).get("message") or "서버에서 옮기지 못했어요"), 502
    _옮김_고치기(lambda m: m.__setitem__(sid, to))
    return jsonify(ok=True, to=to)


@bp.post("/local/record/start")
def record_start():
    wid = (request.get_json(force=True, silent=True) or {}).get("work_id") or ""
    if not _WID.match(wid):
        return jsonify(error="bad_request", message="과제가 올바르지 않습니다"), 400
    r = _기록_시작(wid)
    return (jsonify(r), 200) if r.get("ok") else (jsonify(r), 409)


def _기록_시작(wid):
    """기록 창(app/pill.py — 기록기 + 작은 창 · 화면 글자는 "기록 창", 코드 이름은 pill)을 이 과제로 켠다. 이미 기록 중이면 안 켬 (기록은 한 번에 하나)"""
    지금 = 설정["bridge"]()
    if 지금:
        return {"ok": False, "message": "이미 다른 기록이 켜져 있어요. 기록 창에서 작업을 마친 뒤 시작해 주세요"
                                       if 지금.get("work_id") != wid else "이미 이 과제를 기록하고 있어요"}
    # 콘솔 없는 파이썬(pythonw)으로 — python.exe 로 켜면 검은 터미널 창이 같이 뜨고, 그 창을 닫으면 기록 창도 꺼졌다 (10/13)
    # (venv 의 python.exe 는 진짜 파이썬을 자식으로 다시 켜는 껍데기라, DETACHED 로 켜도 자식이 새 콘솔을 받음)
    창용 = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if getattr(sys, "frozen", False):                            # 설치판 — Trace.exe record (창만 있는 exe 라 콘솔 없음)
        명령 = [sys.executable, "record", "--work", wid]
    else:
        명령 = [창용 if os.path.isfile(창용) else sys.executable, os.path.join(HERE, "pill.py"), "--work", wid]
    cfg = 설정.get("config")
    cfg = cfg() if callable(cfg) else cfg                       # 이 화면과 같은 설정 파일 → 같은 서버 · 같은 data 폴더
    if cfg:
        명령 += ["--config", cfg]
    로그 = open(os.path.join(S._기록["data_dir"](), "record-window.log"), "a", encoding="utf-8")   # 기록기 출력은 여기로 (문제 생기면 보는 곳)
    옵션 = {"cwd": ROOT, "stdin": subprocess.DEVNULL, "stdout": 로그, "stderr": subprocess.STDOUT}
    if sys.platform == "win32":                                  # 이 화면을 꺼도 기록 창은 계속 돌게 · 콘솔 창 없이
        옵션["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        옵션["start_new_session"] = True
    try:
        subprocess.Popen(명령, **옵션)
    except OSError as e:
        return {"ok": False, "message": f"기록 창을 켜지 못했어요 ({type(e).__name__})"}
    finally:
        로그.close()
    return {"ok": True, "message": "기록 창이 켜졌어요. 화면 오른쪽 아래를 보세요"}


# ─────────────── 제출 전 다듬기 — 출처 보기의 [다듬기] · [인용 달기] (10/31 · 캔버스 S-2 · 기획 v2.2) ───────────────
@bp.post("/local/refine")
def refine():
    """{work_id} → 이 과제 기록을 이어서 켜고(이미 이 과제를 기록 중이면 그대로) 출처 보기에서 연 결과물 Word 파일을 연다.
    다듬는 과정도 기록에 남게 — 기록 없이 고친 글은 "기록 밖에서 바뀐 글" 로 보인다. 다른 과제를 기록 중이면 409.
    파일 자리를 모르면(파일 고르는 창으로 고른 파일 · 화면엔 경로가 안 옴) 기록만 켜고 "파일을 열어 고쳐 주세요" """
    wid = (request.get_json(force=True, silent=True) or {}).get("work_id") or ""
    if not _WID.match(wid):
        return jsonify(error="bad_request", message="과제가 올바르지 않습니다"), 400
    지금 = 설정["bridge"]()
    if 지금 and 지금.get("work_id") != wid:
        return jsonify(error="recording", message="다른 과제를 기록하는 중이에요. 기록 창에서 작업을 마친 뒤 다듬어 주세요"), 409
    켬 = False
    if not 지금:
        r = 설정.get("start", _기록_시작)(wid)
        if not r.get("ok"):
            return jsonify(error="start", message=r["message"]), 409
        켬 = True
    p = _결과물_자리(wid)
    열림 = bool(p) and 설정.get("open_file", _파일_열기)(p)
    말 = ("기록을 켜고 Word 를 열었어요" if 켬 else "Word 를 열었어요") if 열림 else \
         ("기록을 켰어요. 결과물 파일을 열어 고쳐 주세요" if 켬 else "결과물 파일을 열어 고쳐 주세요")
    return jsonify(ok=True, started=켬, opened=열림, message=말 + " — 고친 뒤 저장하고 여기로 돌아오면 다시 읽어요")


def _결과물_자리(wid):
    """출처 보기에서 지금 연 결과물 파일의 PC 자리 — 기록된 자리에서 열었거나 내용으로 찾은 파일만 앎 (없으면 None)"""
    이름 = (S._파일.get(wid) or (S._연_이름.get(wid),))[0]          # 지금 화면에 연 파일 이름
    찾은 = S._찾은_목록().get(wid)
    if 찾은 and os.path.basename(찾은) == 이름 and os.path.isfile(찾은):
        return 찾은
    return next((d["path"] for d in S._문서_목록(wid) if d["name"] == 이름 and d["exists"]), None)


def _파일_열기(p):
    try:
        os.startfile(p)                                          # noqa: S606  윈도에서 그 파일의 기본 프로그램(Word)으로
        return True
    except (AttributeError, OSError):                            # 윈도가 아니거나 못 엶 → 기록만 켜고 직접 열라고
        return False


# ─────────────── 과제 상세 ───────────────
@bp.get("/local/work")
def detail():
    """{work:{id,title,ai_scope,course,due}, stage, report_made, go, recording, sessions:[…], docs:[{name, exists}]}
    sessions = 이 PC 기록 (새것부터): {id, start, end, active_sec, questions, pastes, pause_sec, recording, sealed}"""
    wid = request.args.get("work_id", "")
    if not _WID.match(wid):
        return jsonify(error="bad_request"), 400
    코드, w = S._기록["server"]("GET", f"/works/{quote(wid, safe='')}")
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    if 코드 == 404:
        return jsonify(error="not_found", message="내 과제 목록에 없는 과제예요"), 404
    봉인 = {s["id"]: s.get("sealed") for s in (w.get("sessions") or [])} if 코드 == 200 else {}
    m = meta(wid)
    rec = 설정["bridge"]()
    sessions = _기록_목록(wid, rec, 봉인)
    있나 = S._기록.get("statement_exists")
    단계 = CF.단계(wid) if sessions else "record"
    return jsonify(work={"id": wid, "title": w.get("title") or wid if 코드 == 200 else wid, "ai_scope": w.get("ai_scope") if 코드 == 200 else None,
                         "course": m.get("course", ""), "due": m.get("due", "")},
                   server_ok=코드 == 200, stage=단계, report_made=bool(sessions and 있나 and 있나(wid)),
                   go=f"{CF.STEPS[단계]}?work={quote(wid, safe='')}" if 단계 in CF.STEPS else None,
                   recording=rec if rec and rec.get("work_id") == wid else None, sessions=sessions,
                   docs=[{"name": d["name"], "exists": d["exists"]} for d in S._문서_목록(wid)])


def _기록_목록(wid, rec, 봉인):
    세션 = S._기록["sessions"]().get(wid, set())
    if not 세션:
        return []
    by = {s: {"id": s, "start": "", "end": "", "pastes": 0, "pause_sec": 0, "questions": 0, "_멈춤": None, "_마지막": ""} for s in 세션}
    for e in S._기록["jsonl"]("events-*.jsonl"):
        x = by.get(e.get("session_id"))
        if not x:
            continue
        t, ts = e.get("type"), e.get("ts", "")
        x["_마지막"] = max(x["_마지막"], ts)
        if t == "session_start":
            x["start"] = ts
        elif t == "session_end":
            x["end"] = ts
        elif t == "paste":
            x["pastes"] += 1
        elif t == "pause_start":
            x["_멈춤"] = ts
        elif t == "pause_end" and x["_멈춤"]:
            x["pause_sec"] += _초(x["_멈춤"], ts)
            x["_멈춤"] = None
    msgs = [m for m in S._기록["jsonl"]("ai-messages-*.jsonl") if m.get("session_id") in 세션]
    for m in M.latest_messages(msgs):
        if m.get("role") == "question":
            by[m["session_id"]]["questions"] += 1
    out = []
    for x in by.values():
        x.pop("_멈춤")
        마지막 = x.pop("_마지막")
        x["recording"] = bool(rec and rec.get("session_id") == x["id"])
        if not x["end"] and not x["recording"]:              # 끝 기록 없이 꺼진 기록 (PC 가 꺼짐 등) — 마지막 이벤트 시각까지
            x["end"] = 마지막
        끝 = x["end"] or (datetime.now().astimezone().isoformat(timespec="seconds") if x["recording"] else "")
        x["active_sec"] = max(0, _초(x["start"], 끝) - x["pause_sec"]) if x["start"] and 끝 else None
        x["sealed"] = 봉인.get(x["id"])
        out.append(x)
    return sorted(out, key=lambda x: x["start"], reverse=True)


def _초(a, b):
    try:
        return int((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds())
    except (TypeError, ValueError):
        return 0
