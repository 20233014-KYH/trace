"""
platform_win.py — 윈도우에서 "지금 무슨 창?" "얼마나 쉬었나?"

맥용은 platform_mac.py. 두 파일은 이름이 같은 함수를 갖고 같은 모양의 답을 돌려준다.
collector.py 는 어느 쪽인지 신경 쓰지 않는다.

★ collector.py 안에 있던 foreground() / idle_seconds() 를 그대로 옮긴 것이다.
  동작은 한 글자도 바꾸지 않았다. 맥용을 끼워 넣을 자리를 만들려고 분리했을 뿐이다.

준비물 : pip install pywin32 psutil
"""
import psutil
import win32api
import win32gui
import win32process


def foreground() -> tuple[str, str]:
    """(exe 이름, 창 제목). 못 읽으면 ('?', '').

    윈도우는 권한 없이 창 제목까지 읽힌다 — domains.json 의 title_keywords 가 여기서 동작한다.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe = psutil.Process(pid).name() if pid else "?"
    except Exception:
        return "?", ""
    return exe, title


def idle_seconds() -> float:
    try:
        return (win32api.GetTickCount() - win32api.GetLastInputInfo()) / 1000.0
    except Exception:
        return 0.0


def input_permission_hint():
    """윈도우는 키를 세는 데 권한이 필요 없다."""
    return None
