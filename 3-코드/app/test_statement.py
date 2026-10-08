"""
test_statement.py — 학생 PC 의 내역서 화면(app/statement.py)을 처음부터 끝까지.

  python 3-코드/server/app.py                 # 다른 창에서 서버를 켜고 (시험용 SQLite 권장)
  python 3-코드/app/test_statement.py

학생 PC 흉내: tests/fixtures/match_rec (실제 녹화 시험 · 실제 ChatGPT 답 2개 · 실제 Word) 로 data 폴더를 임시로 만들고,
같은 이벤트를 토큰을 붙여 서버에 보낸다(주인 있는 과제). 그다음 화면이 부르는 주소를 그대로 부른다:
  로그인 → 과제 목록 → 과제 파일 분석 → 맞다·아니다·질문 가리기 → 내역서 만들기 → 링크 → 교수 화면 데이터
"""
import json
import os
import sys
import tempfile
import uuid

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from core import chain as C                     # noqa: E402
from core.texthash import sha256_text           # noqa: E402
import statement as ST                          # noqa: E402

BASE = f"http://127.0.0.1:{os.environ.get('TRACE_PORT', '5000')}/api"
FX = os.path.join(ROOT, "tests", "fixtures", "match_rec")
통과, 실패 = 0, 0


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✅' if 조건 else '❌'} {이름:<30} {설명}")


def L(name):
    return [json.loads(l) for l in open(os.path.join(FX, name + ".jsonl"), encoding="utf-8") if l.strip()]


