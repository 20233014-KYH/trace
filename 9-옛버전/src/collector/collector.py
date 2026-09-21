"""
collector.py — Trace Tier 0 수집기 (윈도우 · 맥 상주 프로그램)

무엇을 잡나 (기획안 §4.1 Tier 0):
  · 세션 시작·종료 · 유휴(5분 무입력) · heartbeat(30초)
  · 활성 창의 앱 이름 + 창 제목 (1초 폴링, 화이트리스트 앱만 제목 저장)
  · 클립보드 변경 → 길이와 SHA256 만 (원문 저장 안 함)
  · (Proof 필수) 입력·삭제 횟수, Ctrl+V / Ctrl+Z / Ctrl+Y / Ctrl+X 감지 — config.keys.enabled
  · (옵션) 감시 폴더 파일 생성·수정·저장  — config.files.watch_dirs

무엇을 안 하나: 화면 캡처, 키 내용, 클립보드 원문, 창 제목 밖의 문서 내용.

흐름 (기획안 §12.2):
  이벤트 생성 → ../data/events-YYYY-MM-DD.jsonl 에 먼저 기록(로컬 우선)
             → POST {server}/api/event
             → 서버가 꺼져 있으면 ../data/queue.jsonl 에 쌓았다가 다음에 재전송

실행:
  python collector.py              # 서버로 전송
  python collector.py --dry-run    # 서버 없이 콘솔 + 로컬 파일만 (Day 1 확인용)
  python collector.py --config 다른경로.json
"""
import argparse
import hashlib
import json
import os
import queue
import signal
import sys
import threading
import time
from datetime import datetime, timezone, timedelta

import pyperclip
import requests

from classify import Classifier

# ── 운영체제에 따라 맞는 파일을 불러온다 ──────────────────────────
#   platform_win.py / platform_mac.py 는 같은 이름의 함수를 갖는다:
#     foreground()  idle_seconds()  clipboard_serial()  input_permission_hint()
#   그래서 아래 코드는 지금이 맥인지 윈도우인지 신경 쓰지 않아도 된다.
if sys.platform == "win32":
    import platform_win as osx
elif sys.platform == "darwin":
    import platform_mac as osx
else:
    sys.exit(f"맥과 윈도우만 지원합니다 (지금: {sys.platform}).")

foreground = osx.foreground
idle_seconds = osx.idle_seconds

HERE = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))


def now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8", "surrogatepass")).hexdigest()


# ─────────────────────────── 이벤트 저장·전송 ───────────────────────────
class Sink:
    """로컬 jsonl 에 먼저 쓰고, 백그라운드 스레드가 서버로 POST.
    서버가 꺼져 있으면 queue.jsonl 에 보관하고 10초마다 재접속을 시도한다.
    전송이 폴링 루프를 막지 않도록 메인 스레드에서는 절대 네트워크를 안 탄다."""

    RETRY_SEC = 10

    def __init__(self, data_dir: str, server: str | None, session_id: str):
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir
        self.server = server
        self.session_id = session_id
        self.queue_path = os.path.join(data_dir, "queue.jsonl")
        self._seq = 0
        self._lock = threading.Lock()
        self._log_path = None
        self._log_f = None
        self._q: queue.Queue = queue.Queue()
        self._online = None            # None=모름, True/False
        self._next_retry = 0.0
        self._worker = threading.Thread(target=self._send_loop, daemon=True)
        if server:
            self._worker.start()

    def _local_file(self):
        p = os.path.join(self.data_dir, f"events-{datetime.now(KST):%Y-%m-%d}.jsonl")
        if p != self._log_path:
            if self._log_f:
                self._log_f.close()
            self._log_path = p
            self._log_f = open(p, "a", encoding="utf-8")
        return self._log_f

    def emit(self, ev: dict):
        with self._lock:
            self._seq += 1
            ev = {"id": f"evt_{self._seq:06d}", "session_id": self.session_id,
                  "ts": now_iso(), "source": "collector", **ev}
            f = self._local_file()
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            f.flush()
        self._print(ev)
        if self.server:
            self._q.put(ev)

    def _print(self, ev):
        t = ev["ts"][11:19]
        k = ev["type"]
        if k == "window":
            body = f"[{ev['category']:8}] {ev['app']:18} {ev.get('title', '')[:60]}"
        elif k in ("copy", "paste"):
            body = f"len={ev['len']:5}  {ev['hash'][:23]}…  app={ev.get('app', '')}"
        elif k == "keys":
            body = f"typed={ev['count']}  deleted={ev.get('deleted', 0)}  app={ev.get('app', '')}"
        elif k == "file":
            body = f"{ev['action']:8} {ev['path']}"
        else:
            body = json.dumps({x: y for x, y in ev.items() if x not in ("id", "session_id", "ts", "source", "type")}, ensure_ascii=False)
        print(f"{t}  {k:13} {body}")

    # ── 백그라운드 전송 ──
    def _post_one(self, ev: dict) -> bool:
        try:
            requests.post(self.server + "/api/event", json=ev, timeout=2).raise_for_status()
            return True
        except requests.RequestException:
            return False

    def _send_loop(self):
        while True:
            ev = self._q.get()
            if ev is None:
                return
            if self._online is False and time.time() < self._next_retry:
                self._park(ev)              # 오프라인: 재시도 시각 전엔 바로 보관
                continue
            if self._post_one(ev):
                if self._online is not True:
                    self._online = True
                    print(f"        · 서버 연결됨 {self.server}")
                    self.flush_queue()
            else:
                if self._online is not False:
                    self._online = False
                    print(f"        · 서버 응답 없음 → queue.jsonl 에 보관, {self.RETRY_SEC}초마다 재시도")
                self._next_retry = time.time() + self.RETRY_SEC
                self._park(ev)

    def _park(self, ev: dict):
        with open(self.queue_path, "a", encoding="utf-8") as q:
            q.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def flush_queue(self):
        """서버가 살아나면 밀린 이벤트를 순서대로 재전송."""
        if not os.path.exists(self.queue_path):
            return
        with open(self.queue_path, encoding="utf-8") as q:
            lines = [l for l in q if l.strip()]
        sent = 0
        for l in lines:
            if not self._post_one(json.loads(l)):
                break
            sent += 1
        rest = lines[sent:]
        with open(self.queue_path, "w", encoding="utf-8") as q:
            q.writelines(rest)
        if sent:
            print(f"        · 밀린 이벤트 {sent}건 재전송, 남은 {len(rest)}건")

    def close(self):
        if self.server:
            self._q.put(None)
            self._worker.join(timeout=3)
        if self._log_f:
            self._log_f.close()


