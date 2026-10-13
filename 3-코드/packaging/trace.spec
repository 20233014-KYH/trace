# -*- mode: python ; coding: utf-8 -*-
"""
trace.spec — PyInstaller 묶음 설정 (v0.1 · 10/13).  직접 부르지 말고 packaging/build.py 로.

  dist/Trace/Trace.exe          ← packaging/trace_app.py (창만 · 콘솔 없음)
  dist/Trace/_internal/trace/   ← 우리 원본 .py · html · json · 글꼴 그대로 (trace_app.py 머리말 참고)

라이브러리는 우리 코드의 import 를 읽어서 모은다 — 새 라이브러리를 써도 여기를 안 고쳐도 되게.
(우리 모듈 자체는 묶음에 넣지 않는다: 같은 이름이 둘이면 묶음 쪽이 먼저 잡혀 __file__ 이 틀어진다)
"""
import ast
import glob
import importlib.util
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

HERE = SPECPATH                                   # noqa: F821  PyInstaller 가 넣어 줌
ROOT = os.path.dirname(HERE)                      # 3-코드

# ── 싣는 원본 (테스트 · 개발용 도구는 뺀다) ──
원본_폴더 = ["app", "collector", "core"]
뺄 = ("test_", "dev_receiver", "compare_", "llm.py")
datas, 우리_파일 = [], []
for d in 원본_폴더:
    for p in glob.glob(os.path.join(ROOT, d, "*")):
        n = os.path.basename(p)
        if os.path.isdir(p) or n.startswith(뺄) or n.endswith((".pyc", ".log")):
            continue
        datas.append((p, os.path.join("trace", d)))
        if n.endswith(".py"):
            우리_파일.append(p)
for p in ["server/statement_pdf.py", "server/demo_share.json"] + glob.glob(os.path.join(ROOT, "server", "fonts", "*")):
    p = os.path.join(ROOT, p) if not os.path.isabs(p) else p
    datas.append((p, os.path.join("trace", os.path.dirname(os.path.relpath(p, ROOT)))))
    if p.endswith(".py"):
        우리_파일.append(p)

# ── 우리 코드가 import 하는 것 (표준 라이브러리 + 설치된 라이브러리) ──
우리_이름 = {os.path.splitext(os.path.basename(p))[0] for p in 우리_파일} | {"core", "statement_pdf"}
쓰는 = set()
for p in 우리_파일:
    for n in ast.walk(ast.parse(open(p, encoding="utf-8").read())):
        if isinstance(n, ast.Import):
            쓰는 |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            쓰는.add(n.module)
            쓰는 |= {f"{n.module}.{a.name}" for a in n.names}       # from x import 모듈 — 모듈이면 같이
hidden = []
for m in sorted(쓰는):
    if m.split(".")[0] in 우리_이름 or m.split(".")[0] in ("openai", "anthropic"):   # 우리 것 · 쓰지 않는 LLM
        continue
    try:
        if importlib.util.find_spec(m) is not None:
            hidden.append(m)
    except (ImportError, ValueError, AttributeError):
        pass                                     # 이 OS 에 없는 것 (맥 전용 · 윈도우 전용) · 모듈이 아닌 이름
# 실행 중에 고르는 백엔드 — import 문만으로는 안 보인다
for pkg in ("pynput", "watchdog.observers", "webview", "comtypes", "win32com", "reportlab.graphics.barcode"):
    try:
        hidden += collect_submodules(pkg)
    except Exception:                             # noqa: BLE001  이 OS 에 없음
        pass
hidden += ["comtypes.stream"] if sys.platform == "win32" else []
print(f"[trace.spec] 원본 {len(datas)}개 · 라이브러리 {len(hidden)}개")

a = Analysis(                                     # noqa: F821
    [os.path.join(HERE, "trace_app.py")],
    pathex=[],
    datas=datas,
    hiddenimports=hidden,
    # core 는 trace_app.py 가 import 하지만 묶지 않는다 — 원본(_internal/trace/core)을 읽어야 ROOT 가 맞다
    excludes=["core", "tkinter", "matplotlib", "numpy", "pandas", "IPython", "pytest", "openai", "anthropic",
              "sqlalchemy", "psycopg"],
    noarchive=False,
)
pyz = PYZ(a.pure)                                 # noqa: F821
icon = os.path.join(HERE, "build", "trace.ico")
exe = EXE(                                        # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Trace",
    console=False,                                # 창만 — print 는 내 폴더 logs/ 로 (trace_app._log)
    icon=icon if os.path.exists(icon) else None,
    version=os.path.join(HERE, "build", "version_info.txt") if sys.platform == "win32" else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Trace")   # noqa: F821
