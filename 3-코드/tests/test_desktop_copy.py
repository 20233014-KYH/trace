"""
test_desktop_copy.py — 데스크톱 AI 앱(ChatGPT 앱 · Claude 앱)에서 복사해 붙여넣은 글이 AI 답과 이어지는지 (10/9)

  python tests/test_desktop_copy.py

  10/9 ChatGPT 앱 녹화 시험: 앱에서 복사해 Word 에 붙인 글이 '다른 곳에서 붙여넣음 (ChatGPT)' 으로 갔다.
  해시 고리(복사 발췌 = copy = paste)의 '복사 발췌'를 웹 AI 는 확장이 남기는데, 앱은 남기는 쪽이 없었기 때문.
  → 수집기가 데스크톱 AI 앱에서 복사하면 복사한 글을 발췌로 PC 에 남긴다 (collector._desktop_excerpt).
"""
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "collector"))
from core import match as M          # noqa: E402

fails = []


def check(name, ok, detail=""):
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


def collector():
    fake = types.ModuleType("platform_win")
    fake.foreground = lambda: ("", "")
    fake.idle_seconds = lambda: 0
    fake.input_permission_hint = lambda: None
    sys.modules["platform_win"] = fake
    real, sys.platform = sys.platform, "win32"
    import collector as C
    sys.platform = real
    with open(os.path.join(ROOT, "collector", "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["data_dir"] = tempfile.mkdtemp()
    return C, C.Collector(cfg, "W_test", dry_run=True), cfg


def main():
    C, c, cfg = collector()
    T = "• 운영 비용 절감: 모델료, 촬영 장소 대여비 등 콘텐츠 제작 비용을 줄일 수 있다."
    c._clip_text = T
    c._desktop_excerpt("ChatGPT.exe")        # 앱에서 복사 → 발췌
    c._desktop_excerpt("chrome.exe")         # 브라우저 복사 → 여기선 안 남김 (확장 몫)
    c._desktop_excerpt("WINWORD.EXE")        # 다른 앱 → 안 남김
    c.capture["ai_answer_excerpt"] = False
    c._desktop_excerpt("claude.exe")         # 토글을 끄면 안 남김
    c.sink.close()
    ctx = [json.loads(line) for f in os.listdir(cfg["data_dir"]) if f.startswith("context")
           for line in open(os.path.join(cfg["data_dir"], f), encoding="utf-8")]
    check("앱에서 복사하면 발췌 하나 · 브라우저·다른 앱·토글 끔은 안 남김", len(ctx) == 1, str(len(ctx)))
    check("발췌 = 복사한 글 그대로 · 도구 이름", ctx and ctx[0]["text"] == T and ctx[0]["meta"]["tool"] == "ChatGPT 앱")

    h = C.sha256_text(T)
    ev = [{"ts": "2026-10-09T18:59:08+09:00", "type": "copy", "hash": h, "app": "ChatGPT.exe", "category": "ai"},
          {"ts": "2026-10-09T18:59:14+09:00", "type": "paste", "hash": h, "app": "WINWORD.EXE"},
          {"ts": "2026-10-09T18:59:14+09:00", "type": "doc_paste_at", "app": "Word", "file": "문서2", "where": "문단 3"}]
    ctx += [{"ts": "2026-10-09T18:59:14+09:00", "kind": "diff", "text": T, "meta": {"where": "문단 3"}}]
    ai, other = M.pasted_from_ai(ev, ctx), M.pasted_from_other(ev, ctx)
    check("붙여넣은 글 = AI 답 붙여넣기 (해시 고리)", len(ai) == 1 and ai[0]["domain"] == "chatgpt.exe", str(ai))
    check("'다른 곳에서 붙여넣음' 으로 가지 않음", other == [], str(other))
    without = [x for x in ctx if x.get("kind") != "ai_answer_excerpt"]
    check("(고치기 전) 발췌가 없으면 '다른 곳' 으로 갔었다", len(M.pasted_from_other(ev, without)) == 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
    print("✓ 통과" if not fails else f"✗ {len(fails)}건 실패")
    sys.exit(1 if fails else 0)
