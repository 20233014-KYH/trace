# Trace API 계약 ③ (확정본 v2.1 · 9/30 AI 허용 과제만)

**2026-09-28 개정** · v1.0(9/21 확정) → 기획 전면 개정(`1-기획/5-기획 수정사항 (2026-09-28).md`) 반영.
바꿀 때는 **상대에게 먼저 말하고** 이 파일을 고칩니다.

> 🆕 **10절 — 원문 위치 결정(원문은 학생 PC · 서버엔 해시)에 따른 테이블 설계 초안 (10/3 · 김용현).** 박상진 확인 후 확정하면 4·5절을 이 기준으로 고친다. 코드가 아니라 **이 문서가 기준**입니다.

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
| **수정** | `POST /works {title, mode:"learn"\|"proof"}` | `POST /works {title, ai_scope?}` — **v2.1(9/30):** `ai_policy` 삭제, AI 금지 과제는 대상 아님. `ai_scope` = 교수가 허용한 범위 메모(선택) |
| **수정** | 세션 생성 요청에 `mode` | **`mode` 제거** — 세션에 모드 개념이 없음 |
| **수정** | `/context` 는 Learn 세션에서만 (Proof 면 403) | **항상 받는다.** 403 없음. 의미도 "학습 맥락" → **"AI 대화 기록"** |
| **추가** | — | `/works/{id}/summary` · `/links` · `/redactions` · `/share` · `GET /share/{token}` · `/import` |

**서버 구현자에게:** `3-코드/server/app.py` 의 `_learn만()` 헬퍼와 `report`·`chat` 라우트를 지우고,
`db.Work` 에 `ai_scope` 컬럼(선택 · 자유 텍스트)을 더하고, `db.Sess.mode` 는 남기되 쓰지 않습니다(옛 데이터 호환).

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

**과제 목록·과제 조회·`/me`·과제 만들기/고치기는 언제나 로그인이 필요합니다 (10/7 · 배포 전 · 로그인 없으면 401).** 기록기가 쓰는 주소(세션·이벤트·봉인·맥락)는 아래처럼 **아직 강제하지 않습니다.** 기록기가 아직 토큰을 보내지 않아
여기서 401 을 던지면 10/7 관통 테스트가 깨집니다.

```bash
python server/app.py                        # 인증 선택 (기본)
TRACE_REQUIRE_AUTH=1 python server/app.py   # 인증 강제
```

---

## 2. Work — 하나의 과제

```
POST /works        {title, ai_scope?}                         → {id, title, ai_scope, created_at}
GET  /works                                                    → [{id, title, ai_scope, sessions:n, last_at}]
GET  /works/{id}                                               → {id, title, ai_scope, sessions:[{id, start, end, dur, events, sealed}]}
PATCH /works/{id}  {title?, ai_scope?}                         → {id, title, ai_scope}
```

