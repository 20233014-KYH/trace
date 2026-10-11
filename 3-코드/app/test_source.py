"""
test_source.py — 출처 보기 화면(app/source.py)을 실제 녹화 시험 자료로. 서버 없이 돈다.

  python app/test_source.py              # 검사
  python app/test_source.py --serve      # 같은 자료로 화면을 띄워 눈으로 확인 (http://127.0.0.1:5079/source)

tests/fixtures 의 녹화 시험(실제 AI 답 · 실제 Word · 실제 기록기 이벤트)으로 학생 PC 의 data 폴더를 임시로 만든다 —
과제 하나에 시험 하나. 그다음 화면이 부르는 주소를 그대로 부르고 확인한다:
  · 문장마다 표시가 내역서 화면(/local/analyze)과 같다 (두 화면이 다른 말을 하면 안 됨)
  · 문장 표시가 정답 파일(report_truth.json)과 맞는 개수가 연결시제품.py 와 같다
  · AI 답 기준: 답이 있는 질문은 모두 나오고, 결과물에 글이 들어간 답은 원문에 칠한 곳이 있다
  · 점수·퍼센트가 응답 어디에도 없다
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from core.texthash import sha256_text           # noqa: E402
import statement as ST                          # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures")
CASES = ["match_rec", "match_mix", "match_app", "match_web", "match_proc", "match_view"]
통과, 실패 = 0, 0


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✅' if 조건 else '❌'} {이름:<34} {설명}")


def L(case, name):
    p = os.path.join(FX, case, name + ".jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


NO_PATH = "match_rec"      # 10/11 전 기록처럼 문서 위치(doc_path)가 없는 과제 — 학생이 골라야 함


def 학생_PC(data):
    """시험마다 과제 하나 · 세션 하나. 기록기가 남겼을 파일 세 가지(events · context · ai-messages)를 만든다.
    문서 위치(doc_path): 기록에 남은 이름으로 data/문서/ 에 report.docx 를 복사해 두고 그 자리를 적는다 (NO_PATH 빼고)"""
    ev_all, ctx_all, msg_all = [], [], []
    os.makedirs(os.path.join(data, "문서"), exist_ok=True)
    for n, case in enumerate(CASES):
        sid, wid = f"S-{case}", f"W-{case}"
        evs = L(case, "events")
        t0 = min((e["ts"] for e in evs), default="2026-10-05T15:00:00+09:00")
        h, m = int(t0[11:13]), int(t0[14:16])
        start = f"{t0[:11]}{max(0, h - 1):02d}:{m:02d}:00{t0[19:]}"
        ev_all.append({"id": "evt_000000", "session_id": sid, "ts": start, "type": "session_start", "work_id": wid})
        for k, a in enumerate(L(case, "ai_answers")):          # 질문 · 답 = 기록 시작 뒤 2분 간격 (붙여넣기보다 앞)
            for role, text, s in (("question", a.get("question") or "", 0), ("answer", a["text"], 20)):
                if not text:
                    continue
                ts = f"{start[:14]}{k * 2:02d}:{s:02d}{start[19:]}"
                msg_all.append({"session_id": sid, "event_id": f"evt_9{k:02d}{role[0]}", "ts": ts, "tool": a.get("tool", ""),
                                "model": a.get("model", ""), "turn": k * 2 + 1, "role": role, "hash": sha256_text(text), "text": text})
        ev_all += [{**e, "session_id": sid} for e in evs]
        ctx_all += [{**c, "session_id": sid} for c in L(case, "context")]
        이름 = next((e["file"] for e in evs if e.get("app") == "Word" and e.get("file")), None)
        if 이름 and case != NO_PATH:
            경로 = os.path.join(data, "문서", case, 이름)
            os.makedirs(os.path.dirname(경로), exist_ok=True)
            shutil.copy(os.path.join(FX, case, "report.docx"), 경로)
            ctx_all.append({"session_id": sid, "id": f"p-{case}", "ts": t0, "source": "office", "kind": "doc_path", "text": "",
                            "meta": {"app": "Word", "file": 이름, "path": 경로}})
    for name, rows in (("events", ev_all), ("context", ctx_all), ("ai-messages", msg_all)):
        with open(os.path.join(data, f"{name}-2026-10-05.jsonl"), "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def main():
    print("\n  출처 보기 화면 검사 — 녹화 시험 자료 · 서버 없음\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-src-")
    try:
        학생_PC(data)
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)       # 서버는 안 부른다
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}

        # 저장 전 이름("문서1") → 저장하며 이름 바뀜 = 같은 문서 · 끝까지 저장 안 한 "문서2" 는 남김 (10/11 실제 Word 시험에서 나옴)
        with open(os.path.join(data, "events-2026-10-11.jsonl"), "w", encoding="utf-8") as f:
            for i, (t, ty, fn) in enumerate([("21:03:00", "session_start", None), ("21:03:07", "doc_change", "문서1"),
                                             ("21:03:12", "doc_save", "보고서.docx"), ("21:04:00", "doc_change", "보고서.docx"),
                                             ("21:05:00", "doc_change", "문서2")]):
                e = {"id": f"evt_{i:06d}", "session_id": "S-rename", "ts": f"2026-10-11T{t}+09:00", "type": ty}
                e.update({"work_id": "W-rename"} if fn is None else {"app": "Word", "file": fn})
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        검사("저장 전 이름은 저장된 문서로 합침", [d["name"] for d in ST.출처._문서_목록("W-rename")] == ["문서2", "보고서.docx"],
             " · ".join(d["name"] for d in ST.출처._문서_목록("W-rename")))

        r = c.get("/source", **HOST)
        검사("화면 열림", r.status_code == 200 and "출처 보기" in r.get_data(as_text=True))
        r = c.post("/local/source", data={"work_id": f"W-{NO_PATH}"}, headers=H, **HOST)
        검사("위치 없으면 고르라고 함 · 문서 이름 힌트", r.status_code == 400 and r.json["error"] == "no_file",
             " · ".join(r.json.get("files", [])))
        r = c.post("/local/source", data={"work_id": "W-match_mix"}, headers=H, **HOST)
        검사("위치 있으면 고르지 않아도 바로 열림", r.status_code == 200 and r.json["in_records"] and r.json["file"] == "네트워크과제_보고서.docx",
             r.json.get("file", ""))
        검사("화면엔 경로 안 보냄", "path" not in json.dumps(r.json.get("recorded_docs")) and data not in r.get_data(as_text=True))
        r = c.post("/local/source/open", data={"work_id": "W-match_mix", "name": "네트워크과제_보고서.docx"}, headers=H, **HOST)
        검사("목록에서 이름 눌러 열기", r.status_code == 200 and r.json["recorded_docs"][0]["exists"])
        옛 = os.path.join(data, "문서", "match_mix", "네트워크과제_보고서.docx")
        os.replace(옛, 옛 + ".옮김")
        r = c.post("/local/source/open", data={"work_id": "W-match_mix", "name": "네트워크과제_보고서.docx"}, headers=H, **HOST)
        r2 = c.post("/local/source", data={"work_id": "W-match_mix"}, headers=H, **HOST)
        검사("옮긴 파일 → 410 · 예전 내용 대신 고르라고 함", r.status_code == 410 and r2.status_code == 400 and r2.json["error"] == "no_file")
        os.replace(옛 + ".옮김", 옛)
        c.post("/local/source", data={"work_id": "W-match_mix"}, headers=H, **HOST)
        shutil.copy(os.path.join(FX, "match_rec", "report.docx"), 옛)      # Word 에서 고쳐 저장한 것처럼 내용이 바뀜
        r = c.post("/local/source", data={"work_id": "W-match_mix"}, headers=H, **HOST)
        새것 = ST.출처.read_docx(옛)
        검사("다시 열면 저장한 최신 내용", r.status_code == 200 and r.json["sentences"][0]["text"] in " ".join(t for _, t in 새것))
        shutil.copy(os.path.join(FX, "match_mix", "report.docx"), 옛)
        r = c.post("/local/source", data={"work_id": "W-match_mix"}, **HOST)
        검사("X-Trace-Local 없으면 거절", r.status_code == 403)
        r = c.get("/local/source/works", **HOST)
        검사("이 PC 과제 목록 (로그인 없이)", r.status_code == 200 and len(r.json["works"]) == len(CASES) + 1)

        for case in CASES:
            print(f"\n  ━━ {case}")
            raw = open(os.path.join(FX, case, "report.docx"), "rb").read()
            wid = f"W-{case}"
            r = c.post("/local/source", data={"work_id": wid, "file": (io.BytesIO(raw), "report.docx")}, headers=H,
                       content_type="multipart/form-data", **HOST)
            if r.status_code != 200:
                검사("출처 보기 응답", False, str(r.json)); continue
            d = r.json
            a = c.post("/local/analyze", data={"work_id": wid, "file": (io.BytesIO(raw), "report.docx")}, headers=H,
                       content_type="multipart/form-data", **HOST).json
            내역서 = [(s["text"], s.get("kind") or s["label"]) for p in a["paragraphs"] for s in p]
            출처 = [(x["text"], x["kind"]) for x in d["sentences"]]
            검사("문장마다 표시가 내역서 화면과 같음", 내역서 == 출처, f"문장 {len(출처)}")

            truth = json.load(open(os.path.join(FX, case, "report_truth.json"), encoding="utf-8"))
            flat = [t for p in truth["paragraphs"] for t in p]
            맞음 = sum(1 for t, x in zip(flat, d["sentences"])         # 표시만 본다 (AI 답·위치까지는 연결시제품.py 가 봄)
                     if ("exact" if x["kind"] == "similar" else x["kind"]) in t.get("label_any", [t["label"]]))
            need = truth.get("expect_at_least", len(flat))
            검사("표시가 정답과 맞음", 맞음 >= need, f"{맞음}/{len(flat)} (기준 {need})")

            기록된 = d["recorded_files"]
            if 기록된:
                같은이름 = c.post("/local/source", data={"work_id": wid, "file": (io.BytesIO(raw), 기록된[0])}, headers=H,
                              content_type="multipart/form-data", **HOST).json
                검사("기록에 없는 이름이면 알림 · 있으면 안 알림", d["in_records"] is False and 같은이름["in_records"] is True,
                     f"기록된 문서 {' · '.join(기록된)}")
            c_ = d["counts"]
            검사("색 묶음 합 = 문장 수", sum(c_[g] for g in ("copy", "edited", "viewed", "none")) == len(d["sentences"]),
                 f"그대로 {c_['copy']} · 고침 {c_['edited']} · 보고 씀 {c_['viewed']} · 기록 없음 {c_['none']}")
            답수 = len(L(case, "ai_answers"))
            검사("질문 = 기록된 답 수", c_["questions"] == 답수 and c_["used"] + c_["ref"] == 답수,
                 f"질문 {c_['questions']} · 글 들어감 {c_['used']} · 참고만 {c_['ref']}")
            칠함 = all(any(p["g"] for p in q["answer"]) for q in d["questions"] if q["uses"])
            검사("글 들어간 답은 원문에 칠한 곳 있음", 칠함)
            원문들 = {m["text"].replace("**", "") for m in L(case, "ai_answers")}
            원문같음 = all("".join(p["t"] for p in q["answer"]) in 원문들 for q in d["questions"] if q["answer"])
            검사("원문 글자 그대로 (** 만 뺌)", 원문같음)
            # 문장을 고르면 그 문장에 이어진 답 부분으로 굴려야 함 → 답 원문에 그 문장 번호(i)가 칠한 채로 있어야
            찾음 = all(any(p.get("i") in x["sents"] and p["g"] for p in d["questions"][x["q"]]["answer"])
                     for x in d["sentences"] if "q" in x and x["sents"])
            검사("고른 문장의 답 부분이 원문에 있음", 찾음)
            이어짐 = all(d["questions"][x["q"]]["uses"].count(x["k"]) == 1 for x in d["sentences"] if "q" in x)
            검사("문장 ↔ 질문 서로 이어짐", 이어짐)
            txt = json.dumps(d, ensure_ascii=False)
            검사("점수·퍼센트 없음", not re.search(r"ratio|cover|score|\d+\s?%", txt))
        print(f"\n  {'─' * 70}\n  통과 {통과} · 실패 {실패}\n")
    finally:
        shutil.rmtree(data, ignore_errors=True)
    return 실패 == 0


def serve():
    """같은 시험 자료로 화면 띄우기 — 눈으로 확인용. 끄면 임시 폴더는 지운다."""
    data = tempfile.mkdtemp(prefix="trace-src-")
    학생_PC(data)
    ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
    # 문서 위치가 적힌 과제는 저절로 열림 · NO_PATH(match_rec) 는 옛 기록처럼 직접 골라야 함
    print(f"  시험 자료로 띄움 · 기록 {data}\n  http://127.0.0.1:{ST.PORT}/source?work=W-match_mix  (파일: tests/fixtures/match_mix/report.docx)")
    try:
        ST.app.run(host="127.0.0.1", port=ST.PORT, debug=False)
    finally:
        shutil.rmtree(data, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if "--serve" in sys.argv:
        serve()
    else:
        sys.exit(0 if main() else 1)
