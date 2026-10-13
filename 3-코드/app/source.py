"""
source.py — 학생 PC 의 "출처 보기" 화면 (캔버스 4 · 10/11 박상진)

  python app/statement.py  →  http://127.0.0.1:5079/source        (내역서 화면과 같은 작은 서버에 붙는다)

과제 파일(.docx) 문장마다 어디서 왔는지 색으로 보여 준다. 탭 둘:
  문서 기준  — 보고서 전문에 색 (결정 C: AI 답과 같음 · 다른 곳에서 옴 = 빨강 바탕 · 고침 = 파랑 바탕 · 보고 씀 = 파랑 점선 밑줄 · 출처 기록 없음 = 거의 안 보이는 회색)
              문장을 누르면 오른쪽에 질문 · 결과물 · AI 답 원문(쓰인 곳 칠함) · 출처(언제 복사 → 언제 붙여넣음)
  AI 답 기준 — 질문을 시간 순으로. 결과물에 글이 들어간 답과 **참고만 한 답**(이해·확인에 쓴 것)을 같이 보여 준다

★ 보기만 한다. 맞다/아니다 고르기는 다음 단계(연결 확인)에서. 서버로 아무것도 보내지 않는다 — 원문은 이 PC 안에서만.
★ 점수·퍼센트는 내지 않는다 (core/match.py 원칙 1). "출처 기록 없음" 은 "직접 씀" 이 아니다 (원칙 2).

연결 판단은 statement.py 의 /local/analyze 와 같은 core/match 함수를 같은 순서로 부른다 — 두 화면 결과가 같아야 한다.
"""
import io
import os
import re

from flask import Blueprint, abort, jsonify, request, send_from_directory

from core import match as M
from core.docx import read_docx

HERE = os.path.dirname(os.path.abspath(__file__))
bp = Blueprint("source", __name__)
_기록 = {}          # statement.py 가 init() 으로 넘겨줌: jsonl(pattern) · sessions() → {work_id: {세션 id}} · data_dir() · statement_exists(wid)
_파일 = {}          # work_id → (파일 이름, 바이트) — 학생이 직접 고른 파일. 새로 고쳐도 다시 고르지 않게 (이 PC 메모리에만)
_연_이름 = {}        # work_id → 기록된 자리에서 연 문서 이름 — 열 때마다 그 자리에서 다시 읽는다 (Word 에서 저장한 최신 내용)

# 화면 묶음 (결정 C): 빨강 = 글이 그대로 들어온 것 (일치 · 유사 · 다른 곳 붙여넣음 · 쓴 과정 기록 없음) — 붙여넣기든 보면서 똑같이 쳤든
GROUP = {"exact": "copy", "similar": "copy", "web": "copy", "noproc": "copy", "edited": "edited", "viewed": "viewed", "none": "none"}


def init(jsonl, sessions, data_dir=None, statement_exists=None, **kw):
    """kw: server(방법, 경로, json=…) → (코드, JSON) · auth() → {token, user} · made(wid) — 내보내기가 쓴다"""
    _기록.update(jsonl=jsonl, sessions=sessions, data_dir=data_dir, statement_exists=statement_exists, **kw)


@bp.get("/source")
def page():
    return send_from_directory(HERE, "source.html")


@bp.get("/ui/<name>")
def ui(name):
    """PC 앱 화면들이 같이 쓰는 화면 틀 (왼쪽 메뉴 · 위 줄)"""
    if name not in ("shell.css", "shell.js", "work.css", "work.js"):
        abort(404)
    return send_from_directory(HERE, name, max_age=0)    # 늘 새로 확인 — 고친 뒤에도 예전 틀이 남아 보이지 않게


