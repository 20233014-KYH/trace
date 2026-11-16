"""
test_mac_chatgpt_ax.py — 맥 ChatGPT 앱 26.x (크로미움 · 번들 com.openai.codex) 의 대화 화면 열기 (11/16)

실제 앱에서 본 것 (김용현 맥 · ChatGPT 26.1029): AXManualAccessibility 만 켜면 창 틀 요소 12개뿐이라 질문 · 답을 못 읽음.
AXEnhancedUserInterface 를 켜자 2~3초 뒤 대화 화면(415개)이 열려 "내가 한 말:" · "ChatGPT 답변:" 으로 읽힘.
여기선 앱 없이 — 기록기가 ChatGPT 앱이 앞일 때 그 스위치를 켜는지, 화면이 비면 다시 켜는지, Claude 앱엔 안 켜는지만 본다.

  python 3-코드/collector/test_mac_chatgpt_ax.py
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
if sys.platform != "darwin":
    print("  맥에서만 돈다 — 건너뜀")
    sys.exit(0)
import desktop_ai_mac as D       # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✓' if 조건 else '✗'} {이름} {덧}")


class 앱:
    def __init__(self, bid, name, pid):
        self.b, self.n, self.p = bid, name, pid

    def bundleIdentifier(self):
        return self.b

    def localizedName(self):
        return self.n

    def processIdentifier(self):
        return self.p


def 돌리기(bid, name, pid, 노드수):
    """앞 앱 = (bid, name) 로 _tick 한 번 → 켠 스위치들"""
    켬 = []
    앞 = 앱(bid, name, pid)
    sys.modules["AppKit"] = types.SimpleNamespace(NSWorkspace=types.SimpleNamespace(
        sharedWorkspace=lambda: types.SimpleNamespace(frontmostApplication=lambda: 앞)))
    D.mac_ax.trusted = lambda ask=False: True
    D.mac_ax.app = lambda pid, t: "root"
    D.mac_ax.set_ = lambda el, k, v: 켬.append(k) or True
    D.mac_ax.get = lambda el, k: "win" if k in ("AXFocusedWindow", "AXMainWindow") else ""
    w.__dict__["_읽기"] = lambda el: (D._N({}, None), 노드수)            # 빈 화면 (창 틀만)
    w._tick()
    return 켬


w = D.MacDesktopAIWatcher(lambda items: None, {}, poll_sec=1, data_dir=".", debug=False)
print("\n  맥 ChatGPT 앱 (크로미움) 대화 화면 열기\n  " + "─" * 60)
k = 돌리기("com.openai.codex", "ChatGPT", 101, 12)
검사("ChatGPT 앱이 앞 → AXManualAccessibility + AXEnhancedUserInterface", "AXManualAccessibility" in k and "AXEnhancedUserInterface" in k, str(k))
k = 돌리기("com.openai.codex", "ChatGPT", 101, 12)
검사("두 번째에도 화면이 비어 있으면 AXEnhancedUserInterface 를 다시 켬", k == ["AXEnhancedUserInterface"], str(k))
k = 돌리기("com.openai.codex", "ChatGPT", 101, 400)
검사("화면이 열려 있으면(요소 많음) 다시 안 켬", k == [], str(k))
k = 돌리기("com.anthropic.claudefordesktop", "Claude", 202, 12)
검사("Claude 앱엔 AXEnhancedUserInterface 를 안 켬 (Electron 은 원래 길)", k == ["AXManualAccessibility"], str(k))
print("  " + "─" * 60 + f"\n  {'✓ 통과' if not 실패 else '✗ 실패'}  ({통과}개 통과 · {실패}개 실패)\n")
sys.exit(1 if 실패 else 0)
