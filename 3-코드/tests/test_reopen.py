"""
test_reopen.py — 기록을 다시 켰을 때 · 맥 Word 를 늦게 읽을 때 · 잘린 참고문헌 줄 (11/16 김용현 맥 실제 시험)

  ① 같은 과제 기록을 다시 켜면 "열 때 있던 글" 이 생기는데, 앞 기록에 이미 쓴 과정이 있는 줄은 '쓴 과정 기록 없음' 이 아니다
     — 기록 밖에서 새로 생긴 줄만 남는다
  ② 붙여넣은 글을 Word 가 몇 초 늦게 · 두 번에 나눠 읽어도 그 나머지는 '쓴 과정 기록 없음' 이 아니다
  ③ 조각조각 친 문장도 친 글로 본다
  ④ 마침표로 잘린 참고문헌 한 줄("이유미, & 윤회정." "(2024).")은 옆 줄과 같은 AI 답으로

  python 3-코드/tests/test_reopen.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import match as M                      # noqa: E402

통과, 실패 = 0, 0
F = "보고서.docx"


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✓' if 조건 else '✗'} {이름} {덧}")


def t(mmss):
    return f"2026-11-16T15:{mmss}+09:00"


def 친(ts, 글, 문단="문단 3"):
    """타이핑 한 조각 — 글 변화 + 그 무렵 키"""
    return ({"kind": "diff", "ts": ts, "text": 글, "meta": {"app": "Word", "file": F, "where": 문단}},
            {"type": "keys", "ts": ts, "app": "Microsoft Word", "count": 3 * len(글)})


def main():
    print("\n  다시 켠 기록 · 늦게 읽은 붙여넣기 · 잘린 참고문헌\n  " + "─" * 60)
    문장 = "이 연구는 국내외 대학의 생성형 AI 가이드라인을 분석하여 교양교육 차원의 방안을 제시한다."
    조각들 = ["이 연구는", " 국내외 대학의", " 생성형 AI 가이드라인을", " 분석하여 교양교육", " 차원의 방안을 제시한다."]
    ctx, evs = [], []
    for i, g in enumerate(조각들):
        c, k = 친(t(f"{10 + i}:00"), g)
        ctx.append(c); evs.append(k)
    새줄 = "기록을 끈 동안 다른 데서 가져다 붙인 문단이 여기에 있다고 치자."
    ctx.append({"kind": "doc_open", "ts": t("55:00"), "text": 문장 + "\n" + 새줄, "meta": {"app": "Word", "file": F}})
    pe = M.process_evidence(evs, ctx)
    열때 = [x for x in pe["noproc"] if x["how"] == "open"]
    검사("① 다시 연 문서: 앞 기록에 친 과정이 있는 줄은 빠짐", 열때 and 문장 not in 열때[0]["text"], str([x["text"][:20] for x in 열때]))
    검사("① 기록 밖에서 새로 생긴 줄은 남음", 열때 and 새줄 in 열때[0]["text"])
    검사("③ 조각조각 친 문장도 친 글 (문단으로 이음)", any(M.norm(문장) in M.norm(x) for x in pe["typed"]))
    처음 = M.process_evidence([], [{"kind": "doc_open", "ts": t("00:00"), "text": 문장, "meta": {"app": "Word", "file": F}}])
    검사("① 처음 여는 문서는 예전처럼 전부 '열 때 있던 글'", [x["text"] for x in 처음["noproc"]] == [문장])

    붙인글 = "설계, 학생에게는 윤리 준수와 사전 협의를, 연구자에게는 프라이버시 보호를 강조하며 전반적"
    나머지 = ", 연구자에게는 프라이버시 보호를 강조하며 전반적으로 수용적인 태도를 보였"
    늦은 = "An 등 (2025): 미국 상위 50개 대학의 생성형 AI 가이드라인 및 정책 분석"
    evs2 = [{"type": "doc_paste_at", "ts": t("29:10"), "where": "문단 19"}, {"type": "doc_paste_at", "ts": t("26:51"), "where": "문단 17"}]
    ctx2 = [{"kind": "diff", "ts": t("29:10"), "text": 붙인글, "meta": {"app": "Word", "file": F, "where": "문단 19"}},
            {"kind": "diff", "ts": t("29:21"), "text": 나머지, "meta": {"app": "Word", "file": F, "where": "문단 19"}},
            {"kind": "diff", "ts": t("26:56"), "text": 늦은, "meta": {"app": "Word", "file": F, "where": "문단 17"}}]
    pe2 = M.process_evidence(evs2, ctx2)
    검사("② 두 번에 나눠 읽은 붙여넣기 나머지는 '쓴 과정 기록 없음' 아님", all(x["text"] != 나머지 for x in pe2["noproc"]), str(pe2["noproc"]))
    검사("② 붙인 자리 5초 뒤 늦게 읽힌 글도", all(x["text"] != 늦은 for x in pe2["noproc"]))

    답 = ("참고문헌 목록\n이유미, & 윤회정. (2024). 생성형 AI 시대의 교양교육－생성형 AI 가이드라인과 생성형 AI 리터러시를 중심으로. "
          "교양교육연구, 18(6), 11-26.")
    줄 = "이유미, & 윤회정. (2024). 생성형 AI 시대의 교양교육－생성형 AI 가이드라인과 생성형 AI 리터러시를 중심으로. 교양교육연구, 18(6), 11-26."
    out = M.link_document([줄], [{"id": "g", "text": 답}], pasted=None)
    l = [(r["text"], r["label"]) for r in out[0]]
    검사("④ 잘린 참고문헌 한 줄은 모두 같은 답 (그대로)", all(x == "exact" for _, x in l), str(l))
    out = M.link_document(["가장 중요한 단계. 브랜드 컨셉을 먼저 정하고 페르소나를 만든다."],
                          [{"id": "a", "text": "브랜드 컨셉을 먼저 정하고 페르소나를 만든다. 이게 가장 중요한 단계예요."}], pasted=None)
    검사("④ 순서대로 이어 있지 않은 짧은 줄은 안 이음", out[0][0]["label"] == "none", str([(r["text"], r["label"]) for r in out[0]]))
    print("  " + "─" * 60 + f"\n  {'✓ 통과' if not 실패 else '✗ 실패'}  ({통과}개 통과 · {실패}개 실패)\n")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