@bp.post("/local/source")
def source():
    """form: work_id · file(.docx) → 문서 기준 · AI 답 기준 두 탭에 필요한 것.
    file 이 없으면: 이 과제에서 전에 고른 파일 → 없으면 기록기가 적어 둔 위치의 가장 최근 문서(있으면) → 없으면 고르라고 함"""
    wid = request.form.get("work_id", "")
    f = request.files.get("file")
    if f:
        _파일[wid] = (f.filename, f.read())
        _연_이름.pop(wid, None)
    if not (f and wid) and not 문서_준비(wid):
        return jsonify(error="no_file", message="과제 파일(.docx)을 골라 주세요", files=_기록된_문서(wid)), 400
    return _분석(wid)


def 문서_준비(wid):
    """파일을 새로 고르지 않았을 때 (연결 확인 화면도 씀): 전에 자리에서 연 문서는 최신 저장본으로 다시 읽고,
    없으면 기록기가 적어 둔 위치의 가장 최근 문서. 열 문서가 있으면 True"""
    if wid in _연_이름 and not _열기(wid, _연_이름[wid]):   # 옮겼으면 예전 내용 대신 아래로
        _파일.pop(wid, None)
    if wid and wid not in _파일:
        for d in _문서_목록(wid):                       # 가장 최근에 본 문서부터
            if d["exists"] and _열기(wid, d["name"]):
                break
    return bool(wid) and wid in _파일


@bp.post("/local/source/open")
def open_recorded():
    """form: work_id · name — 기록된 문서 목록에서 이름을 누르면, 기록기가 적어 둔 위치에서 바로 연다.
    옮겼거나 지웠으면 410 → 화면이 파일 고르는 창을 연다"""
    wid, name = request.form.get("work_id", ""), request.form.get("name", "")
    if not _열기(wid, name):
        return jsonify(error="moved", message=f'"{name}" 이 기록된 자리에 없습니다. 옮겼거나 지웠으면 직접 골라 주세요'), 410
    return _분석(wid)


def _열기(wid, name):
    d = next((d for d in _문서_목록(wid) if d["name"] == name), None)
    if not d or not d["exists"]:
        return False
    try:
        with open(d["path"], "rb") as fh:
            _파일[wid] = (name, fh.read())
        _연_이름[wid] = name
        return True
    except OSError:                                     # Word 가 잠가 둔 파일도 읽기는 됨 · 권한 문제 등은 고르게
        return False


def _분석(wid):
    name, raw = _파일[wid]
    try:
        paras = read_docx(io.BytesIO(raw))
    except Exception:
        _파일.pop(wid, None)
        return jsonify(error="bad_file", message="Word(.docx) 파일을 읽지 못했습니다"), 400
    rec = 과제_기록(wid)
    if not rec:
        return NO_RECORDS
    msgs, events, context, 세션 = rec
    기록된 = _기록된_문서(wid)
    # 화면엔 경로를 안 보낸다 (이름 · 그 자리에 있는지만) — 여는 건 이 PC 서버가 한다
    docs = [{"name": d["name"], "known": d["path"] is not None, "exists": d["exists"]} for d in _문서_목록(wid)]
    return jsonify(file=name, recorded_files=기록된, recorded_docs=docs, in_records=_같은_문서(name, 기록된),
                   sessions=len(세션), **build(paras, msgs, events, context))


NO_RECORDS = ({"error": "no_records", "message": "이 PC 에 이 과제의 기록이 없습니다 (기록기를 켠 PC 에서 열어 주세요)"}, 404)


def 과제_기록(wid):
    """이 PC 에서 이 과제를 기록한 세션들의 (AI 질문·답, 이벤트(시각 순), context, 세션 id) — 없으면 None"""
    세션 = _기록["sessions"]().get(wid, set())
    if not 세션:
        return None
    events = sorted((e for e in _기록["jsonl"]("events-*.jsonl") if e.get("session_id") in 세션), key=lambda e: e.get("ts", ""))
    context = [c for c in _기록["jsonl"]("context-*.jsonl") if c.get("session_id") in 세션]
    msgs = [r for r in _기록["jsonl"]("ai-messages-*.jsonl") if r.get("session_id") in 세션]
    return msgs, events, context, 세션


