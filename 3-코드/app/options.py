"""
options.py — 설정 화면 (캔버스 "Trace 화면 뼈대" 곁가지 · 설정 6칸 · 10/13 박상진)

  /settings?tab=record|window|report|account|data|app   왼쪽 작은 목록에서 칸 하나씩 (한 페이지에 한 칸)

  기록      기록할 곳(이 PC 에서 찾음: 크롬 · 엣지 확장 · ChatGPT · Claude 앱 · Word) · 이 PC 에 남는 것(늘 켜짐 · 끌 수 없음)
  기록 창   Word 열면 묻기(준비 중) · 시간 보이기 · 자리 · 쉬는 시간 · 윈도우 켤 때 켜기(준비 중)   → core/prefs → app/pill.py
  내역서 기본값  링크 기간 · 출처 보기 · 작업 과정 · 개인 정보 그 부분만 가리기 (10/13 모두 켬)   → core/prefs → app/export.py
  계정      이름(내역서 맨 위) 고치기 · 이메일 · 비밀번호 바꾸기 · 로그아웃   → 서버 PATCH /me · POST /auth/password
  내 데이터  이 PC 에 쌓인 기록 (모두 · 과제별) · 폴더 열기 · 계정 지우기(서버 API 없음 · 준비 중)
  앱 정보   버전 · 못 잡는 것

★ 서버 주소 · 로그인한 서버는 보이지 않음 (개발용은 로그인 화면 맨 아래) · 원문 기록은 끌 수 없음 (잠깐 멈춤이 그 역할)
★ 브라우저 확장 확인은 브라우저 설정 파일에서 "Trace" 확장이 깔렸는지만 본다 — 다른 내용은 읽지도 남기지도 않음
"""
import glob
import json
import os
import sys

from flask import Blueprint, jsonify, request, send_from_directory

import source as S
from core import prefs, safefile

HERE = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint("options", __name__)
VERSION = "0.1.0 (개발판)"         # 설치판(#53) 이 들어오면 core/version 으로


@bp.get("/settings")
def page():
    return send_from_directory(HERE, "settings.html")


@bp.get("/local/settings")
def read():
    a = S._기록["auth"]()
    계정 = None
    if a.get("token"):
        코드, me = S._기록["server"]("GET", "/me")
        if 코드 == 200:
            계정 = {"name": me.get("name"), "email": me.get("email"), "works": {w["id"]: w["title"] for w in me.get("works", [])}}
    return jsonify(prefs=prefs.load(S._기록["data_dir"]()), choices=prefs.CHOICES, checks=확인(),
                   account=계정 and {"name": 계정["name"], "email": 계정["email"]},
                   data=_데이터((계정 or {}).get("works", {})), version=VERSION)


@bp.post("/local/settings")
def write():
    b = request.get_json(force=True, silent=True) or {}
    if not isinstance(b, dict) or not b:
        return jsonify(error="bad_request", message="바꿀 것이 없어요"), 400
    cur, 오류 = prefs.save(S._기록["data_dir"](), b)
    if 오류:
        return jsonify(error="bad_request", message=오류), 400
    return jsonify(prefs=cur)


@bp.post("/local/settings/open-folder")
def open_folder():
    d = S._기록["data_dir"]()
    try:
        if sys.platform == "win32":
            os.startfile(d)                                   # noqa: S606  탐색기로 이 PC 기록 폴더
        else:
            import subprocess
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", d])
    except OSError as e:
        return jsonify(error="open_failed", message=f"폴더를 열지 못했어요 ({type(e).__name__})"), 500
    return jsonify(ok=True)


@bp.post("/local/account/name")
def rename():
    이름 = ((request.get_json(force=True, silent=True) or {}).get("name") or "").strip()
    if not 이름 or len(이름) > 40:
        return jsonify(error="bad_request", message="이름은 1~40자로 넣어 주세요"), 400
    코드, 답 = S._기록["server"]("PATCH", "/me", json={"name": 이름})
    if 코드 != 200:
        return jsonify(답), 코드
    경로 = os.path.join(S._기록["data_dir"](), "auth.json")      # 왼쪽 아래 내 이름도 바로 바뀌게
    with safefile.lock(경로):
        a = safefile.read_json(경로)
        if isinstance(a, dict):
            a.setdefault("user", {})["name"] = 이름
            safefile.write_json(경로, a)
    return jsonify(name=이름)


@bp.post("/local/account/password")
def password():
    b = request.get_json(force=True, silent=True) or {}
    if len(b.get("new_password") or "") < 8:
        return jsonify(error="bad_request", message="새 비밀번호는 8자 이상이어야 해요"), 400
    코드, 답 = S._기록["server"]("POST", "/auth/password", json={"password": b.get("password") or "", "new_password": b["new_password"]})
    if 코드 == 401 and 답.get("message") == "지금 비밀번호가 맞지 않습니다":
        return jsonify(error="wrong_password", message="지금 비밀번호가 맞지 않아요"), 400   # 401 이면 화면이 로그인으로 가 버려서
    return jsonify(답), 코드


