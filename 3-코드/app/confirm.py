"""
confirm.py — 학생 PC 의 "연결 확인" 화면 (캔버스 5-1 · 10/12 박상진)

  python app/statement.py  →  http://127.0.0.1:5079/confirm?work=<과제 id>   (출처 보기 다음 단계 · 같은 작은 서버)

붙여넣기 기록 없이 글자만 비슷한 문장(출처 보기의 counts.confirm)을 학생이 출처로 연결할지 고른다.
  · 묻는 단위 = AI 답 하나 — 그 답과 비슷한 문장들을 묶어서 한 번에. 뺄 문장은 체크를 끈다
  · 말투 = "출처로 연결할까요?" (털어놓기가 아니라 출처 달기) · 고르는 것: 연결함 / 연결 안 함 / 잘 모르겠음
  · 기억 대신 증거: 내 질문 원문 · 두 글에 함께 있는 낱말 · 시간 순서(질문 → 답 → 그 문장 입력)
  · 남은 것 모두 연결 (마감 직전에 몰아서 할 때) · 고르지 않고 넘어가면 '잘 모르겠음' 과 같다 → 기록 사실만 남김
  · "모두 연결 안 함" 은 두지 않는다 — 한 번에 다 지우는 버튼이 되므로
붙여넣기 기록으로 확실한 연결은 묻지 않는다 (자동).

고른 것은 이 PC 의 data 폴더 confirm-<과제>.json 에만 둔다 (서버로 안 감).
키 = 결과물 문장 해시 앞 16 + AI 답 해시 앞 16 → 문서를 고쳐 저장해도 같은 문장이면 고른 것이 그대로 남는다.
내역서 만들기는 GET /local/confirm/decisions 로 읽어 가면 된다 (키 만드는 법 = key_of).
★ 점수·퍼센트 없음 — 겹친 낱말은 칠하기만 한다.
"""
import difflib
import io
import json
import os
import re
from datetime import datetime
from urllib.parse import quote

from flask import Blueprint, jsonify, redirect, request, send_from_directory

from core import match as M, safefile
from core.docx import read_docx
from core.pdftext import read_doc
from core.texthash import sha256_text
import source as S

bp = Blueprint("confirm", __name__)
ASK = ("exact", "similar", "edited", "viewed")   # 학생에게 물을 것 = 이 표시 중 붙여넣기 기록 없는 것 (source.build counts.confirm 과 같음)
DECISIONS = ("link", "no", "unsure")             # 연결함 · 연결 안 함 · 잘 모르겠음
MIN_SAME = 3                                     # 띄어쓰기·문장부호 빼고 이만큼 이어서 같아야 "함께 있는 낱말" 로 칠함 ("니다." 같은 끝말은 뺌)
MIN_TYPED = 4                                    # 입력 시각을 찾을 때 쓰는 글 변화의 최소 글자 수 (짧으면 다른 문장에도 들어 있음)
_KEY = re.compile(r"^[0-9a-f]{16}\.[0-9a-f]{16}$")


def _hex(h):
    return h.split(":", 1)[-1][:16]              # 해시는 "sha256:…" 꼴


def key_of(result_text, answer_hash):
    return f"{_hex(sha256_text(result_text))}.{_hex(answer_hash)}"


@bp.get("/confirm")
def page():
    return send_from_directory(S.HERE, "confirm.html")


@bp.post("/local/confirm")
def confirm():
    """form: work_id → 물을 것(AI 답마다 묶음) + 전에 고른 것. 문서는 출처 보기에서 연 것 (없으면 기록된 자리의 최근 문서)"""
    wid = request.form.get("work_id", "")
    r = _물을_것(wid)
    if isinstance(r, tuple):
        return r
    keys = {it["key"] for g in r["groups"] for it in g["items"]}
    if not keys and not os.path.exists(_경로(wid)):
        _쓰기(wid, {})                           # 물을 것이 없는 과제 — 이 화면을 본 것으로 다음 단계(내역서)로 (10/14 · 안 그러면 늘 "출처 보기 전")
    return jsonify(file=r["file"], title=r["title"], groups=r["groups"],
                   decisions={k: v for k, v in _읽기(wid).items() if k in keys}, auto=r["auto"])


