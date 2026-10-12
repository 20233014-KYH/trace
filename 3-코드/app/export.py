"""
export.py — 학생 PC 의 "내역서 내보내기" 화면 (캔버스 7 · 10/12 박상진)

  python app/statement.py  →  http://127.0.0.1:5079/export?work=<과제 id>   (연결 확인 다음 단계 · 같은 작은 서버)

왼쪽 = 교수에게 보이는 PDF 1장 미리 보기. 서버와 같은 코드(server/statement_pdf.py)로 이 PC 에서 그린다 → 받을 PDF 와 같다.
오른쪽 = 고칠 것 넷:
  ① 학생 설명 — 질문 두 칸 (각 150자) · 비우면 "학생이 쓰지 않음"
  ② QR 링크에 넣을 것 — 지금 서버가 주는 것 (내역서 · 학생이 연결한 질문·답). 출처 보기 · 작업 과정은 서버 준비 뒤
  ③ 가리기 — 보낼 질문·답에서 전화번호 · 이메일 · 주민번호 · 카드번호 · API 키 모양을 **규칙으로** 찾는다 (AI 안 씀)
             찾기만 하고 정하는 건 학생. 질문은 기본 가림 · 답을 가리면 그 연결은 내역서에서 빠짐 (기본 안 가림)
  ④ 링크 기간 — 7 · 14 · 30일
[PDF 내려받기] = 서버에 내역서를 만들고(POST /works/<id>/statements) 링크를 받아(POST /statements/<id>/share) PDF 를 연다.

서버로 가는 것 (statement.py /local/statement 와 같은 원칙):
  · 붙여넣기 기록으로 확실한 연결 + 연결 확인에서 "연결함" → confirmed · 원문(답 · 안 가린 질문 · 결과물 문장)
  · "연결 안 함" → rejected · 해시와 위치만
  · "잘 모르겠음" · 안 고름 → 보내지 않음
  · 가린 질문·답 → 어느 이벤트인지만 (원문 안 감)
고쳐 쓰는 중인 것(설명 · 가리기 · 기간)은 이 PC data/export-<과제>.json 에 둔다.
★ 점수·퍼센트 없음.
"""
import glob
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta

from flask import Blueprint, Response, jsonify, request, send_from_directory

from core import match as M
from core.docx import read_docx
from core.summary import work_summary
from core.texthash import sha256_text
import confirm as CF
import source as S

bp = Blueprint("export", __name__)
설명_최대 = 150
기간들 = (7, 14, 30)
ASK = CF.ASK

# 가리기 — 모양으로 찾는 것만 (AI 안 씀 · 틀리지 않고 매번 같음 · 원문이 PC 밖으로 안 나감)
# 기록기가 저장 전에 쓰는 규칙과 같다 (collector/mask.py) — 그 전에 기록된 글이나 규칙이 놓친 글을 여기서 다시 찾는다
sys.path.insert(0, os.path.join(os.path.dirname(S.HERE), "collector"))
from mask import spans as 가릴_자리                     # noqa: E402


def 민감(text):
    """글 → [(종류, 개수)] — 찾은 것만"""
    n = {}
    for _, _, k in 가릴_자리(text):
        n[k] = n.get(k, 0) + 1
    return list(n.items())


def _둘레(text, n=120):
    """가린 자리가 보이게 그 둘레만 (화면 한 줄용)"""
    i = text.find("⟦가림")
    a = max(0, i - 40) if i >= 0 else 0
    return ("…" if a else "") + text[a:a + n] + ("…" if a + n < len(text) else "")


def 가린_글(text):
    """찾은 자리만 ⟦가림:종류⟧ 로 (서버가 저장하는 글과 같게)"""
    for a, b, k in sorted(가릴_자리(text), reverse=True):
        text = text[:a] + f"⟦가림:{k}⟧" + text[b:]
    return text


@bp.get("/export")
def page():
    return send_from_directory(S.HERE, "export.html")


