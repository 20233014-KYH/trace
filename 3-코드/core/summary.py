"""
summary.py — 과제 하나의 요약 숫자 (AI 활용 내역서 맨 위 · docs/api.md 10-5 GET /works/{id}/summary)

  work_summary([(세션정보, 이벤트들), ...]) → dict

★ 서버가 체인 이벤트로 직접 센다 ★
  PC 가 "AI 에 12번 물었다" 고 보낸 숫자를 믿지 않는다. 서버에 쌓인 이벤트(봉인으로 검증된 체인)를 센다.
  세션 하나의 숫자는 derive.py(박상진)를 그대로 쓰고, 여기서는 세션을 합치고 ai_msg·자리 비움만 더 센다.

★ 판정하지 않는다 (기획 원칙 1) ★
  퍼센트·비율·점수를 내지 않는다. 횟수·글자 수·분·시각만. (derive 의 typed_pct 같은 비율도 옮기지 않는다)
  출처를 모르는 붙여넣기는 "직접 씀"이 아니라 "출처 기록 없음"으로 센다 (원칙 2).
"""
from collections import Counter
from datetime import datetime

from core.derive import derive


def _분(초):
    return round(초 / 60, 1)


def _자리비움_초(evs):
    """idle_start → 다음 idle_end (없으면 세션 끝) 사이. 기록기는 5분 무입력이면 idle_start 를 낸다."""
    초, 시작 = 0.0, None
    for e in evs:
        if e["type"] == "idle_start" and 시작 is None:
            시작 = datetime.fromisoformat(e["ts"])
        elif e["type"] == "idle_end" and 시작 is not None:
            초 += (datetime.fromisoformat(e["ts"]) - 시작).total_seconds()
            시작 = None
    if 시작 is not None and evs:
        초 += (datetime.fromisoformat(evs[-1]["ts"]) - 시작).total_seconds()
    return 초


def session_summary(sid, evs):
    """세션 하나. evs = 받은 순서의 이벤트 (heartbeat 없음 · 서버에 저장된 그대로)."""
    evs = [{"session_id": sid, **e} for e in evs]            # derive 가 session_id 를 읽는다
    d = derive(evs)
    st = d["stats"]
    t0, t1 = datetime.fromisoformat(evs[0]["ts"]), datetime.fromisoformat(evs[-1]["ts"])
    ai = [e for e in evs if e["type"] == "ai_msg"]
    링크 = [e for e in evs if e["type"] == "link_decision"]
    return {
        "id": sid, "start": evs[0]["ts"], "end": evs[-1]["ts"],
        "minutes": _분((t1 - t0).total_seconds()),
        "idle_minutes": _분(_자리비움_초(evs)),
        "typed": st["typed"], "deleted": st["deleted"], "undo": st["undo"],
        "pastes": {"count": st["paste_count"], "chars": st["pasted"],
                   "from_ai_count": st["paste_ai_count"], "from_ai_chars": st["pasted_ai"],
                   # 같은 해시의 복사가 기록에 없음 = 어디서 왔는지 모름 (휴대폰·다른 PC·기록 전 복사)
                   "unknown_count": sum(1 for p in d["pastes"] if not p["matched"]),
                   "unknown_chars": sum(p["len"] for p in d["pastes"] if not p["matched"])},
        "ai": {"questions": sum(e.get("role") == "question" for e in ai),
               "answers": sum(e.get("role") == "answer" for e in ai),
               "history": sum(bool(e.get("history")) for e in ai),          # 이전 대화 — 받은 시각 모름
               "tools": dict(Counter(e.get("tool") or "?" for e in ai)),
               "window_minutes": st["ai_min"], "window_visits": st["ai_visits"]},
        "links": {"confirmed": sum(e.get("decision") == "confirmed" for e in 링크),
                  "rejected": sum(e.get("decision") == "rejected" for e in 링크)},
        "events": st["events"],
    }


def work_summary(sessions):
    """sessions = [({"id", "sealed", "verified"}, 이벤트들), ...] → 과제 요약. 이벤트가 없는 세션은 건너뛴다."""
    각 = []
    for 정보, evs in sessions:
        if not evs:
            continue
        s = session_summary(정보["id"], evs)
        s["sealed"], s["verified"] = bool(정보.get("sealed")), bool(정보.get("verified"))
        각.append(s)
    각.sort(key=lambda s: s["start"])

    def 합(*키):
        def 값(s):
            for k in 키:
                s = s[k]
            return s
        return sum(값(s) for s in 각)

    도구 = Counter()
    for s in 각:
        도구.update(s["ai"]["tools"])
    return {
        "sessions": len(각),
        "sealed_verified": sum(s["sealed"] and s["verified"] for s in 각),
        "first_at": 각[0]["start"] if 각 else None,
        "last_at": 각[-1]["end"] if 각 else None,
        "minutes": round(합("minutes"), 1),
        "idle_minutes": round(합("idle_minutes"), 1),
        "typed": 합("typed"), "deleted": 합("deleted"), "undo": 합("undo"),
        "pastes": {k: 합("pastes", k) for k in ("count", "chars", "from_ai_count", "from_ai_chars",
                                                 "unknown_count", "unknown_chars")},
        "ai": {"questions": 합("ai", "questions"), "answers": 합("ai", "answers"),
               "history": 합("ai", "history"), "tools": dict(도구),
               "window_minutes": round(합("ai", "window_minutes"), 1), "window_visits": 합("ai", "window_visits")},
        "links": {"confirmed": 합("links", "confirmed"), "rejected": 합("links", "rejected")},
        "by_session": 각,
    }
