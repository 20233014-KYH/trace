"""
office.py — Word · PowerPoint 문서 변화 수집 (Office COM 자동화)

열려 있는 Word 문서 / PowerPoint 프레젠테이션을 몇 초마다 들여다보고 바뀐 것을 낸다. 두 층으로:

  ① 이벤트 (두 모드 공통 · 숫자만 · 체인에 들어감 · Proof 증명서에 나옴)
     doc_change    {app, file, where, added, removed}      문단 3 · +240자 / -12자
     doc_paste_at  {app, file, where}                      Ctrl+V 직후 붙여넣은 자리 (문단 n / 슬라이드 n)
     doc_save      {app, file, chars, words, slides}       저장 직후 글자·단어·슬라이드 수
  ② 맥락 (Learn 만 · 텍스트 · 서버 /context 로)
     diff          바뀐 문단/도형의 새 텍스트 (≤500자)
     paste_at      붙여넣은 자리 주변 텍스트 (≤200자)

Proof 모드에서는 ①만 낸다 — 문서를 읽기는 하지만 글자는 **저장하지 않는다** (클립보드를 읽고 해시만 남기는 것과 같은 구조).
안 하는 것: 문서 전체 저장, 화면 캡처. 삭제는 두 모드 모두 글자 수만.

동작:
  · 별도 스레드. Word/PPT 가 실행 중이고 그 창이 활성일 때만 읽는다 (COM GetActiveObject — 프로그램을 새로 띄우지 않는다).
  · 문단(Word) / 슬라이드·도형(PPT) 단위로 이전 스냅샷과 비교 → 바뀐 단위만 diff.
  · 문서가 저장되면(Saved 가 False→True) save_stats 하나.
  · COM 이 막히면(모달 대화상자 등) 그 tick 은 건너뛴다.

config.json:  "office": {"enabled": true, "poll_sec": 5}   ·  텍스트(맥락)는 "learn_context": {"office": true} 이고 Learn 모드일 때만
"""
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
MAX_DIFF, MAX_PASTE = 500, 200


def _now():
    return datetime.now(KST).isoformat(timespec="seconds")


def _item(kind, text, meta):
    return {"id": str(uuid.uuid4()), "ts": _now(), "source": "office", "kind": kind, "text": text, "meta": meta}


