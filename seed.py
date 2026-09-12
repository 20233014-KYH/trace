# =============================================
# 데모용 chain.json 생성기 (임시)
#   나중에 B(검증·기획)가 실제로 글을 써서 만든
#   진짜 데이터로 교체할 예정이다.
# 실행 : python seed.py
# =============================================

import json
import os
from datetime import datetime, timedelta

# app.py 에 있는 해시 함수를 그대로 가져다 쓴다.
# (같은 규칙으로 만들어야 검증이 통과한다)
from app import chain_hash, content_hash, CHAIN_PATH


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

data = {
    "sessions": [
        build_session("s1", "직접 작성", s1_start, s1_steps),
        build_session("s2", "붙여넣기 위주", s2_start, s2_steps),
    ]
}

os.makedirs(os.path.dirname(CHAIN_PATH), exist_ok=True)
with open(CHAIN_PATH, "w", encoding="utf-8") as f:
    # ensure_ascii=False : 한글이 서울 로 깨지지 않게
    json.dump(data, f, ensure_ascii=False, indent=2)

print("만들었습니다 ->", CHAIN_PATH)
for s in data["sessions"]:
    print(f"  {s['session_id']} ({s['label']}) 스냅샷 {len(s['snapshots'])}개")
