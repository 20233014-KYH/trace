# =============================================
# Trace - 창작 과정 증명 서비스
# 3단계 : 에디터에서 보낸 스냅샷을 체인에 쌓는다
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


# ---------------------------------------------
# 파일 읽기 / 쓰기
# ---------------------------------------------
def load_chain():
    if not os.path.exists(CHAIN_PATH):
        return {"sessions": []}
    try:
        with open(CHAIN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # 파일이 망가졌을 때 서버가 죽지 않게 한다
        return {"sessions": [], "error": "chain.json 을 읽을 수 없습니다"}


def save_chain(data):
    os.makedirs(os.path.dirname(CHAIN_PATH), exist_ok=True)
    with open(CHAIN_PATH, "w", encoding="utf-8") as f:
        # ensure_ascii=False : 한글이 서울 로 깨지지 않게
        json.dump(data, f, ensure_ascii=False, indent=2)


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

    session_id = body.get("session_id")
    text = body.get("content", "")
    events = body.get("events", {})

    # --- 입력 검증 (빈 입력 오류 케이스) ---
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

    # 이 세션을 찾는다. 없으면 새로 만든다.
    session = next(
        (s for s in data["sessions"] if s["session_id"] == session_id), None
    )
    now = datetime.now().isoformat(timespec="seconds")

    if session is None:
        session = {
            "session_id": session_id,
            "label": body.get("label", "새 세션"),
            "started_at": now,
            "snapshots": [],
        }
        data["sessions"].append(session)

    # 이전 해시를 가져온다. 첫 스냅샷이면 GENESIS.
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
        "seq": session["snapshots"][-1]["seq"],
        "hash": h,
        "total": len(session["snapshots"]),
    })


# 유휴 판정 기준. 스냅샷 간격이 이보다 길면 "자리를 비웠다"고 본다.
IDLE_THRESHOLD = 180   # 초 (3분)


def summarize(session):
    """스냅샷 배열에서 기획안 6.1의 지표를 계산한다.

    프런트가 아니라 서버가 계산한다.
    판단 재료를 만드는 것은 백엔드의 일이고,
    화면은 받은 것을 그리기만 한다.
    """
    snaps = session["snapshots"]
    if not snaps:
        return {
            "snapshot_count": 0, "final_chars": 0,
            "active_sec": 0, "idle_sec": 0, "elapsed_sec": 0,
            "typed": 0, "deleted": 0, "pasted": 0, "undo": 0,
            "paste_ratio": 0, "gaps": [],
        }

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


# ---------------------------------------------
# API : 체인을 돌려주고, 동시에 무결성을 검증한다
# ---------------------------------------------
@app.route("/api/verify")
def verify():
    data = load_chain()

    for session in data["sessions"]:
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

    # ----- 전체 요약 (검증자가 맨 위에서 읽을 한 줄) -----
    sessions = data["sessions"]
    all_times = [s["snapshots"][0]["time"] for s in sessions if s["snapshots"]]

    data["overall"] = {
        "valid": all(s["valid"] for s in sessions) if sessions else True,
        "session_count": len(sessions),
        "active_sec": sum(s["summary"]["active_sec"] for s in sessions),
        "idle_sec": sum(s["summary"]["idle_sec"] for s in sessions),
        "typed": sum(s["summary"]["typed"] for s in sessions),
        "pasted": sum(s["summary"]["pasted"] for s in sessions),
        "undo": sum(s["summary"]["undo"] for s in sessions),
        "gap_count": sum(len(s["summary"]["gaps"]) for s in sessions),
        "first_at": min(all_times) if all_times else None,
        "last_at": max(s["snapshots"][-1]["time"] for s in sessions if s["snapshots"]) if all_times else None,
    }

    total_chars = sum(s["summary"]["final_chars"] for s in sessions)
    data["overall"]["paste_ratio"] = (
        round(data["overall"]["pasted"] / total_chars * 100) if total_chars else 0
    )

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
