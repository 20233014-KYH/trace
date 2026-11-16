"""
test_desktop_sources.py — 데스크톱 AI 앱 답의 출처 링크 읽기 (11/16 · 교수님 피드백 "AI가 어디서 가져왔는지 표시")

진짜 앱 없이: 화면 요소 흉내(역할 · 이름 · Value)로 DesktopAIWatcher._read · _send 를 돌린다.
실행: python tests/test_desktop_sources.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "collector"), ROOT]
import desktop_ai as D   # noqa: E402

통과 = 실패 = 0


def check(name, ok, detail=""):
    global 통과, 실패
    통과, 실패 = 통과 + bool(ok), 실패 + (not ok)
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  {detail}" if detail and not ok else ""))


class El:
    """화면 요소 흉내 — 역할 · 이름 · 링크 주소(Value) · 자식"""
    def __init__(self, role="", name="", url=None, kids=(), cls=""):
        self.CurrentAriaRole, self.CurrentName, self.CurrentClassName, self.CurrentControlType = role, name, cls, 0
        self.url, self.kids, self.parent = url, list(kids), None
        for k in self.kids:
            k.parent = self

    def GetCurrentPropertyValue(self, pid):
        return self.url if pid == D.UIA_VALUE else None


class Walker:
    def GetFirstChildElement(self, e):
        return e.kids[0] if e.kids else None

    def GetNextSiblingElement(self, e):
        s = e.parent.kids if e.parent else []
        i = s.index(e)
        return s[i + 1] if i + 1 < len(s) else None

    def GetParentElement(self, e):
        return e.parent


def main():
    답 = El("article", kids=[
        El("heading", "ChatGPT 답변:", cls="sr-only"),
        El("paragraph", kids=[El("", "DLSS는 낮은 해상도로 그린 뒤 AI로 키우는 기술이다. "),
                              El("link", kids=[El("", "NVIDIA")], url="https://www.nvidia.com/ko-kr/dlss/?utm_source=chatgpt.com")]),
        El("paragraph", kids=[El("link", "위키백과 DLSS", url="https://ko.wikipedia.org/wiki/DLSS#top", kids=[El("", "위키백과")]),
                              El("link", "또", url="https://ko.wikipedia.org/wiki/DLSS", kids=[El("", " ")]),
                              El("link", "대화 공유", url="https://chatgpt.com/share/abc", kids=[El("", "")]),
                              El("link", "이 PC", url="http://localhost:3000/x", kids=[El("", "")]),
                              El("link", "주소 없음", url=None, kids=[El("", "")])]),
    ])
    보냄 = []
    w = D.DesktopAIWatcher(보냄.extend, {}, data_dir=".")
    w.W = Walker()
    role, text = w._read(답, None)
    check("앱 답의 글은 그대로 읽음 (링크 글자 포함)", role == "answer" and "AI로 키우는 기술이다. NVIDIA" in text and "위키백과" in text, text)
    check("답 안의 링크 = 출처 — 주소 정리(utm · # 뺌) · 같은 주소 한 번 · 앱 자기 주소 · 이 PC 주소 · 주소 없는 링크는 뺌",
          w._links == [{"title": "nvidia.com", "url": "https://www.nvidia.com/ko-kr/dlss/"},
                       {"title": "위키백과 DLSS", "url": "https://ko.wikipedia.org/wiki/DLSS"}], str(w._links))

    # 보내기 — 두 번 연속 같은 글이면 보낸다. 출처는 읽힌 답에만 붙고, 못 읽은 답엔 칸이 없다 (밝히지 않음으로 단정하지 않음)
    w._empty_at = 1e18                                                     # 새 채팅에서 막 생긴 대화
    w._src = {"c|0|answer": w._links, "c|1|answer": []}
    items = [("c|0|answer", "answer", "출처 있는 답"), ("c|1|answer", "answer", "링크 없는 답"), ("c|2|question", "question", "질문")]
    w._send("chatgpt.exe", "c", items)
    w._send("chatgpt.exe", "c", items)
    메타 = [x["meta"] for x in 보냄]
    check("보낼 때: 출처가 읽힌 답에만 sources · 링크 없는 답 · 질문엔 칸 없음",
          len(메타) == 3 and 메타[0].get("sources") == w._links and "sources" not in 메타[1] and "sources" not in 메타[2], str(메타))
    print(f"\n{'✓ 통과' if not 실패 else '✗ 실패'}  ({통과}개 통과 · {실패}개 실패)")
    return 실패 == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(0 if main() else 1)
