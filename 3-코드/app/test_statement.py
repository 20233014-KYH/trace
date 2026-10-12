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
    검사("1 틀린 비번은 거절 · 어느 서버인지 알려 줌", r.status_code == 401 and "로그인할 서버" in r.get_json().get("message", ""),
         r.get_json().get("message", "")[:60])
    새 = f"new{uuid.uuid4().hex[:8]}@test.kr"
    r = c.post("/local/signup", json={"email": 새, "password": "가입비번12345", "name": "새학생"}, headers=H)
    검사("1b 화면에서 가입 → 바로 로그인", r.status_code == 200 and r.get_json().get("user", {}).get("name") == "새학생", f"HTTP {r.status_code}")
    c.post("/local/logout", headers=H)
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
                                         "explain_use": "정의 문장은 거의 그대로, 나머지는 줄여 썼습니다.",
                                         "explain_check": "교재와 비교했습니다."}, headers=H)
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
    검사("14 질문 두 칸 · 규칙은 안 넣음", 교수.get("explain_check") == "교재와 비교했습니다." and 교수.get("ai_scope") is None, "")

    # ⑮ 연결 확인(박상진 · confirm.py)에서 고른 것을 내역서가 이어받는다 (10/12)
    import confirm as CF
    묻는것 = [s for s in 제안 if not s["pasted"]]
    답해시 = lambda s: ST.분석들[a["id"]]["links"][s["key"]]["answer"]["hash"]
    고른것 = {CF.key_of(묻는것[0]["text"], 답해시(묻는것[0])): "link",
              CF.key_of(묻는것[1]["text"], 답해시(묻는것[1])): "no",
              CF.key_of(묻는것[2]["text"], 답해시(묻는것[2])): "unsure"}
    r = c.post("/local/confirm/decide", json={"work_id": wid, "set": 고른것}, headers=H)
    검사("15 연결 확인에 고름 저장", r.status_code == 200, f"HTTP {r.status_code}")
    with open(os.path.join(FX, "report.docx"), "rb") as f:
        a2 = c.post("/local/analyze", data={"work_id": wid, "file": (f, "정규화_보고서.docx")}, headers=H,
                    content_type="multipart/form-data").get_json()
    미리 = {s["text"]: s.get("preset") for p in a2["paragraphs"] for s in p if s.get("key")}
    검사("16 붙여넣기 기록 있는 건 자동 '맞다'", all(미리[s["text"]] == "confirmed" for s in 제안 if s["pasted"]), "")
    검사("17 연결 확인에서 고른 대로", [미리[s["text"]] for s in 묻는것[:3]] == ["confirmed", "rejected", "unsure"],
         f"{[미리[s['text']] for s in 묻는것[:3]]}")
    고름2 = {s["key"]: s["preset"] for p in a2["paragraphs"] for s in p if s.get("key") and s.get("preset")}
    r = c.post("/local/statement", json={"analysis_id": a2["id"], "decisions": 고름2}, headers=H)
    st2 = r.get_json()
    sh2 = c.post("/local/share", json={"statement_id": st2.get("id")}, headers=H).get_json()
    교수2 = requests.get(BASE + "/share/" + sh2["url"].rsplit("/", 1)[-1], timeout=30).json()
    보류글 = 묻는것[2]["text"]
    기대 = sum(1 for p in a2["paragraphs"] for s in p if s.get("key") and 고름2.get(s["key"]) not in ("confirmed", "rejected"))
    검사("18 잘 모르겠음 = 개수만 ★", 기대 >= 1 and 교수2.get("unsure") == 기대, f"보류 {교수2.get('unsure')}개 (잘 모르겠음 + 안 고름)")
    검사("19 보류한 문장 원문은 안 나감", 보류글 not in json.dumps(교수2, ensure_ascii=False), "")

    # ⑯ 교수 링크 출처 보기 — 기본 끔 · 켰을 때만 보고서 전문 (10/11 · 10/12)
    검사("20 기본은 출처 보기 없음", "source" not in 교수2 and 교수2.get("show_process") is False, "")
    r = c.post("/local/statement", json={"analysis_id": a2["id"], "decisions": 고름2, "hide_questions": [가림],
                                         "with_source": True, "with_process": True}, headers=H)
    st3 = r.get_json()
    검사("21 출처 보기 켜고 내역서 = 검증됨", r.status_code == 201 and st3.get("verified") is True, f"문제 {st3.get('problems')}")
    sh3 = c.post("/local/share", json={"statement_id": st3.get("id")}, headers=H).get_json()
    t3 = sh3["url"].rsplit("/", 1)[-1]
    교수3 = requests.get(BASE + "/share/" + t3, timeout=30).json()
    src = 교수3.get("source") or {}
    문장들 = src.get("sentences", [])
    검사("22 보고서 전문 + 문장별 종류", len(문장들) >= 8 and {"copy", "none"} <= {x["group"] for x in 문장들},
         f"문장 {len(문장들)}개 · {sorted({x['kind'] for x in 문장들})}")
    아니다글 = 묻는것[1]["text"]
    검사("23 '아니다' 문장은 출처 없음으로", any(x["text"] == 아니다글 and x["group"] == "none" and x.get("rejected") for x in 문장들), "")
    Q = src.get("questions", [])
    검사("24 질문 기준: 가린 질문은 원문 없이", any(q.get("hidden") and q.get("question") is None for q in Q)
         and 가린질문 not in json.dumps(교수3, ensure_ascii=False), f"질문 {len(Q)}개")
    검사("25 질문·답 원문을 서버가 맞춰 봄", all(q.get("answer_ok") is True for q in Q if q.get("answer")), "")
    검사("26 작업 과정 켬 → 기록 목록", len((교수3.get("summary") or {}).get("by_session", [])) == 1, "")
    requests.delete(BASE + f"/shares/{t3}", headers={"Authorization": "Bearer " + json.load(open(os.path.join(data, "auth.json")))["token"]}, timeout=30)
    r = c.get(f"/local/works", headers=H)                                     # 끊은 뒤 학생 쪽에서 다시 보기
    latest = requests.get(BASE + f"/works/{wid}/statements/latest",
                          headers={"Authorization": "Bearer " + json.load(open(os.path.join(data, "auth.json")))["token"]}, timeout=30).json()
    검사("27 링크를 끊으면 보고서 전문을 지움 ★", latest.get("id") == st3["id"] and "source" not in latest, "살아 있는 링크가 없으면 서버에 안 둠")

    # ⑰ 설정 파일 하나로 (10/13) — 로그인 화면에서 서버를 바꾸면 내 설정(~/trace-config.json)에 적힌다
    from core import settings as SET
    내설정 = os.path.join(data, "trace-config.json")                # 시험에선 진짜 홈 대신 임시 폴더
    SET.USER = 내설정
    검사("28 내 설정이 있으면 그걸 먼저", SET.config_path() == SET.REPO and (open(내설정, "w").write("{}") or True)
         and SET.config_path() == 내설정, "")
    os.remove(내설정)
    r = c.post("/local/server", json={"to": "internet"}, headers=H).get_json()
    저장 = json.load(open(내설정, encoding="utf-8"))
    검사("29 인터넷 서버로 바꾸기 → 내 설정에 저장", r.get("server") == SET.INTERNET and 저장["server"] == SET.INTERNET
         and 저장.get("capture") is not None, "저장소 기본 설정을 복사해서 server 만 바꿈")
    s2 = c.get("/local/state", headers=H).get_json()
    검사("30 서버를 바꾸면 로그인은 새로", s2.get("server_local") is False and s2.get("logged_in") is False,
         "토큰은 서버마다 따로 (auth.json 의 server)")
    ST.설정["server"] = BASE                                         # 뒤 검사를 위해 되돌림

    print("  " + "─" * 70 + f"\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
