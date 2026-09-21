"""
collector.py — Trace Tier 0 수집기 (윈도우 · 맥 상주 프로그램)

무엇을 잡나:
  · 세션 시작·종료 · 유휴(5분 무입력) · heartbeat(30초)
  · 활성 창의 앱 이름 + 창 제목 (1초 폴링, 화이트리스트 앱만 제목 저장)
  · 클립보드 변경 → 길이와 SHA256 만 (원문 저장 안 함)
  · 입력·삭제 횟수, Ctrl+V / Ctrl+Z / Ctrl+Y / Ctrl+X 감지 — config.keys.enabled (Proof 필수)
  · (옵션) 감시 폴더 파일 생성·수정·저장 — config.files.watch_dirs
  · Word · PowerPoint 문서 변화 — office.py (COM). 숫자(+n자/-m자 · 붙여넣은 자리 · 저장 통계)는 두 모드, 텍스트는 Learn 만

무엇을 안 하나: 화면 캡처, 키 내용, 클립보드 원문, 창 제목 밖의 문서 내용.

흐름 (API 계약 ③ · 9/20 합의):
  이벤트 생성 → PC에서 체인 해시 계산(core/chain.py) → ../data/events-날짜.jsonl 에 먼저 기록(로컬 우선)
             → 5초/50건 batch 로 POST /api/sessions/{id}/events  (+ chain_head)
             → 서버가 꺼져 있으면 ../data/queue.jsonl 에 순서대로 보관, 10초마다 재시도
  시작: POST /api/works/{work}/sessions      종료: POST /api/sessions/{id}/end (root)

실행:
  python collector.py                          # config.json 의 mode / work_id / server
  python collector.py --mode learn --work W1
  python collector.py --dry-run                # 서버 없이 콘솔 + 로컬 파일만
"""
import argparse
import hashlib
import json
import os
import platform
import queue
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta

import pyperclip
import requests

# ── 운영체제에 따라 맞는 파일을 불러온다 ────────────────────────────
#   platform_win.py / platform_mac.py 는 같은 이름의 함수를 갖는다:
#     foreground()  idle_seconds()  input_permission_hint()
#   나머지(클립보드 pyperclip · 키 pynput · 파일 watchdog)는 양쪽 다 돈다.
if sys.platform == "win32":
    import platform_win as osx
elif sys.platform == "darwin":
    import platform_mac as osx
else:
    sys.exit(f"맥과 윈도우만 지원합니다 (지금: {sys.platform}).")

foreground = osx.foreground
idle_seconds = osx.idle_seconds

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # ../core
from core import chain as C          # noqa: E402
from classify import Classifier      # noqa: E402

VERSION = "0.2.0"
BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe"}   # 확장 탭 분류를 창 분류에 우선 적용하는 앱 (derive.py 와 같음)
KST = timezone(timedelta(hours=9))


def now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8", "surrogatepass")).hexdigest()


