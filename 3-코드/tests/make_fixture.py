"""
make_fixture.py — 픽스처 생성기. 손으로 짠 이벤트(아래 EVENTS)에 체인 해시를 붙여
  fixtures/events_basic.jsonl   (계약 ① · 서버가 받는 그대로)
  fixtures/expected_basic.json  (계약 ② · derive 결과 골든)
를 만든다. 이벤트를 바꿨으면 이 파일을 다시 실행하고, 골든이 바뀐 이유를 커밋 메시지에 적는다.

시나리오 (2026-09-22 14:00~14:20, Learn, Java 과제):
  강의자료 PDF 5분 → VS Code 입력 → 오류 → Chrome 에서 chatgpt.com (확장 tab) → 복사 200자
  → VS Code 붙여넣기(AI 출처 일치) → 직접 수정 · 되돌리기 → 저장 → docs.oracle.com (확장 tab)
  → 카카오톡(화이트리스트 밖) → 탐색기 복사 14자 → VS Code 붙여넣기(일치, AI 아님)
  → 복사 기록 없는 붙여넣기(다른 기기) → Word: AI 복사 120자 붙여넣기 → 문단 4 +120자 → 직접 수정 → 저장 → 유휴 → 종료
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import chain as C          # noqa: E402
from core.derive import derive       # noqa: E402

SID = "fixture-basic-0001"
H = lambda s: "sha256:" + hashlib.sha256(s.encode()).hexdigest()
AI = H("ai-answer-200")
MINE = H("my-own-14")

def ev(t, **k):
    return {"session_id": SID, "ts": f"2026-09-22T14:{t}+09:00", "source": k.pop("source", "collector"), **k}

EVENTS = [
    ev("00:00", type="session_start", mode="learn", work_id="W_fixture", idle_after_sec=300),
    ev("00:01", type="window", app="Acrobat.exe", title="3주차_예외처리.pdf", category="resource"),
    ev("00:30", type="heartbeat"),
    ev("05:00", type="window", app="Code.exe", title="Main.java - java-hw2", category="work"),
    ev("05:10", type="keys", count=42, deleted=5, app="Code.exe", category="work"),
    ev("05:20", type="keys", count=38, deleted=3, app="Code.exe", category="work"),
    ev("06:10", type="keys", count=51, deleted=9, app="Code.exe", category="work"),
    ev("06:40", type="undo", app="Code.exe"),
    ev("07:00", type="window", app="chrome.exe", title="ChatGPT", category="ai"),          # 창 제목 키워드 → ai
    ev("07:01", type="tab", domain="chatgpt.com", category="ai", title="ChatGPT"),         # 확장이 도메인으로 확정
    ev("09:30", type="copy", len=200, hash=AI, app="chrome.exe", category="ai"),
    ev("09:40", type="window", app="Code.exe", title="Main.java - java-hw2", category="work"),
    ev("09:42", type="paste", len=200, hash=AI, app="Code.exe", target_title="Main.java - java-hw2"),
    ev("09:55", type="keys", count=18, deleted=2, app="Code.exe", category="work"),
    ev("10:20", type="undo", app="Code.exe"),
    ev("10:30", type="keys", count=66, deleted=14, app="Code.exe", category="work"),
    ev("11:00", type="file", action="modified", path="C:/work/java-hw2/Main.java", content_hash=H("file-v2")),
    ev("11:30", type="window", app="chrome.exe", title="Java Docs", category="other"),      # 제목만으론 기타
    ev("11:31", type="tab", domain="docs.oracle.com", category="resource", title="Java Docs"),  # 확장이 자료로 정정
    ev("14:00", type="window", app="KakaoTalk.exe", title="", category="other"),           # 화이트리스트 밖
    ev("14:10", type="keys", count=30, deleted=4, app="KakaoTalk.exe", category="other"),
    ev("15:00", type="window", app="explorer.exe", title="", category="other"),
    ev("15:05", type="copy", len=14, hash=MINE, app="explorer.exe", category="other"),
    ev("15:10", type="window", app="Code.exe", title="Main.java - java-hw2", category="work"),
    ev("15:12", type="paste", len=14, hash=MINE, app="Code.exe", target_title="Main.java - java-hw2"),
    ev("15:30", type="paste", len=77, hash=H("unknown-source"), app="Code.exe", target_title="Main.java - java-hw2"),  # 복사 기록 없음
    ev("15:40", type="keys", count=25, deleted=1, app="Code.exe", category="work"),
    ev("16:00", type="window", app="WINWORD.EXE", title="보고서.docx - Word", category="work"),
    ev("16:10", type="copy", len=120, hash=H("ai-answer-120"), app="chrome.exe", category="ai"),   # (AI 창 복사 — 순서상 앞이어도 됨)
    ev("16:20", type="paste", len=120, hash=H("ai-answer-120"), app="WINWORD.EXE", target_title="보고서.docx - Word"),
    ev("16:22", type="doc_paste_at", app="Word", file="보고서.docx", where="문단 4"),
    ev("16:25", type="doc_change", app="Word", file="보고서.docx", where="문단 4", added=120, removed=0),
    ev("16:40", type="keys", count=33, deleted=6, app="WINWORD.EXE", category="work"),
    ev("16:50", type="doc_change", app="Word", file="보고서.docx", where="문단 4", added=27, removed=6),
    ev("16:55", type="doc_save", app="Word", file="보고서.docx", chars=1530, words=310, paragraphs=4),
    ev("17:00", type="idle_start", idle_sec=300),
    ev("19:30", type="idle_end"),
    ev("20:00", type="session_end"),
]


def main():
    out = os.path.join(HERE, "fixtures")
    os.makedirs(out, exist_ok=True)
    prev = C.GENESIS
    rows = []
    for i, e in enumerate(EVENTS, 1):
        e = {"id": f"evt_{i:06d}", **e}
        if C.in_chain(e):
            prev = C.next_hash(prev, e)
            e["h"] = prev
        rows.append(e)
    with open(os.path.join(out, "events_basic.jsonl"), "w", encoding="utf-8") as f:
        for e in rows:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    expected = derive(rows)
    with open(os.path.join(out, "expected_basic.json"), "w", encoding="utf-8") as f:
        json.dump(expected, f, ensure_ascii=False, indent=1)
    s = expected["stats"]
    print(f"events {len(rows)}  chain {s['events']}  root {expected['root'][:16]}…")
    print(f"typed {s['typed']} ({s['typed_pct']}%)  pasted {s['pasted']} ({s['pasted_pct']}%)  ai {s['pasted_ai']}  undo {s['undo']}")
    print("segments:", [(g["s"], g["e"], g["cat"], g["title"][:14]) for g in expected["segments"]])
    print("pastes:", [(p["ts"], p["len"], p["matched"], p["ai"]) for p in expected["pastes"]])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
