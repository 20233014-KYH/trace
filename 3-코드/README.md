# Trace 코드 — 수집기 · 체인 · 참고 서버 · 뷰어

2026-09-20 · B 담당 영역. API 계약 ③(`../08_API 계약 초안.md`) 의 **수집기 쪽 동작이 전부 구현되어 있고**, `dev_receiver.py` 가 계약의 서버 쪽을 참고용으로 구현한다 (A 가 진짜 Backend 를 만들 때 기준).

```
collector.py ─ 이벤트 생성 ─ PC에서 체인 해시(core/chain.py) ─ events-날짜.jsonl (로컬 우선)
             └─ 5초/50건 batch + chain_head ─→ POST /api/sessions/{id}/events ─→ dev_receiver.py (재계산·대조·수신시각)
             └─ 서버 꺼지면 queue.jsonl 에 순서대로 보관 → 살아나면 재전송 (옛 세션은 옛 세션 id로)
             └─ 종료 시 POST /api/sessions/{id}/end (root) → 서버 재계산 → 검증 · 앵커 pending
derive.py  ─ jsonl 또는 서버 이벤트 → session.json (분당 집계 · 붙여넣기 해시 매칭 · stats)
viewer.html ─ session.json → "한눈에" 화면 (서버 없음)
```

**서버 없이 테스트** (아래 1절) 도 되고, **서버 켜고 테스트** (`0_서버시작.bat` 먼저) 도 된다.

## 0. 준비 (한 번)
- Windows 10/11 · Python 3.10+ (`python --version`)
- 이 폴더를 아무 데나 두고 `1_기록시작.bat` 더블클릭 → `.venv` 자동 생성 + 패키지 설치 (1~2분)
- conda 쓰면: `pip install -r requirements.txt` 후 아래 명령을 직접 실행해도 됨

## 1. 테스트 절차 (30분)

| 단계 | 할 일 | 확인 |
|---|---|---|
| 0 | (선택) `0_서버시작.bat` — 서버 쪽까지 보려면 | `Trace dev server http://127.0.0.1:5000/api` |
| 1 | `1_기록시작.bat` 실행 (`--dry-run` 이라 서버 없이 로컬만. 서버로 보내려면 bat 에서 `--dry-run` 을 지움) | 콘솔에 `session_start … h=84935f76`, 창 바꿀 때마다 `window [work] Code.exe …` |
| 2 | **20분 평소처럼 작업**: PDF/문서 읽기 → 코드나 글 쓰기 → 막히면 Claude/ChatGPT에 묻기 → 답 복사해서 붙여넣기 → 고치기 → 저장. 중간에 Ctrl+Z도 몇 번 | 콘솔에 `keys typed=12 deleted=2`, `copy`, `paste`, `undo` 가 찍힘 |
| 3 | 콘솔에서 Ctrl+C | `session_end` 후 종료 |
| 4 | `2_결과보기.bat` 실행 | 콘솔에 요약 숫자, 뷰어 창이 열림 |
| 5 | 뷰어에 `data\session.json` 끌어다 놓기 | 직접 입력 % / 붙여넣기 % · 레인 그래프 · 핵심 순간 |

명령으로 직접 하면:
```bat
.venv\Scripts\python.exe collector\collector.py --dry-run
.venv\Scripts\python.exe core\derive.py "data\events-*.jsonl" --out data\session.json
start ui\viewer.html
```
데이터 없이 화면만 보려면 뷰어의 [샘플 열기] 또는 `data\sample_session.json`.

## 2. 보고해 줄 것 (이게 테스트의 결과물)

