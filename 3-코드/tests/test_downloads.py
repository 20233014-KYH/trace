"""
test_downloads.py — 기록하는 동안 받은 결과물 파일 (collector/downloads.py · 10/15)

  python tests/test_downloads.py

  · 다운로드 폴더에 새 결과물 파일 → 다 받으면 한 번 (브라우저식 .crdownload → 이름 바꿈 · 바로 저장)
  · 임시 · 잠금 파일(~$) · 결과물이 아닌 파일(.zip · .exe)은 무시
  · 기록기: 그 순간 앞에 있던 앱이 AI 앱 · 브라우저일 때만 남김 (Word 로 내 글을 저장한 것은 아님) · 파일 이름 · 지문 · 글
"""
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "collector")]
import downloads as D                           # noqa: E402

ok = True


def 검사(이름, 조건, 설명=""):
    global ok
    ok &= bool(조건)
    print(f"  {'✓' if 조건 else '✗'} {이름}  {설명}")


def 기다림(조건, 초=8):
    for _ in range(int(초 * 10)):
        if 조건():
            return True
        time.sleep(0.1)
    return False


print("\n  받은 파일 지켜보기 검사\n  " + "─" * 60)
t = tempfile.mkdtemp(prefix="trace-dl-")
받음 = []
w = D.DownloadWatcher([t], lambda p, raw: 받음.append((os.path.basename(p), len(raw))))
w.start()
try:
    pdf = open(os.path.join(ROOT, "tests", "fixtures", "match_view", "report.pdf"), "rb").read()
    # 브라우저식: 임시 이름으로 받다가 다 받으면 이름을 바꿈
    임시 = os.path.join(t, "보고서.pdf.crdownload")
    with open(임시, "wb") as f:
        f.write(pdf[:1000]); f.flush(); time.sleep(0.3); f.write(pdf[1000:])
    os.replace(임시, os.path.join(t, "보고서.pdf"))
    검사("브라우저식 받기(.crdownload → .pdf) — 다 받은 뒤 한 번", 기다림(lambda: 받음) and 받음 == [("보고서.pdf", len(pdf))], str(받음))
    # 바로 저장 (데스크톱 앱 저장 창)
    open(os.path.join(t, "답.md"), "w", encoding="utf-8").write("# 보고서\n도시 열섬 현상은 도시가 주변보다 더 뜨거운 현상이다.")
    검사("데스크톱 앱이 바로 저장한 파일도", 기다림(lambda: any(n == "답.md" for n, _ in 받음)))
    전 = len(받음)
    for n in ("~$보고서.docx", "설치.exe", "묶음.zip"):
        open(os.path.join(t, n), "wb").write(b"x" * 10)
    time.sleep(2.5)
    검사("잠금 파일 · 결과물이 아닌 파일은 무시", len(받음) == 전, str(받음[전:]))
    글 = D.글_뽑기("x.pdf", pdf)
    검사("PDF 안의 글을 뽑음 (출처 보기와 같은 읽기)", "AI 자동화" in 글 or len(글) > 50, f"{len(글)}자")
finally:
    w.stop()
    shutil.rmtree(t, ignore_errors=True)

print("\n  ━━ 기록기: 앞에 있던 앱으로 고름")
import collector as C                           # noqa: E402


class 가짜:
    _tab = ("chatgpt.com", "ai", "", "chrome")
    _tab_fits = C.Collector._tab_fits
    _받은_곳 = C.Collector._받은_곳
    DL_WAIT = 0.3

    class sink:
        paused = False

    class clf:
        by_domain = staticmethod(lambda d: "ai" if d in ("claude.ai", "chatgpt.com") else "web")

    def __init__(self, cur):
        self._cur, self.남김, self._dl_src = cur, [], {}

    def _on_context(self, items):
        self.남김 += items


raw = "도시 열섬 현상 보고서".encode("utf-8")
for cur, 남김, 이름 in ((("claude.exe", "Claude", "ai"), True, "Claude 앱이 앞에 있을 때 받은 파일 → 남김 (AI)"),
                     (("chrome.exe", "ChatGPT", "ai"), True, "브라우저(AI 탭)에서 받은 파일 → 남김 · 사이트 이름"),
                     (("WINWORD.EXE", "보고서 - Word", "work"), False, "Word 로 내 글을 다운로드 폴더에 저장 → 안 남김")):
    f = 가짜(cur)
    C.Collector._on_download(f, os.path.join("x", "보고서.txt"), raw)
    검사(이름, bool(f.남김) == 남김 and (not f.남김 or (f.남김[0]["kind"] == "download" and f.남김[0]["meta"]["hash"].startswith("sha256:")
                                                     and f.남김[0]["text"] == "도시 열섬 현상 보고서")),
         str(f.남김[0]["meta"] if f.남김 else ""))
f = 가짜(("chrome.exe", "ChatGPT", "ai")); C.Collector._on_download(f, "보고서.txt", raw)
검사("브라우저면 그때 탭 사이트를 받은 곳으로", f.남김[0]["meta"]["domain"] == "chatgpt.com" and f.남김[0]["meta"]["category"] == "ai")

print("\n  ━━ 확장이 알려 준 받은 사이트 (확장 0.3.9 · 10/17)")
알림 = [{"kind": "download_src", "text": "", "meta": {"name": "보고서 (2).txt", "site": "claude.ai", "browser": "chrome"}}]
f = 가짜(("chrome.exe", "새 탭", "other")); f._tab = ("", "other", "", "chrome")
C.Collector._on_context(f, 알림)
검사("받기 알림은 파일에 안 남기고 기억만", f._dl_src.get("보고서 (2).txt", ("",))[0] == "claude.ai")
C.Collector._on_download(f, os.path.join("x", "보고서 (2).txt"), raw)
m = f.남김[0]["meta"] if f.남김 else {}
검사("앞 탭이 새 탭이어도 확장이 알려 준 사이트로 (전엔 빈칸)", m.get("domain") == "claude.ai" and m.get("category") == "ai", str(m))
f = 가짜(("WINWORD.EXE", "보고서 - Word", "work"))
C.Collector._on_context(f, 알림)
C.Collector._on_download(f, "보고서 (2).txt", raw)
m = f.남김[0]["meta"] if f.남김 else {}
검사("받기가 끝날 때 Word 로 옮겼어도 브라우저에서 받은 파일로 남김", m.get("domain") == "claude.ai" and m.get("app") == "chrome.exe", str(m))
f = 가짜(("WINWORD.EXE", "보고서 - Word", "work"))
C.Collector._on_context(f, [{**알림[0], "meta": {**알림[0]["meta"], "name": "다른 파일.txt"}}])
C.Collector._on_download(f, "보고서 (2).txt", raw)
검사("이름이 다른 받기 알림은 안 씀 (Word 로 저장한 내 글은 그대로 안 남김)", not f.남김)
f = 가짜(("chrome.exe", "ChatGPT", "ai")); f.sink = type("s", (), {"paused": True})
C.Collector._on_context(f, 알림)
검사("멈춘 동안의 받기 알림은 버림", not f._dl_src)
print(f"\n  {'✓ 통과' if ok else '✗ 실패'}")
sys.exit(0 if ok else 1)
