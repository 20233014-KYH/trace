# 서버 (A 담당)

팀원(B)이 만든 참고 서버 `collector/dev_receiver.py` 를 **옮긴 것**입니다. 새로 짜지 않았습니다.

| | 참고 서버 | 이 서버 |
|---|---|---|
| 엔드포인트·요청·응답 | — | **똑같음** (한 글자도 안 바꿈) |
| 해시 계산 | `core/chain.py` | **`core/chain.py` (같은 파일 import)** |
| 화면 데이터 변환 | `core/derive.py` | **`core/derive.py` (같은 파일 import)** |
| 저장 | 메모리 dict | **DB (SQLite / PostgreSQL)** |

---

## 돌리는 법

```bash
conda activate trace
pip install -r 3-코드/requirements.txt
python 3-코드/server/app.py          # http://127.0.0.1:5000/api
```

맥은 **`0_서버시작.command` 더블클릭**, 윈도우는 `0_서버시작.bat`.

### ⚠️ 맥에서 `Address already in use` 또는 `HTTP 403` 이 날 때

**맥은 5000 번을 AirPlay 수신 모드가 이미 쓰고 있습니다.**

더 고약한 건, 우리 서버가 꺼져 있을 때 **AirPlay 가 대신 대답해서 403 을 돌려준다**는 것입니다.
수집기는 "서버가 있네" 하고 보냈다가 계속 거절당합니다 — 원인 찾기가 어렵습니다.

```
· 세션 등록 거절됨 HTTP 403  — 로컬 기록은 남아 있음
· batch 4건 거절됨 HTTP 403
```

**권장 — AirPlay 를 끄세요.** 팀원(윈도우)과 설정이 같아집니다.

> 시스템 설정 → 일반 → AirDrop 및 Handoff → **AirPlay 수신 모드** 끄기

**끄기 싫으면 포트를 바꿉니다.** 이때는 수집기 설정도 같이 바꿔야 합니다.

```bash
TRACE_PORT=5050 python server/app.py
```
그리고 `collector/config.json` 의 `"server"` 를 `http://127.0.0.1:5050/api` 로.

윈도우는 이 문제가 없습니다. 5000 번 그대로 쓰면 됩니다.

### 제대로 도는지 검사

서버를 켜 둔 채로, 다른 창에서:

```bash
python 3-코드/server/test_contract.py
```

```
  ✅ 1 health               세션 0개 · 저장 db
  ✅ 2 세션 만들기 (멱등)      처음 201 · 다시 200
  ✅ 3 batch 정상            저장 18건 · head 35a9e01c2f91…
  ✅ 4 batch 중복 무시        저장 0 · 중복 18
  ✅ 5 batch 조작 탐지        evt_000021 의 입력 30 → 999 → verified=False
  ✅ 6 봉인 (조작 세션)        HTTP 409 · chain_mismatch
  ✅ 7 봉인 (정상)            root 4b1b92beae4e5c03…
  ✅ 8 조회 (session.json)   타자 303자 · 붙임 4건
```

맥은 **`9_계약검사.command` 더블클릭**.

**5번이 이 서비스의 핵심입니다** — 이벤트를 한 글자 고쳐 보내면 서버가 재계산해서 잡아냅니다.

---

## 파일

| | |
|---|---|
| `db.py` | 표(테이블) 정의. `python server/db.py` 로 만들고 구조를 볼 수 있음 |
| `app.py` | 서버 본체 |
| `test_contract.py` | 계약대로 도는지 검사 |
| `trace.db` | SQLite 파일 (깃에 안 올라감) |

---

## 알아둘 것 세 가지

### ① 해시는 여기서 계산하지 않습니다

```python
from core import chain as C      # ★ 이것만 씁니다
```

서버에서 다시 짜면 **수집기와 영원히 안 맞습니다.** B가 세 번 강조한 것이고 맞는 말입니다.

### ② 이벤트 기본키가 `(session_id, id)` 입니다

수집기가 붙이는 `evt_000001` 은 **세션 안에서만** 고유합니다. 세션이 바뀌면 다시 1번부터 시작합니다.
`id` 하나만 기본키로 잡으면 **두 번째 세션에서 충돌**합니다.