# ─────────────────────────── 수집기 본체 ───────────────────────────
class Collector:
    def __init__(self, cfg: dict, dry_run: bool):
        self.cfg = cfg
        self.clf = Classifier(os.path.join(HERE, "domains.json"))
        self.whitelist = {a.lower() for a in cfg.get("whitelist_apps", [])}
        data_dir = os.path.normpath(os.path.join(HERE, cfg.get("data_dir", "../data")))
        self.session_id = f"s_{datetime.now(KST):%Y-%m-%d_%H%M%S}"
        self.sink = Sink(data_dir, None if dry_run else cfg["server"], self.session_id)

        self.poll = float(cfg.get("poll_interval_sec", 1.0))
        self.idle_after = float(cfg.get("idle_after_sec", 300))
        self.hb_every = float(cfg.get("heartbeat_sec", 30))

        self._stop = threading.Event()
        self._cur = None          # (exe, title, category)
        self._idle = False
        self._last_hb = 0.0
        self._clip_hash = None
        self._clip_serial = None      # 클립보드 '번호' (내용을 안 읽고 변화만 안다)
        self._keys = None
        self._last_keys_flush = time.time()
        self._files = None

    # ── 분류 + 화이트리스트 ──
    def describe(self, exe: str, title: str) -> dict:
        # 화이트리스트 밖 앱은 분류·제목 없이 other 로만 남긴다 (기획안 §11 개인정보)
        if exe.lower() not in self.whitelist:
            return {"app": exe, "title": "", "category": "other"}
        return {"app": exe, "title": title, "category": self.clf.by_app(exe, title)}

    # ── 루프 ──
    def run(self):
        cfg = self.cfg
        print(f"Trace collector  session={self.session_id}  data={self.sink.data_dir}")
        print(f"  server={'(dry-run)' if not self.sink.server else self.sink.server}"
              f"  keys={'on' if cfg.get('keys', {}).get('enabled') else 'off'}"
              f"  files={cfg.get('files', {}).get('watch_dirs') or 'off'}")
        print("  Ctrl+C 로 종료\n")

        self.sink.emit({"type": "session_start", "idle_after_sec": self.idle_after})

        if cfg.get("clipboard", {}).get("enabled", True):
            self._clip_serial = osx.clipboard_serial()
            self._clip_hash = self._read_clip_hash()  # 시작 시점 클립보드는 이벤트로 안 잡음

        if cfg.get("keys", {}).get("enabled"):
            안내 = osx.input_permission_hint()
            if 안내:
                print("  ⚠️  " + 안내 + "\n")
            from keys import KeyCounter
            self._keys = KeyCounter(on_paste=self._on_paste,
                                    on_undo=lambda: self._on_edit("undo"),
                                    on_redo=lambda: self._on_edit("redo"),
                                    on_cut=lambda: self._on_edit("cut"))
            self._keys.start()

        fcfg = cfg.get("files", {})
        if fcfg.get("watch_dirs"):
            from file_watch import FileWatcher
            self._files = FileWatcher(fcfg["watch_dirs"], fcfg.get("ignore_patterns", []), self.sink.emit, base=HERE)
            self._files.start()

        try:
            while not self._stop.is_set():
                self._tick()
                self._stop.wait(self.poll)
        finally:
            self._shutdown()

    def _tick(self):
        now = time.time()

        # 1) 활성 창
        exe, title = foreground()
        d = self.describe(exe, title)
        key = (d["app"], d["title"], d["category"])
        if key != self._cur:
            self._flush_keys()      # 창이 바뀌기 전 입력 수를 이전 창에 귀속
            self._cur = key
            self.sink.emit({"type": "window", **d})

        # 2) 유휴
        idle = idle_seconds()
        if not self._idle and idle >= self.idle_after:
            self._idle = True
            self.sink.emit({"type": "idle_start", "idle_sec": int(idle)})
        elif self._idle and idle < self.idle_after:
            self._idle = False
            self.sink.emit({"type": "idle_end"})

        # 3) 클립보드 (복사)
        #    ★ 먼저 '번호'만 본다. 번호가 그대로면 내용을 아예 읽지 않는다.
        #      1초마다 남의 클립보드를 들여다보지 않기 위해서다. (기획안 §11)
        if self.cfg.get("clipboard", {}).get("enabled", True) and self._clip_changed():
            h = self._read_clip_hash()
            if h and h != self._clip_hash:
                self._clip_hash = h
                self.sink.emit({"type": "copy", "len": self._clip_len, "hash": h,
                                "app": self._cur[0], "category": self._cur[2]})

        # 4) 키 카운트 주기 flush
        if self._keys and now - self._last_keys_flush >= float(self.cfg["keys"].get("flush_sec", 10)):
            self._flush_keys()

        # 5) heartbeat — 끊기면 서버가 그 구간을 '공백'으로 표시
        if now - self._last_hb >= self.hb_every:
            self._last_hb = now
            self.sink.emit({"type": "heartbeat"})

    # ── 클립보드: 길이와 해시만 ──
    _clip_len = 0

    def _clip_changed(self) -> bool:
        """클립보드가 바뀌었나. 내용은 읽지 않고 '번호'만 본다.
        번호를 못 구하는 환경이면 늘 True (예전처럼 매번 읽는다)."""
        번호 = osx.clipboard_serial()
        if 번호 is None:
            return True
        if 번호 != self._clip_serial:
            self._clip_serial = 번호
            return True
        return False

    def _read_clip_hash(self):
        try:
            text = pyperclip.paste()
        except Exception:
            return None  # 다른 앱이 클립보드를 잠근 순간 — 다음 tick 에 다시
        if not text:
            return None  # 이미지 등 텍스트 아님
        self._clip_len = len(text)
        return sha256_text(text)

    # ── 붙여넣기 (keys.enabled 일 때만) ──
    def _on_paste(self):
        h = self._read_clip_hash()
        exe, title = foreground()
        self.sink.emit({"type": "paste", "len": self._clip_len if h else 0, "hash": h or "",
                        "app": exe, "target_title": title if exe.lower() in self.whitelist else ""})

    def _flush_keys(self):
        self._last_keys_flush = time.time()
        if not self._keys or not self._cur:
            return
        c = self._keys.pop_counts()
        if c["typed"] or c["deleted"]:
            self.sink.emit({"type": "keys", "count": c["typed"], "deleted": c["deleted"],
                            "app": self._cur[0], "category": self._cur[2]})

    def _on_edit(self, kind: str):
        """undo / redo / cut — 눌렸다는 사실만."""
        exe, _ = foreground()
        self.sink.emit({"type": kind, "app": exe})

    def stop(self):
        self._stop.set()

    def _shutdown(self):
        self._flush_keys()
        if self._keys:
            self._keys.stop()
        if self._files:
            self._files.stop()
        self.sink.emit({"type": "session_end"})
        self.sink.close()
        print("\n종료. 로컬 기록:", self.sink._log_path)


# ─────────────────────────── main ───────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Trace Tier 0 collector")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    ap.add_argument("--dry-run", action="store_true", help="서버로 보내지 않고 콘솔·로컬 파일만")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    c = Collector(cfg, dry_run=args.dry_run)
    signal.signal(signal.SIGINT, lambda *_: c.stop())
    try:
        signal.signal(signal.SIGBREAK, lambda *_: c.stop())  # Windows Ctrl+Break
    except AttributeError:
        pass
    c.run()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
