"""
test_readcheck.py — AI 화면을 읽지 못한 것 알아채기 (core/readcheck.py · 11/19 박상진)

  python 3-코드/tests/test_readcheck.py

"그 AI 에서 복사는 했는데, 같은 기록에 그 AI 의 질문 · 답이 하나도 없다" = 읽지 못함.
  · 웹(확장이 알려 준 탭) · 데스크톱 앱 · 확장이 없을 때 창 제목 · Trace 가 읽지 않는 AI 사이트
  · AI 가 아닌 곳의 복사 · 다른 기록의 질문 · 답은 안 셈
  · 실제 녹화 시험(fixtures)에서는 잘못 알리지 않음
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core.readcheck import read_gaps             # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✓' if 조건 else '✗'} {이름} {덧}")


def t(mmss, h="14"):
    return f"2026-11-19T{h}:{mmss}+09:00"


def 탭(s, ts, domain, cat="ai"):
    return {"session_id": s, "type": "tab", "ts": ts, "domain": domain, "category": cat}


def 창(s, ts, app, title="", cat="other"):
    return {"session_id": s, "type": "window", "ts": ts, "app": app, "title": title, "category": cat}


def 복사(s, ts, app, cat="other"):
    return {"session_id": s, "type": "copy", "ts": ts, "app": app, "category": cat, "len": 120}


def 답(s, tool):
    return {"session_id": s, "tool": tool, "role": "answer", "text": "…"}


def main():
    print("\n  AI 화면을 읽지 못한 것\n  " + "─" * 60)
    웹 = [창("S", t("00:00"), "chrome.exe", "ChatGPT - Chrome", "ai"), 탭("S", t("00:01"), "chatgpt.com"),
         복사("S", t("01:00"), "chrome.exe", "ai"), 복사("S", t("03:00"), "chrome.exe", "ai")]
    검사("웹 ChatGPT: 질문 · 답이 남았으면 알리지 않음", read_gaps(웹, [답("S", "ChatGPT")]) == [])
    g = read_gaps(웹, [])
    검사("웹 ChatGPT: 복사했는데 질문 · 답이 없으면 '읽지 못함'",
         g == [{"session": "S", "tool": "ChatGPT", "kind": "failed", "copies": 2, "first": t("01:00"), "last": t("03:00")}], json.dumps(g, ensure_ascii=False))
    검사("www · 하위 도메인도 같은 사이트", read_gaps([탭("S", t("00:00"), "www.chatgpt.com"), 복사("S", t("00:05"), "chrome.exe")], [])[0]["tool"] == "ChatGPT")

    앱 = [창("S", t("00:00"), "claude.exe", "Claude", "ai"), 복사("S", t("00:10"), "claude.exe", "ai")]
    검사("데스크톱 Claude 앱: 'Claude 앱' 질문 · 답이 있으면 알리지 않음", read_gaps(앱, [답("S", "Claude 앱")]) == [])
    검사("데스크톱 Claude 앱: 없으면 '읽지 못함'", [x["tool"] for x in read_gaps(앱, [답("S", "Claude")])] == ["Claude 앱"])
    검사("맥 앱 이름(ChatGPT)도", [x["tool"] for x in read_gaps([복사("S", t("00:10"), "ChatGPT", "ai")], [])] == ["ChatGPT 앱"])

    확장없음 = [창("S", t("00:00"), "chrome.exe", "Gemini - Google Chrome", "ai"), 복사("S", t("00:30"), "chrome.exe", "ai")]
    검사("확장이 없으면 창 제목으로 (Gemini)", [(x["tool"], x["kind"]) for x in read_gaps(확장없음, [])] == [("Gemini", "failed")])
    모름 = [창("S", t("00:00"), "chrome.exe", "어떤 AI - Chrome", "ai"), 복사("S", t("00:30"), "chrome.exe", "ai")]
    검사("창 제목으로도 모르는 AI 는 'AI 사이트' · 읽지 않는 것으로", [(x["tool"], x["kind"]) for x in read_gaps(모름, [])] == [("AI 사이트", "unsupported")])

    pplx = [탭("S", t("00:00"), "perplexity.ai"), 복사("S", t("00:20"), "chrome.exe", "ai")]
    검사("Trace 가 읽지 않는 AI 사이트 = 'unsupported'", [(x["tool"], x["kind"]) for x in read_gaps(pplx, [답("S", "ChatGPT")])] == [("perplexity.ai", "unsupported")])

    나무 = [탭("S", t("00:00"), "namu.wiki", "other"), 복사("S", t("00:20"), "chrome.exe", "other"), 복사("S", t("00:30"), "WINWORD.EXE", "work")]
    검사("AI 가 아닌 곳의 복사는 안 셈", read_gaps(나무, []) == [])

    떠남 = [탭("S", t("00:00"), "chatgpt.com"), 창("S", t("00:10"), "WINWORD.EXE", "보고서.docx - Word", "work"),
           창("S", t("00:20"), "chrome.exe", "DNS - 나무위키 - Chrome", "other"), 복사("S", t("00:21"), "chrome.exe", "other")]
    검사("브라우저를 떠났다 오면 지난 탭으로 세지 않음", read_gaps(떠남, []) == [])

    두기록 = 웹 + [{**e, "session_id": "S2"} for e in 웹]
    g2 = read_gaps(두기록, [답("S", "ChatGPT")])
    검사("기록마다 따로 — 다른 기록의 질문 · 답은 안 셈", [(x["session"], x["tool"]) for x in g2] == [("S2", "ChatGPT")])
    검사("글은 안 돌려줌 (이름 · 종류 · 수 · 시각만)", all(set(x) == {"session", "tool", "kind", "copies", "first", "last"} for x in g + g2))

    # 실제 녹화 시험 — 질문 · 답이 남은 기록에서 잘못 알리지 않는지
    FX = os.path.join(os.path.dirname(HERE), "tests", "fixtures")
    잘못 = {}
    for case in sorted(os.listdir(FX)):
        p = os.path.join(FX, case, "events.jsonl")
        if not os.path.exists(p):
            continue
        evs = [{**json.loads(l), "session_id": case} for l in open(p, encoding="utf-8") if l.strip()]
        msgs = [{"session_id": case, "tool": a.get("tool", "")} for a in
                (json.loads(l) for l in open(os.path.join(FX, case, "ai_answers.jsonl"), encoding="utf-8") if l.strip())]
        g = read_gaps(evs, msgs)
        if g:
            잘못[case] = [(x["tool"], x["kind"]) for x in g]
    검사("녹화 시험(fixtures)에서 잘못 알리지 않음", not 잘못, json.dumps(잘못, ensure_ascii=False))

    print("\n  " + "─" * 60 + f"\n  통과 {통과} · 실패 {실패}")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
