"""
app.py — Trace Backend (A)

  python 3-코드/server/app.py          → http://127.0.0.1:5000/api

★ 이 파일은 dev_receiver.py 를 '옮긴' 것이다. 새로 짠 것이 아니다 ★
  · 엔드포인트·요청·응답의 모양을 한 글자도 바꾸지 않았다.
    B 의 수집기와 화면이 그 모양을 보고 만들어졌기 때문이다.
  · 바꾼 것은 저장하는 곳뿐이다:  메모리 dict  →  DB (server/db.py)
  · 해시는 core/chain.py 를 import 해서 쓴다. 여기서 다시 계산하지 않는다.
    두 곳에서 계산하면 영원히 안 맞는다. (계약 9절)

계약: docs/api.md
참고 구현: 3-코드/collector/dev_receiver.py  — 둘은 같은 응답을 내야 한다
"""
import base64
import functools
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sys
import time
import traceback
import unicodedata
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlencode
import zlib
from datetime import datetime, timedelta, timezone

from flask import Flask, g, jsonify, redirect, request, send_from_directory
from sqlalchemy import insert
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # 3-코드/ 를 경로에 넣어 core 를 쓴다

from core import chain as C          # noqa: E402  ★ 해시는 여기서만
from core.derive import derive       # noqa: E402
from core.texthash import sha256_text  # noqa: E402  ★ 원문 해시도 여기서만 (내역서 검증)
from core.summary import work_summary  # noqa: E402  요약 숫자 — 체인 이벤트로 센다
from core.settings import INTERNET     # noqa: E402  견본 QR 이 가리키는 곳
import db                            # noqa: E402

KST = timezone(timedelta(hours=9))
LATE_SEC = 5 * 60                    # 이벤트 시각 vs 수신 시각 차이가 이보다 크면 "지연 수신"

app = Flask(__name__)
# Render 는 앞단(프록시)이 https 를 받고 우리에겐 http 로 넘긴다. 이걸 안 하면 교수용 링크가 http:// 로 만들어진다
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
db.init()


def now():
    return datetime.now(KST)


def iso():
    return now().isoformat(timespec="seconds")


def 세션_가져오기(db세션, sid, create=False):
    s = db세션.get(db.Sess, sid)
    if s is None and create:
        s = db.Sess(id=sid, head=C.GENESIS, chain_len=0, integrity_ok=True, anchor_status="none")
        db세션.add(s)
    return s


def 이벤트들(db세션, sid):
    """저장된 이벤트를 받은 순서대로. derive·chain 이 쓸 원본 그대로 돌려준다."""
    행들 = (db세션.query(db.Event)
            .filter(db.Event.session_id == sid)
            .order_by(db.Event.seq).all())
    return [r.payload for r in 행들]


# ─────────────────────────── 인증 (계약 1절) ───────────────────────────
#
# ★ 지금은 '켜져 있지만 강제하지 않는다' ★
#   B 의 수집기는 아직 토큰을 안 보낸다. 여기서 401 을 던지기 시작하면
#   10/7 관통 테스트가 그대로 깨진다.
#   그래서 기본값은 끔. 수집기가 토큰을 보내게 되면 그때 켠다.
#
#       TRACE_REQUIRE_AUTH=1 python server/app.py
#
#   토큰이 오면 꺼져 있어도 확인하고 g.user 에 담는다. 그래야 켜기 전에
#   "제대로 붙었나"를 미리 볼 수 있다.

인증_강제 = os.environ.get("TRACE_REQUIRE_AUTH", "0") == "1"


def 토큰_사용자(d):
    """Authorization: Bearer <token> 을 보고 사용자를 찾는다. 없으면 None."""
    머리 = request.headers.get("Authorization", "")
    if not 머리.startswith("Bearer "):
        return None
    t = d.get(db.Token, 머리[7:].strip())
    if not t:
        return None
    t.last_used_at = now().replace(tzinfo=None)
    return d.get(db.User, t.user_id)


def 로그인_필요(f):
    """★ 사람 화면용 주소(과제 목록·과제·/me)는 언제나 로그인이 필요하다 (10/7 · 배포 전)

    전엔 TRACE_REQUIRE_AUTH=1 일 때만 막아서, 로그인 없이도 과제 목록 → 과제(이름 추측 가능) → 세션 id
    → 기록(창 이름 포함)이 줄줄이 읽혔다. 인터넷에 올리면 누구나 학생 기록을 보게 된다.
    기록기가 쓰는 주소(세션·이벤트·봉인·맥락)는 여기 안 걸린다 — 기록기가 아직 토큰을 안 보내서.
    그쪽은 TRACE_REQUIRE_AUTH 로 나중에 막는다."""
    @functools.wraps(f)
    def 감싼것(*a, **kw):
        with db.Session() as d:
            u = 토큰_사용자(d)
            d.commit()
            g.user_id = u.id if u else None
            g.user_name = u.name if u else None
        if not g.user_id:
            return jsonify(error="unauthorized", message="로그인이 필요합니다"), 401
        return f(*a, **kw)
    return 감싼것


def _비번_맞음(해시, 비번):
    """한글 비밀번호는 맥·윈도우·브라우저에 따라 자모가 갈라져(NFD) 올 수 있다 → 그대로 · 붙인 꼴(NFC) · 가른 꼴(NFD) 다 본다.
    (10/12 이전 가입은 받은 그대로 저장됐으므로 그대로도 본다)"""
    return any(check_password_hash(해시, p) for p in
               dict.fromkeys((비번, unicodedata.normalize("NFC", 비번), unicodedata.normalize("NFD", 비번))))


@app.post("/api/auth/signup")
def signup():
    """★ 계약에 없던 것을 더했다 (9/21, A).
    로그인만 있으면 계정을 만들 방법이 없다. B 에게 알렸다."""
    b = request.get_json(force=True)
    이메일 = (b.get("email") or "").strip().lower()
    비번 = b.get("password") or ""
    if not 이메일 or len(비번) < 8:
        return jsonify(error="bad_request",
                       message="이메일과 8자 이상 비밀번호가 필요합니다"), 400
    with db.Session() as d:
        if d.query(db.User).filter(db.User.email == 이메일).first():
            return jsonify(error="conflict", message="이미 있는 이메일입니다"), 409
        u = db.User(id=str(uuid.uuid4()), email=이메일,
                    password_hash=generate_password_hash(unicodedata.normalize("NFC", 비번)),   # ★ 원문은 저장하지 않는다
                    name=b.get("name") or 이메일.split("@")[0],
                    created_at=now().replace(tzinfo=None))
        d.add(u)
        d.commit()
        결과 = {"id": u.id, "name": u.name}
    print(f"← signup {이메일}")
    return jsonify(id=결과["id"], name=결과["name"]), 201


@app.post("/api/auth/login")
def login():
    b = request.get_json(force=True)
    이메일 = (b.get("email") or "").strip().lower()
    with db.Session() as d:
        u = d.query(db.User).filter(db.User.email == 이메일).first()
        # ★ "이메일이 없다" 와 "비번이 틀렸다" 를 구분해서 알려주지 않는다.
        #   구분해 주면 어떤 이메일이 가입되어 있는지 알아낼 수 있다.
        #   대신 서버 기록(Render Logs)에만 남긴다 — 다른 서버에 로그인한 것인지 찾으려고 (10/12)
        if not u or not _비번_맞음(u.password_hash, b.get("password") or ""):
            print(f"← login 실패 {이메일} ({'이 서버에 없는 계정' if not u else '비밀번호 다름'})")
            return jsonify(error="unauthorized", message="이메일 또는 비밀번호가 맞지 않습니다"), 401
        t = db.Token(token=secrets.token_urlsafe(32), user_id=u.id,
                     device=(b.get("device") or "")[:100],
                     created_at=now().replace(tzinfo=None))
        d.add(t)
        d.commit()
        답 = {"token": t.token, "user": {"id": u.id, "name": u.name}}
    print(f"← login {이메일}")
    return jsonify(답)


@app.post("/api/auth/logout")
def logout():
    """이 기기 연결 끊기. 토큰 한 줄을 지운다."""
    머리 = request.headers.get("Authorization", "")
    if not 머리.startswith("Bearer "):
        return jsonify(error="bad_request", message="토큰이 없습니다"), 400
    with db.Session() as d:
        t = d.get(db.Token, 머리[7:].strip())
        if t:
            d.delete(t)
            d.commit()
    return jsonify(ok=True)