# ─────────────────────────── 전송 (백그라운드) ───────────────────────────
class Sender(threading.Thread):
    """op 를 순서대로 서버에 보낸다. op = {"op":"session"|"events"|"end", ...}
    오프라인이면 queue.jsonl 에 보관했다가 살아나면 같은 순서로 재전송. 메인 스레드는 절대 네트워크를 안 탄다."""

    RETRY_SEC = 10
    BATCH_SEC = 5
    BATCH_MAX = 50

    def __init__(self, base: str, session_id: str, work_id: str, queue_path: str):
        super().__init__(daemon=True)
        self.base, self.sid, self.work, self.queue_path = base.rstrip("/"), session_id, work_id, queue_path
        self.q: queue.Queue = queue.Queue()
        self.online = None
        self._next_retry = 0.0
        self.head = C.GENESIS
        self.chain_len = 0

    # 메인 스레드에서 호출
    def session_start(self, payload):  self.q.put({"op": "session", "sid": self.sid, "work": self.work, "body": payload})
    def event(self, ev):               self.q.put({"op": "event", "ev": ev})
    def end(self, payload):            self.q.put({"op": "end", "sid": self.sid, "body": payload}); self.q.put(None)
    def context(self, items):          self.q.put({"op": "context", "sid": self.sid, "items": items})

    # ── 루프: 이벤트를 5초/50건으로 묶는다 ──
    def run(self):
        pending, t0 = [], time.time()
        while True:
            try:
                item = self.q.get(timeout=0.5)
            except queue.Empty:
                item = "tick"
            if item is None:
                self._flush_events(pending); pending = []
                self._drain_remaining()
                return
            if item == "tick":
                if pending and time.time() - t0 >= self.BATCH_SEC:
                    self._flush_events(pending); pending, t0 = [], time.time()
                continue
            if item["op"] == "event":
                if not pending:
                    t0 = time.time()
                pending.append(item["ev"])
                if len(pending) >= self.BATCH_MAX:
                    self._flush_events(pending); pending, t0 = [], time.time()
            else:                       # session / end 는 순서를 지켜야 하므로 앞의 이벤트를 먼저 보냄
                self._flush_events(pending); pending = []
                self._send_or_park(item)

    def _drain_remaining(self):
        while not self.q.empty():
            item = self.q.get_nowait()
            if item and item != "tick" and item["op"] != "event":
                self._send_or_park(item)

    def _flush_events(self, evs):
        if not evs:
            return
        self._send_or_park({"op": "events", "sid": self.sid, "events": evs, "chain_head": self.head, "chain_len": self.chain_len})

    # ── 전송 ──
    def _post(self, path, body):
        r = requests.post(self.base + path, json=body, timeout=3)
        r.raise_for_status()
        return r.json() if r.content else {}

    def _send(self, op) -> dict:
        """op 는 자기 세션 id 를 갖는다 — 큐에서 나온 옛 세션 op 가 새 세션으로 가면 안 된다."""
        k, sid = op["op"], op.get("sid", self.sid)
        if k == "session":
            return self._post(f"/works/{op.get('work', self.work)}/sessions", op["body"])
        if k == "events":
            return self._post(f"/sessions/{sid}/events",
                              {"events": op["events"], "chain_head": op["chain_head"], "chain_len": op["chain_len"]})
        if k == "end":
            return self._post(f"/sessions/{sid}/end", op["body"])
        if k == "context":
            return self._post(f"/sessions/{sid}/context", {"items": op["items"]})
        return {}

    def _send_or_park(self, op):
        if self.online is False and time.time() < self._next_retry:
            return self._park(op)
        if self.online is not True:            # 처음이거나 재시도 시각 도달
            if not self._flush_queue():        # 밀린 게 안 나가면 지금 것도 보관
                return self._park(op)
        try:
            res = self._send(op)
            self._mark_online()
            self._report(op, res)
        except requests.HTTPError as e:            # 서버가 살아 있고 거절함 → 재시도 안 함
            self._mark_online()
            self._rejected(op, e)
        except requests.RequestException:          # 연결 실패 → 보관
            self._mark_offline()
            self._park(op)

    def _mark_online(self):
        if self.online is not True:
            self.online = True
            print(f"        · 서버 연결됨 {self.base}")

    def _mark_offline(self):
        if self.online is not False:
            self.online = False
            print(f"        · 서버 응답 없음 → queue.jsonl 에 보관, {self.RETRY_SEC}초마다 재시도")
        self._next_retry = time.time() + self.RETRY_SEC

    def _rejected(self, op, e: requests.HTTPError):
        code = e.response.status_code if e.response is not None else "?"
        try:
            body = e.response.json()
        except Exception:
            body = {}
        what = {"session": "세션 등록", "events": f"batch {len(op.get('events', []))}건", "end": "봉인", "context": f"맥락 {len(op.get('items', []))}건"}.get(op["op"], op["op"])
        print(f"        · {what} 거절됨 HTTP {code} {body.get('error', '')} — 로컬 기록은 남아 있음"
              + (f" (server_root {body['server_root'][:8]}…)" if body.get("server_root") else ""))

    def _report(self, op, res):
        if op["op"] == "events" and res:
            v = res.get("verified")
            tag = "체인 일치" if v else ("체인 불일치 ⚠" if v is False else "")
            print(f"        · batch {len(op['events'])}건 전송 {tag}")
        elif op["op"] == "context" and res:
            print(f"        · 맥락 {res.get('accepted', 0)}건 전송")
        elif op["op"] == "end" and res:
            print(f"        · 봉인 {'검증됨' if res.get('verified') else '검증 실패 ⚠'} · 지연 배치 {res.get('late_batches', 0)} · 앵커 {res.get('anchor', {}).get('status', '-')}")

    # ── 오프라인 큐 ──
    def _park(self, op):
        with open(self.queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(op, ensure_ascii=False) + "\n")

    def _flush_queue(self) -> bool:
        """큐를 순서대로 재전송. 전부 나가면 True. 하나라도 실패하면 나머지를 남기고 False."""
        if not os.path.exists(self.queue_path):
            try:
                requests.get(self.base + "/health", timeout=3)
            except requests.RequestException:
                self._mark_offline(); return False
            self._mark_online(); return True
        with open(self.queue_path, encoding="utf-8") as f:
            ops = [json.loads(l) for l in f if l.strip()]
        sent = 0
        for op in ops:
            try:
                self._send(op); sent += 1
            except requests.HTTPError as e:
                self._rejected(op, e); sent += 1   # 거절된 건 다시 보내도 같으니 버린다
            except requests.RequestException:
                break
        with open(self.queue_path, "w", encoding="utf-8") as f:
            for op in ops[sent:]:
                f.write(json.dumps(op, ensure_ascii=False) + "\n")
        if sent:
            print(f"        · 밀린 {sent}건 재전송, 남은 {len(ops) - sent}건")
        if sent == len(ops):
            os.remove(self.queue_path); self._mark_online(); return True
        self._mark_offline(); return False


