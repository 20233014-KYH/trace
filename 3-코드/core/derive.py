"""
derive.py — 수집기 원본 이벤트(jsonl) → "한눈에" 화면 데이터(session.json)

  python core/derive.py data/events-2026-09-19.jsonl            # 가장 최근 세션 → data/session.json
  python core/derive.py data/events-*.jsonl --session s_2026-09-19_150002 --out out.json
  python core/derive.py data/events-*.jsonl --list                # 세션 목록만

출력 구조 = 목업북 <script id="DATA"> 의 session 과 동일. ui/viewer.html 이 그대로 읽는다.
  segments[] {s,e,cat,title}   분 단위 활성 창 구간
  typed[] deleted[]            분당 입력·삭제 횟수 (길이 = minutes)
  pastes[] {m,len,ai,matched,src{app,title,category},target,after_typed}  붙여넣기. ai = 같은 해시가 AI 앱·사이트에서 복사됐음
  flow[]  {ts,app,title,cat,typed,deleted,items[]}   사람이 읽는 이벤트 흐름 — 창별로 묶음
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

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import chain as C  # noqa: E402

GENESIS = C.GENESIS
BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe"}


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


def build_chain(evs):
    """core/chain.py 와 동일 — 수집기·서버·derive 가 같은 해시를 낸다."""
    return C.build(evs)


def derive(evs):
    if not evs:
        return None
    t0 = ts(evs[0])
    t1 = ts(evs[-1])
    minutes = max(1, int((t1 - t0).total_seconds() // 60) + 1)
    mi = lambda e: min(minutes - 1, int((ts(e) - t0).total_seconds() // 60))
    mf = lambda e: round((ts(e) - t0).total_seconds() / 60, 2)   # 구간은 초 단위(분의 소수)로

    typed = [0] * minutes
    deleted = [0] * minutes
    undos = []
    pastes = []
    segments = []
    copies = {}  # hash -> {"app","title","category"} 복사가 일어난 창
    flow = []    # 사람이 읽는 이벤트 흐름: 창별로 묶음
    fw = None    # 현재 창 항목

    cur = None  # 현재 활성 창 (cat, title, start_min)
    for e in evs:
        t = e["type"]
        if t == "window":
            cat, title = e.get("category", "other"), e.get("title", "")
            m = mf(e)
            app = e.get("app", "")
            if cur and cur[0] == cat and cur[1] == title and cur[3] == app:   # 같은 앱·같은 제목만 같은 창
                continue
            if cur:
                segments.append({"s": cur[2], "e": m, "cat": cur[0], "title": cur[1]})
            cur = (cat, title, m, app)
            fw = {"ts": e["ts"][11:19], "app": e.get("app", ""), "title": title, "cat": cat, "typed": 0, "deleted": 0, "items": []}
            flow.append(fw)
        elif t == "tab":
            # 확장이 보낸 탭 전환: 현재 창이 브라우저면 분류·제목을 도메인 기준으로 바꾼다 (창 제목 키워드보다 정확)
            if cur and cur[3] in BROWSERS:
                cat, title, m = e.get("category", "other"), e.get("domain") or e.get("title", ""), mf(e)   # 내부 페이지는 domain "" → 제목으로
                if not (cur[0] == cat and cur[1] == title):
                    segments.append({"s": cur[2], "e": m, "cat": cur[0], "title": cur[1]})
                    cur = (cat, title, m, cur[3])
                    fw = {"ts": e["ts"][11:19], "app": cur[3], "title": title, "cat": cat, "typed": 0, "deleted": 0, "items": []}
                    flow.append(fw)
        elif t == "keys":
            typed[mi(e)] += e.get("count", 0)
            deleted[mi(e)] += e.get("deleted", 0)
            if fw:
                fw["typed"] += e.get("count", 0); fw["deleted"] += e.get("deleted", 0)
        elif t == "undo":
            undos.append(mi(e))
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "undo", "text": "되돌리기 (Ctrl+Z)"})
        elif t in ("redo", "cut"):
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": t, "text": {"redo": "다시 실행 (Ctrl+Y)", "cut": "잘라내기 (Ctrl+X)"}[t]})
        elif t == "copy":
            copies[e.get("hash")] = {"app": e.get("app", ""), "title": (cur[1] if cur else ""), "category": e.get("category", "other")}
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "copy", "text": f"복사 {e.get('len', 0)}자"})
        elif t == "paste":
            h = e.get("hash")
            src = copies.get(h)
            pastes.append({"m": mi(e), "len": e.get("len", 0), "ai": bool(src and src["category"] == "ai"),
                           "matched": src is not None, "ts": e["ts"][11:19],
                           "target": e.get("app", ""), "target_title": e.get("target_title", ""),
                           "src": src})
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "paste", "len": e.get("len", 0), "src": src,
                                       "text": f"붙여넣기 {e.get('len', 0)}자"})
        elif t == "file":
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "file", "text": f"파일 {e.get('action', '')} · {os.path.basename(e.get('path', ''))}"})
        elif t == "commit":
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "commit", "text": f"커밋 {e.get('hash','')[:7]} · {e.get('files',0)}파일 +{e.get('added',0)}/-{e.get('removed',0)} ({e.get('repo','')})"})
        elif t == "git_push":
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "commit", "text": f"푸시 {e.get('remote_ref','')} · {e.get('hash','')[:7]}"})
        elif t == "doc_change":
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "doc", "text": f"문서 {e.get('where','')} +{e.get('added',0)}자 / -{e.get('removed',0)}자"})
        elif t == "doc_paste_at":
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "doc", "text": f"붙여넣은 자리: {e.get('where','')}"})
        elif t == "doc_save":
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": "doc", "text": "저장 · " + " · ".join(f"{k} {e[k]}" for k in ("chars", "words", "slides") if k in e)})
        elif t in ("idle_start", "idle_end"):
            if fw: fw["items"].append({"ts": e["ts"][11:19], "kind": t, "text": "자리 비움 (5분 무입력)" if t == "idle_start" else "복귀"})
    if cur:
        segments.append({"s": cur[2], "e": round((t1 - t0).total_seconds() / 60, 2), "cat": cur[0], "title": cur[1]})
    # 같은 분류가 연속이면 합치기 (제목이 달라도 같은 앱 안 이동은 한 구간). 3초 미만 스침은 앞 구간에 흡수
    merged = []
    for g in segments:
        if merged and (merged[-1]["cat"] == g["cat"] or g["e"] - g["s"] < 0.05):
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
    work_min = {m for g in segments if g["cat"] == "work" for m in range(int(g["s"]), int(g["e"]) + 1)}
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
        "ai_min": round(sum(g["e"] - g["s"] for g in segments if g["cat"] == "ai"), 1),
        "ai_visits": sum(1 for g in segments if g["cat"] == "ai"),
        "events": len(chain),
    }
    return {
        "id": evs[0]["session_id"], "date": evs[0]["ts"][:10],
        "start": evs[0]["ts"][11:19], "end": evs[-1]["ts"][11:19],
        "dur": f"{(t1 - t0).seconds // 60}분 {(t1 - t0).seconds % 60}초", "minutes": minutes,
        "sealed_at": None, "anchor": "none", "root": root,
        "segments": segments, "typed": typed, "deleted": deleted, "pastes": pastes, "undos": undos,
        "flow": flow, "chain": chain, "stats": stats,
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