def _물을_것(wid):
    """→ {file, title, groups, auto} 또는 (오류 JSON, 코드)"""
    if not S.문서_준비(wid):
        return {"error": "no_file", "message": "출처 보기에서 과제 파일을 먼저 열어 주세요"}, 400
    name, raw = S._파일[wid]
    try:
        paras = read_doc(raw)                           # Word(.docx) · PDF
    except Exception:
        return {"error": "bad_file", "message": "Word(.docx) 파일을 읽지 못했습니다"}, 400
    rec = S.과제_기록(wid)
    if not rec:
        return S.NO_RECORDS
    msgs, events, context, _ = rec
    d = S.build(paras, msgs, events, context)
    return {"file": name, "title": d["title"], "groups": 묶기(d, msgs, context),
            "auto": sum(1 for x in d["sentences"] if x["kind"] in ASK and x.get("paste"))}


# ─────────────── 과제마다 지금 단계 (왼쪽 과제 목록 · ← → 가 쓴다) ───────────────
STEPS = {"source": "/source", "confirm": "/confirm", "report": "/export"}       # 출처 보기 → 연결 확인 → 내역서


def 단계(wid):
    """이 과제가 어디까지 왔나 → "source" · "confirm" · "report"
      내역서를 만들었으면(서버) 내역서 · 연결 확인에서 다 골랐으면 내역서(다음 할 일) · 고르다 말았으면 연결 확인 · 아니면 출처 보기"""
    있나 = S._기록.get("statement_exists")
    if 있나 and 있나(wid):
        return "report"
    고름 = _읽기(wid)
    if not 고름 and not os.path.exists(_경로(wid)):     # 고른 것 파일이 없음 = 연결 확인 화면을 아직 안 봄 (물을 것 0 이면 빈 파일)
        return "source"
    r = _물을_것(wid)
    if isinstance(r, tuple):
        return "confirm"                         # 문서를 못 열어도 고르던 곳으로 (화면이 출처 보기로 안내함)
    남음 = any(it["key"] not in 고름 for g in r["groups"] for it in g["items"])
    return "confirm" if 남음 else "report"


@bp.get("/local/stage")
def stage():
    """위 줄 단계 점을 과제마다 칠하려고: {stage: 지금 할 단계, report_made: 내역서를 만들었나}"""
    wid = request.args.get("work_id", "")
    있나 = S._기록.get("statement_exists")
    return jsonify(stage=단계(wid) if wid else "source", report_made=bool(wid and 있나 and 있나(wid)))


@bp.get("/go")
def go():
    """왼쪽 과제 목록에서 과제를 누르면 → 그 과제의 지금 단계 화면으로"""
    wid = request.args.get("work", "")
    if not wid:
        return redirect("/source")
    if not S._기록["sessions"]().get(wid):                  # 아직 기록이 없는 과제 (새로 만든 과제) → 과제 상세에서 기록 시작
        return redirect(f"/work?work={quote(wid, safe='')}")
    return redirect(f"{STEPS[단계(wid)]}?work={quote(wid, safe='')}")


@bp.post("/local/confirm/decide")
def decide():
    """json: {work_id, set: {키: link | no | unsure | null}} — null 은 고른 것 지우기 (다시 '남은 것' 으로)"""
    b = request.get_json(force=True, silent=True) or {}
    wid, 바꿈 = b.get("work_id") or "", b.get("set")
    if not wid or not isinstance(바꿈, dict) or not 바꿈 \
            or any(not isinstance(k, str) or not _KEY.match(k) or v not in DECISIONS + (None,) for k, v in 바꿈.items()):
        return jsonify(error="bad_request", message="고른 것이 올바르지 않습니다"), 400
    고름 = _읽기(wid)
    for k, v in 바꿈.items():
        if v is None:
            고름.pop(k, None)
        else:
            고름[k] = v
    _쓰기(wid, 고름)
    return jsonify(decisions=고름)


@bp.get("/local/confirm/decisions")
def decisions():
    """내역서 만들기가 읽어 갈 것: {키: link | no | unsure} — 없는 키 = 고르지 않음 ('잘 모르겠음' 과 같게 다룸)"""
    return jsonify(decisions=_읽기(request.args.get("work_id", "")))


