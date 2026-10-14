"""
record.py — 기록 다시 보기 (캔버스 "Record" · 과제 상세의 기록 줄을 누르면 · 10/14 박상진)

  /record?work=…&session=…        → 기록 하나를 시간 순으로: 위 숫자 · 시간 막대(AI 질문·답 · 붙여넣기 · Word 글 · 멈춤) ·
                                     왼쪽 목록(전체 | AI 질문·답 | 붙여넣기 | Word 글) · 오른쪽 고른 줄의 자세한 내용
  GET /local/record/detail?work_id=…&session_id=…

★ 원문은 이 PC 화면에만 (이 화면은 서버로 아무것도 안 보낸다).
★ "결과물과 이어진 것" 표시는 출처 보기(source.build)와 같은 결과를 쓴다 — 두 화면이 다른 말을 하면 안 됨.
  과제 파일을 아직 못 열었으면 표시 없이 기록만 보여 준다.
★ 점수·퍼센트 없음 · "출처 기록 없음" 은 "직접 씀" 이 아니다.
"""
import io
import os
import re
from datetime import datetime
from urllib.parse import quote

from flask import Blueprint, jsonify, request, send_from_directory

import source as S
from core import match as M
from core.docx import read_docx

HERE = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint("record", __name__)
_ID = re.compile(r"^[\w\-.]{1,80}$")
KEYS_GAP = 180          # 키 입력이 이만큼(초) 끊기면 Word 글 줄을 새로 (같은 앱일 때만 이어 붙임)
GROUP_NAME = {"copy": "AI 답과 같음", "edited": "고침", "viewed": "보고 씀"}   # 출처 보기 범례와 같은 말
APP_NAME = {"winword.exe": "Word", "code.exe": "VS Code", "hwp.exe": "한글", "powerpnt.exe": "PowerPoint",
            "excel.exe": "Excel", "notepad.exe": "메모장", "claude.exe": "Claude 앱", "chatgpt.exe": "ChatGPT 앱"}


@bp.get("/record")
def page():
    return send_from_directory(HERE, "record.html")


def _앱(a):
    a = a or ""
    return APP_NAME.get(a.lower(), a[:-4] if a.lower().endswith(".exe") else a) or "다른 프로그램"


