"""
desktop_ai.py — 데스크톱 AI 앱(Claude 앱 · ChatGPT 앱 …)의 질문·답 원문 읽기 (Windows UI Automation · 10/7)

브라우저 확장이 웹 AI 사이트를 읽듯, 앱 창의 글을 화면낭독기와 같은 길(UI Automation)로 읽는다.
· 그 앱 창이 **앞에 있을 때만** poll_sec 마다 읽는다 — 손으로 옮겨 치려면 답이 화면에 떠 있어야 하니 그때 읽으면 된다
· 앱 화면은 웹 페이지(Electron)라 HTML 의 역할·클래스가 그대로 보인다 (Claude 앱 2026-10 실제 화면으로 맞춤):
    메시지 = 대화 목록(aria role feed) 안의 article — 앱 옆 창(미리보기 · 브라우저)의 article 은 뺀다
    질문/답 = article 안의 화면낭독 제목: "입력 내용: …"(질문) · "Claude 응답: …"(답) · 영어 화면 "You said:" 등
    본문 = article 을 따라 내려가며 글자만 모은다. 빼는 것: 화면낭독 글(sr-only) · 버튼 · 도구 모음(복사 · 재시도) ·
           시각("6분 전" — 1분마다 바뀌어서 같은 답을 또 보내던 문제) · 진행 표시("…설명 중.") · 제안된 작업("Word 문서 만들기")
    없으면 웹 Claude 와 같은 클래스로: 답 = standard-markdown · font-claude-response, 질문 = font-user-message
· 같은 메시지 글이 두 번 연속 같을 때(생성 끝) 보낸다 → collector._on_context (확장과 같은 길: 가림 → 해시 → PC 원문 + 체인 ai_msg)
· 이전 대화(history) = 그 대화를 처음 읽을 때 이미 있던 메시지. 단 ① 바로 전(2분 안)에 새 채팅 화면(메시지 없음)을 봤거나
  ② 처음 읽은 뒤 마지막 답이 아직 바뀌고 있으면(생성 중) 새 대화로 본다 — 새 채팅은 질문을 보낸 뒤에야 대화가 생겨서 (10/7)
안 하는 것: 화면 캡처 · 키 입력 · 앱 밖 창. 맥은 접근성 권한이 필요해서 아직 없음 (윈도우만).

config.json:  "desktop_ai": {"enabled": true, "poll_sec": 2, "debug": false}  ·  원문 토글은 capture.ai_question / ai_answer
debug=true 면 메시지를 못 찾을 때 화면 구조(역할·클래스·이름 앞부분)를 data/desktop-ai-debug.txt 에 남긴다 (화면이 바뀌어 셀렉터를 고칠 때)
"""
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
APPS = {"claude.exe": "Claude 앱", "chatgpt.exe": "ChatGPT 앱"}          # exe(소문자) → 체인에 남길 도구 이름
Q_HEAD = re.compile(r"^(입력 내용|You said|나의 말)\s*:")                  # 질문 article 의 화면낭독 제목
A_HEAD = re.compile(r"^(Claude 응답|Claude said|ChatGPT의 말|ChatGPT said)\s*:")
SKIP_ROLES = {"status", "toolbar", "button", "time", "img", "progressbar", "menu"}
BLOCK_ROLES = {"group", "heading", "listitem", "list", "paragraph", "separator", "blockquote", "table", "row", "code", "figure", "region", "article"}
SKIP_NAMES = {"제안된 작업", "Suggested actions"}
ANSWER_CLS = ("standard-markdown", "font-claude-response")
QUESTION_CLS = ("font-user-message",)

NEW_CHAT_SEC = 120                                                       # 새 채팅 화면을 본 뒤 이 안에 생긴 대화 = 새 대화


def _get(el, attr, default=""):
    """요소가 사라지는 중이면 COM 오류가 난다 — 그 요소만 건너뛴다 (10/7 시험: 화면이 바뀔 때 tick 전체가 멈췄다)"""
    try:
        v = getattr(el, attr)
        return default if v is None else v
    except Exception:
        return default