def _같은_문서(name, 기록된):
    """고른 파일이 이 과제를 기록할 때 연 문서인가 — 이름으로만 (Word 는 저장 전 "문서1" 처럼 확장자 없이 남기기도 함).
    아무 Word 파일이나 고를 수 있어서, 상관없는 파일이면 화면이 알려 준다 (거의 다 "출처 기록 없음" 으로 나와 오해할 수 있음)"""
    줄기 = lambda n: os.path.splitext(os.path.basename(n or ""))[0].strip().lower()
    return 줄기(name) in {줄기(n) for n in 기록된}


@bp.get("/local/source/works")
def pc_works():
    """로그인 없이도 왼쪽 과제 목록을 그릴 수 있게 — 이 PC 에 기록이 있는 과제 id 와 기록 수"""
    return jsonify(works=[{"id": k, "pc_sessions": len(v)} for k, v in sorted(_기록["sessions"]().items())])


def _기록된_문서(wid):
    """기록기가 이 과제를 기록하는 동안 본 Word 문서 이름"""
    return sorted(d["name"] for d in _문서_목록(wid))


def _문서_목록(wid):
    """이 과제에서 기록된 Word 문서 → [{"name", "path" | None, "exists", "ts"}] 가장 최근에 본 것부터.
    이름 = 체인 이벤트(doc_save · doc_change)의 file · 위치 = 기록기가 PC 에만 적어 둔 doc_path (10/11 부터, 없으면 None)"""
    세션 = _기록["sessions"]().get(wid, set())
    out, 본때 = {}, {}                                   # 본때: (세션, 이름) → [처음, 마지막] 시각
    for e in _기록["jsonl"]("events-*.jsonl"):
        if e.get("session_id") in 세션 and e.get("type") in ("doc_save", "doc_change") and e.get("app") == "Word" and e.get("file"):
            d = out.setdefault(e["file"], {"name": e["file"], "path": None, "ts": ""})
            d["ts"] = max(d["ts"], e.get("ts", ""))
            t = 본때.setdefault((e["session_id"], e["file"]), [e.get("ts", ""), e.get("ts", "")])
            t[0], t[1] = min(t[0], e.get("ts", "")), max(t[1], e.get("ts", ""))
    # 저장 전 이름("문서1" · 확장자 없음) 뒤에 같은 기록에서 저장된 문서가 나오면 = 저장하며 이름이 바뀐 같은 문서 → 목록에서 뺀다
    # (기록기도 내용이 겹치면 같은 문서로 이어 본다 · office._compare). 끝까지 저장 안 한 문서만 "저장 전 이름" 으로 남김
    for (sid, n), (_, 끝) in list(본때.items()):
        if not os.path.splitext(n)[1] and any(s2 == sid and os.path.splitext(m)[1] and 처음 >= 끝
                                              for (s2, m), (처음, _) in 본때.items()):
            out.pop(n, None)
    for c in _기록["jsonl"]("context-*.jsonl"):
        m = c.get("meta") or {}
        if c.get("session_id") in 세션 and c.get("kind") == "doc_path" and m.get("app") == "Word" and m.get("file") and m.get("path"):
            d = out.setdefault(m["file"], {"name": m["file"], "path": None, "ts": ""})
            if c.get("ts", "") >= d.get("path_ts", ""):            # 같은 이름이 여러 자리 → 가장 최근 자리
                d.update(path=m["path"], path_ts=c.get("ts", ""))
            d["ts"] = max(d["ts"], c.get("ts", ""))
    docs = sorted(out.values(), key=lambda d: d["ts"], reverse=True)
    for d in docs:
        d["exists"] = bool(d["path"]) and d["path"].lower().endswith(".docx") and os.path.isfile(d["path"])
        d.pop("path_ts", None)
    return docs


