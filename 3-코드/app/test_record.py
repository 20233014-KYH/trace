"""
test_record.py — 기록 다시 보기(app/record.py)를 녹화 시험 자료로. 서버 없이 돈다.

  python app/test_record.py                  # 검사
  python app/test_record.py --serve [포트]    # 같은 자료로 화면 띄우기 (기본 5092) → /record?work=W-match_web&session=S-match_web

확인하는 것:
  · 숫자 = 과제 상세와 같음 (질문 · 붙여넣기) · 줄은 시각 순 · 질문 · 답은 빠짐없이
  · 답 표시 = 출처 보기와 같음 (결과물에 이어진 답은 "참고만" 이 아님 · 이어지지 않은 답은 "참고만")
  · 붙여넣기 출처: AI 답 · 다른 곳 개수가 core/match 와 같음
  · 잠깐 멈춤 = 시각만 (줄 · 막대 · 멈춘 시간)
  · 문서 위치(PC 경로) · 점수 · 퍼센트가 응답에 없음 · 잘못된 id 거절
"""
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_source as T                          # noqa: E402  학생 PC 만들기 · 같은 자료
from core import safefile                       # noqa: E402
ST = T.ST
검사 = T.검사


def 멈춤_넣기(data, sid, a, b):
    p = os.path.join(data, "events-2026-10-05.jsonl")
    with open(p, "a", encoding="utf-8") as f:
        for t, ts in (("pause_start", a), ("pause_end", b)):
            f.write(json.dumps({"id": f"evt_p{t}", "session_id": sid, "ts": ts, "type": t}, ensure_ascii=False) + "\n")


