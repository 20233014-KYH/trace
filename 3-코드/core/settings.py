"""
settings.py — 기록기 · 알약 · 내역서 화면이 **같은 설정 파일**을 읽게 한다 (10/13)

  찾는 순서:  ① --config 로 준 파일  ② 환경변수 TRACE_CONFIG  ③ 내 설정 ~/trace-config.json  ④ 저장소 collector/config.json

★ 왜 ★
  서버가 둘이다 — 인터넷 서버(Render · Supabase DB) 와 이 PC 의 시험 서버(127.0.0.1 · server/trace.db).
  계정·기록은 서버마다 따로 저장된다. 그런데 기록기는 내 설정(인터넷 서버)으로, 내역서 화면은 저장소 기본 설정
  (시험 서버)으로 열리면 "가입한 계정으로 로그인이 안 된다"(10/12 박상진)가 된다. 실제로는 다른 서버에 물은 것.
  → 세 프로그램이 같은 순서로 같은 파일을 찾는다. 내 설정이 있으면 늘 그것.

내 설정은 저장소 밖(홈 폴더)이라 깃에 안 올라간다. 내역서 화면의 "인터넷 서버로 바꾸기" 가 이 파일을 만든다.
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # 3-코드
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


def load(arg=None):
    """→ (설정 dict, 경로)"""
    p = config_path(arg)
    with open(p, encoding="utf-8") as f:
        return json.load(f), p


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
