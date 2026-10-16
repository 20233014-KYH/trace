"""
downloads.py — 기록하는 동안 받은 결과물 파일 (10/15 박상진)

왜: Claude · ChatGPT 가 보고서를 대화 글이 아니라 **파일(PDF · Word)** 로만 주면 대화 기록엔 "만들었어요" 몇 줄뿐이라
    그 파일을 낸 학생의 결과물이 출처 보기에서 "출처 기록 없음" 으로 나왔다 (10/15 실제 시험 — 3쪽 PDF · 답 글 408자).
→ 다운로드 폴더에 새 결과물 파일이 생기면, 그 순간 앞에 있던 앱(AI 앱 · 브라우저)과 파일 지문 · 안의 글을 PC 에만 남긴다.
   출처 보기는 결과물 문장을 이 글과 비교해 "AI 앱에서 내려받은 파일" 로 칠한다 (core/match.process_evidence · how=download).

  · 다운로드 폴더만 (바탕화면 · 문서는 학생이 자기 글을 저장하는 곳이라 안 봄)
  · 그 순간 앞에 있던 앱이 브라우저나 AI 앱일 때만 — Word 로 내 보고서를 다운로드 폴더에 저장한 것을 "받은 파일" 로 오해하지 않게
  · 브라우저는 .crdownload · .tmp 로 받다가 이름을 바꾼다 → 바뀐 이름(dest)으로 · 크기가 1초 동안 안 바뀌면 다 받은 것
  · 서버 · 체인엔 안 감 (파일 이름 · 글은 PC context 에만)
"""
import hashlib
import os
import threading
import time

EXT = {".pdf", ".docx", ".txt", ".md", ".hwpx", ".pptx"}
MAX_BYTES = 30 * 1024 * 1024
MAX_TEXT = 300_000


def 다운로드_폴더():
    """윈도우 · 맥 모두 ~/Downloads (한국어 윈도우도 실제 폴더 이름은 Downloads)"""
    p = os.path.join(os.path.expanduser("~"), "Downloads")
    return [p] if os.path.isdir(p) else []


def 글_뽑기(path, raw):
    """결과물 파일 → 본문 글 (없으면 "") — 출처 보기와 같은 읽기 (core.pdftext · core.docx)"""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".pdf", ".docx"):
            from core.pdftext import read_doc
            return "\n".join(t for _, t in read_doc(raw))[:MAX_TEXT]
        if ext in (".txt", ".md"):
            return raw.decode("utf-8", "replace")[:MAX_TEXT]
    except Exception:                                   # noqa: BLE001  깨진 파일 — 지문만 남김
        pass
    return ""


class DownloadWatcher:
    def __init__(self, dirs, on_file):
        """on_file(path, raw) — 다 받은 결과물 파일마다 한 번"""
        self.dirs, self._on_file = dirs, on_file
        self._obs, self._seen, self._lock = None, set(), threading.Lock()

    def start(self):
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
        w = self

        class H(FileSystemEventHandler):
            def on_created(self, e):
                if not e.is_directory:
                    w._후보(e.src_path)

            def on_moved(self, e):                       # 브라우저: x.pdf.crdownload → x.pdf
                if not e.is_directory:
                    w._후보(e.dest_path)

        self._obs = Observer()
        for d in self.dirs:
            self._obs.schedule(H(), d, recursive=False)
        self._obs.start()

    def stop(self):
        if self._obs:
            self._obs.stop()

    def _후보(self, path):
        name = os.path.basename(path)
        if os.path.splitext(name)[1].lower() not in EXT or name.startswith(("~$", ".")):
            return
        with self._lock:
            if path in self._seen:
                return
            self._seen.add(path)
        threading.Thread(target=self._다_받으면, args=(path,), daemon=True, name="download").start()

    def _다_받으면(self, path):
        전 = -1
        for _ in range(120):                             # 최대 2분
            try:
                지금 = os.path.getsize(path)
            except OSError:
                return                                   # 사라짐 (임시 파일)
            if 지금 == 전 and 지금 > 0:
                break
            전 = 지금
            time.sleep(1)
        if 전 <= 0 or 전 > MAX_BYTES:
            return
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError:
            return
        self._on_file(path, raw)


def 지문(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()