@bp.post("/local/export")
def export():
    """form: work_id → 화면에 필요한 것: 고쳐 쓰는 중인 것 · 보낼 질문·답 · 가리기 후보 · 숫자 · 로그인 · 마지막으로 만든 링크"""
    wid = request.form.get("work_id", "")
    r = _모으기(wid)
    if isinstance(r, tuple):
        return r
    초안 = _읽기(wid)
    가림 = _가림(r, 초안)
    일부 = _일부(r, 초안)
    보냄 = _보냄(r, 초안)
    흐름 = _흐름(r, 초안)
    a = _auth()
    이름 = {k: n for k, n, _ in 쓰임새}
    return jsonify(
        file=r["file"], title=r["title"], logged_in=bool(a.get("token")),
        draft={"explain_use": 초안.get("explain_use", ""), "explain_check": 초안.get("explain_check", ""),
               "days": 초안.get("days", 14)},
        found=[{"id": m["id"], "role": m["role"], "tool": m["tool"], "n": m["n"],
                "what": " · ".join(f"{이름} {n}개" for 이름, n in m["found"]), "hidden": m["id"] in 가림,
                "masked": m["id"] in 일부, "preview": _둘레(가린_글(m["text"]))}
               for m in 보냄 if m["found"]],
        questions=[{"id": m["id"], "tool": m["tool"], "n": m["n"], "text": m["text"][:120], "hidden": m["id"] in 가림}
                   for m in 보냄 if m["role"] == "question"],
        # v3 ② 대표 질문 고르기 — 이 과제의 질문 전부 (시간 순) · ① 쓰임새 숫자
        flow=[{"id": q["id"], "tool": q["tool"], "n": q["n"], "usage": 이름[q["usage"]],
               "text": (가린_글(q["text"]) if q["found"] and (초안.get("mask") or {}).get(q["id"], True) else q["text"])[:120],
               "used": q["used"], "picked": q["id"] in 흐름 and q["id"] not in 가림, "hidden": q["id"] in 가림}
              for q in r["questions"]],
        usage=[{"name": n, "count": r["usage_counts"][k]} for k, n, _ in 쓰임새],
        counts={"confirmed": len(r["confirmed"]), "rejected": len(r["rejected"]), "unsure": r["unsure"],
                "auto": sum(1 for l in r["confirmed"] if l["origin"] == "auto"),
                "questions": sum(1 for m in 보냄 if m["role"] == "question"),
                "hidden": len(가림), "masked": len(일부), "dropped": sum(1 for l in r["confirmed"] if l["answer_id"] in 가림)},
        made=(초안.get("made") or {}).get("url") and {k: 초안["made"][k] for k in ("url", "pdf_url", "expires_at", "at")} or None)


@bp.post("/local/export/draft")
def save_draft():
    """json: {work_id, explain_use?, explain_check?, days?, hide?: {이벤트 id: true|false}} — 고쳐 쓰는 중인 것 저장"""
    b = request.get_json(force=True, silent=True) or {}
    wid = b.get("work_id") or ""
    if not wid:
        return jsonify(error="bad_request", message="과제가 필요합니다"), 400
    초안 = _읽기(wid)
    for k in ("explain_use", "explain_check"):
        if k in b:
            if not isinstance(b[k], str) or len(b[k].strip()) > 설명_최대:
                return jsonify(error="bad_request", message=f"{설명_최대}자까지 쓸 수 있어요"), 400
            초안[k] = b[k]
    if "days" in b:
        if b["days"] not in 기간들:
            return jsonify(error="bad_request", message="링크 기간은 7 · 14 · 30일 중 하나예요"), 400
        초안["days"] = b["days"]
    if "hide" in b:
        if not isinstance(b["hide"], dict) or not all(isinstance(k, str) and isinstance(v, bool) for k, v in b["hide"].items()):
            return jsonify(error="bad_request", message="가리기가 올바르지 않습니다"), 400
        초안.setdefault("hide", {}).update(b["hide"])
    if "mask" in b:                                             # 찾은 개인 정보 — 그 부분만 가릴지 (이벤트 id: true|false)
        if not isinstance(b["mask"], dict) or not all(isinstance(k, str) and isinstance(v, bool) for k, v in b["mask"].items()):
            return jsonify(error="bad_request", message="가리기가 올바르지 않습니다"), 400
        초안.setdefault("mask", {}).update(b["mask"])
    if "flow" in b:                                             # v3 ② 대표 질문 — 이벤트 id 목록 (최대 3)
        if not isinstance(b["flow"], list) or len(b["flow"]) > 3 or not all(isinstance(x, str) for x in b["flow"]):
            return jsonify(error="bad_request", message="대표 질문은 3개까지 고를 수 있어요"), 400
        초안["flow"] = b["flow"]
    _쓰기(wid, 초안)
    return jsonify(ok=True)