- **`ai_scope`** 는 교수가 허용한 범위를 적는 선택 메모다(예: "코드 설명·디버깅만 허용"). 내역서 맨 위에 그대로 찍을 뿐, 서버가 이걸로 판단하지 않는다.
- 대상은 **AI 허용 과제**뿐이다 (9/30). 과제 유형(`ai_policy`)은 없다.
- 내역서를 내기 직전에 고칠 수 있으므로 `PATCH` 가 필요하다.
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
  응답  {work:{id, title, ai_scope}, sessions:n, span:{start, end}, active_min,
         typed_chars, pasted:{count, from_ai:n, from_other:n},
         ai:{tools:[…], questions:n, links:{verbatim:n, edited:n}},
         unsourced:[{start, end, chars}],            ← "출처 기록 없음" 구간
         chain:{verified:true|false, sealed_sessions:n}}
  · 여기에 점수·확률·등급·퍼센트 유사도는 **없다** (원칙 1)

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
  응답  {work:{title, ai_scope}, summary:{…}, links:[{ai_answer, result, kind}], 
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
POST /works                    {title:"운영체제 과제 3", ai_scope:"코드 설명·디버깅만 허용"} → {id:"W1"}
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
| `users` `works` `devices` | 계약 1·2절. **`works.ai_scope` 추가 (v2.1 · 선택)** |
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
| 1·2·3절 (인증 · Work · 세션 · 이벤트 · 봉인 · 조회) | **완료** — `ai_scope` 만 추가하면 됨 |
| 4절 AI 대화 기록 | **완료** — 403 제거 · 길이 상한 제거만 |
| 5절 요약 1장 (`/summary`) | 10주 |
| 5절 연결 · 가리기 (`/links` · `/redactions`) | 11주 |
| 5절 공유 링크 (`/share` · `GET /share/{token}`) | 11주 |
| 5절 대화 가져오기 (`/import`) | 추가 과제 D — 필수 기능 뒤 |

**10/7 첫 연결에 필요한 것은 3절뿐**이고, 그건 이미 있습니다.

---

## 10. ★ 초안 (10/3 · 김용현) — 원문은 학생 PC, 서버엔 해시만: 테이블 설계

> **상태: 초안.** 로드맵 이번 주 김용현 4번. 박상진 확인 후 확정 → 그때 4·5절을 이 기준으로 고친다.
> **10/8 이름 결정 (박상진 합의):** 학생 화면의 버튼은 "제출" 대신 **"내역서 만들기"**. 누른다고 교수에게 가지 않고(학생이 링크를 따로 냄), 과제 밖 결과물(공모전·자소서 등)에도 맞게. 코드 이름도 `submissions` → **`statements`** (AI 활용 내역서).
> **전제 (10/1 결정 · 수정사항 8절 제안 채택):** 실시간으로 서버에 가는 건 해시·횟수·시각뿐 / 원문은 학생 PC / 내역서를 만들 때 학생이 확인·가린 **연결된 부분의 원문만** 서버로.

### 10-1. 핵심 — "원문은 늦게 와도, 기록 당시 그대로인지 확인된다"

원문을 나중에 받으면 "그동안 고친 것 아닌가?" 가 문제다. 그래서 **기록하는 순간 원문의 해시만 체인에 넣는다.**
내역서를 만들 때 원문이 오면 서버가 같은 함수로 해시를 계산해 체인에 있는 해시와 비교한다.

```
기록 중 (실시간)   PC: 원문 저장 + 해시 계산 → 체인 이벤트 ai_msg{hash, len}  ──▶  서버: 해시만 받음
내역서 만들 때     PC: 학생이 확인·가린 연결의 원문  ──▶  서버: sha256_text(원문) == 체인의 hash ?
                                                              같음 → "기록 당시 그대로" · 다름 → "조작됨"
```

→ 원칙 4(확인 전엔 밖으로 안 나감)와 원칙 5(해시 체인)를 **둘 다** 지킨다.

### 10-2. 무엇이 어디에 있나

| 데이터 | 학생 PC | 서버 (실시간) | 서버 (내역서 뒤) |
|---|---|---|---|
| 창·키 횟수·복사 해시 등 이벤트 | ✅ `events-날짜.jsonl` | ✅ `events` (지금 그대로) | |
| **AI 질문·답 원문** | ✅ | **해시만** (`ai_msg` 이벤트) | 확인된 연결에 쓰인 것만 |
| **문서 버전 (결과물 글)** | ✅ | **해시만** (`file.content_hash` · `doc_save.hash`) | 연결된 부분 발췌만 |
| 연결 제안 계산 (`core/match.py`) | ✅ | ✗ | |
| 학생 결정 (맞다 / 아니다) | ✅ | **해시만** (`link_decision` 이벤트) | 결정 목록 — "아니다" 는 원문 없이 |
| 가림 | ✅ | ✗ | "가림" 표시만 |
| 자동 가리기 (키·이메일·전화 모양) | ✅ **원문을 저장하기 전에** | | |

### 10-3. 체인에 새로 넣는 이벤트 3개 (계약 ① · ⚠️ 박상진 합의 필요)

```
ai_msg         {tool, conv, turn, role:"question"|"answer", len, hash}       확장·Claude Code 기록·대화 내보내기에서
doc_save       기존 {app, file, chars, words, slides} + hash                 Office 저장 때 글 전체의 해시
                                                                             (텍스트 파일은 file.content_hash 가 이미 있음)
link_decision  {answer_hash, result_hash, kind:"exact"|"edited", decision:"confirmed"|"rejected"}   학생이 고른 순간
```

- **해시 함수는 하나만:** 기록기의 `sha256_text()` (`3-코드/collector/collector.py` 69행 · `"sha256:" + SHA-256(UTF-8)`) 를 `core/` 로 옮겨 서버도 import 한다. 해시를 두 곳에서 짜지 않는다 — `chain.py` 와 같은 원칙.
- **자동 가리기 → 그다음 해시.** 그래야 API 키가 PC 파일에도 안 남고, 내역서를 만들 때 검증도 맞는다.
- **⚠️ `core/chain.py` 의 `summary()` 에 새 종류 3줄을 추가해야 한다.** 모르는 종류는 마지막 줄 `return ""` 로 요약이 빈 칸이 돼서, `hash` 가 체인으로 보호되지 않는다. **기존 줄은 안 건드리므로** 골든 픽스처·지난 기록의 해시는 그대로다 (추가 후 `tests/test_derive.py` 로 확인).

### 10-4. 서버 테이블

**그대로:** `users` `tokens` `works` `devices` `sessions` `events` `batches`

**새로 5개**

`statements` — 한 과제의 **내역서 한 번** (학생이 "내역서 만들기"를 누른 한 번). 다시 만들면 새 줄, 마지막 것이 유효.

| 칸 | 뜻 |
|---|---|
| `id` · `work_id` · `created_at` | |
| `ai_scope` | 만들 당시 허용 범위 메모의 사본 |
| `sentence` · `sentence_edited` | GPT 요약 문장 (학생이 켰을 때만) · 학생이 고친 최종 문장 |
| `verified` | 올라온 원문이 **전부** 체인 해시와 맞는가 |

`messages` — 내역서에 담긴 AI 질문·답 원문 (**확인된 연결에 쓰인 것만**)

| 칸 | 뜻 |
|---|---|
| `id` · `statement_id` · `session_id` | |
| `event_id` | 이 원문의 해시가 있는 체인 이벤트 (`ai_msg`) |
| `tool` · `role` · `ts` · `text` | ChatGPT·Claude·Claude Code… · question/answer · 시각 · 원문 |
| `match` | `sha256_text(text)` 가 체인의 해시와 같은가 (다르면 화면에 "조작됨") |

`links` — 학생의 결정 (**맞다·아니다 모두**)

| 칸 | 뜻 |
|---|---|
| `id` · `statement_id` | |
| `answer_msg_id` · `question_msg_id` | 맞다일 때만 — 위 `messages` 를 가리킴 |
| `answer_hash` · `result_hash` | 언제나 (아니다여도) |
| `result_text` | 결과물 발췌 — **맞다일 때만** |
| `location` | 파일 · 문단(문서) 또는 줄 범위(코드) |
| `kind` · `origin` | exact/edited · auto(해시 일치)/suggested(비슷해서 제안) |
| `decision` · `decision_event_id` | confirmed/rejected · 체인의 `link_decision` |

→ "아니다" 는 원문 없이 해시·위치·결정만 남는다: **"제안했고 학생이 연결하지 않음" 은 남되 내용은 나가지 않는다.**

`redactions` — 가린 것: `id` · `statement_id` · `event_id` · `ts`. 내용은 서버에 아예 오지 않는다. 해시는 체인에 있으니 검증은 계속된다.

`shares` — 교수 확인 링크: `token`(기본키 · 무작위) · `statement_id` · `created_at` · `expires_at`(기본 14일) · `revoked_at`

**은퇴 예정 1개:** `contexts` — 원문을 실시간으로 받는 표. **이 결정과 반대 방향이다.**
이번 주 로드맵 김용현 3번(PR #19: `/context` 원문 전체 저장)도 같은 이유로 결정과 어긋난다 → **PC 저장이 생길 때까지(10/7 첫 연결 · 9주 시연 준비)만 임시 경로**로 쓰고, 내역서 경로가 생기면 끈다.

### 10-5. API (5절 대체안)

```
GET  /works/{id}/summary          ← 서버가 체인 이벤트로 센다 (core/summary.py · PC 가 보낸 숫자를 믿지 않음)   ✅ 10/8 구현
  응답  {work_id, sessions, sealed_verified, first_at, last_at, minutes, idle_minutes, typed, deleted, undo,
         pastes:{count, chars, from_ai_count, from_ai_chars, unknown_count, unknown_chars},   ← unknown = 출처 기록 없음
         ai:{questions, answers, history, tools:{도구: 수}, window_minutes, window_visits},
         links:{confirmed, rejected}, by_session:[…세션별 같은 칸 + id, sealed, verified]}
  · 로그인 · 내 과제만 · 비율·점수는 없다 (원칙 1) · 세션 하나의 숫자는 derive.py 그대로
  · 내역서를 만들 때 이 값을 statements.summary 에 함께 남긴다 (뒤에 세션이 늘어도 그 내역서 숫자는 그대로)
POST /works/{id}/statements       ← 내역서 만들기. 원문은 여기서 처음 서버로 온다   ✅ 10/8 구현 (server/app.py)
  요청  {ai_scope?, sentence?,
         messages:   [{session_id, event_id, text}],                       ← 이벤트 id 는 세션 안에서만 고유 → 둘 다
         links:      [{answer_hash, question_hash?, result_hash, result_text?,
                       location, kind, origin, decision:"confirmed"|"rejected", decision_event_id?}],
         redactions: [{session_id, event_id}]}
  응답 201  {id, verified, problems:[{…, why}], sessions:[{id, sealed, verified}],
             counts:{messages, links_confirmed, links_rejected, redactions}}
  · 로그인 필요 · 내 과제만 (주인 없는 과제도 404 — 과제 이름은 추측할 수 있어서)
  · 원문마다 sha256_text(text) 를 체인 ai_msg.hash 와 비교. 다르면 저장은 하되 match=false — 숨기지 않는다
  · tool·role·ts 는 보낸 값이 아니라 체인 이벤트의 값 (history = 이전 대화도 그대로 따라온다)
  · 연결은 해시로 원문을 가리킨다: confirmed 면 answer_hash 가 위에서 확인된 답이어야 한다
  · rejected 의 result_text 는 받아도 버린다 (원문 없이 해시·위치·결정만)
  · 가린 이벤트의 원문을 같이 보내면 400 · 한 요청 5MB · 원문 하나 256KB
  · verified = 문제 0개 (원문이 나온 세션이 전부 봉인·검증됐는가 포함)
  problems.why:  not_in_work · not_in_chain · hash_mismatch · answer_not_verified · question_not_verified
                 · result_hash_mismatch · redaction_not_in_chain · session_not_sealed · session_not_verified
GET    /works/{id}/statements/latest          ← 학생용 (아니다·가림의 위치, 원문별 ok 까지 · 공유 링크 목록)
POST   /statements/{id}/share    {expires_in_days? 1~90, 기본 14}  → 201 {token, path, page, url, pdf_url, expires_at}
                                  ← url = 교수에게 보내는 화면 주소 https://…/s/{token} (서버가 HTML 을 내줌 · 10/8)
DELETE /shares/{token}                        ← 학생이 끊기
GET    /share/{token}/pdf         ← AI 활용 내역서 1장 PDF (링크·QR 포함 · 링크와 같은 열쇠 · 10/8)
GET    /share/{token}             ← 교수용 · 인증 없음 · 읽기 전용 · 없음·끊음·만료는 똑같이 404
  응답  {work:{title}, ai_scope, sentence, verified, problems:[{why}], summary,
         links:[{question, answer:{text, tool, ts, history, ok}, result:{text, location}, kind, origin}],
         rejected:n, redacted:n, created_at, expires_at}
  · 교수 화면엔 summary 도 담긴다 — 단 세션·이벤트 id 는 빼고 (id 를 알면 /sessions/{id}/events 로 기록 전체가 읽힘)
  ✳ 아직: link_decision 이벤트 확인 (기록기가 아직 안 냄)
```

| 5절 (9/28) | 이 초안 |
|---|---|
| `GET /works/{id}/summary` | 그대로 — 단 **체인 이벤트로** 센다 |
| `POST /works/{id}/links` | 내역서 만들기의 `links` 로 합침 (결정은 PC 에서 일어나므로) |
| `POST /works/{id}/redactions` | 내역서 만들기의 `redactions` 로 합침 |
| `POST /works/{id}/share` | `POST /statements/{id}/share` (무엇을 공유하는지가 "내역서 한 번" 이므로) |
| `GET /share/{token}` | 그대로 |
| `POST /works/{id}/import` (추가 과제 D) | **PC 에서 읽는다.** 대화 내보내기 파일은 원문 덩어리라 서버로 보내지 않는다 |

### 10-5-0. 내역서 v3 (10/10 박상진 · ✅ 10/11)

- 요청에 `explain_use`("AI 를 어디에 썼고, 무엇은 직접 했나요?") · `explain_check`("AI 답을 고르거나 고칠 때 어떻게 확인했나요?") — 각 150자 (넘으면 400). 비우면 화면에 "학생이 쓰지 않음"
- `ai_scope` 는 **학생이 넣었을 때만** — 과제 메모를 저절로 옮기지 않는다
- `messages[].model` — PC 기록의 모델 이름 (체인엔 없어 확인되지 않은 참고값) → 응답 `tools:[{tool, models}]` = 투명성 줄의 "도구(모델)"
- 요약에 `pastes.from_other_count/chars` (AI 아닌 곳에서 복사) · `days:[{date, minutes, segments:[{start,end}]}]` (날짜별 작업 막대 · 멈춤은 빈 틈)
- PDF·교수 화면: 투명성 한 줄(서버 일치 · 도구(모델) · 멈춤 · 가림 · 지운 기록) · 글을 쓴 과정(키보드로 친 글자 · 붙여넣은 글자 AI/다른 곳/출처 기록 없음 · 지운 글자 + 막대) · 질문 두 개 · QR 옆 두 줄

### 10-5-2. 교수 링크 출처 보기 · 작업 과정 · 잘 모르겠음 (10/12 · ✅)

내역서 만들기 요청에 더:
```
source?        { file, title, paragraphs:[{head, sents:[k]}], sentences:[{k, p, text, kind, group, q?, unsure?, rejected?, paste?, proc?}],
                 questions:[{n, tool, model, ts, question|null, hidden, question_hash, answer:[{t,g,i}], answer_hash, uses:[k], paras}] }
                 ← 학생이 "출처 보기"를 켰을 때만 (기본 끔 · 10/11 설문 34명 중 문장 출처까지 괜찮다 5명).
                   PC 출처 보기(app/source.build)와 같은 자료 + 학생의 고름 (아니다 → 출처 없음 · 보류 → unsure · 가린 질문 → 원문 없이 hidden)
                   질문·답 원문(참고만 한 것 포함)은 messages 로도 와서 서버가 체인 해시로 맞춰 본다 → 교수 화면 question_ok · answer_ok
                 ★ 보고서 전문은 맞춰 볼 해시가 없다 · 살아 있는 링크가 없어지면(끊기 · 기간 끝 · 과제 지우기 · 새 내역서) 서버에서 지운다
show_process?  true 면 교수 링크에 작업 과정(기록 목록 by_session) — 기본 끔
unsure?        연결 확인에서 "잘 모르겠음"·안 고른 제안 수 (정수) — 원문 없이 개수만 → "판단을 보류한 제안 n개"
```
교수 화면 탭: **요약** · **출처 보기**(source 있을 때) · **질문 기준**(source 있으면 참고만 한 질문까지, 없으면 확인된 연결 묶음) · **작업 과정**(show_process)

### 10-5-3. 내역서 PDF v3 배치 · 일부 가림 (10/12 박상진 · ✅)

내역서 만들기 요청에 더 (모두 선택 · 없으면 예전처럼):
```
result_counts? { total, ai, other, edited, viewed, none }        ← v3 ③ 결과물에 들어간 것 — 보고서 문장 수 (PC 출처 보기가 셈 · 숫자만)
usage_counts?  { learn, fix, write }                              ← v3 ① 어떻게 썼나 — 질문 쓰임새 수 (PC 가 질문 글을 낱말 규칙으로 나눔 · 숫자만)
                                                                     learn 이해·자료 찾기 · fix 고치기·검토 · write 작성 (10/12 다섯 칸 → 셋 · 예전 키는 PDF 가 합쳐 그림)
flow?          [{ session_id, event_id, usage, used }] (최대 3)  ← v3 ② 학생이 고른 대표 질문 · 그 질문 원문이 messages 에 같이 와야 함 (없으면 400)
messages[].mask?  [[시작, 끝, 종류], …]                          ← 일부 가림: 서버는 원문 전체로 체인 해시를 맞춰 본 뒤 ⟦가림:종류⟧ 로 바꾼 글만 저장
                                                                     종류 = API키 · 비밀키 · 주민번호 · 카드번호 · 이메일 · 전화번호 · 직접 (collector/mask.py 와 같음)
```
응답 (학생용 · 교수용)에 `result_counts` · `usage_counts` · `flow:[{text, tool, usage, used, ok, masked}]` · 링크 질문·답의 `masked:[종류]`.
PDF (`server/statement_pdf.py`) = 머리 · 투명성 한 줄 → 글을 쓴 과정 | 언제 작업했나 → ① 쓰임새 칩 → ② 질문 흐름 → ③ 문장 수 + 예시 2개 → ④ 학생 설명 → QR.
연결 하나하나의 표는 PDF 에서 빼고 링크로 — **늘 한 장**.

### 10-5-4. 견본 주소 (10/12 · ✅)

```
GET /demo       → /s/demo                  교수 확인 화면 견본 (상단에 "견본 화면 · 지어낸 기록입니다")
GET /demo/pdf   → /api/share/demo/pdf      내역서 PDF 견본
```
토큰 `demo` 만 DB 대신 `server/demo_share.json` 을 그대로 준다 (expires_at 은 열 때마다 지금+14일). 실제 토큰은 32자라 겹치지 않음.
화면·PDF 를 고쳐 머지하면 같은 주소로 바로 확인 · 교수 인터뷰 때 보여 주기용. 견본 데이터를 바꾸려면 그 JSON 을 고친다.

### 10-5-5. 계정 고치기 (10/13 박상진 · ✅ · PC 앱 설정 › 계정)

```
GET   /api/me                → { id, name, email, works }        ← email 더함
PATCH /api/me                { name }  (1~40자)                    → { id, name } · 이미 낸 내역서는 그때 이름 그대로
POST  /api/auth/password     { password, new_password (8자 이상) } → { ok } · 지금 비번 틀리면 401 · 이 기기 토큰만 남기고 다른 기기는 로그아웃
```

### 10-5-1. 지우기 · 옮기기 · 잠깐 멈춤 (10/10 박상진 요청 · ✅ 10/11 구현)

```
DELETE /works/{id}        ← 과제 지우기 (로그인 · 내 과제). 이벤트·원문·연결·제목을 지우고 deleted_at 만 남긴다
                             → 이미 낸 링크: GET /share/{token} = 410 {error:"deleted", deleted_at, message:"학생이 10/12 에 지운 기록입니다"}
                             → 지운 과제로 기록기가 보내면 410
DELETE /sessions/{id}     ← 기록 하나 지우기. 요약·내역서에 "지운 기록 n개"(시각만)로 남는다. 더 보내면 410
PATCH  /sessions/{id}     ← 기록 옮기기 {work_id} — 내 과제끼리만. 과제 id 는 체인 요약에 없어서 "서버 기록과 일치" 그대로
```

**잠깐 멈춤** — 새 체인 이벤트 `pause_start` · `pause_end` (필드 없음 · `chain.summary` 는 idle 처럼 종류 이름만 — 기존 해시 그대로).
기록기는 멈춘 동안 아무것도 남기지 않는다 (창·키·복사·AI 질문·답·문서 변화 · PC 파일에도). 알약 ⏸.
요약: `minutes` = 처음~끝 − 멈춘 시간 · `pause_minutes` · `pauses`(횟수) · 세션별 `pauses:[{start,end}]` · `deleted_sessions:[{started_at, ended_at, deleted_at}]`

### 10-6. GPT 맥락 요약은 여기서 생긴다

"과제의 이 부분을 만들 때 어느 AI 에 어떻게 묻고 어떤 답을 받아 이렇게 썼는가" — 이 요약은 **내역서 만들기로 확인된 질문·답·결과가 서버에 생긴 뒤에만** 만들 수 있다.
사실은 `links`·`messages` 가 주고 GPT 는 문장만 다듬는다 · 학생이 켤 때만 · 결과는 학생이 확인·수정 (`sentence_edited`) ·
OpenAI 로 내용이 나가므로 **국외 이전 동의**가 필요하다. (설계 자리만. 구현은 10주)

### 10-7. 박상진과 정할 것

| # | 정할 것 | 제안 |
|---|---|---|
| 1 | 새 체인 이벤트 3개의 이름·필드 + `chain.py` 요약 3줄 추가 | 10-3 그대로 (`chain.py` 는 고치기 전 말하기 규칙) |
| 2 | `sha256_text()` 를 `core/` 로 옮기기 | `core/texthash.py` — 기록기·서버가 같이 import |
| 3 | PC 쪽 저장 형태 | `data/local.db` (SQLite) 에 `ai_messages` · `doc_versions` · `suggestions` · `redactions`. **서버는 내역서 요청 형식만 알면 되므로 PC 쪽은 박상진이 정함** |
| 4 | 결과물 "부분" 의 단위 | 문서 = 문단 · 코드 = 줄 범위 |
| 5 | 실시간 `/context` 를 끄는 시점 | PC 저장 + 내역서 경로가 돌아가는 날 |

### 10-8. 만드는 순서 (제안)

1. **같이** — 골든 픽스처에 `ai_msg` 이벤트 하나를 넣고, PC 와 서버가 같은 해시를 내는지부터 확인
2. **박상진** — 기록기 `_on_context` 를 "서버로 보냄" → "PC 에 저장 + `ai_msg` 이벤트" 로 · `link_decision` · `doc_save.hash`
3. **김용현** — 테이블 5개 + `POST /statements`(해시 검증) + 공유 3개 + 테스트 (10~11주, 로드맵 일정)