# ─────────────────────────── 이벤트 저장 ───────────────────────────
class Sink:
    """이벤트에 체인 해시를 붙여 로컬 jsonl 에 먼저 쓰고, Sender 에 넘긴다."""

    def __init__(self, data_dir: str, session_id: str, sender: Sender | None):
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir, self.session_id, self.sender = data_dir, session_id, sender
        self._seq = 0
        self._lock = threading.Lock()
        self._log_path = self._log_f = None
        self.head = C.GENESIS
        self.chain_len = 0

    def _local_file(self):
        p = os.path.join(self.data_dir, f"events-{datetime.now(KST):%Y-%m-%d}.jsonl")
        if p != self._log_path:
            if self._log_f:
                self._log_f.close()
            self._log_path, self._log_f = p, open(p, "a", encoding="utf-8")
        return self._log_f

    def emit(self, ev: dict):
        with self._lock:
            self._seq += 1
            ev = {"id": f"evt_{self._seq:06d}", "session_id": self.session_id,
                  "ts": now_iso(), "source": "collector", **ev}
            if C.in_chain(ev):                      # PC 에서 체인 계산 (서버가 같은 함수로 재계산해 대조)
                self.head = C.next_hash(self.head, ev)
                self.chain_len += 1
                ev["h"] = self.head
            f = self._local_file()
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            f.flush()
            if self.sender:
                self.sender.head, self.sender.chain_len = self.head, self.chain_len
        self._print(ev)
        if self.sender:
            self.sender.event(ev)

    def _print(self, ev):
        t, k = ev["ts"][11:19], ev["type"]
        if k == "window":
            body = f"[{ev['category']:8}] {ev['app']:18} {ev.get('title', '')[:60]}"
        elif k in ("copy", "paste"):
            body = f"len={ev['len']:5}  {ev['hash'][:23]}…  app={ev.get('app', '')}"
        elif k == "keys":
            body = f"typed={ev['count']}  deleted={ev.get('deleted', 0)}  app={ev.get('app', '')}"
        elif k == "file":
            body = f"{ev['action']:8} {ev['path']}"
        elif k == "commit":
            body = f"{ev['repo']} · {ev['hash'][:7]} ({ev.get('branch','')}) · {ev['files']}파일 +{ev['added']}/-{ev['removed']}"
        elif k == "git_push":
            body = f"{ev['repo']} · {ev['remote_ref']} → {ev['hash'][:7]}"
        elif k == "tab":
            body = f"[{ev['category']:8}] {ev['domain']:18} {ev.get('title', '')[:50]}  (확장)"
        elif k == "doc_change":
            body = f"{ev['app']} · {ev['file'][:30]} · {ev['where']}  +{ev['added']}자 / -{ev['removed']}자"
        elif k == "doc_paste_at":
            body = f"{ev['app']} · {ev['file'][:30]} · 붙여넣은 자리: {ev['where']}"
        elif k == "doc_save":
            body = f"{ev['app']} · {ev['file'][:30]} · 저장 · " + " · ".join(f"{k2} {v}" for k2, v in ev.items() if k2 in ('chars', 'words', 'slides', 'paragraphs'))
        elif k == "heartbeat":
            body = ""
        else:
            body = json.dumps({x: y for x, y in ev.items() if x not in ("id", "session_id", "ts", "source", "type", "h")}, ensure_ascii=False)
        h = f"  h={ev['h'][:8]}" if "h" in ev else ""
        print(f"{t}  {k:13} {body}{h}")

    def close(self):
        if self._log_f:
            self._log_f.close()


