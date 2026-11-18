"""
test_split_lines.py — 답 원문이 줄마다 잘려 있어도 그대로 옮긴 문장은 '일치' (11/18 김용현 맥 시험)

맥 ChatGPT 앱은 굵게 · 기울임마다 줄이 끊긴 글로 읽힌다 ("학술지:\\n\\nComputers\\n, 2026, 15(2), 111").
손대지 않은 참고문헌 줄 둘이 '붙여넣고 고침' 으로 나오던 것.

  python 3-코드/tests/test_split_lines.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import match as M                      # noqa: E402

통과, 실패 = 0, 0
답 = ("저자:\nItahisa Pérez-Pérez, David Pérez-Jorge\n학술지:\n\nComputers\n, 2026, 15(2), 111\nDOI:\n10.3390/computers15020111\n"
      "참고문헌\nPérez-Pérez, I., & Pérez-Jorge, D. (2026). Transparency Mechanisms for Generative AI Use in Higher Education "
      "Assessment: A Systematic Scoping Review (2022–2026).\nComputers, 15\n(2), 111. https://doi.org/10.3390/computers15020111")


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✓' if 조건 else '✗'} {이름} {덧}")


def 표(s):
    r = M.link_document([s], [{"id": "g", "text": 답}], pasted=None)[0][0]
    return r["label"], r["full"], r["sents"]


print("\n  줄마다 잘린 답 원문\n  " + "─" * 60)
l = 표("학술지: Computers, 2026, 15(2), 111")
검사("잘린 세 줄에 걸친 한 줄 → 일치 (칠할 줄 셋)", l == ("exact", True, (2, 3, 4)), str(l))
l = 표("Computers, 15(2), 111.")
검사("기울임에서 잘린 참고문헌 조각 → 일치", l[0] == "exact" and l[1], str(l))
l = 표("학술지는 Computers 이며 2026년 15권 2호 111쪽에 실렸다.")
검사("말을 바꿔 쓴 문장은 그대로 비교 (일치 아님)", l[0] != "exact", str(l))
l = 표("Computers 학술지")
검사("답에 이어서 들어 있지 않으면 일치 아님", l[0] != "exact", str(l))
print("  " + "─" * 60 + f"\n  {'✓ 통과' if not 실패 else '✗ 실패'}  ({통과}개 통과 · {실패}개 실패)\n")
sys.exit(1 if 실패 else 0)