# ─────────────── 묶기 · 칠하기 ───────────────
def 묶기(d, msgs, context):
    """source.build 결과 → AI 답마다 [{id, n, tool, model, question, q_ts, a_ts, answer, items}] (답이 나온 시각 순)"""
    기록 = sorted(M.latest_messages(msgs), key=lambda r: r.get("ts", ""))
    답들 = [r for r in 기록 if r.get("role") == "answer"]          # build 와 같은 순서 → x["answer"] 가 이 번호
    글변화 = [(c["ts"], c["text"].strip()) for c in context
            if c.get("kind") == "diff" and len(re.sub(r"\s", "", c.get("text", ""))) >= MIN_TYPED]
    묶음 = {}
    for x in d["sentences"]:
        if x["kind"] not in ASK or x.get("paste") or x.get("answer") is None:
            continue
        a = 답들[x["answer"]]
        g = 묶음.get(x["answer"])
        if g is None:
            q = d["questions"][x["q"]]
            g = 묶음[x["answer"]] = {
                "id": _hex(a["hash"]), "n": q["n"], "tool": a.get("tool") or q["tool"], "model": a.get("model") or q["model"],
                "question": q["question"], "q_ts": q["ts"] if q["question"] else None, "a_ts": a.get("ts", ""),
                "_text": a["text"], "_sents": set(), "items": []}
        입력 = sorted(ts for ts, t in 글변화 if t in x["text"])     # 이 문장 글이 문서에 들어온 시각 (타이핑 조각)
        g["items"].append({"key": key_of(x["text"], a["hash"]), "k": x["k"], "p": x["p"] + 1, "text": x["text"], "kind": x["kind"],
                           "segs": _조각(x["text"], _겹침(x["text"], x.get("ai_text") or "")),
                           "typed": [입력[0], 입력[-1]] if 입력 else None})
        g["_sents"].update(x.get("sents") or ())
    out = sorted(묶음.values(), key=lambda g: g["a_ts"])
    for g in out:
        글들 = "\n".join(it["text"] for it in g["items"])
        g["answer"] = [{"t": p["t"], "on": bool(p["g"]), **({"segs": _조각(p["t"], _겹침(p["t"], 글들))} if p["g"] else {})}
                       for p in S._답_조각(g.pop("_text"), [{"sents": sorted(g.pop("_sents")), "group": "viewed"}])]
    return out


def _겹침(a, b):
    """a 에서 b 와 이어서 같은 곳 [(시작, 끝)] — 글자 단위. 띄어쓰기·문장부호만 같은 곳은 뺀다"""
    if not a or not b:
        return []
    out = []
    for i, _, n in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        s, e = i, i + n
        while s < e and not a[s].strip():
            s += 1
        while e > s and not a[e - 1].strip():
            e -= 1
        if len(re.sub(r"[\W_]", "", a[s:e])) >= MIN_SAME:
            out.append((s, e))
    return out


def _조각(text, 칸):
    """글 + 칠할 곳 → [{"t", "m"}] (m = 함께 있는 낱말)"""
    out, at = [], 0
    for s, e in 칸:
        if s > at:
            out.append({"t": text[at:s], "m": False})
        out.append({"t": text[s:e], "m": True})
        at = e
    if at < len(text):
        out.append({"t": text[at:], "m": False})
    return out


# ─────────────── 고른 것 저장 (이 PC data 폴더) ───────────────
def _경로(wid):
    d = S._기록.get("data_dir")
    if not d:
        raise RuntimeError("data_dir 이 없습니다 (statement.py 의 init)")
    return os.path.join(d(), "confirm-" + re.sub(r"[^\w.-]", "_", wid)[:80] + ".json")


def _읽기(wid):
    if not wid:
        return {}
    try:
        d = safefile.read_json(_경로(wid), {}).get("decisions", {})
        return {k: v for k, v in d.items() if _KEY.match(k) and v in DECISIONS}
    except AttributeError:
        return {}


def _쓰기(wid, 고름):
    safefile.write_json(_경로(wid), {"work_id": wid, "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
                                    "decisions": 고름}, indent=1)        # 쓰다가 꺼져도 예전 파일은 남게 · 읽기와 겹쳐도 (10/14)
