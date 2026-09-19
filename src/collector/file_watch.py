"""
file_watch.py — 감시 폴더의 파일 생성·수정·삭제·이동을 잡는다 (watchdog).

기록: 경로, 동작, 저장 시 내용 SHA256 (내용 자체는 저장 안 함).
에디터는 저장 한 번에 modified 를 여러 번 쏘므로 경로별 1초 디바운스.
"""
import fnmatch
import hashlib
import os
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

_MAX_HASH_BYTES = 5 * 1024 * 1024  # 5MB 넘으면 해시 생략


def _sha256(path: str) -> str | None:
    try:
        if os.path.getsize(path) > _MAX_HASH_BYTES:
            return None
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return "sha256:" + h.hexdigest()
    except OSError:
        return None


class _Handler(FileSystemEventHandler):
    def __init__(self, emit, ignore):
        self._emit = emit
        self._ignore = ignore
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def _skip(self, path: str) -> bool:
        return any(p in path or fnmatch.fnmatch(os.path.basename(path), p) for p in self._ignore)

    def _fire(self, action: str, path: str, dest: str | None = None):
        if self._skip(path):
            return
        now = time.time()
        with self._lock:
            if action == "modified" and now - self._last.get(path, 0) < 1.0:
                return
            self._last[path] = now
        ev = {"type": "file", "action": action, "path": path.replace("\\", "/")}
        if dest:
            ev["dest"] = dest.replace("\\", "/")
        if action in ("created", "modified"):
            ev["content_hash"] = _sha256(path)
        self._emit(ev)

    def on_created(self, e):
        if not e.is_directory: self._fire("created", e.src_path)

    def on_modified(self, e):
        if not e.is_directory: self._fire("modified", e.src_path)

    def on_deleted(self, e):
        if not e.is_directory: self._fire("deleted", e.src_path)

    def on_moved(self, e):
        if not e.is_directory: self._fire("moved", e.src_path, e.dest_path)


class FileWatcher:
    def __init__(self, dirs: list[str], ignore: list[str], emit, base: str = "."):
        self._obs = Observer()
        self._obs.daemon = True
        h = _Handler(emit, ignore)
        self.dirs = []
        for d in dirs:
            d = os.path.abspath(os.path.join(base, os.path.expanduser(d)))
            if os.path.isdir(d):
                self._obs.schedule(h, d, recursive=True)
                self.dirs.append(d)

    def start(self):
        if self.dirs:
            self._obs.start()

    def stop(self):
        if self.dirs:
            self._obs.stop()
            self._obs.join(timeout=2)