# ─────────────────────────── 수집기 본체 ───────────────────────────
class Collector:
    def __init__(self, cfg: dict, mode: str, work_id: str, dry_run: bool):
        self.cfg, self.mode, self.work_id = cfg, mode, work_id
        self.clf = Classifier(os.path.join(HERE, "domains.json"))
        self.whitelist = {a.lower() for a in cfg.get("whitelist_apps", [])}
        data_dir = os.path.normpath(os.path.join(HERE, cfg.get("data_dir", "../data")))
        self.session_id = str(uuid.uuid4())
        self.sender = None if dry_run else Sender(cfg["server"], self.session_id, work_id, os.path.join(data_dir, "queue.jsonl"))
        self.sink = Sink(data_dir, self.session_id, self.sender)

        self.poll = float(cfg.get("poll_interval_sec", 1.0))
        self.idle_after = float(cfg.get("idle_after_sec", 300))
        self.hb_every = float(cfg.get("heartbeat_sec", 30))

        self._stop = threading.Event()
        self._cur = None
        self._idle = False
        self._last_hb = 0.0
        self._clip_hash = None
        self._clip_len = 0
        self._copy_win = None       # Ctrl+C 누른 순간의 (app, category)
        self._last_paste = None     # (time, len) 마지막 Ctrl+V — 저장 파일 diff 가 붙여넣은 자리 판정에 씀
        self._fdiff = None
        self._git = None
        self._copy_at = 0.0
        self._copies = {}          # hash → (app, category)  콘솔 힌트용 (판단은 서버·derive 가 한다)
        self._keys = None
        self._last_keys_flush = time.time()
        self._files = None
        self._bridge = None
        self._tab = None            # 확장이 알려준 현재 탭 (domain, category, title)
        self._office = None         # Learn 모드 · Word/PPT 맥락 (office.py)

    def describe(self, exe: str, title: str) -> dict:
        # 화이트리스트 밖 앱은 분류·제목 없이 other 로만 남긴다 (개인정보)
        if exe.lower() not in self.whitelist:
            return {"app": exe, "title": "", "category": "other"}
        cat = self.clf.by_app(exe, title)
        # 브라우저는 확장이 알려준 탭 도메인이 창 제목보다 정확하다 — ChatGPT 가 대화 제목으로 창 제목을 바꿔도 ai 유지
        if exe.lower() in BROWSERS and self._tab and cat == "other":
            cat = self._tab[1]
        return {"app": exe, "title": title, "category": cat}

    def run(self):
        cfg = self.cfg
        print(f"Trace collector v{VERSION}  mode={self.mode}  work={self.work_id}  session={self.session_id[:8]}…")
        print(f"  server={'(dry-run)' if not self.sender else cfg['server']}"
              f"  keys={'on' if cfg.get('keys', {}).get('enabled') else 'off'}"
              f"  files={cfg.get('files', {}).get('watch_dirs') or 'off'}  data={self.sink.data_dir}")
        print("  Ctrl+C 로 종료 (봉인)\n")

        if self.sender:
            self.sender.start()
            self.sender.session_start({"id": self.session_id, "mode": self.mode, "started_at": now_iso(),
                                       "device": {"name": platform.node(), "os": "win", "collector_version": VERSION}})
        self.sink.emit({"type": "session_start", "mode": self.mode, "work_id": self.work_id, "idle_after_sec": self.idle_after})

        if cfg.get("clipboard", {}).get("enabled", True):
            self._clip_hash = self._read_clip_hash()
        if cfg.get("keys", {}).get("enabled"):
            안내 = osx.input_permission_hint()
            if 안내:
                print("  ⚠️  " + 안내 + "\n")
            from keys import KeyCounter
            self._keys = KeyCounter(on_paste=self._on_paste,
                                    on_undo=lambda: self._on_edit("undo"),
                                    on_redo=lambda: self._on_edit("redo"),
                                    on_cut=lambda: self._on_edit("cut"),
                                    on_copy=self._on_copy_key)
            self._keys.start()
        if cfg.get("bridge", {}).get("enabled", True):
            import bridge
            try:
                self._bridge = bridge.start(self._on_tab, self._on_context, self._status)
                print(f"  확장 다리 http://127.0.0.1:{bridge.PORT}  (브라우저 확장 → tab · context)")
            except OSError as e:
                print(f"  확장 다리 실패 ({e}) — 확장 없이 계속")
        # Office 맥락은 윈도우 COM(pythoncom) 전용이다. 맥에서는 건너뛴다.
        # (import 는 office.py 의 스레드 안에서 일어나서 try 로 안 잡힌다)
        if cfg.get("office", {}).get("enabled", True) and sys.platform == "win32":
            try:
                from office import OfficeWatcher
                with_text = self.mode == "learn" and cfg.get("learn_context", {}).get("office", False)
                self._office = OfficeWatcher(self.sink.emit, lambda exe: bool(self._cur) and self._cur[0].lower() == exe.lower(),
                                             poll_sec=cfg.get("office", {}).get("poll_sec", 5),
                                             emit_context=self._on_context if with_text else None)
                self._office.start()
                print(f"  Office 문서 변화 켜짐 (Word · PowerPoint · 숫자{' + 텍스트 맥락' if with_text else '만'})")
            except Exception as e:
                print(f"  Office 감시 실패 ({e}) — 없이 계속")
        fcfg = cfg.get("files", {})
        if fcfg.get("watch_dirs"):
            from file_watch import FileWatcher
            on_saved = None
            if fcfg.get("diff", True):
                # 저장 파일 diff — 에디터 무관. 숫자는 두 모드 체인에, 바뀐 텍스트는 Learn 맥락으로만 (Office 와 같은 원칙)
                from file_diff import FileDiff
                self._fdiff = FileDiff(self.sink.emit, lambda: self._cur[0] if self._cur else "", lambda: self._last_paste,
                                       emit_context=self._on_context if self.mode == "learn" else None)
                on_saved = self._fdiff.on_saved
            self._files = FileWatcher(fcfg["watch_dirs"], fcfg.get("ignore_patterns", []), self.sink.emit, base=HERE, on_saved=on_saved)
            if on_saved:
                n = self._fdiff.baseline(self._files.dirs, self._files.skip)
                print(f"  저장 파일 diff 켜짐 · 기준 스냅샷 {n}개 (텍스트 파일 · 내용은 메모리에만)")
            self._files.start()
            if fcfg.get("git", True):
                # git 커밋·푸시 — 숫자(해시·파일·줄 수)는 체인, 커밋 메시지는 Learn 맥락만 (결정 13)
                from git_watch import GitWatcher
                self._git = GitWatcher(self._files.dirs, self.sink.emit, emit_context=self._on_context if self.mode == "learn" else None)
                if self._git.repos:
                    self._git.start()
                    print(f"  git 감시 켜짐 · 저장소 {len(self._git.repos)}개 ({', '.join(os.path.basename(r) for r in self._git.repos[:5])})")
                else:
                    print("  git 감시: 감시 폴더에 저장소 없음 (또는 git 미설치)")

        try:
            while not self._stop.is_set():
                self._tick()
                self._stop.wait(self.poll)
        finally:
            self._shutdown()

    def _tick(self):
        now = time.time()
        exe, title = foreground()
        d = self.describe(exe, title)
        key = (d["app"], d["title"], d["category"])
        if key != self._cur:
            self._flush_keys()
            self._cur = key
            self.sink.emit({"type": "window", **d})

        idle = idle_seconds()
        if not self._idle and idle >= self.idle_after:
            self._idle = True
            self.sink.emit({"type": "idle_start", "idle_sec": int(idle)})
        elif self._idle and idle < self.idle_after:
            self._idle = False
            self.sink.emit({"type": "idle_end"})

        if self.cfg.get("clipboard", {}).get("enabled", True):
            h = self._read_clip_hash()
            if h and h != self._clip_hash:
                self._clip_hash = h
                # Ctrl+C 를 누른 순간의 창을 쓴다 — 누르고 바로 작업표시줄을 클릭하면 폴링 시점엔 explorer.exe 가 앞에 있어서
                src = self._copy_win if (self._copy_win and now - self._copy_at < 3) else (self._cur[0], self._cur[2])
                self._copy_win = None
                self._copies[h] = src
                self.sink.emit({"type": "copy", "len": self._clip_len, "hash": h,
                                "app": src[0], "category": src[1]})

        if self._keys and now - self._last_keys_flush >= float(self.cfg["keys"].get("flush_sec", 10)):
            self._flush_keys()

        if now - self._last_hb >= self.hb_every:
            self._last_hb = now
            self.sink.emit({"type": "heartbeat"})

    def _read_clip_hash(self):
        try:
            text = pyperclip.paste()
        except Exception:
            return None
        if not text:
            return None
        self._clip_len = len(text)
        return sha256_text(text)

    def _on_copy_key(self):
        """Ctrl+C — 창만 기억. 실제 copy 이벤트는 클립보드가 바뀐 걸 확인한 _tick 이 낸다."""
        if self._cur:
            self._copy_win, self._copy_at = (self._cur[0], self._cur[2]), time.time()

    def _on_paste(self):
        h = self._read_clip_hash()
        exe, title = foreground()
        self.sink.emit({"type": "paste", "len": self._clip_len if h else 0, "hash": h or "",
                        "app": exe, "target_title": title if exe.lower() in self.whitelist else ""})
        self._last_paste = (time.time(), self._clip_len if h else 0)
        src = self._copies.get(h)
        if src:
            print(f"        ↳ {src[0]}({src[1]}) 에서 복사한 것과 같은 해시")
        if self._office:
            self._office.on_paste()

    def _on_edit(self, kind: str):
        exe, _ = foreground()
        self.sink.emit({"type": kind, "app": exe})

    def _flush_keys(self):
        self._last_keys_flush = time.time()
        if not self._keys or not self._cur:
            return
        c = self._keys.pop_counts()
        if c["typed"] or c["deleted"]:
            self.sink.emit({"type": "keys", "count": c["typed"], "deleted": c["deleted"],
                            "app": self._cur[0], "category": self._cur[2]})

    # ── 브라우저 확장 (bridge) ──
    def _status(self):
        return {"session_id": self.session_id, "mode": self.mode, "work_id": self.work_id, "recording": not self._stop.is_set(),
                "learn_context": self.cfg.get("learn_context", {})}

    def _on_tab(self, body):
        """확장이 보낸 탭 전환. 도메인으로 분류해 체인에 넣는다 (창 제목 키워드보다 정확)."""
        domain = (body.get("domain") or "").lower()
        cat = self.clf.by_domain(domain) if domain else "other"   # "" = 새 탭·chrome:// 등 내부 페이지
        self._tab = (domain, cat, body.get("title", ""))
        self.sink.emit({"type": "tab", "domain": domain, "category": cat, "title": (body.get("title") or "")[:80]})

    def _on_context(self, items):
        """Learn 맥락 — 체인에 안 넣고 서버 /context 로만. 로컬에도 남긴다."""
        for it in items:
            print(f"        ↳ 맥락 {it.get('kind')}  {(it.get('text') or '')[:40]!r}")
        if self.sender:
            self.sender.context(items)
        with open(os.path.join(self.sink.data_dir, f"context-{datetime.now(KST):%Y-%m-%d}.jsonl"), "a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps({"session_id": self.session_id, **it}, ensure_ascii=False) + "\n")

    def stop(self):
        self._stop.set()

    def _shutdown(self):
        self._flush_keys()
        if self._keys:
            self._keys.stop()
        if self._files:
            self._files.stop()
        if self._git:
            self._git.stop()
        if self._bridge:
            self._bridge.shutdown()
        if self._office:
            self._office.stop()
        self.sink.emit({"type": "session_end"})
        root, n = self.sink.head, self.sink.chain_len
        print(f"\n체인 {n}건 · 루트 {root[:16]}…")
        if self.sender:
            self.sender.end({"ended_at": now_iso(), "chain_len": n, "root": root})
            self.sender.join(timeout=8)
        self.sink.close()
        print("종료. 로컬 기록:", self.sink._log_path)


def main():
    ap = argparse.ArgumentParser(description="Trace Tier 0 collector")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    ap.add_argument("--mode", choices=["proof", "learn"], help="기본: config.mode")
    ap.add_argument("--work", help="work id (기본: config.work_id)")
    ap.add_argument("--dry-run", action="store_true", help="서버로 보내지 않고 콘솔·로컬 파일만")
    ap.add_argument("--seconds", type=int, default=0, help="테스트용: N초 뒤 자동 종료(봉인)")
    a = ap.parse_args()
    with open(a.config, encoding="utf-8") as f:
        cfg = json.load(f)
    c = Collector(cfg, a.mode or cfg.get("mode", "proof"), a.work or cfg.get("work_id", "W_local"), a.dry_run)
    signal.signal(signal.SIGINT, lambda *_: c.stop())
    try:
        signal.signal(signal.SIGBREAK, lambda *_: c.stop())
    except AttributeError:
        pass
    if a.seconds:
        threading.Timer(a.seconds, c.stop).start()
    c.run()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
