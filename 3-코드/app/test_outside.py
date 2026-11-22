"""
test_outside.py — 내기 직전 점검 B5 "기록을 꺼 둔 동안 바뀐 문단" (14번 문서 · 11/18 박상진)

  python app/test_outside.py

export._기록_밖(events, context, 세션) 만 본다 — 기록 다시 보기의 "기록 밖에서 바뀐 글" 과 같은 규칙:
  · 첫 기록 전에 있던 글은 세지 않음 (B3 쓴 과정 기록 없음이 맡음)
  · 둘째 기록부터, 그 기록이 문서를 처음 열 때 있던 글 중 앞선 기록에 없던 문단만 · 시간 틈 = 앞 기록 끝 ~ 이 기록 시작
  · 앞 기록에서 친 문단 · 앞 기록 그대로인 문서는 0 · 이 기록에서 고치지 않은 다른 문서는 빼기
  · 숫자와 시각만 (글은 화면으로 안 감)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_source as T                          # noqa: E402  같은 방식으로 app 모듈을 읽음
EX = sys.modules["export"]
검사 = T.검사
F = "보고서.docx"


def ts(hhmm, day=16):
    return f"2026-11-{day:02d}T{hhmm}:00+09:00"


def 기록(sid, a, b, end=True):
    evs = [{"session_id": sid, "type": "session_start", "ts": a}]
    if end:
        evs.append({"session_id": sid, "type": "session_end", "ts": b})
    else:
        evs.append({"session_id": sid, "type": "keys", "ts": b, "count": 3})
    return evs


def 열때(sid, t, 글, file=F):
    return {"session_id": sid, "kind": "doc_open", "ts": t, "text": 글, "meta": {"app": "Word", "file": file}}


def 친(sid, t, 글, file=F):
    return {"session_id": sid, "kind": "diff", "ts": t, "text": 글, "meta": {"app": "Word", "file": file, "where": "문단 1"}}


def main():
    print("\n  B5 기록을 꺼 둔 동안 바뀐 문단\n  " + "─" * 60)
    가 = "첫 기록 전에 이미 문서에 있던 서론 문단이 여기에 있다."
    나 = "첫 기록에서 직접 쳐서 넣은 본론 문단은 이렇게 생겼다."
    다 = "기록을 끈 동안 다른 데서 가져다 붙인 문단이 여기에 있다."
    라 = "다음 날 기록 없이 고친 결론 문단도 하나 더 생겼다고 치자."

    # 첫 기록 하나뿐 — 열 때 있던 글은 B3 몫이라 B5 는 없음
    evs = 기록("S1", ts("14:00"), ts("15:00"))
    ctx = [열때("S1", ts("14:00"), 가), 친("S1", ts("14:20"), 나)]
    검사("첫 기록뿐이면 없음 (첫 기록 전 글은 B3)", EX._기록_밖(evs, ctx, {"S1"}) == [])

    # 둘째 기록: 열 때 '다' 가 새로 있음 → 1문단 · 틈 = S1 끝 ~ S2 시작
    evs2 = evs + 기록("S2", ts("16:30"), ts("17:00"))
    ctx2 = ctx + [열때("S2", ts("16:30"), "\n".join([가, 나, 다]))]
    out = EX._기록_밖(evs2, ctx2, {"S1", "S2"})
    검사("둘째 기록에 새로 생긴 문단 1 · 틈 = 15:00 ~ 16:30",
         out == [{"from": ts("15:00"), "to": ts("16:30"), "spots": 1, "chars": len(다)}], json.dumps(out, ensure_ascii=False))
    검사("앞 기록에서 친 문단 · 열 때 있던 문단은 안 셈", out and out[0]["spots"] == 1)
    검사("숫자와 시각만 (글은 안 감)", all(set(g) == {"from", "to", "spots", "chars"} for g in out))

    # 그대로 다시 열면 0
    ctx3 = ctx + [열때("S2", ts("16:30"), "\n".join([가, 나]))]
    검사("지난 기록 그대로면 없음", EX._기록_밖(evs2, ctx3, {"S1", "S2"}) == [])

    # 셋째 기록 (다음 날): 앞선 두 기록에 없던 '라' 만 · 틈 2개 · session_end 없는 기록은 마지막 이벤트가 끝
    evs4 = 기록("S1", ts("14:00"), ts("15:00")) + 기록("S2", ts("16:30"), ts("17:05"), end=False) + 기록("S3", ts("09:10", 17), ts("10:00", 17))
    ctx4 = ctx2 + [열때("S3", ts("09:10", 17), "\n".join([가, 나, 다, 라]))]
    out4 = EX._기록_밖(evs4, ctx4, {"S1", "S2", "S3"})
    검사("틈마다 따로 · 시각 순", [g["spots"] for g in out4] == [1, 1], json.dumps(out4, ensure_ascii=False))
    검사("끝 이벤트가 없으면 그 기록의 마지막 이벤트가 끝", len(out4) == 2 and out4[1]["from"] == ts("17:05") and out4[1]["to"] == ts("09:10", 17))

    # 이 기록에서 고친 문서가 따로 있으면, 잠깐 연 다른 문서의 글은 안 셈
    ctx5 = ctx + [열때("S2", ts("16:30"), "\n".join([가, 나, 다]), file="다른.docx"),
                  열때("S2", ts("16:31"), "\n".join([가, 나])), 친("S2", ts("16:40"), "이번 기록에서 친 짧지 않은 문장 하나.")]
    evs5 = evs2 + [{"session_id": "S2", "type": "doc_change", "ts": ts("16:40"), "file": F}]
    검사("이 기록에서 고치지 않은 다른 문서는 빼기", EX._기록_밖(evs5, ctx5, {"S1", "S2"}) == [])

    # 짧은 줄(제목 등 MIN_CHARS 미만)은 안 셈
    ctx6 = ctx + [열때("S2", ts("16:30"), "\n".join([가, 나, "결론"]))]
    검사("짧은 줄(제목)은 안 셈", EX._기록_밖(evs2, ctx6, {"S1", "S2"}) == [])

    print("\n  " + "─" * 60 + f"\n  통과 {T.통과} · 실패 {T.실패}")
    sys.exit(1 if T.실패 else 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
