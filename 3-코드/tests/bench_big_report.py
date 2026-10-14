"""
bench_big_report.py — 아주 큰 과제(논문 ~100쪽)를 AI 앱 · 웹을 오가며 쓴 하루치 기록을 만들어 PC 앱 분석이 얼마나 걸리는지 잰다 (10/14)

  python 3-코드/tests/bench_big_report.py                 # 기록 만들기 + 단계별 시간
  python 3-코드/tests/bench_big_report.py --pages 22      # 22쪽 (상진이 실제 시험 크기)
  python 3-코드/tests/bench_big_report.py --profile       # 가장 오래 걸린 함수 30개
  python 3-코드/tests/bench_big_report.py --pages 22 --chat 1500   # AI 와 아주 많이 대화한 학생

만드는 기록 (수집기와 같은 모양 · 임시 폴더):
  · AI 질문 · 답 160쌍 — Claude 앱(데스크톱) · ChatGPT 웹 · Gemini 웹 · 구글 AI 모드
  · 문서: 열 때 이미 있던 글(AI 가 만든 Word) · AI 답 붙여넣기(여러 문단 · 고친 것) · 다른 웹 붙여넣기 · 직접 친 글 · AI 답 보고 친 글
  · 8시간 동안의 창 · 키 · 하트비트 · 복사 · 붙여넣기 · Word 글 변화
  · (--days) 같은 PC 의 다른 날 · 다른 과제 기록 — 한 학기 쌓인 기록에서 이 과제만 골라 읽는 시간까지
글자는 진짜 한국어처럼 보이는 낱말 조각으로 만든다 — 서로 다른 문장은 거의 안 겹치고, 같은 답에서 온 문장만 겹친다.
"""
import argparse
import hashlib
import io
import json
import os
import random
import runpy
import shutil
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KST = timezone(timedelta(hours=9))


def sha(t):
    return "sha256:" + hashlib.sha256(t.encode("utf-8", "surrogatepass")).hexdigest()


class 기록기:
    """수집기 흉내 — 같은 이름 · 같은 칸으로 파일에 쓴다 (체인 해시는 PC 분석이 안 보므로 생략)"""

    def __init__(self, d, sid, wid, t0):
        self.d, self.sid, self.wid, self.t, self.n = d, sid, wid, t0, 0
        self.ev, self.cx, self.msg = [], [], []

    def ts(self):
        return self.t.isoformat(timespec="seconds")

    def 흐름(self, sec):
        self.t += timedelta(seconds=sec)

    def e(self, typ, **kw):
        self.n += 1
        self.ev.append({"id": f"evt_{self.n:06d}", "session_id": self.sid, "ts": self.ts(), "source": "collector", "type": typ, **kw})
        return self.ev[-1]["id"]

    def c(self, source, kind, text, **meta):
        self.cx.append({"session_id": self.sid, "id": f"cx{len(self.cx)}", "ts": self.ts(), "source": source, "kind": kind, "text": text, "meta": meta})

    def 저장(self, 덧붙이기=False):
        day = self.t.strftime("%Y-%m-%d")
        for 이름, rows in (("events", self.ev), ("context", self.cx), ("ai-messages", self.msg)):
            with open(os.path.join(self.d, f"{이름}-{day}.jsonl"), "a" if 덧붙이기 else "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")


def 낱말들(r, n=2500):
    음절 = [chr(c) for c in range(0xAC00, 0xD7A4, 37)][:260]
    return sorted({"".join(r.choice(음절) for _ in range(r.randint(2, 4))) for _ in range(n)})   # 정렬 — set 차례는 실행마다 달라서 같은 기록이 안 나옴


def 문장(r, W, a=6, b=14):
    s = " ".join(r.choice(W) for _ in range(r.randint(a, b)))
    return s + r.choice(["다.", "니다.", "있다.", "된다.", "것이다."])


def 고치기(r, W, s, 비율=0.25):
    """AI 답 문장을 학생이 고친 것 — 낱말 몇 개를 바꾸거나 빼거나 더함"""
    w = s.split()
    for i in range(len(w)):
        if r.random() < 비율:
            w[i] = r.choice(W)
    return " ".join(w)