def build(paras, msgs, events, context):
    """read_docx 문단 [(style, text)] + 이 PC 기록 → {title, paragraphs, sentences, questions, counts}
    문장 번호(k)는 문서 처음부터 셈. 질문 번호(n)는 시간 순 1 부터."""
    title, body, heads = _제목_본문(paras)
    기록 = sorted(M.latest_messages(msgs), key=lambda r: r.get("ts", ""))
    답들 = [r for r in 기록 if r.get("role") == "answer"]
    질문들 = [r for r in 기록 if r.get("role") == "question"]

    def 질문(ans):
        """이 답 바로 앞의 같은 세션·같은 도구 질문 (statement.py 와 같은 규칙)"""
        앞 = [i for i, r in enumerate(질문들) if r["session_id"] == ans["session_id"]
              and r.get("tool") == ans.get("tool") and r.get("ts", "") <= ans.get("ts", "")]
        return 앞[-1] if 앞 else None

    pasted = M.pasted_from_ai(events, context)
    linked = M.link_document(body, [{"id": i, "text": r["text"]} for i, r in enumerate(답들)],
                             pasted, M.pasted_from_other(events, context), M.process_evidence(events, context))

    # 질문 = 한 턴. 답은 그 질문에 붙인다 (질문 기록이 없는 답은 질문 없이 따로 한 턴)
    턴 = [{"q": q, "answers": []} for q in 질문들]
    for ai, a in enumerate(답들):
        qi = 질문(a)
        if qi is None:
            턴.append({"q": None, "answers": [ai]})
        else:
            턴[qi]["answers"].append(ai)
    턴 = [t for t in 턴 if t["q"] or t["answers"]]
    턴.sort(key=lambda t: (t["q"] or 답들[t["answers"][0]]).get("ts", ""))
    답의_턴 = {ai: n for n, t in enumerate(턴) for ai in t["answers"]}

    문단, 문장 = [], []
    for pi, row in enumerate(linked):
        ks = []
        for s in row:
            kind = ("exact" if s.get("full") else "similar") if s["label"] == "exact" else s["label"]
            x = {"k": len(문장), "p": pi, "text": s["text"], "kind": kind, "group": GROUP[kind]}
            if s["label"] in ("exact", "edited", "viewed") and s.get("answer") is not None:
                x.update(q=답의_턴[s["answer"]], answer=s["answer"], sents=list(s["sents"] or ()), ai_text=s.get("ai_text"))
            p = s.get("paste")
            if p:
                x["paste"] = {k: p.get(k, "") for k in ("copied_at", "pasted_at", "where", "domain", "source", "category")}
            if s["label"] == "web":
                x["ai_text"] = s.get("ai_text")                    # 붙여넣은 글 원문 (다른 곳)
            if s["label"] == "noproc":
                pr = s.get("proc") or {}
                x["proc"] = {"how": pr.get("how", ""), "ts": pr.get("ts", "")}
            문장.append(x)
            ks.append(x["k"])
        문단.append({"head": pi in heads, "sents": ks})

    questions = []
    for n, t in enumerate(턴):
        q = t["q"]
        ans = [답들[i] for i in t["answers"]]
        쓰임 = [x for x in 문장 if x.get("answer") in t["answers"]]
        # 같은 질문에 답이 여럿이면(다시 생성) 결과물 문장이 가장 많이 이어진 답을 보여 줌 (같으면 마지막 답)
        # — 마지막 답만 보이면 앞 답에 이어진 문장을 골랐을 때 칠할 곳이 없다 (10/12)
        보일 = max(t["answers"], key=lambda ai: (sum(1 for x in 쓰임 if x["answer"] == ai), ai)) if ans else None
        main = 답들[보일] if ans else None
        questions.append({
            "n": n + 1, "tool": (q or main).get("tool", ""), "model": ((main or {}).get("model") or (q or {}).get("model") or ""),
            "ts": (q or main).get("ts", ""), "question": q["text"] if q else None,
            "answer": _답_조각(main["text"], [x for x in 쓰임 if x["answer"] == 보일]) if main else None,
            "uses": [x["k"] for x in 쓰임],
            "groups": {g: sum(1 for x in 쓰임 if x["group"] == g) for g in ("copy", "edited", "viewed")},
            "paras": sorted({x["p"] + 1 for x in 쓰임}),
            # 교수 링크 출처 보기(김용현 · 10/12): 이 질문·답이 체인의 어느 기록인지 — 서버가 원문을 해시로 맞춰 본다
            "refs": {k: {"session_id": r["session_id"], "event_id": r["event_id"], "hash": r.get("hash", "")}
                     for k, r in (("q", q), ("a", main)) if r and r.get("event_id")},
        })

    counts = {g: sum(1 for x in 문장 if x["group"] == g) for g in ("copy", "edited", "viewed", "none")}
    counts.update(questions=len(questions), used=sum(1 for q in questions if q["uses"]),
                  ref=sum(1 for q in questions if not q["uses"] and q["answer"]),
                  # 연결 확인에서 학생에게 물을 것 = 붙여넣기 기록 없이 글자만 비슷한 것 (복사 → 붙여넣기처럼 확실한 건 자동)
                  confirm=sum(1 for x in 문장 if x["kind"] in ("exact", "similar", "edited", "viewed") and not x.get("paste")))
    return {"title": title, "paragraphs": 문단, "sentences": 문장, "questions": questions, "counts": counts}


