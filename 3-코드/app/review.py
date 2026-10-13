"""
review.py — 돌아보기 (캔버스 곁가지 · 돌아보기 v2 · 10/13 박상진)

  /review?period=week|month|term     나만 보는 화면 · 내역서 · 공유 링크에 안 들어감 · 점수 · 등급 · 퍼센트 없음

  ① 내 기록에서 찾은 것 (최대 3) — 사실(내 기록 숫자) → 해 볼 것 → 내 질문 예. 찾는 법은 규칙 (AI 안 씀):
     · followup  한 번 묻고 끝낸 대화가 많음 — 대화(도구 · 대화 이름)마다 질문 수
     · copied    AI 답과 같은 문장이 결과물에 그대로 남음 — 출처 보기와 같은 분석 (과제 파일을 연 과제만)
     · review    다 쓴 글을 검토 맡긴 적이 적음 — 쓰임새(export.쓰임) 고치기·검토 < 작성
  ② 다음 과제 목표 — ① 에서 "목표로 담기" · 담은 뒤 기록한 과제에서 같은 숫자를 다시 셈 (data/goals.json · 이 PC 에만)
  ③ 어떻게 썼나 · 주별 — 쓰임새 세 칸 개수
"""
import json
import os
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, send_from_directory

import source as S
import export as EX
from core import match as M

HERE = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint("review", __name__)
TIPS = {
    "followup": ("답을 받으면 한 번 더 묻기", "이어서 물은 질문"),
    "copied": ("옮긴 문장은 내 말로", "AI 답과 같은 문장"),
    "review": ("다 쓴 글은 검토를 맡기기", "고치기·검토 질문"),
}
되묻기 = ("왜", "그럼", "근거", "어떻게", "예를 들", "다시", "더 ", "맞아?", "맞나", "차이")


@bp.get("/review")
def page():
    return send_from_directory(HERE, "review.html")


def _시작(period, now):
    if period == "week":
        d = now - timedelta(days=now.weekday())
        return d.replace(hour=0, minute=0, second=0, microsecond=0), "이번 주"
    if period == "term":                                  # 2학기 9/1 · 1학기 3/1 (1·2월은 지난 2학기)
        y, m = now.year, now.month
        s = datetime(y, 3, 1, tzinfo=now.tzinfo) if 3 <= m <= 8 else datetime(y if m >= 9 else y - 1, 9, 1, tzinfo=now.tzinfo)
        return s, f"{'1' if 3 <= m <= 8 else '2'}학기"
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), f"{now.month}월"


def _질문들(works, 시작=""):
    """내 과제들의 질문 [{wid, title, text, tool, conv, turn, ts, usage}] (기록 켜기 전 대화 · 잘린 답 뺌)"""
    세션 = S._기록["sessions"]()
    과제 = {sid: wid for wid in works for sid in 세션.get(wid, ())}
    msgs = [m for m in S._기록["jsonl"]("ai-messages-*.jsonl") if m.get("session_id") in 과제]
    out = []
    for m in M.latest_messages(msgs):
        if m.get("role") != "question" or m.get("history") or m.get("ts", "") < 시작:
            continue
        wid = 과제[m["session_id"]]
        out.append({"wid": wid, "title": works[wid], "text": m.get("text", ""), "tool": m.get("tool") or "AI",
                    "conv": m.get("conv") or m["session_id"], "turn": m.get("turn") or 0, "ts": m.get("ts", ""), "usage": EX.쓰임(m.get("text", ""))})
    return sorted(out, key=lambda q: (q["ts"], q["turn"]))


def _대화(qs):
    """(과제, 도구, 대화) → 질문들 (순서대로) — 둘째 질문부터가 '이어서 물은 질문'"""
    out = {}
    for q in qs:
        out.setdefault((q["wid"], q["tool"], q["conv"]), []).append(q)
    return out


def _같은_문장(wids):
    """과제마다 AI 답과 같은 문장 수 (출처 보기의 일치 · 유사) — 과제 파일을 연 과제만 · {wid: n}"""
    out = {}
    for wid in wids:
        try:
            r = EX._모으기(wid) if S.문서_준비(wid) else None
        except Exception:
            r = None
        if isinstance(r, dict):
            out[wid] = r["result_counts"]["ai"]
    return out


def _목표_경로():
    return os.path.join(S._기록["data_dir"](), "goals.json")


def _목표():
    try:
        g = json.load(open(_목표_경로(), encoding="utf-8"))
        return [x for x in g if isinstance(x, dict) and x.get("key") in TIPS]
    except (OSError, ValueError):
        return []


