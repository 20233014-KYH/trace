"""
platform_mac.py — 맥에서 "지금 무슨 창?" "얼마나 쉬었나?"

윈도우용은 platform_win.py. 두 파일은 이름이 같은 함수를 갖고 같은 모양의 답을 돌려준다.

준비물 : pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz

★ 맥에서 못 하는 것 ★
  창 제목을 못 읽는다. 다른 앱의 창 제목을 보려면 '화면 기록' 권한이 필요한데
  그것까지 요구하면 부담이 커서 안 쓰기로 했다. 그래서 title 은 늘 "" 이다.
  결과적으로 domains.json 의 title_keywords 가 맥에서는 동작하지 않고,
  브라우저는 항상 other 로 떨어진다. 브라우저 탭 구분은 Tier 1 확장이 붙어야 한다.
"""
import ctypes
import ctypes.util

try:
    from AppKit import NSWorkspace
    from Foundation import NSDate, NSRunLoop
    from Quartz import (CGEventSourceSecondsSinceLastEventType,
                        kCGEventSourceStateCombinedSessionState)
except Exception:
    import os
    환경 = os.environ.get("CONDA_DEFAULT_ENV", "(모름)")
    raise SystemExit(
        "\n  " + "─" * 62 +
        "\n  맥용 준비물이 없습니다.\n" +
        (f"\n  지금 환경이 '{환경}' 입니다. 'trace' 여야 합니다."
         "\n  터미널을 껐다 켜면 (base) 로 돌아갑니다:\n\n      conda activate trace\n"
         if 환경 != "trace" else
         "\n      pip install -r 3-코드/requirements.txt") +
        "\n  " + "─" * 62 + "\n")

_모든입력 = 0xFFFFFFFF       # kCGAnyInputEventType
_들을_권한 = 1               # kIOHIDRequestTypeListenEvent
_허용됨 = 0                  # kIOHIDAccessTypeGranted


def foreground() -> tuple[str, str]:
    """(앱 이름, "") — 창 제목은 위 설명대로 읽지 않는다.

    ★ 런루프(run loop)를 한 번 돌려야 한다 ★
      맥은 "지금 이 앱이 활성이다" 같은 알림을 프로세스의 이벤트 큐에 쌓아둔다.
      런루프를 돌려 그 큐를 비우지 않으면, 물어봐도 갱신 전 값을 돌려준다.
      (우편함에 편지가 와 있는데 열어보지 않은 것과 같다)
      아래 NSRunLoop 한 줄이 그 큐를 처리하는 부분이다.
      이거 없이 만들었다가 창 이름이 한 박자씩 늦게 찍혔다.
    """
    try:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.05))
        for 앱 in NSWorkspace.sharedWorkspace().runningApplications():
            if 앱.isActive():
                return (앱.localizedName() or "?"), ""
    except Exception:
        pass
    return "?", ""


def idle_seconds() -> float:
    """마지막 입력 이후 몇 초 지났나. 권한이 필요 없다."""
    try:
        return float(CGEventSourceSecondsSinceLastEventType(
            kCGEventSourceStateCombinedSessionState, _모든입력))
    except Exception:
        return 0.0


def input_permission_hint():
    """키 세기(pynput)가 막혀 있으면 안내문, 괜찮으면 None.

    ★ 맥은 키 권한이 두 개로 나뉘어 있다 ★
      손쉬운 사용    컴퓨터를 '조작'해도 된다
      입력 모니터링  키 입력을 '들어도' 된다   ← 이쪽이 필요하다
      완전히 다른 목록이라, 손쉬운 사용만 켜면 키가 하나도 안 잡힌다.
    """
    if _입력모니터링_켜졌나():
        return None
    앱 = _지금_실행중인_앱() or "이 프로그램"
    return (
        "키 입력을 셀 수 없습니다 ('입력 모니터링' 권한이 꺼져 있습니다).\n"
        f"     시스템 설정 → 개인정보 보호 및 보안 → 입력 모니터링 → '{앱}' 켜기\n"
        f"     ★ 그다음 '{앱}' 을 ⌘Q 로 완전히 껐다 켜야 반영됩니다.\n"
        "     ('손쉬운 사용' 말고 '입력 모니터링' 입니다. 다른 목록입니다)\n"
        "     안 켜도 창·클립보드 기록은 정상으로 남습니다."
    )


def _입력모니터링_켜졌나():
    try:
        lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("IOKit"))
        lib.IOHIDCheckAccess.restype = ctypes.c_int
        lib.IOHIDCheckAccess.argtypes = [ctypes.c_int]
        if lib.IOHIDCheckAccess(_들을_권한) != _허용됨:
            lib.IOHIDRequestAccess.restype = ctypes.c_bool
            lib.IOHIDRequestAccess.argtypes = [ctypes.c_int]
            lib.IOHIDRequestAccess(_들을_권한)      # 설정 목록에 나타나게 정식 요청
        return lib.IOHIDCheckAccess(_들을_권한) == _허용됨
    except Exception:
        return False


def _지금_실행중인_앱():
    """★ 권한은 파이썬이 아니라 '파이썬을 켠 프로그램'에게 붙는다.
    터미널에서 켰으면 터미널, VS Code 안에서 켰으면 Code 가 받아야 한다.
    터미널에만 권한을 주고 다른 데서 돌리면 아무리 켜도 안 된다."""
    import os
    import subprocess
    pid = os.getpid()
    for _ in range(15):
        try:
            줄 = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                                capture_output=True, text=True, timeout=3).stdout.strip()
        except Exception:
            return None
        쪼갬 = 줄.split(None, 1)
        if len(쪼갬) < 2:
            return None
        부모, 경로 = 쪼갬
        if ".app/Contents/MacOS/" in 경로:
            return 경로.split(".app/")[0].split("/")[-1]
        try:
            pid = int(부모)
        except ValueError:
            return None
        if pid <= 1:
            return None
    return None
