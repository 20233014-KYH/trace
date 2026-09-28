# Trace API 계약 ③ (확정본 v2.0)

**2026-09-28 개정** · v1.0(9/21 확정) → 기획 전면 개정(`1-기획/5-기획 수정사항 (2026-09-28).md`) 반영.
바꿀 때는 **상대에게 먼저 말하고** 이 파일을 고칩니다. 코드가 아니라 **이 문서가 기준**입니다.

> 이 계약이 있어서 **한쪽은 기록기 없이 서버를, 다른 쪽은 서버 없이 기록기·화면을** 만들 수 있습니다.
> 참고 구현은 `3-코드/collector/dev_receiver.py` (메모리 저장),
> 실제 서버는 `3-코드/server/` (DB 저장) — **둘은 같은 응답을 내야 합니다.**

---

## ⚠️ v1.0 → v2.0 변경 요약 (구현 전 반드시 읽을 것)

| | v1.0 (9/21) | v2.0 (9/28) |
|---|---|---|
| **삭제** | `GET/POST /sessions/{id}/report` | 없음 — Learning Report 기능 폐기 |
| **삭제** | `POST /sessions/{id}/chat` | 없음 — Side Chat 폐기 |
| **삭제** | `/sessions/{id}/certificate` · `certificate.pdf` · `proof.ots` · `POST /verify` | 요약 1장 + 공유 링크로 대체. 외부 시간 도장(OTS)은 이번 학기 제외 |
| **수정** | `POST /works {title, mode:"learn"\|"proof"}` | `POST /works {title, ai_policy:"forbidden"\|"allowed"}` |
| **수정** | 세션 생성 요청에 `mode` | **`mode` 제거** — 세션에 모드 개념이 없음 |
| **수정** | `/context` 는 Learn 세션에서만 (Proof 면 403) | **항상 받는다.** 403 없음. 의미도 "학습 맥락" → **"AI 대화 기록"** |
| **추가** | — | `/works/{id}/summary` · `/links` · `/redactions` · `/share` · `GET /share/{token}` · `/import` |

**서버 구현자에게:** `3-코드/server/app.py` 의 `_learn만()` 헬퍼와 `report`·`chat` 라우트를 지우고,
`db.Work` 에 `ai_policy` 컬럼을 더하고, `db.Sess.mode` 는 남기되 쓰지 않습니다(옛 데이터 호환).

---

## 0. 공통

- Base: `https://<host>/api` (개발: `http://127.0.0.1:5000/api` · 맥은 `TRACE_PORT=5050`)
- 인증: `Authorization: Bearer <token>` (로그인 후). 기록기는 최초 1회 로그인 토큰을 `config.json`에 저장
- 시각: ISO 8601, 타임존 포함 (`2026-09-19T15:10:01+09:00`)
- id: **클라이언트가 만든다** (UUID v4). 오프라인에서도 세션·이벤트를 만들 수 있어야 하므로. 서버는 받은 id를 그대로 저장, 중복이면 무시(멱등)
- 오류: `{"error":"code","message":"..."}` · 400 형식 오류 · 401 인증 · 404 없음 · 409 중복/상태 충돌

---

## 1. 인증

```
POST /auth/signup       {email, password, name?}    → {id, name}              201
POST /auth/login        {email, password, device?}  → {token, user:{id, name}}
POST /auth/logout       (Bearer)                    → {ok:true}
GET  /me                (Bearer)                    → {id, name, works:[…]}
```

**토큰은 JWT 가 아니라 DB 의 무작위 문자열**입니다. JWT 는 서버가 들고 있지 않아
로그아웃·강제 만료를 못 합니다. 학생 기록을 다루므로 **연결 끊기가 되어야** 합니다.

**인증은 켜져 있지만 강제하지 않습니다.** 기록기가 아직 토큰을 보내지 않아
여기서 401 을 던지면 10/7 관통 테스트가 깨집니다.

```bash
python server/app.py                        # 인증 선택 (기본)
TRACE_REQUIRE_AUTH=1 python server/app.py   # 인증 강제
```

---

## 2. Work — 하나의 과제

```
POST /works        {title, ai_policy:"forbidden"|"allowed"}   → {id, title, ai_policy, created_at}
GET  /works                                                    → [{id, title, ai_policy, sessions:n, last_at}]
GET  /works/{id}                                               → {id, title, ai_policy, sessions:[{id, start, end, dur, events, sealed}]}
PATCH /works/{id}  {title?, ai_policy?}                        → {id, title, ai_policy}
```