class OfficeWatcher(threading.Thread):
    def __init__(self, emit_event, is_active, poll_sec=5.0, emit_context=None):
        """emit_event(ev) : 숫자 이벤트(체인) · emit_context(items) : 텍스트 맥락(Learn 만, None 이면 안 냄) · is_active(exe) : 활성 창인가"""
        super().__init__(daemon=True, name="office")
        self.emit_event, self.emit_context, self.is_active, self.poll = emit_event, emit_context, is_active, float(poll_sec)
        self._stop = threading.Event()
        self._snap = {}          # key(app,file) -> {"units": {unit_id: text}, "saved": bool, "stats": {...}}
        self._paste_pending = None

    def stop(self):
        self._stop.set()

    def on_paste(self):
        """수집기의 Ctrl+V 감지에서 호출 — 다음 tick 에 붙여넣은 자리를 읽는다."""
        self._paste_pending = time.time()

    # ── 루프 ──
    def run(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            while not self._stop.is_set():
                try:
                    if self.is_active("WINWORD.EXE"):
                        self._tick_word()
                    elif self.is_active("POWERPNT.EXE"):
                        self._tick_ppt()
                except Exception as e:      # COM 이 모달 상태이거나 문서가 닫히는 중
                    self._note(f"office 건너뜀: {type(e).__name__}")
                self._stop.wait(self.poll)
        finally:
            pythoncom.CoUninitialize()

    def _note(self, msg):
        print(f"        · {msg}")

    # ── Word ──
    def _tick_word(self):
        import win32com.client
        app = win32com.client.GetActiveObject("Word.Application")
        doc = app.ActiveDocument
        key = ("Word", doc.Name)
        units = {}
        for i, p in enumerate(doc.Paragraphs, 1):
            t = p.Range.Text.rstrip("\r\x07").strip()
            if t:
                units[i] = t
            if i >= 2000:                       # 아주 긴 문서는 앞 2000문단까지만
                break
        stats = {"chars": int(doc.Characters.Count), "words": int(doc.Words.Count), "paragraphs": len(units)}
        where = None
        if self._paste_pending and time.time() - self._paste_pending < self.poll * 2:
            try:
                sel = app.Selection
                pi = doc.Range(0, sel.Start).Paragraphs.Count
                ctx = sel.Paragraphs(1).Range.Text.rstrip("\r\x07").strip()
                where = (f"문단 {pi}", ctx)
            except Exception:
                pass
            self._paste_pending = None
        self._compare(key, units, bool(doc.Saved), stats, where, unit_label="문단")

    # ── PowerPoint ──
    def _tick_ppt(self):
        import win32com.client
        app = win32com.client.GetActiveObject("PowerPoint.Application")
        pres = app.ActivePresentation
        key = ("PowerPoint", pres.Name)
        units = {}
        for s in pres.Slides:
            for sh in s.Shapes:
                try:
                    if sh.HasTextFrame and sh.TextFrame.HasText:
                        t = sh.TextFrame.TextRange.Text.strip()
                        if t:
                            units[f"{s.SlideIndex}:{sh.Name}"] = t
                except Exception:
                    continue
        stats = {"slides": int(pres.Slides.Count), "chars": sum(len(t) for t in units.values()), "shapes": len(units)}
        where = None
        if self._paste_pending and time.time() - self._paste_pending < self.poll * 2:
            try:
                idx = app.ActiveWindow.View.Slide.SlideIndex
                where = (f"슬라이드 {idx}", "")
            except Exception:
                pass
            self._paste_pending = None
        self._compare(key, units, bool(pres.Saved), stats, where, unit_label="슬라이드")

    # ── 스냅샷 비교 ──
    def _compare(self, key, units, saved, stats, where, unit_label):
        app, file = key
        prev = self._snap.get(app)                  # 앱당 하나 — 활성 문서
        # 다른 이름으로 저장(문서1 → 과제.docx)은 같은 문서. 내용이 절반 넘게 겹치면 이어서 본다
        if prev is not None and prev["file"] != file:
            common = sum(1 for u, t in units.items() if prev["units"].get(u) == t)
            if units and common / max(len(units), len(prev["units"])) >= 0.5:
                self._note(f"{app} 문서 이름 바뀜 · {prev['file']} → {file} (같은 문서로 계속)")
                prev["file"] = file
            else:
                prev = None
        events, items = [], []
        if prev is None:
            self._snap[app] = {"file": file, "units": units, "saved": saved, "stats": stats}
            self._note(f"{app} 감시 시작 · {file} · {stats}")
            return
        # 바뀐 단위 → 이벤트는 +n자/-m자, 맥락(Learn)은 새 텍스트. 사라진 단위는 두 층 모두 글자 수만
        for uid, text in units.items():
            old = prev["units"].get(uid)
            if old == text:
                continue
            added = text if old is None else _added_part(old, text)
            plus, minus = len(added), max(0, len(old or "") - (len(text) - len(added)))
            events.append({"type": "doc_change", "app": app, "file": file, "where": f"{unit_label} {uid}", "added": plus, "removed": minus})
            if added:
                items.append(_item("diff", added[:MAX_DIFF], {"app": app, "file": file, "where": f"{unit_label} {uid}"}))
        removed = sum(len(t) for uid, t in prev["units"].items() if uid not in units)
        if removed:
            events.append({"type": "doc_change", "app": app, "file": file, "where": "삭제", "added": 0, "removed": removed})
        if where:
            events.append({"type": "doc_paste_at", "app": app, "file": file, "where": where[0]})
            if where[1]:
                items.append(_item("paste_at", where[1][:MAX_PASTE], {"app": app, "file": file, "where": where[0]}))
        if saved and not prev["saved"]:
            events.append({"type": "doc_save", "app": app, "file": file, **stats})
        self._snap[app] = {"file": file, "units": units, "saved": saved, "stats": stats}
        for ev in events:
            self.emit_event(ev)
        if items and self.emit_context:
            self.emit_context(items)


def _added_part(old: str, new: str) -> str:
    """old → new 에서 새로 들어온 글자만. 간단히 공통 접두·접미를 떼고 남은 가운데."""
    i = 0
    while i < min(len(old), len(new)) and old[i] == new[i]:
        i += 1
    j = 0
    while j < min(len(old), len(new)) - i and old[-1 - j] == new[-1 - j]:
        j += 1
    return new[i:len(new) - j]