# ─────────────── 이 PC 에 쌓인 기록 ───────────────
def _데이터(이름들):
    """{total, works:[{id, title, bytes, sessions}]} — 기록 파일의 줄을 과제별로 나눠 크기를 센다 (원문은 안 보냄)"""
    d = S._기록["data_dir"]()
    세션 = S._기록["sessions"]()
    과제 = {sid: wid for wid, ss in 세션.items() for sid in ss}
    크기, 모두 = {}, 0
    for p in glob.glob(os.path.join(d, "*")):
        if not os.path.isfile(p):
            continue
        n = os.path.getsize(p)
        모두 += n
        if p.endswith(".jsonl"):
            with open(p, encoding="utf-8") as f:
                for 줄 in f:
                    try:
                        wid = 과제.get(json.loads(줄).get("session_id"))
                    except ValueError:
                        continue
                    if wid:
                        크기[wid] = 크기.get(wid, 0) + len(줄.encode("utf-8"))
        else:
            for wid in 세션:                                       # confirm-W… · export-W… · work-W… (과제마다 고른 것)
                if os.path.basename(p).endswith(f"-{wid}.json"):
                    크기[wid] = 크기.get(wid, 0) + n
    works = [{"id": w, "title": 이름들.get(w) or w, "bytes": 크기.get(w, 0), "sessions": len(세션.get(w, ()))}
             for w in sorted(세션, key=lambda w: -크기.get(w, 0)) if w in 이름들]
    return {"total": 모두, "works": works, "other": len([w for w in 세션 if w not in 이름들])}


# ─────────────── 기록할 곳 (이 PC 에서 찾기) ───────────────
def 확인():
    """[{key, name, desc, state: ok | missing | none | unknown, label}] — 윈도우에서만 찾음"""
    if sys.platform != "win32":
        return [{"key": k, "name": n, "desc": d_, "state": "unknown", "label": "확인 못 함"} for k, n, d_ in _목록]
    lad, pf = os.environ.get("LOCALAPPDATA", ""), [os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")]
    out = []
    for k, n, d_ in _목록:
        if k in ("chrome", "edge"):
            root = os.path.join(lad, *(("Google", "Chrome") if k == "chrome" else ("Microsoft", "Edge")), "User Data")
            if not os.path.isdir(root):
                st = ("none", "브라우저 없음")
            else:
                st = ("ok", "연결됨") if _확장_있나(root) else ("missing", "없음")
        elif k == "gptapp":
            st = ("ok", "찾음") if glob.glob(os.path.join(lad, "Packages", "OpenAI.*")) else ("none", "설치 안 됨")
        elif k == "claudeapp":
            있음 = glob.glob(os.path.join(lad, "Packages", "Claude_*")) or os.path.isdir(os.path.join(lad, "AnthropicClaude"))
            st = ("ok", "찾음") if 있음 else ("none", "설치 안 됨")
        else:                                                    # Word
            있음 = any(glob.glob(os.path.join(p, "Microsoft Office", "root", "Office1*", "WINWORD.EXE")) for p in pf if p)
            st = ("ok", "찾음") if 있음 else ("none", "설치 안 됨")
        out.append({"key": k, "name": n, "desc": d_, "state": st[0], "label": st[1]})
    return out


_목록 = [("chrome", "Chrome 확장", "ChatGPT · Claude · Gemini 웹 대화"), ("edge", "Edge 확장", "Edge 에서 쓰는 AI 웹 대화"),
        ("gptapp", "ChatGPT 앱", "데스크톱 앱 대화와 복사"), ("claudeapp", "Claude 앱", "데스크톱 앱 대화와 복사"),
        ("word", "Word", "과제 글이 바뀌는 과정")]


def _확장_있나(root):
    """브라우저 프로필 설정에 이름이 "Trace" 인 확장이 깔려 있나 (켜져 있는지까지) — 설정 파일의 확장 목록만 본다"""
    for f in glob.glob(os.path.join(root, "*", "Secure Preferences")) + glob.glob(os.path.join(root, "*", "Preferences")):
        try:
            ext = ((json.load(open(f, encoding="utf-8")).get("extensions") or {}).get("settings") or {})
        except (OSError, ValueError):
            continue
        for v in ext.values():
            if not isinstance(v, dict) or v.get("state") == 0 or v.get("disable_reasons"):
                continue
            m = v.get("manifest") or {}
            if not m and v.get("path") and os.path.isfile(os.path.join(v["path"], "manifest.json")):
                try:
                    m = json.load(open(os.path.join(v["path"], "manifest.json"), encoding="utf-8"))
                except (OSError, ValueError):
                    m = {}
            if m.get("name") == "Trace":
                return True
    return False
