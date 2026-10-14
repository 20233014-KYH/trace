"""
desktop_ai_mac.py — 맥 데스크톱 AI 앱(Claude 앱 · ChatGPT 앱)의 질문·답 원문 읽기 (손쉬운 사용 API · 10/14)

윈도우판(desktop_ai.py · UI Automation)과 같은 일을 맥의 화면낭독 길(mac_ax.py)로 한다.
· 그 앱이 **앞에 있을 때만** poll_sec 마다 읽는다
· Claude 앱은 웹 화면(Electron) — 처음 한 번 AXManualAccessibility 를 켜야 웹 화면의 구조(역할 · HTML 클래스)가 보인다.
  메시지 = HTML 클래스로 찾는다 (웹 Claude · 윈도우판 ③과 같음): 답 font-claude-response · standard-markdown, 질문 font-user-message.
  못 찾으면 대화 목록(feed) 안의 article + 화면낭독 제목("Claude 응답:" · "입력 내용:")으로 (윈도우판 ①)
· ChatGPT 앱은 맥에선 웹 화면이 아닌 앱이라 구조가 다르다 — 화면낭독 제목("ChatGPT 답변:" 등)이 있으면 그것으로, 없으면 못 읽음
  (debug=true 면 화면 구조를 data/desktop-ai-debug.txt 에 남긴다 → 셀렉터를 맞춘다)
· 대화 · 이전 대화(history) · 생성 끝(두 번 연속 같으면) 판단은 윈도우판 _send 를 그대로 쓴다 → collector._on_context
안 하는 것: 화면 캡처 · 키 입력 · 앱 밖 창 · 권한 없이 읽기 (없으면 한 번 권한 창을 띄우고 기다림)

손으로 화면 구조 보기:  python collector/desktop_ai_mac.py --dump   (3초 안에 Claude 앱을 앞으로 · 결과는 화면에)
"""
import os
import re
import sys
import time
from datetime import datetime

import mac_ax
from desktop_ai import A_HEAD, ANSWER_CLS, KST, Q_HEAD, QUESTION_CLS, SKIP_NAMES, DesktopAIWatcher

# 맥 앱 이름(소문자 · NSWorkspace localizedName) → 체인에 남길 도구 이름. 서버 _앱이름 에도 "claude" · "chatgpt" 가 있다
APPS = {"claude": "Claude 앱", "chatgpt": "ChatGPT 앱"}
BUNDLES = {"com.anthropic.claudefordesktop": "claude", "com.openai.chat": "chatgpt"}
ATTRS = ["AXRole", "AXSubrole", "AXRoleDescription", "AXDOMClassList", "AXTitle", "AXDescription", "AXValue", "AXChildren"]
SKIP_ROLES = {"AXButton", "AXImage", "AXProgressIndicator", "AXBusyIndicator", "AXToolbar", "AXMenu", "AXMenuBar",
              "AXMenuButton", "AXPopUpButton", "AXCheckBox", "AXRadioButton", "AXTextField", "AXScrollBar"}
SKIP_DESC = {"time", "시간", "status", "상태"}
MAX_NODES = 20000


class _N:
    """화면 요소 하나 (읽은 속성만)"""
    __slots__ = ("role", "sub", "desc", "cls", "title", "label", "value", "kids", "parent")

    def __init__(self, a, parent):
        self.role, self.sub, self.desc = a.get("AXRole") or "", a.get("AXSubrole") or "", (a.get("AXRoleDescription") or "")
        self.cls = set(str(c) for c in (a.get("AXDOMClassList") or []))
        self.title, self.label = a.get("AXTitle") or "", a.get("AXDescription") or ""
        v = a.get("AXValue")
        self.value = v if isinstance(v, str) else ""
        self.kids, self.parent = [], parent

    def name(self):
        return self.title or self.label or self.value


