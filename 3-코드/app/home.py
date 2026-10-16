"""
home.py — 홈 · 로그인 (캔버스 "Trace 화면 뼈대" 홈 A · 로그인 · 10/13 박상진)

  /        → 로그인했으면 /home, 아니면 /login
  /home    → 지금 상태(기록 중일 때만) · 문제 알림(있을 때만) · 내 과제 카드 (단계 · 짧은 숫자 · 다음 할 일 버튼)
  /login   → 로그인 · 가입 (서버 /api/auth/* 는 statement.py 의 /local/login · /local/signup 을 그대로 씀)

★ 홈은 점수·퍼센트 없이 개수만. 과제 카드 숫자는 출처 보기·내보내기와 같은 분석(export._모으기)에서 센다.
★ 기록 중인지는 기록기 다리(127.0.0.1:5077/status)에 묻는다. 멈춤·마치기는 지금은 알약에서만 (다리에 조종 길이 없음).
"""
import os
from datetime import datetime
from urllib.parse import quote

import requests
from flask import Blueprint, jsonify, redirect, request, send_from_directory

from core import match as M
import source as S
import confirm as CF
import export as EX
import work as WK
from core import prefs

HERE = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint("home", __name__)
BRIDGE = "http://127.0.0.1:5077/status"          # 기록기 다리 (collector/bridge.py)


def _로그인했나():
    return bool(S._기록["auth"]().get("token"))


@bp.get("/")
def root():
    return redirect("/home" if _로그인했나() else "/login")


@bp.get("/home")
def page():
    if not _로그인했나():
        return redirect("/login")
    if not prefs.load(S._기록["data_dir"]())["onboarded"]:      # 처음이면 준비 점검부터 (캔버스 0b · 한 번만)
        return redirect("/welcome")
    return send_from_directory(HERE, "home.html")


@bp.get("/welcome")
def welcome():
    """처음 한 번 — 무엇을 기록하나 → 기록 준비 점검 → 첫 과제 만들기 (설정 › 앱 정보 › 도움말에서 다시)"""
    if not _로그인했나():
        return redirect("/login")
    return send_from_directory(HERE, "welcome.html")


@bp.get("/login")
def login_page():
    return send_from_directory(HERE, "login.html")


def _기록기():
    """켜져 있으면 {work_id, paused, elapsed_sec, ai_count} · 꺼져 있으면 None
    먼저 0.1초만 문을 두드려 본다 — 꺼져 있을 때 윈도우가 연결을 다시 시도하는 0.6초를 매번 기다렸다 (10/15 · 홈 · 3초마다 확인)"""
    import socket
    from urllib.parse import urlsplit
    u = urlsplit(BRIDGE)
    with socket.socket() as s:
        s.settimeout(0.1)
        if s.connect_ex((u.hostname, u.port)) != 0:
            return None
    try:
        s = requests.get(BRIDGE, timeout=0.6).json()
    except (requests.RequestException, ValueError):
        return None
    if not s.get("recording"):
        return None
    return {k: s.get(k) for k in ("work_id", "session_id", "paused", "elapsed_sec", "ai_count")}


@bp.get("/local/recording")
def recording():
    """기록 창에서 끄거나 멈추면 앱 화면도 바로 바뀌게 — 화면이 몇 초마다 묻는 가벼운 상태 (서버 안 물음 · 10/14)"""
    r = _기록기()
    return jsonify(recording={k: r.get(k) for k in ("work_id", "session_id", "paused")} if r else None)