### ③ `batches` 표가 따로 있습니다

계약 3절의 **"이벤트 시각과 수신 시각 차이가 5분 넘으면 지연 수신으로 표시"** 때문입니다.
배치마다 받은 시각을 남겨야 나중에 증명서에 쓸 수 있습니다. 빼먹기 쉽습니다.

---

## 참고 서버와 다른 곳 (딱 1군데)

`duplicates` 숫자. 참고 서버는 메모리에 id 를 들고 있어 **heartbeat 까지** 중복으로 세고,
이 서버는 계약대로 heartbeat 를 **DB 에 저장하지 않으므로** 중복으로도 세지 않습니다.

로그용 숫자이고, 멱등 보장(중복 저장 안 함)은 양쪽 같습니다. `test_contract.py` 가 이 차이를 알고 검사합니다.

---

## 인증 · Work (계약 1·2절) — 9/21 완료

```bash
python 3-코드/server/test_auth.py     # 검사 14개
```

```
  ✅ 7 비번 원문 저장 안 함    저장된 값: scrypt:32768:8:1$VKj…
  ✅ 12 남의 Work 못 봄       HTTP 404
  ✅ 14 로그아웃하면 토큰 죽음   로그아웃 200 · 그 뒤 /me 401
```

**★ 인증은 켜져 있지만 강제하지 않습니다.**
B 의 수집기가 아직 토큰을 안 보내서, 401 을 던지면 10/7 관통이 깨집니다.

```bash
python server/app.py                        # 인증 선택 (기본)
TRACE_REQUIRE_AUTH=1 python server/app.py   # 인증 강제
```

수집기가 토큰을 보내게 되면 그때 켭니다. 그때까지 `test_contract.py` 11개는 그대로 통과합니다 (10/3: AI 대화 기록 검사 3개 추가).

### 왜 JWT 가 아닌가

JWT 는 서버가 들고 있지 않아 **로그아웃·강제 만료를 못 합니다.**
학생 기록을 다루므로 "이 기기 연결 끊기"가 되어야 합니다. 표 하나면 그게 되고,
초보가 봐도 무슨 일이 일어나는지 보입니다.

---

## AI 활용 내역서 (10절) — 10/8

학생이 **"내역서 만들기"**를 누르면 고른 AI 질문·답·결과물 발췌의 **원문이 처음으로** 서버에 온다.
서버는 원문의 해시(`core/texthash.py`)를 다시 계산해 기록 중 체인에 들어간 `ai_msg.hash` 와 비교한다.

| 주소 | 누가 | 하는 일 |
|---|---|---|
| `POST /api/works/<id>/statements` | 학생 (로그인 · 내 과제만) | 원문 검증 → 내역서 저장. 고친 글은 버리지 않고 "조작됨"으로 남김 |
| `GET /api/works/<id>/summary` | 학생 | 요약 숫자 — 체인 이벤트로 센다 (`core/summary.py` · 비율·점수 없음 · 출처 모르는 붙여넣기는 "출처 기록 없음") |
| `GET /api/works/<id>/statements/latest` | 학생 | 마지막 내역서 (다시 만들면 마지막 것이 유효) |
| `POST /api/statements/<id>/share` | 학생 | 교수 확인 링크 (기본 14일 · 최대 90일) |
| `DELETE /api/shares/<token>` | 학생 | 링크 끊기 |
| `GET /api/share/<token>` | 교수 (로그인 없음) | 확인된 연결만 읽기 · 없음/끊음/만료는 똑같이 404 |

**지키는 것:** "아니다"로 고른 연결의 결과물 원문은 받아도 버린다 · 가린 이벤트는 위치만 · 도구·역할·시각은 학생이 보낸 값이 아니라 체인의 값.

```bash
TRACE_DB_URL=sqlite:///test.db TRACE_PORT=5050 python server/app.py   # ★ 시험은 따로 만든 SQLite 로 (Supabase 에 시험 기록이 쌓이지 않게)
TRACE_PORT=5050 python server/test_statements.py                       # 검사 30개
```

## 아직 안 만든 것

