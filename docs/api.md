# Trace API 계약 ③ (확정본)

**2026-09-21 확정** · B 초안(9/20) → A 검토 → 이 문서가 기준입니다.
바꿀 때는 **상대에게 먼저 말하고** 이 파일을 고칩니다. 코드가 아니라 **이 문서가 기준**입니다.

> 이 계약이 있어서 **A는 수집기 없이 서버를, B는 서버 없이 수집기·화면을** 만들 수 있습니다.
> 참고 구현은 `3-코드/collector/dev_receiver.py` (메모리 저장),
> 실제 서버는 `3-코드/server/` (DB 저장) — **둘은 같은 응답을 내야 합니다.**

## A 검토 결과 (9/21)

초안을 맥에서 실제로 돌려 확인했습니다. **구조·형식은 그대로 갑니다.** 고친 곳은 아래 한 군데뿐입니다.

| | 내용 |
|---|---|
| ✅ 확인 | 참고 서버 왕복 성공 — 세션 생성 201 · batch `verified:true` · 봉인 `verified:true` · 조회 session.json |
| ✅ 확인 | **변조 탐지 동작** — 이벤트의 `keys.count` 를 42→999 로 고쳐 보냈더니 `verified:false` (server_head 불일치) |
| ✅ 확인 | 골든 픽스처 통과 — 이벤트 38건 → root `4b1b92beae4e5c03…` |
| 🔧 **수정 1곳** | **이벤트 `id` 는 세션 안에서만 고유합니다** (`evt_000001` 이 세션마다 다시 시작). DB 기본키를 `id` 하나로 잡으면 두 번째 세션에서 충돌합니다. → **기본키 = `(session_id, id)` 복합키**. 멱등 판정도 이 쌍으로 합니다. |

---

## 0. 공통

- Base: `https://<host>/api` (개발: `http://127.0.0.1:5000/api`)
- 인증: `Authorization: Bearer <token>` (로그인 후). 수집기는 최초 1회 로그인 토큰을 `config.json`에 저장
- 시각: ISO 8601, 타임존 포함 (`2026-09-19T15:10:01+09:00`)
- id: **클라이언트가 만든다** (UUID v4). 오프라인에서도 세션·이벤트를 만들 수 있어야 하므로. 서버는 받은 id를 그대로 저장, 중복이면 무시(멱등)
- 오류: `{"error":"code","message":"..."}` · 400 형식 오류 · 401 인증 · 404 없음 · 409 중복/상태 충돌

---

## 1. 인증 (A)

```
POST /auth/login        {email, password}           → {token, user:{id, name}}
GET  /me                                             → {id, name, works:[…]}
```

## 2. Work — 하나의 과제·작업 단위 (A)

```
POST /works             {title, mode:"learn"|"proof"}          → {id, title, mode, created_at}
GET  /works                                                      → [{id, title, mode, sessions:n, last_at}]
GET  /works/{id}                                                 → {id, title, mode, sessions:[{id, start, end, dur, events, sealed}]}
```
Work의 `mode`는 고정. 한 Work = 한 모드 (가이드 결정: 한 세션에 두 모드 동시 없음).

## 3. Session — 수집기가 켜져 있던 한 번 (A 저장 · B 전송)

```
POST /works/{work_id}/sessions
  요청  {id:"<uuid>", mode, device:{name, os:"win"|"mac", collector_version}, started_at}
  응답  {id, work_id, mode, started_at}              201 · 이미 있으면 200 (멱등)

POST /sessions/{id}/events                            ← 수집기 batch (B)
  요청  {events:[ <이벤트 한 줄> … ], chain_head:"<sha256>", chain_len:n}
        50건 이하 · 5초마다 · 순서대로 · chain_head = 이 배치 마지막 이벤트까지 PC에서 계산한 해시
  응답  {accepted:n, duplicates:n, last_id:"evt_…", verified:true|false, server_head:"<sha256>", received_at}
  · 이벤트 한 줄 = 계약 ① (trace/README.md 4번). 서버는 id 중복이면 세지 않고 200
  · 서버는 받은 이벤트로 체인을 **재계산**해 chain_head 와 비교. 다르면 verified:false + 세션에 "무결성 오류" 표시 (조용히 넘기지 않음)
  · 서버는 배치의 received_at 을 저장. 이벤트 ts 와 received_at 차이가 5분 넘으면 그 구간은 "지연 수신"으로 표시 (증명서에 그대로 나옴)
  · heartbeat 도 보내되 DB엔 저장 안 함 — 세션의 last_heartbeat_at 만 갱신 (공백 계산용)

POST /sessions/{id}/end                               ← 봉인 (B가 로컬 체인 완성 후)
  요청  {ended_at, chain_len:128, root:"<sha256 hex>"}
  응답  {id, ended_at, sealed_at, root, verified:true|false, late_batches:n, anchor:{status:"pending"|"done", provider:"opentimestamps", submitted_at}}
  · 서버는 전체 체인을 다시 계산해 root 일치 여부를 `verified`에. 불일치면 409 + {server_root} 이고 세션은 "봉인 실패"로 남는다
  · 앵커(OpenTimestamps) 제출은 서버가. 확인은 보통 1시간 → anchor.status 가 done 으로 바뀌면 트레이 알림
  · 학생 PC에도 같은 체인·루트가 남는다 → proof.json + .ots 만으로 서버 없이 검증 가능

GET  /sessions/{id}                                   ← 화면 (B)
  응답  = 계약 ② session.json 구조 그대로
        {id, work_id, mode, date, start, end, dur, minutes, sealed_at, anchor, root,
         segments[], typed[], deleted[], pastes[], undos[], chain[], stats{}}
  · derive(events) 결과를 서버가 만든다 (4주차 이관). 그 전엔 B가 로컬 derive로 같은 구조를 만들어 화면 개발

GET  /sessions/{id}/events?after=<evt_id>&limit=500   ← 체인 원본 화면 · 디버그
  응답  {events:[…], next:"evt_…"|null}
```

