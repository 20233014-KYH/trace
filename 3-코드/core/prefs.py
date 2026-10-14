"""
prefs.py — 학생이 설정 화면에서 고르는 것 (이 PC 의 data/settings.json · 10/13)

기록기 설정 파일(trace-config.json · 서버 주소 · data 폴더)과는 따로다 — 그쪽은 개발자 · 설치판이 정하는 것,
이쪽은 학생이 화면에서 바꾸는 것. 기록 창(app/pill.py) · 내보내기(app/export.py) · 설정 화면이 같이 읽는다.

  ★ 원문 기록(AI 질문·답 · 과제 글 · 복사한 답 일부) 과 자동 가리기는 여기 없다 — 끌 수 없음 (10/13 사용자 결정)
"""
import json
import os

from core import safefile

FILE = "settings.json"
DEFAULTS = {
    # 기록 창
    "ask_on_open": True,        # Word 파일을 열면 "이 과제 기록할까요?" (기록기에 아직 없음 · 화면에선 준비 중)
    "show_time": True,          # 기록 창에 시간 보이기 (끄면 점만)
    "position": "br",           # 기록 창 자리: br 오른쪽 아래 · bl 왼쪽 아래 · tr 오른쪽 위 · tl 왼쪽 위
    "idle_min": 5,              # 입력이 없으면 쉬는 중으로 보는 분 (기록기 idle_after_sec)
    "autostart": False,         # 윈도우를 켜면 Trace 도 켜기 (설치판 뒤 · 화면에선 준비 중)
    # 내역서 기본값 (10/13 모두 켬)
    "link_days": 14,            # 교수 링크 기간
    "with_source": True,        # 교수 링크에 출처 보기
    "with_process": True,       # 교수 링크에 작업 과정
    "mask_part": True,          # 찾은 개인 정보는 그 부분만 가리기
    # 처음 한 번 (준비 점검) 을 봤나 — 로그인 뒤 홈 대신 /welcome 으로 한 번
    "onboarded": False,
}
CHOICES = {"position": ("br", "bl", "tr", "tl"), "idle_min": (3, 5, 10, 15), "link_days": (7, 14, 30)}


def load(data_dir):
    """기본값 위에 저장한 것을 얹어서 → dict (파일이 없거나 깨져도 기본값)"""
    out = dict(DEFAULTS)
    try:
        saved = safefile.read_json(os.path.join(data_dir, FILE), {})
        out.update({k: v for k, v in saved.items() if k in DEFAULTS and check(k, v)})
    except AttributeError:
        pass
    return out


def check(k, v):
    """한 값이 올바른가 — 켜고 끄는 것은 bool, 고르는 것은 CHOICES 안"""
    if k not in DEFAULTS:
        return False
    if k in CHOICES:
        return v in CHOICES[k] and not isinstance(v, bool)
    return isinstance(v, bool)


def save(data_dir, changes):
    """changes 를 검사해 저장 → (새 설정, 오류 글 | None)"""
    bad = [k for k, v in changes.items() if not check(k, v)]
    if bad:
        return None, f"바꿀 수 없는 값이에요: {', '.join(bad)}"
    cur = load(data_dir)
    cur.update(changes)
    safefile.write_json(os.path.join(data_dir, FILE), {k: v for k, v in cur.items() if v != DEFAULTS[k]}, indent=1)
    return cur, None