1. `data\session.json` 파일 자체 (기획 쪽에서 목업북 DATA에 넣어봄)
2. 뷰어 스크린샷 1장
3. 아래 질문에 한 줄씩
   - 그래프의 초록(직접 입력) 리듬이 실제로 친 느낌과 맞나? 붙여넣은 순간에 빨강/주황이 맞게 찍혔나?
   - AI 창에서 복사한 걸 붙였을 때 **빨강(AI 일치)** 으로 나왔나? 아니면 주황? (→ `domains.json`/화이트리스트 문제)
   - 키 훅이 켜져 있는 걸 알고 작업하니 어떤 기분이었나? (파일럿 학생 반응 예측용 — 솔직하게)
   - 잘못 잡힌 것: 창 분류가 틀린 앱, 안 잡힌 이벤트, 콘솔 에러
4. 콘솔 에러가 있었으면 그 줄 복사

## 3. 무엇이 어디에

| 파일 | 역할 | 상태 |
|---|---|---|
| `collector/collector.py` | 상주 수집기. 활성 창 1초 폴링 · 클립보드 길이+해시 · 유휴 · heartbeat. **이벤트마다 체인 해시(h)** · 로컬 jsonl 먼저 → 5초/50건 batch POST · 오프라인 큐 · 종료 시 봉인 요청. `--mode proof|learn --work W1 --seconds N(테스트)` | 동작 확인 (온라인 봉인 · 오프라인 큐 · 재전송 · 4xx 거절 처리) |
| `core/chain.py` | 해시 체인 — 수집기·derive·서버가 **같은 함수**를 쓴다. hᵢ = SHA256(hᵢ₋₁‖ts‖type‖summary), heartbeat 제외 | 동작 확인 |
| `collector/keys.py` | 입력·삭제 **횟수**, Ctrl+V/Z/Y/X 감지. 어떤 키인지는 안 남김 — 파일 자체가 증거 | 동작 확인 |
| `collector/classify.py` · `domains.json` | exe 이름 → 창 제목 키워드 → 분류(resource/work/ai/other) | 동작 확인 |
| `collector/file_watch.py` | 감시 폴더 저장 이벤트(옵션, config에서 폴더 지정) | 동작 확인 |
| `collector/config.json` | 화이트리스트 앱 · keys.enabled(**true**) · 감시 폴더 · `learn_context` 항목 토글(office 포함) | 편집 가능 |
| `core/derive.py` | jsonl → session.json. 분당 집계 · 붙여넣기 해시 ↔ AI 창 복사 매칭 · **진짜 SHA-256 체인** · 숫자들 | 동작 확인 |
| `ui/viewer.html` | session.json → 한눈에 화면. 서버 없음 (HTML 한 장) | 동작 확인 |
| `web/` | 같은 화면의 **React 판** (Vite). `npm run dev` · `/api` 프록시 → 5000. A의 골격에 `SessionView` 를 끼운다 | 동작 확인 |
| `tests/` | **derive·chain 픽스처** — `events_basic.jsonl` → `expected_basic.json` 골든. `python tests/test_derive.py`. A 가 서버로 옮길 때 같은 출력이 나오는지 확인 | 통과 |
| `core/llm.py` | **Learn 의 AI 호출 한 곳** — 리포트(JSON 5항목 · **학생이 열 때 생성**) · Side Chat. 공급자 어댑터: `LLM_PROVIDER=qwen`(교수 추천 9/20 · 알리바바 API · 국제 엔드포인트) · `claude`(비교용) · `fake`(기본, 키 없을 때). 키는 환경변수만 | 동작 확인 (fake) · 실제 키는 A |
| `collector/office.py` | **Word·PowerPoint 문서 변화** (COM). 활성 문서를 5초마다 보고 — **숫자는 두 모드 공통 이벤트**(`doc_change` +n자/-m자 · `doc_paste_at` 붙여넣은 자리 · `doc_save` 저장 통계, 체인에 들어감), **텍스트는 Learn 맥락**(`diff` · `paste_at`). Proof 에선 글자를 저장하지 않음 | 동작 확인 (Word · PPT · Proof/Learn) |
| `collector/bridge.py` | **확장 다리** 127.0.0.1:5077 — 확장의 `tab` 이벤트를 체인에 넣고, Learn 모드일 때만 `context` 를 서버로 전달 (Proof 면 403) | 동작 확인 |
| `extension/` | **Chrome 확장 (MV3) 뼈대** — 탭 전환 → 도메인 → 다리. AI 사이트에서 Learn 맥락(질문·선택·답변 발췌). `extension/README.md` | 탭: 동작 · 맥락: 뼈대 |
| `collector/dev_receiver.py` | **계약 ③ 참고 서버** (Flask · 메모리). 세션 등록 · batch 수신 → chain.py 로 재계산 → chain_head 대조 · received_at · 지연 판정 · end 에서 root 대조 · GET /sessions/{id} 는 derive 결과 · **`/report` `/chat`** (Learn 만 · 상한 · Proof 403) | 동작 확인 · A의 Backend 기준 |