## 4. Proof (A · 7~8주차)

```
GET  /sessions/{id}/certificate                       → {certificate_id, work_id, session_id, start, end, events, apps:[…], root, sealed_at, anchor:{…}, verify_url}
GET  /sessions/{id}/certificate.pdf                   → PDF 1장 (목업 11)
GET  /sessions/{id}/proof.json                        → {events:[…], chain:[…], root}   ← 검증 파일
GET  /sessions/{id}/proof.ots                         → OpenTimestamps 증명 바이너리
POST /verify                                          ← 검증자 웹 (목업 12) · 인증 불필요
  요청  multipart: proof.json + proof.ots
  응답  {chain_ok, root, root_matches, anchor:{block, time}, events:n}
```

## 5. Learn — Context · Report (7~11주차)

```
POST /sessions/{id}/context                           ← 브라우저 확장 · VS Code 확장 · Office 모듈 (B) · Learn 모드에서만
  요청  {items:[{id, ts, source:"browser"|"vscode"|"office", kind, text(≤500자), meta:{domain?, url?, file?, line?, app?}}]}
        kind (browser · Must):   ai_question | ai_answer_excerpt | selection | page
        kind (vscode  · Should): error | diff | run_result | selection
        kind (office  · 구현됨): diff | paste_at | save_stats      (Word · PowerPoint, COM 자동화 · meta: app, file, where, chars, words, slides, removed_chars)
  응답  {accepted:n}
  · Proof 세션에 보내면 403. 서버도 저장하지 않는다
  · 항목별 토글이 꺼져 있으면 아예 안 보냄 (목업 17). 시간이 부족하면 browser 까지만 구현

GET  /sessions/{id}/report                            ← 리포트 (Learn 만). **없으면 이때 생성한다 — 학생이 열 때** (9/21 결정)
  응답  {status:"ready", topics:[…], struggles:[…], process:[…], points:[…], todo:[…], generated_at, provider, runs}
  · 세션 종료 시 자동 생성하지 않는다. 안 여는 세션엔 AI 비용을 쓰지 않기 위해 (Learn 비용의 절반 가까이 절감)
  · AI 호출은 서버만 한다 (core/llm.py 참고). 키는 서버 환경변수. Proof 세션이면 403, AI 실패면 502
  · 보내는 것: 세션 id · flow · 맥락. 학생 이름·계정은 보내지 않는다
POST /sessions/{id}/report                            ← 다시 생성 (첫 생성 포함 세션당 3회 · 초과 429)
POST /sessions/{id}/chat                              ← Side Chat 한 턴 (Learn 만 · 세션당 30회)
  요청  {selection:text, question}                    응답 {answer, turns}
  · 대화는 세션 맥락(kind:"chat")으로도 남아 리포트의 "추가 학습" 에 반영된다
```

---

## 6. 수집기 쪽 동작 (B가 지킬 것)

1. 시작: `POST /works/{w}/sessions` (오프라인이면 큐에 넣고 진행)
2. 이벤트가 생길 때마다 **PC에서 체인에 넣는다** (hᵢ = SHA256(hᵢ₋₁ ‖ ts ‖ type ‖ summary)). 로컬 파일에도 해시가 같이 남는다
3. 매 5초 또는 50건: `POST /sessions/{id}/events` batch + 그 시점의 chain_head. 실패 → `queue.jsonl` 보관, 10초 후 재시도, 성공 시 **순서대로** 재전송
4. 종료: 로컬 체인 완성 → `POST /sessions/{id}/end`. 오프라인이면 큐 맨 뒤에 넣고 다음 실행 때 전송
5. 로컬 `events-날짜.jsonl` 은 서버와 무관하게 **항상** 먼저 쓴다 (기획 원칙 · 증거 원본)

