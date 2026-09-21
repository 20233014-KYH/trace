"""
file_diff.py — 저장된 텍스트 파일을 이전 내용과 비교한다. 에디터가 무엇이든(VS Code · IntelliJ · 메모장) 상관없다.

Office(office.py)가 Word 문단을 보는 것과 같은 일을, 파일 저장 단위로 한다.
  이벤트(두 모드 · 체인):  doc_change    {app, file, where:"12~15행", added, removed}
                          doc_paste_at  {app, file, where}     — 저장 직전 3초 안에 Ctrl+V 가 있었고 늘어난 글자가 그만큼이면
  맥락(Learn 만):          diff          새로 들어온 줄들 (≤500자) · meta {file, line, chars}
                          paste_at      붙여넣은 줄들 (≤200자)

내용은 이 프로세스 메모리에만 있다(이전 스냅샷). 파일 전체를 서버로 보내지 않는다.
바이너리·큰 파일(>512KB)·ignore 패턴은 건너뛴다. 시작할 때 감시 폴더를 한 번 훑어 기준 스냅샷을 만든다 (최대 3000개).
"""
import difflib
import os
import time

TEXT_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".kt", ".swift",
            ".html", ".htm", ".css", ".scss", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sql", ".sh", ".bat", ".ps1",
            ".tex", ".r", ".m", ".dart", ".php", ".rb", ".lua", ".vue", ".svelte", ".xml", ".csv"}
MAX_BYTES = 512 * 1024
MAX_FILES = 3000
MAX_DIFF, MAX_PASTE = 500, 200
PASTE_WINDOW_SEC = 3.0


def _read(path: str) -> str | None:
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, "rb") as f:
            raw = f.read()
        if b"\x00" in raw[:4096]:              # 바이너리
            return None
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return None


def is_text(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in TEXT_EXT


class FileDiff:
    def __init__(self, emit_event, active_app, last_paste, emit_context=None, note=print):
        """emit_event(ev) 체인 이벤트 · active_app() → 앞 창 exe · last_paste() → (time, len) 마지막 Ctrl+V · emit_context(items) Learn 만"""
        self.emit_event, self.emit_context, self.active_app, self.last_paste, self.note = emit_event, emit_context, active_app, last_paste, note
        self._snap: dict[str, str] = {}

    def baseline(self, dirs: list[str], skip) -> int:
        """시작 스냅샷 — 이후 첫 저장부터 diff 가 나온다."""
        n = 0
        for d in dirs:
            for root, subdirs, files in os.walk(d):
                subdirs[:] = [s for s in subdirs if not skip(os.path.join(root, s))]
                for fn in files:
                    p = os.path.join(root, fn)
                    if n >= MAX_FILES:
                        return n
                    if skip(p) or not is_text(p):
                        continue
                    t = _read(p)
                    if t is not None:
                        self._snap[p] = t
                        n += 1
        return n

    def on_saved(self, path: str):
        if not is_text(path):
            return
        new = _read(path)
        if new is None:
            return
        old = self._snap.get(path)
        self._snap[path] = new
        if old is None or old == new:
            return
        added_lines, removed_lines, first, added, removed = _line_diff(old, new)
        if not added and not removed:
            return
        app, file = self.active_app() or "", os.path.basename(path)
        where = f"{first}행" if first else ""
        self.emit_event({"type": "doc_change", "app": app, "file": file, "where": where, "added": added, "removed": removed})
        items = []
        added_text = "\n".join(added_lines).strip()
        if added_text:
            items.append(_item("diff", added_text[:MAX_DIFF], {"app": app, "file": file, "line": first, "chars": added}))
        # 붙여넣기 판정 — 직전 3초 안 Ctrl+V 의 글자 수와 늘어난 글자 수가 비슷하면
        lp = self.last_paste()
        if lp and time.time() - lp[0] <= PASTE_WINDOW_SEC and lp[1] > 0 and added >= lp[1] * 0.8:
            self.emit_event({"type": "doc_paste_at", "app": app, "file": file, "where": where})
            items.append(_item("paste_at", added_text[:MAX_PASTE], {"app": app, "file": file, "line": first}))
        if items and self.emit_context:
            self.emit_context(items)


def _line_diff(old: str, new: str):
    """줄 단위 비교 → (추가된 줄들, 삭제된 줄들, 첫 변경 행, +글자, -글자).
    한 줄이 한 줄로 바뀐 경우는 글자 단위로 다시 세서 'User user;' → 'User user = new User();' 가 +13/-0 이 되게."""
    a, b = old.splitlines(), new.splitlines()
    added, removed, first, plus, minus = [], [], 0, 0, 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if not first:
            first = j1 + 1
        if tag == "replace" and i2 - i1 == j2 - j1:
            for x, y in zip(a[i1:i2], b[j1:j2]):
                ins = _added_part(x, y)
                plus += len(ins)
                minus += max(0, len(x) - (len(y) - len(ins)))
                added.append(ins if ins else y)
            continue
        if tag in ("replace", "delete"):
            removed += a[i1:i2]; minus += sum(len(l) for l in a[i1:i2])
        if tag in ("replace", "insert"):
            added += b[j1:j2]; plus += sum(len(l) for l in b[j1:j2])
    return added, removed, first, plus, minus


def _added_part(old: str, new: str) -> str:
    """old → new 에서 새로 들어온 글자만 (공통 접두·접미를 뗀 가운데). office.py 와 같은 정의."""
    i = 0
    while i < min(len(old), len(new)) and old[i] == new[i]:
        i += 1
    j = 0
    while j < min(len(old), len(new)) - i and old[-1 - j] == new[-1 - j]:
        j += 1
    return new[i:len(new) - j]


def _item(kind: str, text: str, meta: dict) -> dict:
    import uuid
    from datetime import datetime, timedelta, timezone
    kst = timezone(timedelta(hours=9))
    return {"id": str(uuid.uuid4()), "ts": datetime.now(kst).isoformat(timespec="seconds"), "source": "editor", "kind": kind, "text": text, "meta": meta}
