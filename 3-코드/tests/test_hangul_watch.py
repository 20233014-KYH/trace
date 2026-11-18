"""
test_hangul_watch.py — 한글 저장할 때마다 문서 변화 (collector/hangul.py · 11/18)

한글 없이 — .hwpx 파일을 직접 만들고 고쳐 저장하면서 기록기가 내는 것을 본다:
  ① 기록을 켠 뒤 만든 문서 = 빈 문서에서 시작 → 쓴 글이 모두 글 변화(diff) · '열 때 있던 글' 아님
  ② 저장해 바뀌면 그 문단만 · 저장 안 하면 그대로 · 글 변화에 since(앞 저장 시각)
  ③ 그 사이 한글 키 입력이 충분하면 직접 친 글 · 없으면 쓴 과정 기록 없음 · 붙여넣기가 많으면 둘 다 아님
  ④ 원래 있던 파일 = 그때 글이 '열 때 있던 글'
  ⑤ 창 제목에서 파일 이름 · 한글 앱 이름 알아보기

  python 3-코드/tests/test_hangul_watch.py
"""
import io
import os
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "collector"))
import hangul as HG                               # noqa: E402
from core import match as M                       # noqa: E402

통과, 실패 = 0, 0
NS = 'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'


def 검사(이름, 조건, 덧=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✓' if 조건 else '✗'} {이름} {덧}")


def 저장(path, 문단들):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("Contents/section0.xml", f"<hs:sec {NS}>" + "".join(f"<hp:p><hp:run><hp:t>{t}</hp:t></hp:run></hp:p>" for t in 문단들) + "</hs:sec>")
    with open(path, "wb") as f:
        f.write(b.getvalue())
    st = os.stat(path)
    os.utime(path, (st.st_atime, st.st_mtime + 0.01 * len(문단들)))        # 같은 초 안에 저장해도 mtime 이 바뀌게


def 기록기(path, started):
    ev, ctx, paths = [], [], []
    w = HG.HangulWatcher(ev.append, lambda: ("한컴오피스 한글", os.path.basename(path) + " - 한컴오피스 한글"), poll_sec=0.1,
                         emit_context=ctx.extend, emit_path=lambda a, f, p: paths.append((a, f, p)), started_at=started)
    w._문서_경로 = lambda title: path
    return w, ev, ctx, paths


def main():
    print("\n  한글 저장할 때마다\n  " + "─" * 60)
    d = tempfile.mkdtemp(prefix="trace-hwp-")
    시작 = time.time() - 1
    p = os.path.join(d, "보고서.hwpx")
    저장(p, ["보고서 제목", "첫 문단을 직접 쳤다."])
    w, ev, ctx, paths = 기록기(p, 시작)
    w._tick(p)
    검사("① 기록 뒤 만든 문서 → 열 때 있던 글 없음 · 쓴 글이 모두 글 변화",
         not any(c["kind"] == "doc_open" for c in ctx) and [c["text"] for c in ctx if c["kind"] == "diff"] == ["보고서 제목", "첫 문단을 직접 쳤다."],
         str([(c["kind"], c["text"][:12]) for c in ctx]))
    검사("① 문서 위치(doc_path) 한 번", paths == [("한글", "보고서.hwpx", p)])
    검사("② 글 변화에 since (앞 저장 시각)", all(c["meta"].get("since") for c in ctx if c["kind"] == "diff"))
    n = len(ctx)
    w._tick(p)
    검사("② 저장 안 했으면 아무것도 안 냄", len(ctx) == n)
    time.sleep(1.1)
    저장(p, ["보고서 제목", "첫 문단을 직접 쳤다.", "둘째 문단은 AI 답을 붙여 넣었다고 치자."])
    w.on_paste("한컴오피스 한글")
    w._tick(p)
    새 = [c for c in ctx[n:] if c["kind"] == "diff"]
    검사("② 저장해 바뀐 문단만", [c["text"] for c in 새] == ["둘째 문단은 AI 답을 붙여 넣었다고 치자."], str([c["text"] for c in 새]))
    검사("② 붙여넣기가 있었으면 가장 늘어난 문단이 붙여넣은 자리", any(e["type"] == "doc_paste_at" and e["where"] == "문단 3" for e in ev))

    # ③ 직접 친 글 판단 — 저장 사이 한글 키 입력 (process_evidence)
    def 판단(키, 붙임=0, 글="저장 사이에 이만큼 글이 생겼다 정말로."):
        c = {"kind": "diff", "ts": "2026-11-18T15:10:00+09:00", "text": 글,
             "meta": {"app": "한글", "file": "보고서.hwpx", "where": "문단 2", "since": "2026-11-18T15:05:00+09:00"}}
        e = [{"type": "keys", "ts": "2026-11-18T15:07:00+09:00", "app": "한컴오피스 한글", "count": 키}]
        if 붙임:
            e.append({"type": "paste", "ts": "2026-11-18T15:08:00+09:00", "app": "한컴오피스 한글", "len": 붙임})
        pe = M.process_evidence(e, [c])
        return "typed" if pe["typed"] else "noproc" if pe["noproc"] else "neither"
    검사("③ 저장 사이 한글 키가 충분 → 직접 친 글", 판단(40) == "typed")
    검사("③ 키 입력이 없음 → 쓴 과정 기록 없음", 판단(0) == "noproc")
    검사("③ 키는 적고 붙여넣기가 대부분 → 둘 다 아님 (붙인 글)", 판단(1, 붙임=20) == "neither")

    q = os.path.join(d, "원래있던.hwpx")
    저장(q, ["전부터 있던 문단."])
    w2, ev2, ctx2, _ = 기록기(q, time.time() + 60)                  # 기록을 켜기 전에 만든 파일
    w2._tick(q)
    검사("④ 원래 있던 파일 → 그때 글 = 열 때 있던 글", [c["kind"] for c in ctx2 if c["kind"] != "doc_path"] == ["doc_open"]
         and ctx2[0]["text"] == "전부터 있던 문단.", str([c["kind"] for c in ctx2]))

    검사("⑤ 창 제목 → 파일 이름", (HG._제목_파일("보고서.hwp - 한글"), HG._제목_파일("과제 2.hwpx [C:\\Users\\a\\Documents\\] - 한글"),
                                HG._제목_파일("빈 문서 1 - 한글")) == ("보고서.hwp", "과제 2.hwpx", ""))
    검사("⑤ 한글 앱 이름 알아보기", all(HG.is_hangul(a) for a in ("Hwp.exe", "한컴오피스 한글", "Hancom Office HWP", "한글"))
         and not any(HG.is_hangul(a) for a in ("Microsoft Word", "WINWORD.EXE", "Google Chrome", "")))
    print("  " + "─" * 60 + f"\n  {'✓ 통과' if not 실패 else '✗ 실패'}  ({통과}개 통과 · {실패}개 실패)\n")
    sys.exit(1 if 실패 else 0)


if __name__ == "__main__":
    main()
