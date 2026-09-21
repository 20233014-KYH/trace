"""
keys.py — 키 입력 훅 (pynput). Proof Mode 에서는 필수, Learn Mode 에서는 옵션.

기록하는 것 — 전부 "횟수" 뿐:
  · 글자 키가 몇 번 눌렸나              → pop_counts()["typed"]
  · Backspace / Delete 가 몇 번 눌렸나   → pop_counts()["deleted"]
  · 붙여넣기  (윈도우 Ctrl+V / 맥 ⌘V)        → on_paste()
  · 되돌리기  (윈도우 Ctrl+Z / 맥 ⌘Z)        → on_undo()
  · 다시실행  (윈도우 Ctrl+Y / 맥 ⌘⇧Z)       → on_redo()
  · 잘라내기  (윈도우 Ctrl+X / 맥 ⌘X)        → on_cut()

어떤 키가 눌렸는지, 무슨 글자인지는 어디에도 저장하지 않는다.
이 파일 전체가 그 증거다 — 파일럿 학생에게 그대로 보여준다.
"""
import sys
import threading

맥 = sys.platform == "darwin"

# ★ 윈도우와 맥은 '수정자 키'가 다르다 ★
#     윈도우 : Ctrl + V / Z / Y / X
#     맥     : ⌘(Command) + V / Z / X,  다시실행은 ⌘⇧Z
#   이걸 안 나누면 맥에서는 붙여넣기가 한 번도 안 잡힌다.
VK_V, VK_Z, VK_Y, VK_X = 0x56, 0x5A, 0x59, 0x58
CTRL_CHARS = {"\x16": "paste", "\x1a": "undo", "\x19": "redo", "\x18": "cut"}
CTRL_VKS = {VK_V: "paste", VK_Z: "undo", VK_Y: "redo", VK_X: "cut"}

# 맥은 ⌘ 를 누른 채여도 글자가 그대로 온다 ('v', 'z', …)
MAC_CHARS = {"v": "paste", "z": "undo", "y": "redo", "x": "cut"}


class KeyCounter:
    def __init__(self, on_paste, on_undo=None, on_redo=None, on_cut=None):
        from pynput import keyboard  # 지연 import: enabled=false 면 pynput 없어도 됨
        self._kb = keyboard
        self._cb = {"paste": on_paste, "undo": on_undo, "redo": on_redo, "cut": on_cut}
        self._mod = False        # 윈도우면 Ctrl, 맥이면 ⌘ 를 누르고 있나
        self._shift = False      # 맥의 다시실행(⌘⇧Z) 판별용
        self._typed = 0
        self._deleted = 0
        self._lock = threading.Lock()
        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)
        self._listener.daemon = True

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()

    def pop_counts(self) -> dict:
        """지금까지 센 횟수를 돌려주고 0으로 되돌린다."""
        with self._lock:
            out = {"typed": self._typed, "deleted": self._deleted}
            self._typed = self._deleted = 0
        return out

    # ── 내부 ──
    def _수정자인가(self, key):
        """지금 이 키가 '수정자 키'인가. 맥이면 ⌘, 윈도우면 Ctrl."""
        kb = self._kb
        if 맥:
            return key in (kb.Key.cmd, kb.Key.cmd_l, kb.Key.cmd_r)
        return key in (kb.Key.ctrl_l, kb.Key.ctrl_r)

    def _press(self, key):
        kb = self._kb

        if self._수정자인가(key):
            self._mod = True
            return
        if key in (kb.Key.shift, kb.Key.shift_l, kb.Key.shift_r):
            self._shift = True
            return

        if self._mod:
            # 수정자 조합 — 무슨 동작인지만 보고, 글자로는 세지 않는다
            글자 = getattr(key, "char", None)
            if 맥:
                이름 = MAC_CHARS.get((글자 or "").lower())
                if 이름 == "undo" and self._shift:
                    이름 = "redo"          # 맥의 다시실행은 ⌘⇧Z
            else:
                이름 = CTRL_CHARS.get(글자) or CTRL_VKS.get(getattr(key, "vk", None))
            cb = self._cb.get(이름)
            if cb:
                cb()
            return

        if key in (kb.Key.backspace, kb.Key.delete):
            with self._lock:
                self._deleted += 1
            return
        if getattr(key, "char", None) is not None:  # 글자 키만 (화살표·F키 등 제외)
            with self._lock:
                self._typed += 1

    def _release(self, key):
        kb = self._kb
        if self._수정자인가(key):
            self._mod = False
        elif key in (kb.Key.shift, kb.Key.shift_l, kb.Key.shift_r):
            self._shift = False
