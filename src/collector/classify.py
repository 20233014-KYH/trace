"""
classify.py — 앱 이름·창 제목 → 분류(resource / work / ai / other)

domains.json 을 읽어 분류한다. 매칭 순서(워크플로우 §3.4):
  1. exe 이름 정확 일치 (apps)
  2. 창 제목 키워드 (title_keywords)  ← 브라우저는 확장이 붙기 전까지 이걸로 임시 판별
  3. 나머지 other

브라우저 탭의 실제 도메인은 Tier 1 확장이 보내는 tab 이벤트로 잡는다.
"""
import fnmatch
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ORDER = ("ai", "resource", "work")  # 제목 키워드가 겹칠 때 우선순위 (AI 먼저)


class Classifier:
    def __init__(self, path: str | None = None):
        path = path or os.path.join(_HERE, "domains.json")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        cats = raw.get("categories", raw)
        self.apps: dict[str, str] = {}
        self.keywords: list[tuple[str, str]] = []
        self.domains: list[tuple[str, str]] = []
        for cat in _ORDER:
            c = cats.get(cat, {})
            for exe in c.get("apps", []):
                self.apps[exe.lower()] = cat
            for kw in c.get("title_keywords", []):
                self.keywords.append((kw.lower(), cat))
            for d in c.get("domains", []):
                self.domains.append((d.lower(), cat))

    def by_app(self, exe: str, title: str = "") -> str:
        cat = self.apps.get((exe or "").lower())
        if cat:
            return cat
        t = (title or "").lower()
        for kw, cat in self.keywords:
            if kw in t:
                return cat
        return "other"

    def by_domain(self, domain: str) -> str:
        d = (domain or "").lower()
        for pat, cat in self.domains:
            if d == pat or fnmatch.fnmatch(d, pat) or d.endswith("." + pat):
                return cat
        return "other"


if __name__ == "__main__":
    c = Classifier()
    for exe, title in [("Code.exe", "app.py - trace"), ("chrome.exe", "Claude"),
                       ("chrome.exe", "강의자료_4주차.pdf"), ("Spotify.exe", "Now Playing")]:
        print(f"{exe:14} {title:22} → {c.by_app(exe, title)}")
    for d in ["claude.ai", "www.chatgpt.com", "cs.ac.kr", "example.com"]:
        print(f"{d:22} → {c.by_domain(d)}")