_HEAD = re.compile(r"^(heading\d|제목\s?\d)$", re.I)
_NUM = re.compile(r"^\s*(\d{1,2}|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|[가-하])[.)]\s")


def _제목_본문(paras):
    """core/docx.doc_body 와 같게 제목을 떼고 (연결 결과가 내역서 화면과 같아야 함), 소제목 문단 번호도 같이"""
    heads = [i for i, (st, t) in enumerate(paras) if st.lower() in ("title", "heading1", "제목")]
    if not heads and paras and len(paras[0][1]) <= 60 and not re.search(r"[.!?。]$", paras[0][1]):
        heads = [0]
    title = paras[heads[0]][1] if heads else ""
    rest = [(st, t) for i, (st, t) in enumerate(paras) if i not in heads]
    # 소제목 = Word 제목 서식, 또는 "1. 서론" · "Ⅱ. 본론" · "가. 사례" 처럼 번호로 시작하는 짧은 줄 (목록 줄은 굵게 하지 않음)
    sub = {i for i, (st, t) in enumerate(rest) if _HEAD.match(st or "")
           or (len(t) <= 40 and _NUM.match(t) and not re.search(r"[.!?。]$", t) and "\n" not in t)}
    return title, [t for st, t in rest], sub


def _답_조각(text, 쓰임):
    """AI 답 원문 → [{"t": 글, "g": 묶음 | None, "i": 답의 문장 번호}] — 결과물로 간 문장만 칠한다 (match.split_sentences 와 같은 문장 나누기)
    i 로 화면이 "지금 고른 문장" 에 이어진 부분만 진하게 칠하고 그 자리로 굴린다 (결과물 문장의 sents 와 같은 번호)"""
    shown = text.replace("**", "")
    색 = {}
    for x in 쓰임:
        for i in x.get("sents", []):
            색.setdefault(i, x["group"])
    out, at = [], 0
    for i, s in enumerate(M.split_sentences(text)):
        j = shown.find(s, at)
        if j < 0:
            continue
        if j > at:
            out.append({"t": shown[at:j], "g": None})
        out.append({"t": s, "g": 색.get(i), "i": i})
        at = j + len(s)
    if at < len(shown):
        out.append({"t": shown[at:], "g": None})
    return out
