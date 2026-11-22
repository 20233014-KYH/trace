"""
readcheck.py — AI 화면 읽기가 깨졌는지 기록만 보고 알아챈다 (11/19 박상진 · 출시 전 고칠 것 5번 ①)

Trace 는 ChatGPT · Claude · Gemini 의 웹 화면(크롬 확장)과 데스크톱 앱 화면(기록기)을 읽어 질문 · 답을 남긴다.
그 회사들이 화면을 바꾸면 읽기가 조용히 멈춘다 (11/16 맥 ChatGPT 앱 26.x). 그러면 기록에는 "AI 질문 0개" 로 남아
**교수가 'AI 를 안 썼다' 로 오해**할 수 있다.

복사는 화면 읽기와 따로 남는다 (기록기가 클립보드를 본다). 그래서
  "그 AI 에서 복사는 했는데, 같은 기록에 그 AI 의 질문 · 답이 하나도 없다" = 그 AI 화면을 읽지 못했다
로 본다. 판정이 아니라 솔직하게 알려 주기 — 기록 다시 보기 · 내기 전에 확인할 것에 보인다.

  read_gaps(events, msgs) → [{"session", "tool", "kind", "copies", "first", "last"}]
    kind = "failed"      읽는 AI 인데 이 기록에서 못 읽음 (확장이 꺼졌거나 · 화면이 바뀜)
           "unsupported" Trace 가 아직 읽지 않는 AI 사이트 (Perplexity · Copilot 등) — 복사한 글로만 이어진다
숫자와 이름 · 시각만 돌려준다 (글은 안 봄).
"""

WEB = {"chatgpt.com": "ChatGPT", "chat.openai.com": "ChatGPT", "claude.ai": "Claude", "gemini.google.com": "Gemini"}
APPS = {"chatgpt.exe": "ChatGPT 앱", "claude.exe": "Claude 앱", "chatgpt": "ChatGPT 앱", "claude": "Claude 앱"}   # 윈도우 exe · 맥 앱 이름
TITLE = {"chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini"}        # 확장이 없을 때 브라우저 창 제목으로
BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "whale.exe", "google chrome", "microsoft edge", "firefox", "safari"}


def _도메인(d):
    d = (d or "").lower().removeprefix("www.")
    for k in WEB:
        if d == k or d.endswith("." + k):
            return k
    return d


def _도구(e, tab, title):
    """복사 한 번 → (도구 이름, 읽는 AI 인가) · AI 에서 복사한 게 아니면 None"""
    app = (e.get("app") or "").lower()
    if app in APPS:
        return APPS[app], True
    if app not in BROWSERS:
        return None
    if tab and tab[1] == "ai":                       # 확장이 알려 준 탭 (도메인 · 분류)
        d = _도메인(tab[0])
        return (WEB[d], True) if d in WEB else (d or "AI 사이트", False)
    if e.get("category") == "ai":                     # 확장이 없거나 꺼짐 — 기록기가 창 제목으로 AI 라고 본 복사
        t = (title or "").lower()
        return next(((v, True) for k, v in TITLE.items() if k in t), ("AI 사이트", False))
    return None


def read_gaps(events, msgs):
    msg_tools = {}                                   # (기록, 도구) → 남은 질문 · 답 수
    for m in msgs:
        k = (m.get("session_id"), (m.get("tool") or "").strip())
        msg_tools[k] = msg_tools.get(k, 0) + 1
    tab, title, seen = {}, {}, {}                    # 기록마다 지금 보던 탭 · 창 제목
    for e in sorted(events, key=lambda e: e.get("ts", "")):
        s, t = e.get("session_id"), e.get("type")
        if t == "tab":
            tab[s] = (e.get("domain", ""), e.get("category", "other"))
        elif t == "window":
            title[s] = e.get("title", "")
            if (e.get("app") or "").lower() not in BROWSERS:
                tab.pop(s, None)                     # 브라우저를 떠나면 그 탭 정보는 지난 것
        elif t == "copy":
            r = _도구(e, tab.get(s), title.get(s))
            if not r:
                continue
            g = seen.setdefault((s, r[0]), {"session": s, "tool": r[0], "supported": r[1], "copies": 0, "first": e["ts"], "last": e["ts"]})
            g["copies"] += 1
            g["last"] = e["ts"]
    out = []
    for (s, tool), g in seen.items():
        if not g["supported"]:
            kind = "unsupported"
        elif msg_tools.get((s, tool), 0):
            continue                                 # 이 기록에 그 AI 의 질문 · 답이 남아 있음 = 읽었음
        else:
            kind = "failed"
        out.append({"session": s, "tool": tool, "kind": kind, "copies": g["copies"], "first": g["first"], "last": g["last"]})
    return sorted(out, key=lambda g: g["first"])
