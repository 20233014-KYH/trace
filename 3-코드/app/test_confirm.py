"""
test_confirm.py — 연결 확인 화면(app/confirm.py)을 녹화 시험 자료로. 서버 없이 돈다.

  python app/test_confirm.py              # 검사
  python app/test_source.py --serve       # 같은 자료로 화면 → http://127.0.0.1:5079/confirm?work=W-match_view

학생 PC 는 test_source.py 의 학생_PC() 로 똑같이 만든다. 확인하는 것:
  · 물을 문장 = 출처 보기의 counts.confirm 과 같다 (두 화면이 다른 수를 말하면 안 됨) · 붙여넣기 기록 있는 건 묻지 않음
  · AI 답마다 묶임 · 답이 나온 시각 순 · 칠한 글을 이으면 원문 그대로
  · 고른 것: 이 PC data 폴더에만 · 잘못된 키·값은 거절 · 지우기(null) · 문서를 다시 읽어도 같은 문장이면 그대로
  · 점수·퍼센트 없음 · 화면에 PC 경로 안 보냄
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_source as T                          # noqa: E402  학생 PC 만들기 · 같은 자료
ST = T.ST
검사 = T.검사


def 앞에_문단(경로, 글):
    """.docx 본문 맨 앞에 문단 하나 (Word 에서 고쳐 저장한 것처럼) — python-docx 없이 zip 안 document.xml 을 고친다"""
    with zipfile.ZipFile(경로) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    xml = re.sub(r"(<w:body[^>]*>)", lambda m: m.group(1) + f"<w:p><w:r><w:t>{글}</w:t></w:r></w:p>", xml, count=1)
    parts["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(경로, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            z.writestr(n, b)


def main():
    print("\n  연결 확인 화면 검사 — 녹화 시험 자료 · 서버 없음\n  " + "─" * 70)
    data = tempfile.mkdtemp(prefix="trace-cf-")
    try:
        T.학생_PC(data)
        ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)       # 서버는 안 부른다
        c = ST.app.test_client()
        H = {"X-Trace-Local": "1"}
        HOST = {"base_url": f"http://127.0.0.1:{ST.PORT}"}

        r = c.get("/confirm", **HOST)
        검사("화면 열림", r.status_code == 200 and "연결 확인" in r.get_data(as_text=True))
        검사("화면 틀 파일 (shell.css · shell.js)", c.get("/ui/shell.css", **HOST).status_code == 200
             and c.get("/ui/shell.js", **HOST).status_code == 200 and c.get("/ui/statement.py", **HOST).status_code == 404)
        r = c.post("/local/confirm", data={"work_id": f"W-{T.NO_PATH}"}, headers=H, **HOST)
        검사("문서를 못 열면 출처 보기로 보냄", r.status_code == 400 and r.json["error"] == "no_file")
        검사("X-Trace-Local 없으면 거절", c.post("/local/confirm", data={"work_id": "W-match_view"}, **HOST).status_code == 403
             and c.post("/local/confirm/decide", json={}, **HOST).status_code == 403)

        물은 = {}
        for case in T.CASES:
            if case == T.NO_PATH:
                continue
            print(f"\n  ━━ {case}")
            wid = f"W-{case}"
            src = c.post("/local/source", data={"work_id": wid}, headers=H, **HOST).json
            r = c.post("/local/confirm", data={"work_id": wid}, headers=H, **HOST)
            if r.status_code != 200:
                검사("연결 확인 응답", False, str(r.json)); continue
            d = r.json
            items = [it for g in d["groups"] for it in g["items"]]
            검사("물을 문장 수 = 출처 보기 counts.confirm", len(items) == src["counts"]["confirm"], f"답 {len(d['groups'])} · 문장 {len(items)}")
            by_k = {x["k"]: x for x in src["sentences"]}
            검사("붙여넣기 기록 있는 건 안 물음", all(not by_k[it["k"]].get("paste") and it["kind"] in ("exact", "similar", "edited", "viewed") for it in items))
            검사("확실한 연결 수 = 붙여넣기 기록 있는 AI 연결",
                 d["auto"] == sum(1 for x in src["sentences"] if x["kind"] in ("exact", "similar", "edited", "viewed") and x.get("paste")),
                 f"자동 {d['auto']}")
            검사("AI 답마다 한 묶음 · 답 시각 순",
                 all(by_k[it["k"]].get("q") is not None for it in items)
                 and len({g["id"] for g in d["groups"]}) == len(d["groups"])
                 and [g["a_ts"] for g in d["groups"]] == sorted(g["a_ts"] for g in d["groups"]))
            검사("칠한 글을 이으면 결과물 문장 그대로", all("".join(s["t"] for s in it["segs"]) == it["text"] for it in items))
            원문들 = {m["text"].replace("**", "") for m in T.L(case, "ai_answers")}
            검사("AI 답 원문 그대로 · 칠한 곳 있음",
                 all("".join(p["t"] for p in g["answer"]) in 원문들 for g in d["groups"])
                 and all(any(s["m"] for p in g["answer"] if p["on"] for s in p["segs"]) for g in d["groups"]))
            검사("키 모양 (문장 해시 . 답 해시)", all(re.fullmatch(r"[0-9a-f]{16}\.[0-9a-f]{16}", it["key"]) for it in items)
                 and len({it["key"] for it in items}) == len(items))
            검사("입력 시각은 처음 ≤ 끝", all(it["typed"] is None or it["typed"][0] <= it["typed"][1] for it in items),
                 f"시각 찾음 {sum(1 for it in items if it['typed'])}/{len(items)}")
            txt = r.get_data(as_text=True)
            검사("점수·퍼센트 없음 · PC 경로 없음", not re.search(r"ratio|cover|score|\d+\s?%", txt) and data.replace("\\", "\\\\") not in txt
                 and "path" not in txt)
            물은[case] = d

        print("\n  ━━ 고르기")
        d = 물은["match_view"]
        ks = [it["key"] for it in d["groups"][0]["items"]]
        P = lambda body, **kw: c.post("/local/confirm/decide", json=body, headers=H, **HOST, **kw)
        검사("잘못된 키 · 값 거절", P({"work_id": "W-match_view", "set": {"../x": "link"}}).status_code == 400
             and P({"work_id": "W-match_view", "set": {ks[0]: "yes"}}).status_code == 400
             and P({"work_id": "W-match_view", "set": {}}).status_code == 400
             and P({"set": {ks[0]: "link"}}).status_code == 400)
        r = P({"work_id": "W-match_view", "set": {ks[0]: "link", ks[1]: "no", ks[2]: "unsure"}})
        검사("연결함 · 연결 안 함 · 잘 모르겠음 저장", r.status_code == 200 and r.json["decisions"] == {ks[0]: "link", ks[1]: "no", ks[2]: "unsure"})
        r = P({"work_id": "W-match_view", "set": {ks[2]: None}})
        검사("null = 고른 것 지우기", ks[2] not in r.json["decisions"] and len(r.json["decisions"]) == 2)
        파일 = os.path.join(data, "confirm-W-match_view.json")
        검사("이 PC data 폴더에만 저장", os.path.isfile(파일) and json.load(open(파일, encoding="utf-8"))["decisions"][ks[0]] == "link")
        again = c.post("/local/confirm", data={"work_id": "W-match_view"}, headers=H, **HOST).json
        검사("다시 열어도 고른 것 그대로", again["decisions"] == {ks[0]: "link", ks[1]: "no"})
        검사("내역서가 읽어 갈 곳", c.get("/local/confirm/decisions?work_id=W-match_view", **HOST).json["decisions"] == again["decisions"])
        검사("다른 과제엔 안 섞임", c.get("/local/confirm/decisions?work_id=W-match_mix", **HOST).json["decisions"] == {})

        # Word 에서 문서를 고쳐 저장 → 앞에 문단이 하나 생겨도 같은 문장은 같은 키 (문장 번호가 아니라 글로 잇는다)
        경로 = os.path.join(data, "문서", "match_view", next(e["file"] for e in T.L("match_view", "events") if e.get("file")))
        앞에_문단(경로, "고쳐 저장하며 맨 앞에 넣은 새 문단입니다.")
        고친뒤 = c.post("/local/confirm", data={"work_id": "W-match_view"}, headers=H, **HOST).json
        새키 = [it["key"] for g in 고친뒤["groups"] for it in g["items"]]
        검사("문서를 고쳐도 같은 문장이면 고른 것 유지", ks[0] in 새키 and 고친뒤["decisions"].get(ks[0]) == "link",
             f"문단 {d['groups'][0]['items'][0]['p']} → {고친뒤['groups'][0]['items'][0]['p']}")

        print("\n  ━━ 왼쪽 과제를 누르면 그 과제의 지금 단계로 (/go)")
        갈곳 = lambda w: c.get(f"/go?work={w}", **HOST).headers.get("Location", "")
        웹 = os.path.join(data, "confirm-W-match_web.json")       # match_web 은 물을 것 0 (붙여넣기 기록으로 다 확실)
        검사("물을 것 없는 과제는 연결 확인을 보면 내역서로 (10/14)", os.path.exists(웹) and 갈곳("W-match_web").endswith("/export?work=W-match_web"))
        os.remove(웹)                                             # ↓ 연결 확인을 아직 안 본 과제로 되돌림
        검사("고른 것 없으면 출처 보기", 갈곳("W-match_web").endswith("/source?work=W-match_web"))
        검사("고르다 말았으면 연결 확인", 갈곳("W-match_view").endswith("/confirm?work=W-match_view"))
        P({"work_id": "W-match_view", "set": {k: "unsure" for k in 새키}})
        검사("다 골랐으면 내역서 (다음 할 일)", 갈곳("W-match_view").endswith("/export?work=W-match_view"))
        옛것 = ST.출처._기록["statement_exists"]
        ST.출처._기록["statement_exists"] = lambda w: w == "W-match_mix"            # 서버에 내역서가 있다고 치고
        검사("내역서를 만든 과제는 내역서", 갈곳("W-match_mix").endswith("/export?work=W-match_mix") and 갈곳("W-match_web").endswith("/source?work=W-match_web"))
        ST.출처._기록["statement_exists"] = 옛것
        검사("로그인 안 했으면 서버에 안 물음 (PC 기록만)", 옛것("W-match_mix") is None)
        S_ = lambda w: c.get(f"/local/stage?work_id={w}", **HOST).json
        검사("단계 점: 지금 할 단계 · 내역서 만들었나", S_("W-match_view") == {"stage": "report", "report_made": False}
             and S_("W-match_web") == {"stage": "source", "report_made": False})
        검사("과제 이름에 특수 문자도 안전 · 기록 없는 과제는 과제 상세로", 갈곳("a%26b%3Fc").endswith("/work?work=a%26b%3Fc"))

        깨짐 = os.path.join(data, "confirm-W-match_app.json")
        open(깨짐, "w", encoding="utf-8").write("{깨진 파일")
        r = c.post("/local/confirm", data={"work_id": "W-match_app"}, headers=H, **HOST)
        검사("저장 파일이 깨져도 화면은 열림 (고른 것 없음)", r.status_code == 200 and r.json["decisions"] == {})
        print(f"\n  {'─' * 70}\n  통과 {T.통과} · 실패 {T.실패}\n")
    finally:
        shutil.rmtree(data, ignore_errors=True)
    return T.실패 == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(0 if main() else 1)