def _초(a, b):
    try:
        return int((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds())
    except (TypeError, ValueError):
        return 0


@bp.get("/local/record/detail")
def detail():
    """→ {work, session:{id, start, end, n, total, active_sec, pause_sec}, stats, lanes, items:[…], linked(문서를 열어 표시가 있나)}
    items: {id, ts, end?, kind: start|doc|q|a|paste|word|pause|end, title, text, tag:{t, c} | None, more:{…}}"""
    wid, sid = request.args.get("work_id", ""), request.args.get("session_id", "")
    if not _ID.match(wid) or not _ID.match(sid):
        return jsonify(error="bad_request"), 400
    rec = S.과제_기록(wid)
    if not rec or sid not in rec[3]:
        return jsonify(error="not_found", message="이 PC 에 이 기록이 없어요"), 404
    msgs, events, context, 세션 = rec
    evs = [e for e in events if e.get("session_id") == sid]
    ctx = [c for c in context if c.get("session_id") == sid]
    mine = sorted((m for m in M.latest_messages(msgs) if m.get("session_id") == sid), key=lambda m: m.get("ts", ""))

    # 결과물과 이어진 것 — 출처 보기와 같은 분석 (과제 파일을 열 수 있을 때만)
    분석 = None
    if S.문서_준비(wid):
        try:
            분석 = S.build(read_docx(io.BytesIO(S._파일[wid][1])), msgs, events, context)
        except Exception:
            분석 = None
    턴 = {}                                            # 메시지 event_id → 출처 보기의 질문 한 턴
    for q in (분석 or {}).get("questions", []):
        for r in q.get("refs", {}).values():
            턴[r["event_id"]] = q
    문장 = (분석 or {}).get("sentences", [])

    items, lanes = [], {"ai": [], "paste": [], "word": [], "pause": []}
    시작 = next((e["ts"] for e in evs if e.get("type") == "session_start"), evs[0]["ts"] if evs else "")
    끝 = next((e["ts"] for e in evs if e.get("type") == "session_end"), "") or (evs[-1]["ts"] if evs else "")
    문서들 = [c["meta"]["file"] for c in ctx if c.get("kind") in ("doc_path", "doc_open") and (c.get("meta") or {}).get("file")]
    items.append({"kind": "start", "ts": 시작, "title": "기록 시작", "text": 문서들[0] if 문서들 else "", "tag": None})

    # 문서를 처음 볼 때 이미 있던 글 (AI 가 만든 Word · 다른 기기에서 만든 파일) — 출처 보기의 "쓴 과정 기록 없음"
    for c in ctx:
        if c.get("kind") == "doc_open":
            m = c.get("meta") or {}
            n = m.get("chars") or len(c.get("text", ""))
            items.append({"kind": "doc", "ts": c["ts"], "title": "문서 열기", "text": f"{m.get('file', '')} · 열 때부터 있던 글 {n:,}자",
                          "tag": {"t": "쓴 과정 기록 없음", "c": "copy"} if n else None,
                          "more": {"file": m.get("file", ""), "chars": n, "excerpt": c.get("text", "")[:400]}})

    # AI 질문 · 답
    번호 = {}
    질문들 = [m for m in mine if m.get("role") == "question"]
    for m in mine:
        q = 턴.get(m.get("event_id"))
        tool = m.get("tool") or "AI"
        딴답 = False
        if q is None and m.get("role") == "answer":          # 같은 질문의 다른 답 (다시 생성 등) — 출처 보기는 가장 많이 이어진 답 하나만 보여 줌
            짝 = next((x for x in reversed(질문들) if x.get("tool") == m.get("tool") and x.get("ts", "") <= m.get("ts", "")), None)
            q, 딴답 = (턴.get(짝.get("event_id")), True) if 짝 else (None, False)
        n = q["n"] if q else 번호.setdefault((tool, m.get("turn")), len(번호) + 1)
        lanes["ai"].append(m["ts"])
        if m.get("role") == "question":
            items.append({"kind": "q", "ts": m["ts"], "title": f"{tool} 질문 {n}", "text": f"“{_한줄(m['text'], 70)}”", "tag": None,
                          "more": _턴_자세히(q, m, 문장, mine)})
        else:
            tag = None
            if 딴답 and q is not None:
                tag = {"t": "같은 질문의 다른 답", "c": "plain"}
            elif q is not None:
                g = q.get("groups") or {}
                쓰임 = [(k, g.get(k, 0)) for k in ("copy", "edited", "viewed") if g.get(k)]
                tag = {"t": " · ".join(f"{GROUP_NAME[k]} {v}" for k, v in 쓰임), "c": 쓰임[0][0]} if 쓰임 else {"t": "참고만", "c": "ref"}
            items.append({"kind": "a", "ts": m["ts"], "title": f"{tool} 답 {n}", "text": f"{len(m['text']):,}자", "tag": tag,
                          "more": _턴_자세히(None if 딴답 else q, m, 문장, mine)})

    # 붙여넣기 — 어디서 왔나 (출처 보기와 같은 규칙: AI 답 · 다른 곳 · 그 밖)
    ai붙 = {p["pasted_at"]: p for p in M.pasted_from_ai(evs, ctx)}
    다른붙 = {p["pasted_at"]: p for p in M.pasted_from_other(evs, ctx)}
    for e in evs:
        if e.get("type") != "paste":
            continue
        lanes["paste"].append(e["ts"])
        n, 어디로 = e.get("len") or 0, _앱(e.get("app"))
        if e["ts"] in ai붙:
            p = ai붙[e["ts"]]
            items.append({"kind": "paste", "ts": e["ts"], "title": "복사 → 붙여넣기",
                          "text": f"AI 답에서 {n:,}자 → {p.get('where') or 어디로}", "tag": {"t": "AI 답", "c": "copy"},
                          "more": {"from": "AI 답" + (f" · {p['domain']}" if p.get("domain") else ""), "to": p.get("where") or 어디로,
                                   "copied_at": p.get("copied_at", ""), "len": n, "excerpt": p.get("text", "")[:600]}})
        elif e["ts"] in 다른붙:
            p = 다른붙[e["ts"]]
            src = p.get("source") or "다른 곳"
            items.append({"kind": "paste", "ts": e["ts"], "title": "복사 → 붙여넣기",
                          "text": f"{src} 에서 {n:,}자 → {p.get('where') or 어디로}", "tag": {"t": "다른 곳", "c": "copy"},
                          "more": {"from": src, "to": p.get("where") or 어디로, "copied_at": p.get("copied_at", ""), "len": n,
                                   "excerpt": p.get("text", "")[:600]}})
        else:
            ai앱 = (e.get("category") == "ai") or 어디로.endswith("앱") or "chatgpt" in (e.get("target_title") or "").lower() \
                or "claude" in (e.get("target_title") or "").lower() or "gemini" in (e.get("target_title") or "").lower()
            items.append({"kind": "paste", "ts": e["ts"], "title": "복사 → 붙여넣기",
                          "text": f"{n:,}자 → {어디로}", "tag": {"t": "AI 에 넣음", "c": "ref"} if ai앱 else None,
                          "more": {"from": "", "to": 어디로, "copied_at": "", "len": n, "excerpt": ""}})

    # Word 글 — 문서 변화(doc_change) 가 있으면 그것, 없으면 AI 아닌 프로그램의 키 입력을 몇 분 단위로 묶음
    바뀜 = [e for e in evs if e.get("type") == "doc_change" and e.get("where") != "삭제"]
    덩이 = []                                          # 몇 초마다 남는 문서 변화를 몇 분 단위로 한 줄에 (10/14 · 59줄 → 몇 줄)
    for e in 바뀜:
        app, k = _앱(e.get("app")), 덩이[-1] if 덩이 else None
        if k and k["app"] == app and _초(k["end"], e["ts"]) <= KEYS_GAP:
            k.update(end=e["ts"], added=k["added"] + (e.get("added") or 0), removed=k["removed"] + (e.get("removed") or 0))
        else:
            k = {"app": app, "start": e["ts"], "end": e["ts"], "added": e.get("added") or 0, "removed": e.get("removed") or 0, "where": []}
            덩이.append(k)
        if e.get("where") and e["where"] not in k["where"]:
            k["where"].append(e["where"])
    for k in 덩이:
        lanes["word"].append([k["start"], k["end"]])
        곳 = _곳(k["where"])
        items.append({"kind": "word", "ts": k["start"], "end": k["end"], "title": k["app"],
                      "text": " · ".join(filter(None, [곳, f"+{k['added']:,}자" + (f" −{k['removed']:,}자" if k["removed"] else ""),
                                                      f"{_hm(k['start'])}–{_hm(k['end'])}" if k["end"] != k["start"] else ""])),
                      "tag": None, "more": {"app": k["app"], "where": 곳, "added": k["added"], "removed": k["removed"], "from": k["start"], "to": k["end"]}})
    묶음들 = []
    for e in evs:
        if e.get("type") != "keys" or e.get("category") != "work":   # 과제 프로그램(Word · VS Code …)만 — AI 앱에 친 글은 질문 줄, 탐색기 등은 뺌
            continue
        app, k = _앱(e.get("app")), 묶음들[-1] if 묶음들 else None
        if k and k["app"] == app and _초(k["end"], e["ts"]) <= KEYS_GAP:
            k.update(end=e["ts"], count=k["count"] + (e.get("count") or 0), deleted=k["deleted"] + (e.get("deleted") or 0))
        else:
            묶음들.append({"app": app, "start": e["ts"], "end": e["ts"], "count": e.get("count") or 0, "deleted": e.get("deleted") or 0})
    if not 바뀜:
        for k in 묶음들:
            lanes["word"].append([k["start"], k["end"]])
            items.append({"kind": "word", "ts": k["start"], "end": k["end"], "title": k["app"],
                          "text": f"키보드로 +{k['count']:,}자" + (f" · 지움 {k['deleted']:,}" if k["deleted"] else "")
                                  + (f" · {_hm(k['start'])}–{_hm(k['end'])}" if k["end"] != k["start"] else ""),
                          "tag": None, "more": {"app": k["app"], "typed": k["count"], "deleted": k["deleted"], "from": k["start"], "to": k["end"]}})

    # 잠깐 멈춤 — 시각만
    멈춤초, 멈춤 = 0, None
    for e in evs:
        if e.get("type") == "pause_start":
            멈춤 = e["ts"]
        elif e.get("type") == "pause_end" and 멈춤:
            s = _초(멈춤, e["ts"])
            멈춤초 += s
            lanes["pause"].append([멈춤, e["ts"]])
            items.append({"kind": "pause", "ts": 멈춤, "end": e["ts"], "title": "잠깐 멈춤",
                          "text": f"{_hm(멈춤)} – {_hm(e['ts'])} · {_분(s)} · 이 동안은 기록 안 함", "tag": {"t": "시각만", "c": "plain"}})
            멈춤 = None
    if 끝 and any(e.get("type") == "session_end" for e in evs):
        items.append({"kind": "end", "ts": 끝, "title": "기록 끝", "text": "", "tag": None})

    순 = ["start", "doc", "q", "a", "paste", "word", "pause", "end"]
    items.sort(key=lambda x: (x["kind"] != "start", x["kind"] == "end", x["ts"], 순.index(x["kind"])))   # 시작 · 끝은 늘 맨 앞 · 맨 뒤
    for i, x in enumerate(items):
        x["id"] = i
    순서 = sorted(세션, key=lambda s: next((e["ts"] for e in events if e.get("session_id") == s and e.get("type") == "session_start"), ""))
    typed = sum(e.get("count") or 0 for e in evs if e.get("type") == "keys" and e.get("category") == "work")
    return jsonify(
        work={"id": wid}, linked=분석 is not None,
        session={"id": sid, "start": 시작, "end": 끝, "n": 순서.index(sid) + 1, "total": len(순서),
                 "active_sec": max(0, _초(시작, 끝) - 멈춤초) if 시작 and 끝 else None, "pause_sec": 멈춤초},
        stats={"questions": sum(1 for m in mine if m.get("role") == "question"), "pastes": len(lanes["paste"]),
               "typed": typed, "pause_sec": 멈춤초},
        lanes=lanes, items=items, source=f"/source?work={quote(wid, safe='')}")


def _턴_자세히(q, m, 문장, mine):
    """오른쪽 칸: 질문 · 결과물에 이어진 문장 · AI 답 원문(쓰인 곳 칠함). 출처 보기 AI 답 기준 탭과 같은 자료"""
    if q is None:                                        # 문서를 못 열었거나 이 턴이 분석에 없음 → 원문만
        짝 = None
        if m.get("role") == "answer":
            짝 = next((x for x in reversed(mine) if x.get("role") == "question" and x.get("ts", "") <= m.get("ts", "")
                       and x.get("tool") == m.get("tool")), None)
        return {"tool": m.get("tool") or "AI", "model": m.get("model") or "", "ts": m.get("ts", ""),
                "question": (m if m.get("role") == "question" else 짝 or {}).get("text"),
                "answer": [{"t": m["text"], "g": None}] if m.get("role") == "answer" else None, "uses": []}
    return {"tool": q.get("tool") or "AI", "model": q.get("model") or "", "ts": q.get("ts", ""), "question": q.get("question"),
            "answer": q.get("answer"), "uses": [{"text": 문장[k]["text"], "group": 문장[k]["group"], "p": 문장[k]["p"] + 1}
                                                for k in q.get("uses", [])[:8]]}


def _곳(wheres):
    """["문단 1", "문단 2", "문단 4"] → "문단 1–2 · 4" (같은 단위일 때) · 섞여 있으면 앞 셋"""
    단위 = {w.rsplit(" ", 1)[0] for w in wheres if " " in w}
    수 = sorted({int(w.rsplit(" ", 1)[1]) for w in wheres if " " in w and w.rsplit(" ", 1)[1].isdigit()})
    if len(단위) != 1 or len(수) != len(wheres):
        return " · ".join(wheres[:3]) + (" …" if len(wheres) > 3 else "")
    조각, i = [], 0
    while i < len(수):
        j = i
        while j + 1 < len(수) and 수[j + 1] == 수[j] + 1:
            j += 1
        조각.append(f"{수[i]}–{수[j]}" if j > i else str(수[i]))
        i = j + 1
    return f"{단위.pop()} " + " · ".join(조각)


def _한줄(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def _hm(ts):
    return ts[11:16] if ts and len(ts) >= 16 else ""


def _분(s):
    return f"{max(1, round(s / 60))}분" if s < 3600 else f"{s // 3600}시간 {s % 3600 // 60}분"