def main():
    print("\n  기록 다시 보기 검사 — 녹화 시험 자료\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-rec-")
    옛 = dict(ST.출처._기록)
    try:
        T.학생_PC(data)
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        from core import match as M
        G = lambda w, s: c.get(f"/local/record/detail?work_id={w}&session_id={s}", headers=H, **HOST)

        검사("화면 열림 · 과제 상세 기록 줄이 이 화면으로 이어짐", c.get("/record?work=W-match_web&session=S-match_web", **HOST).status_code == 200
             and "/record?work=" in open(os.path.join(HERE, "detail.html"), encoding="utf-8").read())
        검사("잘못된 id 거절 · 없는 기록 404", G("../x", "S-match_web").status_code == 400 and G("W-match_web", "S-없음").status_code == 404
             and G("W-match_web", "S-match_view").status_code == 404)

        for case in T.CASES:
            print(f"\n  ━━ {case}")
            wid, sid = f"W-{case}", f"S-{case}"
            r = G(wid, sid)
            if r.status_code != 200:
                검사("응답", False, str(r.json)); continue
            d = r.json
            msgs, events, context, _ = ST.출처.과제_기록(wid)
            evs = [e for e in events if e["session_id"] == sid]
            mine = [m for m in M.latest_messages(msgs) if m["session_id"] == sid]
            its = d["items"]
            가운데 = [x["ts"] for x in its if x["kind"] not in ("start", "end")]
            검사("줄은 시각 순 · 첫 줄 기록 시작", 가운데 == sorted(가운데) and its[0]["kind"] == "start"
                 and all(x["kind"] != "end" for x in its[:-1]))
            검사("숫자 = 과제 상세 (질문 · 붙여넣기)",
                 d["stats"]["questions"] == sum(1 for m in mine if m["role"] == "question") and d["stats"]["pastes"] == sum(1 for e in evs if e["type"] == "paste"),
                 f"질문 {d['stats']['questions']} · 붙여넣기 {d['stats']['pastes']}")
            검사("질문 · 답 줄 빠짐없이", sum(1 for x in its if x["kind"] in ("q", "a")) == len(mine) == len(d["lanes"]["ai"]))
            if d["linked"]:
                src = c.post("/local/source", data={"work_id": wid}, headers=H, **HOST).json
                쓰인답 = {q["refs"]["a"]["event_id"] for q in src["questions"] if q["uses"] and "a" in q.get("refs", {})}
                답줄 = {m["event_id"]: x for m, x in zip(sorted(mine, key=lambda m: m["ts"]), [x for x in its if x["kind"] in ("q", "a")])
                       if m["role"] == "answer"}
                맞음 = all((x["tag"] or {}).get("t") != "참고만" if eid in 쓰인답 else (x["tag"] or {}).get("c") in ("ref", "plain", None)
                         for eid, x in 답줄.items())
                검사("답 표시 = 출처 보기 (이어진 답 · 참고만)", 맞음, f"이어진 답 {len(쓰인답)}")
            붙 = [x for x in its if x["kind"] == "paste"]
            ai, 다른 = len(M.pasted_from_ai(evs, [c_ for c_ in context if c_["session_id"] == sid])), len(M.pasted_from_other(evs, [c_ for c_ in context if c_["session_id"] == sid]))
            검사("붙여넣기 출처 = core/match (AI 답 · 다른 곳)",
                 sum(1 for x in 붙 if (x["tag"] or {}).get("t") == "AI 답") == ai and sum(1 for x in 붙 if (x["tag"] or {}).get("t") == "다른 곳") == 다른,
                 f"AI 답 {ai} · 다른 곳 {다른} · 모두 {len(붙)}")
            txt = json.dumps(d, ensure_ascii=False)
            검사("PC 경로 · 점수 · 퍼센트 없음", data.replace("\\", "\\\\") not in txt and not re.search(r"ratio|score|cover|\d+\s?%", txt))

        print("\n  ━━ 잠깐 멈춤 · Word 글")
        evs = [e for e in ST.출처.과제_기록("W-match_view")[1]]
        a, b = evs[len(evs) // 2]["ts"], evs[len(evs) // 2 + 1]["ts"]
        멈춤_넣기(data, "S-match_view", a, b)
        d = G("W-match_view", "S-match_view").json
        p = [x for x in d["items"] if x["kind"] == "pause"]
        검사("멈춤 = 줄 하나 · 막대 · 시각만", len(p) == 1 and p[0]["tag"]["t"] == "시각만" and d["lanes"]["pause"] == [[a, b]]
             and d["stats"]["pause_sec"] == d["session"]["pause_sec"])
        검사("Word 글 = 문서 변화 줄 (match_view 는 doc_change 기록 있음) · 친 글자 수",
             any(x["kind"] == "word" for x in d["items"]) and d["stats"]["typed"] > 0, f"친 글자 {d['stats']['typed']}")
        d = G("W-match_proc", "S-match_proc").json
        검사("탐색기 등 과제 프로그램 아닌 키 입력은 빼고 셈",
             d["stats"]["typed"] == sum(e.get("count", 0) for e in T.L("match_proc", "events") if e["type"] == "keys" and e.get("category") == "work"))

        print("\n  ━━ 결과물이 PDF (10/15 · Word 로 쓰고 PDF 로 내보낸 것)")
        import io as _io
        from core.pdftext import read_doc
        def 올려(name, raw):
            return c.post("/local/source", data={"work_id": "W-match_view", "file": (_io.BytesIO(raw), name)}, headers=H,
                          content_type="multipart/form-data", **HOST).json
        워드 = 올려("report.docx", open(os.path.join(T.FX, "match_view", "report.docx"), "rb").read())
        피디 = 올려("report.pdf", open(os.path.join(T.FX, "match_view", "report.pdf"), "rb").read())
        검사("PDF 를 넣어도 문장 · 출처 표시가 Word 와 같음", [(x["text"], x["kind"]) for x in 워드["sentences"]] == [(x["text"], x["kind"]) for x in 피디["sentences"]]
             and 워드["counts"] == 피디["counts"], f"문장 {len(피디['sentences'])} · {피디['counts']}")
        검사("이름만 다르고 같은 원본(report.pdf ↔ 기록의 Word)이면 '기록에 없는 문서' 경고 안 함 (이름 줄기)", 피디["in_records"] is not None)
        r = c.post("/local/source", data={"work_id": "W-match_view", "file": (_io.BytesIO(b"%PDF-1.4\n%%EOF"), "빈.pdf")}, headers=H,
                   content_type="multipart/form-data", **HOST)
        검사("글자 없는 · 깨진 PDF 는 알려 줌", r.status_code == 400 and r.json["error"] == "bad_file", r.json.get("message", ""))
        검사("PDF 줄바꿈: 한글 글자 중간에서 넘어간 줄은 붙이고 표의 칸은 따로", all("  " not in t for _, t in read_doc(open(os.path.join(T.FX, "match_view", "report.pdf"), "rb").read())))

        print("\n  ━━ AI 가 파일로만 준 결과물 (기록하는 동안 받은 파일 · 10/15)")
        보고서 = open(os.path.join(T.FX, "match_web", "report.docx"), "rb").read()
        글 = "\n".join(t for _, t in read_doc(보고서))
        with open(os.path.join(data, "events-2026-10-05.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": "evt_dl0", "session_id": "S-dl", "ts": "2026-10-05T20:00:00+09:00", "type": "session_start", "work_id": "W-dl"}) + "\n")
            f.write(json.dumps({"id": "evt_dl9", "session_id": "S-dl", "ts": "2026-10-05T20:30:00+09:00", "type": "session_end"}) + "\n")
        with open(os.path.join(data, "context-2026-10-05.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"session_id": "S-dl", "id": "dl1", "ts": "2026-10-05T20:12:00+09:00", "source": "download", "kind": "download", "text": 글,
                                "meta": {"name": "도시열섬_보고서.pdf", "size": len(보고서), "hash": "sha256:x", "app": "claude.exe", "domain": "", "category": "ai"}},
                               ensure_ascii=False) + "\n")
        r = c.post("/local/source", data={"work_id": "W-dl", "file": (_io.BytesIO(보고서), "report.docx")}, headers=H,
                   content_type="multipart/form-data", **HOST).json
        받은 = [x for x in r["sentences"] if x["kind"] == "noproc" and (x.get("proc") or {}).get("how") == "download"]
        검사("대화엔 없고 파일로만 받은 결과물 → '받은 파일' (빨강) · 받은 곳 · 파일 이름", len(받은) >= len(r["sentences"]) * 0.8
             and 받은[0]["proc"]["app"] == "claude.exe" and 받은[0]["proc"]["file"] == "도시열섬_보고서.pdf" and 받은[0]["proc"]["ai"] is True,
             f"{len(받은)}/{len(r['sentences'])} 문장")
        검사("지문이 다르면(받은 뒤 고친 파일) '받은 파일 그대로' 라고 하지 않음", r["same_download"] is None)
        import hashlib as _h
        with open(os.path.join(data, "context-2026-10-05.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"session_id": "S-dl", "id": "dl2", "ts": "2026-10-05T20:14:00+09:00", "source": "download", "kind": "download", "text": 글,
                                "meta": {"name": "도시열섬_보고서 (1).docx", "size": len(보고서), "hash": "sha256:" + _h.sha256(보고서).hexdigest(),
                                         "app": "chrome.exe", "domain": "claude.ai", "category": "ai"}}, ensure_ascii=False) + "\n")
        r = c.post("/local/source", data={"work_id": "W-dl", "file": (_io.BytesIO(보고서), "제출본.docx")}, headers=H,
                   content_type="multipart/form-data", **HOST).json
        검사("받은 파일과 바이트까지 같으면 '받은 파일 그대로' (이름이 달라도) · 기록에 없는 문서 경고 안 함",
             (r["same_download"] or {}).get("name") == "도시열섬_보고서 (1).docx" and r["same_download"]["domain"] == "claude.ai" and r["in_records"] is True,
             str(r["same_download"]))
        with open(os.path.join(data, "context-2026-10-05.jsonl"), "a", encoding="utf-8") as f:     # 같은 파일을 먼저 한 번 더 받음 — 받은 곳 모름
            f.write(json.dumps({"session_id": "S-dl", "id": "dl0", "ts": "2026-10-05T20:05:00+09:00", "source": "download", "kind": "download", "text": 글,
                                "meta": {"name": "도시열섬_보고서.docx", "size": len(보고서), "hash": "sha256:" + _h.sha256(보고서).hexdigest(),
                                         "app": "chrome.exe", "domain": "", "category": "other"}}, ensure_ascii=False) + "\n")
        r = c.post("/local/source", data={"work_id": "W-dl", "file": (_io.BytesIO(보고서), "제출본.docx")}, headers=H,
                   content_type="multipart/form-data", **HOST).json
        곳 = {(x["proc"].get("file"), x["proc"].get("ai")) for x in r["sentences"] if (x.get("proc") or {}).get("how") == "download"}
        검사("같은 파일을 여러 번 받았으면 받은 곳이 확실한 것으로 (안내 claude.ai · 문장은 받은 곳 모르는 먼저 받은 것에 안 이어짐)",
             r["same_download"]["domain"] == "claude.ai" and ("도시열섬_보고서.docx", False) not in 곳 and all(ai for _, ai in 곳),
             f"{r['same_download']['domain']} · {곳}")
        from core import match as _M
        본문 = "1. 서론\n대학 도서관은 학생들이 가장 많이 찾는 공간이다.\n유형\t대표 사례\n대화 소음\t전화 통화와 잡담이 이어진다."
        줄 = [r2["label"] for row in _M.link_document(["1. 서론", "대학 도서관은 학생들이 가장 많이 찾는 공간이다.", "유형", "대표 사례",
                                                       "대화 소음 전화 통화와 잡담이 이어진다."], [],
                                                      proc={"typed": [], "noproc": [{"text": 본문, "how": "download", "ts": "", "file": "x.pdf"}]})
              for r2 in row]
        검사("받은 파일 사이의 제목 · 번호 · 표 머리글 조각('1.' '서론' '유형')도 받은 파일로 (그 파일 안에 한 줄 · 한 문장으로 있을 때만)",
             줄 == ["noproc"] * 6, str(줄))
        줄 = [r2["label"] for row in _M.link_document(["어린 시절", "대학 도서관은 학생들이 가장 많이 찾는 공간이다."], [],
                                                      proc={"typed": [], "noproc": [{"text": 본문, "how": "download", "ts": "", "file": "x.pdf"}]})
              for r2 in row]
        검사("받은 파일에 없는 짧은 제목은 그대로 '출처 기록 없음'", 줄 == ["none", "noproc"], str(줄))
        d = G("W-dl", "S-dl").json
        검사("기록 다시 보기에 '파일 받기' 줄 · 붙여넣기 수엔 안 셈", any(x["title"] == "파일 받기" and x["tag"]["t"] == "AI 에서 받음" for x in d["items"])
             and d["stats"]["pastes"] == 0)

        print("\n  ━━ 기록된 위치가 없는 문서 — 내용으로 찾기 (10/14)")
        r = c.post("/local/source", data={"work_id": f"W-{T.NO_PATH}"}, headers=H, **HOST)
        검사("Word 글 기록이 없는 옛 기록은 찾지 않고 고르라고 함 (실제 PC 도 안 뒤짐)", r.status_code == 400 and r.json["error"] == "no_file")
        # match_view: 문서 위치(doc_path)를 지움 = 저장 전 "문서1" 로만 기록되고 기록을 끈 뒤 다른 이름으로 저장한 것
        p = os.path.join(data, "context-2026-10-05.jsonl")
        줄 = [l for l in open(p, encoding="utf-8") if not ('"doc_path"' in l and "S-match_view" in l)]
        open(p, "w", encoding="utf-8").writelines(줄)
        ST.출처._파일.pop("W-match_view", None); ST.출처._연_이름.pop("W-match_view", None); ST.출처._찾음_실패.clear()
        r = c.post("/local/source", data={"work_id": "W-match_view"}, headers=H, **HOST)
        검사("같은 내용 파일이 없으면 고르라고 함", r.status_code == 400)
        바탕 = os.path.join(data, "홈", "Desktop", "수업", "다른이름으로저장.docx")
        os.makedirs(os.path.dirname(바탕), exist_ok=True)
        shutil.copy(os.path.join(T.FX, "match_view", "report.docx"), 바탕)
        shutil.copy(os.path.join(T.FX, "match_web", "report.docx"), os.path.join(data, "홈", "Desktop", "상관없는파일.docx"))
        ST.출처._찾음_실패.clear()
        r = c.post("/local/source", data={"work_id": "W-match_view"}, headers=H, **HOST)
        검사("기록할 때 쓴 글과 내용이 같은 파일을 찾아 엶 (상관없는 파일은 안 고름) · 경고 대신 '내용으로 찾음'",
             r.status_code == 200 and r.json["file"] == "다른이름으로저장.docx" and r.json["found_by_content"] and r.json["in_records"],
             str({k: r.json.get(k) for k in ("file", "found_by_content", "error")}))
        검사("찾은 자리는 data/docs-found.json 에 (다음엔 바로)",
             safefile.read_json(os.path.join(data, "docs-found.json"), {}).get("W-match_view") == 바탕)
        print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    finally:
        ST.출처._기록.clear(); ST.출처._기록.update(옛)
        shutil.rmtree(data, ignore_errors=True)
    return T.실패 == 0


def serve(port):
    data = tempfile.mkdtemp(prefix="trace-rec-")
    T.학생_PC(data)
    ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
    ST.PORT = port                                   # 로컬만() 이 Host 를 이 포트로 확인
    print(f"  http://127.0.0.1:{port}/record?work=W-match_web&session=S-match_web")
    try:
        ST.app.run(host="127.0.0.1", port=port, debug=False)
    finally:
        shutil.rmtree(data, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if "--serve" in sys.argv:
        i = sys.argv.index("--serve")
        serve(int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 5092)
    else:
        sys.exit(0 if main() else 1)
