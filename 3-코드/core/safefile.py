"""
safefile.py — 이 PC data 폴더의 작은 JSON 파일을 여러 요청이 한꺼번에 읽고 써도 안 깨지게 (10/14)

윈도우는 누가 파일을 열어 두면 그 파일을 바꿔 끼우거나(os.replace) 지우지(os.remove) 못한다 (PermissionError · WinError 5 · 32).
화면 서버는 요청마다 스레드를 따로 쓰므로, 내역서 학생 설명을 칠 때 "저장" 과 "미리 보기(읽기)" 가 겹쳐
저장이 HTTP 500 으로 실패했다 (10/14 실제 시험). 로그아웃도 같은 이유로 한 번 auth.json 을 못 지웠다.

  · 같은 파일은 이 프로세스 안에서 한 번에 하나만 읽고 쓴다 (경로마다 잠금)
  · 임시 파일 이름을 쓰는 쪽마다 다르게 → 두 저장이 같은 .tmp 를 같이 쓰지 않는다
  · 다른 프로그램(백신 · 검색 색인)이 잠깐 잡고 있으면 조금 기다렸다 다시 (최대 약 2초)
"""
import json
import os
import threading
import time
import uuid

_잠금들 = {}
_큰_잠금 = threading.Lock()


def lock(path):
    """경로마다 하나인 잠금 (with safefile.lock(p): …)"""
    k = os.path.normcase(os.path.abspath(path))
    with _큰_잠금:
        return _잠금들.setdefault(k, threading.RLock())


def _다시(fn, *a):
    for i in range(40):
        try:
            return fn(*a)
        except PermissionError:
            if i == 39:
                raise
            time.sleep(0.05)


def read_json(path, default=None):
    """없거나 깨졌으면 default"""
    with lock(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return default


def write_json(path, data, **dump_kw):
    """임시 파일에 다 쓴 뒤 바꿔 끼운다 — 쓰다가 꺼져도 예전 파일은 남는다"""
    dump_kw.setdefault("ensure_ascii", False)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.{uuid.uuid4().hex[:8]}.tmp"
    with lock(path):
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, **dump_kw)
            _다시(os.replace, tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass


def remove(path):
    """지움 → 지웠거나 원래 없으면 True"""
    with lock(path):
        try:
            _다시(os.remove, path)
        except FileNotFoundError:
            pass
        except OSError:
            return False
        return not os.path.exists(path)


def drop_lines(path, drop):
    """jsonl 에서 drop(줄 dict) 이 참인 줄만 빼고 다시 쓴다 → 뺀 줄 수. 읽지 못하는 줄은 그대로 둔다 (과제 삭제 · 10/15)"""
    with lock(path):
        try:
            with open(path, encoding="utf-8") as f:
                줄들 = f.readlines()
        except OSError:
            return 0
        남김, 뺌 = [], 0
        for l in 줄들:
            try:
                if l.strip() and drop(json.loads(l)):
                    뺌 += 1
                    continue
            except ValueError:
                pass
            남김.append(l)
        if not 뺌:
            return 0
        tmp = f"{path}.{uuid.uuid4().hex[:8]}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.writelines(남김)
        _다시(os.replace, tmp, path)
        return 뺌