def _목표_쓰기(g):
    os.makedirs(S._기록["data_dir"](), exist_ok=True)
    json.dump(g, open(_목표_경로(), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _셈(key, qs, 같은):
    """목표 하나의 숫자 — followup 이어서 물은 질문 · copied AI 답과 같은 문장 · review 고치기·검토 질문"""
    if key == "followup":
        return sum(len(v) - 1 for v in _대화(qs).values())
    if key == "copied":
        return sum(같은.get(w, 0) for w in {q["wid"] for q in qs})
    return sum(1 for q in qs if q["usage"] == "fix")


@bp.get("/local/review")
def data():
    a = S._기록["auth"]()
    if not a.get("token"):
        return jsonify(error="login", message="로그인이 필요합니다"), 401
    코드, me = S._기록["server"]("GET", "/me")
    if 코드 == 401:
        return jsonify(error="login", message="다시 로그인해 주세요"), 401
    works = {w["id"]: w.get("title") or w["id"] for w in (me.get("works", []) if 코드 == 200 else [])}
    period = request.args.get("period", "month")
    now = datetime.now().astimezone()
    시작, 이름 = _시작(period, now)
    모든질문 = _질문들(works)
    qs = [q for q in 모든질문 if q["ts"] >= 시작.isoformat(timespec="seconds")]
    대화 = _대화(qs)
    한번 = [v for v in 대화.values() if len(v) == 1]
    이어 = [q for v in 대화.values() for q in v[1:]]
    쓰임 = {k: sum(1 for q in qs if q["usage"] == k) for k in ("learn", "fix", "write")}
    과제들 = sorted({q["wid"] for q in qs})
    같은 = _같은_문장(과제들)

    tips = []
    if len(대화) >= 2 and len(한번) * 2 > len(대화):              # 대화의 절반 넘게 한 번 묻고 끝
        좋은 = [q for q in reversed(이어) if any(w in q["text"] for w in 되묻기)] or list(reversed(이어))
        tips.append({"key": "followup", "title": "한 번 묻고 끝낸 대화가 많아요",
                     "fact": f"대화 {len(대화)}개 중 {len(한번)}개는 질문 하나로 끝났어요 · 이어서 물은 질문은 {len(이어)}개",
                     "todo": "답을 받으면 \"왜 그런지\" \"근거가 뭔지\" 한 번 더 물어 보세요. 이해한 것이 내 글에 남아요",
                     "example": {"text": 좋은[0]["text"][:120], "where": f"{좋은[0]['title']} · 이어서 물은 예"} if 좋은 else None})
    if 같은 and max(같은.values()) > 0:
        w = max(같은, key=같은.get)
        tips.append({"key": "copied", "title": "AI 답과 같은 문장이 그대로 남았어요",
                     "fact": f"{works.get(w, w)} 에서 {같은[w]}문장" + (f" · 다른 과제까지 {sum(같은.values())}문장" if len([x for x in 같은.values() if x]) > 1 else ""),
                     "todo": "옮긴 문장은 내 말로 바꾸거나, 그대로 둘 거면 내역서에 쓴 이유를 적어 두세요",
                     "link": f"/source?work={w}"})
    if 쓰임["write"] and 쓰임["fix"] < 쓰임["write"]:
        tips.append({"key": "review", "title": "다 쓴 글을 검토 맡긴 적은 적어요",
                     "fact": f"고치기·검토 질문 {쓰임['fix']}개 · 작성 질문 {쓰임['write']}개",
                     "todo": "먼저 직접 쓰고 \"내 논리에서 빈 곳을 찾아줘\" 처럼 검토를 맡기면, 글은 내 것으로 남고 AI 는 확인만 해요"})

    # 다음 과제 목표 — 담은 뒤 처음 기록한 과제부터 셈 (전 숫자 → 지금 숫자)
    첫기록 = {}
    for e in S._기록["jsonl"]("events-*.jsonl"):
        if e.get("type") == "session_start" and e.get("work_id") in works:
            첫기록[e["work_id"]] = min(첫기록.get(e["work_id"], "9"), e.get("ts", ""))
    goals = []
    for g in _목표():                   # 담기 바로 전 과제 하나 → 담은 뒤 가장 최근 과제 하나 (과제마다 같은 숫자)
        전 = max((w for w, t in 첫기록.items() if t < g.get("added_at", "")), key=첫기록.get, default=None)
        뒤 = max((w for w, t in 첫기록.items() if t >= g.get("added_at", "")), key=첫기록.get, default=None)
        한과제 = lambda w: _셈(g["key"], [q for q in 모든질문 if q["wid"] == w], _같은_문장([w]) if g["key"] == "copied" else {}) if w else None
        goals.append({**g, "text": TIPS[g["key"]][0], "label": TIPS[g["key"]][1], "before": 한과제(전),
                      "after": 한과제(뒤), "after_title": works.get(뒤) if 뒤 else None})

    # 주별 — 이 기간을 주(월요일 시작)로 · 최대 6주
    주 = {}
    for q in qs:
        d = datetime.fromisoformat(q["ts"])
        월 = (d - timedelta(days=d.weekday())).date()
        주.setdefault(월, {"learn": 0, "fix": 0, "write": 0})[q["usage"]] += 1
    weeks = [{"label": f"{k.month}/{k.day}주", **v} for k, v in sorted(주.items())][-6:]
    return jsonify(period=period, name=이름, works=len(과제들), questions=len(qs), usage=쓰임,
                   tips=tips[:3], goals=goals, weeks=weeks, has_goal=[g["key"] for g in goals])


@bp.post("/local/review/goal")
def goal():
    """json: {key, action: add | done | undo | remove} — 다음 과제 목표 (이 PC 에만)"""
    b = request.get_json(force=True, silent=True) or {}
    key, act = b.get("key"), b.get("action")
    if key not in TIPS or act not in ("add", "done", "undo", "remove"):
        return jsonify(error="bad_request", message="목표가 올바르지 않아요"), 400
    g = [x for x in _목표() if x["key"] != key or act != "remove"]
    지금 = datetime.now().astimezone().isoformat(timespec="seconds")
    have = next((x for x in g if x["key"] == key), None)
    if act == "add" and not have:
        g.append({"key": key, "added_at": 지금, "done": False})
    elif have and act in ("done", "undo"):
        have["done"] = act == "done"
    _목표_쓰기(g)
    return jsonify(goals=g)
