"""
trace_app.py — 설치판 입구 (Trace.exe · v0.1 · 10/13)

  Trace.exe              내역서 화면 (app/statement.py) 을 앱 창으로 — 로그인 · 과제 · 내역서 · 기록 시작 버튼
  Trace.exe record       알약 + 기록기 (app/pill.py) — 시작 메뉴 "Trace 기록 시작"
  Trace.exe --selftest   묶인 것이 다 열리는지 시험 (빌드가 부른다) → 결과를 화면과 파일에

★ 우리 코드는 묶지 않고 원본 .py 를 그대로 싣는다 (_internal/trace/app · collector · core · server/statement_pdf.py) ★
  각 파일이 자기 위치(__file__)로 html · config.json · 글꼴을 찾기 때문 — 저장소에서 돌릴 때와 똑같이 돈다.
  그래서 여기서는 스크립트를 runpy 로 "python app/statement.py" 처럼 돌리기만 한다.
  필요한 라이브러리(flask · pywebview · pynput …)는 trace.spec 이 우리 코드의 import 를 읽어 함께 묶는다.

저장소에서도 그대로 돈다:  python 3-코드/packaging/trace_app.py [record | --selftest]
"""
import os
import runpy
import socket
import sys
import threading
import time
import traceback

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = (os.path.join(sys._MEIPASS, "trace") if FROZEN                      # noqa: SLF001  PyInstaller 가 푼 곳
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 3-코드
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True        # 설치 폴더에 __pycache__ 를 만들지 않는다

from core import settings             # noqa: E402
from core.version import VERSION      # noqa: E402

STATEMENT = os.path.join(ROOT, "app", "statement.py")
PILL = os.path.join(ROOT, "app", "pill.py")
HOME_PORT = 5079                      # app/statement.py 의 PORT
BRIDGE_PORT = 5077                    # collector/bridge.py — 기록기가 켜져 있으면 열려 있다


def _log(name):
    """창만 있는 exe 는 print 할 곳이 없다 (sys.stdout = None) → 내 폴더 logs/ 에 남긴다. 2MB 넘으면 새로."""
    d = os.path.join(settings.app_data(), "logs")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{name}.log")
    if os.path.exists(p) and os.path.getsize(p) > 2_000_000:
        os.replace(p, p + ".old")
    f = open(p, "a", encoding="utf-8", buffering=1)  # noqa: SIM115  프로세스가 끝날 때까지 연다
    f.write(f"\n── Trace {VERSION}  {time.strftime('%Y-%m-%d %H:%M:%S')}  {' '.join(sys.argv[1:])}\n")
    sys.stdout = sys.stderr = f
    return p


def _열림(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _돌리기(path, *args):
    """python <path> <args> 와 같게 — 스크립트 폴더가 sys.path 맨 앞, __main__ 으로."""
    sys.argv = [path, *args]
    sys.path.insert(0, os.path.dirname(path))
    runpy.run_path(path, run_name="__main__")


def _알림(text):
    """작은 알림 창 (윈도우) — 없으면 로그에만"""
    print(text)
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, "Trace", 0x40)


def home():
    """내역서 화면을 앱 창으로. 창을 닫으면 끝난다. 이미 켜져 있으면(다른 창) 창만 하나 더."""
    주소 = f"http://127.0.0.1:{HOME_PORT}/"
    if not _열림(HOME_PORT):
        threading.Thread(target=_돌리기, args=(STATEMENT, "--no-browser", "--port", str(HOME_PORT)),
                         daemon=True, name="statement").start()
        for _ in range(100):                          # 10초
            if _열림(HOME_PORT):
                break
            time.sleep(0.1)
    try:
        import webview
        if os.name == "nt":                           # 작업 표시줄에 Trace 로 따로 묶여 앱 아이콘이 보이게 (10/13)
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Trace.App")
        창 = webview.create_window(f"Trace {VERSION}", 주소, width=1280, height=820, min_size=(1024, 640))
        webview.start(_아이콘, 창)
    except Exception:                                 # WebView2 가 없거나 창을 못 띄우면 브라우저로
        traceback.print_exc()
        import webbrowser
        webbrowser.open(주소)
        while True:                                   # 브라우저 탭이 쓰는 동안 화면 서버를 살려 둔다
            time.sleep(3600)
    os._exit(0)                                       # 화면 서버 스레드까지 같이 끝낸다


def _아이콘(창):
    """앱 창 아이콘 = app/trace.ico (WinForms) — 못 하면 그냥 둔다"""
    try:
        from webview.platforms.winforms import BrowserView
        from System import Action
        from System.Drawing import Icon
        for _ in range(50):
            form = BrowserView.instances.get(창.uid)
            if form:
                break
            time.sleep(0.1)
        form.Invoke(Action(lambda: setattr(form, "Icon", Icon(os.path.join(ROOT, "app", "trace.ico")))))
    except Exception:                                 # noqa: BLE001
        pass


def record(args=()):
    """알약 + 기록기. 이미 기록 중이면 하나 더 켜지 않는다 (기록이 둘로 갈라진다). args = --config 등 pill.py 에 그대로"""
    if _열림(BRIDGE_PORT):
        _알림("이미 기록 중입니다. 화면 구석의 기록 창을 확인해 주세요.")
        return
    _돌리기(PILL, *args)


def selftest():
    """묶인 것이 다 열리는지. 빌드(packaging/build.py)가 부르고, 학생 PC 에서 문제가 생기면 로그로 받아 본다."""
    결과, 실패 = [], 0

    def 검사(이름, f):
        nonlocal 실패
        try:
            덧 = f()
            결과.append(f"✓ {이름}" + (f"  {덧}" if 덧 else ""))
        except Exception as e:                        # noqa: BLE001
            실패 += 1
            결과.append(f"✗ {이름}  {type(e).__name__}: {e}")

    import importlib
    for d in ("app", "collector"):
        sys.path.insert(0, os.path.join(ROOT, d))
    검사("버전", lambda: VERSION)

    def 원본():
        빠짐 = [p for p in ("app/statement.html", "app/pill.html", "app/shell.css", "app/home.html", "app/login.html",
                          "app/settings.html", "app/review.html", "app/work.css", "app/work.js", "app/trace.ico", "collector/config.json",
                          "collector/domains.json", "server/demo_share.json")
              if not os.path.exists(os.path.join(ROOT, p))]
        if 빠짐:
            raise FileNotFoundError(", ".join(빠짐))
    검사("원본 파일", 원본)
    for m in ("flask", "requests", "pyperclip", "watchdog.observers", "reportlab.platypus", "webview"):
        검사(f"라이브러리 {m}", lambda m=m: importlib.import_module(m) and None)
    if os.name == "nt":
        for m in ("win32api", "win32gui", "win32process", "win32com.client", "pythoncom", "psutil", "comtypes.client",
                  "pynput.keyboard", "pynput.mouse", "clr", "webview.platforms.winforms"):
            검사(f"윈도우 {m}", lambda m=m: importlib.import_module(m) and None)
        for m in ("platform_win", "keys", "office", "desktop_ai"):
            검사(f"기록기 {m}", lambda m=m: importlib.import_module(m) and None)
    for m in ("collector", "bridge", "file_watch", "mask", "classify"):
        검사(f"기록기 {m}", lambda m=m: importlib.import_module(m) and None)

    def 화면():
        g = runpy.run_path(STATEMENT, run_name="trace_selftest")      # main() 은 안 돈다
        import tempfile
        g["설정"].update(server=settings.LOCAL, data_dir=tempfile.mkdtemp(prefix="trace-selftest-"))   # main() 이 채우는 것 (로그인 안 한 빈 폴더)
        c = g["app"].test_client()
        h = {"Host": f"127.0.0.1:{HOME_PORT}"}
        assert c.get("/", headers=h).status_code == 302                     # 로그인 → 홈 (10/13 · #54)
        for 주소, 글 in (("/login", "로그인"), ("/make", "내역서")):
            r = c.get(주소, headers=h)
            assert r.status_code == 200 and 글 in r.get_data(as_text=True), (주소, r.status_code)
        return f"{len(g['app'].url_map._rules)}개 경로"                 # noqa: SLF001
    검사("내역서 화면", 화면)

    def pdf():
        sys.path.insert(0, os.path.join(ROOT, "server"))
        import json
        import statement_pdf
        with open(os.path.join(ROOT, "server", "demo_share.json"), encoding="utf-8") as f:
            d = json.load(f)
        b = statement_pdf.render(d, "https://trace-server-8aa0.onrender.com/s/demo")
        assert b[:4] == b"%PDF"
        return f"{len(b) // 1024}KB"
    검사("내역서 PDF (글꼴)", pdf)

    글 = f"Trace {VERSION} 자체 시험 — {len(결과) - 실패}개 통과, {실패}개 실패\n" + "\n".join(결과)
    print(글)
    out = os.path.join(settings.app_data(), "selftest.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(글 + "\n")
    return 1 if 실패 else 0


def main():
    인자 = sys.argv[1:]
    모드 = "selftest" if "--selftest" in 인자 else "record" if "record" in 인자 else "home"
    if FROZEN or sys.stdout is None:
        _log(모드)
    if FROZEN and 모드 != "selftest":
        print("내 설정", settings.first_run())
    try:
        if 모드 == "selftest":
            sys.exit(selftest())
        record([a for a in 인자 if a != "record"]) if 모드 == "record" else home()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        _알림("Trace 를 여는 중에 문제가 생겼습니다.\n" + os.path.join(settings.app_data(), "logs") + " 의 로그를 보내 주세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
