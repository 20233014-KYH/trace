"""
test_export.py — 내역서 내보내기 화면(app/export.py)을 녹화 시험 자료로. 인터넷 서버 없이 돈다.

  python app/test_export.py
  python app/test_source.py --serve       # 같은 자료로 화면 → http://127.0.0.1:5079/export?work=W-match_mix

학생 PC 는 test_source.py 의 학생_PC() 로 똑같이 만들고, 인터넷 서버는 가짜로 바꿔 **보낸 몸통을 잡아서** 본다:
  · 붙여넣기로 확실한 연결 + "연결함" 만 원문이 간다 · "연결 안 함" 은 해시·위치만 · "잘 모르겠음" 은 안 감
  · 가린 질문은 원문 대신 위치만 · 답을 가리면 그 연결이 빠짐 · 전화번호·이메일 모양을 규칙으로 찾음
  · 바뀐 게 없으면 내역서를 또 만들지 않음 · 링크 끊기
  · 미리 보기 PDF 는 로그인 없이도 그려짐 · 점수·퍼센트 · PC 경로 없음
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
from core.texthash import sha256_text            # noqa: E402
ST = T.ST
S = ST.출처
검사 = T.검사
EX = sys.modules["export"]
CF = sys.modules["confirm"]


def 질문에_넣기(data, wid, 덧붙일):
    """그 과제의 첫 질문 원문 끝에 글을 붙인다 (해시도 다시) — 전화번호가 든 질문을 흉내"""
    p = os.path.join(data, "ai-messages-2026-10-05.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8")]
    for r in rows:
        if r["session_id"] == "S-" + wid[2:] and r["role"] == "question":
            r["text"] += 덧붙일
            r["hash"] = sha256_text(r["text"])
            break
    with open(p, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def main():
    print("\n  내역서 내보내기 화면 검사 — 녹화 시험 자료 · 가짜 서버\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-ex-")
    옛 = dict(S._기록)
    try:
        T.학생_PC(data)
        질문에_넣기(data, "W-match_mix", " 궁금하면 010-1234-5678 이나 me@example.com 으로")
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}
        W = "W-match_mix"
        E = lambda: c.post("/local/export", data={"work_id": W}, headers=H, **HOST)
        D = lambda body: c.post("/local/export/draft", json={"work_id": W, **body}, headers=H, **HOST)

        검사("화면 열림", c.get("/export", **HOST).status_code == 200)
        r = c.post("/local/export", data={"work_id": f"W-{T.NO_PATH}"}, headers=H, **HOST)
        검사("문서를 못 열면 출처 보기로 보냄", r.status_code == 400 and r.json["error"] == "no_file")
        검사("X-Trace-Local 없으면 거절", c.post("/local/export", data={"work_id": W}, **HOST).status_code == 403)

        d = E().json
        검사("처음: 붙여넣기로 확실한 것만 연결 · 나머지는 잘 모르겠음",
             d["counts"]["confirmed"] == d["counts"]["auto"] == 3 and d["counts"]["unsure"] == 3 and d["counts"]["rejected"] == 0,
             json.dumps(d["counts"], ensure_ascii=False))
        검사("전화번호 · 이메일 찾음 → 기본은 그 부분만 가림 (질문은 그대로 · 10/12)",
             any(f["role"] == "question" and "전화번호 1개" in f["what"] and "이메일 1개" in f["what"] and f["masked"] and not f["hidden"]
                 and "⟦가림:전화번호⟧" in f["preview"] and "010-1234-5678" not in f["preview"] for f in d["found"]))
        검사("로그인 안 했으면 링크 못 만듦", d["logged_in"] is False
             and c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST).status_code == 401)
        p = c.get(f"/local/export/preview?work_id={W}", **HOST)
        검사("미리 보기 PDF (로그인 없이)", p.status_code == 200 and p.data[:5] == b"%PDF-" and p.mimetype == "application/pdf",
             f"{len(p.data):,} 바이트")
        쪽 = {case: len(re.findall(rb"/Type\s*/Page[^s]", c.get(f"/local/export/preview?work_id=W-{case}", **HOST).data))
             for case in T.CASES if case != T.NO_PATH}
        검사("PDF 는 늘 한 장 (v3)", set(쪽.values()) == {1}, " · ".join(f"{k[6:]} {v}" for k, v in 쪽.items()))

        # 연결 확인에서 하나 연결 · 하나 연결 안 함 · 하나 잘 모르겠음
        cf = c.post("/local/confirm", data={"work_id": W}, headers=H, **HOST).json
        ks = [it["key"] for g in cf["groups"] for it in g["items"]]
        c.post("/local/confirm/decide", json={"work_id": W, "set": {ks[0]: "link", ks[1]: "no", ks[2]: "unsure"}}, headers=H, **HOST)
        d = E().json
        검사("연결 확인에서 고른 대로", (d["counts"]["confirmed"], d["counts"]["rejected"], d["counts"]["unsure"]) == (4, 1, 1))

        검사("설명 150자 넘으면 거절 · 기간은 7·14·30 만 · 가리기 모양 확인",
             D({"explain_use": "가" * 151}).status_code == 400 and D({"days": 10}).status_code == 400
             and D({"hide": {"x": "yes"}}).status_code == 400 and D({"hide": []}).status_code == 400)
        검사("고쳐 쓰는 것 저장", D({"explain_use": "서론은 Claude 답을 참고했어요", "days": 30}).status_code == 200
             and E().json["draft"] == {"explain_use": "서론은 Claude 답을 참고했어요", "explain_check": "", "days": 30,
                                       "with_source": True, "with_process": True})         # 10/13 기본 켬

        # 가짜 서버 · 로그인
        부름 = []

        def 서버(방법, 경로, **kw):
            부름.append((방법, 경로, kw.get("json")))
            if 방법 == "POST" and 경로.endswith("/statements"):
                return 201, {"id": f"st{len(부름)}", "verified": True, "problems": []}
            if 방법 == "POST" and 경로.endswith("/share"):
                return 201, {"url": f"https://trace.test/s/tok{len(부름)}", "pdf_url": f"https://trace.test/api/share/tok{len(부름)}/pdf",
                             "expires_at": "2099-01-01T00:00:00+09:00"}
            if 방법 == "DELETE":
                return 200, {"ok": True}
            return 404, {"error": "not_found"}
        S._기록.update(server=서버, auth=lambda: {"token": "t", "user": {"name": "시험 학생"}}, made=lambda w: None)
        EX._이름.clear()

        r = c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST)
        검사("만들기 → 링크 · PDF 주소", r.status_code == 200 and r.json["url"].startswith("https://trace.test/s/") and r.json["reused"] is False)
        만든 = [b for m, p, b in 부름 if m == "POST" and p.endswith("/statements")]
        나눔 = [b for m, p, b in 부름 if m == "POST" and p.endswith("/share")]
        body = 만든[-1] if 만든 else {}
        글 = json.dumps(body, ensure_ascii=False)
        rej = [l for l in body.get("links", []) if l["decision"] == "rejected"]
        conf = [l for l in body.get("links", []) if l["decision"] == "confirmed"]
        검사("연결함 4 · 연결 안 함 1 · 잘 모르겠음은 안 감", len(conf) == 4 and len(rej) == 1, f"links {len(body.get('links', []))}")
        안함글 = next(it["text"] for g in cf["groups"] for it in g["items"] if it["key"] == ks[1])
        모름글 = next(it["text"] for g in cf["groups"] for it in g["items"] if it["key"] == ks[2])
        # 문장 글이 AI 답과 똑같으면 같이 보낸 답 원문 안에 같은 글이 있을 수 있다 → 결과물 문장으로 갔는지만 본다
        결과들 = {l.get("result_text") for l in body.get("links", [])}
        검사("연결 안 함 · 잘 모르겠음 문장은 결과물로 안 감", 안함글 not in 결과들 and 모름글 not in 결과들 and "result_text" not in rej[0]
             and sha256_text(모름글) not in 글)
        qm = next(m for m in body["messages"] if "010-1234-5678" in m["text"])
        가린 = qm["text"]
        for a_, b_, k_ in sorted(qm.get("mask", []), reverse=True):
            가린 = 가린[:a_] + f"⟦가림:{k_}⟧" + 가린[b_:]
        검사("일부 가림: 원문은 확인용으로 · 가릴 자리(전화번호 · 이메일)를 같이 보냄",
             {k for _, _, k in qm.get("mask", [])} == {"전화번호", "이메일"} and "010-1234-5678" not in 가린 and "me@example.com" not in 가린
             and body["redactions"] == [])
        검사("잘 모르겠음은 개수만 · 출처 보기 · 작업 과정은 기본 켬 (10/13)", body.get("unsure") == 1 and isinstance(body.get("source"), dict)
             and body.get("show_process") is True)
        검사("학생 설명 · 링크 기간", body.get("explain_use") == "서론은 Claude 답을 참고했어요" and 나눔[-1] == {"expires_in_days": 30})
        src = c.post("/local/source", data={"work_id": W}, headers=H, **HOST).json
        rc = body.get("result_counts") or {}
        검사("v3 ③ 문장 수 = 출처 보기 (숫자만 감)", rc.get("total") == len(src["sentences"]) and rc.get("ai", 0) + rc.get("other", 0) == src["counts"]["copy"]
             and (rc.get("edited"), rc.get("viewed"), rc.get("none")) == (src["counts"]["edited"], src["counts"]["viewed"], src["counts"]["none"]),
             json.dumps(rc, ensure_ascii=False))
        uc = body.get("usage_counts") or {}
        검사("v3 ① 쓰임새 수 = 이 과제의 질문 수 (숫자만)", sum(uc.values()) == len(E().json["flow"]) and set(uc) == {"learn", "fix", "write"},
             json.dumps(uc, ensure_ascii=False))
        검사("v3 ① 쓰임새 규칙 (세 칸)", (EX.쓰임("1페이지짜리 보고서 써줘"), EX.쓰임("내 코드 맞는지 봐줘"), EX.쓰임("이 문장 자연스럽게 다듬어줘"),
                                EX.쓰임("국내 사례 찾아줘"), EX.쓰임("HTTP 와 HTTPS 차이가 뭐야?")) == ("write", "fix", "fix", "learn", "learn"))
        흐름 = E().json["flow"]
        검사("v3 ② 처음엔 결과물에 글이 들어간 질문 · 가린 질문은 빠짐", all(q["used"] and not q["hidden"] for q in 흐름 if q["picked"])
             and [f["event_id"] for f in body["flow"]] == [q["id"].split("/")[1] for q in 흐름 if q["picked"]])
        검사("대표 질문은 3개까지", D({"flow": ["a", "b", "c", "d"]}).status_code == 400)
        검사("보낸 원문은 모두 연결함의 답 · 질문", all(m["text"] for m in body["messages"])
             and {sha256_text(m["text"]) for m in body["messages"]} >= {l["answer_hash"] for l in conf})

        n = len(부름)
        r = c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST)
        검사("바뀐 게 없으면 또 만들지 않음 (같은 링크)", r.json.get("reused") is True and len(부름) == n)
        D({"explain_check": "숫자는 기사로 확인했어요"})
        r = c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST)
        검사("고치면 새로 만듦", r.json.get("reused") is False and len(부름) == n + 2)

        답 = next(f for f in E().json["found"] if f["role"] == "question")
        D({"mask": {답["id"]: False}})                                         # 그 부분 가리기를 끔 → 가릴 자리 없이
        c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST)
        검사("일부 가림을 끄면 가릴 자리 없이 감", all("mask" not in m for m in 부름[-2][2]["messages"]) and 부름[-2][2]["redactions"] == [])
        D({"hide": {답["id"]: True}})                                          # 통째로 가림 → 원문 대신 위치만
        c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST)
        b1 = 부름[-2][2]
        검사("통째로 가리면 원문 대신 위치만 · 연결의 질문 해시도 비움", "010-1234-5678" not in json.dumps(b1, ensure_ascii=False)
             and len(b1["redactions"]) == 1 and all(l.get("question_hash") is None for l in b1["links"] if l["decision"] == "confirmed"
                                                    and l["answer_hash"] == conf[0]["answer_hash"]))
        D({"hide": {답["id"]: False}, "mask": {답["id"]: True}})
        첫답 = E().json
        a_id = next(m["id"] for m in EX._보냄(EX._모으기(W), EX._읽기(W)) if m["role"] == "answer")
        D({"hide": {a_id: True}})
        d = E().json
        c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST)
        b2 = 부름[-2][2]
        검사("답을 가리면 그 연결은 빠지고 위치만", d["counts"]["dropped"] >= 1
             and len([l for l in b2["links"] if l["decision"] == "confirmed"]) == 4 - d["counts"]["dropped"]
             and {"session_id": a_id.split("/")[0], "event_id": a_id.split("/")[1]} in b2["redactions"])

        # 교수 링크 출처 보기 · 작업 과정 켜기 (김용현 #44 의 서버 기능) — 질문 · 답 전부가 가므로 가리기도 전부를 본다
        D({"with_source": True, "with_process": True, "hide": {a_id: False}})
        c.post("/local/export/make", json={"work_id": W}, headers=H, **HOST)
        b3 = 부름[-2][2]
        src = b3.get("source") or {}
        qs = [q for q in src.get("questions", []) if q.get("question")]
        검사("출처 보기를 켜면 보고서 전문 · 질문 · 답이 감 (번호는 가린 글로)", b3.get("show_process") is True and src.get("sentences")
             and qs and all("010-1234-5678" not in q["question"] for q in qs) and any("⟦가림:전화번호⟧" in q["question"] for q in qs)
             and all(sha256_text(m["text"]) for m in b3["messages"]) and len(b3["messages"]) >= len(body["messages"]),
             f"문장 {len(src.get('sentences', []))} · 질문 {len(src.get('questions', []))} · 원문 {len(b3['messages'])}")
        D({"with_source": False, "with_process": False})

        r = c.post("/local/export/revoke", json={"work_id": W}, headers=H, **HOST)
        검사("링크 끊기 → 서버 DELETE · 화면에서 링크 지움", r.status_code == 200 and 부름[-1][0] == "DELETE"
             and 부름[-1][1].startswith("/shares/tok") and E().json["made"] is None)

        txt = json.dumps(첫답, ensure_ascii=False) + E().get_data(as_text=True)
        검사("점수·퍼센트 없음 · PC 경로 없음", not re.search(r"ratio|score|\d+\s?%", txt) and data.replace("\\", "\\\\") not in txt)
        print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    finally:
        S._기록.clear(); S._기록.update(옛)
        shutil.rmtree(data, ignore_errors=True)
    return T.실패 == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(0 if main() else 1)
