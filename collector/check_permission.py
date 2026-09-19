# =============================================
# 맥에서 붙여넣기가 왜 안 잡히는지 짚어주는 진단 파일
#
#   python check_permission.py
#
# 맥은 키를 보는 권한이 두 개로 나뉘어 있다.
#
#   손쉬운 사용     컴퓨터를 '조작'해도 된다      (마우스를 움직이고 클릭하고)
#   입력 모니터링   키 입력을 '들어도' 된다       ★ 붙여넣기는 이쪽이 필요하다
#
# 둘은 완전히 다른 목록이다. 하나만 켜면 안 된다.
# 이 파일은 둘 다 확인하고, 실제로 키 소식이 오는지까지 시험한다.
# =============================================

import ctypes
import ctypes.util
import sys
import time

try:
    from AppKit import (
        NSApplication, NSEvent, NSEventMaskKeyDown, NSEventModifierFlagCommand,
    )
    from Foundation import NSRunLoop, NSDate
except Exception:
    import os
    지금환경 = os.environ.get("CONDA_DEFAULT_ENV", "(모름)")
    raise SystemExit(
        "\n  " + "─" * 62 +
        "\n  준비물이 없습니다: 맥용 도구 (pyobjc)\n" +
        (f"\n  지금 환경이 '{지금환경}' 입니다. 'trace' 여야 합니다."
         "\n  터미널을 껐다 켜면 항상 (base) 로 돌아갑니다. 매번 켜 주세요:"
         "\n\n      conda activate trace\n"
         "\n  프롬프트 맨 앞이 (trace) 로 바뀌면 된 것입니다."
         if 지금환경 != "trace" else
         "\n  환경은 맞는데 준비물이 빠졌습니다:"
         "\n\n      pip install pyobjc-framework-Cocoa") +
        "\n  " + "─" * 62 + "\n"
    )


from platform_mac import 지금_실행중인_앱      # 어느 프로그램이 켰는지 찾는다

V_키 = 9

# 입력 모니터링 관련 숫자들 (애플이 정해둔 값)
들을_권한 = 1          # kIOHIDRequestTypeListenEvent
허용됨 = 0             # kIOHIDAccessTypeGranted
거부됨 = 1
물어본적없음 = 2


# ---------------------------------------------
# 1. 권한 두 개를 각각 확인한다
# ---------------------------------------------
def 손쉬운사용_켜졌나():
    try:
        경로 = ctypes.util.find_library("ApplicationServices")
        lib = ctypes.cdll.LoadLibrary(경로)
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        lib.AXIsProcessTrusted.argtypes = []
        return bool(lib.AXIsProcessTrusted())
    except Exception as e:
        print("     (확인 실패:", e, ")")
        return False


def _iokit():
    경로 = ctypes.util.find_library("IOKit")
    lib = ctypes.cdll.LoadLibrary(경로)
    lib.IOHIDCheckAccess.restype = ctypes.c_int
    lib.IOHIDCheckAccess.argtypes = [ctypes.c_int]
    lib.IOHIDRequestAccess.restype = ctypes.c_bool
    lib.IOHIDRequestAccess.argtypes = [ctypes.c_int]
    return lib


def 입력모니터링_상태():
    try:
        return _iokit().IOHIDCheckAccess(들을_권한)
    except Exception:
        return None


def 입력모니터링_요청():
    """맥에게 '입력 모니터링 좀 쓰겠다'고 정식으로 요청한다.

    처음이면 창이 뜬다. 한 번 거부한 적이 있으면 창은 안 뜨지만,
    대신 시스템 설정의 '입력 모니터링' 목록에 터미널이 추가된다.
    그러면 사람이 직접 스위치를 켤 수 있다.
    """
    try:
        return _iokit().IOHIDRequestAccess(들을_권한)
    except Exception:
        return False


# ---------------------------------------------
# 2. 실제로 키 소식이 오는지 시험한다
# ---------------------------------------------
def 키_받아보기(설명, 초=8, 앱_먼저=False):
    """설명한 방식으로 감시를 걸고, 초 만큼 기다리며 ⌘V 를 세어 본다."""
    센_횟수 = {"값": 0, "아무키": 0}

    def 눌렸을때(이벤트):
        센_횟수["아무키"] += 1
        if (이벤트.modifierFlags() & NSEventModifierFlagCommand) and 이벤트.keyCode() == V_키:
            센_횟수["값"] += 1

    if 앱_먼저:
        # NSApplication 을 먼저 깨워야 키 소식이 온다는 이야기가 있어서 시험한다.
        앱 = NSApplication.sharedApplication()
        앱.setActivationPolicy_(1)      # 1 = 액세서리. Dock 에 아이콘이 안 뜬다.

    감시자 = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        NSEventMaskKeyDown, 눌렸을때
    )

    print()
    print(f"  [{설명}]")
    print(f"  감시자 만들어짐: {'예' if 감시자 is not None else '아니오'}")
    print(f"  ★ 지금부터 {초}초 동안, 아무 데나 ⌘V 를 몇 번 눌러 보세요.")

    끝 = time.monotonic() + 초
    while time.monotonic() < 끝:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.2)
        )
        남음 = int(끝 - time.monotonic()) + 1
        print(f"\r  남은 시간 {남음}초 …  키 소식 {센_횟수['아무키']}개, "
              f"그중 ⌘V {센_횟수['값']}번   ", end="", flush=True)

    print()
    if 감시자 is not None:
        NSEvent.removeMonitor_(감시자)

    성공 = 센_횟수["값"] > 0
    print(f"  → {'✅ 잡힙니다' if 성공 else '❌ 안 잡힙니다'}  "
          f"(키 소식 {센_횟수['아무키']}개, ⌘V {센_횟수['값']}번)")
    return 성공, 센_횟수["아무키"]