def 학생_PC(data, email, pw):
    """match_rec 으로 기록기가 남겼을 파일 세 가지를 만들고, 같은 이벤트를 서버에 보낸다."""
    requests.post(BASE + "/auth/signup", json={"email": email, "password": pw, "name": "김학생"}, timeout=30)
    tok = requests.post(BASE + "/auth/login", json={"email": email, "password": pw}, timeout=30).json()["token"]
    H = {"Authorization": f"Bearer {tok}"}
    wid = "W-" + uuid.uuid4().hex[:8]
    requests.post(BASE + "/works", json={"id": wid, "title": "데이터베이스 정규화 보고서"}, headers=H, timeout=30)
    sid = str(uuid.uuid4())
    evs, 원문 = [{"type": "session_start", "ts": "2026-10-05T15:10:00+09:00", "work_id": wid}], {}
    for k, a in enumerate(L("ai_answers")):
        for role, text, t in (("question", a["question"], f"2026-10-05T15:1{1 + k * 2}:00+09:00"),
                              ("answer", a["text"], f"2026-10-05T15:1{1 + k * 2}:20+09:00")):
            evs.append({"type": "ai_msg", "ts": t, "tool": "ChatGPT", "conv": "c1", "turn": str(k * 2 + 1), "role": role,
                        "len": len(text), "hash": sha256_text(text)})
            원문[sha256_text(text)] = text
    evs += [{k: v for k, v in e.items() if k not in ("id", "h", "session_id")} for e in L("events")]
    evs.append({"type": "session_end", "ts": "2026-10-05T15:40:00+09:00"})
    evs.sort(key=lambda e: e["ts"])
    prev = C.GENESIS
    for i, e in enumerate(evs):
        e.update(id=f"evt_{i + 1:06d}", session_id=sid)
        prev = C.next_hash(prev, e)
        e["h"] = prev
    def 쓰기(name, rows):
        with open(os.path.join(data, name), "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    쓰기("events-2026-10-05.jsonl", evs)
    쓰기("context-2026-10-05.jsonl", [{"session_id": sid, **c} for c in L("context")])
    쓰기("ai-messages-2026-10-05.jsonl", [{"session_id": sid, "event_id": e["id"], "ts": e["ts"], "tool": e["tool"],
                                           "turn": e["turn"], "role": e["role"], "hash": e["hash"], "text": 원문[e["hash"]]}
                                          for e in evs if e["type"] == "ai_msg"])
    requests.post(BASE + f"/works/{wid}/sessions", json={"id": sid, "started_at": evs[0]["ts"]}, headers=H, timeout=30)
    requests.post(BASE + f"/sessions/{sid}/events", json={"events": evs, "chain_head": prev}, timeout=30)
    requests.post(BASE + f"/sessions/{sid}/end", json={"ended_at": evs[-1]["ts"], "root": prev}, timeout=30)
    return wid


def main():
    print(f"\n  학생 PC 내역서 화면 검사 — 서버 {BASE}\n  " + "─" * 70)
    try:
        requests.get(BASE + "/health", timeout=30)
    except requests.RequestException:
        sys.exit("  서버를 먼저 켜 주세요:  python 3-코드/server/app.py")
    data = tempfile.mkdtemp(prefix="trace-pc-")
    email, pw = f"pc{uuid.uuid4().hex[:8]}@test.kr", "테스트비번12345"
    wid = 학생_PC(data, email, pw)
    ST.설정.update(server=BASE, data_dir=data)
    c = ST.app.test_client()
    H = {"Host": f"127.0.0.1:{ST.PORT}", "X-Trace-Local": "1"}

    r = c.post("/local/login", json={"email": email, "password": "틀린비번00000"}, headers=H)
    검사("1 틀린 비번은 거절", r.status_code == 401, f"HTTP {r.status_code}")
    r = c.post("/local/login", json={"email": email, "password": pw}, headers=H)
    검사("2 로그인 → 토큰은 data/auth.json", r.status_code == 200 and os.path.exists(os.path.join(data, "auth.json")), "")
    r = c.post("/local/logout", headers={"Host": H["Host"]})
    검사("3 머리 없는 요청은 막음", r.status_code == 403, f"HTTP {r.status_code} (다른 사이트가 부르는 것 방지)")
    r = c.get("/local/state", headers={"Host": "evil.example:5079"})
    검사("4 다른 Host 는 막음", r.status_code == 403, f"HTTP {r.status_code}")

    r = c.get("/local/works", headers=H).get_json()
    w = next((x for x in r["works"] if x["id"] == wid), {})
    검사("5 내 과제 + 이 PC 기록 수", w.get("pc_sessions") == 1, f"{w.get('title')} · 기록 {w.get('pc_sessions')}번")

    with open(os.path.join(FX, "report.docx"), "rb") as f:
        r = c.post("/local/analyze", data={"work_id": wid, "file": (f, "정규화_보고서.docx")}, headers=H,
                   content_type="multipart/form-data")
    a = r.get_json()
    제안 = [s for p in a.get("paragraphs", []) for s in p if s.get("key")]
    종류 = sorted(s["kind"] for s in 제안)
    검사("6 문장마다 연결 제안", r.status_code == 200 and len(제안) == 6, f"{종류}")
    검사("7 match_rec 정답과 같은 모양", 종류.count("exact") == 2 and 종류.count("edited") == 2 and 종류.count("viewed") == 2,
         "일치 2 · 붙여넣고 고침 2 · 보고 씀 2")

    # 고르기: 다섯째는 아니다 · 둘째 답(인덱스)의 질문은 가린다
    고름 = {s["key"]: "confirmed" for s in 제안}
    아니다 = 제안[4]
    고름[아니다["key"]] = "rejected"
    가림 = 제안[3]["question"]["id"]
    r = c.post("/local/statement", json={"analysis_id": a["id"], "decisions": 고름, "hide_questions": [가림],
                                         "sentence": "정의 문장은 거의 그대로, 나머지는 줄여 썼습니다."}, headers=H)
    st = r.get_json()
    검사("8 내역서 만들기 = 검증됨", r.status_code == 201 and st.get("verified") is True, f"문제 {st.get('problems')}")
    검사("9 원문은 맞다인 답·안 가린 질문만", st.get("counts", {}).get("messages") == 3
         and st["counts"]["redactions"] == 1 and st["counts"]["links_rejected"] == 1,
         f"{st.get('counts')}")

    r = c.post("/local/share", json={"statement_id": st.get("id"), "days": 7}, headers=H)
    url = r.get_json().get("url", "")
    검사("10 교수에게 보낼 링크", r.status_code == 201 and "/s/" in url, url)
    교수 = requests.get(BASE + "/share/" + url.rsplit("/", 1)[-1], timeout=30).json()
    글 = json.dumps(교수, ensure_ascii=False)
    검사("11 교수 화면: 아니다 문장 없음 ★", 아니다["text"] not in 글 and 교수.get("rejected") == 1, "")
    가린질문 = 제안[3]["question"]["text"]
    검사("12 교수 화면: 가린 질문 없음 ★", 가린질문 not in 글 and 교수.get("redacted") == 1, "")
    검사("13 교수 화면: 연결 5개", len(교수.get("links", [])) == 5, f"{len(교수.get('links', []))}개")

    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
