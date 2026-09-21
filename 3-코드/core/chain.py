"""
chain.py — 해시 체인. 수집기(PC) · derive.py · 서버(dev_receiver / A의 Backend)가 전부 이 함수를 쓴다.
같은 이벤트에서 같은 해시가 나와야 "양쪽에서 만들고 대조"가 성립한다. 여기 말고 다른 데서 해시를 계산하지 말 것.

  hᵢ = SHA256( hᵢ₋₁ ‖ "|" ‖ ts ‖ "|" ‖ type ‖ "|" ‖ summary(event) )
  h₀ = "0" × 64

heartbeat 는 체인에 넣지 않는다 (공백 계산용일 뿐, 5초마다 생기는 잡음).
summary 에는 내용이 없다 — 앱·제목·횟수·길이·해시만.
"""
import hashlib

GENESIS = "0" * 64
SKIP = {"heartbeat"}


def in_chain(e: dict) -> bool:
    return e.get("type") not in SKIP


def summary(e: dict) -> str:
    """체인에 들어가는 한 줄 요약. 이벤트 필드가 바뀌면 여기도 같이 바뀌어야 한다(계약 ①)."""
    t = e.get("type", "")
    if t == "window":
        return f"{e.get('app','')} · {e.get('title','')}".rstrip(" ·")
    if t in ("copy", "paste"):
        return f"{e.get('len',0)}자 · {(e.get('hash') or '')[:19]}… · {e.get('app','')}"
    if t == "keys":
        return f"입력 {e.get('count',0)}자 · 삭제 {e.get('deleted',0)}자 · {e.get('app','')}"
    if t == "file":
        return f"{e.get('action','')} · {e.get('path','')} · {(e.get('content_hash') or '')[:19]}"
    if t == "commit":
        return f"{e.get('repo','')} · {e.get('hash','')} · {e.get('branch','')} · {e.get('files',0)}파일 · +{e.get('added',0)} · -{e.get('removed',0)}"
    if t == "git_push":
        return f"{e.get('repo','')} · {e.get('remote_ref','')} · {e.get('hash','')}"
    if t in ("undo", "redo", "cut"):
        return {"undo": "되돌리기 (Ctrl+Z)", "redo": "다시 실행 (Ctrl+Y)", "cut": "잘라내기 (Ctrl+X)"}[t]
    if t == "tab":
        return f"{e.get('domain','')} · {e.get('category','')}"
    if t == "doc_change":
        return f"{e.get('app','')} · {e.get('file','')} · {e.get('where','')} · +{e.get('added',0)} · -{e.get('removed',0)}"
    if t == "doc_paste_at":
        return f"{e.get('app','')} · {e.get('file','')} · {e.get('where','')}"
    if t == "doc_save":
        return f"{e.get('app','')} · {e.get('file','')} · " + " · ".join(f"{k}={e.get(k)}" for k in ("chars", "words", "slides") if k in e)
    if t == "session_start":
        return f"세션 시작 · {e.get('mode','')}"
    if t == "session_end":
        return "세션 종료"
    if t in ("idle_start", "idle_end"):
        return t
    return ""


def next_hash(prev: str, e: dict) -> str:
    return hashlib.sha256(f"{prev}|{e['ts']}|{e['type']}|{summary(e)}".encode("utf-8")).hexdigest()


def build(events):
    """이벤트 목록 → (rows, root). rows = [ts, type, summary, prev, hash]. 이벤트의 'h' 필드는 무시하고 다시 계산한다."""
    prev, rows = GENESIS, []
    for e in events:
        if not in_chain(e):
            continue
        h = next_hash(prev, e)
        rows.append([e["ts"][11:19], e["type"], summary(e), prev, h])
        prev = h
    return rows, prev


def verify(events):
    """이벤트에 붙어 온 'h' 와 재계산이 전부 같은지. (ok, 첫 불일치 이벤트 id 또는 None)"""
    prev = GENESIS
    for e in events:
        if not in_chain(e):
            continue
        h = next_hash(prev, e)
        if e.get("h") and e["h"] != h:
            return False, e.get("id")
        prev = h
    return True, None
