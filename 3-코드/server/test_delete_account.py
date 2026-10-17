"""
test_delete_account.py — 계정 지우기 (10/15 · server/app.py POST /api/me/delete) — 서버는 이 프로세스 안 · 임시 DB

  python 3-코드/server/test_delete_account.py

확인하는 것:
  · 토큰만으로는 못 지움 — 비밀번호(있으면) · "계정 삭제"(구글 · 카카오로만 가입했으면)
  · 지우면: 과제마다 과제 지우기와 같은 규칙 (기록 내용 · 내역서 원문 지움 · 교수 링크는 "지운 기록입니다") · 토큰 끊김 · 로그인 안 됨
  · 계정 줄엔 지운 시각만 — 이메일 · 이름 · 비밀번호 · 구글 · 카카오 연결 지움 → 같은 이메일로 다시 가입 · 카카오로 다시 오면 새 계정
  · 다른 사람 과제는 그대로
"""
import os
import sys
import tempfile
import uuid
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
d = tempfile.mkdtemp(prefix="trace-delacct-")
os.environ["TRACE_DB_URL"] = "sqlite:///" + os.path.join(d, "server.db")
os.environ.update(KAKAO_CLIENT_ID="rest-key", KAKAO_CLIENT_SECRET="카카오-비밀")
import app as A                                   # noqa: E402
from core import chain as C                       # noqa: E402
from core.texthash import sha256_text             # noqa: E402

통과, 실패 = 0, 0


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    통과, 실패 = 통과 + bool(조건), 실패 + (not 조건)
    print(f"  {'✅' if 조건 else '❌'} {이름:<46} {설명}")


s = A.app.test_client()


def 가입(이메일, 비번, 이름):
    s.post("/api/auth/signup", json={"email": 이메일, "password": 비번, "name": 이름})
    return {"Authorization": "Bearer " + s.post("/api/auth/login", json={"email": 이메일, "password": 비번}).get_json()["token"]}


def 과제와_기록(H, 제목):
    """과제 · 봉인한 기록(AI 답 해시) · 내역서 · 교수 링크 → (wid, sid, 링크 토큰)"""
    wid = s.post("/api/works", json={"title": 제목}, headers=H).get_json()["id"]
    sid = str(uuid.uuid4())
    s.post(f"/api/works/{wid}/sessions", json={"id": sid, "started_at": "2026-10-15T10:00:00+09:00",
                                                "device": {"name": "T", "os": "mac"}}, headers=H)
    답 = "광합성은 빛에너지를 화학에너지로 바꾸는 과정입니다."
    evs = [{"id": "e1", "ts": "2026-10-15T10:00:00+09:00", "type": "session_start"},
           {"id": "e2", "ts": "2026-10-15T10:01:00+09:00", "type": "ai_msg", "tool": "chatgpt", "conv": "c", "turn": "1",
            "role": "answer", "len": len(답), "hash": sha256_text(답)},
           {"id": "e3", "ts": "2026-10-15T10:30:00+09:00", "type": "session_end"}]
    prev = C.GENESIS
    for e in evs:
        prev = C.next_hash(prev, e)
        e["h"] = prev
    s.post(f"/api/sessions/{sid}/events", json={"events": evs, "chain_head": prev, "chain_len": len(evs)}, headers=H)
    s.post(f"/api/sessions/{sid}/end", json={"ended_at": evs[-1]["ts"], "root": prev}, headers=H)
    st = s.post(f"/api/works/{wid}/statements", json={"messages": [{"session_id": sid, "event_id": "e2", "text": 답}],
                                                       "links": [{"answer_hash": sha256_text(답), "result_hash": sha256_text("결과"),
                                                                  "result_text": "결과", "decision": "confirmed"}]}, headers=H).get_json()
    tok = s.post(f"/api/statements/{st['id']}/share", json={}, headers=H).get_json()["token"]
    return wid, sid, tok


