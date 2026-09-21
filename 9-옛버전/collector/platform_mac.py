# =============================================
# 맥에서 "지금 무슨 프로그램?" 과 "뭔가 복사했나?" 를 알아내는 파일
#
# 윈도우용은 platform_win.py 에 따로 있다.
# 두 파일은 이름이 같은 함수를 갖고, 같은 모양의 답을 돌려준다.
# 그래서 collector.py 는 맥인지 윈도우인지 신경 쓰지 않아도 된다.
# =============================================

import ctypes
import ctypes.util
import hashlib

def _환경_안내(모자란것):
    """왜 안 되는지와 무엇을 치면 되는지 알려준다. 에러 더미 대신."""
    import os
    지금환경 = os.environ.get("CONDA_DEFAULT_ENV", "(모름)")
    줄 = []
    줄.append("")
    줄.append("  " + "─" * 62)
    줄.append(f"  준비물이 없습니다: {모자란것}")
    줄.append("")
    if 지금환경 != "trace":
        줄.append(f"  지금 환경이 '{지금환경}' 입니다. 'trace' 여야 합니다.")
        줄.append("  터미널을 껐다 켜면 항상 (base) 로 돌아갑니다. 매번 켜 주세요:")
        줄.append("")
        줄.append("      conda activate trace")
        줄.append("")
        줄.append("  프롬프트 맨 앞이 (trace) 로 바뀌면 된 것입니다.")
    else:
        줄.append("  환경은 맞는데 준비물이 빠졌습니다:")
        줄.append("")
        줄.append("      pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz")
    줄.append("  " + "─" * 62)
    줄.append("")
    return "\n".join(줄)


try:
    from AppKit import (
        NSWorkspace, NSPasteboard, NSPasteboardTypeString,
        NSApplication, NSEvent, NSEventMaskKeyDown, NSEventModifierFlagCommand,
    )
    from Foundation import NSRunLoop, NSDate
except Exception:
    # 에러 더미를 쏟아내는 대신, 뭘 치면 되는지 알려주고 끝낸다.
    raise SystemExit(_환경_안내("맥용 도구 (pyobjc)"))


def active_app():
    """지금 맨 앞에 떠 있는 프로그램의 이름을 돌려준다.

    돌려주는 모양 (윈도우용도 똑같아야 한다) :
        {"app": "Google Chrome", "title": None}


    ★ 우편함 이야기 — 이 함수가 두 줄짜리가 아닌 이유 ★

    맥은 "지금 어떤 프로그램이 활성이다" 같은 소식을 우리 프로그램의
    우편함에 넣어 둔다. 그런데 우리가 우편함을 열어보지 않으면,
    맥에게 물어봐도 예전에 받아둔 옛날 소식을 그대로 돌려준다.

    그래서 창을 바꿔도 한 박자 늦게 따라오는 일이 생긴다.
    (직접 겪었다. 창을 바꿔도 직전 프로그램 이름이 계속 찍혔다)

    아래 NSRunLoop... 한 줄이 "우편함을 잠깐 열어본다"는 뜻이다.


    title(창 제목)이 None 인 이유 :
        맥은 다른 프로그램의 창 제목을 읽으려면 '화면 기록' 권한이 필요하다.
        1단계에서는 프로그램 이름만으로 충분하므로 None 을 넣는다.
    """
    NSRunLoop.currentRunLoop().runUntilDate_(
        NSDate.dateWithTimeIntervalSinceNow_(0.05)
    )

    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.isActive():
            return {"app": app.localizedName(), "title": None}

    return {"app": None, "title": None}