@bp.get("/local/export/preview")
def preview():
    """교수에게 보이는 PDF 1장 — 서버와 같은 코드로 이 PC 에서. 링크·QR 은 아직 없으니 자리만"""
    wid = request.args.get("work_id", "")
    r = _모으기(wid)
    if isinstance(r, tuple):
        return r
    초안 = _읽기(wid)
    d = _미리_보기(wid, r, 초안)
    pdf = _pdf().render(d, (초안.get("made") or {}).get("url") or "링크는 PDF 를 내려받을 때 만들어집니다")
    return Response(pdf, mimetype="application/pdf", headers={"Cache-Control": "no-store",      # 주소로 열어도 내려받기 말고 화면에
                                                              "Content-Disposition": 'inline; filename="preview.pdf"'})


@bp.post("/local/export/make")
def make():
    """서버에 내역서 만들기 → 링크 받기. 바뀐 게 없으면 전에 만든 링크를 그대로 준다 (내역서가 쌓이지 않게)"""
    wid = request.form.get("work_id", "") or (request.get_json(silent=True) or {}).get("work_id", "")
    if not _auth().get("token"):
        return jsonify(error="login", message="로그인해야 링크와 PDF 를 만들 수 있어요"), 401
    r = _모으기(wid)
    if isinstance(r, tuple):
        return r
    초안 = _읽기(wid)
    body = _보낼_것(r, 초안)
    days = 초안.get("days", 14)
    서명 = hashlib.sha256(json.dumps([body, days], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    전 = 초안.get("made") or {}
    if 전.get("sig") == 서명 and 전.get("expires_at", "") > datetime.now().astimezone().isoformat():
        return jsonify(**{k: 전[k] for k in ("url", "pdf_url", "expires_at", "at")}, reused=True)
    if not body["links"]:
        return jsonify(error="empty", message="내역서에 넣을 연결이 없어요. 연결 확인에서 하나 이상 연결해 주세요"), 400
    서버 = S._기록["server"]
    코드, st = 서버("POST", f"/works/{wid}/statements", json=body)
    if 코드 != 201:
        return jsonify(st), 코드
    코드, sh = 서버("POST", f"/statements/{st['id']}/share", json={"expires_in_days": days})
    if 코드 != 201:
        return jsonify(sh), 코드
    초안["made"] = {"sig": 서명, "statement_id": st["id"], "url": sh["url"], "pdf_url": sh["pdf_url"],
                  "expires_at": sh["expires_at"], "at": datetime.now().astimezone().isoformat(timespec="seconds")}
    _쓰기(wid, 초안)
    if S._기록.get("made"):
        S._기록["made"](wid)
    return jsonify(**{k: 초안["made"][k] for k in ("url", "pdf_url", "expires_at", "at")},
                   verified=st.get("verified"), problems=st.get("problems", []), reused=False)


@bp.post("/local/export/revoke")
def revoke():
    """마지막으로 만든 링크 끊기 (서버 DELETE /shares/<토큰>) — 교수가 더는 못 엶. 내려받은 PDF 의 QR 도 안 열림"""
    wid = (request.get_json(silent=True) or {}).get("work_id", "")
    초안 = _읽기(wid)
    url = (초안.get("made") or {}).get("url") or ""
    if not url:
        return jsonify(error="none", message="끊을 링크가 없어요"), 400
    코드, 답 = S._기록["server"]("DELETE", f"/shares/{url.rstrip('/').rsplit('/', 1)[-1]}")
    if 코드 != 200:
        return jsonify(답), 코드
    초안.pop("made", None)
    _쓰기(wid, 초안)
    return jsonify(ok=True)


# ─────────────── 모으기: 문장마다 연결 + 연결 확인에서 고른 것 ───────────────
def _모으기(wid):
    """→ {file, title, confirmed, rejected, unsure, sent, msgs, events, sessions} 또는 (오류, 코드)
    연결 = statement.py /local/analyze 와 같은 규칙: 표시 exact · similar · edited · viewed 이고 AI 답이 있는 문장"""
    if not S.문서_준비(wid):
        return {"error": "no_file", "message": "출처 보기에서 과제 파일을 먼저 열어 주세요"}, 400
    name, raw = S._파일[wid]
    # 문서 · 기록 · 연결 확인에서 고른 것이 그대로면 전에 분석한 것을 다시 쓴다 — 학생 설명을 칠 때마다 다시 분석하지 않게
    # (분석 0.4초가 미리 보기 대부분 · 10/12)
    표 = (hashlib.sha1(raw).hexdigest(), json.dumps(CF._읽기(wid), sort_keys=True),
         tuple((p, os.path.getsize(p), os.path.getmtime(p)) for p in sorted(glob.glob(os.path.join(S._기록["data_dir"](), "*.jsonl")))))
    if _분석.get(wid, (None,))[0] == 표:
        return _분석[wid][1]
    try:
        paras = read_docx(io.BytesIO(raw))
    except Exception:
        return {"error": "bad_file", "message": "Word(.docx) 파일을 읽지 못했습니다"}, 400
    rec = S.과제_기록(wid)
    if not rec:
        return S.NO_RECORDS
    msgs, events, context, 세션 = rec
    d = S.build(paras, msgs, events, context)
    기록 = sorted(M.latest_messages(msgs), key=lambda m: m.get("ts", ""))
    답들 = [m for m in 기록 if m.get("role") == "answer"]
    질문들 = [m for m in 기록 if m.get("role") == "question"]
    번호 = {}                                                   # 메시지 → 도구별 번호 (화면 "ChatGPT 질문 2")
    for m in 기록:
        k = (m.get("tool") or "AI", m.get("role"))
        번호[_id(m)] = 번호.get(k, 0) + 1
        번호[k] = 번호[_id(m)]

    def 질문(a):                                               # statement.py · source.build 와 같은 규칙
        앞 = [q for q in 질문들 if q["session_id"] == a["session_id"] and q.get("tool") == a.get("tool")
              and q.get("ts", "") <= a.get("ts", "")]
        return 앞[-1] if 앞 else None

    고름 = CF._읽기(wid)
    confirmed, rejected, unsure = [], [], 0
    for x in d["sentences"]:
        if x["kind"] not in ASK or x.get("answer") is None:
            continue
        a = 답들[x["answer"]]
        if x.get("paste"):
            결정, origin = "confirmed", "auto"
        else:
            g = 고름.get(CF.key_of(x["text"], a["hash"]))
            결정, origin = {"link": "confirmed", "no": "rejected"}.get(g), "suggested"
        if not 결정:
            unsure += 1
            continue
        q = 질문(a)
        l = {"answer": a, "question": q, "answer_id": _id(a), "question_id": _id(q) if q else None,
             "text": x["text"], "paragraph": x["p"] + 1, "kind": x["kind"], "origin": origin, "file": name}
        (confirmed if 결정 == "confirmed" else rejected).append(l)

    def 칸(m):
        return {"id": _id(m), "role": m["role"], "tool": m.get("tool") or "AI", "n": 번호[_id(m)],
                "text": m["text"], "ts": m.get("ts", ""), "found": 민감(m["text"]), "msg": m}

    보냄 = {}                                                   # 원문이 서버로 갈 수 있는 것 = 연결함 의 답 · 질문 (+ 학생이 고른 대표 질문)
    for l in confirmed:
        for m in (l["answer"], l["question"]):
            if m and _id(m) not in 보냄:
                보냄[_id(m)] = 칸(m)
    쓰인질문 = {l["question_id"] for l in confirmed if l["question_id"]}
    질문칸 = [{**칸(q), "usage": 쓰임(q["text"]), "used": _id(q) in 쓰인질문} for q in 질문들]   # v3 ① ② — 이 과제의 질문 전부
    종류 = [x["kind"] for x in d["sentences"]]
    결과수 = {"total": len(종류), "ai": 종류.count("exact") + 종류.count("similar"),       # 내역서 v3 ③ — 출처 보기와 같은 묶음
              "other": 종류.count("web") + 종류.count("noproc"), "edited": 종류.count("edited"),
              "viewed": 종류.count("viewed"), "none": 종류.count("none")}
    r = {"file": name, "title": d["title"], "confirmed": confirmed, "rejected": rejected, "unsure": unsure,
         "result_counts": 결과수, "questions": 질문칸,
         "usage_counts": {k: sum(1 for q in 질문칸 if q["usage"] == k) for k, _, _ in 쓰임새},
         "sent_base": 보냄, "events": events, "sessions": 세션}
    _분석[wid] = (표, r)
    return r


_분석 = {}           # work_id → (문서·기록·고른 것 표, 분석 결과)


def _id(m):
    return f"{m['session_id']}/{m['event_id']}"


# ─────────────── v3 ① 쓰임새 — 질문 글을 낱말 규칙으로 나눈다 (AI 안 씀 · 숫자만 서버로) ───────────────
# 앞에서부터 처음 맞는 것. 아무것도 안 맞으면 이해·설명. (키, 이름, 낱말들)
쓰임새 = [
    ("review", "내 코드 검토", ("내 코드", "내가 짠", "내가 쓴 코드", "맞는지", "검토", "리뷰", "피드백", "에러", "오류", "버그", "디버", "왜 안 돼", "왜 안되")),
    ("polish", "다듬기", ("다듬", "고쳐 줘", "고쳐줘", "수정해", "맞춤법", "자연스럽", "매끄럽", "줄여", "늘려", "번역", "어색")),
    ("write", "글·코드 작성", ("써줘", "써 줘", "작성해", "작성 해", "만들어줘", "만들어 줘", "짜줘", "짜 줘", "초안", "페이지짜리",
                             "보고서 써", "구현해", "코드 줘")),
    ("find", "자료·예시 찾기", ("사례", "예시", "예를 들", "자료", "찾아", "출처", "논문", "통계", "기사", "추천")),
    ("understand", "이해·설명", ()),
]


def 쓰임(text):
    t = (text or "").lower()
    return next((k for k, _, 낱말 in 쓰임새 if any(w in t for w in 낱말)), "understand")


def _흐름(r, 초안):
    """v3 ② 질문 흐름 — 학생이 고른 대표 질문 id (최대 3 · 시간 순). 안 골랐으면 결과물에 글이 들어간 질문 앞에서 3개
    (개인 정보는 그 부분만 가려서 보내므로 그런 질문도 고를 수 있다)"""
    있는 = {q["id"]: q for q in r["questions"]}
    고른 = 초안.get("flow")
    if not isinstance(고른, list):
        고른 = [q["id"] for q in r["questions"] if q["used"]][:3]
    return [q["id"] for q in r["questions"] if q["id"] in set(고른) and q["id"] in 있는][:3]


def _보냄(r, 초안):
    """원문이 서버로 갈 수 있는 것 = 연결함의 답 · 질문 + 학생이 대표로 고른 질문 (시간 순)"""
    out = dict(r["sent_base"])
    for qid in _흐름(r, 초안):
        out.setdefault(qid, next(q for q in r["questions"] if q["id"] == qid))
    return sorted(out.values(), key=lambda m: m["ts"])


def _가림(r, 초안):
    """통째로 가릴 이벤트 id 들 — 학생이 직접 고른 것만 (10/12: 개인 정보가 찾아지면 통째로가 아니라 그 부분만 가림 → _일부)"""
    고른 = 초안.get("hide") or {}
    return {m["id"] for m in _보냄(r, 초안) if 고른.get(m["id"], False)}


def _일부(r, 초안):
    """그 부분만 가릴 이벤트 id 들 — 개인 정보가 찾아진 글 (기본 켬 · 학생이 끌 수 있음 · 통째로 가린 건 빼고)"""
    고른 = 초안.get("mask") or {}
    통째 = _가림(r, 초안)
    return {m["id"] for m in _보냄(r, 초안) if m["found"] and m["id"] not in 통째 and 고른.get(m["id"], True)}


def _보낼_것(r, 초안):
    """서버 POST /works/<id>/statements 몸통. 답을 가린 연결은 빠진다 (원문 없이 '맞다'를 보내면 서버가 확인을 못 함)"""
    가림 = _가림(r, 초안)
    messages, links = {}, []
    for l in r["confirmed"]:
        if l["answer_id"] in 가림:
            continue
        a, q = l["answer"], l["question"]
        messages[l["answer_id"]] = a
        q_보냄 = q is not None and l["question_id"] not in 가림
        if q_보냄:
            messages[l["question_id"]] = q
        links.append({"answer_hash": a["hash"], "question_hash": q["hash"] if q_보냄 else None,
                      "result_hash": sha256_text(l["text"]), "result_text": l["text"],
                      "location": {"file": l["file"], "paragraph": l["paragraph"]},
                      "kind": l["kind"], "origin": l["origin"], "decision": "confirmed"})
    for l in r["rejected"]:                                     # 아니다 — 원문 없이 해시·위치만
        links.append({"answer_hash": l["answer"]["hash"], "result_hash": sha256_text(l["text"]),
                      "location": {"file": l["file"], "paragraph": l["paragraph"]},
                      "kind": l["kind"], "origin": l["origin"], "decision": "rejected"})
    흐름 = []                                                   # v3 ② 학생이 고른 대표 질문 — 원문을 같이 보낸다 (가린 질문은 뺌)
    for qid in _흐름(r, 초안):
        if qid in 가림:
            continue
        q = next(x for x in r["questions"] if x["id"] == qid)
        messages[qid] = q["msg"]
        흐름.append({"session_id": q["msg"]["session_id"], "event_id": q["msg"]["event_id"], "usage": q["usage"], "used": q["used"]})
    일부 = _일부(r, 초안)
    return {"explain_use": (초안.get("explain_use") or "").strip()[:설명_최대] or None,
            "explain_check": (초안.get("explain_check") or "").strip()[:설명_최대] or None,
            "messages": [{"session_id": m["session_id"], "event_id": m["event_id"], "text": m["text"],
                          "model": m.get("model") or None,
                          **({"mask": [list(x) for x in 가릴_자리(m["text"])]} if i in 일부 else {})}
                         for i, m in messages.items()],
            "links": links, "result_counts": r["result_counts"],                  # 숫자만 (문장 원문 아님)
            "usage_counts": r["usage_counts"], "flow": 흐름,                      # v3 ① 숫자만 · ② 고른 질문
            "redactions": [{"session_id": i.split("/", 1)[0], "event_id": i.split("/", 1)[1]} for i in sorted(가림)]}


def _미리_보기(wid, r, 초안):
    """server app._내역서_내용(교수용) 과 같은 모양 — 숫자는 이 PC 의 같은 체인 이벤트로 센다 (core/summary)"""
    body = _보낼_것(r, 초안)
    원문 = {m["hash"]: m for l in r["confirmed"] for m in (l["answer"], l["question"]) if m}
    원문id = {_id(m): m for l in r["confirmed"] for m in (l["answer"], l["question"]) if m}
    원문id.update({q["id"]: q["msg"] for q in r["questions"]})          # 대표 질문 (연결 없는 질문일 수 있음)

    일부 = _일부(r, 초안)

    def 보일(m):
        return 가린_글(m["text"]) if _id(m) in 일부 else m["text"]

    def 글(h):
        m = 원문.get(h) if h else None
        return {"text": 보일(m), "tool": m.get("tool"), "model": m.get("model"), "ts": m.get("ts"),
                "history": bool(m.get("history")), "ok": True} if m else None

    도구 = {}
    for m in body["messages"]:
        x = 원문id[f"{m['session_id']}/{m['event_id']}"]
        도구.setdefault(x.get("tool") or "AI", set())
        if x.get("model"):
            도구[x.get("tool") or "AI"].add(x["model"])
    세션별 = {}
    for e in r["events"]:
        세션별.setdefault(e["session_id"], []).append(e)
    요약 = work_summary([({"id": sid, "sealed": any(e.get("type") == "session_end" for e in evs), "verified": True}, evs)
                        for sid, evs in 세션별.items()])
    a = _auth()
    지금 = datetime.now().astimezone()
    return {"id": "미리보기", "created_at": 지금.isoformat(timespec="seconds"), "ai_scope": None,
            "explain_use": body["explain_use"], "explain_check": body["explain_check"],
            "tools": [{"tool": t, "models": sorted(ms)} for t, ms in 도구.items()],
            "verified": True, "problems": [], "summary": 요약, "result_counts": body["result_counts"],
            "usage_counts": body["usage_counts"],
            "flow": [{**{k: f[k] for k in ("usage", "used")}, "text": 보일(원문id[f"{f['session_id']}/{f['event_id']}"]),
                      "tool": 원문id[f"{f['session_id']}/{f['event_id']}"].get("tool"), "ok": True} for f in body["flow"]],
            "links": [{"question": 글(l.get("question_hash")), "answer": 글(l["answer_hash"]),
                       "result": {"text": l["result_text"], "location": l["location"]}, "kind": l["kind"], "origin": l["origin"]}
                      for l in body["links"] if l["decision"] == "confirmed"],
            "rejected": sum(l["decision"] == "rejected" for l in body["links"]), "redacted": len(body["redactions"]),
            "work": {"title": _과제_이름(wid) or r["title"] or wid}, "author": (a.get("user") or {}).get("name"),
            "expires_at": (지금 + timedelta(days=초안.get("days", 14))).isoformat(timespec="seconds")}


_이름 = {}


def _과제_이름(wid):
    """서버의 과제 이름 (로그인했을 때만 · 한 번 받으면 기억). 없으면 None → 문서 제목"""
    if wid not in _이름 and _auth().get("token") and S._기록.get("server"):
        코드, w = S._기록["server"]("GET", f"/works/{wid}")
        if 코드 == 200:
            _이름[wid] = w.get("title")
    return _이름.get(wid)


def _auth():
    f = S._기록.get("auth")
    return (f() if f else {}) or {}


_PDF = None


def _pdf():
    """server/statement_pdf.py 를 그대로 — 교수가 받을 PDF 와 같게 (reportlab · Pretendard 는 처음 그릴 때만 읽음)"""
    global _PDF
    if _PDF is None:
        sys.path.insert(0, os.path.join(os.path.dirname(S.HERE), "server"))
        import statement_pdf
        _PDF = statement_pdf
    return _PDF


# ─────────────── 고쳐 쓰는 중인 것 (이 PC data 폴더) ───────────────
def _경로(wid):
    return os.path.join(S._기록["data_dir"](), "export-" + re.sub(r"[^\w.-]", "_", wid)[:80] + ".json")


def _읽기(wid):
    try:
        with open(_경로(wid), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _쓰기(wid, d):
    p = _경로(wid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
