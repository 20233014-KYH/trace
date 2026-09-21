# tests — derive · chain 픽스처

A 가 `core/derive.py` · `core/chain.py` 를 서버로 옮길 때 **"같은 입력 → 같은 출력"** 을 기계로 확인한다. 언어가 달라도 된다 — 입력 jsonl 과 기대 json 만 맞추면 된다.

```bash
python tests/test_derive.py            # ✓ 통과 — 이벤트 38 · 체인 37 · root 4b1b92be…
python tests/test_derive.py --json     # 실패 상세를 JSON 으로 (다른 언어 구현 비교용)
python tests/make_fixture.py           # 시나리오(이벤트)를 바꿨을 때 픽스처 재생성
python tests/test_derive.py --update   # 골든만 갱신 (derive 정의를 의도적으로 바꿨을 때)
```

## 파일
| 파일 | 무엇 |
|---|---|
| `fixtures/events_basic.jsonl` | 입력 — 계약 ① 이벤트 30건, 체인 해시 `h` 포함. 모든 이벤트 종류가 한 번 이상 |
| `fixtures/expected_basic.json` | 기대 출력 — 계약 ② session.json 골든 (segments · typed · deleted · pastes · undos · flow · chain · root · stats) |
| `make_fixture.py` | 시나리오 정의 + 생성기 |
| `test_derive.py` | 비교. 체인 재계산 · derive 결과 · root 세 가지 |

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
