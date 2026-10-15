"""
bench_server.py — 아주 큰 과제(논문 ~100쪽) 기록이 서버를 지날 때 얼마나 걸리나 · DB 를 몇 번 묻나 (10/14)

  python 3-코드/tests/bench_server.py               # 100쪽
  python 3-코드/tests/bench_server.py --pages 22
  python 3-코드/tests/bench_server.py --chat 1500           # AI 와 아주 많이 대화한 학생

bench_big_report.py 가 만든 기록을 그대로 쓴다 — 기록기처럼 50건씩 체인을 붙여 올리고, PC 앱의 [링크 · PDF 만들기]를 누른 뒤,
교수 화면 · PDF · 요약을 연다. 서버는 이 프로세스 안(Flask 시험 클라이언트) · DB 는 임시 SQLite.
★ 인터넷 서버(Render 무료 · 0.1 CPU)는 이 맥보다 느리고, Supabase 는 묻기마다 네트워크를 오간다 →
  시간은 '이 맥에서' 이고, DB 를 묻는 횟수가 많은 요청이 인터넷 서버에서 느려진다.
"""
import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT, os.path.join(ROOT, "server")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=100)
    ap.add_argument("--chat", type=int, default=0, help="보고서에 안 쓴 AI 질문 · 답을 이만큼 더")
    ap.add_argument("--mem", action="store_true", help="서버가 내역서를 받을 때 쓴 메모리 (Render 무료 512MB)")
    a = ap.parse_args()
    d = tempfile.mkdtemp(prefix="trace-bench-srv-")
    os.environ["TRACE_DB_URL"] = "sqlite:///" + os.path.join(d, "server.db")
    import bench_big_report as B
    문서, 답들, g = B.만들기(d, a.pages, days=0, chat=a.chat)
    B.docx(문서, os.path.join(d, "논문.docx"))
    import app as 서버앱                                     # 서버 (server/app.py)
    import db as 서버db
    from sqlalchemy import event
    from core import chain as C
    묻기 = {"n": 0, "글": []}
    import collections

    def 셈(conn, cur, statement, params, context, executemany):
        묻기["n"] += 1
        묻기["글"].append(" ".join(statement.split()[:4])[:70])
    event.listen(서버db.engine, "before_cursor_execute", 셈)
    s = 서버앱.app.test_client()
    시간 = []

    def 재기(이름, f):
        묻기["n"], 묻기["글"] = 0, []
        t0 = time.perf_counter()
        r = f()
        시간.append((이름, time.perf_counter() - t0, 묻기["n"], r))
        if 묻기["n"] > 100:
            print(f"  [{이름}] DB 많이 물은 것:", collections.Counter(묻기["글"]).most_common(6))
        return r

    s.post("/api/auth/signup", json={"email": "bench@test.kr", "password": "벤치비번12345", "name": "벤치"})
    tok = s.post("/api/auth/login", json={"email": "bench@test.kr", "password": "벤치비번12345"}).get_json()["token"]
    A = {"Authorization": f"Bearer {tok}"}
    # ① 기록기처럼 올리기 — 세션 시작 · 50건씩 · 끝 (체인)
    sid = g.sid
    s.post("/api/works/W-bench/sessions", json={"id": sid, "started_at": g.ev[0]["ts"], "device": {"name": "BENCH", "os": "mac"}}, headers=A)
    prev, evs = C.GENESIS, []
    for e in g.ev:
        e = {k: v for k, v in e.items() if k not in ("session_id", "source")}
        if C.in_chain(e):
            prev = C.next_hash(prev, e)
            e["h"] = prev
        evs.append(e)
    n = sum(1 for e in evs if C.in_chain(e))
    t0, q0 = time.perf_counter(), 0
    for i in range(0, len(evs), 50):
        묻기["n"] = 0
        chunk = evs[i:i + 50]
        head = next((e["h"] for e in reversed(evs[:i + 50]) if "h" in e), C.GENESIS)
        r = s.post(f"/api/sessions/{sid}/events", json={"events": chunk, "chain_head": head,
                                                         "chain_len": sum(1 for e in evs[:i + 50] if C.in_chain(e))}, headers=A)
        q0 += 묻기["n"]
        if r.status_code >= 400:
            print("올리기 실패", r.status_code, r.get_data(as_text=True)[:200])
            break
    시간.append((f"기록 올리기 (50건씩 {len(evs) // 50 + 1}번)", time.perf_counter() - t0, q0, None))
    재기("세션 끝 (봉인)", lambda: s.post(f"/api/sessions/{sid}/end", json={"ended_at": evs[-1]["ts"], "root": prev}, headers=A))
    # ② PC 앱: 출처 보기 → [링크 · PDF 만들기] — PC 앱의 서버 부르기를 이 서버로 돌린다
    G, S = B.앱_불러오기(d)
    G["설정"]["server"] = "http://bench/api"

    class 응답:
        def __init__(self, r):
            self.status_code, self._r = r.status_code, r

        def json(self):
            return self._r.get_json()

    보낸 = []

    class 길:                                                  # statement._서버 가 쓰는 requests 자리
        RequestException = Exception

        @staticmethod
        def request(method, url, headers=None, timeout=None, **kw):
            if kw.get("data") is not None and (headers or {}).get("Content-Encoding") == "gzip":
                import gzip
                보낸.append((method, url.rsplit("/api", 1)[-1] + " (gzip)", len(kw["data"])))
                kw["json"] = json.loads(gzip.decompress(kw["data"]))
                print(f"    gzip {len(kw['data']) / 1024:.0f}KB · 풀면 {len(gzip.decompress(kw['data'])) / 1024:.0f}KB")
                if a.mem:
                    import tracemalloc
                    tracemalloc.start()
                r = s.open(url.replace("http://bench", ""), method=method, headers=headers, data=kw["data"])
                if a.mem:
                    print(f"    서버가 받는 동안 메모리 최고 {tracemalloc.get_traced_memory()[1] / 1e6:.0f}MB")
                    tracemalloc.stop()
                return 응답(r)
            if kw.get("json") is not None:                    # PC 가 서버로 보내는 크기 (requests 는 ensure_ascii 로 보낸다)
                j = kw["json"]
                보낸.append((method, url.rsplit("/api", 1)[-1], len(json.dumps(j).encode())))
                if isinstance(j, dict) and len(보낸[-1]) and 보낸[-1][2] > 100_000:   # 큰 몸통은 어디가 큰지
                    for k, v in sorted(j.items(), key=lambda x: -len(json.dumps(x[1]))):
                        if len(json.dumps(v)) > 10_000:
                            print(f"    {k}: {len(json.dumps(v).encode()) / 1024:.0f}KB (UTF-8 {len(json.dumps(v, ensure_ascii=False).encode()) / 1024:.0f}KB)"
                                  + ("" if not isinstance(v, dict) else " · " + " · ".join(f"{kk} {len(json.dumps(vv).encode()) / 1024:.0f}KB" for kk, vv in v.items())))
            return 응답(s.open(url.replace("http://bench", ""), method=method, headers=headers, **kw))

        get = staticmethod(lambda url, **kw: 길.request("GET", url, **kw))
    G["_서버"].__globals__["requests"] = 길                 # runpy 가 준 G 는 복사본 — 함수가 보는 진짜 전역에 넣는다
    G["_서버"].__globals__["_연결"] = 길                    # 10/15 (#83) 연결을 다시 쓰는 requests.Session — 그 자리도
    import source as _S
    from core import safefile
    safefile.write_json(os.path.join(d, "auth.json"), {"server": "http://bench/api", "token": tok, "user": {"name": "벤치"}})
    c = G["app"].test_client()
    H = {"Host": "127.0.0.1:5079", "X-Trace-Local": "1"}
    raw = open(os.path.join(d, "논문.docx"), "rb").read()
    재기("PC: 출처 보기 (파일 열기)", lambda: c.post("/local/source", headers=H, data={"work_id": "W-bench", "file": (io.BytesIO(raw), "논문.docx")},
                                                content_type="multipart/form-data"))
    r = 재기("PC → 서버: 링크 · PDF 만들기", lambda: c.post("/local/export/make", headers=H, data={"work_id": "W-bench"}))
    made = r.get_json() or {}
    if r.status_code >= 400:
        print("만들기 실패", r.status_code, json.dumps(made, ensure_ascii=False)[:300])
    token = (made.get("url") or "").rsplit("/", 1)[-1]
    # ③ 교수 · 학생이 여는 것
    재기("서버: 교수 화면 자료 (/api/share)", lambda: s.get(f"/api/share/{token}"))
    재기("서버: 내역서 PDF", lambda: s.get(f"/api/share/{token}/pdf"))
    재기("서버: 과제 요약 숫자 (/summary)", lambda: s.get("/api/works/W-bench/summary", headers=A))
    재기("서버: 최근 내역서 (/statements/latest)", lambda: s.get("/api/works/W-bench/statements/latest", headers=A))
    print(f"\n{a.pages}쪽 · 이벤트 {len(evs):,} (체인 {n:,}) · AI 답 {len(답들)}")
    for 이름, t, q, r in 시간:
        크기 = f" · 응답 {len(r.get_data()) / 1024:.0f}KB" if r is not None else ""
        상태 = f" · HTTP {r.status_code}" if r is not None else ""
        print(f"  {t:7.2f}초 · DB {q:5d}번  {이름}{상태}{크기}")
    for m, u, n in 보낸:
        print(f"  PC → 서버 {m} {u} 보낸 크기 {n / 1024:.0f}KB")
    shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
