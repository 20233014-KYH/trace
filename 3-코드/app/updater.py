"""
updater.py — 앱 안에서 새 버전으로 바꾸기 (설치판 · 10/14)

왜: 맥은 애플 공증 전이라 내려받기 화면에서 새 dmg 를 받을 때마다 "'Trace'을(를) 열지 않음" 이 뜬다 (브라우저가 받은 파일엔
    '인터넷에서 받음' 표시가 붙고, 맥이 그 표시가 있는 처음 보는 앱을 막는다). 윈도우도 받을 때마다 "Windows의 PC 보호".
    → 처음 한 번만 그 길로 깔고, 그 뒤 새 버전은 Trace 가 직접 받아 바꾼다. 앱이 직접 받은 파일엔 그 표시가 없어서 다시 묻지 않는다.

  GET  /local/update            (statement.py) 새 버전이 있나 + can_install
  POST /local/update/install    받기 시작 (기록 중이면 거절 — 기록이 둘로 갈라지지 않게)
  GET  /local/update/progress   {state: idle | downloading | installing | error, pct, message}

  맥   : dmg 받기 → 열어서 Trace.app 을 내 폴더에 복사 → (이 앱이 끝나길 기다렸다가) 지금 Trace.app 자리에 바꿔 넣고 다시 연다
  윈도우: 설치 파일 받기 → (이 앱이 끝나길 기다렸다가) 조용히 설치(/VERYSILENT) → 다시 연다
바꾸는 일은 따로 띄운 작은 스크립트가 한다 — 앱이 자기 파일을 돌면서 덮어쓸 수 없어서.
"""
import os
import plistlib
import shutil
import subprocess
import sys
import threading

import requests
from flask import Blueprint, jsonify

from core import settings
from core.version import VERSION, parse as parse_version

bp = Blueprint("updater", __name__)
_상태 = {"state": "idle", "pct": 0, "message": ""}
_잠금 = threading.Lock()
기록_중 = lambda: False            # noqa: E731  statement.py 가 넣어 준다 (확장 다리 5077 이 열려 있나)


_최신 = {"at": 0.0, "d": None}


def 최신(새로=False):
    """인터넷 서버의 최신 설치판 {version, mac, windows, …} · 못 물으면 {}.
    10분 기억 — 화면을 옮길 때마다 묻지 않게. 이 앱(프로세스)이 기억하니 업데이트 뒤 새로 켠 앱은 새로 묻는다"""
    import time
    if not 새로 and _최신["d"] is not None and time.time() - _최신["at"] < 600:
        return _최신["d"]
    try:
        r = requests.get(settings.INTERNET + "/app/latest", timeout=15)
        d = r.json() if r.ok else {}
    except (requests.RequestException, ValueError):
        d = {}
    if d:
        _최신.update(at=time.time(), d=d)
    return d


def 내_파일(d):
    """이 OS 에 맞는 설치 파일 {name, url} · 없으면 None"""
    return (d.get("mac") if sys.platform == "darwin" else d.get("windows") if os.name == "nt" else None) or None


def 앱_자리():
    """지금 돌고 있는 설치판의 자리 — 맥 …/Trace.app · 윈도우 Trace.exe. 저장소에서 돌리면 None"""
    if not settings.FROZEN:
        return None
    exe = os.path.realpath(sys.executable)
    if sys.platform == "darwin":
        i = exe.find(".app/Contents/MacOS/")
        return exe[:i + 4] if i > 0 else None
    return exe


def 바꿀_수_있나(d):
    app = 앱_자리()
    if not app or not 내_파일(d):
        return False
    if sys.platform == "darwin" and "/AppTranslocation/" in app:      # dmg 창에서 바로 연 앱 — 바꿔 넣을 자리가 임시 폴더
        return False
    return os.access(os.path.dirname(app), os.W_OK)


def 요약(notes):
    """릴리스 글(packaging/notes/v….md) → 학생에게 보일 요약 {title, items, record, todo} (10/14)
    글의 첫 '---' 위만 학생용이고 아래는 개발 메모. 위쪽에서:
      첫 줄(- 로 시작 안 함) = 한 줄 소개 · "- …" = 바뀐 것 (6개까지)
      "기록:" 으로 시작하는 줄 = 기록하는 것이 바뀜 (화면이 따로 강조) · "할 일:" = 업데이트 뒤 할 일"""
    if not notes:
        return None
    줄 = [l.strip() for l in notes.split("\n---", 1)[0].splitlines() if l.strip()]
    out = {"title": 줄[0] if 줄 and not 줄[0].startswith("-") else "", "items": [], "record": "", "todo": ""}
    for l in 줄:
        if l.startswith(("기록:", "기록하는 것:")):
            out["record"] = l.split(":", 1)[1].strip()
        elif l.startswith(("할 일:", "업데이트 후:")):
            out["todo"] = l.split(":", 1)[1].strip()
        elif l.startswith("- ") and len(out["items"]) < 6:
            out["items"].append(l[2:].strip())
    return out


def _본_곳():
    return os.path.join(settings.app_data(), "update-seen.json")


def _본_버전():
    try:
        import json
        with open(_본_곳(), encoding="utf-8") as f:
            return json.load(f).get("version")
    except (OSError, ValueError):
        return None


def _봄(v):
    import json
    os.makedirs(os.path.dirname(_본_곳()), exist_ok=True)
    with open(_본_곳(), "w", encoding="utf-8") as f:
        json.dump({"version": v}, f)


