# =============================================
# Trace - 창작 과정 증명 서비스
#
# 데이터 구조 :  작품 > 파일 > 세션 > 스냅샷
#
#   작품   창작물 하나. 증명서는 여기에 한 장 나온다.
#   파일   그 작품을 만들며 건드린 파일들 (러프 / 선화 / 채색 …)
#   세션   한 번 앉아서 작업한 구간
#   스냅샷 30초마다 남긴 해시 한 줄
# =============================================

import json
import hashlib
import os
from datetime import datetime

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

CHAIN_PATH = os.path.join(os.path.dirname(__file__), "data", "chain.json")

# 체인의 출발점. 이전 해시가 없는 첫 스냅샷이 쓸 값
GENESIS = "0" * 64

# 유휴 판정 기준. 스냅샷 간격이 이보다 길면 "자리를 비웠다"고 본다.
IDLE_THRESHOLD = 180   # 초 (3분)


# ---------------------------------------------
# 해시 - 이 프로젝트의 심장
# ---------------------------------------------
def chain_hash(prev_hash, time_str, content_hash, events):
    """이전 해시 + 시각 + 내용해시 + 이벤트 를 이어붙여 SHA256 을 낸다.

    이전 해시를 재료에 넣기 때문에, 중간 스냅샷 하나만 바꿔도
    그 이후의 해시가 전부 어긋난다.
    """
    events_str = json.dumps(events, sort_keys=True)   # 순서 고정
    material = f"{prev_hash}|{time_str}|{content_hash}|{events_str}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def content_hash(text):
    """글 내용의 해시. 내용 원본은 서버에 저장하지 않는다."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def work_root(work):
    """작품 루트 해시.

    파일이 여러 개여도 작품 하나에는 값이 하나 나와야 한다.
    세션마다 체인이 따로 돌기 때문에, 각 세션의 마지막 해시를
    시간 순서대로 이어 붙여 한 번 더 해싱한다.

    증명서에 찍히고 외부 앵커(OpenTimestamps)에 고정되는 값이 이것이다.
    세션이 하나라도 바뀌면 이 값이 달라진다.
    """
    tails = [s["snapshots"][-1]["hash"] for s in work["sessions"] if s["snapshots"]]
    if not tails:
        return None
    return hashlib.sha256("|".join(tails).encode("utf-8")).hexdigest()


# ---------------------------------------------
# 파일 읽기 / 쓰기
# ---------------------------------------------
def blank_chain():
    return {"works": []}


def load_chain():
    if not os.path.exists(CHAIN_PATH):
        return blank_chain()
    try:
        with open(CHAIN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # 파일이 망가졌을 때 서버가 죽지 않게 한다
        return {"works": [], "error": "chain.json 을 읽을 수 없습니다"}

    # 작품 계층이 없던 예전 파일이면 작품 하나로 감싸 준다.
    # (예전에 만든 chain.json 이 그대로 열리게 하기 위한 것)
    if "works" not in data and "sessions" in data:
        old = data.get("sessions", [])
        # 예전 세션에는 파일 이름이 없다. 파일 하나에 다 들어 있던 것으로 본다.
        for s in old:
            s.setdefault("file_name", "(파일 이름이 없던 기록)")
            s.setdefault("excluded", False)
        data = {"works": [{
            "work_id": "w-legacy",
            "title": "이전 기록",
            "created_at": old[0]["started_at"] if old else "",
            "files": ([{"name": "(파일 이름이 없던 기록)",
                        "first_seen": old[0]["started_at"]}] if old else []),
            "excluded": [],
            "sessions": old,
        }]}

    data.setdefault("works", [])
    return data


def save_chain(data):
    os.makedirs(os.path.dirname(CHAIN_PATH), exist_ok=True)
    with open(CHAIN_PATH, "w", encoding="utf-8") as f:
        # ensure_ascii=False : 한글이 서울 로 깨지지 않게
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_work(data, work_id):
    return next((w for w in data["works"] if w["work_id"] == work_id), None)


# ---------------------------------------------
# 화면
# ---------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------
# API : 스냅샷 1건을 체인에 추가한다
# ---------------------------------------------
@app.route("/api/snapshot", methods=["POST"])
def snapshot():
    body = request.get_json()

    work_id    = body.get("work_id")
    work_title = body.get("work_title", "이름 없는 작품")
    file_name  = body.get("file_name", "이름 없는 파일")
    session_id = body.get("session_id")
    text       = body.get("content", "")
    events     = body.get("events", {})

    # --- 입력 검증 (빈 입력 오류 케이스) ---
    if not work_id:
        return jsonify({"error": "작품 ID가 없습니다"}), 400
    if not session_id:
        return jsonify({"error": "세션 ID가 없습니다"}), 400
    if text.strip() == "":
        return jsonify({"error": "내용이 비어 있습니다"}), 400

    # 이벤트 4종을 빠짐없이 채운다 (없으면 0)
    events = {
        "typed":   int(events.get("typed", 0)),
        "deleted": int(events.get("deleted", 0)),
        "pasted":  int(events.get("pasted", 0)),
        "undo":    int(events.get("undo", 0)),
    }

    data = load_chain()
    now = datetime.now().isoformat(timespec="seconds")

    # 1) 작품을 찾는다. 없으면 새로 만든다.
    work = find_work(data, work_id)
    if work is None:
        work = {
            "work_id": work_id,
            "title": work_title,
            "created_at": now,
            "files": [],
            "excluded": [],     # 뺀 파일의 "사실"만 쌓인다. 이름은 적지 않는다.
            "sessions": [],
        }
        data["works"].append(work)

    # 2) 이 파일을 작품의 파일 목록에 올린다.
    #    작업 중에는 사용자에게 묻지 않는다. 종료할 때 한 번에 확인한다.
    if file_name not in [f["name"] for f in work["files"]]:
        work["files"].append({"name": file_name, "first_seen": now})

    # 3) 세션을 찾는다. 없으면 새로 만든다.
    session = next(
        (s for s in work["sessions"] if s["session_id"] == session_id), None
    )
    if session is None:
        session = {
            "session_id": session_id,
            "file_name": file_name,
            "label": body.get("label", "새 세션"),
            "started_at": now,
            "excluded": False,
            "snapshots": [],
        }
        work["sessions"].append(session)

    # 4) 이전 해시를 가져온다. 첫 스냅샷이면 GENESIS.
    prev = session["snapshots"][-1]["hash"] if session["snapshots"] else GENESIS

    ch = content_hash(text)
    h = chain_hash(prev, now, ch, events)

    session["snapshots"].append({
        "seq": len(session["snapshots"]),
        "time": now,
        "chars": len(text),
        "content_hash": ch,     # 내용이 아니라 해시만 남긴다
        "events": events,
        "hash": h,
    })

    save_chain(data)

    return jsonify({
        "ok": True,
        "work_id": work_id,
        "seq": session["snapshots"][-1]["seq"],
        "hash": h,
        "total": len(session["snapshots"]),
        "root_hash": work_root(work),
    })


# ---------------------------------------------
# API : 파일을 작품에서 뺀다
#
# 이름도 내용도 남기지 않는다. 다만 "뺐다"는 사실과 시각은 남는다.
# 공백 구간을 지우지 않고 빗금으로 남기는 것과 같은 원칙이다.
# ---------------------------------------------
@app.route("/api/exclude", methods=["POST"])
def exclude():
    body = request.get_json()
    work_id   = body.get("work_id")
    file_name = body.get("file_name")

    if not work_id or not file_name:
        return jsonify({"error": "작품 ID 와 파일 이름이 필요합니다"}), 400

    data = load_chain()
    work = find_work(data, work_id)
    if work is None:
        return jsonify({"error": "그런 작품이 없습니다"}), 404

    now = datetime.now().isoformat(timespec="seconds")

    # 파일 목록에서 이름을 지운다
    before = len(work["files"])
    work["files"] = [f for f in work["files"] if f["name"] != file_name]
    if len(work["files"]) == before:
        return jsonify({"error": "그런 파일이 없습니다"}), 404

    # 그 파일의 세션에 표시를 남긴다. 체인은 그대로 두고 이름만 지운다.
    for s in work["sessions"]:
        if s.get("file_name") == file_name:
            s["excluded"] = True
            s["file_name"] = None

    # 뺐다는 사실만 기록한다
    work["excluded"].append({"at": now})

    save_chain(data)
    return jsonify({"ok": True, "excluded_count": len(work["excluded"])})


# ---------------------------------------------
# 지표 계산 - 전부 서버가 한다
# ---------------------------------------------
def blank_summary():
    return {
        "snapshot_count": 0, "final_chars": 0,
        "active_sec": 0, "idle_sec": 0, "elapsed_sec": 0,
        "typed": 0, "deleted": 0, "pasted": 0, "undo": 0,
        "paste_ratio": 0, "gaps": [],
    }


def summarize(session):
    """스냅샷 배열에서 기획안 6.1의 지표를 계산한다.

    프런트가 아니라 서버가 계산한다.
    판단 재료를 만드는 것은 백엔드의 일이고,
    화면은 받은 것을 그리기만 한다.
    """
    snaps = session["snapshots"]
    if not snaps:
        return blank_summary()

    times = [datetime.fromisoformat(s["time"]) for s in snaps]

    active_sec = 0      # 실제로 작업한 시간
    idle_sec = 0        # 비어 있던 시간
    gaps = []           # 공백 구간 목록 (숨기지 않고 표시한다)

    for i in range(1, len(times)):
        gap = (times[i] - times[i - 1]).total_seconds()
        if gap > IDLE_THRESHOLD:
            idle_sec += gap
            gaps.append({
                "from": snaps[i - 1]["time"],
                "to": snaps[i]["time"],
                "seconds": int(gap),
                "at_seq": snaps[i]["seq"],
            })
        else:
            active_sec += gap

    total = lambda k: sum(s["events"][k] for s in snaps)
    pasted = total("pasted")
    final_chars = snaps[-1]["chars"]

    return {
        "snapshot_count": len(snaps),
        "final_chars": final_chars,
        "active_sec": int(active_sec),
        "idle_sec": int(idle_sec),
        "elapsed_sec": int((times[-1] - times[0]).total_seconds()),
        "typed": total("typed"),
        "deleted": total("deleted"),
        "pasted": pasted,
        "undo": total("undo"),
        "paste_ratio": round(pasted / final_chars * 100) if final_chars else 0,
        "gaps": gaps,
    }


def summarize_work(work, files_summary):
    """작품 하나의 합계. 뺀 세션은 숫자에서 제외한다.

    분량(final_chars)은 세션끼리 더하면 안 된다. 같은 파일을 두 번에 나눠
    작업했으면 두 번째 세션의 마지막 값이 그 파일의 분량이고, 첫 세션 값을
    거기에 더하면 같은 글자를 두 번 세는 셈이 된다.
    그래서 파일별 최종값(files_summary)을 더한다.
    """
    live = [s for s in work["sessions"] if not s.get("excluded")]
    sums = [s["summary"] for s in live]

    starts = [s["snapshots"][0]["time"] for s in live if s["snapshots"]]
    ends   = [s["snapshots"][-1]["time"] for s in live if s["snapshots"]]

    final_chars = sum(f["final_chars"] for f in files_summary)
    pasted = sum(x["pasted"] for x in sums)

    return {
        "session_count": len(live),
        "file_count": len(work["files"]),
        "excluded_count": len(work.get("excluded", [])),
        "active_sec": sum(x["active_sec"] for x in sums),
        "idle_sec": sum(x["idle_sec"] for x in sums),
        "typed": sum(x["typed"] for x in sums),
        "deleted": sum(x["deleted"] for x in sums),
        "pasted": pasted,
        "undo": sum(x["undo"] for x in sums),
        "gap_count": sum(len(x["gaps"]) for x in sums),
        "snapshot_count": sum(x["snapshot_count"] for x in sums),
        "final_chars": final_chars,
        "paste_ratio": round(pasted / final_chars * 100) if final_chars else 0,
        "first_at": min(starts) if starts else None,
        "last_at": max(ends) if ends else None,
    }


def summarize_files(work):
    """파일별로 묶는다. 검증 화면의 '어느 파일을 언제 만졌는가' 띠가 쓰는 값."""
    rows = []
    for f in work["files"]:
        mine = [s for s in work["sessions"]
                if s.get("file_name") == f["name"] and not s.get("excluded")]
        # 이 파일의 분량은 "마지막 세션의 마지막 값" 이다 (세션끼리 더하지 않는다)
        with_snaps = [s for s in mine if s["snapshots"]]
        last = max(with_snaps, key=lambda s: s["snapshots"][-1]["time"]) if with_snaps else None
        rows.append({
            "name": f["name"],
            "final_chars": last["snapshots"][-1]["chars"] if last else 0,
            "session_count": len(mine),
            "active_sec": sum(s["summary"]["active_sec"] for s in mine),
            "snapshot_count": sum(s["summary"]["snapshot_count"] for s in mine),
            "pasted": sum(s["summary"]["pasted"] for s in mine),
            "first_at": min([s["snapshots"][0]["time"] for s in mine if s["snapshots"]], default=None),
            "last_at":  max([s["snapshots"][-1]["time"] for s in mine if s["snapshots"]], default=None),
        })
    return rows


# ---------------------------------------------
# API : 체인을 돌려주고, 동시에 무결성을 검증한다
# ---------------------------------------------
@app.route("/api/verify")
def verify():
    data = load_chain()

    for work in data["works"]:
        for session in work["sessions"]:
            prev = GENESIS
            broken_at = None

            for snap in session["snapshots"]:
                # 저장된 재료로 해시를 "다시" 계산한다
                expected = chain_hash(
                    prev, snap["time"], snap["content_hash"], snap["events"]
                )
                # 다시 계산한 값과 파일에 적힌 값이 다르면 = 누군가 고쳤다
                if expected != snap["hash"] and broken_at is None:
                    broken_at = snap["seq"]
                prev = snap["hash"]

            session["valid"] = broken_at is None
            session["broken_at"] = broken_at
            session["summary"] = summarize(session)

        # 작품 단위로 묶는다
        work["valid"] = all(s["valid"] for s in work["sessions"]) if work["sessions"] else True
        work["root_hash"] = work_root(work)
        work["files_summary"] = summarize_files(work)
        work["summary"] = summarize_work(work, work["files_summary"])

    # ----- 전체 요약 (검증자가 맨 위에서 읽을 한 줄) -----
    works = data["works"]
    firsts = [w["summary"]["first_at"] for w in works if w["summary"]["first_at"]]
    lasts  = [w["summary"]["last_at"]  for w in works if w["summary"]["last_at"]]
    total_chars = sum(w["summary"]["final_chars"] for w in works)
    pasted = sum(w["summary"]["pasted"] for w in works)

    data["overall"] = {
        "valid": all(w["valid"] for w in works) if works else True,
        "work_count": len(works),
        "file_count": sum(w["summary"]["file_count"] for w in works),
        "session_count": sum(w["summary"]["session_count"] for w in works),
        "active_sec": sum(w["summary"]["active_sec"] for w in works),
        "idle_sec": sum(w["summary"]["idle_sec"] for w in works),
        "typed": sum(w["summary"]["typed"] for w in works),
        "pasted": pasted,
        "undo": sum(w["summary"]["undo"] for w in works),
        "gap_count": sum(w["summary"]["gap_count"] for w in works),
        "excluded_count": sum(w["summary"]["excluded_count"] for w in works),
        "paste_ratio": round(pasted / total_chars * 100) if total_chars else 0,
        "first_at": min(firsts) if firsts else None,
        "last_at": max(lasts) if lasts else None,
    }

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