class DesktopAIWatcher(threading.Thread):
    def __init__(self, emit_context, toggles, poll_sec=2.0, data_dir=".", debug=False):
        """emit_context(items) : collector._on_context · toggles : capture (ai_question · ai_answer 가 꺼져 있으면 그 쪽은 안 보냄)"""
        super().__init__(daemon=True, name="desktop_ai")
        self.emit_context, self.toggles, self.poll = emit_context, toggles, float(poll_sec)
        self.data_dir, self.debug = data_dir, debug
        self._stop = threading.Event()
        self._last = {}           # key → 지난번 글 (두 번 연속 같으면 생성 끝)
        self._sent = {}           # key → 보낸 글
        self._first = {}          # key → 처음 읽을 때의 글 (이전 대화 후보)
        self._history = set()     # 이전 대화로 볼 key
        self._convs = set()       # 한 번이라도 읽은 대화
        self._empty_at = 0.0      # 새 채팅 화면(메시지 없음)을 마지막으로 본 시각
        self._dumped = 0.0

    def stop(self):
        self._stop.set()

    def run(self):
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()
        try:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as U
            self.uia = comtypes.client.CreateObject(U.CUIAutomation, interface=U.IUIAutomation)
            self.W = self.uia.RawViewWalker
            while not self._stop.is_set():
                try:
                    self._tick()
                except Exception as e:          # 창이 닫히는 중
                    print(f"        · 데스크톱 AI 건너뜀: {type(e).__name__}")
                self._stop.wait(self.poll)
        finally:
            comtypes.CoUninitialize()

    # ── 한 번 읽기 ──
    def _tick(self):
        import win32gui
        import win32process
        import psutil
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return
        try:
            exe = psutil.Process(win32process.GetWindowThreadProcessId(hwnd)[1]).name().lower()
        except Exception:
            return
        if exe not in APPS:
            return
        els = self.uia.ElementFromHandle(hwnd).FindAll(4, self.uia.CreateTrueCondition())     # TreeScope_Descendants
        allel = [els.GetElement(i) for i in range(els.Length)]
        msgs = self._messages(allel)
        if not msgs:
            self._empty_at = time.time()       # 새 채팅 화면 — 곧 생길 대화는 새 대화
            self._dump(exe, allel)
            return
        convs = {}
        for i, (el, hint) in enumerate(msgs):
            conv = self._conv(el)
            role, text = self._read(el, hint)
            name = _get(el, "CurrentName")
            slot = name if re.search(r"\d", name) else i                   # "2개 메시지 중 2번째" · "메시지 42" 처럼 번호가 있으면 그걸로
            convs.setdefault(conv, []).append((f"{conv}|{slot}|{role}", role, text))
        for conv, items in convs.items():
            self._send(exe, conv, items)

    def _send(self, exe, conv, items):
        now = time.time()
        if conv not in self._convs:
            self._convs.add(conv)
            if now - self._empty_at > NEW_CHAT_SEC:                      # 새 채팅에서 막 생긴 대화가 아니면 → 이미 있던 건 이전 대화
                for key, role, text in items:
                    self._history.add(key)
                    self._first[key] = text
        # 처음 읽은 뒤 마지막 답이 바뀌고 있으면(생성 중) 그 답과 바로 앞 질문은 지금 대화
        last = items[-1]
        if last[0] in self._first and last[2] != self._first[last[0]]:
            for key, _, _ in items[-2:]:
                self._history.discard(key)
        for n, (key, role, text) in enumerate(items, 1):
            prev, self._last[key] = self._last.get(key), text
            if not text or text != prev or self._sent.get(key) == text:
                continue                        # 아직 한 번만 봄(생성 중일 수 있음) · 이미 보냄
            kind = "ai_question" if role == "question" else "ai_answer"
            self._sent[key] = text
            if self.toggles.get(kind) is False:
                continue
            self.emit_context([{"id": str(uuid.uuid4()), "ts": datetime.now(KST).isoformat(timespec="seconds"),
                                "source": "desktop", "kind": kind, "text": text,
                                "meta": {"tool": APPS[exe], "domain": exe, "conv": conv, "turn": n,
                                         "history": key in self._history}}])

    # ── 메시지 찾기 · 읽기 ──
    def _up(self, el, test, up=14):
        p = self.W.GetParentElement(el)
        for _ in range(up):
            if not p:
                return None
            if test(p):
                return p
            p = self.W.GetParentElement(p)
        return None

    def _conv(self, el):
        """대화 이름 = 이 메시지가 들어 있는 문서 영역의 이름 ("AI 인플루언서 제작 과정 - Claude")"""
        web = self._up(el, lambda p: _get(p, "CurrentAutomationId") == "RootWebArea", up=40)
        return _get(web, "CurrentName") if web else ""

    def _messages(self, allel):
        """메시지 [(el, role 힌트 | None)] — ① 대화 목록(feed) 안의 article ② 웹 Claude 클래스"""
        arts = [(e, None) for e in allel
                if _get(e, "CurrentAriaRole") == "article" and self._up(e, lambda p: _get(p, "CurrentAriaRole") == "feed")]
        if arts:
            return arts
        out = []
        for e in allel:
            cls = _get(e, "CurrentClassName").split()
            if any(c in ANSWER_CLS for c in cls):
                out.append((e, "answer"))
            elif any(c in QUESTION_CLS for c in cls):
                out.append((e, "question"))
        return out

    def _read(self, el, hint):
        """(role, 본문) — article 을 따라 내려가며 글자만. 화면낭독 제목으로 질문/답을 가리고, 버튼·시각·진행 표시는 뺀다"""
        parts, heads = [], []

        def walk(e, depth=0):
            c = self.W.GetFirstChildElement(e)
            while c:
                role, cls, name = _get(c, "CurrentAriaRole"), _get(c, "CurrentClassName").split(), _get(c, "CurrentName")
                if "sr-only" in cls:
                    if role == "heading":
                        heads.append(name)
                elif role in SKIP_ROLES or name in SKIP_NAMES or any(x.startswith("group/morph") for x in cls):
                    pass
                elif self.W.GetFirstChildElement(c) and depth < 30:
                    walk(c, depth + 1)          # 굵게·기울임·링크는 이름이 비어 있고 안에 글이 있다 (10/7: 굵은 글씨가 빠졌다)
                    if role in BLOCK_ROLES:
                        parts.append("\n")      # 문단·제목·목록 항목 끝은 줄바꿈
                else:
                    parts.append(name)          # 맨 끝 글자 조각
                c = self.W.GetNextSiblingElement(c)

        walk(el)
        role = hint
        for h in heads:
            if Q_HEAD.match(h):
                role = "question"
            elif A_HEAD.match(h):
                role = "answer"
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", "".join(parts).replace("￼", ""))
        return role or "answer", re.sub(r"\n{3,}", "\n\n", text).strip()

    def _dump(self, exe, allel):
        """debug: 메시지를 못 찾으면 화면 구조를 1분에 한 번 남긴다 (셀렉터 고칠 때)"""
        if not self.debug or time.time() - self._dumped < 60:
            return
        self._dumped = time.time()
        with open(os.path.join(self.data_dir, "desktop-ai-debug.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n== {datetime.now(KST):%H:%M:%S} {exe} · 요소 {len(allel)}\n")
            for e in allel[:600]:
                f.write(f"{_get(e, 'CurrentAriaRole')} | {_get(e, 'CurrentLocalizedControlType')} | {_get(e, 'CurrentClassName')[:60]} | "
                        f"{_get(e, 'CurrentAutomationId')[:20]} | {_get(e, 'CurrentName').replace(chr(10), ' ')[:50]}\n")