@bp.get("/local/home")
def home():
    """{user, recording, works:[{id, title, ai_scope, pc_sessions, last}], orphans, error?}
    과제 순서 = 기록 중인 과제 → 마지막으로 기록한 때가 최근인 것 (마감일은 서버에 아직 없음)"""
    a = S._기록["auth"]()
    if not a.get("token"):
        return jsonify(error="login", message="로그인이 필요합니다"), 401
    if request.args.get("cached"):                  # 마지막으로 받은 목록으로 바로 (서버 안 물음 · 10/15) — 화면이 먼저 그리고 새로 받아 바꿈
        답 = (S._기록.get("me_last") or (lambda t: None))(a.get("token"))
        if 답 is None:
            return jsonify(error="no_cache"), 404
        코드 = 200
    else:
        코드, 답 = S._기록["server"]("GET", "/me")
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    pc = S._기록["sessions"]()
    마지막 = {}
    for e in S._기록["jsonl"]("events-*.jsonl"):
        if e.get("type") == "session_start" and e.get("work_id"):
            마지막[e["work_id"]] = max(마지막.get(e["work_id"], ""), e.get("ts", ""))
    rec = _기록기()
    works = 답.get("works", []) if 코드 == 200 else []
    내것 = {w["id"] for w in works}
    out = []
    for w in works:
        m = WK.meta(w["id"])
        out.append({"id": w["id"], "title": w.get("title") or w["id"], "ai_scope": w.get("ai_scope"),
                    "course": m.get("course", ""), "due": m.get("due", ""),
                    "pc_sessions": len(pc.get(w["id"], ())), "last": 마지막.get(w["id"], "") or m.get("created_at", "")})
    # 마감 순 (캔버스 "마감 순") — 기록 중 → 마감이 남은 것(가까운 순) → 마감 없는 것(최근 기록 순) → 마감 지난 것
    오늘 = datetime.now().strftime("%Y-%m-%d")
    out.sort(key=lambda w: w["last"], reverse=True)
    out.sort(key=lambda w: (not (rec and rec["work_id"] == w["id"]),
                            0 if w["due"] and w["due"][:10] >= 오늘 else 1 if not w["due"] else 2,
                            w["due"] if w["due"] and w["due"][:10] >= 오늘 else ""))
    나 = {**(a.get("user") or {}), **{k: 답[k] for k in ("name", "email") if 코드 == 200 and 답.get(k)}}   # 이메일은 프로필 칸에 (10/15)
    return jsonify(user=나, recording=rec, works=out,
                   orphans=[{"id": k, "pc_sessions": len(v)} for k, v in sorted(pc.items()) if k not in 내것],
                   error=None if 코드 == 200 else (답.get("message") or "서버에서 과제 목록을 받지 못했습니다"))


@bp.get("/local/home/card")
def card():
    """과제 카드 하나 — {stage, report_made, shared, facts:{questions, answers, linked} | null}
    카드마다 따로 부른다 (서버 확인·문서 분석이 과제마다 걸려서 홈을 먼저 그리고 채운다)"""
    wid = request.args.get("work_id", "")
    if not wid:
        return jsonify(error="bad_request"), 400
    있나 = S._기록.get("statement_exists")
    단계 = CF.단계(wid)
    made = (EX._읽기(wid).get("made") or {})
    shared = made.get("url") and made.get("expires_at", "") > datetime.now().astimezone().isoformat()
    질문 = _질문_수(wid)
    facts = {"questions": 질문, "answers": None, "linked": None}
    r = EX._모으기(wid) if S.문서_준비(wid) else None
    if isinstance(r, dict):                                         # 내역서 PDF 와 같은 셈 — 학생이 확인한 연결만 (붙여넣기 기록은 자동)
        facts.update(questions=len(r["questions"]), answers=len({l["answer_id"] for l in r["confirmed"]}),
                     linked=len(r["confirmed"]))
    return jsonify(stage=단계, report_made=bool(있나 and 있나(wid)), shared=bool(shared),
                   expires_at=made.get("expires_at") if shared else None, facts=facts,
                   go=f"{CF.STEPS[단계]}?work={quote(wid, safe='')}")


def _질문_수(wid):
    """이 PC 에 남은 이 과제의 AI 질문 수 (같은 질문이 두 번 저장된 것은 하나로)"""
    세션 = S._기록["sessions"]().get(wid, set())
    if not 세션:
        return 0
    msgs = [m for m in S._기록["jsonl"]("ai-messages-*.jsonl") if m.get("session_id") in 세션]
    return sum(1 for m in M.latest_messages(msgs) if m.get("role") == "question")