# ---------------------------------------------
# 복사(클립보드) 관련 함수 두 개
#
# 왜 두 개로 나눴나 :
#   1초마다 클립보드 "내용"을 읽으면 남의 비밀번호까지 계속 들여다보는 셈이다.
#   그래서 평소에는 번호만 본다. 번호가 바뀌었을 때만 길이를 잰다.
#   이게 기획안 4.3 "내용을 읽지 않는다" 원칙을 코드로 지키는 방법이다.
# ---------------------------------------------
def clipboard_serial():
    """클립보드가 바뀔 때마다 1씩 오르는 번호를 돌려준다.

    내용은 전혀 읽지 않는다. 번호만 본다.
    (윈도우에도 똑같은 번호가 있다 — GetClipboardSequenceNumber)
    """
    return NSPasteboard.generalPasteboard().changeCount()


def clipboard_digest():
    """지금 클립보드의 '길이'와 '지문'만 돌려준다. 내용은 돌려주지 않는다.

    돌려주는 모양 :
        {"length": 240, "hash": "a3f9c2d1..."}
        글자가 아니면 (사진 등)  {"length": None, "hash": None}

    지문(해시)이란 :
        아무리 긴 글이라도 넣으면 64자리 암호 같은 값이 나온다.
        같은 글은 언제나 같은 값, 한 글자만 달라도 완전히 다른 값이 나온다.
        그래서 "AI 탭에서 복사한 것"과 "워드에 붙여넣은 것"이 같은지를
        내용을 보지 않고도 비교할 수 있다.
    """
    text = NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)

    if text is None:                       # 사진·파일 등 글자가 아닌 것
        return {"length": None, "hash": None}

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {"length": len(text), "hash": digest}



# =============================================
# 붙여넣기 감지
#
# 왜 따로 만드나 — 복사는 클립보드를 바꾸지만
# 붙여넣기는 아무것도 바꾸지 않는다. 그래서 클립보드를 아무리 들여다봐도
# 못 잡는다. 키를 누르는 것(⌘V)을 직접 봐야 한다.
#
# ★ 솔직하게 적어 둔다 ★
#   맥은 "V 키만 알려줘" 같은 주문을 받아주지 않는다.
#   그래서 어떤 키를 누르든 우리 프로그램에 소식이 온다.
#   아래 _키를_눌렀을때() 가 하는 일은 딱 두 줄이다 —
#   ⌘V 인지 보고, 맞으면 숫자를 1 올린다. 아니면 그냥 버린다.
#   무슨 글자를 쳤는지는 세지도, 적지도, 저장하지도 않는다.
#
# 이 기능은 '손쉬운 사용' 권한이 있어야 돌아간다.
# 권한이 없으면 붙여넣기만 못 볼 뿐, 나머지 기록은 정상이다.
# =============================================

_붙여넣기_횟수 = 0
_감시자 = None          # 이 변수를 남겨둬야 한다. 안 그러면 파이썬이 감시자를 치워버린다.
_탭 = None
_탭_소스 = None
_쓰는_방식 = None        # "tap" 또는 "global"

V_키 = 9                # 맥에서 V 자리의 번호 (자판이 한글이어도 같다)


# ★ 맥은 키를 보는 권한이 두 개로 나뉘어 있다 ★
#
#   손쉬운 사용     컴퓨터를 '조작'해도 된다   (마우스를 움직이고 클릭하고)
#   입력 모니터링   키 입력을 '들어도' 된다    ← 붙여넣기는 이쪽이 필요하다
#
# 완전히 다른 목록이다. 손쉬운 사용만 켜면 붙여넣기는 안 잡힌다.
# (실제로 이것 때문에 한참 헤맸다)

들을_권한 = 1          # kIOHIDRequestTypeListenEvent
허용됨 = 0             # kIOHIDAccessTypeGranted


