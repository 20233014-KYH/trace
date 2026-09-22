"""
make_sample_proof.py — 화면용 Proof 샘플 생성기. 손으로 짠 이벤트(아래 EVENTS)에 체인 해시를 붙여 derive 를 돌리고
  web/public/sample_session.json  (React 화면 [샘플 · Proof])
을 만든다. 실제 데이터가 아니라 화면 디자인·문구 확인용 임의 시나리오. make_fixture.py 와 같은 방식.

시나리오 (2026-09-22 16:00~16:48, Proof, DB 과제 보고서):
  강의자료 PDF 6분 → Word 보고서 직접 입력 → 위키백과(자료) 복사 85자 → Word 붙여넣기(자료 출처)
  → ChatGPT 4분 → 복사 310자 → Word 붙여넣기(AI 출처 일치) · 문단 6 → 붙여넣은 부분 고치기(삭제 많음 · 되돌리기 2회) → 저장
  → 카카오톡(화이트리스트 밖) → Word → 복사 기록 없는 붙여넣기 60자 → ChatGPT 2분 → 복사 140자 → Word 붙여넣기(AI) → 직접 입력 → 저장 → 종료
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import chain as C          # noqa: E402
from core.derive import derive       # noqa: E402

SID = "sample-proof-0001"
H = lambda s: "sha256:" + hashlib.sha256(s.encode()).hexdigest()
WIKI, AI1, AI2 = H("wiki-85"), H("ai-answer-310"), H("ai-answer-140")
WORD = dict(app="WINWORD.EXE", title="DB과제_보고서.docx - Word", category="work")

def ev(t, **k):
    return {"session_id": SID, "ts": f"2026-09-22T16:{t}+09:00", "source": k.pop("source", "collector"), **k}

def keys(t, n, d, **w):
    return ev(t, type="keys", count=n, deleted=d, app=w.get("app", "WINWORD.EXE"), category=w.get("category", "work"))

EVENTS = [
    ev("00:00", type="session_start", mode="proof", work_id="DB 과제 보고서", idle_after_sec=300),
    ev("00:02", type="window", app="Acrobat.exe", title="5주차_정규화.pdf", category="resource"),
    ev("00:30", type="heartbeat"),
    ev("06:00", type="window", **WORD),
    keys("06:20", 44, 3), keys("07:10", 52, 6), keys("08:05", 48, 4), keys("09:00", 39, 7),
    keys("10:05", 55, 5), ev("11:00", type="undo", app="WINWORD.EXE"), keys("11:10", 41, 9),
    keys("12:05", 47, 3), keys("13:00", 50, 4), keys("14:10", 36, 2),
    ev("15:00", type="window", app="chrome.exe", title="정규화 - 위키백과", category="other"),
    ev("15:01", type="tab", domain="ko.wikipedia.org", category="resource", title="정규화 - 위키백과"),
    ev("18:00", type="copy", len=85, hash=WIKI, app="chrome.exe", category="resource"),
    ev("18:30", type="window", **WORD),
    ev("18:40", type="paste", len=85, hash=WIKI, app="WINWORD.EXE", target_title="DB과제_보고서.docx - Word"),
    ev("18:42", type="doc_paste_at", app="Word", file="DB과제_보고서.docx", where="문단 3"),
    keys("19:10", 42, 5), keys("20:05", 46, 3), keys("21:00", 38, 6), keys("22:10", 51, 4), keys("23:05", 33, 2),
    ev("24:00", type="window", app="chrome.exe", title="ChatGPT", category="ai"),
    ev("24:01", type="tab", domain="chatgpt.com", category="ai", title="ChatGPT"),
    ev("27:20", type="copy", len=310, hash=AI1, app="chrome.exe", category="ai"),
    ev("28:00", type="window", **WORD),
    ev("28:05", type="paste", len=310, hash=AI1, app="WINWORD.EXE", target_title="DB과제_보고서.docx - Word"),
    ev("28:07", type="doc_paste_at", app="Word", file="DB과제_보고서.docx", where="문단 6"),
    ev("28:10", type="doc_change", app="Word", file="DB과제_보고서.docx", where="문단 6", added=310, removed=0),
    keys("29:10", 22, 18), ev("29:40", type="undo", app="WINWORD.EXE"), keys("30:05", 31, 24),
    keys("31:00", 28, 15), ev("31:30", type="undo", app="WINWORD.EXE"), keys("32:10", 35, 9),
    keys("33:05", 44, 5), keys("34:00", 40, 3), keys("35:10", 29, 4),
    ev("35:50", type="doc_change", app="Word", file="DB과제_보고서.docx", where="문단 6", added=96, removed=71),
    ev("36:00", type="doc_save", app="Word", file="DB과제_보고서.docx", chars=2140, words=430, paragraphs=7),
    ev("36:10", type="window", app="KakaoTalk.exe", title="", category="other"),
    keys("36:40", 20, 2, app="KakaoTalk.exe", category="other"),
    ev("38:00", type="window", **WORD),
    keys("38:20", 37, 4), keys("39:10", 45, 6), keys("40:05", 41, 3),
    ev("41:00", type="paste", len=60, hash=H("unknown-source"), app="WINWORD.EXE", target_title="DB과제_보고서.docx - Word"),  # 복사 기록 없음
    ev("42:00", type="window", app="chrome.exe", title="ChatGPT", category="ai"),
    ev("42:01", type="tab", domain="chatgpt.com", category="ai", title="ChatGPT"),
    ev("43:40", type="copy", len=140, hash=AI2, app="chrome.exe", category="ai"),
    ev("44:00", type="window", **WORD),
    ev("44:05", type="paste", len=140, hash=AI2, app="WINWORD.EXE", target_title="DB과제_보고서.docx - Word"),
    ev("44:07", type="doc_paste_at", app="Word", file="DB과제_보고서.docx", where="문단 7"),
    keys("45:00", 34, 7), keys("46:05", 48, 4), keys("47:00", 30, 2),
    ev("47:40", type="doc_save", app="Word", file="DB과제_보고서.docx", chars=2610, words=520, paragraphs=8),
    ev("48:00", type="session_end"),
]


def main():
    prev = C.GENESIS
    rows = []
    for i, e in enumerate(EVENTS, 1):
        e = {"id": f"evt_{i:06d}", **e}
        if C.in_chain(e):
            prev = C.next_hash(prev, e)
            e["h"] = prev
        rows.append(e)
    out = derive(rows)
    out["mode"] = "proof"
    out["work_id"] = "DB 과제 보고서"
    path = os.path.join(os.path.dirname(HERE), "web", "public", "sample_session.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    s = out["stats"]
    print(f"→ {path}")
    print(f"events {len(rows)}  chain {s['events']}  root {out['root'][:16]}…  flow {len(out['flow'])}")
    print(f"typed {s['typed']} ({s['typed_pct']}%)  pasted {s['pasted']} ({s['pasted_pct']}%)  ai {s['pasted_ai']}  undo {s['undo']}  pauses {s['pauses']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
