# tests — derive · chain 픽스처

A 가 `core/derive.py` · `core/chain.py` 를 서버로 옮길 때 **"같은 입력 → 같은 출력"** 을 기계로 확인한다. 언어가 달라도 된다 — 입력 jsonl 과 기대 json 만 맞추면 된다.

```bash
python tests/test_derive.py            # ✓ 통과 — 이벤트 38 · 체인 37 · root 4b1b92be…
python tests/test_derive.py --json     # 실패 상세를 JSON 으로 (다른 언어 구현 비교용)
python tests/make_fixture.py           # 시나리오(이벤트)를 바꿨을 때 픽스처 재생성
python tests/test_derive.py --update   # 골든만 갱신 (derive 정의를 의도적으로 바꿨을 때)
python tests/기술테스트_제안서.py      # 제안서 4장 기술 테스트 — ① 붙여넣기 출처 4/4 ② 조작 2건 탐지
python tests/연결시제품.py             # 결과물(Word) 문장 ↔ AI 답 연결 시험 4개 + 색칠한 화면 (data/연결시제품/*.html)
python tests/test_paste_source.py      # 수집기→derive 한 바퀴 · 나무위키 등 사이트별 붙여넣기 출처 10건
xvfb-run -a -s "-screen 0 1440x900x24" python tests/녹화시험_위키.py   # 실제 Chromium+확장+수집기로 나무위키·위키백과 복사 녹화 (결과: 녹화시험_결과.md)
```

## 파일
| 파일 | 무엇 |
|---|---|
| `fixtures/events_basic.jsonl` | 입력 — 계약 ① 이벤트 30건, 체인 해시 `h` 포함. 모든 이벤트 종류가 한 번 이상 |
| `fixtures/expected_basic.json` | 기대 출력 — 계약 ② session.json 골든 (segments · typed · deleted · pastes · undos · flow · chain · root · stats) |
| `make_fixture.py` | 시나리오 정의 + 생성기 |
| `test_derive.py` | 비교. 체인 재계산 · derive 결과 · root 세 가지 |
| `test_paste_source.py` | 실제 수집기(창·클립보드만 가짜)를 돌려 붙여넣기 출처 확인. 나무위키(목록 밖 → 기타 + 도메인) · 문서 제목에 "ChatGPT" 가 있어도 도메인 우선 · 맥 크롬(창 제목 없음) · 확장 없을 때 제목 키워드 |
| `녹화시험_위키.py` | 실제 Chromium + Trace 확장 + 수집기(다리 5077) + X 클립보드로 나무위키·위키백과·chatgpt.com 복사→붙여넣기, 화면 녹화. 사이트 내용만 로컬 흉내(주소·탭 제목은 실제와 같음), 전경 창은 시험이 지정 |
| `기술테스트_제안서.py` | 서비스 제안서 4장 증거 코드. 같은 픽스처로 ① 붙여넣기 4건 출처 판정 ② 글자 수 1 변경·기록 1개 삭제를 체인이 잡는지 |
| `연결시제품.py` · `fixtures/match*` | 문장 연결 시험 (`core/match.py`). match = 만든 보고서 12문장 · match3 = 경제 14문장(정답 먼저) · match_rec = 녹화(실제 기록기 + ChatGPT + Word) 8문장 · match_mix = 세 AI 섞어 쓴 녹화 9문장. · match_web = **실제 나무위키·위키백과 + 사람이 직접 Ctrl+C·V** 녹화 7문장 (다른 곳 붙여넣기 = 빨강 + 출처 · Word 안 잘라 옮기기는 자기 글) · match_proc = **AI 가 만든 Word 파일을 열고** 사람이 직접 치고 프로그램이 한 문장 넣은 녹화 5문장 (열 때부터 있던 글 · 키 입력 없이 들어온 글 = 빨강 "쓴 과정 기록 없음") · match_view = **사람이 ChatGPT 에 직접 묻고 답을 보며 손으로 고쳐 친** 녹화 5문장 (90% 넘게 같으면 빨강 — 100% 같으면 "일치" · 90~99% 는 "유사" — 그 아래는 "보고 씀" · 10/7 결정) · match_app = **데스크톱 Claude 앱** 답을 보며 손으로 옮겨 친 녹화 15줄 (collector/desktop_ai.py 가 앱 화면에서 답 원문을 읽음 · 8자 미만 짧은 줄은 비교 안 함) 녹화 폴더엔 `report.docx` · `events.jsonl`(복사·붙여넣기) · `context.jsonl`(복사 발췌) 도. `--edit-cover 0.35` 로 기준 바꿔 보기. 10/7 결과 71/75 · 직접 쓴 문장 잘못 잡음 0 |

## 시나리오가 덮는 것
- 붙여넣기 3종: **AI 출처와 해시 일치**(빨강) · **일치하지만 AI 아님**(주황) · **복사 기록 없음**
- 확장 `tab` 이벤트가 브라우저 창의 분류를 정정 (제목 "Java Docs"=기타 → 도메인 docs.oracle.com=학습자료)
- 화이트리스트 밖 앱(카카오톡·탐색기): 이름만, 제목 없음
- 입력·삭제·되돌리기 · 파일 저장 · 유휴 · heartbeat(체인 제외)
- 1초 미만 스침 구간은 앞 구간에 흡수
- Word: AI 창 복사 120자 → 붙여넣기 → `doc_paste_at` 문단 4 → `doc_change` +120자 → 직접 수정 +27/-6 → `doc_save` (숫자만, 두 모드 공통)

## 서버 구현자(A)가 맞춰야 하는 것
1. `chain.verify` 가 통과 — hᵢ = SHA256(hᵢ₋₁ ‖ "|" ‖ ts ‖ "|" ‖ type ‖ "|" ‖ summary). summary 문자열은 `core/chain.py` 의 `summary()` 그대로 (공백·중점 `·` 포함)
2. root `4b1b92beae4e5c03…` 가 나와야 봉인 검증이 성립
3. `GET /sessions/{id}` 응답이 `expected_basic.json` 과 같아야 화면이 같게 그려짐

파이썬이면 `core/` 두 파일을 그대로 import 하는 게 가장 안전하다. 다른 언어면 이 픽스처로 맞추고, 못 맞추는 필드가 있으면 알려달라 — 계약 ②를 같이 고친다.

## 정의 메모 (헷갈리기 쉬운 것)
- **직접 입력**은 모든 창의 입력 합계다 (카카오톡에 친 것도 포함). 어디서 쳤는지는 `flow` · 앱별 표에서 나뉜다. **9/20 결정: 이대로 간다** — 작업 창만 세면 편집기가 화이트리스트에 없는 학생은 0%가 되기 때문
- **붙여넣기 AI 여부**는 "같은 해시가 `category=ai` 창에서 복사됐는가" 뿐. 판정이 아니라 출처 표기
- **segments** 의 시각은 분 단위 소수(초 정밀도). `typed`/`deleted` 배열만 분 단위 정수