- **`ai_policy` 는 기록을 바꾸지 않는다.** 요약 1장(4절)의 내용만 바꾼다.
- 요약을 내기 직전에 바꿀 수 있으므로 `PATCH` 가 필요하다.
- 한 과제(Work)는 여러 세션으로 이루어진다 — 며칠에 걸쳐 껐다 켰다 해도 한 과제다.

---

## 3. Session — 기록기가 켜져 있던 한 번

```
POST /works/{work_id}/sessions
  요청  {id:"<uuid>", device:{name, os:"win"|"mac", collector_version}, started_at}
  응답  {id, work_id, started_at}                   201 · 이미 있으면 200 (멱등)
  ★ v2.0: 요청에서 mode 제거

POST /sessions/{id}/events                            ← 기록기 batch
  요청  {events:[ <이벤트 한 줄> … ], chain_head:"<sha256>", chain_len:n}
        50건 이하 · 5초마다 · 순서대로 · chain_head = 이 배치 마지막 이벤트까지 PC에서 계산한 해시
  응답  {accepted:n, duplicates:n, last_id:"evt_…", verified:true|false, server_head:"<sha256>", received_at}
  · 이벤트 한 줄 = 계약 ① (3-코드/README.md 4번). 서버는 id 중복이면 세지 않고 200
  · 서버는 받은 이벤트로 체인을 **재계산**해 chain_head 와 비교. 다르면 verified:false + 세션에 "조작됨" 표시 (조용히 넘기지 않음)
  · 서버는 배치의 received_at 을 저장. 이벤트 ts 와 received_at 차이가 5분 넘으면 그 구간은 "지연 수신"으로 표시
  · heartbeat 도 보내되 DB엔 저장 안 함 — 세션의 last_heartbeat_at 만 갱신 (공백 계산용)

POST /sessions/{id}/end                               ← 봉인
  요청  {ended_at, chain_len:128, root:"<sha256 hex>"}
  응답  {id, ended_at, sealed_at, root, verified:true|false, late_batches:n}
  · 서버는 전체 체인을 다시 계산해 root 일치 여부를 `verified` 에. 불일치면 409 + {server_root}, 세션은 "봉인 실패"
  ★ v2.0: anchor(OpenTimestamps) 필드 제외 — 이번 학기 범위 밖

GET  /sessions/{id}                                   ← 화면
  응답  = 계약 ② session.json 구조 그대로
        {id, work_id, date, start, end, dur, minutes, sealed_at, root,
         segments[], typed[], deleted[], pastes[], undos[], chain[], stats{}}

GET  /sessions/{id}/events?after=<evt_id>&limit=500   ← 체인 원본 화면 · 디버그
  응답  {events:[…], next:"evt_…"|null}
```

---

## 4. AI 대화 기록 (옛 Context)

```
POST /sessions/{id}/context                           ← 브라우저 확장 · 편집기 확장 · Office 모듈
  요청  {items:[{id, ts, source:"browser"|"editor"|"office", kind, text, meta:{domain?, url?, file?, line?, app?}}]}
        kind (browser): ai_question | ai_answer | selection | page
        kind (editor):  diff | paste_at | bulk_insert | external_edit
        kind (office):  diff | paste_at | save_stats
  응답  {accepted:n}
  ★ v2.0: 403 없음 — 모든 세션에서 받는다 (모드가 사라졌으므로)
  ★ v2.0: ai_answer_excerpt → ai_answer. 발췌가 아니라 **원문**을 받는다 (고쳐 쓴 곳을 나란히 보여주려면 원문이 필요)
  · 항목별 토글이 꺼져 있으면 기록기·확장이 아예 안 보낸다 (서버가 막는 게 아님)

GET  /sessions/{id}/context                           ← 읽기
  응답  {items:[{id, ts, source, kind, text, meta}]}   ts 순서
```

**길이 상한:** v1.0 의 500자 제한을 **없앱니다.** AI 답 원문 전체가 있어야 "그대로 붙였는지 고쳐 붙였는지"를
나란히 보여줄 수 있습니다. 대신 한 항목 64KB, 한 요청 1MB 를 넘으면 413.

---

## 5. 요약 1장 · 연결 · 가리기 · 공유 (신규 · 11~12주)

