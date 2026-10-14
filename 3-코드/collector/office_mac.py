"""
office_mac.py — 맥 Word · PowerPoint 문서 변화 수집 (AppleScript · 10/14)

윈도우판(office.py · COM)과 같은 이벤트 · 맥락을 낸다 — 비교(_compare) · 위치(doc_path) 규칙은 office.py 를 그대로 쓴다.
읽는 길만 다르다: 윈도우 COM 대신 맥 Office 의 AppleScript (osascript) 로 열린 문서의 글을 읽는다.
  Word        : active document 의 글 전체 → 문단(\\r)으로 나눔 · 저장 여부 · 위치 · 커서 위치(붙여넣은 문단)
  PowerPoint  : active presentation 의 슬라이드 · 도형 글 · 저장 위치 · 지금 슬라이드

· 그 앱이 **앞에 있을 때만** 읽는다 (윈도우판과 같음) — 꺼져 있는 Word 를 새로 띄우지 않는다
· ★ 처음 한 번 맥이 "Trace 가 Microsoft Word 를 제어하려고 합니다" 를 묻는다 → 허용. 거부하면 문서 변화만 빠지고 나머지는 계속
  (나중에 바꾸려면 시스템 설정 → 개인정보 보호 및 보안 → 자동화 → Trace → Microsoft Word)
"""
import os
import subprocess
import time

from office import OfficeWatcher

WORD, PPT = "Microsoft Word", "Microsoft PowerPoint"
SEP = "\x1e"                                          # 글에 거의 안 나오는 구분 문자 (record separator)

WORD_SCRIPT = '''
set trSep to character id 30
tell application "Microsoft Word"
  if (count of documents) is 0 then return ""
  with timeout of 4 seconds
    set trD to active document
    set trPath to ""
    try
      set trPath to POSIX path of ((full name of trD) as text)
    end try
    set trSel to -1
    try
      set trSel to selection start of selection
    end try
    return (name of trD) & trSep & trPath & trSep & ((saved of trD) as text) & trSep & (trSel as text) & trSep & (content of text object of trD)
  end timeout
end tell
'''

PPT_SCRIPT = '''
set trSep to character id 30
set trUs to character id 31
tell application "Microsoft PowerPoint"
  if (count of presentations) is 0 then return ""
  with timeout of 6 seconds
    set trPr to active presentation
    set trPath to ""
    try
      set trPath to POSIX path of ((full name of trPr) as text)
    end try
    set trSaved to "true"
    try
      set trSaved to ((saved of trPr) as text)
    end try
    set trCur to 0
    try
      set trCur to slide index of slide of view of document window 1
    end try
    set trRes to (name of trPr) & trSep & trPath & trSep & trSaved & trSep & (trCur as text) & trSep & ((count of slides of trPr) as text)
    repeat with trSi from 1 to (count of slides of trPr)
      set trS to slide trSi of trPr
      repeat with trJ from 1 to (count of shapes of trS)
        set trSh to shape trJ of trS
        try
          if has text frame of trSh then
            set trT to content of text range of text frame of trSh
            if trT is not "" then set trRes to trRes & trSep & (trSi as text) & ":" & (name of trSh) & trUs & trT
          end if
        end try
      end repeat
    end repeat
    return trRes
  end timeout
end tell
'''


def _실행(script, timeout=8):
    """osascript → 글 (실패 · 권한 거부 · 시간 초과면 None)"""
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(err[-160:] or f"osascript {r.returncode}")
    return r.stdout.decode("utf-8", "replace").rstrip("\n")


class MacOfficeWatcher(OfficeWatcher):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._거부 = set()            # 제어를 거부당한 앱 — 같은 오류를 매번 찍지 않게

    def run(self):
        while not self._stop.is_set():
            pend = self._paste_pending and time.time() - self._paste_pending < self.poll * 2
            try:
                if self.is_active(WORD) or (pend and self._paste_app == WORD.upper()):
                    self._tick_word()
                elif self.is_active(PPT) or (pend and self._paste_app == PPT.upper()):
                    self._tick_ppt()
            except Exception as e:
                self._오류(e)
            if self._wake.wait(self.poll):
                self._wake.clear()
                self._stop.wait(0.3)

    def _오류(self, e):
        m = str(e)
        if "-1743" in m or "Not authorized" in m or "허용되지" in m:       # 자동화 권한 거부
            if "자동화" not in self._거부:
                self._거부.add("자동화")
                self._note("Word · PowerPoint 를 읽을 권한이 없습니다 — 시스템 설정 → 개인정보 보호 및 보안 → 자동화 → Trace 에서 켜기")
            return
        self._note(f"office 건너뜀: {m[:120]}")

    # ── Word ──
    def _tick_word(self):
        out = _실행(WORD_SCRIPT)
        if not out:
            return
        name, path, saved, sel, text = (out.split(SEP, 4) + ["", "", "", "", ""])[:5]
        key = ("Word", name)
        self._path_mac(key, path)
        units = {}
        paras = text.split("\r")
        for i, p in enumerate(paras, 1):
            t = p.rstrip("\x07").replace("\x0b", "\n").strip()       # Shift+Enter 줄바꿈(\x0b) = 줄바꿈 (윈도우판과 같음)
            if t:
                units[i] = t
            if i >= 2000:
                break
        stats = {"chars": len(text), "words": len(text.split()), "paragraphs": len(units)}
        where = None
        if self._paste_pending and time.time() - self._paste_pending < self.poll * 2:
            try:
                s = int(sel)
                if s >= 0:
                    pi = text[:s].count("\r") + 1
                    ctx = paras[pi - 1].rstrip("\x07").strip() if pi - 1 < len(paras) else ""
                    where = (f"문단 {pi}", ctx)
            except ValueError:
                pass
            self._paste_pending = None
        self._compare(key, units, saved.strip().lower() == "true", stats, where, unit_label="문단")

    # ── PowerPoint ──
    def _tick_ppt(self):
        out = _실행(PPT_SCRIPT, timeout=10)
        if not out:
            return
        f = out.split(SEP)
        name, path, saved, cur, count = (f[:5] + [""] * 5)[:5]
        key = ("PowerPoint", name)
        self._path_mac(key, path)
        units = {}
        for item in f[5:]:
            uid, _, t = item.partition("\x1f")
            t = t.replace("\r", "\n").strip()
            if uid and t:
                units[uid] = t
        try:
            slides = int(count)
        except ValueError:
            slides = 0
        stats = {"slides": slides, "chars": sum(len(t) for t in units.values()), "shapes": len(units)}
        where = None
        if self._paste_pending and time.time() - self._paste_pending < self.poll * 2:
            if cur and cur != "0":
                where = (f"슬라이드 {cur}", "")
            self._paste_pending = None
        self._compare(key, units, saved.strip().lower() == "true", stats, where, unit_label="슬라이드")

    def _path_mac(self, key, path):
        """문서 위치 — 저장 전 문서는 위치가 없어서(가짜 경로) 실제 파일이 있을 때만"""
        if not self.emit_path or not path or not os.path.isfile(path) or self._paths.get(key) == path:
            return
        self._paths[key] = path
        self.emit_path(key[0], key[1], path)
