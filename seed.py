# =============================================
# 데모용 chain.json 생성기
#
# 실행 :
#   python seed.py            데모 작품 2개를 "추가"한다 (기존 기록은 그대로 둔다)
#   python seed.py --reset    전부 지우고 데모 2개만 남긴다 (지우기 전에 한 번 묻는다)
#
# 왜 "추가"가 기본인가:
#   에디터로 직접 쓴 기록은 다시 만들 수 없다.
#   실수로 한 번 실행해서 발표 데이터가 날아가는 일이 없어야 한다.
#
# 만드는 것 :
#   작품 1  "기록은 왜 증거가 되는가"  글 · 파일 1개 · 세션 2개
#   작품 2  "재이 커미션"              그림 · 파일 3개 · 세션 3개 + 뺀 파일 1개
#
# 이벤트 4종(typed / deleted / pasted / undo)은 글과 그림이 같이 쓴다.
# 그림에서는 이렇게 대응한다 :
#   typed = 그은 획,  deleted = 지운 획,  pasted = 밖에서 들어온 양,  undo = 되돌리기
# =============================================

import json
import os
import shutil
import sys
from datetime import datetime, timedelta

# app.py 에 있는 함수를 그대로 가져다 쓴다.
# (같은 규칙으로 만들어야 검증이 통과한다)
from app import chain_hash, content_hash, load_chain, CHAIN_PATH


def build_session(session_id, file_name, label, start, steps, excluded=False):
    """steps = [(경과분, 누적량, typed, deleted, pasted, undo), ...]"""
    snapshots = []
    prev = "0" * 64

    for seq, (minute, amount, typed, deleted, pasted, undo) in enumerate(steps):
        t = (start + timedelta(minutes=minute)).isoformat(timespec="seconds")

        # 누적량에 맞춰 가짜 본문을 만든다 (내용 자체는 저장하지 않는다)
        ch = content_hash("가" * amount + session_id)

        events = {"typed": typed, "deleted": deleted, "pasted": pasted, "undo": undo}
        h = chain_hash(prev, t, ch, events)

        snapshots.append({
            "seq": seq,
            "time": t,
            "chars": amount,
            "content_hash": ch,
            "events": events,
            "hash": h,
        })
        prev = h

    return {
        "session_id": session_id,
        "file_name": None if excluded else file_name,
        "label": label,
        "started_at": start.isoformat(timespec="seconds"),
        "excluded": excluded,
        "snapshots": snapshots,
    }


def unique_id(base, taken):
    """이미 쓰이고 있는 id 면 뒤에 번호를 붙여 겹치지 않게 한다.

    w1 이 있으면 w1-2, 그것도 있으면 w1-3 …
    같은 id 가 두 개면 어느 쪽 기록인지 구분할 수 없어진다.
    """
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


# ---------------------------------------------
# 데모 데이터를 만드는 재료
#
# 중요 : 캡처 간격은 IDLE_THRESHOLD(3분)보다 짧아야 "작업한 시간"으로 센다.
#        간격을 10분씩 벌려 놓으면 전부 "자리 비움"이 되어 작업 시간이 0이 된다.
#        실제 수집기도 30초~2분마다 한 장씩 남긴다.
# ---------------------------------------------
def wobble(seed):
    """같은 결과가 나오는 작은 난수. 곡선이 기계처럼 일정하지 않게 만든다."""
    x = seed
    while True:
        x = (x * 1103515245 + 12345) % 2147483648
        yield x / 2147483648


def make_steps(n, interval, per_step, seed,
               gaps=(), paste_at=None, paste_amount=0, undo_rate=0.0,
               start_amount=0):
    """steps = [(경과분, 누적량, typed, deleted, pasted, undo), ...] 를 만든다.

    start_amount 시작할 때 이미 있던 양. 같은 파일을 이어서 작업할 때 쓴다
    n            캡처 몇 장
    interval     캡처 간격(분)
    per_step     한 캡처 동안 평균 얼마나 늘어나는가
    gaps         [(몇 번째 캡처 앞에서, 몇 분 비웠나), ...]  공백 구간
    paste_at     몇 번째 캡처에서 밖에서 들어왔는가
    paste_amount 얼마나 들어왔는가
    undo_rate    캡처당 평균 되돌리기 횟수
    """
    r = wobble(seed)
    gap_at = dict(gaps)

    steps = []
    minute = 0.0
    amount = start_amount

    for i in range(n):
        if i in gap_at:
            minute += gap_at[i]          # 자리를 비운 만큼 시각을 건너뛴다
        elif i > 0:
            minute += interval

        typed = deleted = pasted = undo = 0

        if i == 0:
            pass                          # 첫 장은 빈 상태
        elif paste_at is not None and i == paste_at:
            pasted = paste_amount         # 밖에서 들어온 분량
            amount += paste_amount
        else:
            grow = int(per_step * (0.6 + next(r) * 0.8))
            if next(r) < 0.28:            # 가끔 줄어든다 - 고쳐 쓴 흔적
                deleted = int(grow * (0.4 + next(r) * 0.5))
                amount -= deleted
                typed = int(deleted * 0.3)
                amount += typed
            else:
                typed = grow
                amount += grow
            undo = int(undo_rate * (0.5 + next(r)))

        steps.append((round(minute, 2), max(0, amount), typed, deleted, pasted, undo))

    return steps


# 작품 1 - 글. 파일 하나짜리 작품.
#   직접 쓴 세션 : 30초마다, 중간에 12분 자리 비움
W1_S1 = make_steps(n=33, interval=0.5, per_step=44, seed=11,
                   gaps=[(18, 12)], undo_rate=0.4)