## 4. 데이터 계약 — 이 두 형식은 유지해 주세요

**원본 이벤트 한 줄** (`events-*.jsonl` · batch 의 `events[]` 원소)
```json
{"id":"evt_000012","session_id":"1054ba96-…","ts":"2026-09-20T15:10:01+09:00","source":"collector","type":"keys","count":12,"deleted":2,"app":"Code.exe","category":"work","h":"ae935bc6…"}
```
type: `session_start`{mode,work_id} `session_end` `window`{app,title,category} **`tab`{domain,category,title}**(확장) `copy`/`paste`{len,hash,app} `keys`{count,deleted} `undo` `redo` `cut` `file`{action,path,content_hash} **`doc_change`{app,file,where,added,removed} `doc_paste_at`{app,file,where} `doc_save`{app,file,chars,words,slides}**(Office) `idle_start` `idle_end` `heartbeat`(체인 제외·DB 저장 안 함)
`h` = PC 에서 계산한 체인 해시. 서버는 이걸 믿지 않고 `core/chain.py` 로 재계산해 비교한다. `session_id` 는 클라이언트 UUID.

**session.json** (= 목업북 `DATA.session` = 뷰어 입력 = 나중에 `GET /api/session/<id>` 응답)
```
segments[] {s,e,cat,title}   typed[]  deleted[]   pastes[] {m,len,ai,matched,after_typed}   undos[]
chain[] [ts,type,summary,prev,hash]   root   stats{typed,pasted,pasted_ai,cpm,undo,pauses,…}
```
필드 이름을 바꿔야 하면 알려주세요 — 목업북·뷰어가 같이 바뀌어야 합니다.

## 4-1. AI 키 (Learn 만)
```bat
set LLM_PROVIDER=qwen
set DASHSCOPE_API_KEY=sk-…          :: 알리바바 Model Studio 에서 발급. 서버 환경변수에만. 저장소·화면·확장에 절대 넣지 않는다
0_서버시작.bat
```
키가 없으면 `fake` 로 돌아 가짜 리포트를 준다 (화면 개발용). Claude 와 비교하려면 `LLM_PROVIDER=claude` + `ANTHROPIC_API_KEY`.

## 5. 다음 (순서)
0. A: 서버로 옮긴 derive/chain 이 `tests/test_derive.py` 를 통과하는지 (픽스처 준비됨)
1. 실데이터로 `domains.json`·화이트리스트 보정
2. A: `dev_receiver.py` 를 기준으로 진짜 Backend(DB · 인증 · Work) — 엔드포인트·응답 형식은 그대로, 저장만 DB 로. OpenTimestamps 앵커 실제 제출
3. B: ~~브라우저 확장 뼈대~~ 완료(`extension/`) → 실사용 테스트 · 사이트별 질문 입력창 셀렉터 · `page` 맥락
4. B: ~~viewer.html → React~~ 완료(`web/`) → A 골격에 결합 · Learn 화면 · 트레이(pystray)
5. 앱 포장: pywebview 창 + PyInstaller (Could)

## 6. 하지 않는 것 (다시 한 번)
화면 캡처 · 키 내용 · 클립보드 원문 · AI 대화 내용. 점수·등급·AI 확률 계산. 코드 어디에도 없어야 하고, 있으면 기획 위반입니다.