# ─────────────────────────── 구글 · 카카오 로그인 (10/15) ───────────────────────────
# PC 앱 [Google · 카카오로 계속하기] → 브라우저로 /api/auth/<p>/start?pc=<앱이 만든 무작위>&port=<앱 포트>   (p = google | kakao)
#   → 그 회사 로그인 · 계정 고르기 → /api/auth/<p>/callback (받은 code 를 그 회사 토큰 주소에서 바꿔 계정 번호 · 이메일 확인)
#   → 한 번 쓰는 표(2분)를 만들어 http://127.0.0.1:<port>/local/auth/<p>/done?ticket=…&state=<pc> 로 돌려보냄
#   → PC 앱이 state 가 자기가 만든 것인지 보고 POST /api/auth/<p>/claim 으로 표를 토큰으로 바꾼다
# ★ 앱 창(pywebview) 안에서는 구글이 로그인을 막는다(disallowed_useragent) → 늘 브라우저로 (카카오도 같게)
# ★ 서버는 아무것도 기억하지 않는다 — state 는 서명한 쪽지(10분 · 어느 회사인지까지) · 구글 PKCE 검증값도 state 로 다시 만든다
# ★ 돌려보내는 곳은 이 PC(127.0.0.1)뿐 — 다른 사이트로 보내는 데 쓰일 수 없다
# 잇기 (mode=link): 이미 로그인한 사람이 설정 › 계정에서 [Google · 카카오 계정 잇기] → 같은 길로 다녀오되 callback 은
#   로그인하지 않고 "잇기 표"(그 회사 계정 번호)만 만든다 → PC 앱이 자기 토큰과 함께 POST /api/auth/<p>/link 로 그 사람 계정에 붙인다.
#   ★ 누구에게 붙일지는 주소가 아니라 PC 앱의 토큰으로 정한다 — 주소가 새도 남의 계정에 내 구글 · 카카오를 붙일 수 없게
# 계정 고르기: 그 회사 계정 번호로 찾고 → 없으면 **확인된** 같은 이메일 계정에 붙이고 → 없으면 새로 만든다.
#   카카오는 이메일을 기본으로 안 준다(비즈 앱이어야 함) → 이메일 없이도 카카오 계정 번호로 계정을 만든다 (kakao-<번호>@kakao.trace · 화면엔 안 보임)
# 설정 (server/README.md "구글 · 카카오 로그인"): GOOGLE_CLIENT_ID · GOOGLE_CLIENT_SECRET · KAKAO_CLIENT_ID(REST API 키) · KAKAO_CLIENT_SECRET
#   돌아올 주소 = <서버>/api/auth/<p>/callback. 없으면 PC 앱에 그 버튼이 "준비 중" 그대로
구글_인증 = "https://accounts.google.com/o/oauth2/v2/auth"
구글_토큰 = "https://oauth2.googleapis.com/token"
카카오_인증 = "https://kauth.kakao.com/oauth/authorize"
카카오_토큰 = "https://kauth.kakao.com/oauth/token"
카카오_나 = "https://kapi.kakao.com/v2/user/me"
구글_비번 = "!google"                      # 구글로만 가입한 사람의 password_hash — 어떤 비밀번호와도 안 맞음 (werkzeug 가 False)
가짜_메일 = "@kakao.trace"                 # 이메일을 안 준 카카오 계정의 자리 채움 (보내지지 않는 주소 · /me 는 이메일 없음으로)
제공자 = {"google": {"이름": "Google", "로": "Google 로", "env": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"), "칸": "google_sub", "비번": 구글_비번},
         "kakao": {"이름": "카카오", "로": "카카오로", "env": ("KAKAO_CLIENT_ID", "KAKAO_CLIENT_SECRET"), "칸": "kakao_sub", "비번": "!kakao"}}


def _설정(p):
    i, s = (os.environ.get(k, "").strip() for k in 제공자[p]["env"])
    return (i, s) if i and s else None


def _구글_설정():
    return _설정("google")


def _비번_없음(u):
    """구글 · 카카오로만 가입해 비밀번호가 없는 계정 ("!google" · "!kakao")"""
    return (u.password_hash or "").startswith("!")


def _보이는_메일(u):
    return None if (u.email or "").endswith(가짜_메일) else u.email


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _쪽지(값, 비밀):
    본문 = _b64(json.dumps(값, separators=(",", ":")).encode())
    return 본문 + "." + hmac.new(비밀.encode(), 본문.encode(), hashlib.sha256).hexdigest()


def _쪽지_읽기(쪽지, 비밀):
    """서명이 맞고 시간이 안 지났으면 값 · 아니면 None"""
    본문, _, 서명 = (쪽지 or "").partition(".")
    if not 본문 or not hmac.compare_digest(서명, hmac.new(비밀.encode(), 본문.encode(), hashlib.sha256).hexdigest()):
        return None
    try:
        값 = json.loads(base64.urlsafe_b64decode(본문 + "=" * (-len(본문) % 4)))
    except ValueError:
        return None
    return 값 if isinstance(값, dict) and 값.get("exp", 0) >= time.time() else None


def _검증값(쪽지, 비밀):
    """PKCE code_verifier (구글) — 쪽지로 다시 만들 수 있게 (서버가 따로 기억하지 않음). 43자 [A-Za-z0-9_-]"""
    return _b64(hmac.new(비밀.encode(), ("pkce:" + 쪽지).encode(), hashlib.sha256).digest())


def _돌아올_곳(p):
    return request.host_url.rstrip("/") + f"/api/auth/{p}/callback"     # ProxyFix 로 https · Render 주소


def _안내(제목, 글, 코드=200):
    """브라우저에 뜨는 짧은 안내 화면 (구글 · 카카오 로그인 중간)"""
    return (f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(제목)} · Trace</title><style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:Pretendard,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;background:#f4f4f5;color:#18181b}}
.c{{background:#fff;border-radius:16px;padding:32px 28px;max-width:360px;margin:16px;box-shadow:0 0 0 1px rgba(24,24,27,.08)}}
h1{{font-size:20px;margin:0 0 8px}}p{{margin:0;font-size:14px;line-height:1.6;color:#52525b}}</style></head>
<body><div class="c"><h1>{html.escape(제목)}</h1><p>{html.escape(글)}</p></div></body></html>""",
            코드, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@app.get("/api/auth/providers")
def auth_providers():
    """PC 앱 로그인 화면이 어떤 버튼을 살릴지 (10/15)"""
    return jsonify(**{p: bool(_설정(p)) for p in 제공자})


@app.get("/api/auth/<p>/start")
def oauth_start(p):
    if p not in 제공자:
        return jsonify(error="not_found"), 404
    이름, 설정 = 제공자[p]["이름"], _설정(p)
    if not 설정:
        return _안내(f"{이름} 로그인을 아직 준비 중이에요", "Trace 앱에서 이메일로 로그인해 주세요.", 503)
    pc, port, mode = request.args.get("pc", ""), request.args.get("port", ""), request.args.get("mode", "login")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", pc) or not port.isdigit() or not 1024 <= int(port) <= 65535 \
            or mode not in ("login", "link"):
        return _안내("Trace 앱에서 시작해 주세요", f"Trace 앱 로그인 화면의 [{제공자[p]['로']} 계속하기] 를 눌러 주세요.", 400)
    쪽지 = _쪽지({"p": p, "pc": pc, "port": int(port), "mode": mode, "exp": int(time.time()) + 600}, 설정[1])
    if p == "kakao":
        return redirect(카카오_인증 + "?" + urlencode({"client_id": 설정[0], "redirect_uri": _돌아올_곳(p),
                                                     "response_type": "code", "state": 쪽지}))
    return redirect(구글_인증 + "?" + urlencode({
        "client_id": 설정[0], "redirect_uri": _돌아올_곳(p), "response_type": "code", "scope": "openid email profile",
        "state": 쪽지, "code_challenge": _b64(hashlib.sha256(_검증값(쪽지, 설정[1]).encode()).digest()),
        "code_challenge_method": "S256", "prompt": "select_account"}))


def _구글_코드_바꾸기(code, 검증값, 돌아올_곳, 설정):
    """구글 토큰 주소에서 code → id_token 의 내용 {sub, email, email_verified, name, …}.
    구글에서 TLS 로 바로 받은 id_token 이라 서명 대신 TLS 로 발급자를 믿는다 (OpenID Connect Core 3.1.3.7) — 받는 쪽 · 발급자 · 시간은 본다"""
    몸 = urlencode({"code": code, "client_id": 설정[0], "client_secret": 설정[1], "redirect_uri": 돌아올_곳,
                    "grant_type": "authorization_code", "code_verifier": 검증값}).encode()
    요청 = urllib.request.Request(구글_토큰, data=몸, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(요청, timeout=15) as r:
        답 = json.loads(r.read())
    본문 = 답["id_token"].split(".")[1]
    c = json.loads(base64.urlsafe_b64decode(본문 + "=" * (-len(본문) % 4)))
    if c.get("aud") != 설정[0] or c.get("iss") not in ("https://accounts.google.com", "accounts.google.com") \
            or c.get("exp", 0) < time.time():
        raise ValueError("id_token 의 받는 쪽 · 발급자 · 시간이 맞지 않음")
    return c


def _카카오_코드_바꾸기(code, 돌아올_곳, 설정):
    """카카오 토큰 주소에서 code → 접근 토큰 → 사용자 정보 → {sub, email, email_verified, name}.
    우리 REST 키 · 비밀로 카카오에서 TLS 로 바로 받은 토큰이라, 그 토큰으로 물은 사용자 정보는 우리 앱에 로그인한 그 사람이다.
    이메일은 동의 항목(비즈 앱)을 켰고 학생이 동의했을 때만 온다 — 유효하고 인증된 이메일만 확인된 것으로 본다"""
    머리 = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
    몸 = urlencode({"grant_type": "authorization_code", "client_id": 설정[0], "client_secret": 설정[1],
                    "redirect_uri": 돌아올_곳, "code": code}).encode()
    with urllib.request.urlopen(urllib.request.Request(카카오_토큰, data=몸, headers=머리), timeout=15) as r:
        토큰 = json.loads(r.read())["access_token"]
    with urllib.request.urlopen(urllib.request.Request(카카오_나, headers={**머리, "Authorization": f"Bearer {토큰}"}), timeout=15) as r:
        나 = json.loads(r.read())
    계정 = 나.get("kakao_account") or {}
    return {"sub": str(나["id"]), "email": 계정.get("email"),
            "email_verified": bool(계정.get("is_email_valid") and 계정.get("is_email_verified")),
            "name": (계정.get("profile") or {}).get("nickname") or (나.get("properties") or {}).get("nickname")}


def _외부_사용자(d, p, c):
    """그 회사 계정 번호로 찾고 → 없으면 확인된 같은 이메일 계정에 붙이고 → 없으면 새로 만든다.
    같은 이메일 계정에 이미 다른 그 회사 계정이 붙어 있으면 None"""
    칸 = 제공자[p]["칸"]
    sub = str(c["sub"])
    u = d.query(db.User).filter(getattr(db.User, 칸) == sub).first()
    if u:
        return u
    이메일 = str(c.get("email") or "").strip().lower()
    확인됨 = bool(이메일) and c.get("email_verified") in (True, "true")
    if 확인됨:
        u = d.query(db.User).filter(db.User.email == 이메일).first()
        if u:                                           # 이메일로 먼저 가입한 사람 — 그 회사가 이메일 주인임을 확인했으니 같은 계정으로
            if getattr(u, 칸) and getattr(u, 칸) != sub:
                return None
            setattr(u, 칸, sub)
            return u
    else:                                               # 이메일을 안 줬거나 확인 안 됨 — 그 이메일로 남의 계정에 붙거나 자리를 차지하지 않게
        이메일 = f"{p}-{sub}{가짜_메일}"
    u = db.User(id=str(uuid.uuid4()), email=이메일, password_hash=제공자[p]["비번"], **{칸: sub},
                name=(str(c.get("name") or "").strip() or (이메일.split("@")[0] if 확인됨 else "카카오 사용자"))[:40],
                created_at=now().replace(tzinfo=None))
    d.add(u)
    return u


@app.get("/api/auth/<p>/callback")
def oauth_callback(p):
    if p not in 제공자:
        return jsonify(error="not_found"), 404
    이름, 설정 = 제공자[p]["이름"], _설정(p)
    쪽지 = request.args.get("state", "")
    st = _쪽지_읽기(쪽지, 설정[1]) if 설정 else None
    if not st or st.get("p", "google") != p:
        return _안내("다시 시도해 주세요", f"로그인 시간이 지났거나 잘못된 주소예요. Trace 앱에서 [{제공자[p]['로']} 계속하기] 를 다시 눌러 주세요.", 400)
    if request.args.get("error") or not request.args.get("code"):
        return _안내(f"{이름} 로그인을 취소했어요", "Trace 앱으로 돌아가 다시 시도할 수 있어요.", 400)
    try:
        c = (_구글_코드_바꾸기(request.args["code"], _검증값(쪽지, 설정[1]), _돌아올_곳(p), 설정) if p == "google"
             else _카카오_코드_바꾸기(request.args["code"], _돌아올_곳(p), 설정))
    except Exception as e:                                  # noqa: BLE001
        왜 = _회사_오류(e)
        print(f"← {이름} 로그인 실패 ({왜})")
        traceback.print_exc()
        return _안내(f"{이름}에서 확인하지 못했어요", f"잠시 뒤 Trace 앱에서 다시 시도해 주세요. (까닭: {왜})", 502)
    try:
        return _로그인_마무리(p, 이름, st, c)
    except Exception as e:                                  # noqa: BLE001  (10/15 처음 카카오 시험에서 까닭 없이 500 — 기록을 남긴다)
        print(f"← {이름} 로그인 마무리 실패 ({type(e).__name__}: {str(e)[:200]})")
        traceback.print_exc()
        return _안내("로그인을 마치지 못했어요", f"서버에서 막혔어요 ({type(e).__name__}). 잠시 뒤 다시 시도하고, 계속되면 이 화면을 알려 주세요.", 500)


def _회사_오류(e):
    """구글 · 카카오가 돌려준 오류의 까닭 — 화면 · 서버 기록용 (비밀은 안 들어 있음: 오류 코드 · 설명만)"""
    if isinstance(e, urllib.error.HTTPError):
        try:
            몸 = json.loads(e.read().decode("utf-8", "replace") or "{}")
        except ValueError:
            몸 = {}
        코드 = 몸.get("error_code") or 몸.get("error") or ""
        설명 = 몸.get("error_description") or 몸.get("msg") or ""
        return f"HTTP {e.code} {코드} {설명}".strip()[:160]
    return f"{type(e).__name__}: {str(e)[:120]}"


def _로그인_마무리(p, 이름, st, c):
    if not c.get("sub") or (p == "google" and (not c.get("email") or c.get("email_verified") not in (True, "true"))):
        return _안내(f"확인된 이메일이 없는 {이름} 계정이에요", f"다른 {이름} 계정을 고르거나 Trace 앱에서 이메일로 가입해 주세요.", 400)
    with db.Session() as d:
        옛날 = now().replace(tzinfo=None) - timedelta(minutes=10)
        d.query(db.LoginTicket).filter(db.LoginTicket.created_at < 옛날).delete()
        표 = secrets.token_urlsafe(32)
        if st.get("mode") == "link":                       # 잇기 — 아무도 로그인시키지 않고 그 회사 계정 번호만 담아 둔다
            d.add(db.LoginTicket(ticket=표, kind="link", provider=p, sub=str(c["sub"]), created_at=now().replace(tzinfo=None)))
            d.commit()
        else:
            u = _외부_사용자(d, p, c)
            if not u:
                return _안내(f"이미 다른 {이름} 계정과 이어진 이메일이에요",
                            f"처음 이은 {이름} 계정으로 로그인하거나 이메일 · 비밀번호로 로그인해 주세요.", 409)
            d.add(db.LoginTicket(ticket=표, kind="login", provider=p, user_id=u.id, created_at=now().replace(tzinfo=None)))
            d.commit()
            print(f"← {이름} 로그인 {u.id[:8]}…")
    return redirect(f"http://127.0.0.1:{st['port']}/local/auth/{p}/done?" + urlencode({"ticket": 표, "state": st["pc"]}))


@app.post("/api/auth/<p>/claim")
def oauth_claim(p):
    """PC 앱이 한 번 쓰는 표를 토큰으로 바꾼다 (2분 · 한 번만) — /auth/login 과 같은 답"""
    if p not in 제공자:
        return jsonify(error="not_found"), 404
    b = request.get_json(force=True, silent=True) or {}
    표 = str(b.get("ticket") or "")
    with db.Session() as d:
        t = d.get(db.LoginTicket, 표) if 표 else None
        if t:
            d.delete(t)                                     # 맞든 늦었든 한 번 쓰면 끝
        if not t or (t.kind or "login") != "login" or (now().replace(tzinfo=None) - t.created_at).total_seconds() > 120:
            d.commit()
            return jsonify(error="unauthorized", message=f"로그인 시간이 지났어요. [{제공자[p]['로']} 계속하기] 를 다시 눌러 주세요"), 401
        u = d.get(db.User, t.user_id)
        tok = db.Token(token=secrets.token_urlsafe(32), user_id=u.id, device=str(b.get("device") or "")[:100],
                       created_at=now().replace(tzinfo=None))
        d.add(tok)
        d.commit()
        답 = {"token": tok.token, "user": {"id": u.id, "name": u.name}}
    return jsonify(답)


@app.post("/api/auth/<p>/link")
@로그인_필요
def oauth_link(p):
    """설정 › 계정 › [Google · 카카오 계정 잇기] — 잇기 표(2분 · 한 번)의 그 회사 계정을 지금 로그인한 계정에 붙인다 (10/15).
    그 회사 계정이 이미 다른 Trace 계정에 붙어 있으면: 비밀번호 없이 만든 빈 계정(과제 없음)이면 거기서 떼어 옮기고, 아니면 거절"""
    if p not in 제공자:
        return jsonify(error="not_found"), 404
    이름, 칸 = 제공자[p]["이름"], 제공자[p]["칸"]
    표 = str((request.get_json(force=True, silent=True) or {}).get("ticket") or "")
    with db.Session() as d:
        t = d.get(db.LoginTicket, 표) if 표 else None
        if t:
            d.delete(t)
        if not t or t.kind != "link" or (t.provider or "google") != p \
                or (now().replace(tzinfo=None) - t.created_at).total_seconds() > 120:
            d.commit()
            return jsonify(error="expired", message=f"시간이 지났어요. [{이름} 계정 잇기] 를 다시 눌러 주세요"), 400
        sub = t.sub or t.google_sub                      # (10/15 처음 잇기 표는 google_sub 칸에 담았다)
        u = d.get(db.User, g.user_id)
        다른 = d.query(db.User).filter(getattr(db.User, 칸) == sub, db.User.id != u.id).first()
        if 다른:
            과제 = d.query(db.Work).filter(db.Work.user_id == 다른.id, db.Work.deleted_at.is_(None)).count()
            if not _비번_없음(다른) or 과제:
                d.commit()
                return jsonify(error="conflict", message=f"이 {이름} 계정은 기록이 있는 다른 Trace 계정에 이어져 있어요. "
                                                         "그 계정으로 로그인해 주세요"), 409
            setattr(다른, 칸, None)                       # 비밀번호 없이 만든 빈 계정 — 연결만 떼어 옮긴다 (계정은 지우지 않음)
            if not (다른.google_sub or 다른.kakao_sub):     # 로그인할 길이 없어졌으면 그 계정 로그인도 끊음
                d.query(db.Token).filter(db.Token.user_id == 다른.id).delete()
            print(f"← {이름} 연결 옮김 {다른.id[:8]}… → {u.id[:8]}… (빈 계정에서)")
        setattr(u, 칸, sub)
        d.commit()
    print(f"← {이름} 계정 이음 {g.user_id[:8]}…")
    return jsonify(**{p: True})


@app.post("/api/auth/<p>/unlink")
@로그인_필요
def oauth_unlink(p):
    """연결 끊기 — 끊어도 로그인할 길(비밀번호 · 다른 회사 계정)이 남을 때만"""
    if p not in 제공자:
        return jsonify(error="not_found"), 404
    with db.Session() as d:
        u = d.get(db.User, g.user_id)
        남는길 = not _비번_없음(u) or any(getattr(u, 제공자[q]["칸"]) for q in 제공자 if q != p)
        if not 남는길:
            return jsonify(error="no_password", message=f"비밀번호 없이 {제공자[p]['로']}만 로그인하는 계정이라 끊을 수 없어요"), 400
        setattr(u, 제공자[p]["칸"], None)
        d.commit()
    return jsonify(**{p: False})


@app.get("/api/me")
@로그인_필요
def me():
    if not g.user_id:
        return jsonify(error="unauthorized", message="로그인이 필요합니다"), 401
    with db.Session() as d:
        works = d.query(db.Work).filter(db.Work.user_id == g.user_id, db.Work.deleted_at.is_(None)).all()
        u = d.get(db.User, g.user_id)
        답 = {"id": g.user_id, "name": g.user_name, "email": _보이는_메일(u) if u else None,     # 이메일은 설정 › 계정에 보임 (10/13 · 카카오가 안 준 것은 없음)
              "password": bool(u and not _비번_없음(u)),                                  # 로그인 방법 (10/15)
              "google": bool(u and u.google_sub), "kakao": bool(u and u.kakao_sub),
              "works": [{"id": w.id, "title": w.title, "ai_scope": w.ai_scope} for w in works]}
    return jsonify(답)


@app.patch("/api/me")
@로그인_필요
def update_me():
    """설정 › 계정 › 이름 고치기 (10/13 박상진) — 이름은 내역서 맨 위에 나온다. 이미 낸 내역서는 그때 이름 그대로"""
    이름 = ((request.get_json(force=True, silent=True) or {}).get("name") or "").strip()
    if not 이름 or len(이름) > 40:
        return jsonify(error="bad_request", message="이름은 1~40자로 넣어 주세요"), 400
    with db.Session() as d:
        u = d.get(db.User, g.user_id)
        u.name = 이름
        d.commit()
    return jsonify(id=g.user_id, name=이름)


@app.post("/api/auth/password")
@로그인_필요
def change_password():
    """설정 › 계정 › 비밀번호 바꾸기 (10/13 박상진) — 지금 비밀번호를 맞혀야 바뀜 · 바꾸면 이 기기 말고 다른 기기는 로그아웃"""
    b = request.get_json(force=True, silent=True) or {}
    새것 = b.get("new_password") or ""
    if len(새것) < 8:
        return jsonify(error="bad_request", message="새 비밀번호는 8자 이상이어야 합니다"), 400
    지금토큰 = request.headers.get("Authorization", "")[7:].strip()
    with db.Session() as d:
        u = d.get(db.User, g.user_id)
        if not _비번_맞음(u.password_hash, b.get("password") or ""):
            return jsonify(error="unauthorized", message="지금 비밀번호가 맞지 않습니다"), 401
        u.password_hash = generate_password_hash(unicodedata.normalize("NFC", 새것))   # ★ 원문은 저장하지 않는다
        d.query(db.Token).filter(db.Token.user_id == u.id, db.Token.token != 지금토큰).delete()
        d.commit()
    print(f"← 비밀번호 바꿈 {g.user_id[:8]}…")
    return jsonify(ok=True)


# ─────────────────────────── Work (계약 2절) ───────────────────────────
@app.post("/api/works")
@로그인_필요
def create_work():
    b = request.get_json(force=True)
    범위 = b.get("ai_scope")                      # 교수가 허용한 범위 메모 (선택). 서버는 이걸로 판단하지 않는다
    if 범위 is not None and not isinstance(범위, str):
        return jsonify(error="bad_request", message="ai_scope 는 글자(메모)여야 합니다"), 400
    with db.Session() as d:
        w = db.Work(id=b.get("id") or str(uuid.uuid4()), user_id=g.user_id,
                    title=b.get("title") or "제목 없음", ai_scope=범위,
                    created_at=now().replace(tzinfo=None))
        d.add(w)
        d.commit()
        답 = {"id": w.id, "title": w.title, "ai_scope": w.ai_scope,
              "created_at": w.created_at.isoformat(timespec="seconds")}
    print(f"← work 만듦 {답['id'][:8]}…  {답['title']}")
    return jsonify(답), 201


@app.get("/api/works")
@로그인_필요
def list_works():
    with db.Session() as d:
        q = d.query(db.Work).filter(db.Work.user_id == g.user_id, db.Work.deleted_at.is_(None))
        목록 = []
        for w in q.all():
            세션들 = d.query(db.Sess).filter(db.Sess.work_id == w.id, db.Sess.deleted_at.is_(None)).all()
            마지막 = max((s.started_at for s in 세션들 if s.started_at), default=None)
            목록.append({"id": w.id, "title": w.title, "ai_scope": w.ai_scope,
                         "sessions": len(세션들), "last_at": 마지막})
    return jsonify(목록)


@app.get("/api/works/<wid>")
@로그인_필요
def get_work(wid):
    with db.Session() as d:
        w = d.get(db.Work, wid)
        if not w or w.user_id != g.user_id or w.deleted_at:   # 주인 없는 과제·지운 과제도 404 (10/8 · 10/10)
            return jsonify(error="not_found"), 404
        세션들 = []
        for s in d.query(db.Sess).filter(db.Sess.work_id == wid, db.Sess.deleted_at.is_(None)).all():
            n = d.query(db.Event).filter(db.Event.session_id == s.id).count()
            세션들.append({"id": s.id, "start": s.started_at, "end": s.ended_at,
                           "dur": None, "events": n, "sealed": bool(s.sealed_at)})
        답 = {"id": w.id, "title": w.title, "ai_scope": w.ai_scope, "sessions": 세션들}
    return jsonify(답)


@app.patch("/api/works/<wid>")
@로그인_필요
def update_work(wid):
    """제목·허용 범위 메모 고치기 — 내역서를 내기 직전에 고칠 수 있어야 한다 (계약 2절)."""
    b = request.get_json(force=True)
    if "ai_scope" in b and b["ai_scope"] is not None and not isinstance(b["ai_scope"], str):
        return jsonify(error="bad_request", message="ai_scope 는 글자(메모)여야 합니다"), 400
    with db.Session() as d:
        w = d.get(db.Work, wid)
        if not w or w.user_id != g.user_id or w.deleted_at:
            return jsonify(error="not_found"), 404
        if "title" in b:
            w.title = b["title"] or "제목 없음"
        if "ai_scope" in b:
            w.ai_scope = b["ai_scope"]
        d.commit()
        답 = {"id": w.id, "title": w.title, "ai_scope": w.ai_scope}
    return jsonify(답)


# ─────────────────────────── 지우기 · 옮기기 (10/10 박상진 요청) ───────────────────────────
#
# ★ "확인값은 지우고, 지운 사실과 시각만 남긴다" ★
#   이벤트(해시·창 이름)·원문·연결은 지운다. 과제·기록의 줄은 남겨 deleted_at 을 찍는다 — 그래야
#   ① 이미 낸 PDF 의 QR 을 열면 404 대신 "학생이 10/12 에 지운 기록입니다" 를 보여 줄 수 있고
#   ② 기록기가 지운 기록에 계속 보내도 되살아나지 않는다 (410).

def _기록_비우기(d, sid):
    """기록 하나의 내용(이벤트·배치·맥락·그 기록에서 온 내역서 원문)을 지운다. 줄은 남긴다."""
    for 표 in (db.Event, db.Batch, db.Context):
        d.query(표).filter(표.session_id == sid).delete(synchronize_session=False)
    d.query(db.Message).filter(db.Message.session_id == sid).delete(synchronize_session=False)
    d.query(db.Redaction).filter(db.Redaction.session_id == sid).delete(synchronize_session=False)
    s = d.get(db.Sess, sid)
    s.deleted_at = s.deleted_at or iso()
    s.root = s.head = s.device_id = None


def _내_기록(d, sid):
    """로그인한 사람의 과제에 든 기록만 (지운 과제·지운 기록 제외)."""
    s = d.get(db.Sess, sid)
    if not s or s.deleted_at:
        return None
    return s if 내_과제(d, s.work_id) else None


@app.delete("/api/works/<wid>")
@로그인_필요
def delete_work(wid):
    """과제 지우기 — 기록·내역서 내용을 지우고, 과제 줄엔 지운 시각만. 공유 링크는 "지운 기록입니다" 로 바뀐다."""
    with db.Session() as d:
        w = 내_과제(d, wid)
        if not w:
            return jsonify(error="not_found"), 404
        세션 = d.query(db.Sess).filter(db.Sess.work_id == wid).all()
        for s in 세션:
            _기록_비우기(d, s.id)
        for st in d.query(db.Statement).filter(db.Statement.work_id == wid).all():
            for 표 in (db.Message, db.Link, db.Redaction):
                d.query(표).filter(표.statement_id == st.id).delete(synchronize_session=False)
            st.sentence = st.ai_scope = None
            st.problems, st.summary, st.source = None, None, None
        w.title, w.ai_scope, w.deleted_at = None, None, iso()
        d.commit()
        답 = {"id": wid, "deleted_at": w.deleted_at, "sessions": len(세션)}
    print(f"← 과제 지움 {wid}  기록 {답['sessions']}개")
    return jsonify(답)


@app.delete("/api/sessions/<sid>")
@로그인_필요
def delete_session(sid):
    """기록 하나 지우기 — 내역서의 투명성 줄에 "지운 기록 n개" 로 남는다 (언제 기록이었는지 시각은 남음)."""
    with db.Session() as d:
        s = _내_기록(d, sid)
        if not s:
            return jsonify(error="not_found"), 404
        _기록_비우기(d, sid)
        d.commit()
        답 = {"id": sid, "deleted_at": s.deleted_at}
    print(f"← 기록 지움 {sid[:8]}…")
    return jsonify(답)


@app.patch("/api/sessions/<sid>")
@로그인_필요
def move_session(sid):
    """기록 옮기기 — 다른 과제를 고른 채 켰을 때. 체인·확인값은 그대로 따라간다
    (과제 id 는 체인 요약에 들어가지 않아서 "서버 기록과 일치" 가 유지된다 · core/chain.py)."""
    b = request.get_json(force=True, silent=True) or {}
    with db.Session() as d:
        s = _내_기록(d, sid)
        if not s:
            return jsonify(error="not_found"), 404
        if not isinstance(b.get("work_id"), str) or not 내_과제(d, b["work_id"]):
            return jsonify(error="bad_request", message="옮길 곳은 내 과제여야 합니다"), 400
        전, s.work_id = s.work_id, b["work_id"]
        d.commit()
        답 = {"id": sid, "work_id": s.work_id, "from": 전}
    print(f"← 기록 옮김 {sid[:8]}…  {전} → {답['work_id']}")
    return jsonify(답)


# ─────────────────────────── 계약 0 · 확인용 ───────────────────────────
@app.get("/api/health")
def health():
    with db.Session() as s:
        return jsonify(ok=True, sessions=s.query(db.Sess).count(), storage="db",
                       auth="required" if 인증_강제 else "optional")


# ─────────────────────────── 계약 3 · 세션 ───────────────────────────
@app.post("/api/works/<work>/sessions")
def create_session(work):
    b = request.get_json(force=True)
    with db.Session() as d:
        w0 = d.get(db.Work, work)
        if w0 is not None and w0.deleted_at:
            return jsonify(error="gone", message="학생이 지운 과제입니다"), 410
        s0 = d.get(db.Sess, b.get("id"))
        if s0 is not None and s0.deleted_at:
            return jsonify(error="gone", message="학생이 지운 기록입니다"), 410
        if w0 is None:
            # ★ 기록기는 과제를 따로 만들지 않고 config 의 work_id 로 바로 세션을 보낸다.
            #   SQLite 는 없는 과제를 가리키는 세션도 받아 주지만, PostgreSQL(Supabase) 은 외래키로 거절한다 (500).
            #   → 없으면 여기서 만들어 둔다. 토큰이 왔으면 그 사람 과제로. (10/4 Supabase 로 옮기다 발견)
            주인 = 토큰_사용자(d)
            d.add(db.Work(id=work, user_id=주인.id if 주인 else None, title=work,
                          created_at=now().replace(tzinfo=None)))
            d.flush()
        s = 세션_가져오기(d, b["id"], create=True)
        existed = s.work_id is not None              # 전에는 mode 로 판단했다. 이제 mode 가 없으니 work_id 로
        장치 = b.get("device") or {}
        s.work_id = work                             # 요청에 mode 가 와도 무시한다 (기록기가 아직 보낼 수 있음)
        s.device_id = 장치.get("name")
        s.started_at = b.get("started_at")
        d.commit()
    print(f"← session {b['id'][:8]}…  work={work}  {'(이미 있음)' if existed else ''}")
    return jsonify(id=b["id"], work_id=work,
                   started_at=b.get("started_at")), 200 if existed else 201


@app.post("/api/sessions/<sid>/events")
def events(sid):
    b = request.get_json(force=True)
    받은시각 = now()
    with db.Session() as d:
        s = 세션_가져오기(d, sid, create=True)
        if s.deleted_at:                      # 지운 기록에 기록기가 계속 보내면 받지 않는다 (지운 걸 되살리지 않게)
            return jsonify(error="gone", message="학생이 지운 기록입니다"), 410
        기존 = {r.id for r in d.query(db.Event.id).filter(db.Event.session_id == sid).all()}
        seq = s.chain_len or 0
        저장, 중복, 지연 = 0, 0, 0
        마지막id = None

        for e in b.get("events", []):
            if e["id"] in 기존:                   # 멱등 — 오프라인 큐 재전송은 정상이다
                중복 += 1
                continue
            기존.add(e["id"])

            if e["type"] == "heartbeat":          # 저장 안 함 — 마지막 시각만 (계약 3절)
                s.last_heartbeat_at = e["ts"]
                continue

            s.head = C.next_hash(s.head, e)       # ★ 서버가 같은 함수로 재계산
            s.chain_len = (s.chain_len or 0) + 1
            seq += 1
            if e.get("h") and e["h"] != s.head:
                s.integrity_ok = False

            d.add(db.Event(session_id=sid, id=e["id"], seq=seq, ts=e["ts"], type=e["type"],
                           payload=e, h=e.get("h"), server_h=s.head,
                           received_at=받은시각.isoformat(timespec="seconds")))
            저장 += 1
            마지막id = e["id"]

            try:
                if (받은시각 - datetime.fromisoformat(e["ts"])).total_seconds() > LATE_SEC:
                    지연 += 1
            except ValueError:
                pass

        verified = (b.get("chain_head") == s.head) and bool(s.integrity_ok)
        if b.get("chain_head") and not verified:
            s.integrity_ok = False

        d.add(db.Batch(session_id=sid, chain_head=b.get("chain_head"), chain_len=b.get("chain_len"),
                       n=저장, late=지연, verified=verified,
                       received_at=받은시각.isoformat(timespec="seconds")))
        머리 = s.head
        d.commit()

    print(f"← batch {len(b.get('events', []))}건 (저장 {저장}, 중복 {중복}, 지연 {지연})  "
          f"head {머리[:8]}… {'일치' if verified else '불일치 ⚠'}")
    return jsonify(accepted=저장, duplicates=중복, last_id=마지막id,
                   verified=verified, server_head=머리,
                   received_at=받은시각.isoformat(timespec="seconds"))


@app.post("/api/sessions/<sid>/end")
def end(sid):
    b = request.get_json(force=True)
    with db.Session() as d:
        s = 세션_가져오기(d, sid)
        if not s:
            return jsonify(error="not_found"), 404
        if s.deleted_at:
            return jsonify(error="gone", message="학생이 지운 기록입니다"), 410

        rows, root = C.build(이벤트들(d, sid))       # ★ 전체를 처음부터 다시 계산
        verified = (root == b.get("root")) and bool(s.integrity_ok)
        늦은배치 = d.query(db.Batch).filter(db.Batch.session_id == sid, db.Batch.late > 0).count()

        s.ended_at = b.get("ended_at")
        s.sealed_at = iso()
        s.root, s.verified = root, verified
        s.anchor_status, s.anchor_submitted_at = "pending", iso()
        봉인 = {"ended_at": s.ended_at, "sealed_at": s.sealed_at, "root": root,
                "verified": verified, "late_batches": 늦은배치,
                "anchor": {"status": "pending", "provider": "opentimestamps",
                           "submitted_at": s.anchor_submitted_at}}
        d.commit()

    print(f"← end  chain {len(rows)}건  root {root[:12]}…  "
          f"{'검증됨' if verified else '불일치 ⚠ (client ' + str(b.get('root',''))[:12] + '…)'}  지연 배치 {늦은배치}")
    if not verified:
        return jsonify(error="chain_mismatch", server_root=root,
                       client_root=b.get("root"), **봉인), 409
    return jsonify(id=sid, **봉인)


@app.get("/api/sessions/<sid>")
def get_session(sid):
    with db.Session() as d:
        s = 세션_가져오기(d, sid)
        evs = 이벤트들(d, sid) if s else []
        if not s or not evs:
            return jsonify(error="not_found"), 404
        늦은배치 = d.query(db.Batch).filter(db.Batch.session_id == sid, db.Batch.late > 0).count()
        out = derive(evs)                            # ★ B 의 함수 그대로
        out.update({"work_id": s.work_id, "sealed_at": s.sealed_at,
                    "anchor": s.anchor_status or "none",
                    "integrity_ok": bool(s.integrity_ok), "late_batches": 늦은배치})
    return jsonify(out)


@app.get("/api/sessions/<sid>/events")
def get_events(sid):
    after, limit = request.args.get("after"), int(request.args.get("limit", 500))
    with db.Session() as d:
        if not 세션_가져오기(d, sid):
            return jsonify(error="not_found"), 404
        evs = 이벤트들(d, sid)
    if after:
        idx = next((i for i, e in enumerate(evs) if e["id"] == after), -1)
        evs = evs[idx + 1:]
    page = evs[:limit]
    return jsonify(events=page, next=page[-1]["id"] if len(evs) > limit else None)


# ─────────────────────────── 계약 4 · AI 대화 기록 ───────────────────────────
# 9/28 개정: 모드가 없어져 모든 세션에서 받는다 (전에는 Learn 세션만, Proof 면 403).
# Learn 의 리포트(/report)·Side Chat(/chat) 은 기능째 없어졌다.
항목_최대 = 64 * 1024          # 한 항목 글자 64KB (계약 4절)
요청_최대 = 1024 * 1024        # 한 요청 1MB


@app.post("/api/sessions/<sid>/context")
def context(sid):
    if (request.content_length or 0) > 요청_최대:
        return jsonify(error="too_large", message="한 요청은 1MB 까지입니다"), 413
    b = request.get_json(force=True)
    항목들 = b.get("items", [])
    for it in 항목들:
        if len((it.get("text") or "").encode("utf-8")) > 항목_최대:
            return jsonify(error="too_large", message=f"한 항목은 64KB 까지입니다 ({it.get('kind')})"), 413
    with db.Session() as d:
        s = 세션_가져오기(d, sid)
        if not s:
            return jsonify(error="not_found"), 404
        if s.deleted_at:
            return jsonify(error="gone", message="학생이 지운 기록입니다"), 410
        for it in 항목들:
            d.add(db.Context(id=it.get("id") or str(uuid.uuid4()), session_id=sid,
                             ts=it.get("ts"), source=it.get("source"), kind=it.get("kind"),
                             text=it.get("text") or "", meta=it.get("meta") or {}))   # 500자로 자르던 것 없앰
        d.commit()
    print(f"← context {len(항목들)}건")
    return jsonify(accepted=len(항목들))


@app.get("/api/sessions/<sid>/context")
def get_context(sid):
    with db.Session() as d:
        if not 세션_가져오기(d, sid):
            return jsonify(error="not_found"), 404
        항목 = [{"id": c.id, "ts": c.ts, "source": c.source, "kind": c.kind,
                 "text": c.text, "meta": c.meta or {}}
                for c in (d.query(db.Context)
                          .filter(db.Context.session_id == sid)
                          .order_by(db.Context.ts).all())]
    return jsonify(items=항목)


# ─────────────────────────── 10 · AI 활용 내역서 ───────────────────────────
#
# ★ "원문은 늦게 와도, 기록 당시 그대로인지 확인된다" (docs/api.md 10-1) ★
#   기록하는 동안 서버엔 해시만 왔다 (ai_msg.hash). 학생이 "내역서 만들기"를 누르면 고른 원문이 처음 온다.
#   서버는 sha256_text(원문) 을 체인 이벤트의 hash 와 비교한다. 같으면 그때 그 글, 다르면 나중에 바꾼 글.
#   다른 것도 버리지 않고 저장해 "조작됨"으로 보여 준다 — 숨기면 내역서를 믿을 이유가 없어진다.
#
#   도구·역할·시각은 학생이 보낸 값을 쓰지 않고 체인 이벤트의 값을 쓴다 (PC 가 보낸 숫자를 믿지 않음).

내역서_최대 = 5 * 1024 * 1024       # 한 요청 5MB (보낸 크기 — PC 앱은 큰 내역서를 gzip 으로 줄여 보낸다 · 10/14)
풀린_최대 = 40 * 1024 * 1024        # 줄인 것을 푼 크기 (AI 를 아주 많이 쓴 100쪽 ≈ 9MB · 지나치게 부푸는 파일 막기)
원문_최대 = 256 * 1024              # 원문 한 개 256KB (긴 AI 답)
설명_최대 = 150                     # 내역서 v3 질문 두 칸 (10/10 박상진)
공유_기본일, 공유_최대일 = 14, 90


def 내_과제(d, wid):
    """로그인한 사람의 과제만. 주인이 없는 과제(기록기가 로그인 없이 만든 것)도 거절한다 —
    과제 이름(W-1007 같은)은 추측할 수 있어서, 누구나 남의 기록으로 내역서를 만들 수 있게 되므로."""
    w = d.get(db.Work, wid)
    if not w or w.user_id != g.user_id or w.deleted_at:
        return None
    return w


def _쌍(x, 이름):
    """{session_id, event_id} 를 꺼낸다. 이벤트 id 는 세션 안에서만 고유하다 (events 기본키와 같은 이유)."""
    if not isinstance(x, dict) or not x.get("session_id") or not x.get("event_id"):
        raise ValueError(f"{이름} 마다 session_id 와 event_id 가 필요합니다")
    return str(x["session_id"]), str(x["event_id"])


가림_종류 = {"API키", "비밀키", "주민번호", "카드번호", "이메일", "전화번호", "직접"}


def _가릴자리(m):
    """학생이 원문 일부만 가린 메시지 — mask: [[시작, 끝, 종류], …] (collector/mask.py 와 같은 종류).
    서버는 원문 전체로 체인 해시를 맞춰 본 뒤, 가린 글(⟦가림:종류⟧)만 저장한다. 원문은 남기지 않는다 (10/12)"""
    칸 = m.get("mask")
    if 칸 is None:
        return []
    n = len(m.get("text") or "")
    if not (isinstance(칸, list) and len(칸) <= 50 and all(
            isinstance(x, list) and len(x) == 3 and all(isinstance(v, int) and not isinstance(v, bool) for v in x[:2])
            and 0 <= x[0] < x[1] <= n and x[2] in 가림_종류 for x in 칸)):
        raise ValueError("mask 는 [[시작, 끝, 종류], …] 여야 합니다 (종류: " + " · ".join(sorted(가림_종류)) + ")")
    칸 = sorted(칸)
    if any(a[1] > b[0] for a, b in zip(칸, 칸[1:])):
        raise ValueError("mask 의 자리가 겹칩니다")
    return 칸


def _가린글(text, 칸):
    for s, e, 종류 in sorted(칸, reverse=True):
        text = text[:s] + f"⟦가림:{종류}⟧" + text[e:]
    return text


def _과제_요약(d, wid):
    """과제의 세션 전부를 체인 이벤트로 센다 (core/summary.py). PC 가 보낸 숫자는 쓰지 않는다."""
    세션들 = d.query(db.Sess).filter(db.Sess.work_id == wid).all()
    return work_summary([({"id": s.id, "sealed": bool(s.sealed_at), "deleted_at": s.deleted_at,
                           "started_at": s.started_at, "ended_at": s.ended_at,
                           "verified": bool(s.verified) and bool(s.integrity_ok)},
                          [] if s.deleted_at else 이벤트들(d, s.id))
                         for s in 세션들])


@app.get("/api/works/<wid>/summary")
@로그인_필요
def summary(wid):
    """내역서 맨 위 숫자. 작업 시간 · 입력 · 붙여넣기(출처 기록 없음 포함) · AI 질문·답 · 연결. 비율·점수는 없다."""
    with db.Session() as d:
        if not 내_과제(d, wid):
            return jsonify(error="not_found"), 404
        답 = _과제_요약(d, wid)
    return jsonify(work_id=wid, **답)


@app.post("/api/works/<wid>/statements")
@로그인_필요
def create_statement(wid):
    if (request.content_length or 0) > 내역서_최대:
        return jsonify(error="too_large", message="한 요청은 5MB 까지입니다"), 413
    try:
        b = _몸통_json()
    except OverflowError:
        return jsonify(error="too_large", message="내역서가 너무 큽니다 (풀어서 40MB 까지)"), 413
    if not isinstance(b, dict):
        return jsonify(error="bad_request", message="JSON 이 필요합니다"), 400
    메시지들, 연결들, 가림들 = b.get("messages") or [], b.get("links") or [], b.get("redactions") or []
    if not all(isinstance(v, list) for v in (메시지들, 연결들, 가림들)):
        return jsonify(error="bad_request", message="messages · links · redactions 는 목록이어야 합니다"), 400
    for 이름 in ("ai_scope", "sentence", "explain_use", "explain_check"):
        if b.get(이름) is not None and not isinstance(b[이름], str):
            return jsonify(error="bad_request", message=f"{이름} 는 글자여야 합니다"), 400
    출처 = b.get("source")                                     # 교수 링크 출처 보기 (학생이 켰을 때만 · 10/12)
    if 출처 is not None and not (isinstance(출처, dict) and all(isinstance(출처.get(k), list)
                                                           for k in ("paragraphs", "sentences", "questions"))):
        return jsonify(error="bad_request", message="source 는 paragraphs · sentences · questions 가 든 것이어야 합니다"), 400
    보류 = b.get("unsure", 0)                                  # "잘 모르겠음" 개수 (10/12) — 원문은 받지 않는다
    if not isinstance(보류, int) or isinstance(보류, bool) or not 0 <= 보류 <= 100000:
        return jsonify(error="bad_request", message="unsure 는 0 이상의 정수입니다"), 400
    for 이름 in ("explain_use", "explain_check"):              # v3 질문 두 칸 — 각 150자
        if len((b.get(이름) or "").strip()) > 설명_최대:
            return jsonify(error="bad_request", message=f"{이름} 는 {설명_최대}자까지입니다"), 400
    # v3 ③ 결과물에 들어간 것 — 보고서 문장 수 묶음 (PC 가 셈 · 선택 · 10/12). 숫자만 받는다 (문장 원문은 안 받음)
    결과수 = b.get("result_counts")
    if 결과수 is not None and not (isinstance(결과수, dict) and set(결과수) <= {"total", "ai", "other", "edited", "viewed", "none"}
                                and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 100000 for v in 결과수.values())):
        return jsonify(error="bad_request", message="result_counts 는 {total · ai · other · edited · viewed · none: 0 이상 정수} 여야 합니다"), 400
    # v3 ① 질문 쓰임새 수 (숫자만) · ② 학생이 고른 대표 질문 (최대 3 · 원문은 messages 에 같이 와야 함)
    쓰임키 = {"learn", "fix", "write"}
    쓰임수 = b.get("usage_counts")
    if 쓰임수 is not None and not (isinstance(쓰임수, dict) and set(쓰임수) <= 쓰임키
                                and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 100000 for v in 쓰임수.values())):
        return jsonify(error="bad_request", message="usage_counts 는 {learn · fix · write: 0 이상 정수} 여야 합니다"), 400
    흐름 = b.get("flow")
    if 흐름 is not None:
        원문쌍 = {(m.get("session_id"), m.get("event_id")) for m in 메시지들 if isinstance(m, dict)}
        if not (isinstance(흐름, list) and len(흐름) <= 3 and all(
                isinstance(f, dict) and (f.get("session_id"), f.get("event_id")) in 원문쌍
                and f.get("usage") in 쓰임키 | {None} and isinstance(f.get("used", False), bool) for f in 흐름)):
            return jsonify(error="bad_request", message="flow 는 최대 3개 · 질문 원문을 messages 에 같이 보내야 합니다"), 400
        흐름 = [{"session_id": f["session_id"], "event_id": f["event_id"], "usage": f.get("usage"), "used": bool(f.get("used"))}
               for f in 흐름]
    try:
        가림쌍 = {_쌍(r, "redactions") for r in 가림들}
        for m in 메시지들:
            _쌍(m, "messages")
            if not isinstance(m.get("text"), str) or not m["text"]:
                raise ValueError("messages 마다 text(원문)가 필요합니다")
            if len(m["text"].encode("utf-8", "surrogatepass")) > 원문_최대:
                return jsonify(error="too_large", message="원문 한 개는 256KB 까지입니다"), 413
            if _쌍(m, "messages") in 가림쌍:
                raise ValueError("가린 이벤트의 원문을 함께 보낼 수 없습니다")
            _가릴자리(m)                                          # 일부 가림 모양 확인 (틀리면 ValueError)
        for l in 연결들:
            if not isinstance(l, dict) or l.get("decision") not in ("confirmed", "rejected"):
                raise ValueError("links 마다 decision 이 confirmed 또는 rejected 여야 합니다")
            if not l.get("answer_hash") or not l.get("result_hash"):
                raise ValueError("links 마다 answer_hash 와 result_hash 가 필요합니다")
    except ValueError as e:
        return jsonify(error="bad_request", message=str(e)), 400

    with db.Session() as d:
        w = 내_과제(d, wid)
        if not w:
            return jsonify(error="not_found"), 404
        세션들 = {s.id: s for s in d.query(db.Sess).filter(db.Sess.work_id == wid).all()}
        # 원문 · 가림이 가리키는 이벤트를 한꺼번에 불러 둔다 (10/14) — 하나씩 물으면 100쪽 보고서는 수백 번 DB 를 오간다
        # (Render 싱가포르 ↔ Supabase 서울 한 번 ≈ 75ms → 몇 분)
        이벤트표 = _이벤트_모아(d, {_쌍(m, "messages") for m in 메시지들} | 가림쌍, 세션들)

        def 이벤트(sid, eid):
            return 이벤트표.get((sid, eid))

        문제들, 쓰인세션 = [], set()
        st = db.Statement(id=str(uuid.uuid4()), work_id=wid, user_id=g.user_id,
                          created_at=now().isoformat(timespec="microseconds"),   # 같은 초에 두 번 만들어도 순서가 갈리게
                          # 교수 규칙은 학생이 넣었을 때만 (10/10 · 아직 규칙 정한 교수가 거의 없어서) — 과제 메모를 저절로 옮기지 않는다
                          ai_scope=(b.get("ai_scope") or "").strip() or None, sentence=b.get("sentence"),
                          explain_use=(b.get("explain_use") or "").strip() or None,
                          explain_check=(b.get("explain_check") or "").strip() or None, unsure=보류 or None,
                          source=출처, show_process=bool(b.get("show_process")),
                          result_counts=결과수, usage_counts=쓰임수, flow=흐름)
        d.add(st)
        d.flush()

        # ① 원문 — 하나씩 체인과 맞춰 본다
        원문해시 = {}                                         # 서버가 계산한 해시 → role (연결 확인용, 맞은 것만)
        넣을 = {db.Message: [], db.Link: [], db.Redaction: []}   # 줄마다 INSERT 하지 않고 표마다 한 번에 (10/14)
        for m in 메시지들:
            sid, eid = _쌍(m, "messages")
            해시 = sha256_text(m["text"])
            e = 이벤트(sid, eid)
            p = e.payload if e else {}
            if sid not in 세션들:
                왜 = "not_in_work"                           # 이 과제의 세션이 아니다
            elif not e or e.type != "ai_msg":
                왜 = "not_in_chain"                          # 체인에 그런 AI 질문·답 이벤트가 없다
            elif p.get("hash") != 해시:
                왜 = "hash_mismatch"                         # 기록 당시 글과 다르다
            else:
                왜 = None
            if 왜:
                문제들.append({"session_id": sid, "event_id": eid, "why": 왜})
            else:
                원문해시[해시] = p.get("role")
                쓰인세션.add(sid)
            칸 = _가릴자리(m)                                      # 일부 가림 — 원문으로 확인했으니 가린 글만 남긴다
            넣을[db.Message].append(dict(statement_id=st.id, session_id=sid, event_id=eid,
                                        tool=p.get("tool") if e else m.get("tool"), role=p.get("role") if e else m.get("role"),
                                        ts=e.ts if e else m.get("ts"), text=_가린글(m["text"], 칸), hash=해시,
                                        history=bool(p.get("history")), match=왜 is None,
                                        model=str(m.get("model") or "")[:64] or None,
                                        masked=sorted({x[2] for x in 칸}) or None))

        # ② 연결 — "맞다"는 위에서 확인된 답을 가리켜야 한다. "아니다"는 원문을 받지 않는다
        for l in 연결들:
            맞다 = l["decision"] == "confirmed"
            결과 = l.get("result_text") if 맞다 and isinstance(l.get("result_text"), str) else None
            if 맞다:
                if 원문해시.get(l["answer_hash"]) != "answer":
                    문제들.append({"answer_hash": l["answer_hash"], "why": "answer_not_verified"})
                if l.get("question_hash") and 원문해시.get(l["question_hash"]) != "question":
                    문제들.append({"question_hash": l["question_hash"], "why": "question_not_verified"})
                if 결과 is not None and sha256_text(결과) != l["result_hash"]:
                    문제들.append({"result_hash": l["result_hash"], "why": "result_hash_mismatch"})
            넣을[db.Link].append(dict(statement_id=st.id, answer_hash=l["answer_hash"],
                                     question_hash=l.get("question_hash") if 맞다 else None,
                                     result_hash=l["result_hash"], result_text=결과, location=l.get("location"),
                                     kind=l.get("kind"), origin=l.get("origin"), decision=l["decision"],
                                     decision_event_id=l.get("decision_event_id")))

        # ③ 가림 — 어느 이벤트인지만. 이 과제의 체인에 있어야 한다
        for sid, eid in sorted(가림쌍):
            if not 이벤트(sid, eid):
                문제들.append({"session_id": sid, "event_id": eid, "why": "redaction_not_in_chain"})
            넣을[db.Redaction].append(dict(statement_id=st.id, session_id=sid, event_id=eid))
        for 표, 줄들 in 넣을.items():
            if 줄들:
                d.execute(insert(표), 줄들)                   # 받은 순서 그대로 (연결은 id 순으로 읽는다)

        # ④ 원문이 나온 세션은 봉인·검증돼 있어야 한다 (아직 기록 중이거나 체인이 어긋난 세션)
        세션상태 = []
        for sid in sorted(쓰인세션):
            s = 세션들[sid]
            봉인됨 = bool(s.sealed_at) and bool(s.verified) and bool(s.integrity_ok)
            세션상태.append({"id": sid, "sealed": bool(s.sealed_at), "verified": 봉인됨})
            if not 봉인됨:
                문제들.append({"session_id": sid, "why": "session_not_sealed" if not s.sealed_at else "session_not_verified"})

        # 같은 과제의 예전 내역서 중 살아 있는 링크가 없는 것은 보고서 전문을 지운다 (새 내역서가 대신함)
        for 옛 in d.query(db.Statement).filter(db.Statement.work_id == wid, db.Statement.id != st.id,
                                                db.Statement.source.isnot(None)).all():
            if not _출처_정리(d, 옛) and not d.query(db.Share).filter(db.Share.statement_id == 옛.id).count():
                옛.source = None                       # 링크도 안 만든 예전 내역서 — 새 내역서가 대신하므로
        st.problems, st.verified = 문제들, not 문제들
        st.summary = _과제_요약(d, wid)                   # 만들 당시 숫자를 함께 남긴다
        d.commit()
        답 = {"id": st.id, "work_id": wid, "created_at": st.created_at, "verified": st.verified,
              "problems": 문제들, "sessions": 세션상태,
              "counts": {"messages": len(메시지들),
                         "links_confirmed": sum(l["decision"] == "confirmed" for l in 연결들),
                         "links_rejected": sum(l["decision"] == "rejected" for l in 연결들),
                         "redactions": len(가림쌍)}}
    print(f"← 내역서 {답['id'][:8]}…  work={wid}  원문 {len(메시지들)} · 연결 {len(연결들)} · 가림 {len(가림쌍)}  "
          f"{'검증됨' if 답['verified'] else '문제 ' + str(len(문제들)) + '건 ⚠'}")
    return jsonify(답), 201


def _몸통_json():
    """요청 JSON — Content-Encoding: gzip 이면 풀어서 (PC 앱 0.1.8~ 은 큰 내역서를 줄여 보낸다 · 10/14). 못 읽으면 None.
    푼 크기가 풀린_최대 를 넘으면 OverflowError (작게 줄여 크게 부풀린 파일)"""
    if request.headers.get("Content-Encoding", "").strip().lower() != "gzip":
        return request.get_json(force=True, silent=True)
    try:
        풀기 = zlib.decompressobj(16 + zlib.MAX_WBITS)
        글 = 풀기.decompress(request.get_data(cache=False), 풀린_최대 + 1)
        if len(글) > 풀린_최대 or 풀기.unconsumed_tail:
            raise OverflowError
        return json.loads(글)
    except (zlib.error, ValueError):
        return None


def _이벤트_모아(d, 쌍들, 세션들):
    """{(세션, 이벤트 id)} → {(세션, 이벤트 id): Event}. 이 과제의 세션 것만 · 세션마다 500개씩 묶어 묻는다"""
    세션별 = {}
    for sid, eid in 쌍들:
        if sid in 세션들:
            세션별.setdefault(sid, set()).add(eid)
    표 = {}
    for sid, ids in 세션별.items():
        ids = sorted(ids)
        for i in range(0, len(ids), 500):
            for e in d.query(db.Event).filter(db.Event.session_id == sid, db.Event.id.in_(ids[i:i + 500])):
                표[(sid, e.id)] = e
    return 표


def _출처_정리(d, st):
    """보고서 전문(출처 보기)은 살아 있는 링크가 있을 때만 서버에 둔다 (10/12 · 학생이 켰을 때만 오는 것).
    살아 있는 링크 = 안 끊었고 기간이 안 끝남. 하나도 없으면 지운다. 지웠으면 True."""
    if not st.source:
        return False
    지금 = now()
    for sh in d.query(db.Share).filter(db.Share.statement_id == st.id, db.Share.revoked_at.is_(None)).all():
        if datetime.fromisoformat(sh.expires_at) >= 지금:
            return False
    if d.query(db.Share).filter(db.Share.statement_id == st.id).count() == 0:
        return False                                   # 아직 링크를 안 만들었음 — 지금 만드는 중일 수 있다
    st.source = None
    print(f"  · 내역서 {st.id[:8]}… 보고서 전문 지움 (살아 있는 링크 없음)")
    return True


_앱이름 = {"winword.exe": "Word", "microsoft word": "Word", "powerpnt.exe": "PowerPoint", "microsoft powerpoint": "PowerPoint",
          "excel.exe": "Excel", "microsoft excel": "Excel", "chrome.exe": "Chrome", "google chrome": "Chrome",
          "msedge.exe": "Edge", "microsoft edge": "Edge", "firefox.exe": "Firefox", "firefox": "Firefox", "safari": "Safari",
          "code.exe": "VS Code", "code": "VS Code", "claude.exe": "Claude 앱", "claude": "Claude 앱",
          "chatgpt.exe": "ChatGPT 앱", "chatgpt": "ChatGPT 앱", "hwp.exe": "한글", "notepad.exe": "메모장"}
_문서창 = re.compile(r"^(.+?\.(?:docx?|pptx?|xlsx?|hwpx?|txt|md|py|java|c|cpp|js))\b", re.I)


def _작업_과정(d, sid):
    """교수 링크 '작업 과정' 탭 (학생이 켰을 때만 · 캔버스 8 PublicLog): 세 줄 + 창 이름.
    AI 질문·답 = ai_msg 시각 · 붙여넣기 = paste 시각 · 글 = 키 입력이 이어진 구간(3분 넘게 끊기면 새 구간) ·
    창 = 앱 이름 + 문서 이름(창 제목의 파일 이름) + 탭 도메인. 글 원문은 없다."""
    evs = 이벤트들(d, sid)
    ai = [e["ts"] for e in evs if e.get("type") == "ai_msg" and not e.get("history")]
    붙임 = [e["ts"] for e in evs if e.get("type") == "paste"]
    글, 시작, 끝 = [], None, None
    for e in evs:
        if e.get("type") != "keys" or not e.get("count"):
            continue
        t = datetime.fromisoformat(e["ts"])
        if 끝 and (t - 끝).total_seconds() > 180:
            글.append({"start": 시작.isoformat(), "end": 끝.isoformat()})
            시작 = None
        시작 = 시작 or t - timedelta(seconds=10)
        끝 = t
    if 시작:
        글.append({"start": 시작.isoformat(), "end": 끝.isoformat()})
    창 = []
    for e in evs:
        if e.get("type") == "window":
            이름 = _앱이름.get((e.get("app") or "").lower())
            m = _문서창.match(e.get("title") or "")
            for x in (이름, m.group(1) if m and 이름 in ("Word", "PowerPoint", "Excel", "VS Code", "한글") else None):
                if x and x not in 창:
                    창.append(x)
        elif e.get("type") == "tab" and e.get("domain") and e["domain"] not in 창:
            창.append(e["domain"])
    return {"ai": ai, "paste": 붙임, "typing": 글, "windows": 창[:12]}


def _내역서_내용(d, st, 학생용):
    """내역서 하나를 화면용으로. 학생용이면 '아니다'·가림의 위치까지, 교수용이면 확인된 연결만."""
    메시지 = d.query(db.Message).filter(db.Message.statement_id == st.id).all()
    해시로 = {}
    for m in 메시지:
        해시로.setdefault(m.hash, m)
    연결 = d.query(db.Link).filter(db.Link.statement_id == st.id).order_by(db.Link.id).all()
    가림 = d.query(db.Redaction).filter(db.Redaction.statement_id == st.id).all()

    def 글(h):
        m = 해시로.get(h) if h else None
        # history = 이전 대화라 ts 는 '본 시각'이지 '받은 시각'이 아니다 → 화면이 그렇게 써야 한다
        return {"text": m.text, "tool": m.tool, "model": m.model, "ts": m.ts, "history": bool(m.history),
                "ok": bool(m.match), "masked": m.masked or []} if m else None

    맞다 = [{"question": 글(l.question_hash), "answer": 글(l.answer_hash),
             "result": {"text": l.result_text, "location": l.location},
             "kind": l.kind, "origin": l.origin} for l in 연결 if l.decision == "confirmed"]
    # 투명성 한 줄 (v3) — 쓴 도구(모델) : 내역서에 담긴 원문 기준. 모델은 PC 가 보낸 참고값
    # 도구 이름은 작업 기록(요약 · 체인의 ai_msg)에서 — 연결을 하나도 안 골라도 "Claude 앱 · 질문 2번" 처럼 나오게 (10/11 박상진)
    # 모델 이름만 내역서 원문에서 (PC 가 보낸 참고값)
    도구 = {t: set() for t in ((st.summary or {}).get("ai") or {}).get("tools", {})}
    for m in 메시지:
        도구.setdefault(m.tool or "AI", set())
        if m.model:
            도구[m.tool or "AI"].add(m.model)
    out = {"id": st.id, "created_at": st.created_at, "ai_scope": st.ai_scope, "sentence": st.sentence,
           "explain_use": st.explain_use, "explain_check": st.explain_check,
           "tools": [{"tool": t, "models": sorted(ms)} for t, ms in 도구.items()],
           "verified": bool(st.verified), "problems": st.problems or [], "summary": st.summary, "links": 맞다,
           "result_counts": st.result_counts, "usage_counts": st.usage_counts,
           # v3 ② 학생이 고른 대표 질문 — 원문 · 도구는 체인과 맞춰 본 메시지에서 (ok = 기록 당시 글과 같음)
           "flow": None if st.flow is None else [
               {"text": m.text, "tool": m.tool, "usage": f.get("usage"), "used": bool(f.get("used")), "ok": bool(m.match), "masked": m.masked or []}
               for f in st.flow for m in 메시지 if (m.session_id, m.event_id) == (f["session_id"], f["event_id"])],
           "rejected": sum(l.decision == "rejected" for l in 연결), "unsure": st.unsure or 0, "redacted": len(가림),
           "show_process": bool(st.show_process)}
    if st.source:
        # 출처 보기의 질문·답마다 서버가 맞춰 본 결과 (messages 의 해시) — 가린 질문은 원문 없이
        def 맞음(h):
            m = 해시로.get(h) if h else None
            return None if m is None else bool(m.match)
        out["source"] = {**st.source, "questions": [{**q, "question_ok": 맞음(q.get("question_hash")), "answer_ok": 맞음(q.get("answer_hash"))}
                                                     for q in st.source.get("questions", [])]}
    if not 학생용:
        # ★ 교수 화면엔 세션·이벤트 id 를 내보내지 않는다. 세션 id 를 알면 /sessions/<id>/events 로
        #   작업 기록 전체(창 이름 포함)를 읽을 수 있다 — 학생이 공유한 건 내역서뿐이다.
        out["problems"] = [{"why": p.get("why")} for p in out["problems"]]
        if not st.show_process and out["summary"]:          # 작업 과정(기록 목록)은 학생이 켰을 때만
            out["summary"] = {**out["summary"], "by_session": []}
        elif out["summary"]:                                 # 켰으면 세 줄 + 창 이름 (지운 기록은 이벤트가 없어 빈 줄)
            out["summary"] = {**out["summary"], "by_session": [{**x, "process": _작업_과정(d, x["id"])} if x.get("id") else x
                                                               for x in out["summary"].get("by_session", [])]}
        if out["summary"]:
            out["summary"] = {**out["summary"],
                              "by_session": [{k: v for k, v in s.items() if k != "id"}
                                             for s in out["summary"].get("by_session", [])]}
    if 학생용:
        out["rejected_links"] = [{"answer_hash": l.answer_hash, "result_hash": l.result_hash, "location": l.location}
                                 for l in 연결 if l.decision == "rejected"]
        out["redactions"] = [{"session_id": r.session_id, "event_id": r.event_id} for r in 가림]
        out["messages"] = [{"session_id": m.session_id, "event_id": m.event_id, "tool": m.tool, "role": m.role,
                            "ts": m.ts, "ok": bool(m.match)} for m in 메시지]
    return out


@app.get("/api/works/<wid>/statements/latest")
@로그인_필요
def latest_statement(wid):
    with db.Session() as d:
        if not 내_과제(d, wid):
            return jsonify(error="not_found"), 404
        st = (d.query(db.Statement).filter(db.Statement.work_id == wid)
              .order_by(db.Statement.created_at.desc(), db.Statement.id.desc()).first())
        if not st:
            return jsonify(error="not_found", message="아직 만든 내역서가 없습니다"), 404
        if request.args.get("brief"):                # 있나만 (PC 앱이 과제를 누를 때 · 10/14 — 100쪽이면 내용이 10MB 넘음)
            return jsonify(id=st.id, work_id=wid, created_at=st.created_at)
        답 = _내역서_내용(d, st, 학생용=True)
        답["shares"] = [{"token": s.token, "expires_at": s.expires_at, "revoked_at": s.revoked_at}
                        for s in d.query(db.Share).filter(db.Share.statement_id == st.id).all()]
    return jsonify(답)


@app.post("/api/statements/<stid>/share")
@로그인_필요
def create_share(stid):
    b = request.get_json(force=True, silent=True) or {}
    일수 = b.get("expires_in_days", 공유_기본일)
    if not isinstance(일수, int) or isinstance(일수, bool) or not 1 <= 일수 <= 공유_최대일:
        return jsonify(error="bad_request", message=f"expires_in_days 는 1~{공유_최대일} 사이 정수입니다"), 400
    with db.Session() as d:
        st = d.get(db.Statement, stid)
        if not st or st.user_id != g.user_id:
            return jsonify(error="not_found"), 404
        지금 = now()
        sh = db.Share(token=secrets.token_urlsafe(24), statement_id=stid, created_at=지금.isoformat(timespec="seconds"),
                      expires_at=(지금 + timedelta(days=일수)).isoformat(timespec="seconds"))
        d.add(sh)
        d.commit()
        답 = {"token": sh.token, "path": f"/api/share/{sh.token}", "page": f"/s/{sh.token}",
              "url": request.host_url.rstrip("/") + f"/s/{sh.token}",      # 학생이 교수에게 보내는 주소
              "pdf_url": request.host_url.rstrip("/") + f"/api/share/{sh.token}/pdf",   # 과제와 함께 내는 1장
              "expires_at": sh.expires_at}
    print(f"← 공유 링크 만듦  내역서 {stid[:8]}…  {일수}일")
    return jsonify(답), 201


@app.delete("/api/shares/<token>")
@로그인_필요
def revoke_share(token):
    with db.Session() as d:
        sh = d.get(db.Share, token)
        st = d.get(db.Statement, sh.statement_id) if sh else None
        if not st or st.user_id != g.user_id:
            return jsonify(error="not_found"), 404
        if not sh.revoked_at:
            sh.revoked_at = iso()
            _출처_정리(d, st)
            d.commit()
    return jsonify(ok=True)


견본_토큰 = "demo"     # 실제 토큰은 32자 무작위라 겹치지 않는다
인터넷_주소 = INTERNET.removesuffix("/api")


def _견본_내용():
    """늘 열리는 견본 내역서 — DB 를 안 쓰고 server/demo_share.json 을 그대로 준다.
    화면을 고칠 때마다 /demo · /demo/pdf 로 바로 확인하고, 인터뷰 때 보여 주는 용도. 지어낸 기록이다."""
    import json
    with open(os.path.join(HERE, "demo_share.json"), encoding="utf-8") as f:
        답 = json.load(f)
    답["expires_at"] = (now() + timedelta(days=14)).isoformat(timespec="seconds")
    return 답


def _공유_내용(token):
    """교수용 내역서 데이터. 없는 링크·끊은 링크·지난 링크는 None (어느 쪽인지 알려 주지 않는다)."""
    if token == 견본_토큰:
        return _견본_내용()
    with db.Session() as d:
        sh = d.get(db.Share, token)
        if not sh or sh.revoked_at:
            return None
        if datetime.fromisoformat(sh.expires_at) < now():
            st = d.get(db.Statement, sh.statement_id)
            if st and st.source and _출처_정리(d, st):         # 기간이 끝난 링크 — 보고서 전문을 지금 지운다
                d.commit()
            return None
        st = d.get(db.Statement, sh.statement_id)
        w, u = d.get(db.Work, st.work_id), d.get(db.User, st.user_id)
        if w and w.deleted_at:
            return {"deleted_at": w.deleted_at}             # 지운 과제 — 내용 없이 지운 시각만
        답 = _내역서_내용(d, st, 학생용=False)
        답["work"] = {"title": w.title if w else None}
        답["author"] = u.name if u else None            # 계정 이름 — Trace 가 신원을 확인하지는 않는다
        답["expires_at"] = sh.expires_at
    return 답


@app.get("/api/share/<token>")
def read_share(token):
    """교수 확인용 — 로그인 없음 · 읽기 전용. 없는 링크·끊은 링크·지난 링크는 똑같이 404 (어느 쪽인지 알려 주지 않는다)."""
    답 = _공유_내용(token)
    if 답 is None:
        return jsonify(error="not_found", message="없거나 끝난 링크입니다"), 404
    if "deleted_at" in 답 and len(답) == 1:
        return jsonify(error="deleted", deleted_at=답["deleted_at"],
                       message=f"학생이 {답['deleted_at'][5:10].replace('-', '/')} 에 지운 기록입니다"), 410
    return jsonify(답)


@app.get("/api/share/<token>/pdf")
def share_pdf(token):
    """AI 활용 내역서 1장 PDF (기획서 10절). 학생이 과제와 함께 낸다. 안에 교수 확인 링크·QR 이 들어간다.
    링크를 아는 사람만 받는다 — 링크와 같은 열쇠. (server/statement_pdf.py)"""
    답 = _공유_내용(token)
    if 답 is None or ("deleted_at" in 답 and len(답) == 1):
        return jsonify(error="not_found", message="없거나 끝난 링크입니다"), 404
    from urllib.parse import quote
    import statement_pdf                                   # reportlab · 글꼴은 PDF 를 처음 만들 때만 읽는다
    # 견본 PDF 의 QR 은 늘 인터넷 서버로 — 로컬 서버(127.0.0.1)에서 만든 견본도 휴대폰으로 찍으면 열린다
    주소 = 인터넷_주소 if token == 견본_토큰 else request.host_url.rstrip("/")
    pdf = statement_pdf.render(답, 주소 + f"/s/{token}")
    이름 = f"AI활용내역서_{(답['work']['title'] or '과제')[:40]}.pdf"
    return app.response_class(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f"inline; filename=\"statement.pdf\"; filename*=UTF-8''{quote(이름)}"})


@app.get("/s/<token>")
def share_page(token):
    """교수가 여는 화면. HTML 한 장이 /api/share/<token> 을 읽어 그린다 (server/static/share.html).
    토큰이 맞는지는 여기서 보지 않는다 — 화면이 API 를 부르고, 없으면 "볼 수 없는 링크"를 그린다."""
    return send_from_directory(os.path.join(HERE, "static"), "share.html")


@app.get("/demo")
def demo_page():
    """견본 교수 화면 — 링크 없이 바로 열어 보는 주소."""
    return redirect(f"/s/{견본_토큰}")


@app.get("/demo/pdf")
def demo_pdf():
    """견본 내역서 PDF."""
    return redirect(f"/api/share/{견본_토큰}/pdf")


# ─────────────── 설치판 내려받기 (v0.1 · 10/13) ───────────────
# 설치 파일은 GitHub 릴리스에 있다 (태그 v* 를 올리면 .github/workflows/release.yml 이 윈도우 · 맥에서 묶어 올림).
# 서버는 최신 릴리스를 10분마다 읽어 두고 → 내려받기 화면과 PC 앱의 "새 버전" 알림이 같은 것을 본다.
# ★ GitHub API 는 쓰지 않는다 (10/14) — 로그인 없는 API 는 IP 마다 시간당 60번인데 Render 는 여러 서비스가 IP 를 같이 써서
#   첫 릴리스(v0.1.0) 를 올려도 계속 "없음" 이었다. 대신 보통 웹 주소를 본다:
#   ① …/releases/latest 가 넘겨 주는 주소(…/tag/v0.1.0) 로 태그 ② 파일 이름은 build.py 가 정한 대로 ③ 바뀐 것 글은 저장소의 notes/<태그>.md
저장소 = "20233014-KYH/trace"
_릴리스 = {"at": 0.0, "data": None}
설치_파일 = {"windows": "Trace-Setup-{v}.exe", "mac": "Trace-{v}-mac.dmg", "extension": "Trace-{v}-extension.zip"}


class _안_따라감(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):                     # 넘겨 주는 주소만 보고 따라가지 않는다
        return None


def _github(url, method="GET"):
    """(상태, 머리, 몸) — 넘겨 주기(30x)를 따라가지 않는다"""
    요청 = urllib.request.Request(url, method=method, headers={"User-Agent": "trace-server"})
    try:
        with urllib.request.build_opener(_안_따라감).open(요청, timeout=8) as r:
            return r.status, r.headers, r.read() if method == "GET" else b""
    except urllib.error.HTTPError as e:
        return e.code, e.headers, b""


def _릴리스_읽기():
    """→ {version, tag, page, notes, windows, mac, extension} · 릴리스가 없으면 {"version": ""}"""
    from urllib.parse import quote
    코드, 머리, _ = _github(f"https://github.com/{저장소}/releases/latest", "HEAD")
    m = re.search(r"/releases/tag/([^/?#]+)$", 머리.get("Location") or "") if 코드 in (301, 302, 303, 307, 308) else None
    if not m:
        if 코드 in (301, 302, 303, 307, 308, 404):              # 릴리스 목록으로 넘어감 = 아직 없음
            return {"version": "", "tag": None}
        raise OSError(f"releases/latest HTTP {코드}")
    tag = m.group(1)
    v = tag.lstrip("vV")
    d = {"version": v, "tag": tag, "published_at": None, "page": f"https://github.com/{저장소}/releases/tag/{tag}", "notes": ""}
    for 키, 틀 in 설치_파일.items():
        이름 = 틀.format(v=v)
        url = f"https://github.com/{저장소}/releases/download/{tag}/{이름}"
        코드, _, _ = _github(url, "HEAD")                      # 있으면 내려받는 곳으로 넘겨 줌(302)
        d[키] = {"name": 이름, "url": url, "size": None} if 코드 in (200, 302) else None
    코드, _, 몸 = _github(f"https://raw.githubusercontent.com/{저장소}/{tag}/" + quote(f"3-코드/packaging/notes/{tag}.md"))
    if 코드 == 200:
        d["notes"] = 몸.decode("utf-8", "replace").strip()[:2000]
    return d


def _최신_릴리스():
    import time
    if _릴리스["data"] is not None and time.time() - _릴리스["at"] < 600:
        return _릴리스["data"]
    try:
        _릴리스["data"] = _릴리스_읽기()
        _릴리스["at"] = time.time()
    except Exception as e:                                   # noqa: BLE001  GitHub 이 안 되면 전에 읽은 것 (없으면 None)
        print(f"  릴리스 읽기 실패 ({type(e).__name__}: {e}) — 전에 읽은 것으로")
        _릴리스["at"] = time.time() - 540                      # 1분 뒤 다시
    return _릴리스["data"]


@app.get("/api/app/latest")
def app_latest():
    """최신 설치판 {version, tag, page, notes, windows · mac · extension: {name, url} | null} · 없으면 404"""
    d = _최신_릴리스()
    if not d or not d.get("version"):
        return jsonify(error="no_release", message="아직 올린 설치판이 없습니다"), 404
    return jsonify(d)


@app.get("/download")
def download_page():
    """Trace 내려받기 화면 (static/download.html) — /api/app/latest 를 읽어 버튼을 채운다"""
    return send_from_directory(os.path.join(HERE, "static"), "download.html")


@app.after_request
def 공유_머리(resp):
    """공유 링크는 주소 자체가 열쇠다. 다른 사이트로 새지 않게(Referer) · 검색에 안 잡히게 · 저장 안 되게."""
    if request.path.startswith(("/s/", "/api/share/")):
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    # ★ 맥은 5000 번을 AirPlay 수신 모드가 이미 쓰고 있다 ★
    #   우리 서버가 꺼져 있으면 AirPlay 가 대신 대답하고 403 을 돌려준다.
    #   수집기는 "서버가 있네" 하고 보냈다가 계속 거절당한다. 원인 찾기 어렵다.
    #   맥에서는 포트를 바꾸는 쪽이 낫다:  TRACE_PORT=5050 python server/app.py
    #   (윈도우는 이 문제가 없어 5000 그대로 쓰면 된다)
    PORT = int(os.environ.get("TRACE_PORT", "5000"))
    print(f"Trace Backend  http://127.0.0.1:{PORT}/api   저장: {db.DB_URL_SAFE}")
    print("  계약: docs/api.md   ·  참고 구현과 같은 응답을 내야 합니다")
    print(f"  인증: {'강제' if 인증_강제 else '선택 (TRACE_REQUIRE_AUTH=1 로 켬)'}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
