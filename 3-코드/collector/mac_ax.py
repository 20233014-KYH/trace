"""
mac_ax.py — 맥 손쉬운 사용(Accessibility) API 를 쓰는 작은 도구 (10/14)

화면낭독기(VoiceOver)가 다른 앱의 글을 읽는 길과 같다. 윈도우의 UI Automation 과 같은 자리.
  · 앞 창 제목 (platform_mac.foreground) — '화면 기록' 권한 없이 창 제목을 읽는다
  · 데스크톱 AI 앱 화면의 글 (desktop_ai_mac.py)

★ 권한: 시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용 → Trace 켜기
  권한은 파이썬이 아니라 '파이썬을 켠 앱'에 붙는다 (설치판 = Trace, 저장소에서 돌리면 터미널 등).
  없으면 아무것도 읽지 않고 빈 값을 돌려준다 — 기록기는 창 이름 · 복사 · 키 횟수로 계속 돈다.
"""
try:
    from ApplicationServices import (AXIsProcessTrusted, AXIsProcessTrustedWithOptions, AXUIElementCopyAttributeValue,
                                     AXUIElementCopyMultipleAttributeValues, AXUIElementCreateApplication,
                                     AXUIElementSetAttributeValue, AXUIElementSetMessagingTimeout,
                                     kAXTrustedCheckOptionPrompt)
    from Foundation import NSArray
    _있음 = True
except Exception:                                         # pyobjc-framework-ApplicationServices 가 없음
    _있음 = False

_물음 = {"done": False}


def trusted(ask=False):
    """손쉬운 사용 권한이 있나. ask=True 면 (한 번만) 시스템이 권한 창을 띄워 설정 목록에 Trace 가 나타나게 한다"""
    if not _있음:
        return False
    try:
        if ask and not _물음["done"]:
            _물음["done"] = True
            return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
        return bool(AXIsProcessTrusted())
    except Exception:
        return False


def app(pid, timeout=1.0):
    el = AXUIElementCreateApplication(pid)
    try:
        AXUIElementSetMessagingTimeout(el, float(timeout))   # 앱이 바쁠 때 기록기가 같이 멈추지 않게
    except Exception:
        pass
    return el


def get(el, name):
    """속성 하나 — 없거나 오류면 None"""
    try:
        err, v = AXUIElementCopyAttributeValue(el, name, None)
        return v if err == 0 else None
    except Exception:
        return None


def set_(el, name, value):
    try:
        return AXUIElementSetAttributeValue(el, name, value) == 0
    except Exception:
        return False


def _값(v):
    """글 · 숫자 → 그대로, 목록(NSArray) → list, 그 밖(없는 속성의 오류 값 등) → None"""
    if isinstance(v, (str, int, float)):
        return v
    if _있음 and isinstance(v, NSArray):
        return list(v)
    return None


def gets(el, names):
    """속성 여럿을 한 번에 (앱과 한 번만 주고받아서 빠르다) → {이름: 값 | None}"""
    try:
        err, vals = AXUIElementCopyMultipleAttributeValues(el, names, 0, None)
    except Exception:
        err, vals = -1, None
    if err != 0 or vals is None:
        return {n: _값(get(el, n)) for n in names}
    return {n: _값(v) for n, v in zip(names, vals)}


def window_title(pid):
    """앞 앱의 앞 창 제목 — 권한이 없으면 "" """
    if not trusted():
        return ""
    w = get(app(pid, 0.3), "AXFocusedWindow")
    t = get(w, "AXTitle") if w is not None else None
    return str(t) if isinstance(t, str) else ""
