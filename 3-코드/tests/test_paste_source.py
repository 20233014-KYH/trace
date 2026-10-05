"""
test_paste_source.py — 붙여넣기 출처가 "어느 사이트에서 복사했나" 로 맞게 남는지 (수집기 → derive 한 바퀴)

  python tests/test_paste_source.py

실제 collector.Collector 를 돌리고, 운영체제 쪽(창 · 클립보드)만 가짜로 바꾼다. 리눅스에서도 돈다.
지키는 것:
  · 나무위키처럼 domains.json 에 없는 사이트도 도메인(또는 창 제목)이 출처로 남는다 — 분류는 기타
  · 문서 제목에 "ChatGPT" · "Claude" 가 있어도 확장이 알려준 도메인이 이긴다 (AI 답으로 세지 않음)
  · 맥(창 제목 없음 · 앱 이름 "Google Chrome")에서도 확장 도메인으로 분류·출처 표기
  · 확장이 없으면 예전처럼 창 제목 키워드로 판별
"""
import glob
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "collector"))
sys.path.insert(0, ROOT)

fake = types.ModuleType("platform_win")          # 운영체제 함수는 아래 run() 에서 바꿔 끼운다
fake.foreground = lambda: ("", "")
fake.idle_seconds = lambda: 0
fake.input_permission_hint = lambda: None
sys.modules["platform_win"] = fake
_real_platform, sys.platform = sys.platform, "win32"
import pyperclip                                 # noqa: E402
import collector as M                            # noqa: E402
sys.platform = _real_platform
from core.derive import derive                   # noqa: E402


def run(steps):
    """steps: ("win", 앱, 제목) · ("tab", 도메인, 제목) · ("copy", 글) · ("paste", 앱, 제목). 탭 이벤트 뒤엔 폴링 1번 (실제 1초 주기)."""
    with open(os.path.join(ROOT, "collector", "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["data_dir"] = tempfile.mkdtemp()
    clip, fg = {"t": ""}, {"v": ("Code.exe", "a.md")}
    pyperclip.paste = lambda: clip["t"]
    M.foreground = lambda: fg["v"]
    M.idle_seconds = lambda: 0
    c = M.Collector(cfg, "proof", "W_test", dry_run=True)
    for s in steps:
        if s[0] == "win":
            fg["v"] = (s[1], s[2]); c._tick()
        elif s[0] == "tab":
            c._on_tab({"domain": s[1], "title": s[2]}); c._tick()
        elif s[0] == "copy":
            c._on_copy_key(); clip["t"] = s[1]; c._tick()
        elif s[0] == "paste":
            fg["v"] = (s[1], s[2]); c._tick(); c._on_paste()
    c.sink.close()
    evs = [json.loads(line) for p in glob.glob(os.path.join(cfg["data_dir"], "events-*.jsonl"))
           for line in open(p, encoding="utf-8")]
    return derive(evs)["pastes"][-1]


CASES = [
    # (이름, 단계, 기대 ai, 기대 분류, 출처 표기에 들어가야 할 글)
    ("나무위키 일반 문서",
     [("win", "Code.exe", "a.md"), ("win", "chrome.exe", "고양이 - 나무위키 - Chrome"), ("tab", "namu.wiki", "고양이 - 나무위키"),
      ("copy", "고양이는 식육목 고양이과의 동물이다."), ("paste", "Code.exe", "a.md")],
     False, "other", "namu.wiki"),
    ("나무위키 'ChatGPT' 문서 — 제목 키워드보다 도메인",
     [("win", "Code.exe", "a.md"), ("win", "chrome.exe", "ChatGPT - 나무위키 - Chrome"), ("tab", "namu.wiki", "ChatGPT - 나무위키"),
      ("copy", "ChatGPT는 OpenAI가 개발한 챗봇이다."), ("paste", "Code.exe", "a.md")],
     False, "other", "나무위키"),
    ("위키백과 'Claude' 문서 — 자료",
     [("win", "Code.exe", "a.md"), ("win", "chrome.exe", "Claude (언어 모델) - 위키백과 - Chrome"),
      ("tab", "ko.wikipedia.org", "Claude (언어 모델)"), ("copy", "Claude는 언어 모델이다."), ("paste", "Code.exe", "a.md")],
     False, "resource", "위키백과"),
    ("맥 크롬 chatgpt.com — 창 제목 없음",
     [("win", "Code", ""), ("win", "Google Chrome", ""), ("tab", "chatgpt.com", "ChatGPT"),
      ("copy", "AI 답변입니다."), ("paste", "Code", "")],
     True, "ai", "chatgpt.com"),
    ("맥 크롬 나무위키 → 다른 앱 → 복귀 (탭 이벤트 없음)",
     [("win", "Google Chrome", ""), ("tab", "namu.wiki", "고양이"), ("win", "Code", ""), ("win", "Google Chrome", ""),
      ("copy", "고양이는 동물"), ("paste", "Code", "")],
     False, "other", "namu.wiki"),
    ("확장 없음 — 창 제목 키워드로 AI",
     [("win", "chrome.exe", "ChatGPT - Chrome"), ("copy", "AI 답"), ("paste", "Code.exe", "a.md")],
     True, "ai", "ChatGPT"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import contextlib, io
    bad = 0
    for name, steps, ai, cat, label in CASES:
        with contextlib.redirect_stdout(io.StringIO()):   # 수집기 콘솔 출력 숨김
            p = run(steps)
        src = p["src"] or {}
        ok = p["matched"] and p["ai"] == ai and src.get("category") == cat and label in src.get("title", "")
        bad += not ok
        print(f"{'✓' if ok else '✗'} {name:42} ai={p['ai']!s:5} 분류={src.get('category')!s:8} 출처={src.get('app')} · {src.get('title')}")
    if bad:
        sys.exit(f"✗ {bad}건 실패")
    print("✓ 통과")


if __name__ == "__main__":
    main()
