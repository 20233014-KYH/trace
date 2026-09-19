# =============================================
# 윈도우에서 "지금 무슨 프로그램?" 과 "뭔가 복사했나?" 를 알아내는 파일
#
# 맥용은 platform_mac.py 에 있다. 두 파일은 이름이 같은 함수를 갖고,
# 같은 모양의 답을 돌려준다. 그래서 collector.py 는 맥인지 윈도우인지
# 신경 쓰지 않아도 된다.
#
# 준비물 :  pip install pywin32 psutil
#
# ★ 잘 되는지 확인하려면 이 파일을 그냥 실행해 보세요 ★
#      python platform_win.py
#   세 가지 기능을 하나씩 시험해서 어디가 잘못됐는지 알려줍니다.
# =============================================

import ctypes
import time as _time
import hashlib

try:
    import win32clipboard
    import win32gui
    import win32process
    import psutil
except ImportError as e:
    raise ImportError(
        f"\n\n  필요한 것이 설치되지 않았습니다: {e.name}\n"
        f"  Anaconda Prompt 에서 아래를 치세요:\n\n"
        f"      pip install pywin32 psutil\n"
    ) from e


# ---------------------------------------------
# 지금 맨 앞에 뜬 프로그램
# ---------------------------------------------
def active_app():
    """지금 맨 앞에 떠 있는 프로그램의 이름과 창 제목을 돌려준다.

    돌려주는 모양 (맥용과 똑같다) :
        {"app": "chrome.exe", "title": "claude.ai - Claude"}
        못 찾으면  {"app": None, "title": None}

    맥과 달리 윈도우는 창 제목까지 권한 없이 읽힌다.
    그래서 title 에 실제 제목이 들어간다 — 기록이 더 자세하다.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()      # 맨 앞 창의 번호
        if not hwnd:
            return {"app": None, "title": None}

        제목 = win32gui.GetWindowText(hwnd) or None

        # 그 창을 만든 프로그램을 찾는다
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        이름 = psutil.Process(pid).name()          # 예: "chrome.exe"

        return {"app": 이름, "title": 제목}

    except Exception:
        # 창이 막 닫히는 중이거나 접근이 막힌 프로그램일 때가 있다.
        # 수집기가 멈추면 안 되므로 조용히 빈 답을 돌려준다.
        return {"app": None, "title": None}


# ---------------------------------------------
# 복사(클립보드) 관련 함수 두 개
#
# 왜 두 개로 나눴나 :
#   1초마다 클립보드 "내용"을 읽으면 남의 비밀번호까지 계속 들여다보는 셈이다.
#   그래서 평소에는 번호만 본다. 번호가 바뀌었을 때만 길이를 잰다.
#   기획안 4.3 "내용을 읽지 않는다" 원칙을 코드로 지키는 방법이다.
# ---------------------------------------------
_user32 = ctypes.windll.user32
_user32.GetClipboardSequenceNumber.restype = ctypes.c_uint

_직접_센_번호 = 0          # 아래 예비 방법에서 쓰는 값
_직접_센_지문 = None


def clipboard_serial():
    """클립보드가 바뀔 때마다 오르는 번호를 돌려준다. 내용은 읽지 않는다.

    윈도우가 직접 세어주는 번호를 쓴다 (GetClipboardSequenceNumber).
    혹시 그게 0만 돌려주면 — 아주 오래된 윈도우 —
    아래 예비 방법으로 우리가 직접 센다.
    """
    번호 = _user32.GetClipboardSequenceNumber()
    if 번호:
        return 번호

    # ── 예비 방법 : 내용이 바뀌었는지 보고 직접 센다 ──
    global _직접_센_번호, _직접_센_지문
    지금 = clipboard_digest()["hash"]
    if 지금 != _직접_센_지문:
        _직접_센_지문 = 지금
        _직접_센_번호 += 1
    return _직접_센_번호


def clipboard_digest():
    """지금 클립보드의 '길이'와 '지문'만 돌려준다. 내용은 돌려주지 않는다.

    돌려주는 모양 (맥용과 똑같다) :
        {"length": 240, "hash": "a3f9c2d1..."}
        글자가 아니면 (사진·파일 등)  {"length": None, "hash": None}

    지문(해시)이란 :
        아무리 긴 글이라도 넣으면 64자리 값이 나온다.
        같은 글은 언제나 같은 값, 한 글자만 달라도 완전히 다른 값이다.
        그래서 "AI 탭에서 복사한 것"과 "워드에 붙여넣은 것"이 같은지를
        내용을 보지 않고도 비교할 수 있다.
    """
    글자 = None
    열렸나 = False

    try:
        win32clipboard.OpenClipboard()
        열렸나 = True

        # 글자 형식이 들어있을 때만 꺼낸다 (사진이면 건너뛴다)
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            글자 = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)

    except Exception:
        # 다른 프로그램이 클립보드를 쓰고 있으면 잠깐 열리지 않는다.
        # 다음 번에 다시 시도하면 되므로 조용히 넘어간다.
        글자 = None

    finally:
        # 열었으면 반드시 닫아야 한다. 안 닫으면 다른 프로그램이
        # 복사·붙여넣기를 못 하게 된다.
        if 열렸나:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

    if not 글자:
        return {"length": None, "hash": None}

    지문 = hashlib.sha256(글자.encode("utf-8")).hexdigest()
    return {"length": len(글자), "hash": 지문}



# =============================================
# 붙여넣기 감지
#
# 왜 따로 만드나 — 복사는 클립보드를 바꾸지만
# 붙여넣기는 아무것도 바꾸지 않는다. 그래서 클립보드를 아무리 들여다봐도
# 못 잡는다. 키를 누르는 것(Ctrl+V)을 직접 봐야 한다.
#
# ★ 윈도우는 권한이 필요 없다. (맥은 '손쉬운 사용' 권한이 필요하다)
#
# ★ 어떻게 보나 — '키 후킹'은 일부러 쓰지 않았다.
#   키 후킹은 모든 키 입력이 우리 프로그램을 거쳐 가게 만드는 방식이라,
#   우리 프로그램이 잠깐만 버벅여도 컴퓨터 전체의 키 입력이 같이 느려진다.
#   대신 GetAsyncKeyState 로 "지금 이 키가 눌려 있나?" 만 0.05초마다 물어본다.
#   키 입력을 가로채지 않으므로 다른 프로그램에 아무 영향이 없다.
#
# ★ 무슨 글자를 쳤는지는 보지 않는다.
#   물어보는 키는 Ctrl, Shift, V, Insert — 이 네 개뿐이다.
# =============================================

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_INSERT = 0x2D
VK_V = 0x56

_눌림 = 0x8000          # 이 자리가 켜져 있으면 "지금 눌려 있다"는 뜻

_붙여넣기_횟수 = 0
_직전_V = False          # 방금 전에도 V 가 눌려 있었나
_직전_INSERT = False


def paste_watch_start():
    """윈도우는 따로 준비할 게 없다. 늘 성공이다."""
    return True


def _키가_눌려있나(키번호):
    return bool(_user32.GetAsyncKeyState(키번호) & _눌림)


def _한번_살펴보기():
    """지금 이 순간 Ctrl+V (또는 Shift+Insert) 가 눌렸는지 본다.

    '막 눌린 순간'만 한 번 센다.
    안 그러면 키를 꾹 누르고 있는 동안 계속 세어버린다.
    """
    global _붙여넣기_횟수, _직전_V, _직전_INSERT

    ctrl = _키가_눌려있나(VK_CONTROL)
    shift = _키가_눌려있나(VK_SHIFT)

    지금_V = _키가_눌려있나(VK_V)
    if 지금_V and not _직전_V and ctrl:        # 안 눌려 있다가 방금 눌렸다
        _붙여넣기_횟수 += 1
    _직전_V = 지금_V

    지금_INSERT = _키가_눌려있나(VK_INSERT)    # 옛날 방식 붙여넣기 (Shift+Insert)
    if 지금_INSERT and not _직전_INSERT and shift:
        _붙여넣기_횟수 += 1
    _직전_INSERT = 지금_INSERT


def paste_watch_poll():
    """지난번에 물어본 뒤로 붙여넣기를 몇 번 했는지 돌려주고 0 으로 되돌린다."""
    global _붙여넣기_횟수
    횟수 = _붙여넣기_횟수
    _붙여넣기_횟수 = 0
    return 횟수


def permission_hint():
    """윈도우는 권한이 필요 없다."""
    return None


def sleep(초):
    """기다린다. 단, 기다리는 동안 0.05초마다 키를 살펴본다.

    ★ 왜 잘게 쪼개나 ★
      time.sleep(1) 로 1초를 통째로 자버리면
      그 사이에 눌렀다 뗀 Ctrl+V 를 통째로 놓친다.
      사람이 키를 누르고 있는 시간은 보통 0.1초쯤이라 0.05초면 충분하다.
    """
    끝나는_시각 = _time.monotonic() + 초
    while True:
        _한번_살펴보기()
        남은시간 = 끝나는_시각 - _time.monotonic()
        if 남은시간 <= 0:
            break
        _time.sleep(min(0.05, 남은시간))


# ---------------------------------------------
# 자가진단 — 이 파일을 직접 실행하면 돈다
#     python platform_win.py
# ---------------------------------------------
if __name__ == "__main__":
    import time

    print()
    print("  윈도우용 수집기 자가진단")
    print("  " + "─" * 50)

    # ① 활성 프로그램
    r = active_app()
    if r["app"]:
        print(f"  ✅ 활성 프로그램   {r['app']}")
        print(f"     창 제목        {r['title']}")
    else:
        print("  ❌ 활성 프로그램을 못 읽었습니다")

    # ② 클립보드 번호
    n1 = clipboard_serial()
    print(f"  ✅ 클립보드 번호   {n1}")

    # ③ 클립보드 지문
    d = clipboard_digest()
    if d["length"] is None:
        print("  ⚠️  클립보드에 글자가 없습니다 (사진이거나 비어 있음)")
    else:
        print(f"  ✅ 클립보드 내용   {d['length']}글자  지문 {d['hash'][:12]}…")

    # ④ 변화 감지
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
