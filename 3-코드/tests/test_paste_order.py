"""
test_paste_order.py — 10/14 실제 시험에서 찾은 두 가지 (core/match.py)

  python tests/test_paste_order.py

① 웹 AI(ChatGPT 웹)에서 복사한 글: 복사 단추가 표 · 굵게를 화면 글과 다르게 클립보드에 넣어 확장 발췌 해시 ≠ copy 해시
   → 같은 순간(3초 안) 브라우저 발췌로 이어 "AI 답 붙여넣기" 로 본다
② 먼저 붙여넣은 글이 나중에 나온 AI 답(보고서를 요약한 답)과 글자가 겹쳐도 그 답에서 온 것으로 잡지 않는다
   — 문장이 문서에 처음 들어온 붙여넣기가 출처. 그 AI 대화 기록이 없으면(웹 화면을 못 읽음) 붙여넣은 곳(도메인)으로
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import match as M                   # noqa: E402
from core.texthash import sha256_text         # noqa: E402

ok = True


def 검사(이름, 조건, 설명=""):
    global ok
    ok &= bool(조건)
    print(f"  {'✓' if 조건 else '✗'} {이름}  {설명}")


T = lambda m, s=0: f"2026-10-14T14:{m:02d}:{s:02d}+09:00"
웹글 = "먼작귀는 뭔가 작고 귀여운 녀석의 줄임말로 일본 원제인 치이카와를 국내에서 부르는 명칭이다."
화면글 = "먼작귀는 **뭔가 작고 귀여운 녀석**의 줄임말로 일본 원제인 치이카와를 국내에서 부르는 명칭이다."   # 확장 발췌 (굵게 표시가 남음)
요약답 = "본 보고서를 요약하면 다음과 같아요. " + 웹글 + " 이 작품은 귀여움과 현실성을 함께 다룬다."
요약발췌 = 요약답

events = [
    {"type": "tab", "ts": T(17), "domain": "chatgpt.com", "category": "ai"},
    {"type": "copy", "ts": T(18, 6), "app": "chrome.exe", "category": "ai", "hash": sha256_text(웹글), "len": len(웹글)},
    {"type": "paste", "ts": T(18, 7), "app": "WINWORD.EXE", "hash": sha256_text(웹글), "len": len(웹글)},
    {"type": "doc_paste_at", "ts": T(18, 8), "app": "Word", "file": "보고서.docx", "where": "문단 2"},
    {"type": "copy", "ts": T(28, 14), "app": "claude.exe", "category": "ai", "hash": sha256_text(요약발췌), "len": len(요약발췌)},
    {"type": "paste", "ts": T(28, 15), "app": "WINWORD.EXE", "hash": sha256_text(요약발췌), "len": len(요약발췌)},
    {"type": "doc_paste_at", "ts": T(28, 16), "app": "Word", "file": "보고서.docx", "where": "문단 9"},
]
context = [
    {"ts": T(18, 6), "source": "browser", "kind": "ai_answer_excerpt", "text": 화면글, "meta": {"domain": "chatgpt.com"}},
    {"ts": T(28, 14), "source": "desktop", "kind": "ai_answer_excerpt", "text": 요약발췌, "meta": {"tool": "Claude 앱", "domain": "claude.exe"}},
]
answers = [{"id": 0, "text": 요약답, "ts": T(28, 9)}]          # 웹 ChatGPT 대화는 기록되지 않음 · Claude 요약 답만

print("\n  붙여넣기 순서 · 웹 AI 복사 해시 검사\n  " + "─" * 60)
pa = M.pasted_from_ai(events, context)
검사("① 해시가 다른 웹 AI 복사도 같은 순간 발췌로 이어짐", len(pa) == 2 and {p["domain"] for p in pa} == {"chatgpt.com", "claude.exe"},
     str([(p["domain"], p["pasted_at"][11:19]) for p in pa]))
검사("① 그 붙여넣기는 '다른 곳' 목록엔 없음", M.pasted_from_other(events, context) == [])

doc = ["치이카와 보고서", 웹글, "결론", 요약답]
rows = M.link_document(doc, answers, pa, M.pasted_from_other(events, context))
첫 = rows[1][0]
검사("② 먼저 웹에서 붙여넣은 문장 → Claude 요약 답이 아니라 chatgpt.com", 첫["label"] == "web" and 첫["paste"]["source"] == "chatgpt.com"
     and 첫["answer"] is None, f"{첫['label']} · {(첫.get('paste') or {}).get('source')}")
뒤 = [r for r in rows[3] if M.norm(r["text"]) == M.norm(웹글)][0]
검사("② 나중에 Claude 요약 답을 붙여넣은 같은 문장도 처음 들어온 곳은 웹 (문장은 같은 글)", 뒤["label"] == "web")
결 = [r for r in rows[3] if "귀여움과 현실성" in r["text"]][0]
검사("② Claude 요약 답에만 있는 문장은 그대로 Claude 답 · 붙여넣기 기록", 결["label"] == "exact" and 결["answer"] == 0
     and 결["paste"] and 결["paste"]["domain"] == "claude.exe")

# 시각이 없는 옛 기록 · 시험은 예전처럼 (시간으로 막지 않음)
옛 = M.link_document(doc, [{"id": 0, "text": 요약답}], pa)
검사("시각 모르는 답은 막지 않음 (옛 기록)", 옛[3][-1]["label"] == "exact")
print(f"\n  {'✓ 통과' if ok else '✗ 실패'}")
sys.exit(0 if ok else 1)