def 만들기(d, pages=100, days=30, seed=1, chat=0):
    r = random.Random(seed)
    W = 낱말들(r)
    wid, sid = "W-bench", "sess-bench"
    g = 기록기(d, sid, wid, datetime(2026, 10, 14, 9, 0, 0, tzinfo=KST))
    g.e("session_start", work_id=wid, idle_after_sec=300.0)
    목표 = pages * 26                                       # 쪽당 문장 26개 (한국어 A4 · 10pt 정도)
    문서, 답들 = [], []                                     # 문단 글 · (도구, 답 문장들)
    도구 = [("Claude 앱", "desktop", "claude", "Claude"), ("ChatGPT", "browser", "chatgpt.com", "Google Chrome"),
           ("Gemini", "browser", "gemini.google.com", "Google Chrome"), ("Google AI 모드", "browser", "google.com/ai", "Google Chrome")]
    파일 = "논문.docx"

    def 창(app, cat, title=""):
        g.e("window", app=app, title=title, category=cat)

    def 키(n, app="Microsoft Word"):
        g.e("keys", count=n, deleted=r.randint(0, n // 6), app=app, category="work")

    def 묻기():
        tool, src, dom, app = r.choice(도구)
        창(app, "ai", f"{tool} - 대화")
        if src == "browser":
            g.e("tab", domain=dom, category="ai", title=tool)
        q = 문장(r, W, 5, 10).replace("다.", "?")
        g.흐름(r.randint(10, 40))
        답 = [문장(r, W) for _ in range(r.randint(10, 22))]
        for role, text in (("question", q), ("answer", "\n".join(답))):
            eid = g.e("ai_msg", tool=tool, conv=f"conv{len(답들)}", turn=1, role=role, len=len(text), hash=sha(text))
            g.msg.append({"session_id": sid, "event_id": eid, "ts": g.ts(), "seen_at": g.ts(), "tool": tool, "model": "",
                          "conv": f"conv{len(답들)}", "turn": 1, "role": role, "hash": sha(text), "masked": 0,
                          "history": False, "url": "", "text": text})
            g.흐름(r.randint(5, 30))
        답들.append((tool, src, dom, app, 답))
        return 답들[-1]

    def 붙이기(글, 출처):
        """문단 여러 개를 한 번에 붙여넣기 — 붙여넣기 · 그 순간 문단마다 diff · 커서 문단 doc_paste_at"""
        tool, src, dom, app, kind = 출처
        text = "\n".join(글)
        h = sha(text)
        if kind == "ai":
            g.c(src if src == "desktop" else "browser", "ai_answer_excerpt", text, tool=tool, domain=dom)
        g.e("copy", len=len(text), hash=h, app=app, category="ai" if kind == "ai" else "other")
        g.흐름(r.randint(1, 4))
        창("Microsoft Word", "work", 파일)
        g.e("paste", len=len(text), hash=h, app="Microsoft Word", target_title=파일)
        g.흐름(1)
        for t in 글:
            문서.append(t)
            g.e("doc_change", app="Word", file=파일, where=f"문단 {len(문서)}", added=len(t), removed=0)
            g.c("office", "diff", t, app="Word", file=파일, where=f"문단 {len(문서)}")
        g.e("doc_paste_at", app="Word", file=파일, where=f"문단 {len(문서)}")
        g.c("office", "paste_at", 문서[-1][:200], app="Word", file=파일, where=f"문단 {len(문서)}")

    def 치기(글):
        """한 문단을 직접 친다 — 5초마다 15자 정도씩 diff · 10초마다 키 횟수"""
        창("Microsoft Word", "work", 파일)
        문서.append("")
        i = len(문서)
        for k in range(0, len(글), 15):
            조각 = 글[k:k + 15]
            문서[-1] += 조각
            g.흐름(5)
            g.e("doc_change", app="Word", file=파일, where=f"문단 {i}", added=len(조각), removed=0)
            g.c("office", "diff", 조각, app="Word", file=파일, where=f"문단 {i}")
            if k % 30 == 0:
                키(len(조각) * 5)

    for _ in range(chat):                                    # (--chat) 보고서에 안 쓴 AI 대화 — 질문을 아주 많이 한 학생
        묻기()
    # ① 열 때 이미 있던 글 (AI 가 만든 Word 를 받아 시작한 부분 · 15%)
    처음 = [" ".join(문장(r, W) for _ in range(3)) for _ in range(int(목표 * 0.15 / 3))]
    문서 += 처음
    창("Microsoft Word", "work", 파일)
    g.c("office", "doc_open", "\n".join(처음), app="Word", file=파일, chars=sum(map(len, 처음)))
    hb = g.t
    while sum(t.count("다.") + t.count("니다.") for t in 문서) < 목표:
        x = r.random()
        if x < 0.35:                                         # AI 답 붙여넣기 (여러 문단 · 가끔 고침)
            tool, src, dom, app, 답 = 묻기()
            k = r.randint(0, max(0, len(답) - 6))
            조각 = 답[k:k + r.randint(2, 6)]
            글 = [" ".join(조각[j:j + 2]) for j in range(0, len(조각), 2)]
            붙이기(글, (tool, src, dom, app, "ai"))
            if r.random() < 0.3:                             # 붙여넣은 문단 하나를 고침
                j = len(문서) - 1
                새 = 고치기(r, W, 문서[j], 0.2)
                g.흐름(20)
                g.e("doc_change", app="Word", file=파일, where=f"문단 {j + 1}", added=len(새) // 4, removed=len(새) // 5)
                g.c("office", "diff", 새[: len(새) // 4], app="Word", file=파일, where=f"문단 {j + 1}")
                키(len(새))
                문서[j] = 새
        elif x < 0.45:                                       # 다른 웹 붙여넣기
            dom = r.choice(["namu.wiki", "ko.wikipedia.org", "scholar.google.com", "blog.naver.com"])
            창("Google Chrome", "other", dom)
            g.e("tab", domain=dom, category="other", title=dom)
            g.흐름(r.randint(20, 90))
            붙이기([" ".join(문장(r, W) for _ in range(2)) for _ in range(r.randint(1, 4))], ("", "", dom, "Google Chrome", "web"))
        elif x < 0.7:                                        # 직접 친 글
            치기(" ".join(문장(r, W) for _ in range(r.randint(2, 4))))
        else:                                                # AI 답을 보고 고쳐 친 글
            if not 답들:
                묻기()
            답 = r.choice(답들)[4]
            k = r.randint(0, len(답) - 2)
            치기(" ".join(고치기(r, W, s, 0.3) for s in 답[k:k + 2]))
        while (g.t - hb).total_seconds() >= 30:
            hb += timedelta(seconds=30)
            g.e("heartbeat")
    g.e("doc_save", app="Word", file=파일, chars=sum(map(len, 문서)), words=sum(len(t.split()) for t in 문서), paragraphs=len(문서))
    g.e("session_end")
    g.저장()
    # ② 같은 PC 의 다른 날 · 다른 과제 기록 (한 학기 쌓임)
    for k in range(days):
        o = 기록기(d, f"sess-other-{k}", f"W-other-{k % 5}", datetime(2026, 9, 10, 10, tzinfo=KST) + timedelta(days=k))
        o.e("session_start", work_id=o.wid, idle_after_sec=300.0)
        for _ in range(2000):
            o.흐름(10)
            (o.e("heartbeat") if r.random() < 0.5 else o.e("keys", count=r.randint(5, 60), deleted=2, app="Microsoft Word", category="work"))
            if r.random() < 0.2:
                o.c("office", "diff", 문장(r, W, 2, 4), app="Word", file="다른.docx", where="문단 1")
        o.e("session_end")
        o.저장()
    return 문서, 답들, g


def docx(paragraphs, path):
    from xml.sax.saxutils import escape
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{escape(p)}</w:t></w:r></w:p>' for p in paragraphs)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                   f"<w:body>{body}</w:body></w:document>")


def 앱_불러오기(d):
    """PC 앱 화면 서버(statement.py)를 main 없이 불러 이 데이터 폴더를 보게 한다"""
    sys.path[:0] = [ROOT, os.path.join(ROOT, "app"), os.path.join(ROOT, "collector")]
    sys.argv = ["bench"]
    g = runpy.run_path(os.path.join(ROOT, "app", "statement.py"), run_name="bench")
    g["설정"].update(data_dir=d, server="http://127.0.0.1:9/api", config=None)
    import source as S
    return g, S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=100)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--chat", type=int, default=0, help="보고서에 안 쓴 AI 질문 · 답을 이만큼 더 (질문을 아주 많이 한 학생)")
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--keep", help="기록을 남길 폴더 (없으면 임시)")
    ap.add_argument("--dump", help="출처 분석 결과(JSON)를 이 파일에 — 고치기 전 · 뒤 결과가 같은지 비교용")
    ap.add_argument("--screens", action="store_true", help="실제 화면 요청(출처 보기 · 연결 확인 · 내보내기 · PDF 미리 보기 · 홈 · 돌아보기)까지")
    a = ap.parse_args()
    d = a.keep or tempfile.mkdtemp(prefix="trace-bench-")
    os.makedirs(d, exist_ok=True)
    t = time.perf_counter()
    문서, 답들, g = 만들기(d, a.pages, a.days, chat=a.chat)
    크기 = sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d))
    문장수 = sum(t.count("다.") + t.count("니다.") for t in 문서)
    print(f"기록 만듦 {time.perf_counter() - t:.1f}초 · 문단 {len(문서)} · 문장 약 {문장수} · 글자 {sum(map(len, 문서)):,} · AI 답 {len(답들)} · "
          f"이 과제 이벤트 {len(g.ev):,} · 맥락 {len(g.cx):,} · 폴더 전체 {크기 / 1e6:.1f}MB ({a.days}일 더)")
    path = os.path.join(d, "논문.docx")
    docx(문서, path)
    G, S = 앱_불러오기(d)
    from core.docx import read_docx
    시간 = {}

    def 재기(이름, f):
        t0 = time.perf_counter()
        r = f()
        시간[이름] = time.perf_counter() - t0
        return r
    세션 = 재기("과제별 세션 찾기 (_과제별_세션)", G["_과제별_세션"])
    rec = 재기("이 과제 기록 읽기 (과제_기록)", lambda: S.과제_기록("W-bench"))
    paras = 재기("Word 읽기", lambda: read_docx(path))
    msgs, events, context, _ = rec
    if a.profile:
        import cProfile
        import pstats
        pr = cProfile.Profile()
        pr.enable()
    out = 재기("출처 분석 (source.build · 처음)", lambda: S.build(paras, msgs, events, context))
    if a.profile:
        pr.disable()
    재기("출처 분석 (다시 · 기억)", lambda: S.build(paras, msgs, events, context))
    if a.dump:
        with open(a.dump, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, sort_keys=True, default=str)
    if a.screens:                                            # 학생이 실제로 누르는 차례 — 앱 화면 서버에 요청 (서버 없이 · 로그인 없이)
        c = G["app"].test_client()
        H = {"Host": "127.0.0.1:5079", "X-Trace-Local": "1"}
        S._결과.clear()                                       # 출처 분석 기억을 비우고 처음부터
        raw = open(path, "rb").read()

        def 요청(이름, f):
            r = 재기(이름, f)
            if r.status_code >= 400:
                print(f"  ! {이름} HTTP {r.status_code} {r.get_data(as_text=True)[:120]}")
        요청("화면: 출처 보기 (파일 열기 · 처음)", lambda: c.post("/local/source", headers=H, data={"work_id": "W-bench", "file": (io.BytesIO(raw), "논문.docx")},
                                                       content_type="multipart/form-data"))
        요청("화면: 연결 확인", lambda: c.post("/local/confirm", headers=H, data={"work_id": "W-bench"}))
        요청("화면: 내보내기", lambda: c.post("/local/export", headers=H, data={"work_id": "W-bench"}))
        요청("화면: PDF 미리 보기", lambda: c.get("/local/export/preview?work_id=W-bench", headers=H))
        요청("화면: 홈 카드", lambda: c.get("/local/home/card?work_id=W-bench", headers=H))
    import collections
    print("결과:", dict(collections.Counter(s.get("kind") for s in out["sentences"])))
    for k, v in 시간.items():
        print(f"  {v:7.2f}초  {k}")
    if a.profile:
        pstats.Stats(pr).sort_stats("cumulative").print_stats(30)
    if not a.keep:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