def 지금_실행중인_앱():
    """이 파이썬을 켠 '프로그램'이 무엇인지 찾는다.

    ★ 왜 필요한가 ★
      맥 권한은 파이썬이 아니라 '파이썬을 켠 프로그램'에게 붙는다.
      터미널에서 켰으면 터미널이, Claude 안에서 켰으면 Claude 가 받아야 한다.
      터미널에만 권한을 주고 Claude 안에서 돌리면 아무리 켜도 안 된다.
      (실제로 이것 때문에 한참 헤맸다)

    부모의 부모의 부모… 를 거슬러 올라가며 .app 을 찾는다.
    돌려주는 모양: ("터미널", "/System/.../Terminal") 또는 (None, None)
    """
    import os
    import subprocess

    pid = os.getpid()
    for _ in range(15):
        try:
            결과 = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                                  capture_output=True, text=True, timeout=3)
        except Exception:
            return None, None
        줄 = 결과.stdout.strip()
        if not 줄:
            return None, None
        쪼갬 = 줄.split(None, 1)
        if len(쪼갬) < 2:
            return None, None
        부모, 실행경로 = 쪼갬
        if ".app/Contents/MacOS/" in 실행경로:
            이름 = 실행경로.split(".app/")[0].split("/")[-1]
            return 이름, 실행경로
        try:
            pid = int(부모)
        except ValueError:
            return None, None
        if pid <= 1:
            return None, None
    return None, None


def 손쉬운사용_켜졌나():
    """'손쉬운 사용' 목록에 들어 있나."""
    try:
        경로 = ctypes.util.find_library("ApplicationServices")
        라이브러리 = ctypes.cdll.LoadLibrary(경로)
        라이브러리.AXIsProcessTrusted.restype = ctypes.c_bool
        라이브러리.AXIsProcessTrusted.argtypes = []
        return bool(라이브러리.AXIsProcessTrusted())
    except Exception:
        return False


def _iokit():
    경로 = ctypes.util.find_library("IOKit")
    라이브러리 = ctypes.cdll.LoadLibrary(경로)
    라이브러리.IOHIDCheckAccess.restype = ctypes.c_int
    라이브러리.IOHIDCheckAccess.argtypes = [ctypes.c_int]
    라이브러리.IOHIDRequestAccess.restype = ctypes.c_bool
    라이브러리.IOHIDRequestAccess.argtypes = [ctypes.c_int]
    return 라이브러리


def 입력모니터링_켜졌나():
    """'입력 모니터링' 목록에 들어 있고 켜져 있나."""
    try:
        return _iokit().IOHIDCheckAccess(들을_권한) == 허용됨
    except Exception:
        return False


def 입력모니터링_요청():
    """맥에게 정식으로 요청한다.

    처음이면 허락을 묻는 창이 뜬다.
    한 번 거부한 적이 있으면 창은 안 뜨지만, 대신 시스템 설정의
    '입력 모니터링' 목록에 그 프로그램이 추가되어 직접 켤 수 있게 된다.
    """
    try:
        return bool(_iokit().IOHIDRequestAccess(들을_권한))
    except Exception:
        return False


def 권한_있나():
    """붙여넣기를 잡을 가망이 있나. 둘 중 하나라도 있으면 일단 시도해 본다."""
    return 입력모니터링_켜졌나() or 손쉬운사용_켜졌나()


# ---------------------------------------------
# 방식 ① 이벤트 탭 — 좋은 방식
#
# ★ 왜 이걸 쓰나 ★
#   원래 addGlobalMonitor 를 썼는데, 이름 그대로 '글로벌(다른 앱)' 전용이다.
#   내 앱에 간 키는 안 준다. 수집기는 터미널의 자식이므로 터미널이 내 앱이고,
#   터미널 안에서 누른 ⌘V 는 통째로 안 보였다. (여기서 또 헤맸다)
#
#   이벤트 탭은 화면 전체의 키를 본다. 내 앱이든 남의 앱이든 다 잡힌다.
#
# ★ ListenOnly 로 만든다 ★
#   '듣기만 하고 건드리지 않는다'는 뜻이다. 키를 가로채지 않으므로
#   우리 프로그램이 버벅여도 남의 키 입력이 느려지지 않는다.
# ---------------------------------------------
def _탭_콜백(프록시, 종류, 이벤트, 참조):
    """키가 눌릴 때마다 불린다. ⌘V 인지만 보고 나머지는 전부 버린다."""
    global _붙여넣기_횟수
    from Quartz import (
        CGEventGetFlags, CGEventGetIntegerValueField, CGEventTapEnable,
        kCGEventFlagMaskCommand, kCGEventTapDisabledByTimeout,
        kCGEventTapDisabledByUserInput, kCGKeyboardEventKeycode,
    )

    # 맥이 탭을 꺼버리는 경우가 있다 (우리가 너무 느리면). 다시 켠다.
    if 종류 in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
        if _탭 is not None:
            CGEventTapEnable(_탭, True)
        return 이벤트

    커맨드 = bool(CGEventGetFlags(이벤트) & kCGEventFlagMaskCommand)
    키번호 = CGEventGetIntegerValueField(이벤트, kCGKeyboardEventKeycode)
    if 커맨드 and 키번호 == V_키:
        _붙여넣기_횟수 += 1
    return 이벤트          # 건드리지 않고 그대로 돌려준다