# ---------------------------------------------
def main():
    print()
    print("  붙여넣기 권한 진단")
    print("  " + "─" * 62)

    a = 손쉬운사용_켜졌나()
    b = 입력모니터링_상태()
    이름 = {허용됨: "✅ 허용됨", 거부됨: "❌ 거부됨/꺼짐",
            물어본적없음: "❔ 아직 물어본 적 없음", None: "확인 실패"}

    앱, 경로 = 지금_실행중인_앱()
    켤것 = f"'{앱}'" if 앱 else "이 프로그램"

    print(f"  손쉬운 사용    {'✅ 켜짐' if a else '❌ 꺼짐'}")
    print(f"  입력 모니터링  {이름.get(b, b)}     ★ 붙여넣기는 이게 있어야 합니다")
    print()
    print(f"  ★ 지금 이것을 켠 프로그램:  {앱 or '(못 찾음)'}")
    if 경로:
        print(f"     {경로}")
    print(f"     맥 권한은 파이썬이 아니라 {켤것} 에게 붙습니다.")
    print("     터미널에 권한을 줘도, 다른 프로그램 안에서 돌리면 소용없습니다.")

    if b != 허용됨:
        print()
        print("  맥에게 입력 모니터링을 정식으로 요청해 봅니다…")
        입력모니터링_요청()
        다시 = 입력모니터링_상태()
        print(f"  요청 뒤 상태: {이름.get(다시, 다시)}")
        if 다시 != 허용됨:
            print()
            print("  ──────────────────────────────────────────────────────")
            print("  해야 할 일")
            print()
            print("   1. 시스템 설정 → 개인정보 보호 및 보안 → 입력 모니터링")
            print("      (손쉬운 사용 말고 '입력 모니터링' 입니다. 다른 목록입니다)")
            print(f"   2. 목록에서 {켤것} 을 켭니다")
            if 앱 and 앱.lower() != "terminal" and 앱 != "터미널":
                print(f"      ★ '터미널' 이 아니라 {켤것} 입니다.")
                print(f"        지금 {켤것} 안에서 돌리고 계시기 때문입니다.")
                print("        터미널에서 돌리고 싶으면 터미널을 따로 열어서")
                print("        거기서 실행하시면 됩니다. 그러면 '터미널' 을 켜면 됩니다.")
            else:
                print("      안 보이면 왼쪽 아래 + 를 눌러 응용 프로그램 → 유틸리티 → 터미널")
            print(f"   3. ★ {켤것} 을 완전히 종료했다 다시 켭니다 (⌘Q)")
            print("   4. 이 파일을 다시 실행합니다")
            print("  ──────────────────────────────────────────────────────")
            print()
            return

    # 권한이 있으면 실제로 키가 오는지 두 가지 방식으로 시험한다
    성공, 아무키 = 키_받아보기("방식 1 — 그냥 감시", 초=8, 앱_먼저=False)

    if not 성공:
        성공2, 아무키2 = 키_받아보기(
            "방식 2 — NSApplication 을 먼저 깨우고 감시", 초=8, 앱_먼저=True)
        성공 = 성공 or 성공2
        아무키 = max(아무키, 아무키2)

    print()
    print("  " + "─" * 62)
    if 성공:
        print("  ✅ 붙여넣기를 잡을 수 있습니다. 수집기를 그냥 켜시면 됩니다.")
    elif 아무키 > 0:
        print("  ⚠️  키 소식은 오는데 ⌘V 만 안 잡혔습니다.")
        print("      ⌘V 를 정말 누르셨는지 확인하고 다시 돌려보세요.")
    else:
        print("  ❌ 키 소식이 하나도 오지 않습니다.")
        print("      권한 목록은 켜졌는데도 이렇다면, 터미널을 ⌘Q 로 완전히")
        print("      껐다 켜지 않았을 가능성이 큽니다. 맥은 껐다 켜야 반영됩니다.")
        print("      그래도 안 되면 이 화면을 캡처해서 보내주세요.")
    print()


if __name__ == "__main__":
    if sys.platform != "darwin":
        print("  이 진단은 맥 전용입니다. 윈도우는 권한이 필요 없습니다.")
        sys.exit(0)
    main()