```
GET  /works/{id}/summary                              ← 요약 1장 데이터 (규칙 기반 · AI 호출 없음)
  응답  {work:{id, title, ai_policy}, sessions:n, span:{start, end}, active_min,
         typed_chars, pasted:{count, from_ai:n, from_other:n},
         ai:{tools:[…], questions:n, links:{verbatim:n, edited:n}},
         unsourced:[{start, end, chars}],            ← "출처 기록 없음" 구간
         chain:{verified:true|false, sealed_sessions:n}}
  · 여기에 점수·확률·등급·퍼센트 유사도는 **없다** (원칙 1)
  · ai_policy 에 따라 화면이 고르는 항목이 다를 뿐, 응답은 같다

POST /works/{id}/links                                ← 연결 확인 결과 저장
  요청  {links:[{context_id, target:{session_id, event_id, offset?}, state:"confirmed"|"rejected", kind:"verbatim"|"edited"}]}
  응답  {saved:n}
  · state:"rejected" 도 **지우지 않고 저장한다** — "제안했고 학생이 연결하지 않음" 이 남는다 (원칙)
  · 연결 확인 자체가 체인 이벤트(`link_decision`)로 기록기가 아니라 서버에서 추가된다

POST /works/{id}/redactions                           ← 가리기
  요청  {items:[{context_id|event_id, reason?}]}
  응답  {redacted:n}
  · 내용은 응답에서 빠지고 자리에 {redacted:true} 만 남는다
  · **해시는 그대로** 두므로 체인 검증은 계속 된다

POST /works/{id}/share                                ← 공유 링크 만들기
  요청  {expires_in_days?:14}
  응답  {token, url, expires_at}
DELETE /works/{id}/share/{token}                       → {ok:true}       ← 되돌리기

GET  /share/{token}                                   ← 교수용 · **인증 불필요 · 읽기 전용**
  응답  {work:{title, ai_policy}, summary:{…}, links:[{ai_answer, result, kind}], 
         redacted:n, chain:{verified, sealed_sessions}, generated_at}
  · 로그인 없이 링크만으로 열린다. 쓰기는 어떤 것도 안 된다
  · 학생이 가린 항목은 내용 없이 "가림"으로만 보인다
  · chain.verified 가 false 면 화면 맨 위에 "조작됨"

POST /works/{id}/import                               ← AI 대화 내보내기 파일 (추가 과제 D)
  요청  multipart: file (ChatGPT·Claude 대화 내보내기 zip/json)
  응답  {imported:n, in_range:n, suggestions:n}
  · 과제 기간에 걸친 대화만 추려 context 로 넣고, 결과물과 비슷한 것을 연결 **제안**만 한다
```

---

## 6. 기록기 쪽 동작 (지킬 것)

1. 시작: `POST /works/{w}/sessions` (오프라인이면 큐에 넣고 진행)
2. 이벤트가 생길 때마다 **PC에서 체인에 넣는다** (hᵢ = SHA256(hᵢ₋₁ ‖ ts ‖ type ‖ summary)). 로컬 파일에도 해시가 같이 남는다
3. 매 5초 또는 50건: `POST /sessions/{id}/events` batch + 그 시점의 chain_head. 실패 → `queue.jsonl` 보관, 10초 후 재시도, 성공 시 **순서대로** 재전송
4. 종료: 로컬 체인 완성 → `POST /sessions/{id}/end`. 오프라인이면 큐 맨 뒤에 넣고 다음 실행 때 전송
5. 로컬 `events-날짜.jsonl` 은 서버와 무관하게 **항상** 먼저 쓴다 (기획 원칙 · 증거 원본)

---

## 7. 예시 — 한 과제의 왕복

```
POST /works                    {title:"운영체제 과제 3", ai_policy:"allowed"}      → {id:"W1"}
POST /works/W1/sessions        {id:"7f3a…", device:{os:"win"}, started_at:"…15:00:02+09:00"}
POST /sessions/7f3a…/events    {events:[session_start, window, keys, copy, paste, …]}   × 여러 번
POST /sessions/7f3a…/context   {items:[{kind:"ai_question", …}, {kind:"ai_answer", …}]}
POST /sessions/7f3a…/end       {ended_at:"…15:42:15+09:00", chain_len:128, root:"e71c…"}
                               → {verified:true}
GET  /works/W1/summary         → 요약 1장 데이터
POST /works/W1/links           {links:[{context_id:"c12", state:"confirmed", kind:"edited"}]}
POST /works/W1/redactions      {items:[{context_id:"c07"}]}
POST /works/W1/share           → {token:"s_9a2f…", url:"https://…/share/s_9a2f…"}
GET  /share/s_9a2f…            ← 교수가 연다 (로그인 없이)
```