## 7. 예시 — 한 세션의 왕복

```
POST /works/W1/sessions        {id:"7f3a…", mode:"proof", device:{os:"win"}, started_at:"…15:00:02+09:00"}
POST /sessions/7f3a…/events    {events:[session_start, window, heartbeat, keys, …]}   × 여러 번
POST /sessions/7f3a…/end       {ended_at:"…15:42:15+09:00", chain_len:128, root:"e71c…"}
                               → {verified:true, anchor:{status:"pending"}}
GET  /sessions/7f3a…           → session.json (화면)
GET  /sessions/7f3a…/certificate.pdf
```

---

## 8. 열어 둔 것 (회의에서)

| 질문 | 제안 |
|---|---|
| heartbeat를 DB에 전부 넣나 | 안 넣고 "마지막 heartbeat 시각"만 갱신. 공백은 이걸로 계산 |
| batch 크기 | 50건 / 5초. 키 이벤트가 10초마다 1건이라 평소엔 1~3건 |
| 세션 id | 클라이언트 UUID (오프라인 때문). 서버 발급으로 바꾸면 오프라인 시작이 불가 |
| 지연 수신 기준 | 이벤트 ts 와 서버 received_at 차이 5분. 오프라인 큐 재전송이 여기 걸리는데, 숨기지 않고 "지연 수신 구간"으로 표시 |
| Learn Context 최대 길이 | 500자. 그 이상은 확장이 잘라서 보냄 |
| `end` 시 체인 불일치 | 409 반환하되 세션은 "봉인 실패"로 남김. 조용히 덮어쓰지 않음 |
| AI 공급자 | **Qwen API (알리바바 Model Studio · 국제/싱가포르 엔드포인트) — 교수 결정 9/20.** `core/llm.py` 어댑터라 Claude 로 바꿔 비교 가능. 키 없으면 fake |
| AI 호출 상한 | 리포트 세션당 3회 · Side Chat 세션당 30회. 서버가 셈 |


---

## 9. A 구현 메모 (9/21)

### 반드시 지킬 것

1. **해시는 `3-코드/core/chain.py` 를 import 해서 쓴다.** 서버에서 다시 짜지 않는다.
   두 곳에서 계산하면 영원히 안 맞는다. (B 가 세 번 강조한 것이고 맞는 말이다)
2. **응답 모양을 바꾸지 않는다.** `dev_receiver.py` 와 같은 키·같은 타입.
   B 의 수집기와 화면이 이 모양을 보고 만들어졌다.
3. **멱등** — 같은 `(session_id, event id)` 가 다시 오면 세지 않고 200.
   오프라인 큐가 재전송하므로 중복은 정상이다.

### 저장할 것 (DB)

| 테이블 | 왜 필요한가 |
|---|---|
| `users` `works` `devices` | 계약 1·2절 |
| `sessions` | 세션 메타 + `root` · `verified` · `sealed_at` · `last_heartbeat_at` |
| `events` | **기본키 `(session_id, id)`** · 원본 JSON 보관 |
| `batches` | **지연 수신 판정용.** 배치마다 `received_at` 과 `chain_head` 를 남긴다 |

`batches` 를 빼먹기 쉬운데, 계약 3절의 **"5분 넘게 늦은 구간은 지연 수신으로 표시"** 가 이 표 없이는 안 됩니다.

### 참고 서버와 의도적으로 다른 곳 (1군데)

| | |
|---|---|
| `duplicates` 수 | 참고 서버는 메모리에 id 를 들고 있어 **heartbeat 까지** 중복으로 셉니다. 실제 서버는 계약 3절대로 heartbeat 를 **DB 에 저장하지 않으므로** 중복으로도 세지 않습니다. 같은 배치를 두 번 보내면 참고 서버는 19, 실제 서버는 18 을 돌려줍니다. |

`duplicates` 는 로그용 숫자이고 멱등 보장(중복 저장 안 함)은 양쪽 같습니다.
`3-코드/server/test_contract.py` 가 이 차이를 알고 검사합니다.

### 아직 없는 것 (참고 서버에도 없음 · A 가 만들 것)

| 계약 | 언제 |
|---|---|
| 1절 인증 (`/auth/login` · `/me`) | 4주차 |
| 2절 Work CRUD (`POST /works` · `GET /works` · `GET /works/{id}`) | 4주차 |
| 4절 Proof (증명서 · proof.json · .ots · `/verify`) | 7~8주차 |
| 앵커 실제 제출 (OpenTimestamps) | 7주차 |

3주차 관통에 필요한 것은 **3절(세션·이벤트·봉인·조회)뿐**입니다. 그건 참고 서버에 이미 있습니다.
