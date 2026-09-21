"""
derive.py — 수집기 원본 이벤트(jsonl) → "한눈에" 화면 데이터(session.json)

  python core/derive.py data/events-2026-09-19.jsonl            # 가장 최근 세션 → data/session.json
  python core/derive.py data/events-*.jsonl --session s_2026-09-19_150002 --out out.json
  python core/derive.py data/events-*.jsonl --list                # 세션 목록만

출력 구조 = 목업북 <script id="DATA"> 의 session 과 동일. ui/viewer.html 이 그대로 읽는다.
  segments[] {s,e,cat,title}   분 단위 활성 창 구간
  typed[] deleted[]            분당 입력·삭제 횟수 (길이 = minutes)
  pastes[] {m,len,ai,after_typed}  붙여넣기. ai = 같은 해시가 AI 창(category=ai)에서 복사됐음
  undos[]                      되돌리기가 일어난 분
  chain[] [ts,type,summary,prev,hash]   해시 체인 (진짜 SHA-256)
  root                         마지막 해시 = 루트
  stats{}                      화면 상단 숫자들

판정하지 않는다: 여기엔 점수·등급·확률 계산이 없다. 횟수·길이·해시를 세고 묶을 뿐.
"""
import argparse
import glob
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime

GENESIS = "0" * 64


def load(paths):
    by = defaultdict(list)
    for pat in paths:
        for p in glob.glob(pat):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        ev = json.loads(line)
                        by[ev["session_id"]].append(ev)
    for evs in by.values():
        evs.sort(key=lambda e: e["ts"])
    return by


def ts(e):
    return datetime.fromisoformat(e["ts"])


def summary(e):
    """체인에 들어가는 한 줄 요약. 내용은 없다 — 앱·제목·횟수·길이·해시만."""
    t = e["type"]
    if t == "window":
        return f"{e.get('app','')} · {e.get('title','')}".rstrip(" ·")
    if t in ("copy", "paste"):
        return f"{e.get('len',0)}자 · {e.get('hash','')[:19]}… · {e.get('app','')}"
    if t == "keys":
        return f"입력 {e.get('count',0)}자 · 삭제 {e.get('deleted',0)}자 · {e.get('app','')}"
    if t == "file":
        return f"{e.get('action','')} · {e.get('path','')} · {(e.get('content_hash') or '')[:19]}"
    if t in ("undo", "redo", "cut"):
        return {"undo": "되돌리기 (Ctrl+Z)", "redo": "다시 실행 (Ctrl+Y)", "cut": "잘라내기 (Ctrl+X)"}[t]
    if t == "session_start":
        return "세션 시작"
    if t == "session_end":
        return "세션 종료"
    return ""


def build_chain(evs):
    """hᵢ = SHA256(hᵢ₋₁ ‖ ts ‖ type ‖ summary). heartbeat 는 체인에 안 넣는다(공백 계산용)."""
    prev, rows = GENESIS, []
    for e in evs:
        if e["type"] == "heartbeat":
            continue
        s = summary(e)
        h = hashlib.sha256(f"{prev}|{e['ts']}|{e['type']}|{s}".encode("utf-8")).hexdigest()
        rows.append([e["ts"][11:19], e["type"], s, prev, h])
        prev = h
    return rows, prev


