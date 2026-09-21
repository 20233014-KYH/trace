"""
platform_win.py — 윈도우에서 "지금 무슨 창?" "얼마나 쉬었나?" "뭘 복사했나?"

맥용은 platform_mac.py 에 있다. 두 파일은 같은 이름의 함수를 갖고
같은 모양의 답을 돌려준다. collector.py 는 어느 쪽인지 신경 쓰지 않는다.

준비물 :  pip install pywin32 psutil

★ 원래 collector.py 안에 있던 foreground() / idle_seconds() 를 그대로 옮긴 것이다.
  동작은 바꾸지 않았다. 맥용을 끼워 넣을 자리를 만들려고 분리했을 뿐이다.
"""
import ctypes

try:
    import psutil
    import win32api
    import win32gui
    import win32process
except ImportError as e:
    raise SystemExit(
        f"\n  윈도우용 준비물이 없습니다: {e.name}\n"
        f"      pip install pywin32 psutil\n")


def foreground() -> tuple[str, str]:
    """(exe 이름, 창 제목). 못 읽으면 ('?', '').

    윈도우는 맥과 달리 권한 없이 창 제목까지 읽힌다.
    그래서 domains.json 의 title_keywords 가 여기서는 제대로 동작한다.
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
    """마지막 입력 이후 몇 초 지났나."""
    try:
        return (win32api.GetTickCount() - win32api.GetLastInputInfo()) / 1000.0
    except Exception:
        return 0.0


_user32 = ctypes.windll.user32
_user32.GetClipboardSequenceNumber.restype = ctypes.c_uint


def clipboard_serial():
    """클립보드가 바뀔 때마다 오르는 번호. ★ 내용은 전혀 읽지 않는다.

    이게 있으면 수집기가 1초마다 클립보드 '내용'을 읽지 않아도 된다.
    번호가 달라진 순간에만 읽으면 된다. (기획안 §11)
    """
    try:
        번호 = _user32.GetClipboardSequenceNumber()
        return 번호 or None
    except Exception:
        return None


def input_permission_hint():
    """윈도우는 키를 세는 데 권한이 필요 없다."""
    return None
