"""
test_paste_cards.py — AI 앱 답을 복사할 때 딸려 온 카드 제목 줄 (11/16 실제 시험)

ChatGPT 앱 답을 복사하면 이미지 · 출처 카드의 제목 글자가 같이 붙는다. 이 줄들은 답 본문에 없어서, 글자 조각이 겹치는
**다른 대화의 답**에 "고침" 으로 이어졌다 (그 답의 출처 링크가 엉뚱하게 보임). 한 번에 복사해 붙인 글은 그 복사의 출처 답에만 잇는다.
실행: python tests/test_paste_cards.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import match as M   # noqa: E402

실패 = 0


def check(name, ok, detail=""):
    global 실패
    실패 += not ok
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  {detail}" if detail and not ok else ""))


def main():
    옛답 = ("A cinematic photo of the new GB300 Blackwell Ultra AI servers in a liquid cooled data center cluster, wide shot.\n"
           "8\n" + "Keep the same character and lighting in every frame of the series. " * 30)
    답 = ("엔비디아는 이번 주 새 서버 제품군을 공개했다. 젠슨 황은 기조연설에서 액체 냉각 방식의 장점을 길게 설명했다. "
          "업계는 이번 발표가 데이터 센터 투자 흐름을 바꿀 것으로 본다. 다만 실제 공급 일정은 아직 확정되지 않았다.")
    카드 = "NVIDIA's GB300 'Blackwell Ultra' AI Servers: A Leap Towards Fully Liquid-Cooled AI Clusters"
    카드2 = "Nvidia CEO expects to make announcements with South Korean partners this week By Reuters"
    붙인글 = 답 + chr(10) + 카드 + " " + 카드2 + " 8"          # 카드 제목은 앞뒤 줄과 끊김 없이 붙어 온다 → 문장끼리 비교로는 '그대로' 가 안 됨
    answers = [{"id": 0, "text": 옛답, "ts": "2026-11-16T12:27:54+09:00"},
               {"id": 1, "text": 답, "ts": "2026-11-16T12:29:15+09:00"}]
    pasted = [{"text": 붙인글, "copied_at": "2026-11-16T12:29:16+09:00", "pasted_at": "2026-11-16T12:29:18+09:00", "domain": "chatgpt.exe"}]
    out = M.link_document(답.replace(". ", ".\n").split("\n") + [카드, "8"], answers, pasted=pasted, others=[])
    rows = [r for row in out for r in row]
    본문 = [r for r in rows if r["text"] not in (카드, "8")]
    카드줄 = next(r for r in rows if r["text"] == 카드)
    check("답 본문 문장은 그 답(1)에 그대로 이어짐", all(r["label"] == "exact" and r["answer"] == 1 for r in 본문), str([(r["label"], r["answer"]) for r in 본문]))
    check("딸려 온 카드 제목은 다른 대화의 답(0)에 잇지 않음 — AI 에서 그대로 붙여넣은 글로",
          카드줄["label"] == "web" and 카드줄["answer"] is None and (카드줄["paste"] or {}).get("category") == "ai" and 카드줄["paste"].get("alongside") is True, str((카드줄["label"], 카드줄["answer"])))
    check("어느 문장도 옛 답(0)에 이어지지 않음 (짧은 줄 '8' 포함)", not any(r.get("answer") == 0 for r in rows), str([(r["text"][:10], r["label"]) for r in rows if r.get("answer") == 0]))
    # 진짜로 두 답에서 따로 복사해 붙인 경우는 그대로 — 각자 자기 답에
    둘 = [{"text": 답, "copied_at": "2026-11-16T12:29:16+09:00", "pasted_at": "2026-11-16T12:29:18+09:00", "domain": "chatgpt.exe"},
          {"text": 옛답.split("\n")[0], "copied_at": "2026-11-16T12:31:00+09:00", "pasted_at": "2026-11-16T12:31:02+09:00", "domain": "chatgpt.exe"}]
    out = M.link_document([답, 옛답.split("\n")[0]], answers, pasted=둘, others=[])
    끝 = out[1][0]
    check("따로 복사해 붙인 옛 답 문장은 그 답(0)에 그대로", 끝["label"] == "exact" and 끝["answer"] == 0, str((끝["label"], 끝["answer"])))
    print("✓ 통과" if not 실패 else f"✗ {실패}건 실패")
    return not 실패


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(0 if main() else 1)
