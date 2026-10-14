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
from core import prefs, safefile, settings
from core.version import VERSION   # 설치판과 같은 버전 (10/14 · 전엔 "0.1.0 (개발판)" 을 적어 둬서 0.1.1 설치판에도 0.1.0 으로 보임)

HERE = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint("options", __name__)


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
            계정 = {"name": me.get("name"), "email": me.get("email"), "works": {w["id"]: w["title"] for w in me.get("works", [])},
                  "password": me.get("password", True), "google": bool(me.get("google"))}     # 로그인 방법 (10/15 · 옛 서버는 없음 → 비밀번호)
    return jsonify(prefs=prefs.load(S._기록["data_dir"]()), choices=prefs.CHOICES, checks=확인(),
                   account=계정 and {k: 계정[k] for k in ("name", "email", "password", "google")},
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


@bp.post("/local/settings/permission")
def ask_permission():
    """맥 (10/14): 권한을 맥에 정식으로 물어 시스템 설정 목록에 Trace 가 나타나게 하고, 그 설정 화면을 연다.
    묻기 전엔 목록에 Trace 가 없어서 학생이 켤 곳을 못 찾았다 ("+ 로 추가" 를 몰라서). kind = ax(손쉬운 사용) · keys(입력 모니터링)"""
    kind = (request.get_json(force=True, silent=True) or {}).get("kind")
    if sys.platform != "darwin" or kind not in _권한_화면:
        return jsonify(error="bad_request", message="맥에서만 쓰는 권한이에요"), 400
    import subprocess
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collector")
    if d not in sys.path:
        sys.path.insert(0, d)
    try:
        if kind == "ax":
            import mac_ax
            켜짐 = mac_ax.trusted()
            if not 켜짐:
                _권한_줄_지우기("Accessibility")
                mac_ax._물음["done"] = False
                켜짐 = mac_ax.trusted(ask=True)                  # 맥이 "손쉬운 사용 접근" 창을 띄우고 목록에 Trace 를 넣는다
        else:
            import platform_mac
            켜짐 = platform_mac._입력모니터링_켜졌나(요청=False)
            if not 켜짐:
                _권한_줄_지우기("ListenEvent")
                켜짐 = platform_mac._입력모니터링_켜졌나(요청=True)  # "키 입력 수신" 창 · 목록에 Trace
    except Exception:                                            # noqa: BLE001
        켜짐 = False
    if not 켜짐:
        subprocess.Popen(["open", _권한_화면[kind]])
    return jsonify(ok=True, granted=bool(켜짐))


def _권한_줄_지우기(서비스):
    """권한 목록에서 이 앱(Trace) 줄만 지운다 — 설치판에서 권한이 꺼져 있을 때만 (10/14).
    맥은 권한을 앱 서명으로 기억한다. 서명이 바뀐 앱(임시 서명 때의 업데이트 · 서명 방식을 바꾼 첫 업데이트)은 목록의 Trace 가
    켜져 있어 보여도 안 먹어서 학생이 끄고 다시 켜거나 − 로 지워야 했다. 지우고 다시 물으면 새 줄이 생겨 켜기만 하면 된다.
    다른 앱 줄은 건드리지 않는다 · 안 되면 그냥 둔다 (그때는 도움말대로 손으로)"""
    if not settings.FROZEN:
        return                                                   # 저장소에서 돌리면 권한 주인이 터미널 · VS Code 라 지우면 안 됨
    try:
        from Foundation import NSBundle
        앱 = str(NSBundle.mainBundle().bundleIdentifier() or "kr.trace.app")
    except Exception:                                            # noqa: BLE001
        앱 = "kr.trace.app"
    import subprocess
    try:
        subprocess.run(["tccutil", "reset", 서비스, 앱], capture_output=True, timeout=10)
    except Exception:                                            # noqa: BLE001
        pass


@bp.get("/local/settings/mac-permissions")
def mac_permissions():
    """맥 권한 두 가지가 켜져 있나 {ax, keys} — True · False · None(모름 · 맥 아님). 왼쪽 메뉴 알림용 (10/14 · 업데이트 뒤 꺼졌는지)"""
    if sys.platform != "darwin":
        return jsonify(ax=None, keys=None)
    d = os.path.join(os.path.dirname(HERE), "collector")
    if d not in sys.path:
        sys.path.insert(0, d)
    try:
        import mac_ax
        ax = mac_ax.trusted()
    except Exception:                                            # noqa: BLE001
        ax = None
    try:
        import platform_mac
        keys = platform_mac._입력모니터링_켜졌나(요청=False)
    except Exception:                                            # noqa: BLE001
        keys = None
    return jsonify(ax=ax, keys=keys)


_권한_화면 = {"ax": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
           "keys": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"}


@bp.post("/local/account/google/unlink")
def google_unlink():
    """설정 › 계정 › Google [끊기] (10/15) — 비밀번호가 있는 계정만 (서버가 막음)"""
    코드, 답 = S._기록["server"]("POST", "/auth/google/unlink", json={})
    return jsonify(답), 코드


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
    """[{key, name, desc, state: ok | missing | none | unknown, label, help?}] — 윈도우 · 맥에서 찾음"""
    if sys.platform == "darwin":
        return _맥_확인()
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


def _맥_확인():
    """맥 (10/14) — 같은 다섯 곳 + 앱 화면 읽기(손쉬운 사용) · 키 입력 횟수(입력 모니터링).
    데스크톱 AI 앱 대화 · 창 제목은 손쉬운 사용 권한으로 (desktop_ai_mac.py), Word · PowerPoint 는 AppleScript 로 (office_mac.py)"""
    home = os.path.expanduser("~")
    지원 = os.path.join(home, "Library", "Application Support")

    def 앱(이름):
        return any(os.path.isdir(os.path.join(d, 이름)) for d in ("/Applications", os.path.join(home, "Applications")))
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collector")
    if d not in sys.path:
        sys.path.insert(0, d)
    try:
        import mac_ax
        화면 = mac_ax.trusted()
    except Exception:                                            # noqa: BLE001
        화면 = None
    out = []
    for k, n, d_ in _목록:
        if k in ("chrome", "edge"):
            root = os.path.join(지원, *(("Google", "Chrome") if k == "chrome" else ("Microsoft Edge",)))
            st = ("none", "브라우저 없음") if not os.path.isdir(root) else ("ok", "연결됨") if _확장_있나(root) else ("missing", "없음")
        elif k in ("gptapp", "claudeapp"):
            if not 앱("ChatGPT.app" if k == "gptapp" else "Claude.app"):
                st = ("none", "설치 안 됨")
            else:
                st = ("ok", "찾음") if 화면 else ("missing", "권한 필요")
            d_ = "데스크톱 앱 대화와 복사 · 맥은 '손쉬운 사용' 권한"
        else:
            st, d_ = (("ok", "찾음") if 앱("Microsoft Word.app") else ("none", "설치 안 됨")), "과제 글이 바뀌는 과정 · 처음 한 번 'Word 제어' 허용"
        row = {"key": k, "name": n, "desc": d_, "state": st[0], "label": st[1]}
        if st[1] == "권한 필요":
            row["help"], row["perm"] = _화면_도움, "ax"
        out.append(row)
    out.append({"key": "ax", "name": "앱 화면 읽기", "desc": "데스크톱 AI 앱 대화 · 창 제목 — 맥은 '손쉬운 사용' 권한이 있어야 해요",
                "state": "ok" if 화면 else "unknown" if 화면 is None else "missing",
                "label": "켜짐" if 화면 else "확인 못 함" if 화면 is None else "꺼짐", "help": _화면_도움, "perm": "ax"})
    try:
        import platform_mac
        켜짐 = platform_mac._입력모니터링_켜졌나(요청=False)
    except Exception:                                            # noqa: BLE001
        켜짐 = None
    out.append({"key": "keys", "name": "키 입력 횟수", "desc": "몇 번 쳤는지만 셈 · 맥은 '입력 모니터링' 권한이 있어야 해요",
                "state": "ok" if 켜짐 else "unknown" if 켜짐 is None else "missing",
                "label": "켜짐" if 켜짐 else "확인 못 함" if 켜짐 is None else "꺼짐",
                "help": "[설정 열기] → 입력 모니터링 목록에서 Trace 켜기 → Trace 를 ⌘Q 로 껐다 다시 열기. "
                        "('손쉬운 사용' 과 다른 목록이에요. 안 켜도 창 · 복사 · AI 대화 기록은 남아요)", "perm": "keys"})
    return out


_화면_도움 = ("[설정 열기] → 손쉬운 사용 목록에서 Trace 켜기 (목록에 없으면 + 로 응용 프로그램의 Trace 추가) "
           "→ 기록 창을 껐다 다시 켜기. 화면낭독기와 같은 길로 AI 앱 글을 읽어요 — 화면을 찍지 않아요.")


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