#   붙여넣고 편집한 세션 : 한 번에 튀고 그 뒤로 평평하다.
#   같은 파일을 이어서 쓰는 것이므로 앞 세션이 끝난 글자 수에서 시작한다.
W1_S2 = make_steps(n=9, interval=0.5, per_step=7, seed=22,
                   paste_at=3, paste_amount=980, undo_rate=0.1,
                   start_amount=W1_S1[-1][1])

# 작품 2 - 그림. 파일 세 개짜리 작품.
#   2분마다 화면 캡처. typed = 그은 획, pasted = 밖에서 들어온 것.
W2_ROUGH = make_steps(n=38, interval=2, per_step=45, seed=33,
                      gaps=[(21, 25)], paste_at=14, paste_amount=1,
                      undo_rate=1.6)
W2_LINE = make_steps(n=81, interval=2, per_step=52, seed=44,
                     gaps=[(38, 45)], undo_rate=2.1)
W2_COLOR = make_steps(n=127, interval=2, per_step=58, seed=55,
                      gaps=[(46, 30), (92, 55)], undo_rate=1.9)
#   작품에서 뺀 파일. 이름은 남기지 않고 "뺐다"는 사실만 남는다.
W2_DROPPED = make_steps(n=4, interval=2, per_step=60, seed=66)


def make_work1(work_id):
    return {
        "work_id": work_id,
        "title": "기록은 왜 증거가 되는가",
        "created_at": "2026-09-12T14:02:00",
        "files": [{"name": "초고.docx", "first_seen": "2026-09-12T14:02:00"}],
        "excluded": [],
        "sessions": [
            build_session(f"{work_id}-s1", "초고.docx", "직접 작성",
                          datetime(2026, 9, 12, 14, 2, 0), W1_S1),
            build_session(f"{work_id}-s2", "초고.docx", "붙여넣고 편집",
                          datetime(2026, 9, 12, 16, 40, 0), W1_S2),
        ],
    }


def make_work2(work_id):
    return {
        "work_id": work_id,
        "title": "재이 커미션",
        "created_at": "2026-09-13T11:20:00",
        "files": [
            {"name": "러프.procreate", "first_seen": "2026-09-13T11:20:00"},
            {"name": "선화.procreate", "first_seen": "2026-09-13T16:10:00"},
            {"name": "채색.procreate", "first_seen": "2026-09-14T10:00:00"},
        ],
        # 파일 1개를 뺐다는 사실. 이름은 적지 않는다.
        "excluded": [{"at": "2026-09-14T18:32:00"}],
        "sessions": [
            build_session(f"{work_id}-s1", "러프.procreate", "러프",
                          datetime(2026, 9, 13, 11, 20, 0), W2_ROUGH),
            build_session(f"{work_id}-s2", "선화.procreate", "선화",
                          datetime(2026, 9, 13, 16, 10, 0), W2_LINE),
            build_session(f"{work_id}-s3", "채색.procreate", "채색",
                          datetime(2026, 9, 14, 10, 0, 0), W2_COLOR),
            build_session(f"{work_id}-s4", "참고_포즈모음.psd", "뺀 파일",
                          datetime(2026, 9, 13, 13, 5, 0), W2_DROPPED, excluded=True),
        ],
    }


# ---------------------------------------------
# 실행
# ---------------------------------------------
reset = "--reset" in sys.argv

data = load_chain()          # 파일이 없거나 망가져 있으면 빈 체인을 돌려준다
before = data.get("works", [])

if reset:
    # --- 지우기 전에 확인을 받는다 ---
    print(f"현재 작품 {len(before)}개가 들어 있습니다:")
    for w in before:
        print(f"  - {w['work_id']} ({w.get('title', '')}) "
              f"파일 {len(w.get('files', []))}개 · 세션 {len(w.get('sessions', []))}개")
    print()
    print("--reset 은 이 기록을 전부 지웁니다. 직접 만든 기록은 되살릴 수 없습니다.")
    answer = input("정말 지우려면 yes 를 입력하세요: ").strip()
    if answer != "yes":
        print("취소했습니다. 아무것도 바꾸지 않았습니다.")
        sys.exit(0)

    # 그래도 혹시 모르니 사본을 남긴다
    if os.path.exists(CHAIN_PATH):
        backup = CHAIN_PATH.replace(".json", ".backup.json")
        shutil.copy(CHAIN_PATH, backup)
        print("사본을 남겼습니다 ->", backup)

    data = {"works": []}

taken = {w["work_id"] for w in data["works"]}

w1_id = unique_id("w1", taken); taken.add(w1_id)
w2_id = unique_id("w2", taken); taken.add(w2_id)

new_works = [make_work1(w1_id), make_work2(w2_id)]
data["works"].extend(new_works)

os.makedirs(os.path.dirname(CHAIN_PATH), exist_ok=True)
with open(CHAIN_PATH, "w", encoding="utf-8") as f:
    # ensure_ascii=False : 한글이 서울 로 깨지지 않게
    json.dump(data, f, ensure_ascii=False, indent=2)

print()
print(("전부 새로 만들었습니다 ->" if reset else "덧붙였습니다 ->"), CHAIN_PATH)
for w in new_works:
    live = [s for s in w["sessions"] if not s["excluded"]]
    print(f"  + {w['work_id']} ({w['title']}) "
          f"파일 {len(w['files'])}개 · 세션 {len(live)}개"
          + (f" · 뺀 파일 {len(w['excluded'])}개" if w["excluded"] else ""))
print(f"  체인의 작품은 모두 {len(data['works'])}개가 되었습니다.")
