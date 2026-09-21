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

## 아직 안 만든 것

| 계약 | 언제 |
|---|---|
| 1절 인증 (`/auth/login` · `/me`) | 4주차 |
| 2절 Work CRUD | 4주차 |
| 4절 증명서 · proof.json · .ots · `/verify` | 7~8주차 |
| 앵커 실제 제출 (OpenTimestamps) | 7주차 |

**3주차 관통에 필요한 3절(세션·이벤트·봉인·조회)은 다 됐습니다.**

---

## 배포할 때 (9주차)

주소만 바꾸면 PostgreSQL 로 갑니다. 코드는 그대로입니다.

```bash
export TRACE_DB_URL="postgresql://..."
python server/app.py
```
