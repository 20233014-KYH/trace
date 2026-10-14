"""
test_mac_capture.py — 맥 기록 (Word · PowerPoint AppleScript · 데스크톱 AI 앱 손쉬운 사용) 를 앱 없이 시험 (10/14)

  python 3-코드/collector/test_mac_capture.py       # 맥에서. 실제 앱 · 권한 없이 — 앱이 돌려줄 글을 흉내 낸다

실제 앱으로 본 것 (10/14 김용현 맥): Word 문단 추가 → doc_change +21자 · PowerPoint 도형 글 · Claude 앱 화면 → ai_msg
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
if sys.platform != "darwin":
    print("  맥에서만 돈다 — 건너뜀")
    sys.exit(0)

import desktop_ai_mac as D       # noqa: E402
import office_mac as O           # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 맞음, 덧=""):
    global 통과, 실패
    통과, 실패 = 통과 + bool(맞음), 실패 + (not 맞음)
    print(f"  {'✓' if 맞음 else '✗'} {이름}  {'' if 맞음 else 덧}")


def word_out(name, path, saved, sel, *paras):
    return O.SEP.join([name, path, "true" if saved else "false", str(sel), "\r".join(paras) + "\r"])


def 오피스():
    ev, ctx, paths = [], [], []
    w = O.MacOfficeWatcher(ev.append, lambda a: True, poll_sec=1, emit_context=ctx.extend, emit_path=lambda *a: paths.append(a))
    나올 = []
    O._실행 = lambda script, timeout=8: 나올.pop(0)
    문서 = os.path.abspath(__file__)                           # 실제로 있는 파일 = 저장된 문서인 척
    나올.append(word_out("과제.docx", 문서, True, 0, "첫 문단", "둘째 문단"))
    w._tick_word()
    검사("1 Word 처음 읽기 → doc_open (PC 에만) · 위치", ctx and ctx[-1]["kind"] == "doc_open" and paths == [("Word", "과제.docx", 문서)], ctx)
    나올.append(word_out("과제.docx", 문서, False, 0, "첫 문단", "둘째 문단 AI 답을 붙여넣음", "셋째"))
    w._tick_word()
    바뀜 = [e for e in ev if e["type"] == "doc_change"]
    검사("2 문단이 바뀌고 늘면 doc_change (+n자)", [b["where"] for b in 바뀜] == ["문단 2", "문단 3"] and 바뀜[0]["added"] == len(" AI 답을 붙여넣음"), 바뀜)
    w.on_paste("Microsoft Word")
    나올.append(word_out("과제.docx", 문서, True, len("첫 문단\r둘째"), "첫 문단", "둘째 문단 AI 답을 붙여넣음", "셋째"))
    w._tick_word()
    검사("3 붙여넣은 자리 = 커서가 있는 문단", any(e["type"] == "doc_paste_at" and e["where"] == "문단 2" for e in ev), ev[-3:])
    검사("4 저장하면 doc_save (글자 · 단어 수)", any(e["type"] == "doc_save" and e["words"] == 8 for e in ev), ev[-2:])
    나올.append(O.SEP.join(["발표.pptx", "", "true", "1", "2", "1:Title 1\x1f제목", "2:Text 2\x1f본문 글\r둘째 줄"]) + "\n")
    w._tick_ppt()
    검사("5 PowerPoint 슬라이드 · 도형 글 (저장 전 문서는 위치 없음)",
         ctx[-1]["kind"] == "doc_open" and ctx[-1]["text"] == "제목\n본문 글\n둘째 줄" and len(paths) == 1, ctx[-1])
    나올.append("")
    w._tick_word()
    검사("6 열린 문서가 없으면 조용히 넘어감", True)
    w._오류(RuntimeError("execution error: Not authorized to send Apple events to Microsoft Word. (-1743)"))
    검사("7 자동화 권한 거부는 한 번만 안내", w._거부 == {"자동화"})


class F:
    """가짜 화면 요소 → desktop_ai_mac._N 과 같은 모양"""
    def __init__(self, role, cls="", text="", kids=(), desc="", sub=""):
        self.a = {"AXRole": role, "AXDOMClassList": cls.split(), "AXValue": text if role == "AXStaticText" else "",
                  "AXTitle": "" if role == "AXStaticText" else text, "AXRoleDescription": desc, "AXSubrole": sub}
        self.kids = list(kids)


def 나무(f, parent=None):
    n = D._N(f.a, parent)
    n.kids = [나무(k, n) for k in f.kids]
    return n


def 데스크톱():
    질문 = F("AXGroup", "font-user-message", kids=[F("AXGroup", kids=[F("AXStaticText", text="정규화가 뭐야?")])])
    답 = F("AXGroup", "font-claude-response", kids=[
        F("AXGroup", "standard-markdown", kids=[
            F("AXGroup", kids=[F("AXStaticText", text="정규화는 "), F("AXStaticText", text="중복을 줄이는 과정")]),
            F("AXGroup", kids=[F("AXStaticText", text="1NF 는 원자값")]),
        ]),
        F("AXGroup", "sr-only", kids=[F("AXStaticText", text="Claude 응답:")]),
        F("AXButton", text="복사", kids=[F("AXStaticText", text="복사")]),
        F("AXGroup", desc="time", kids=[F("AXStaticText", text="3분 전")]),
    ])
    web = F("AXWebArea", text="정규화 공부 - Claude", kids=[F("AXGroup", kids=[질문, 답])])
    root = 나무(F("AXWindow", text="Claude", kids=[web]))
    got = []
    w = D.MacDesktopAIWatcher(got.extend, {}, poll_sec=1)
    msgs = w._찾기(root)
    검사("8 Claude 앱: 클래스로 질문 · 답 (안의 standard-markdown 은 또 안 셈)", [h for _, h in msgs] == ["question", "answer"], msgs)
    role, text = w._글(msgs[1][0], msgs[1][1])
    검사("9 답 글: 문단은 줄바꿈 · 버튼 · 시각 · 화면낭독 글은 뺌", (role, text) == ("answer", "정규화는 중복을 줄이는 과정\n1NF 는 원자값"), repr(text))
    검사("10 대화 이름 = 웹 화면 제목", w._대화(msgs[1][0], None) == "정규화 공부 - Claude")
    w._empty_at = time.time()                                  # 새 채팅에서 막 생긴 대화 → 이전 대화 아님
    items = [(f"c|{i}|{h}", h, w._글(n, h)[1]) for i, (n, h) in enumerate(msgs)]
    w._send("claude", "정규화 공부 - Claude", items)
    검사("11 처음 한 번 본 글은 아직 안 보냄 (생성 중일 수 있음)", got == [])
    w._send("claude", "정규화 공부 - Claude", items)
    검사("12 두 번 연속 같으면 보냄 → 도구 'Claude 앱' · domain claude · 새 대화",
         [g["kind"] for g in got] == ["ai_question", "ai_answer"] and got[1]["meta"]["tool"] == "Claude 앱"
         and got[1]["meta"]["domain"] == "claude" and got[1]["meta"]["history"] is False, got)
    article = F("AXGroup", "feed-x", desc="feed", kids=[
        F("AXGroup", sub="AXDocumentArticle", kids=[F("AXHeading", "sr-only", kids=[F("AXStaticText", text="입력 내용: 안녕")]),
                                                   F("AXGroup", kids=[F("AXStaticText", text="안녕")])])])
    msgs = w._찾기(나무(F("AXWindow", kids=[article])))
    검사("13 클래스가 없으면 feed 안 article + 화면낭독 제목으로 질문", msgs and w._글(*msgs[0]) == ("question", "안녕"), msgs)


if __name__ == "__main__":
    print("  맥 기록 시험 — Word · PowerPoint · 데스크톱 AI 앱 (흉내)\n  " + "─" * 70)
    오피스()
    데스크톱()
    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    sys.exit(1 if 실패 else 0)