def _탭으로_시작():
    global _탭, _탭_소스
    try:
        from Quartz import (
            CFMachPortCreateRunLoopSource, CFRunLoopAddSource, CFRunLoopGetCurrent,
            CGEventMaskBit, CGEventTapCreate, CGEventTapEnable,
            kCFRunLoopCommonModes, kCGEventKeyDown, kCGEventTapOptionListenOnly,
            kCGHeadInsertEventTap, kCGSessionEventTap,
        )
    except ImportError:
        return False        # Quartz 가 없으면 아래 방식으로 넘어간다

    try:
        _탭 = CGEventTapCreate(
            kCGSessionEventTap,              # 이 로그인 세션 전체
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,     # ★ 듣기만. 가로채지 않는다
            CGEventMaskBit(kCGEventKeyDown),  # 키를 누를 때만
            _탭_콜백,
            None,
        )
        if _탭 is None:
            return False                     # 권한이 없으면 여기서 None 이 나온다

        _탭_소스 = CFMachPortCreateRunLoopSource(None, _탭, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), _탭_소스, kCFRunLoopCommonModes)
        CGEventTapEnable(_탭, True)
        return True
    except Exception:
        return False


# ---------------------------------------------
# 방식 ② 글로벌 모니터 — 예비용
#   내 앱에 간 키는 못 본다는 한계가 있지만, 탭이 안 될 때를 대비해 남겨 둔다.
# ---------------------------------------------
def _키를_눌렀을때(이벤트):
    """키가 눌릴 때마다 불린다. ⌘V 인지만 보고 나머지는 전부 버린다."""
    global _붙여넣기_횟수
    커맨드를_같이_눌렀나 = bool(이벤트.modifierFlags() & NSEventModifierFlagCommand)
    if 커맨드를_같이_눌렀나 and 이벤트.keyCode() == V_키:
        _붙여넣기_횟수 += 1
    # ← 함수가 여기서 끝난다. 다른 키는 쳐다보지도 않고 버려진다.


def _모니터로_시작():
    global _감시자
    try:
        앱 = NSApplication.sharedApplication()
        앱.setActivationPolicy_(1)      # Dock 에 아이콘이 뜨지 않게
    except Exception:
        pass
    _감시자 = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        NSEventMaskKeyDown, _키를_눌렀을때
    )
    return _감시자 is not None


def paste_watch_start():
    """붙여넣기 감시를 시작한다. 성공하면 True, 권한이 없으면 False."""
    global _쓰는_방식

    # 아직 허락을 안 받았으면 맥에게 정식으로 물어본다.
    # (이래야 시스템 설정 '입력 모니터링' 목록에 그 프로그램이 나타난다)
    if not 입력모니터링_켜졌나():
        입력모니터링_요청()

    if _탭으로_시작():
        _쓰는_방식 = "tap"
        return True

    if 권한_있나() and _모니터로_시작():
        _쓰는_방식 = "global"
        return True

    _쓰는_방식 = None
    return False