| 계약 | 언제 |
|---|---|
| 4절 증명서 · proof.json · .ots · `/verify` | 7~8주차 |
| 앵커 실제 제출 (OpenTimestamps) | 7주차 |
| 교수 화면 · `link_decision` 확인 | 다음 |
| 기록기가 토큰을 보내기 (그전엔 기록기가 만든 과제는 주인이 없어 내역서를 못 만든다) | 박상진과 정할 것 |

**3주차 관통에 필요한 3절(세션·이벤트·봉인·조회)은 다 됐습니다.**

---

## 인터넷 DB (Supabase) — 10/4

맥·PC 안의 파일(`trace.db`) 대신 **Supabase(PostgreSQL · 서울 지역)** 에 저장한다. 서버 코드는 같다. 저장하는 곳만 바뀐다.

```bash
cp server/.env.example server/.env     # 그다음 .env 의 TRACE_DB_URL= 뒤에 주소를 넣는다 (비우면 trace.db)
python server/app.py                   # 첫 줄 "저장: postgresql+psycopg://postgres.…:***@…" 이면 Supabase
```

| 꼭 지킬 것 | 왜 |
|---|---|
| 주소는 Supabase **Connect → Direct → Session pooler** (포트 5432) | 무료 플랜의 Direct connection 은 IPv6 전용이라 집·학교 인터넷에서 안 붙을 수 있다 |
| 주소·비밀번호는 **`.env` 에만** | `.env` 는 `.gitignore` 에 걸려 저장소에 안 올라간다. 서버는 비밀번호를 `***` 로 가려서 찍는다 |
| 프로젝트의 **Data API 는 끔** | 우리 서버가 DB 에 직접 붙으므로 필요 없다. 서버는 켜질 때 표마다 행 보안(RLS)도 켠다 (예비 잠금) |
| **없는 과제로 세션이 와도 됨** | 기록기는 과제를 안 만들고 바로 세션을 보낸다. SQLite 는 받아 주지만 PostgreSQL 은 거절(500)해서, 서버가 없는 과제를 먼저 만든다 |

`pip install "psycopg[binary]"` 가 필요하다 (`requirements.txt` 에 있음).

## 배포 (Render · 10/7)

**쓰는 법(기록기 연결)은 [`../서버_이용가이드.md`](../서버_이용가이드.md).** 주소: `https://trace-server-8aa0.onrender.com/api`

저장소 맨 위 `render.yaml` 이 설정 전부다. Render → **New → Blueprint** → 이 저장소 → `TRACE_DB_URL` 하나만 넣는다 (Supabase Session pooler 주소 · 비밀번호 포함 · 저장소엔 안 씀).

| | |
|---|---|
| 지역 | 싱가포르 (Render 지역 중 서울 Supabase 에 가장 가까움) |
| 실행 | `gunicorn --workers 1 --threads 4` — **서버는 하나만.** 여럿이면 처음 켤 때 동시에 표를 만들다 하나가 죽는다 (10/7 시험) |
| 부품 | `server/requirements.txt` (서버에 필요한 것만 · 기록기 부품은 안 깔림) |
| 무료 플랜 | 15분 안 쓰면 잠들고 첫 요청이 1분쯤 걸린다. 기록기는 실패하면 큐에 쌓았다가 다시 보내서 기록은 안 잃는다 |
| 확인 | `https://<주소>/api/health` → `"storage":"db"` |

**인터넷에 올리기 전에 막은 것 (10/7):** 과제 목록·과제 조회·`/me` 는 **언제나 로그인이 필요**하다(401). 전엔 로그인 없이도 과제 목록 → 과제 → 세션 id → 기록(창 이름 포함)이 줄줄이 읽혔다. 기록기가 쓰는 주소(세션·이벤트·봉인·맥락)는 기록기가 토큰을 보내게 되면 `TRACE_REQUIRE_AUTH=1` 로 막는다. 그 전까지 세션 기록은 추측할 수 없는 세션 id(UUID)를 알아야만 읽힌다.

로컬에서 Render 와 똑같이 돌려 보기:
```bash
pip install -r 3-코드/server/requirements.txt
gunicorn --chdir "3-코드/server" app:app --bind 127.0.0.1:5052 --workers 1 --threads 4
```
