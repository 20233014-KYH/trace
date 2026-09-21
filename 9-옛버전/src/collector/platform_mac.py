"""
platform_mac.py — 맥에서 "지금 무슨 창?" "얼마나 쉬었나?" "뭘 복사했나?"

윈도우용은 platform_win.py 에 있다. 두 파일은 같은 이름의 함수를 갖고
같은 모양의 답을 돌려준다. collector.py 는 어느 쪽인지 신경 쓰지 않는다.

준비물 :  pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz
"""
import ctypes
import ctypes.util

try:
    from AppKit import NSWorkspace, NSPasteboard
    from Foundation import NSRunLoop, NSDate
    from Quartz import (
        CGEventSourceSecondsSinceLastEventType,
        kCGEventSourceStateCombinedSessionState,
    )
except Exception:
    import os
    환경 = os.environ.get("CONDA_DEFAULT_ENV", "(모름)")
    raise SystemExit(
        "\n  " + "─" * 62 +
        "\n  맥용 준비물이 없습니다.\n" +
        (f"\n  지금 환경이 '{환경}' 입니다. 'trace' 여야 합니다."
         "\n  터미널을 껐다 켜면 (base) 로 돌아갑니다:\n\n      conda activate trace\n"
         if 환경 != "trace" else
         "\n      pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz") +
        "\n  " + "─" * 62 + "\n")

# 애플이 정해둔 값
_모든입력 = 0xFFFFFFFF      # kCGAnyInputEventType
_들을_권한 = 1              # kIOHIDRequestTypeListenEvent
_허용됨 = 0                 # kIOHIDAccessTypeGranted


def foreground() -> tuple[str, str]:
    """(앱 이름, 창 제목). 못 읽으면 ('?', '').

    ★ 맥은 창 제목을 못 준다 ★
      다른 앱의 창 제목을 읽으려면 '화면 기록' 권한이 필요하다.
      그것까지 요구하면 부담이 크므로 앱 이름만 쓰고 제목은 빈 문자열로 둔다.
      그래서 맥에서는 domains.json 의 title_keywords 가 동작하지 않는다.
      브라우저 탭 구분은 Tier 1 확장이 붙어야 가능하다.

    ★ 우편함 이야기 ★
      맥은 "지금 이 앱이 활성이다" 같은 소식을 우리 프로그램의 우편함에 넣어둔다.
      열어보지 않으면 옛날 값을 돌려준다. 아래 NSRunLoop 한 줄이 우편함을 여는 것.
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


def clipboard_serial():
    """클립보드가 바뀔 때마다 오르는 번호. ★ 내용은 전혀 읽지 않는다.

    이게 있으면 수집기가 1초마다 클립보드 '내용'을 읽지 않아도 된다.
    번호가 달라진 순간에만 읽으면 된다. (기획안 §11)
    윈도우도 같은 걸 준다. 없는 운영체제면 None 을 돌려주면 된다.
    """
    try:
        return NSPasteboard.generalPasteboard().changeCount()
    except Exception:
        return None


def input_permission_hint():
    """키 세기(pynput)가 막혀 있으면 안내문, 괜찮으면 None."""
    if _입력모니터링_켜졌나():
        return None
    앱 = _지금_실행중인_앱() or "이 프로그램"
    return (
        "키 입력을 셀 수 없습니다 ('입력 모니터링' 권한이 꺼져 있습니다).\n"
        f"     시스템 설정 → 개인정보 보호 및 보안 → 입력 모니터링 → '{앱}' 켜기\n"
        f"     ★ 그다음 '{앱}' 을 ⌘Q 로 완전히 껐다 켜야 반영됩니다.\n"
        "     ('손쉬운 사용' 말고 '입력 모니터링' 입니다. 다른 목록입니다)\n"
        "     안 켜도 창·복사 기록은 정상으로 남습니다."
    )


# ── 아래는 안내문을 만들기 위한 보조 ──────────────────────────
def _입력모니터링_켜졌나():
    try:
        경로 = ctypes.util.find_library("IOKit")
        lib = ctypes.cdll.LoadLibrary(경로)
        lib.IOHIDCheckAccess.restype = ctypes.c_int
        lib.IOHIDCheckAccess.argtypes = [ctypes.c_int]
        if lib.IOHIDCheckAccess(_들을_권한) != _허용됨:
            lib.IOHIDRequestAccess.restype = ctypes.c_bool
            lib.IOHIDRequestAccess.argtypes = [ctypes.c_int]
            lib.IOHIDRequestAccess(_들을_권한)      # 목록에 나타나게 정식 요청
        return lib.IOHIDCheckAccess(_들을_권한) == _허용됨
    except Exception:
        return False


def _지금_실행중인_앱():
    """권한은 파이썬이 아니라 '파이썬을 켠 프로그램'에게 붙는다.
    터미널에서 켰으면 터미널, VS Code 안에서 켰으면 Code 가 받아야 한다."""
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
