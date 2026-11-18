"""
test_via_app.py — AI 답을 메모장 · 한글 같은 PC 프로그램에서 고쳐 붙여도 AI 답 연결이 남는다 (11/18 김용현 맥 시험)

  GPT 답 복사 → 메모장(텍스트 편집기)에 붙여 고침 → 다시 복사 → Word 에 붙임
  전: "다른 곳(메모장)에서 붙여넣음" — AI 연결이 사라지고 다듬기 카드는 '웹 글 출처 없음(A2)' 로 나옴 (한 글자만 고쳐도 세탁)
  후: "붙여넣고 고침" · AI 답에 이어짐 · 붙여넣기 기록엔 메모장 (via)
  웹사이트에서 복사한 글 · AI 답보다 먼저 복사한 글은 그대로 '다른 곳'

  python 3-코드/tests/test_via_app.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import match as M                      # noqa: E402

통과, 실패 = 0, 0
답 = ("대학의 생성형 AI 가이드라인은 2024년 이후 빠르게 늘었다. "
      "교육부는 대학 공통의 AI 활용 윤리 가이드라인을 발표하며 과제에 AI 사용 사실을 밝히도록 권고했다.")
고친 = "교육부는 대학 공통 AI 윤리 가이드라인을 내놓으며, 과제에 AI를 썼다는 사실을 밝히라고 권고했다."


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✓' if 조건 else '✗'} {이름} {덧}")


def 이어(글, app, 복사, category="other"):
    others = [{"text": 글, "source": app, "app": app, "category": category, "copied_at": f"2026-11-18T{복사}:00+09:00",
               "pasted_at": f"2026-11-18T{복사}:10+09:00", "file": "보고서.docx", "where": "문단 2"}]
    return M.link_document([글], [{"id": "g", "text": 답, "asked": "2026-11-18T10:00:00+09:00"}], pasted=[], others=others)[0][0]


def main():
    print("\n  PC 프로그램을 거쳐 고친 AI 답\n  " + "─" * 60)
    r = 이어(고친, "TextEdit", "10:05")
    검사("메모장(맥 텍스트 편집기)에서 고침 → 붙여넣고 고침 · AI 답", r["label"] == "edited" and r["answer"] == "g" and r["paste"].get("via"), r["label"])
    r = 이어(고친, "Notepad.exe", "10:05")
    검사("윈도우 메모장도 같음", r["label"] == "edited" and r["answer"] == "g", r["label"])
    r = 이어(답.split(". ")[1], "TextEdit", "10:05")
    검사("메모장을 거쳤지만 거의 그대로 → AI 답과 일치 · 유사", r["label"] == "exact" and r["answer"] == "g", r["label"])
    r = 이어(고친, "Google Chrome", "10:05")
    검사("웹사이트에서 복사한 글은 그대로 '다른 곳'", r["label"] == "web" and r["answer"] is None, r["label"])
    r = 이어(고친, "TextEdit", "09:50")
    검사("AI 답을 묻기 전에 복사한 글은 그대로 '다른 곳'", r["label"] == "web" and r["answer"] is None, r["label"])
    r = 이어(고친, "", "10:05")
    검사("어디서 복사했는지 모르면 그대로 '다른 곳'", r["label"] == "web", r["label"])
    evs = [{"type": "copy", "ts": "2026-11-18T10:05:00+09:00", "hash": "h1", "app": "TextEdit", "category": "other"},
           {"type": "window", "ts": "2026-11-18T10:05:05+09:00", "app": "Word", "category": "work"},
           {"type": "paste", "ts": "2026-11-18T10:05:10+09:00", "hash": "h1", "app": "Microsoft Word", "len": len(고친)},
           {"type": "doc_paste_at", "ts": "2026-11-18T10:05:10+09:00", "where": "문단 2", "app": "Word", "file": "보고서.docx"}]
    ctx = [{"kind": "diff", "ts": "2026-11-18T10:05:10+09:00", "text": 고친, "meta": {"app": "Word", "file": "보고서.docx", "where": "문단 2"}}]
    o = M.pasted_from_other(evs, ctx)
    검사("붙여넣기 기록에 복사한 프로그램 이름(app)이 남음", o and o[0].get("app") == "TextEdit", str(o[:1]))
    print("  " + "─" * 60 + f"\n  {'✓ 통과' if not 실패 else '✗ 실패'}  ({통과}개 통과 · {실패}개 실패)\n")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
