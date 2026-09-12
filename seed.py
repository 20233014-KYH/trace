# =============================================
# 데모용 chain.json 생성기
#
# 실행 :
#   python seed.py            데모 세션 2개를 "추가"한다 (기존 기록은 그대로 둔다)
#   python seed.py --reset    전부 지우고 데모 2개만 남긴다 (지우기 전에 한 번 묻는다)
#
# 왜 "추가"가 기본인가:
#   에디터로 직접 쓴 기록은 다시 만들 수 없다.
#   실수로 한 번 실행해서 발표 데이터가 날아가는 일이 없어야 한다.
#
# 세션끼리는 체인이 독립이다 (app.py 의 verify 가 세션마다 GENESIS 부터 다시 계산한다).
# 그래서 세션을 뒤에 붙여도 기존 세션의 검증은 깨지지 않는다.
# =============================================

import json
import os
import shutil
import sys
from datetime import datetime, timedelta

# app.py 에 있는 함수를 그대로 가져다 쓴다.
# (같은 규칙으로 만들어야 검증이 통과한다)
from app import chain_hash, content_hash, load_chain, CHAIN_PATH


def build_session(session_id, label, start, steps):
    """steps = [(경과분, 글자수, typed, deleted, pasted, undo), ...]"""
    snapshots = []
    prev = "0" * 64
    text = ""

    for seq, (minute, chars, typed, deleted, pasted, undo) in enumerate(steps):
        t = (start + timedelta(minutes=minute)).isoformat(timespec="seconds")

        # 글자수에 맞춰 가짜 본문을 만든다 (내용 자체는 저장하지 않는다)
        text = "가" * chars
        ch = content_hash(text)

        events = {"typed": typed, "deleted": deleted, "pasted": pasted, "undo": undo}
        h = chain_hash(prev, t, ch, events)

        snapshots.append({
            "seq": seq,
            "time": t,
            "chars": chars,
            "content_hash": ch,
            "events": events,
            "hash": h,
        })
        prev = h

    return {
        "session_id": session_id,
        "label": label,
        "started_at": start.isoformat(timespec="seconds"),
        "snapshots": snapshots,
    }


def unique_id(base, taken):
    """이미 쓰이고 있는 session_id 면 뒤에 번호를 붙여 겹치지 않게 한다.

    s1 이 있으면 s1-2, 그것도 있으면 s1-3 …
    같은 id 가 두 개면 어느 쪽 기록인지 구분할 수 없어진다.
    """
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


# ---------------------------------------------
# 데모 세션의 재료
# ---------------------------------------------

# 세션 1 - 직접 쓴 글. 늘었다 줄었다 하고, 되돌리기가 있다
s1_start = datetime(2026, 9, 12, 14, 2, 0)
#  (경과분, 글자수, typed, deleted, pasted, undo)
#  중간에 12분짜리 공백을 일부러 넣었다 - "공백 구간" 지표가 보이게
s1_steps = [
    (0,    0,    0,   0,  0, 0),
    (0.5,  212,  212, 0,  0, 0),
    (1,    180,  14,  46, 0, 3),
    (1.5,  340,  160, 0,  0, 0),
    (2,    295,  8,   53, 0, 2),
    (14,   470,  175, 0,  0, 0),   # <- 12분 자리 비움
    (14.5, 455,  22,  37, 0, 1),
    (15,   610,  155, 0,  0, 0),
    (15.5, 660,  50,  0,  0, 0),
]

# 세션 2 - 붙여넣고 끝. 한 번에 튀고 그 뒤로 평평하다
s2_start = datetime(2026, 9, 12, 16, 40, 0)
s2_steps = [
    (0,   0,    0,  0, 0,   0),
    (0.5, 0,    0,  0, 0,   0),
    (1,   980,  0,  0, 980, 0),
    (1.5, 980,  0,  0, 0,   0),
    (2,   1012, 32, 0, 0,   0),
    (2.5, 1012, 0,  0, 0,   0),
]


# ---------------------------------------------
# 실행
# ---------------------------------------------
reset = "--reset" in sys.argv

data = load_chain()          # 파일이 없거나 망가져 있으면 빈 체인을 돌려준다
before = data.get("sessions", [])

if reset:
    # --- 지우기 전에 확인을 받는다 ---
    print(f"현재 세션 {len(before)}개가 들어 있습니다:")
    for s in before:
        print(f"  - {s['session_id']} ({s.get('label', '')}) 스냅샷 {len(s['snapshots'])}개")
    print()
    print("--reset 은 이 기록을 전부 지웁니다. 에디터로 직접 쓴 기록은 되살릴 수 없습니다.")
    answer = input("정말 지우려면 yes 를 입력하세요: ").strip()
    if answer != "yes":
        print("취소했습니다. 아무것도 바꾸지 않았습니다.")
        sys.exit(0)

    # 그래도 혹시 모르니 사본을 남긴다
    if os.path.exists(CHAIN_PATH):
        backup = CHAIN_PATH.replace(".json", ".backup.json")
        shutil.copy(CHAIN_PATH, backup)
        print("사본을 남겼습니다 ->", backup)

    data = {"sessions": []}

# 이미 쓰이고 있는 id 를 모아둔다
taken = {s["session_id"] for s in data["sessions"]}

new_sessions = [
    build_session(unique_id("s1", taken), "직접 작성", s1_start, s1_steps),
]
taken.add(new_sessions[0]["session_id"])
new_sessions.append(
    build_session(unique_id("s2", taken), "붙여넣기 위주", s2_start, s2_steps)
)

data["sessions"].extend(new_sessions)

os.makedirs(os.path.dirname(CHAIN_PATH), exist_ok=True)
with open(CHAIN_PATH, "w", encoding="utf-8") as f:
    # ensure_ascii=False : 한글이 서울 로 깨지지 않게
    json.dump(data, f, ensure_ascii=False, indent=2)

print()
print(("전부 새로 만들었습니다 ->" if reset else "덧붙였습니다 ->"), CHAIN_PATH)
for s in new_sessions:
    print(f"  + {s['session_id']} ({s['label']}) 스냅샷 {len(s['snapshots'])}개")
print(f"  체인의 세션은 모두 {len(data['sessions'])}개가 되었습니다.")
