"""
test_issue26.py — 이슈 #26 (10/7 첫 연결·녹화 시험에서 찾은 문제) 고친 것 확인

  python tests/test_issue26.py

  ② Word 줄바꿈(<w:br/>)·탭(<w:tab/>)이 읽을 때 사라져 두 문장이 붙던 것
  ③ AI 답에서 붙여넣은 8자 미만 짧은 줄이 "출처 기록 없음" 이던 것 — 붙여넣은 원문 안에 그대로 있을 때만 잇는다
  ④ 생성 도중 잘린 답이 한 번 더 저장되던 것 — 기록기가 "replaces" 를 남기고, 연결·내역서는 잘린 답을 뺀다
  (① 확장 재주입은 크롬 안에서만 확인 가능 — extension/README · 확장 새로고침 뒤 열린 AI 탭에서 질문 1개)
"""
import importlib.util
import json
import os
import sys
import tempfile
import types
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "collector"))
from core import match as M          # noqa: E402

_spec = importlib.util.spec_from_file_location("p", os.path.join(HERE, "연결시제품.py"))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

fails = []


def check(name, ok, detail=""):
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


# ── ② Word 줄바꿈 ──
def test_docx_breaks():
    path = os.path.join(tempfile.mkdtemp(), "br.docx")
    body = ('<w:p><w:r><w:t>페이지를 한 번 만들면 다른 곳에도 확장하기가 쉽다.</w:t><w:br/><w:t>그리고 나중에 다시 고치기도 쉽다.</w:t></w:r></w:p>'
            '<w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="720"/></w:tabs></w:pPr><w:r><w:t>이름</w:t><w:tab/><w:t>하늘</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>첫 줄</w:t><w:br w:type="page"/><w:t>다음 쪽</w:t></w:r></w:p>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="w"><w:body>{body}</w:body></w:document>')
    paras = [t for _, t in P.read_docx(path)]
    check("② <w:br/> 가 줄바꿈으로 남아 두 문장으로 나뉨", M.split_sentences(paras[0]) ==
          ["페이지를 한 번 만들면 다른 곳에도 확장하기가 쉽다.", "그리고 나중에 다시 고치기도 쉽다."], repr(paras[0]))
    check("② 글 안의 <w:tab/> 은 탭 · 문단 설정의 탭 위치는 글자에 안 들어감", paras[1] == "이름\t하늘", repr(paras[1]))
    check("② 쪽 나눔(<w:br w:type=\"page\"/>)도 줄바꿈", paras[2] == "첫 줄\n다음 쪽", repr(paras[2]))


# ── ③ 붙여넣은 글 안의 짧은 줄 ──
def test_short_lines():
    answer = ("제 이름은 하늘이고 사진 찍는 걸 좋아합니다.\n나이: 24세\n어릴 때 친구가 이렇게 말했어요.\n"
              "\"너 사진 잘 찍는다.\"\n그때 처음으로 사진작가가 되고 싶다는 생각을 했어요.\n예를 들어 풍경 사진을 많이 찍었어요.")
    answers = [{"id": "A1", "text": answer}]
    pasted = [{"text": answer, "copied_at": "2026-10-07T15:36:17+09:00", "pasted_at": "2026-10-07T15:36:20+09:00", "where": "문단 2", "domain": "chatgpt.com"}]
    doc = ["어린 시절",                                    # 직접 친 짧은 제목 — 붙여넣은 글에 없음
           "제 이름은 하늘이고 사진 찍는 걸 좋아합니다.", "나이: 24세", "어릴 때 친구가 이렇게 말했어요.",
           "\"너 사진 잘 찍는다.\"", "그때 처음으로 사진작가가 되고 싶다는 생각을 했어요.",
           "아래는 내가 직접 쓴 문장이라서 붙여넣은 답과 관계가 없다.", "예를 들어",   # 붙여넣은 글에 있는 말이지만 앞뒤가 직접 쓴 문장
           "이 문장도 내가 직접 쓴 긴 문장이라서 붙여넣은 글과 상관없다."]
    got = {r["text"]: r for row in M.link_document(doc, answers, pasted) for r in row}
    for line in ("나이: 24세", "\"너 사진 잘 찍는다.\""):
        r = got[line]
        check(f"③ 붙여넣은 덩어리 안의 짧은 줄 '{line}' → 그 붙여넣기 · 일치",
              r["label"] == "exact" and r["full"] and r["paste"] is pasted[0] and r["answer"] == "A1", f"{r['label']} {r.get('sents')}")
    check("③ 짧은 줄이 칠할 원문 문장 위치도 맞음 (나이: 24세 → 원문 2번째 줄)", got["나이: 24세"]["sents"] == (1,), str(got["나이: 24세"]["sents"]))
    check("③ 직접 친 짧은 제목은 그대로 '기록 없음'", got["어린 시절"]["label"] == "none")
    check("③ 붙여넣은 글에 있는 말이라도 앞뒤가 직접 쓴 문장이면 잇지 않음", got["예를 들어"]["label"] == "none", got["예를 들어"]["label"])


# ── ④ 생성 도중 잘린 답 ──
def test_partial_answer():
    fake = types.ModuleType("platform_win")
    fake.foreground = lambda: ("", "")
    fake.idle_seconds = lambda: 0
    fake.input_permission_hint = lambda: None
    sys.modules["platform_win"] = fake
    real, sys.platform = sys.platform, "win32"
    import collector as C
    sys.platform = real
    with open(os.path.join(ROOT, "collector", "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["data_dir"] = tempfile.mkdtemp()
    c = C.Collector(cfg, "W_test", dry_run=True)
    full = "첫 문장입니다. 둘째 문장입니다. 셋째 문장은 끝까지 다 나온 완성본입니다."
    part = full[:24]
    meta = {"tool": "ChatGPT", "conv": "", "turn": 2}
    c._on_ai_msg({"kind": "ai_answer", "text": part, "meta": meta})
    c._on_ai_msg({"kind": "ai_answer", "text": full, "meta": meta})
    c._on_ai_msg({"kind": "ai_answer", "text": "다시 생성한 전혀 다른 답입니다.", "meta": meta})
    c.sink.close()
    recs = [json.loads(l) for f in os.listdir(cfg["data_dir"]) if f.startswith("ai-messages")
            for l in open(os.path.join(cfg["data_dir"], f), encoding="utf-8")]
    check("④ 기록기: 완성본이 잘린 답을 대체한다고 남김 (replaces)", len(recs) == 3 and recs[1].get("replaces") == recs[0]["hash"])
    check("④ 기록기: 다시 생성한 다른 답은 대체가 아님", "replaces" not in recs[2])
    kept = [r["text"] for r in M.latest_messages(recs)]
    check("④ 연결·내역서: 잘린 답은 빼고 완성본·다시 생성한 답만", kept == [full, "다시 생성한 전혀 다른 답입니다."], str([k[:10] for k in kept]))
    old = [{k: v for k, v in r.items() if k != "replaces"} for r in recs]          # replaces 가 없는 예전 기록
    check("④ 예전 기록(replaces 없음)도 앞 글을 품은 더 긴 답이 있으면 잘린 답을 뺌", [r["text"] for r in M.latest_messages(old)] == kept)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    test_docx_breaks()
    test_short_lines()
    test_partial_answer()
    print("✓ 통과" if not fails else f"✗ {len(fails)}건 실패")
    sys.exit(1 if fails else 0)
