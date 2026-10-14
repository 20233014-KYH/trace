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
