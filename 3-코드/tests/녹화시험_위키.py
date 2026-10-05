"""
녹화시험_위키.py — 나무위키 · 위키백과에서 복사 → 붙여넣기가 실제 브라우저 + 확장 + 수집기로 어떻게 기록되나 (화면 녹화)

  xvfb-run -s "-screen 0 1440x900x24" python tests/녹화시험_위키.py      # 리눅스 (Xvfb · ffmpeg · xclip · playwright)
  → data/녹화시험/녹화.mp4 · events.jsonl · session.json · 결과.md

실제로 도는 것: Chromium + Trace 확장(extension/) · 수집기 Collector.run() 과 확장 다리(127.0.0.1:5077) ·
  X 클립보드(xclip) · core/derive.py
가짜인 것:
  · 사이트 내용 — 클라우드 환경에서 namu.wiki · ko.wikipedia.org 가 막혀서, 브라우저가 그 주소를 로컬 페이지로 연다
    (--host-resolver-rules). 확장이 보는 도메인 · 탭 제목은 진짜와 같다. 실제 사이트가 열리는 PC 면 MOCK=0 으로.
  · 전경 창 — 리눅스엔 foreground() 가 없어서, 시험이 지금 앞에 있는 창(크롬 탭 / VS Code)을 알려준다 (윈도우 표기)
  · 키 훅 — Playwright 키 입력은 OS 키 훅에 안 잡혀서, Ctrl+C · Ctrl+V 순간에 수집기 콜백을 직접 부른다 (keys.py 가 하는 일)
"""
import http.server
import json
import os
import shutil
import ssl
import subprocess
import sys
import threading
import time
import types
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "녹화시험")
MOCK = os.environ.get("MOCK", "1") != "0"
sys.path.insert(0, os.path.join(ROOT, "collector"))
sys.path.insert(0, ROOT)

# ── 수집기: 운영체제 함수만 바꿔 끼운다 ──
FG = {"v": ("Code.exe", "report.md - trace - Visual Studio Code")}
fake = types.ModuleType("platform_win")
fake.foreground = lambda: FG["v"]
fake.idle_seconds = lambda: 0
fake.input_permission_hint = lambda: None
sys.modules["platform_win"] = fake
_real, sys.platform = sys.platform, "win32"
import collector as M                    # noqa: E402
sys.platform = _real
from core.derive import derive           # noqa: E402
from playwright.sync_api import sync_playwright   # noqa: E402

# ── 시나리오: (사이트 주소, 탭 제목, 본문 첫 문단 = 복사할 글, 기대) ──
SCENES = [
    ("https://namu.wiki/w/고양이", "고양이 - 나무위키",
     "고양이는 식육목 고양이과에 속하는 포유류로, 사람과 함께 살아온 대표적인 반려동물이다.", "기타 · namu.wiki"),
    ("https://namu.wiki/w/ChatGPT", "ChatGPT - 나무위키",
     "ChatGPT는 OpenAI가 개발한 대화형 인공지능 서비스로, 2022년 11월에 공개되었다.", "기타 (제목에 ChatGPT 가 있어도 AI 아님)"),
    ("https://ko.wikipedia.org/wiki/고양이", "고양이 - 위키백과, 우리 모두의 백과사전",
     "고양이는 고양이과에 속하는 작은 육식 동물로, 약 1만 년 전부터 사람과 함께 살아왔다.", "학습자료 · ko.wikipedia.org"),
    ("https://ko.wikipedia.org/wiki/Claude_(언어_모델)", "Claude (언어 모델) - 위키백과, 우리 모두의 백과사전",
     "Claude는 Anthropic이 개발한 대규모 언어 모델 계열이다.", "학습자료 (제목에 Claude 가 있어도 AI 아님)"),
    ("https://chatgpt.com/c/demo", "파이썬 예외처리 질문",
     "try 블록에서 예외가 나면 except 블록이 실행되고, finally 는 항상 실행됩니다.", "AI (대조군 — 창 제목만으론 모름, 도메인으로 AI)"),
]

PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font:16px/1.7 system-ui,'Noto Sans CJK KR',sans-serif;margin:0;background:{bg}}}
header{{background:{hd};color:#fff;padding:14px 28px;font-weight:700;font-size:20px}}
main{{max-width:760px;padding:24px 28px}} h1{{font-size:30px;margin:4px 0 16px}} .note{{color:#888;font-size:13px}}</style></head>
<body><header>{brand}</header><main><h1>{h1}</h1><p id="lead">{lead}</p>
<p class="note">(녹화시험용 로컬 페이지 — 주소·탭 제목은 실제 사이트와 같고 내용만 흉내)</p></main></body></html>"""
BRAND = {"namu.wiki": ("나무위키", "#00a495", "#fff"), "ko.wikipedia.org": ("위키백과", "#36c", "#f8f9fa"),
         "chatgpt.com": ("ChatGPT", "#202123", "#fff")}


class Mock(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        url = f"https://{host}{unquote(self.path)}"
        sc = next((s for s in SCENES if s[0] == url), None)
        if not sc:
            self.send_response(404); self.end_headers(); return
        brand, hd, bg = BRAND[host]
        body = PAGE.format(title=sc[1], brand=brand, hd=hd, bg=bg, h1=sc[1].split(" - ")[0], lead=sc[2]).encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


def mock_server():
    cert = os.path.join(OUT, "mock.pem")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=mock",
                    "-keyout", cert, "-out", cert], check=True, capture_output=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8443), Mock)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()


# ── 화면 오른쪽 패널: 수집기가 방금 남긴 기록 ──
PANEL_JS = """([cap, rows]) => {
  let p = document.getElementById('__trace');
  if (!p) { p = document.createElement('div'); p.id='__trace';
    p.style.cssText='position:fixed;top:0;right:0;width:520px;height:100vh;background:#111;color:#ddd;font:12.5px/1.55 ui-monospace,monospace;padding:12px 14px;box-sizing:border-box;overflow:hidden;z-index:99999;border-left:3px solid #ef4444';
    document.body.appendChild(p); document.body.style.marginRight='520px'; }
  const esc = (s) => s.replace(/[&<>]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  p.innerHTML = '<div style="color:#fff;font:700 15px system-ui;margin-bottom:6px">Trace 수집기 — 실시간 기록</div>'
    + '<div style="background:#ef4444;color:#fff;padding:6px 8px;border-radius:6px;margin-bottom:10px;font:600 13px system-ui">' + esc(cap) + '</div>'
    + rows.slice(-30).map((r) => '<div style="color:' + r[0] + '">' + esc(r[1]) + '</div>').join('');
}"""
COLOR = {"ai": "#f87171", "resource": "#60a5fa", "work": "#4ade80", "other": "#a1a1aa"}


def row(ev):
    t, k = ev["ts"][11:19], ev["type"]
    if k == "window":
        return COLOR.get(ev["category"], "#ddd"), f"{t} 창   [{ev['category']}] {ev['app']} · {ev['title'][:38]}"
    if k == "tab":
        return COLOR.get(ev["category"], "#ddd"), f"{t} 탭   [{ev['category']}] {ev['domain']}  (확장)"
    if k == "copy":
        return "#fbbf24", f"{t} 복사 {ev['len']}자 · [{ev['category']}] {ev['app']}"
    if k == "paste":
        return "#fbbf24", f"{t} 붙여넣기 {ev['len']}자 → {ev['app']}"
    return "#777", f"{t} {k}"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
    if MOCK:
        mock_server()

    with open(os.path.join(ROOT, "collector", "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.update(data_dir=OUT, keys={"enabled": False}, office={"enabled": False}, files={"watch_dirs": []})
    col = M.Collector(cfg, "proof", "W_녹화시험", dry_run=True)
    events = []
    emit = col.sink.emit
    col.sink.emit = lambda ev: (events.append(dict(ev, ts=M.now_iso())), emit(ev))[1]
    threading.Thread(target=col.run, daemon=True).start()
    time.sleep(1.5)

    disp = os.environ.get("DISPLAY", ":99")
    rec = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "x11grab", "-framerate", "12", "-video_size", "1440x900",
                            "-i", disp, "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-preset", "veryfast",
                            os.path.join(OUT, "녹화.mp4")], stdin=subprocess.PIPE)
    ext = os.path.join(ROOT, "extension")
    args = [f"--disable-extensions-except={ext}", f"--load-extension={ext}", "--no-proxy-server",
            "--window-position=0,0", "--window-size=1440,900", "--no-first-run", "--lang=ko-KR", "--test-type"]
    if MOCK:
        args += ["--host-resolver-rules=MAP namu.wiki 127.0.0.1:8443, MAP ko.wikipedia.org 127.0.0.1:8443, MAP chatgpt.com 127.0.0.1:8443",
                 "--ignore-certificate-errors"]
    results = []
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(os.path.join(OUT, "profile"), headless=False, args=args,
                                                    executable_path=os.environ.get("CHROMIUM") or None,
                                                    no_viewport=True, ignore_https_errors=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def show(cap, wait=0.0):
            time.sleep(wait)
            try:
                page.evaluate(PANEL_JS, [cap, [row(e) for e in events if e["type"] != "heartbeat"]])
            except Exception as e:
                print("  (패널 못 그림:", str(e).splitlines()[0], ")")

        for i, (url, title, lead, expect) in enumerate(SCENES, 1):
            page.goto(url)
            FG["v"] = ("chrome.exe", f"{title} - Chrome")           # 크롬이 앞에 있음 (윈도우 창 제목 표기)
            show(f"{i}/{len(SCENES)} {url} 열기", 2.5)              # 확장 tab 이벤트 + 수집기 1초 폴링
            n0 = len(events)
            page.evaluate("""() => { const r = document.createRange(); r.selectNodeContents(document.getElementById('lead'));
                                     const s = getSelection(); s.removeAllRanges(); s.addRange(r); }""")
            col._on_copy_key()                                       # Ctrl+C 키 훅 (keys.py 가 부르는 것)
            page.keyboard.press("Control+C")                         # 실제 복사 → X 클립보드
            show(f"{i}/{len(SCENES)} 첫 문단 드래그 → Ctrl+C", 2.0)
            FG["v"] = ("Code.exe", "report.md - trace - Visual Studio Code")
            show(f"{i}/{len(SCENES)} VS Code 로 전환 → Ctrl+V", 1.5)
            col._on_paste()                                          # Ctrl+V 키 훅
            show(f"{i}/{len(SCENES)} 붙여넣기 기록됨 · 기대: {expect}", 2.5)
            copied = [e for e in events[n0:] if e["type"] == "copy"]
            results.append((url, title, expect, copied[-1] if copied else None))
            FG["v"] = ("chrome.exe", f"{title} - Chrome")

        col._stop.set(); time.sleep(1.5)                            # 봉인 (session_end)
        col.sink.close()
        evs = [json.loads(l) for l in open(col.sink._log_path, encoding="utf-8")]
        sess = derive(evs)
        with open(os.path.join(OUT, "session.json"), "w", encoding="utf-8") as f:
            json.dump(sess, f, ensure_ascii=False, indent=1)
        shutil.copy(col.sink._log_path, os.path.join(OUT, "events.jsonl"))

        # 마지막 화면: 결과 뷰어 (ui/viewer.html) 에 session.json 을 그대로
        page.goto("file://" + os.path.join(ROOT, "ui", "viewer.html"))
        page.evaluate("(s) => render(s)", sess)
        time.sleep(4)
        for y in range(0, 2400, 400):
            page.mouse.wheel(0, 400); time.sleep(1.2)
        ctx.close()
    rec.communicate(b"q", timeout=30)

    lines = ["# 녹화시험 — 나무위키 · 위키백과 붙여넣기 출처", "",
             f"사이트 내용: {'로컬 흉내 페이지 (주소·탭 제목은 실제와 같음)' if MOCK else '실제 사이트'} · 전경 창: 시험이 지정 · 나머지(브라우저·확장·수집기·클립보드·derive)는 실제", "",
             "| # | 주소 | 기대 | 붙여넣기 출처 (derive) | AI 로 셈 |", "|---|---|---|---|---|"]
    bad = 0
    for i, (p, sc) in enumerate(zip(sess["pastes"], SCENES), 1):
        src = p["src"] or {}
        want_ai = sc[3].startswith("AI")
        ok = p["matched"] and p["ai"] == want_ai
        bad += not ok
        lines.append(f"| {i} | {sc[0]} | {sc[3]} | {'✓' if ok else '✗'} [{src.get('category')}] {src.get('app')} · {src.get('title')} | {p['ai']} |")
    lines += ["", f"붙여넣기 {len(sess['pastes'])}건 · 체인 {sess['stats']['events']}건 · root `{sess['root'][:16]}…`",
              "", "✓ 통과" if bad == 0 and len(sess["pastes"]) == len(SCENES) else f"✗ {bad}건 다름"]
    open(os.path.join(OUT, "결과.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
