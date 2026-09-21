"""
keys.py — 키 입력 훅 (pynput). Proof Mode 에서는 필수, Learn Mode 에서는 옵션.

기록하는 것 — 전부 "횟수" 뿐:
  · 글자 키가 몇 번 눌렸나              → pop_counts()["typed"]
  · Backspace / Delete 가 몇 번 눌렸나   → pop_counts()["deleted"]
  · Ctrl+V (붙여넣기)                     → on_paste()
  · Ctrl+Z / Ctrl+Y (되돌리기 / 다시실행) → on_undo() / on_redo()
  · Ctrl+X (잘라내기)                     → on_cut()

어떤 키가 눌렸는지, 무슨 글자인지는 어디에도 저장하지 않는다.
이 파일 전체가 그 증거다 — 파일럿 학생에게 그대로 보여준다.
"""
import threading

VK_V, VK_Z, VK_Y, VK_X = 0x56, 0x5A, 0x59, 0x58
CTRL_CHARS = {"\x16": "paste", "\x1a": "undo", "\x19": "redo", "\x18": "cut"}
CTRL_VKS = {VK_V: "paste", VK_Z: "undo", VK_Y: "redo", VK_X: "cut"}


class KeyCounter:
    def __init__(self, on_paste, on_undo=None, on_redo=None, on_cut=None):
        from pynput import keyboard  # 지연 import: enabled=false 면 pynput 없어도 됨
        self._kb = keyboard
        self._cb = {"paste": on_paste, "undo": on_undo, "redo": on_redo, "cut": on_cut}
        self._ctrl = False
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
    def _press(self, key):
        kb = self._kb
        if key in (kb.Key.ctrl_l, kb.Key.ctrl_r):
            self._ctrl = True
            return
        if self._ctrl:
            # Ctrl 조합: pynput 은 char 가 제어문자('\x16')로 오거나 vk 로 온다
            name = CTRL_CHARS.get(getattr(key, "char", None)) or CTRL_VKS.get(getattr(key, "vk", None))
            cb = self._cb.get(name)
            if cb:
                cb()
            return  # ctrl 조합은 글자로 세지 않음
        if key in (kb.Key.backspace, kb.Key.delete):
            with self._lock:
                self._deleted += 1
            return
        if getattr(key, "char", None) is not None:  # 글자 키만 (화살표·F키 등 제외)
            with self._lock:
                self._typed += 1

    def _release(self, key):
        kb = self._kb
        if key in (kb.Key.ctrl_l, kb.Key.ctrl_r):
            self._ctrl = False
