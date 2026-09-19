# =============================================
# 붙여넣기 판별이 맞는지 시험하는 파일
#
#   python test_paste.py
#
# 진짜 키보드를 치지 않고, '가짜 키 입력'을 넣어서
# ⌘V / Ctrl+V 만 골라내는지 확인한다.
#
# ★ 왜 이렇게 하나 ★
#   ① 맥에서 윈도우 코드를 시험할 수 있다. (팀원 컴을 빌리지 않아도 된다)
#   ② 권한이 없어도 판별 로직은 시험할 수 있다.
#   ③ ⌘C 를 붙여넣기로 잘못 세는 것 같은 실수를 바로 잡아낸다.
#
# 단, 이 시험이 통과해도 "진짜 키보드에서 잘 잡힌다"는 보장은 아니다.
# 그건 실제로 수집기를 켜고 붙여넣어 봐야 안다.
# =============================================

import ctypes
import sys
import types


# ---------------------------------------------
# 맥 — ⌘V 만 세는가
# ---------------------------------------------
def 맥_시험():
    import platform_mac as m

    CMD, SHIFT, OPT = 1 << 20, 1 << 17, 1 << 19

    class 가짜키:
        """맥이 보내주는 키 소식을 흉내낸 것."""
        def __init__(self, code, flags):
            self._c, self._f = code, flags
        def keyCode(self):
            return self._c
        def modifierFlags(self):
            return self._f

    시험 = [
        ("⌘V  (붙여넣기)",           가짜키(9, CMD),         1),
        ("⌘⇧V (서식없이 붙여넣기)",  가짜키(9, CMD | SHIFT), 1),
        ("⌘C  (복사)",               가짜키(8, CMD),         0),
        ("그냥 V 타이핑",            가짜키(9, 0),           0),
        ("⌘A  (전체선택)",           가짜키(0, CMD),         0),
        ("⌥V",                       가짜키(9, OPT),         0),
    ]

    문제 = False
    for 설명, 이벤트, 기대 in 시험:
        m.paste_watch_poll()                  # 0 으로 되돌리고 시작
        m._키를_눌렀을때(이벤트)
        실제 = m.paste_watch_poll()
        맞나 = 실제 == 기대
        문제 |= not 맞나
        print(f"  {'✅' if 맞나 else '❌'}  {설명:<26} 셈 {실제}  (기대 {기대})")

    return not 문제


# ---------------------------------------------
# 윈도우 — Ctrl+V 만 세는가
#
# 맥에는 pywin32 도 ctypes.windll 도 없다.
# 그래서 가짜로 만들어 끼워 넣고 platform_win.py 를 불러온다.
# ---------------------------------------------
def 윈도우_시험():
    for 이름 in ["win32clipboard", "win32gui", "win32process", "psutil"]:
        가짜 = types.ModuleType(이름)
        가짜.CF_UNICODETEXT = 13
        sys.modules[이름] = 가짜

    눌린키 = set()          # 지금 눌려 있는 키들. 우리가 마음대로 조작한다.

    class 가짜User32:
        def GetAsyncKeyState(self, 키):
            return 0x8000 if 키 in 눌린키 else 0
        def __getattr__(self, _):
            return lambda *a, **k: 0

    class 가짜WinDLL:
        user32 = 가짜User32()

    ctypes.windll = 가짜WinDLL()
    import platform_win as w

    CTRL, SHIFT, V, INS = w.VK_CONTROL, w.VK_SHIFT, w.VK_V, w.VK_INSERT
    C, A = 0x43, 0x41

    def 누르고떼기(*키들):
        눌린키.update(키들)
        w._한번_살펴보기()          # 누른 순간
        w._한번_살펴보기()          # 아직 누르고 있음
        w._한번_살펴보기()
        눌린키.difference_update(키들)
        w._한번_살펴보기()          # 뗌

    시험 = [
        ("Ctrl+V  (붙여넣기)",       [CTRL, V],    1),
        ("Shift+Insert (옛날 방식)", [SHIFT, INS], 1),
        ("Ctrl+C  (복사)",           [CTRL, C],    0),
        ("그냥 V 타이핑",            [V],          0),
        ("Ctrl+A  (전체선택)",       [CTRL, A],    0),
        ("Shift+V (대문자 V)",       [SHIFT, V],   0),
    ]

    문제 = False
    for 설명, 키들, 기대 in 시험:
        w.paste_watch_poll()
        누르고떼기(*키들)
        실제 = w.paste_watch_poll()
        맞나 = 실제 == 기대
        문제 |= not 맞나
        print(f"  {'✅' if 맞나 else '❌'}  {설명:<26} 셈 {실제}  (기대 {기대})")

    # 꾹 누르고 있어도 한 번만 세야 한다
    w.paste_watch_poll()
    눌린키.update([CTRL, V])
    for _ in range(40):
        w._한번_살펴보기()
    눌린키.clear()
    w._한번_살펴보기()
    실제 = w.paste_watch_poll()
    맞나 = 실제 == 1
    문제 |= not 맞나
    print(f"  {'✅' if 맞나 else '❌'}  {'Ctrl+V 를 2초간 꾹':<26} 셈 {실제}  (기대 1)")

    # 연속으로 두 번이면 두 번 세야 한다
    w.paste_watch_poll()
    누르고떼기(CTRL, V)
    누르고떼기(CTRL, V)
    실제 = w.paste_watch_poll()
    맞나 = 실제 == 2
    문제 |= not 맞나
    print(f"  {'✅' if 맞나 else '❌'}  {'Ctrl+V 두 번':<26} 셈 {실제}  (기대 2)")

    return not 문제


if __name__ == "__main__":
    import platform

    print()
    print("  붙여넣기 판별 시험  (가짜 키 입력으로)")

    통과 = True

    if platform.system() == "Darwin":
        print()
        print("  맥 — ⌘V 만 골라내나")
        print("  " + "─" * 52)
        통과 &= 맥_시험()

    print()
    print("  윈도우 — Ctrl+V 만 골라내나")
    print("  " + "─" * 52)
    통과 &= 윈도우_시험()

    print()
    print("  ✅ 전부 통과했습니다." if 통과 else "  ❌ 문제가 있습니다.")
    print()
    sys.exit(0 if 통과 else 1)