def paste_watch_method():
    """지금 어떤 방식으로 보고 있나. 못 보고 있으면 None."""
    return _쓰는_방식


def paste_watch_poll():
    """지난번에 물어본 뒤로 붙여넣기를 몇 번 했는지 돌려주고 0 으로 되돌린다."""
    global _붙여넣기_횟수
    횟수 = _붙여넣기_횟수
    _붙여넣기_횟수 = 0
    return 횟수


def permission_hint():
    """권한이 모자랄 때 보여줄 안내문. 다 있으면 None."""
    입력 = 입력모니터링_켜졌나()
    손쉬운 = 손쉬운사용_켜졌나()
    if 입력:
        return None

    앱, _ = 지금_실행중인_앱()
    켤것 = f"'{앱}'" if 앱 else "이 프로그램"

    안내 = ["붙여넣기는 못 잡습니다. 맥은 권한이 두 개로 나뉘어 있습니다.",
            f"     손쉬운 사용    {'✅ 켜짐' if 손쉬운 else '❌ 꺼짐'}",
            "     입력 모니터링  ❌ 꺼짐   ← 붙여넣기는 이게 있어야 합니다",
            "",
            f"     ★ 지금 이것을 켠 프로그램: {앱 or '(못 찾음)'}",
            f"       권한은 파이썬이 아니라 {켤것} 이 받아야 합니다.",
            "",
            "     시스템 설정 → 개인정보 보호 및 보안 → 입력 모니터링",
            "     ('손쉬운 사용' 말고 '입력 모니터링' 입니다. 다른 목록입니다)",
            f"     목록에서 {켤것} 을 켜고, ★ {켤것} 을 완전히 껐다 켜세요.",
            "",
            "     자세히 알아보려면:  python check_permission.py",
            "     안 켜도 창·복사 기록은 정상으로 남습니다."]
    return "\n".join(안내)


def sleep(초):
    """기다린다. 단, 가만히 자는 게 아니라 맥의 소식을 계속 받으며 기다린다.

    ★ 여기가 중요하다 ★
      time.sleep() 으로 자버리면 그 1초 동안 온 ⌘V 소식을 통째로 놓친다.
      아래 방식은 '우편함을 열어둔 채로' 1초를 보낸다.
      (위에 나온 우편함 이야기와 같은 것이다)
    """
    NSRunLoop.currentRunLoop().runUntilDate_(
        NSDate.dateWithTimeIntervalSinceNow_(초)
    )


# ---------------------------------------------
# 자가진단 — 이 파일을 직접 실행하면 돈다
#     python platform_mac.py
# ---------------------------------------------
if __name__ == "__main__":
    import time

    print()
    print("  맥용 수집기 자가진단")
    print("  " + "─" * 50)

    r = active_app()
    if r["app"]:
        print(f"  ✅ 활성 프로그램   {r['app']}")
        print("     창 제목        (맥은 '화면 기록' 권한이 있어야 읽힙니다)")
    else:
        print("  ❌ 활성 프로그램을 못 읽었습니다")

    n1 = clipboard_serial()
    print(f"  ✅ 클립보드 번호   {n1}")

    d = clipboard_digest()
    if d["length"] is None:
        print("  ⚠️  클립보드에 글자가 없습니다 (사진이거나 비어 있음)")
    else:
        print(f"  ✅ 클립보드 내용   {d['length']}글자  지문 {d['hash'][:12]}…")

    print()
    print("  이제 아무 글자나 복사해 보세요. 10초 동안 기다립니다...")
    for _ in range(10):
        time.sleep(1)
        n2 = clipboard_serial()
        if n2 != n1:
            d = clipboard_digest()
            길이 = d["length"] if d["length"] is not None else "글자 아님"
            print(f"  ✅ 복사 감지됨!   {길이}")
            break
    else:
        print("  ⚠️  10초 동안 복사가 감지되지 않았습니다")

    print()
