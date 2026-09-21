"""
compare_llm.py — 같은 세션을 여러 AI 공급자로 돌려 리포트를 나란히 놓는다.

  python 3-코드/server/compare_llm.py                       # 키가 있는 것만 전부
  python 3-코드/server/compare_llm.py qwen openai           # 지정해서
  python 3-코드/server/compare_llm.py --out 비교.md          # 파일로 저장

왜 만드나 — Qwen 은 교수님 '추천'이지 결정이 아니다. 어느 모델이 나은지는
의견이 아니라 **같은 입력을 넣고 나란히 봐야** 정해진다. 결과를 그대로
팀 회의·교수님께 보여줄 수 있게 표로 만든다.

입력은 tests/fixtures/events_basic.jsonl (이벤트 38건짜리 진짜 세션).
키가 없는 공급자는 건너뛴다. 하나도 없으면 fake 로 모양만 보여준다.

★ 여기서 재는 것: 글의 품질(사람이 판단) · 토큰 수 · 걸린 시간.
  값은 공급자마다 단가가 달라 이 스크립트가 계산하지 않는다 — 토큰 수만 준다.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
sys.path.insert(0, CODE)

from core.derive import derive        # noqa: E402

FIX = os.path.join(CODE, "tests", "fixtures", "events_basic.jsonl")

# 공급자 → 필요한 환경변수
필요한키 = {
    "qwen":   "DASHSCOPE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "fake":   None,
}
항목이름 = {
    "topics":    "주요 학습 내용",
    "struggles": "어려움",
    "process":   "학습 과정",
    "points":    "학습 포인트",
    "todo":      "추가 학습",
}


def 세션_읽기():
    evs = [json.loads(l) for l in open(FIX, encoding="utf-8") if l.strip()]
    return derive(evs), evs


def 한번_돌리기(공급자, 세션, 맥락):
    """★ llm.py 는 import 할 때 환경변수를 읽는다. 공급자를 바꾸려면 다시 읽어야 한다."""
    import importlib
    os.environ["LLM_PROVIDER"] = 공급자
    from core import llm
    importlib.reload(llm)

    시작 = time.time()
    try:
        몸 = llm.make_report(세션, 맥락)
        오류 = None
    except Exception as e:
        몸, 오류 = {}, f"{type(e).__name__}: {e}"
    걸린 = time.time() - 시작

    모델 = {"qwen": llm.QWEN_MODEL, "openai": llm.OPENAI_MODEL,
            "claude": llm.CLAUDE_MODEL}.get(공급자, "fake")
    글자수 = sum(len(str(v)) for v in 몸.values()) if 몸 else 0
    return {"공급자": 공급자, "모델": 모델, "몸": 몸, "오류": 오류,
            "초": 걸린, "글자수": 글자수}


def 표로(결과들):
    줄 = []
    줄.append("# AI 공급자 비교 — 같은 세션, 같은 프롬프트\n")
    줄.append(f"입력: `tests/fixtures/events_basic.jsonl` · 이벤트 38건\n")
    줄.append("## 한눈에\n")
    줄.append("| 공급자 | 모델 | 걸린 시간 | 답 길이 | 상태 |")
    줄.append("|---|---|---|---|---|")
    for r in 결과들:
        상태 = "오류: " + r["오류"] if r["오류"] else "정상"
        줄.append(f"| {r['공급자']} | `{r['모델']}` | {r['초']:.1f}초 | {r['글자수']}자 | {상태} |")
    줄.append("")
    줄.append("> 값(원)은 공급자마다 단가가 달라 여기서 계산하지 않습니다. "
              "각 콘솔의 사용량으로 확인하세요.\n")

    for 열쇠, 이름 in 항목이름.items():
        줄.append(f"## {이름}\n")
        for r in 결과들:
            값 = r["몸"].get(열쇠)
            줄.append(f"**{r['공급자']}** (`{r['모델']}`)\n")
            if not 값:
                줄.append("(없음)\n")
            elif isinstance(값, list):
                줄+= [f"- {x}" for x in 값] + [""]
            else:
                줄.append(f"{값}\n")
    return "\n".join(줄)


def main():
    ap = argparse.ArgumentParser(description="AI 공급자 리포트 비교")
    ap.add_argument("providers", nargs="*", help="qwen openai claude fake (비우면 키 있는 것 전부)")
    ap.add_argument("--out", help="결과를 이 파일로 저장 (.md)")
    a = ap.parse_args()

    고를것 = a.providers or [p for p, k in 필요한키.items()
                             if p != "fake" and k and os.environ.get(k)]
    if not 고를것:
        print()
        print("  키가 하나도 없습니다. fake 로 모양만 보여줍니다.")
        print("  실제 비교를 하려면 키를 넣고 다시 돌리세요:")
        print()
        for p, k in 필요한키.items():
            if k:
                print(f"      export {k}=...        # {p}")
        print()
        고를것 = ["fake"]

    세션, _ = 세션_읽기()
    맥락 = []          # 픽스처에 Learn 맥락은 없다. 있으면 여기에 넣는다.

    결과들 = []
    for p in 고를것:
        키 = 필요한키.get(p)
        if 키 and not os.environ.get(키):
            print(f"  건너뜀 — {p} (환경변수 {키} 없음)")
            continue
        print(f"  돌리는 중: {p} …", end="", flush=True)
        r = 한번_돌리기(p, 세션, 맥락)
        print(f" {r['초']:.1f}초  {r['글자수']}자" + (f"  ⚠ {r['오류']}" if r["오류"] else ""))
        결과들.append(r)

    글 = 표로(결과들)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(글)
        print(f"\n  저장했습니다: {a.out}\n")
    else:
        print()
        print(글)
    return 0


if __name__ == "__main__":
    sys.exit(main())
