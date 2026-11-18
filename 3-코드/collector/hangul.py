"""
hangul.py — 한글(한컴오피스) 문서 변화 수집 · 저장할 때마다 (11/18 · 최종 발표 전)

Word 는 실행 중인 프로그램을 몇 초마다 직접 읽지만(office.py · office_mac.py) 한글은 그런 길이 없어서,
**한글이 앞에 있을 때 열린 문서 파일을 몇 초마다 보고, 저장돼 바뀌었으면 읽어서** 문단마다 바뀐 글을 낸다.
내는 것은 Word 와 같은 모양 (doc_change · doc_save · doc_open · diff · doc_path) — 출처 보기 · 내역서가 그대로 쓴다.

  · 문서 위치: 맥 = 앞 창의 AXDocument (파일 주소) · 윈도우 = 창 제목의 파일 이름을 흔한 자리에서 찾음
  · 글 읽기: core/hwp.py (.hwpx · .hwp)
  · 처음 본 문서: 기록을 켠 뒤 만든 파일이면 빈 문서에서 시작 (쓴 글이 모두 '글 변화') · 원래 있던 파일이면 그때 글 = 열 때 있던 글
  · 저장 사이 글 변화엔 meta.since(앞 저장 시각)를 단다 → core/match.process_evidence 가 그 사이 한글 키 입력으로 '직접 친 글' 을 가른다
  · 붙여넣기: 저장 사이에 붙여넣기가 있었으면 가장 많이 늘어난 문단을 붙여넣은 자리로 낸다 (정확한 자리 · 순간은 Word 보다 거침)

한계 (발표 · 문서에 그대로): 저장할 때만 보므로 저장 전에 지운 글 · 고친 과정은 안 남는다. 웹에서 붙인 글은 '다른 곳' 대신
'출처 기록 없음' 으로 보일 수 있다 (AI 답에서 붙인 글은 글 내용으로 이어짐).
"""
import os
import sys
import time
from datetime import datetime
from urllib.parse import unquote, urlparse

from office import OfficeWatcher

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core import hwp                              # noqa: E402

APP = "한글"
EXT = (".hwpx", ".hwp")


def is_hangul(app: str) -> bool:
    """앞 앱 이름이 한글인가 — 윈도우 Hwp.exe · 맥 '한컴오피스 한글' · 'Hancom Office HWP' 등"""
    a = (app or "").lower()
    return a in ("hwp.exe", "hwp") or "한글" in a or "hancom office hwp" in a or a.startswith("hwp ")