@bp.get("/local/update/changes")
def changes():
    """업데이트 뒤 처음 열었나 → {just_updated, version, summary}. 처음 설치(본 버전 없음)는 그냥 지금 버전을 본 것으로"""
    본 = _본_버전()
    if 본 is None:
        _봄(VERSION)
        return jsonify(just_updated=False, version=VERSION)
    if 본 == VERSION:
        return jsonify(just_updated=False, version=VERSION)
    d = 최신()
    return jsonify(just_updated=True, version=VERSION, before=본,
                   summary=요약(d.get("notes")) if d.get("version") == VERSION else None)


@bp.post("/local/update/seen")
def seen():
    _봄(VERSION)
    return jsonify(ok=True)


@bp.post("/local/update/install")
def install():
    with _잠금:
        if _상태["state"] in ("downloading", "installing"):
            return jsonify(ok=True, **_상태)
        if 기록_중():
            return jsonify(error="recording", message="기록 중에는 업데이트할 수 없어요. 기록 창에서 작업을 마친 뒤 눌러 주세요"), 409
        d = 최신(새로=True)
        if not d.get("version") or parse_version(d["version"]) <= parse_version(VERSION):
            return jsonify(error="no_update", message="이미 최신 버전이에요"), 409
        if not 바꿀_수_있나(d):
            return jsonify(error="manual", message="이 Trace 는 직접 바꿀 수 없어요 — 내려받기 화면에서 받아 주세요",
                           download=settings.INTERNET.removesuffix("/api") + "/download"), 409
        _상태.update(state="downloading", pct=0, message=f"v{d['version']} 받는 중")
    threading.Thread(target=_진행, args=(d,), daemon=True, name="update").start()
    return jsonify(ok=True, **_상태)


@bp.get("/local/update/progress")
def progress():
    return jsonify(**_상태)


def _진행(d):
    try:
        f = 내_파일(d)
        곳 = os.path.join(settings.app_data(), "updates")
        shutil.rmtree(곳, ignore_errors=True)
        os.makedirs(곳)
        받은 = os.path.join(곳, f["name"])
        _받기(f["url"], 받은)
        _상태.update(state="installing", pct=100, message="바꿔 넣는 중 — 곧 다시 열려요")
        (_맥 if sys.platform == "darwin" else _윈도우)(받은, 곳)
        threading.Timer(1.0, lambda: os._exit(0)).start()         # 화면이 "다시 열려요" 를 받을 틈 · 끝나면 스크립트가 바꾸고 연다
    except Exception as e:                                         # noqa: BLE001
        _상태.update(state="error", message=f"업데이트하지 못했어요 ({type(e).__name__}: {str(e)[:120]}) — 내려받기 화면에서 받아 주세요")


def _받기(url, path):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        전체, 받음 = int(r.headers.get("Content-Length") or 0), 0
        with open(path, "wb") as out:
            for chunk in r.iter_content(1 << 16):
                out.write(chunk)
                받음 += len(chunk)
                if 전체:
                    _상태["pct"] = min(99, int(받음 * 100 / 전체))
    if 받음 < 1_000_000:
        raise IOError(f"받은 파일이 너무 작음 ({받음}B)")


def _맥(dmg, 곳):
    """dmg 를 열어 Trace.app 을 꺼내 두고, 이 앱이 끝나면 바꿔 넣을 스크립트를 띄운다"""
    r = subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", dmg], capture_output=True, check=True)
    mnt = next(e["mount-point"] for e in plistlib.loads(r.stdout)["system-entities"] if e.get("mount-point"))
    새 = os.path.join(곳, "Trace.app")
    try:
        subprocess.run(["ditto", os.path.join(mnt, "Trace.app"), 새], check=True)
    finally:
        subprocess.run(["hdiutil", "detach", "-quiet", mnt])
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", 새])                # 혹시 붙어 있으면 (앱이 받은 건 보통 없음)
    app = 앱_자리()
    sh = os.path.join(곳, "바꾸기.sh")
    with open(sh, "w", encoding="utf-8") as f:
        f.write(f'''#!/bin/bash
# Trace 업데이트 — 앱이 끝나길 기다렸다가 바꿔 넣고 다시 연다. 실패하면 옛 앱을 되돌린다
for i in $(seq 1 150); do kill -0 {os.getpid()} 2>/dev/null || break; sleep 0.2; done
OLD="{app}.옛-$$"
if mv "{app}" "$OLD" && ditto "{새}" "{app}"; then rm -rf "$OLD" "{새}"; else rm -rf "{app}"; mv "$OLD" "{app}"; fi
{'' if not os.environ.get("TRACE_UPDATE_NO_OPEN") else '# (시험) '}open "{app}"
''')
    os.chmod(sh, 0o755)
    subprocess.Popen(["/bin/bash", sh], start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=open(os.path.join(곳, "바꾸기.log"), "w"), stderr=subprocess.STDOUT)


def _윈도우(exe, 곳):
    """이 앱이 끝나면 설치 파일을 조용히 돌리고 다시 연다 (콘솔 없이 도는 cmd 라 timeout 대신 ping 으로 기다림)"""
    app = 앱_자리()
    cmd = os.path.join(곳, "바꾸기.cmd")
    with open(cmd, "w", encoding="utf-8") as f:
        f.write(f'''@echo off
chcp 65001 >nul
:wait
tasklist /FI "PID eq {os.getpid()}" | find "{os.getpid()}" >nul && (ping -n 2 127.0.0.1 >nul & goto wait)
"{exe}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS
start "" "{app}"
''')
    subprocess.Popen(["cmd", "/c", cmd], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
