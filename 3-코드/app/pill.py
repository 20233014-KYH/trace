"""
pill.py — 알약 창 시제품 (목업 03·13·13b·13c · 결정 10·11).

콘솔 대신 화면 오른쪽 아래에 작은 창 하나: [질문칸 (Learn 만)] 위, [알약] 아래.
  · 프레임 없음 · 항상 위(on_top) · 투명 배경 · 알약을 잡아 끌면 옮겨짐
  · 알약 클릭 → 점 하나로 줄어드는 최소 모드 · ■ → 세션 종료(봉인) 후 창 닫힘
  · 질문칸 클릭 → 그 자리 위로 채팅 패널 (서버 POST /chat) → ✕ 로 접힘
  · 모션은 없음 (9/22 결정 — 투명 창 크기를 단계별로 바꾸면 WebView 가 튄다. 나중에)

수집기(collector.Collector)는 이 프로세스 안 스레드에서 그대로 돈다. 알약은 그 상태(경과·이벤트·맥락 수)를 1초마다 읽는다.
    python app/pill.py --mode learn        (서버 켜져 있으면 /chat 도 됨 · --dry-run 이면 채팅은 안 됨)

A 의 pywebview 골격에 넣을 때 참고용. 창 크기·API 이름은 pill.html 과 짝.
"""
import argparse
import ctypes
import ctypes.wintypes
import json
import os
import sys
import threading
import time

import webview
from webview.window import FixPoint

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "collector"))
from collector import Collector  # noqa: E402

# 창 크기 — pill.html 의 레이아웃과 짝 (논리 px). open = 패널 392 + 알약 26 + 여백
SIZE = {"mini": (34, 34), "pill": (168, 34), "learn": (168, 72), "open": (368, 442)}
MARGIN = 12


class Api:
    """pill.html 이 pywebview.api.* 로 부르는 것. Collector·Window 는 밑줄로 숨긴다 (pywebview 가 공개 속성을 JS 에 노출하려 든다)"""

    def __init__(self, c: Collector, server: str | None):
        self._c, self._server, self._win = c, server, None

    def status(self):
        s = self._c._status()
        e = s["elapsed_sec"]
        s["elapsed"] = f"{e // 3600:02d}:{e % 3600 // 60:02d}:{e % 60:02d}"
        return s

    def layout(self, name: str, dock: bool = False):
        """창 크기를 바꾼다 — mini · pill · learn · open. 오른쪽 아래 모서리는 그 자리에 둔다 (끌어다 놓은 위치 유지).
        dock=True(처음 한 번)면 화면 오른쪽 아래에 붙인다."""
        w, h = SIZE[name]
        self._win.resize(w, h, FixPoint.SOUTH | FixPoint.EAST)   # 물리 픽셀로 계산 → 배율 오차 없음
        if dock:
            ww, wh = _work_area()
            self._win.move(ww - w - MARGIN, wh - h - MARGIN)
        return name

    def chat(self, question: str):
        if not self._server:
            return {"error": "dry-run — 서버 없이 실행 중이라 AI 답을 받을 수 없습니다"}
        try:
            import requests
            r = requests.post(f"{self._server}/sessions/{self._c.session_id}/chat", json={"selection": "", "question": question}, timeout=60)
            if r.status_code == 403:
                return {"error": "Proof 세션에는 AI 기능이 없습니다"}
            if r.status_code == 429:
                return {"error": "이 세션의 채팅 상한(30회)에 닿았습니다"}
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": f"서버 오류: {e}"}

    def stop(self):
        """■ — 봉인하고 창을 닫는다"""
        self._c.stop()
        threading.Timer(1.5, self._win.destroy).start()   # 수집기가 session_end·봉인을 보낼 시간
        return True


def _work_area():
    """작업표시줄을 뺀 화면 영역을 pywebview 논리 픽셀로 (배율 200% 에서 물리/논리가 섞이지 않게)"""
    sc = webview.screens[0]
    try:
        u = ctypes.windll.user32
        r = ctypes.wintypes.RECT()
        u.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)   # SPI_GETWORKAREA
        scale = u.GetSystemMetrics(0) / sc.width or 1
        return int(r.right / scale), int(r.bottom / scale)
    except Exception:
        return sc.width, sc.height - 48


def _make_transparent(window):
    """pywebview 의 transparent 는 WebView2 배경만 투명하게 하고 창(WinForms Form) 바탕은 회색으로 남긴다.
    TransparencyKey 방식은 레이어드 창이 되어 WebView2 가 마우스를 못 받는다 (클릭·드래그 전부 죽음).
    → DWM 방식: 바탕 검정 + 프레임을 클라이언트 전체(-1)로 확장하면 알파 0 인 곳이 뚫리고 입력은 그대로."""
    try:
        from webview.platforms.winforms import BrowserView
        from System.Drawing import Color
        from System import Action

        class MARGINS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]

        for _ in range(50):                       # 창이 만들어질 때까지 잠깐 기다림 (최대 5초)
            form = BrowserView.instances.get(window.uid)
            if form:
                break
            time.sleep(0.1)

        def apply():
            form.BackColor = Color.Black
            m = MARGINS(-1, -1, -1, -1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(form.Handle.ToInt32(), ctypes.byref(m))
        form.Invoke(Action(apply))
    except Exception as e:
        print(f"  투명 처리 실패 ({e}) — 회색 바탕으로 계속")


def main():
    ap = argparse.ArgumentParser(description="Trace 알약 창 (시제품)")
    ap.add_argument("--config", default=os.path.join(HERE, "..", "collector", "config.json"))
    ap.add_argument("--mode", choices=["proof", "learn"])
    ap.add_argument("--work")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    with open(a.config, encoding="utf-8") as f:
        cfg = json.load(f)
    mode = a.mode or cfg.get("mode", "proof")
    c = Collector(cfg, mode, a.work or cfg.get("work_id", "W_local"), a.dry_run)
    threading.Thread(target=c.run, daemon=True, name="collector").start()

    api = Api(c, None if a.dry_run else cfg["server"])
    w, h = SIZE["learn" if mode == "learn" else "pill"]
    ww, wh = _work_area()
    api._win = webview.create_window(
        "Trace", os.path.join(HERE, "pill.html"), js_api=api,
        width=w, height=h, x=ww - w - MARGIN, y=wh - h - MARGIN,
        frameless=True, on_top=True, transparent=True, resizable=False, easy_drag=False,
        min_size=(30, 30),                               # 기본 min_size (200,100) 이면 알약(72px)·점(34px) 크기로 못 줄어든다
    )
    webview.start(_make_transparent, api._win, debug=False)
    c.stop()                                              # 창이 닫히면 수집기도 정리


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