---

## 8. 열어 둔 것

| 질문 | 제안 |
|---|---|
| heartbeat를 DB에 전부 넣나 | 안 넣고 "마지막 heartbeat 시각"만 갱신. 공백은 이걸로 계산 |
| batch 크기 | 50건 / 5초 |
| 세션 id | 클라이언트 UUID (오프라인 때문) |
| 지연 수신 기준 | 이벤트 ts 와 서버 received_at 차이 5분. 숨기지 않고 "지연 수신 구간"으로 표시 |
| `end` 시 체인 불일치 | 409 반환하되 세션은 "봉인 실패"로 남김. 조용히 덮어쓰지 않음 |
| **문장 유사도 임계값** | **열려 있음 — 10월 1주 테스트로 정한다.** 기준: 고치거나 합쳐 넣은 AI 답 10개 중 8개 이상 짝짓기. 못 미치면 문단 단위 |
| **공유 링크 만료** | 기본 14일 제안. 학생이 언제든 DELETE 로 끊을 수 있어야 함 |
| AI 공급자 (선택 요약만) | GPT-5.6 Luna. `core/llm.py` 어댑터. **기본은 규칙 기반이라 호출 자체가 없다** |

---

## 9. 서버 구현 메모

### 반드시 지킬 것

1. **해시는 `3-코드/core/chain.py` 를 import 해서 쓴다.** 서버에서 다시 짜지 않는다. 두 곳에서 계산하면 영원히 안 맞는다.
2. **응답 모양을 바꾸지 않는다.** `dev_receiver.py` 와 같은 키·같은 타입.
3. **멱등** — 같은 `(session_id, event id)` 가 다시 오면 세지 않고 200. 오프라인 큐가 재전송하므로 중복은 정상이다.
4. **`/share/{token}` 은 어떤 쓰기도 하지 않는다.** 읽기 전용이고, 인증이 없으므로 토큰이 곧 권한이다.

### 저장할 것 (DB)

| 테이블 | 왜 필요한가 |
|---|---|
| `users` `works` `devices` | 계약 1·2절. **`works.ai_policy` 추가 (v2.0)** |
| `sessions` | 세션 메타 + `root` · `verified` · `sealed_at` · `last_heartbeat_at` |
| `events` | **기본키 `(session_id, id)`** · 원본 JSON 보관 |
| `batches` | **지연 수신 판정용.** 배치마다 `received_at` 과 `chain_head` |
| `contexts` | AI 대화 기록. 길이 상한 없앰 |
| **`links`** | **신규** — 연결 확인 결과. `rejected` 도 지우지 않고 남긴다 |
| **`redactions`** | **신규** — 가린 항목. 내용이 아니라 "가렸다는 사실"만 |
| **`shares`** | **신규** — 공유 토큰 · 만료 · 취소 |
| ~~`reports`~~ | **폐기** — Learning Report 기능 삭제 |

> **이벤트 `id` 는 세션 안에서만 고유합니다** (`evt_000001` 이 세션마다 다시 시작).
> DB 기본키를 `id` 하나로 잡으면 두 번째 세션에서 충돌합니다. → **기본키 = `(session_id, id)` 복합키.**

### 참고 서버와 의도적으로 다른 곳 (1군데)

`duplicates` 수 — 참고 서버는 메모리에 id 를 들고 있어 **heartbeat 까지** 중복으로 셉니다.
실제 서버는 heartbeat 를 **DB 에 저장하지 않으므로** 중복으로도 세지 않습니다.
같은 배치를 두 번 보내면 참고 서버는 19, 실제 서버는 18 을 돌려줍니다.
`3-코드/server/test_contract.py` 가 이 차이를 알고 검사합니다.

### 언제 만드나

| 계약 | 언제 |
|---|---|
| 1·2·3절 (인증 · Work · 세션 · 이벤트 · 봉인 · 조회) | **완료** — `ai_policy` 만 추가하면 됨 |
| 4절 AI 대화 기록 | **완료** — 403 제거 · 길이 상한 제거만 |
| 5절 요약 1장 (`/summary`) | 10주 |
| 5절 연결 · 가리기 (`/links` · `/redactions`) | 11주 |
| 5절 공유 링크 (`/share` · `GET /share/{token}`) | 11주 |
| 5절 대화 가져오기 (`/import`) | 추가 과제 D — 필수 기능 뒤 |

**10/7 첫 연결에 필요한 것은 3절뿐**이고, 그건 이미 있습니다.