class MacDesktopAIWatcher(DesktopAIWatcher):
    APPS = APPS

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._켬 = set()              # AXManualAccessibility 를 켠 pid
        self._알림 = False

    def run(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:      # 창이 닫히는 중 등
                print(f"        · 데스크톱 AI 건너뜀: {type(e).__name__}: {e}")
            self._stop.wait(self.poll)

    # ── 한 번 읽기 ──
    def _tick(self):
        from AppKit import NSWorkspace
        a = NSWorkspace.sharedWorkspace().frontmostApplication()
        if a is None:
            return
        key = BUNDLES.get(str(a.bundleIdentifier() or "")) or str(a.localizedName() or "").lower()
        if key not in APPS:
            return
        if not mac_ax.trusted(ask=True):
            if not self._알림:
                self._알림 = True
                print("        · 데스크톱 AI 앱을 읽으려면 '손쉬운 사용' 권한이 필요합니다 — "
                      "시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용 → Trace 켜기")
            return
        pid = int(a.processIdentifier())
        root = mac_ax.app(pid, 2.0)
        if pid not in self._켬:                       # Electron 앱(Claude)은 이걸 켜야 웹 화면 구조를 연다 (켜는 데 한두 번 걸림)
            self._켬.add(pid)
            mac_ax.set_(root, "AXManualAccessibility", True)
        win = mac_ax.get(root, "AXFocusedWindow") or mac_ax.get(root, "AXMainWindow")
        if win is None:
            return
        tree, n = self._읽기(win)
        msgs = self._찾기(tree)
        if not msgs:
            self._empty_at = time.time()
            self._dump_mac(key, tree, n)
            return
        convs = {}
        for i, (node, hint) in enumerate(msgs):
            conv = self._대화(node, win)
            role, text = self._글(node, hint)
            convs.setdefault(conv, []).append((f"{conv}|{i}|{role}", role, text))
        for conv, items in convs.items():
            self._send(key, conv, items)

    def _읽기(self, el):
        """창 아래 요소를 한 번에 훑어 _N 나무로 (앱과 요소마다 한 번씩만 주고받음)"""
        root = _N(mac_ax.gets(el, ATTRS), None)
        stack, n = [(el, root, mac_ax.gets(el, ["AXChildren"]).get("AXChildren") or [])], 1
        while stack and n < MAX_NODES:
            _, node, kids = stack.pop()
            for c in kids:
                a = mac_ax.gets(c, ATTRS)
                k = _N(a, node)
                node.kids.append(k)
                n += 1
                if a.get("AXChildren"):
                    stack.append((c, k, a["AXChildren"]))
        # pop 이 뒤에서부터라 순서가 뒤집히지 않게 — 자식은 node.kids 에 원래 순서로 붙어 있음
        return root, n

    # ── 메시지 찾기 · 읽기 ──
    def _찾기(self, root):
        """[(node, "question" | "answer" | None)] 화면 순서대로"""
        out = []

        def walk(nd):
            if nd.cls & set(ANSWER_CLS):
                out.append((nd, "answer"))
                return                                  # 바깥 것 하나만 (안의 standard-markdown 을 또 세지 않게)
            if nd.cls & set(QUESTION_CLS):
                out.append((nd, "question"))
                return
            for k in nd.kids:
                walk(k)
        walk(root)
        if out:
            return out
        # 윈도우판 ① — 대화 목록(feed) 안의 article. 질문/답은 _글 이 화면낭독 제목으로 가린다
        arts = []

        def walk2(nd, in_feed):
            feed = in_feed or nd.desc in ("feed", "피드") or "feed" in nd.sub.lower()
            if feed and (nd.sub == "AXDocumentArticle" or nd.desc in ("article", "기사")):
                arts.append((nd, None))
                return
            for k in nd.kids:
                walk2(k, feed)
        walk2(root, False)
        if arts:
            return arts
        # 화면낭독 제목만 있는 화면 (ChatGPT 앱처럼) — 제목 다음 형제가 글 덩어리
        heads = []

        def walk3(nd):
            for i, k in enumerate(nd.kids):
                if k.role == "AXHeading":
                    t = _모은글(k).strip()
                    role = "question" if Q_HEAD.match(t) else "answer" if A_HEAD.match(t) else None
                    if role and i + 1 < len(nd.kids):
                        heads.append((nd.kids[i + 1], role))
                        continue
                walk3(k)
        walk3(root)
        return heads

    def _대화(self, node, win):
        """대화 이름 = 이 메시지가 든 웹 화면(AXWebArea)의 제목 · 없으면 창 제목"""
        p = node.parent
        while p is not None:
            if p.role == "AXWebArea" and p.title:
                return p.title
            p = p.parent
        t = mac_ax.get(win, "AXTitle")
        return str(t) if isinstance(t, str) else ""

    def _글(self, node, hint):
        """(role, 본문) — 글자 조각(AXStaticText)만 모으고, 블록이 바뀌면 줄바꿈. 버튼 · 시각 · 화면낭독 글은 뺀다"""
        parts, heads, last = [], [], [None]

        def walk(nd, block, depth=0):
            if "sr-only" in nd.cls:
                if nd.role == "AXHeading" or nd.kids:
                    heads.append(_모은글(nd))
                return
            if nd.role in SKIP_ROLES or nd.desc.lower() in SKIP_DESC or nd.name() in SKIP_NAMES \
                    or any(c.startswith("group/morph") for c in nd.cls):
                return
            if nd.role == "AXStaticText":
                t = nd.value or nd.title or nd.label
                if t:
                    if last[0] is not None and last[0] is not block:
                        parts.append("\n")
                    parts.append(t)
                    last[0] = block
                return
            blk = nd if nd.role in ("AXGroup", "AXHeading", "AXList", "AXRow", "AXCell", "AXTable", "AXParagraph") else block
            for k in nd.kids:
                if depth < 60:
                    walk(k, blk, depth + 1)

        walk(node, node)
        role = hint
        for h in heads:
            if Q_HEAD.match(h.strip()):
                role = "question"
            elif A_HEAD.match(h.strip()):
                role = "answer"
        text = re.sub(r"[ \t]*\n[ \t]*", "\n", "".join(parts).replace("￼", ""))
        return role or "answer", re.sub(r"\n{3,}", "\n\n", text).strip()

    def _dump_mac(self, key, root, n):
        """debug: 메시지를 못 찾으면 화면 구조를 1분에 한 번 남긴다 (셀렉터 고칠 때)"""
        if not self.debug or time.time() - self._dumped < 60:
            return
        self._dumped = time.time()
        with open(os.path.join(self.data_dir, "desktop-ai-debug.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n== {datetime.now(KST):%H:%M:%S} {key} (맥) · 요소 {n}\n")
            _적기(root, f.write)


def _모은글(nd):
    if nd.role == "AXStaticText":
        return nd.value or nd.title or nd.label
    return nd.title or nd.label or "".join(_모은글(k) for k in nd.kids)


def _적기(nd, w, depth=0, limit=[0]):
    if depth == 0:
        limit[0] = 0
    limit[0] += 1
    if limit[0] > 3000:
        return
    w(f"{'  ' * min(depth, 40)}{nd.role}|{nd.sub}|{nd.desc}|{' '.join(sorted(nd.cls))[:60]}|{nd.name().replace(chr(10), ' ')[:60]}\n")
    for k in nd.kids:
        _적기(k, w, depth + 1)


if __name__ == "__main__" and "--dump" in sys.argv:
    # 손으로 화면 구조 보기 — 3초 안에 Claude 앱(또는 ChatGPT 앱)을 앞으로
    print("손쉬운 사용 권한:", mac_ax.trusted(ask=True))
    time.sleep(3)
    got = []
    w = MacDesktopAIWatcher(lambda items: got.extend(items), {}, poll_sec=1, data_dir=".", debug=False)
    from AppKit import NSWorkspace
    a = NSWorkspace.sharedWorkspace().frontmostApplication()
    root_el = mac_ax.app(int(a.processIdentifier()), 3.0)
    mac_ax.set_(root_el, "AXManualAccessibility", True)
    time.sleep(1.5)
    win = mac_ax.get(root_el, "AXFocusedWindow") or mac_ax.get(root_el, "AXMainWindow")
    tree, n = w._읽기(win)
    print(f"앱 {a.localizedName()} · 요소 {n}")
    out = sys.argv[sys.argv.index("--dump") + 1] if len(sys.argv) > sys.argv.index("--dump") + 1 else None
    if out:
        with open(out, "w", encoding="utf-8") as f:
            _적기(tree, f.write)
        print("구조 →", out)
    for node, hint in w._찾기(tree):
        role, text = w._글(node, hint)
        print(f"--- {role} · {w._대화(node, win)[:40]}\n{text[:300]}")
