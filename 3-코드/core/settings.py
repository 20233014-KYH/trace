"""
settings.py — 기록기 · 알약 · 내역서 화면이 **같은 설정 파일**을 읽게 한다 (10/13)

  찾는 순서:  ① --config 로 준 파일  ② 환경변수 TRACE_CONFIG  ③ 내 설정 ~/trace-config.json  ④ 저장소 collector/config.json

★ 왜 ★
  서버가 둘이다 — 인터넷 서버(Render · Supabase DB) 와 이 PC 의 시험 서버(127.0.0.1 · server/trace.db).
  계정·기록은 서버마다 따로 저장된다. 그런데 기록기는 내 설정(인터넷 서버)으로, 내역서 화면은 저장소 기본 설정
  (시험 서버)으로 열리면 "가입한 계정으로 로그인이 안 된다"(10/12 박상진)가 된다. 실제로는 다른 서버에 물은 것.
  → 세 프로그램이 같은 순서로 같은 파일을 찾는다. 내 설정이 있으면 늘 그것.

내 설정은 저장소 밖(홈 폴더)이라 깃에 안 올라간다. 내역서 화면의 "인터넷 서버로 바꾸기" 가 이 파일을 만든다.

설치판(Trace.exe · packaging/) 에서는 (10/13)
  · 처음 켤 때 내 설정을 만든다 — 인터넷 서버 · 이 PC 만의 과제 id (W_local 은 모두가 같아 남의 과제와 겹친다)
  · 기록 폴더는 설치 폴더 밖 (윈도우 %LOCALAPPDATA%\Trace\data) — 새 버전을 깔아도 기록이 남게
"""
import json
import os
import shutil
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # 3-코드 (설치판은 _internal/trace)
FROZEN = bool(getattr(sys, "frozen", False))                           # PyInstaller 로 묶인 설치판
REPO = os.path.join(ROOT, "collector", "config.json")
USER = os.path.join(os.path.expanduser("~"), "trace-config.json")
INTERNET = "https://trace-server-8aa0.onrender.com/api"
LOCAL = "http://127.0.0.1:5000/api"


def config_path(arg=None):
    """쓸 설정 파일 경로 (위 순서)"""
    for p in (arg, os.environ.get("TRACE_CONFIG")):
        if p:
            return os.path.abspath(p)
    return USER if os.path.exists(USER) else REPO


def app_data():
    """설치판의 내 폴더 — 기록 · 로그. 설치 폴더와 따로 둬야 업데이트해도 안 지워진다."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "Trace")


def load(arg=None):
    """→ (설정 dict, 경로)"""
    p = config_path(arg)
    with open(p, encoding="utf-8") as f:
        cfg = json.load(f)
    if FROZEN and not os.path.isabs(cfg.get("data_dir") or ""):
        cfg["data_dir"] = os.path.join(app_data(), "data")    # 상대 경로면 설치 폴더 안이 된다 → 업데이트 때 지워짐
    return cfg, p


def first_run():
    """설치판을 처음 켤 때 내 설정을 만든다 (있으면 그대로). → 경로"""
    if os.path.exists(USER):
        return USER
    with open(REPO, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["server"] = INTERNET
    cfg["work_id"] = "W-" + uuid.uuid4().hex[:10]
    cfg["data_dir"] = os.path.join(app_data(), "data")
    with open(USER + ".tmp", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(USER + ".tmp", USER)
    return USER


def is_local(server):
    return "127.0.0.1" in (server or "") or "localhost" in (server or "")


def set_server(server):
    """내 설정(~/trace-config.json)의 server 를 바꾼다. 없으면 저장소 기본 설정을 복사해 만든다. → 경로"""
    if not os.path.exists(USER):
        shutil.copyfile(REPO, USER)
    with open(USER, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["server"] = server
    with open(USER + ".tmp", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(USER + ".tmp", USER)
    return USER