def main():
    print("\n  계정 지우기 검사 — 임시 DB\n  " + "─" * 70)
    갑 = 가입("Kim@Naver.com", "갑비번12345678", "갑")
    을 = 가입("lee@naver.com", "을비번12345678", "을")
    w1, sid1, 링크 = 과제와_기록(갑, "갑의 과제")
    w2, _, _ = 과제와_기록(갑, "갑의 두 번째")
    wb, _, 을링크 = 과제와_기록(을, "을의 과제")
    검사("준비: 교수 링크 열림", s.get(f"/api/share/{링크}").status_code == 200)

    검사("토큰만으로는 못 지움 (비밀번호 없음 · 틀림 → 403)",
         s.post("/api/me/delete", json={}, headers=갑).status_code == 403
         and s.post("/api/me/delete", json={"password": "틀린비번123"}, headers=갑).status_code == 403
         and s.get("/api/me", headers=갑).status_code == 200)
    검사("로그인 안 하면 못 지움", s.post("/api/me/delete", json={"password": "갑비번12345678"}).status_code == 401)
    r = s.post("/api/me/delete", json={"password": "갑비번12345678"}, headers=갑)
    j = r.get_json() or {}
    검사("비밀번호로 지움 → 지운 과제 목록 · 기록 수", r.status_code == 200 and sorted(j.get("works", [])) == sorted([w1, w2]) and j.get("sessions") == 2, f"{j}")
    검사("토큰 끊김 · 로그인 안 됨", s.get("/api/me", headers=갑).status_code == 401
         and s.post("/api/auth/login", json={"email": "kim@naver.com", "password": "갑비번12345678"}).status_code == 401)
    r = s.get(f"/api/share/{링크}")
    검사("교수 링크: \"지운 기록입니다\" (과제 지우기와 같은 규칙)", r.status_code == 410 and "지운 기록" in (r.get_json() or {}).get("message", ""))
    with A.db.Session() as x:
        u = x.query(A.db.User).filter(A.db.User.email.like("deleted-%")).one()
        이벤트 = x.query(A.db.Event).filter(A.db.Event.session_id == sid1).count()
        메시지 = x.query(A.db.Message).filter(A.db.Message.session_id == sid1).count()
        과제 = x.get(A.db.Work, w1)
        검사("계정 줄엔 지운 시각만 (이메일 · 이름 · 비밀번호 · 연결 지움)", u.deleted_at and u.name is None and u.password_hash == "!deleted"
             and u.email.endswith("@deleted.trace") and not u.google_sub and not u.kakao_sub)
        검사("기록 내용 · 내역서 원문 지움 · 과제 줄엔 지운 시각", 이벤트 == 0 and 메시지 == 0 and 과제.deleted_at and 과제.title is None)
    검사("같은 이메일로 다시 가입 (새 계정)", s.post("/api/auth/signup", json={"email": "kim@naver.com", "password": "새비번12345678"}).status_code == 201)
    검사("다른 사람 과제 · 링크는 그대로", s.get(f"/api/share/{을링크}").status_code == 200
         and [w["id"] for w in s.get("/api/me", headers=을).get_json()["works"]] == [wb])

    # 카카오로만 가입한 계정 — 비밀번호가 없으니 "계정 삭제" 를 그대로 쳐야
    A._카카오_코드_바꾸기 = lambda code, r, c: {"sub": "k-77", "email": None, "email_verified": False, "name": "카톡"}

    def 카카오_로그인():
        q = parse_qs(urlparse(s.get("/api/auth/kakao/start?pc=pc-state-0123456789abcdef&port=5079").headers["Location"]).query)
        r2 = s.get(f"/api/auth/kakao/callback?code=c&state={q['state'][0]}")
        t = parse_qs(urlparse(r2.headers["Location"]).query)["ticket"][0]
        return s.post("/api/auth/kakao/claim", json={"ticket": t}).get_json()
    k = 카카오_로그인()
    K = {"Authorization": f"Bearer {k['token']}"}
    검사("카카오로만: 확인 글 없거나 틀리면 400", s.post("/api/me/delete", json={}, headers=K).status_code == 400
         and s.post("/api/me/delete", json={"confirm": "삭제"}, headers=K).status_code == 400)
    r = s.post("/api/me/delete", json={"confirm": "계정 삭제"}, headers=K)
    k2 = 카카오_로그인()
    검사("카카오로만: '계정 삭제' 로 지움 → 카카오로 다시 오면 새 계정", r.status_code == 200 and k2["user"]["id"] != k["user"]["id"])

    print(f"  {'─' * 70}\n  {통과}개 통과, {실패}개 실패\n")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main())