class HangulWatcher(OfficeWatcher):
    def __init__(self, emit_event, current, poll_sec=3.0, emit_context=None, emit_path=None, started_at=None):
        """current() → (앞 앱 이름, 창 제목) · started_at = 기록 시작 시각(초) — 그 뒤에 만든 파일은 빈 문서에서 시작"""
        super().__init__(emit_event, lambda exe: False, poll_sec, emit_context, emit_path)
        self.name = "hangul"
        self.current = current
        self.started_at = started_at or time.time()
        self._본때 = {}             # 경로 → 마지막으로 읽은 파일 시각(mtime)
        self._읽은때 = {}           # 경로 → 마지막으로 읽은 순간 (ISO · 다음 글 변화의 since)
        self._붙임 = []             # 저장 사이 한글에 붙여넣은 시각들
        self._since = None
        if emit_context:                # 글 변화에 since(앞 저장 시각)를 단다 — 그 사이 키 입력으로 '직접 친 글' 을 가르게
            def 달기(items, 원래=emit_context):
                for it in items:
                    if it.get("kind") == "diff" and self._since:
                        it["meta"]["since"] = self._since
                원래(items)
            self.emit_context = 달기

    def on_paste(self, app: str = ""):
        if is_hangul(app):
            self._붙임.append(time.time())

    def run(self):
        while not self._stop.is_set():
            self.한번()
            self._stop.wait(self.poll)

    def 한번(self):
        """한글이 앞이면 지금 문서를 찾아 보고, 한 번 본 문서는 앞에 없어도 저장됐는지 본다
        (11/18 실제 한글 맥 시험: ⌘S 하고 2초 안에 다른 창으로 가면 마지막 저장을 놓쳤다 — 그대로 닫으면 마지막 글이 통째로 빠짐)"""
        try:
            app, title = self.current()
            if is_hangul(app):
                path = self._문서_경로(title)
                if path:
                    self._tick(path)
        except Exception as e:                            # noqa: BLE001 — 파일을 저장하는 중 · 잠김 등
            self._note(f"한글 건너뜀: {type(e).__name__}: {str(e)[:80]}")
        for path in list(self._본때):
            try:
                if os.path.isfile(path) and os.path.getmtime(path) != self._본때[path]:
                    self._tick(path)
            except Exception as e:                        # noqa: BLE001
                self._note(f"한글 건너뜀: {type(e).__name__}: {str(e)[:80]}")

    # ── 지금 열린 문서 위치 ──
    def _문서_경로(self, title):
        if sys.platform == "darwin":
            p = _맥_문서()
            if p:
                return p
        return _이름으로_찾기(_제목_파일(title))

    # ── 저장됐으면 읽어 비교 ──
    def _tick(self, path):
        m = os.path.getmtime(path)
        if self._본때.get(path) == m:
            return
        with open(path, "rb") as f:
            raw = f.read()
        units = {i: t for i, (_, t) in enumerate(hwp.read_hangul(raw), 1) if i <= 2000}
        name = os.path.basename(path)
        key = (APP, name)
        if self.emit_path and self._paths.get(key) != path:
            self._paths[key] = path
            self.emit_path(APP, name, path)
        처음 = path not in self._본때
        self._본때[path] = m
        since = self._읽은때.get(path)
        self._읽은때[path] = _iso()
        if 처음 and _생긴때(path) >= self.started_at - 5:      # 기록을 켠 뒤 만든 파일 — 빈 문서에서 시작 (쓴 글이 모두 글 변화)
            self._snap[APP] = {"file": name, "units": {}, "saved": True, "stats": {}}
            since = datetime.fromtimestamp(self.started_at).astimezone().isoformat(timespec="seconds")
        stats = {"chars": sum(len(t) for t in units.values()), "paragraphs": len(units)}
        where = None
        if self._붙임 and APP in self._snap:
            prev = self._snap[APP]["units"]
            늘어난 = max(units, key=lambda u: len(units[u]) - len(prev.get(u, "")), default=None)
            if 늘어난 is not None and len(units[늘어난]) > len(prev.get(늘어난, "")):
                where = (f"문단 {늘어난}", units[늘어난])
        self._붙임 = []
        self._since = since
        self._compare(key, units, True, stats, where, unit_label="문단")

    def _note(self, msg):
        print(f"        · {msg}")


def _iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _생긴때(path):
    st = os.stat(path)
    return getattr(st, "st_birthtime", None) or (st.st_ctime if os.name == "nt" else st.st_mtime)


def _제목_파일(title):
    """창 제목 → 파일 이름. '보고서.hwp - 한글' · '보고서.hwpx [C:\\...] - 한글' · '보고서 - 한컴오피스 한글' 등"""
    t = (title or "").strip()
    for 끝 in EXT:
        i = t.lower().find(끝)
        if i > 0:
            return t[:i + len(끝)].split("\\")[-1].split("/")[-1].strip(" [")
    return ""


def _이름으로_찾기(name, 최대깊이=2):
    """파일 이름 → 흔한 자리(바탕화면 · 문서 · 다운로드 · OneDrive)에서 가장 최근에 바뀐 그 이름의 파일"""
    if not name:
        return None
    집 = os.path.expanduser("~")
    best = None
    for r in [os.path.join(집, *p) for p in (("Desktop",), ("Documents",), ("Downloads",), ("OneDrive", "Desktop"),
                                             ("OneDrive", "Documents"), ("OneDrive", "바탕 화면"), ("OneDrive", "문서"))]:
        if not os.path.isdir(r):
            continue
        for d, dirs, files in os.walk(r):
            if d[len(r):].count(os.sep) >= 최대깊이:
                dirs[:] = []
            dirs[:] = [x for x in dirs if not x.startswith((".", "$")) and x.lower() not in ("node_modules", "appdata")]
            if name in files:
                p = os.path.join(d, name)
                m = os.path.getmtime(p)
                if best is None or m > best[0]:
                    best = (m, p)
    return best[1] if best else None


def _맥_문서():
    """맥: 앞 앱의 앞 창 AXDocument (file:// 주소) → 경로. 한글 파일일 때만"""
    try:
        import mac_ax
        from AppKit import NSWorkspace
        a = NSWorkspace.sharedWorkspace().frontmostApplication()
        root = mac_ax.app(int(a.processIdentifier()), 1.0)
        win = mac_ax.get(root, "AXFocusedWindow") or mac_ax.get(root, "AXMainWindow")
        doc = mac_ax.get(win, "AXDocument") if win is not None else None
    except Exception:                                     # noqa: BLE001
        return None
    if not isinstance(doc, str) or not doc:
        return None
    p = unquote(urlparse(doc).path) if doc.startswith("file:") else doc
    return p if p.lower().endswith(EXT) and os.path.isfile(p) else None