def derive(evs):
    if not evs:
        return None
    t0 = ts(evs[0])
    t1 = ts(evs[-1])
    minutes = max(1, int((t1 - t0).total_seconds() // 60) + 1)
    mi = lambda e: min(minutes - 1, int((ts(e) - t0).total_seconds() // 60))

    typed = [0] * minutes
    deleted = [0] * minutes
    undos = []
    pastes = []
    segments = []
    copies = {}  # hash -> category of window where copied

    cur = None  # 현재 활성 창 (cat, title, start_min)
    for e in evs:
        t = e["type"]
        if t == "window":
            cat, title = e.get("category", "other"), e.get("title", "")
            m = mi(e)
            if cur and cur[0] == cat and cur[1] == title:
                continue
            if cur:
                segments.append({"s": cur[2], "e": max(cur[2] + 1, m), "cat": cur[0], "title": cur[1]})
            cur = (cat, title, m)
        elif t == "keys":
            typed[mi(e)] += e.get("count", 0)
            deleted[mi(e)] += e.get("deleted", 0)
        elif t == "undo":
            undos.append(mi(e))
        elif t == "copy":
            copies[e.get("hash")] = e.get("category", "other")
        elif t == "paste":
            h = e.get("hash")
            pastes.append({"m": mi(e), "len": e.get("len", 0), "ai": copies.get(h) == "ai",
                           "matched": h in copies, "ts": e["ts"][11:19], "target": e.get("app", "")})
    if cur:
        segments.append({"s": cur[2], "e": minutes, "cat": cur[0], "title": cur[1]})
    # 같은 분류가 연속이면 합치기 (제목이 달라도 같은 앱 안 이동은 한 구간)
    merged = []
    for g in segments:
        if merged and merged[-1]["cat"] == g["cat"] and merged[-1]["e"] >= g["s"]:
            merged[-1]["e"] = g["e"]
        else:
            merged.append(dict(g))
    segments = [g for g in merged if g["e"] > g["s"]]

    # 붙여넣기 뒤 3분간 직접 입력
    for p in pastes:
        p["after_typed"] = sum(typed[p["m"]:p["m"] + 3])

    chain, root = build_chain(evs)

    # 숫자들 (사실만)
    T, Dl = sum(typed), sum(deleted)
    P = sum(p["len"] for p in pastes)
    PAI = sum(p["len"] for p in pastes if p["ai"])
    active = [x for x in typed if x > 0]
    work_min = {m for g in segments if g["cat"] == "work" for m in range(g["s"], g["e"])}
    pauses, run = 0, 0
    for m in range(minutes):
        if m in work_min and typed[m] == 0:
            run += 1
            if run == 2:
                pauses += 1
        else:
            run = 0
    stats = {
        "typed": T, "deleted": Dl, "pasted": P, "pasted_ai": PAI, "pasted_other": P - PAI,
        "total": T + P,
        "typed_pct": round(T / (T + P) * 100) if T + P else 0,
        "pasted_pct": round(P / (T + P) * 100) if T + P else 0,
        "cpm": round(sum(active) / len(active)) if active else 0,
        "max_cpm": max(typed) if typed else 0,
        "edit_ratio": round(Dl / T * 100) if T else 0,
        "undo": len(undos), "pauses": pauses,
        "paste_count": len(pastes), "paste_ai_count": sum(1 for p in pastes if p["ai"]),
        "ai_min": sum(g["e"] - g["s"] for g in segments if g["cat"] == "ai"),
        "ai_visits": sum(1 for g in segments if g["cat"] == "ai"),
        "events": len(chain),
    }
    return {
        "id": evs[0]["session_id"], "date": evs[0]["ts"][:10],
        "start": evs[0]["ts"][11:19], "end": evs[-1]["ts"][11:19],
        "dur": f"{(t1 - t0).seconds // 60}분 {(t1 - t0).seconds % 60}초", "minutes": minutes,
        "sealed_at": None, "anchor": "none", "root": root,
        "segments": segments, "typed": typed, "deleted": deleted, "pastes": pastes, "undos": undos,
        "chain": chain, "stats": stats,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="events-*.jsonl")
    ap.add_argument("--session", help="세션 id (기본: 가장 최근)")
    ap.add_argument("--out", default=None, help="출력 파일 (기본: 입력 폴더의 session.json)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    by = load(a.paths)
    if not by:
        sys.exit("이벤트가 없습니다. 경로를 확인하세요.")
    if a.list:
        for sid, evs in sorted(by.items()):
            print(f"{sid}  {len(evs):5}건  {evs[0]['ts'][11:19]}–{evs[-1]['ts'][11:19]}")
        return
    sid = a.session or sorted(by)[-1]
    if sid not in by:
        sys.exit(f"세션 없음: {sid}. --list 로 확인하세요.")
    out = derive(by[sid])
    path = a.out or (glob.glob(a.paths[0])[0].rsplit("/", 1)[0].rsplit("\\", 1)[0] + "/session.json"
                     if ("/" in a.paths[0] or "\\" in a.paths[0]) else "session.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    s = out["stats"]
    print(f"세션 {sid}  {out['minutes']}분  이벤트 {s['events']}건")
    print(f"  직접 입력 {s['typed']}자 ({s['typed_pct']}%)  붙여넣기 {s['pasted']}자 ({s['pasted_pct']}%)"
          f"  그중 AI 창 복사본 {s['pasted_ai']}자 ({s['paste_ai_count']}건)")
    print(f"  삭제 {s['deleted']}자  되돌리기 {s['undo']}회  긴 멈춤 {s['pauses']}회  AI 창 {s['ai_min']}분")
    print(f"  루트 해시 {out['root'][:16]}…  →  {path}")


if __name__ == "__main__":
    main()
