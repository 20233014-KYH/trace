"""
test_paste_group.py — 여러 문단 붙여넣기 · AI 에게 한 질문 붙여넣기 · 표 칸 (10/14 맥 실제 시험에서 찾음)

  python 3-코드/tests/test_paste_group.py

10/14 김용현 맥 시험 (SoC 보고서):
  ① 구글 AI 답 14문단을 한 번에 붙여넣었는데 커서가 놓인 문단 하나만 '다른 곳' · 나머지 13문단은 '쓴 과정 기록 없음' 이거나
     비슷한 Claude 답으로 감 — 붙여넣기 직후 Word 를 읽은 그 순간 생긴 글 변화를 다 그 붙여넣기로 본다
  ② Claude 답을 구글 검색창에 붙여넣어 물어봄(문서가 아님) → 그 붙여넣기가 문서 글의 출처로 잡힘 — 브라우저 · AI 앱에 붙인 건 뺀다
  ③ Claude 표 붙여넣기의 짧은 칸("M6" · "저가형 라인")이 '출처 기록 없음' — 표 칸(탭)도 한 줄로
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import match as M   # noqa: E402

통과, 실패 = 0, 0


def check(이름, 맞음, 덧=""):
    global 통과, 실패
    통과, 실패 = 통과 + bool(맞음), 실패 + (not 맞음)
    print(f"  {'✓' if 맞음 else '✗'} {이름}  {'' if 맞음 else 덧}")


def h(t):
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


T = "2026-10-14T15:{}+09:00".format
F = "보고서.docx"
CLAUDE = "M6는 TSMC의 2나노 공정을 처음 적용하는 M 시리즈 칩으로 알려져 있다. 발열이 적고 배터리가 오래간다."
TABLE = "구분\t현황\nM6\t2026년 하반기 예상\n저가형 라인\t아이폰용 칩을 사용"
GOOGLE = ["핵심 기술 트렌드 및 전망 (M6 칩셋 중심)",
          "내용: M6 시리즈는 TSMC의 2나노(nm) 선단 공정을 최초로 적용하는 M 시리즈 칩셋이 될 것으로 전망됩니다.",
          "기대 효과: 트랜지스터 집적도의 비약적인 상승을 통해 연산 속도가 향상되는 동시에 전력 효율이 개선됩니다."]


def 기록():
    ev, cx = [], []
    # Claude 앱 표 → Word (칸마다 문단)
    cx.append({"ts": T("33:47"), "source": "desktop", "kind": "ai_answer_excerpt", "text": TABLE, "meta": {"tool": "Claude 앱", "domain": "claude"}})
    ev += [{"ts": T("33:47"), "type": "copy", "hash": h(TABLE), "app": "Claude", "category": "ai", "len": len(TABLE)},
           {"ts": T("33:48"), "type": "paste", "hash": h(TABLE), "app": "Microsoft Word", "len": len(TABLE)},
           {"ts": T("33:48"), "type": "doc_paste_at", "app": "Word", "file": F, "where": "문단 6"}]
    for i, t in enumerate(["구분", "현황", "M6", "2026년 하반기 예상", "저가형 라인", "아이폰용 칩을 사용"], 1):
        cx.append({"ts": T("33:48"), "source": "office", "kind": "diff", "text": t, "meta": {"app": "Word", "file": F, "where": f"문단 {i}"}})
    # Claude 답을 구글 검색창에 질문으로 붙여넣음 (문서 아님)
    cx.append({"ts": T("35:03"), "source": "desktop", "kind": "ai_answer_excerpt", "text": CLAUDE, "meta": {"tool": "Claude 앱", "domain": "claude"}})
    ev += [{"ts": T("35:03"), "type": "copy", "hash": h(CLAUDE), "app": "Claude", "category": "ai", "len": len(CLAUDE)},
           {"ts": T("35:09"), "type": "paste", "hash": h(CLAUDE), "app": "Google Chrome", "len": len(CLAUDE)}]
    # 구글 답 3문단을 한 번에 Word 로 — 커서는 마지막 문단
    g = "\n".join(GOOGLE)
    ev += [{"ts": T("36:20"), "type": "tab", "domain": "google.com", "category": "other"},
           {"ts": T("36:26"), "type": "copy", "hash": h(g), "app": "Google Chrome", "category": "other", "len": len(g)},
           {"ts": T("36:28"), "type": "paste", "hash": h(g), "app": "Microsoft Word", "len": len(g)},
           {"ts": T("36:29"), "type": "doc_paste_at", "app": "Word", "file": F, "where": "문단 10"}]
    for i, t in enumerate(GOOGLE, 8):
        cx.append({"ts": T("36:29"), "source": "office", "kind": "diff", "text": t, "meta": {"app": "Word", "file": F, "where": f"문단 {i}"}})
    return ev, cx


def main():
    ev, cx = 기록()
    groups = M.paste_groups(ev, cx)
    check("① 붙여넣기 한 번 = 그 순간 들어온 문단 전부", [len(ds) for _, _, ds in groups] == [6, 3], [len(ds) for _, _, ds in groups])
    proc = M.process_evidence(ev, cx)
    check("① 붙여넣은 문단은 '쓴 과정 기록 없음' 이 아님", proc["noproc"] == [], proc["noproc"])
    other = M.pasted_from_other(ev, cx)
    check("① 다른 곳 붙여넣기 글 = 세 문단 전부 · 출처 google.com", len(other) == 1 and other[0]["text"] == "\n".join(GOOGLE)
          and other[0]["source"] == "google.com", other)
    ai = M.pasted_from_ai(ev, cx)
    check("② 구글 검색창에 붙여넣은 Claude 답은 문서 붙여넣기가 아님", len(ai) == 1 and ai[0]["text"] == TABLE, [a["text"][:20] for a in ai])
    answers = [{"id": 0, "text": CLAUDE + "\n" + TABLE, "ts": T("33:40"), "asked": T("33:27")}]
    # 문서 = 표(칸마다 문단) → 구글 답 세 문단 → 직접 쓴 소감 (실제 보고서와 같은 차례)
    rows = M.link_document(["M6", "2026년 하반기 예상", "저가형 라인", "아이폰용 칩을 사용",
                            "핵심 기술 트렌드 및 전망 (M6 칩셋 중심)", GOOGLE[1], GOOGLE[2], "느낀 점: 직접 쓴 소감입니다."],
                           answers, pasted=ai, others=other, proc=proc)
    라벨 = [r["label"] for row in rows for r in row]
    check("③ 표 칸 = Claude 답 붙여넣기 (짧은 칸 \"M6\" · \"저가형 라인\" 까지)",
          라벨[0] == 라벨[2] == "exact" and all(l in ("exact", "edited") for l in 라벨[:4]), 라벨)
    check("① 구글 답 문단 = 다른 곳 (Claude 답과 비슷해도)", 라벨[4:7] == ["web"] * 3, 라벨)
    check("직접 쓴 글 = 출처 기록 없음", 라벨[7] == "none", 라벨)
    # ③ 맥: 키 입력 이벤트의 app 이 "Microsoft Word" (윈도우는 WINWORD.EXE) — 11/2 맥에서 직접 친 글이 전부 "키 입력 없음" 으로 보였다
    친글 = "해시 체인이란 데이터를 반복해서 해시하는 구조다."
    for app, 이름 in (("Microsoft Word", "맥"), ("WINWORD.EXE", "윈도우")):
        p = M.process_evidence([{"ts": T("40:07"), "type": "keys", "count": 60, "app": app, "category": "work"}],
                               [{"ts": T("40:11"), "source": "office", "kind": "diff", "text": 친글, "meta": {"app": "Word", "file": F, "where": "문단 4"}}])
        check(f"③ {이름} Word 에서 친 글 = 타이핑 (쓴 과정 기록 없음 아님)", p["typed"] == [친글] and p["noproc"] == [], p)
    # ④ AI 앱에서 복사해 그대로 붙였는데 원래 답이 기록에 없음 (11/2 실제: ChatGPT 앱 보고서 답이 빠짐) → 글자 조각만 겹치는
    #    다른 답에 "고침" 으로 잇지 않고 "AI 에서 그대로 붙여넣음 · 대화 기록 없음"
    다른답 = "해시 테이블은 키를 해시 함수로 변환해 데이터를 빠르게 저장하고 찾는 자료구조야."
    공식 = "H₂ = 해시(H₁ || 데이터₂)"
    cx4 = [{"ts": T("50:01"), "source": "desktop", "kind": "ai_answer_excerpt", "text": 공식, "meta": {"tool": "ChatGPT 앱", "domain": "chatgpt"}}]
    ev4 = [{"ts": T("50:01"), "type": "copy", "hash": h(공식), "app": "ChatGPT", "category": "ai", "len": len(공식)},
           {"ts": T("50:02"), "type": "paste", "hash": h(공식), "app": "Microsoft Word", "len": len(공식)},
           {"ts": T("50:02"), "type": "doc_paste_at", "app": "Word", "file": F, "where": "문단 1"}]
    줄 = M.link_document([공식], [{"id": 0, "text": 다른답, "ts": T("40:00"), "asked": T("39:50")}],
                        M.pasted_from_ai(ev4, cx4), M.pasted_from_other(ev4, cx4), M.process_evidence(ev4, cx4))[0][0]
    check("④ 원래 답이 없는 AI 붙여넣기 = 그대로 붙여넣음 (엉뚱한 답에 '고침' 으로 안 이음)",
          줄["label"] == "web" and 줄["answer"] is None and 줄["paste"]["category"] == "ai" and 줄["paste"]["source"] == "chatgpt", 줄)
    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
