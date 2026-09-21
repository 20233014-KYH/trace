# Trace 수집기 (윈도우 · 맥)

2026-09-19 · 기획(B) → 개발(A) · 목적: **기본 기능만으로 20분 실데이터를 만들어 "한눈에" 화면이 말이 되는지 본다.**

> **A(맥) 가 고친 것** — 원래 윈도우 전용이던 것을 **맥에서도 돌게** 만들었습니다.
> 구조·데이터 형식·`derive.py`·`viewer.html` 은 **하나도 안 바꿨습니다.**
> 자세한 건 맨 아래 [맥 지원](#맥-지원-a-가-붙인-것) 을 보세요.

디자인·서버·앱 포장은 전부 나중. 여기서는 아래 세 줄이 도는지만 확인한다.

```
수집기 (collector.py)  →  events-날짜.jsonl  →  derive.py  →  session.json  →  viewer.html
   창·입력·삭제·되돌리기·복사·붙여넣기        분당 집계 + SHA-256 체인           한눈에 화면
```

## 0. 준비 (한 번)

### 윈도우
- Windows 10/11 · Python 3.10+ (`python --version`)
- `1_기록시작.bat` 더블클릭 → `.venv` 자동 생성 + 패키지 설치 (1~2분)

### 맥
```bash
conda create -n trace python=3.11 -y
conda activate trace
pip install -r requirements.txt
```
그다음부터는 **`1_기록시작.command` 더블클릭**. (`conda activate` 를 대신 쳐 줍니다)

> `requirements.txt` 에 `; sys_platform == "win32"` 같은 조건이 붙어 있어서
> **자기 운영체제 것만 깔립니다.** 맥에서 `pywin32` 를 깔려다 실패하지 않습니다.

### ★ 맥은 권한을 한 번 켜야 합니다 (입력·붙여넣기)
```bash
python collector/check_permission.py
```
**시스템 설정 → 개인정보 보호 및 보안 → 입력 모니터링** ('손쉬운 사용' 아님, **다른 목록**)
에서 **수집기를 켠 그 프로그램**을 켜고 **⌘Q 로 완전히 껐다 켜세요.**
진단이 무엇을 켜야 하는지 이름으로 짚어 줍니다. 안 켜도 창·복사 기록은 정상입니다.

## 1. 테스트 절차 (30분)

| 단계 | 할 일 | 확인 |
|---|---|---|
| 1 | `1_기록시작.bat` 실행 | 콘솔에 `session_start`, 창 바꿀 때마다 `window [work] Code.exe …` |
| 2 | **20분 평소처럼 작업**: PDF/문서 읽기 → 코드나 글 쓰기 → 막히면 Claude/ChatGPT에 묻기 → 답 복사해서 붙여넣기 → 고치기 → 저장. 중간에 Ctrl+Z도 몇 번 | 콘솔에 `keys typed=12 deleted=2`, `copy`, `paste`, `undo` 가 찍힘 |
| 3 | 콘솔에서 Ctrl+C | `session_end` 후 종료 |
| 4 | `2_결과보기.bat` 실행 | 콘솔에 요약 숫자, 뷰어 창이 열림 |
| 5 | 뷰어에 `data\session.json` 끌어다 놓기 | 직접 입력 % / 붙여넣기 % · 레인 그래프 · 핵심 순간 |

명령으로 직접 하면:
```bash
python collector/collector.py --dry-run
python core/derive.py "data/events-*.jsonl" --out data/session.json
```
> 윈도우는 `.venv\Scripts\python.exe` 로, 경로 구분자는 `\` 로.
> 맥은 `1_기록시작.command` / `2_결과보기.command` 더블클릭이 더 편합니다.
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
| `collector/platform_win.py` · `platform_mac.py` | **운영체제마다 다른 부분만** 모아둔 곳. 함수 4개 | A 가 추가 |
| `collector/check_permission.py` | 맥에서 키 권한이 왜 막혔는지 짚어준다 | A 가 추가 |
| `collector/collector.py` | 상주 수집기. 활성 창 1초 폴링 · 클립보드 길이+해시 · 유휴 · heartbeat. 로컬 jsonl 먼저 쓰고 (서버 있으면) POST | 동작 확인 |
| `collector/keys.py` | 입력·삭제 **횟수**, Ctrl+V/Z/Y/X 감지. 어떤 키인지는 안 남김 — 파일 자체가 증거 | 동작 확인 |
| `collector/classify.py` · `domains.json` | exe 이름 → 창 제목 키워드 → 분류(resource/work/ai/other) | 동작 확인 |
| `collector/file_watch.py` | 감시 폴더 저장 이벤트(옵션, config에서 폴더 지정) | 동작 확인 |
| `collector/config.json` | 화이트리스트 앱 · keys.enabled(**true**) · 감시 폴더 | 편집 가능 |
| `core/derive.py` | jsonl → session.json. 분당 집계 · 붙여넣기 해시 ↔ AI 창 복사 매칭 · **진짜 SHA-256 체인** · 숫자들 | 동작 확인 |
| `ui/viewer.html` | session.json → 한눈에 화면. 서버 없음 | 동작 확인 |
| `collector/dev_receiver.py` | (지금은 안 씀) Flask 수신 서버. 과제 요건(Flask→JSON→화면) 시연 때 사용 | 동작 확인 |

## 4. 데이터 계약 — 이 두 형식은 유지해 주세요

**원본 이벤트 한 줄** (`events-*.jsonl`)
```json
{"id":"evt_000012","session_id":"s_2026-09-19_150002","ts":"2026-09-19T15:10:01+09:00","source":"collector","type":"keys","count":12,"deleted":2,"app":"Code.exe","category":"work"}
```
type: `session_start` `session_end` `window`{app,title,category} `copy`/`paste`{len,hash,app} `keys`{count,deleted} `undo` `redo` `cut` `file`{action,path,content_hash} `idle_start` `idle_end` `heartbeat`

**session.json** (= 목업북 `DATA.session` = 뷰어 입력 = 나중에 `GET /api/session/<id>` 응답)
```
segments[] {s,e,cat,title}   typed[]  deleted[]   pastes[] {m,len,ai,matched,after_typed}   undos[]
chain[] [ts,type,summary,prev,hash]   root   stats{typed,pasted,pasted_ai,cpm,undo,pauses,…}
```
필드 이름을 바꿔야 하면 알려주세요 — 목업북·뷰어가 같이 바뀌어야 합니다.

## 5. 이 테스트 다음 (순서 제안)
1. 실데이터로 `domains.json`·화이트리스트 보정 (테스트에서 틀린 분류 반영)
2. 봉인: `session_end` 때 root 확정 + OpenTimestamps 제출 (`opentimestamps-client`) → `sealed_at`, `anchor`
3. Flask `app.py`: `/api/event` 수신 + `/api/session/<id>` 가 session.json 형식으로 응답 (데스크 크리틱 요건)
4. 앱 포장: pywebview 로 `viewer.html`·목업북 화면을 창으로, 알약은 프레임 없는 작은 창, 트레이는 pystray, PyInstaller 로 exe

## 6. 하지 않는 것 (다시 한 번)
화면 캡처 · 키 내용 · 클립보드 원문 · AI 대화 내용. 점수·등급·AI 확률 계산. 코드 어디에도 없어야 하고, 있으면 기획 위반입니다.

---

## 맥 지원 (A 가 붙인 것)

### 무엇을 바꿨나 — **구조는 그대로입니다**

운영체제마다 다른 건 **함수 4개뿐**이라, 그것만 따로 빼냈습니다.

| 함수 | 윈도우 | 맥 |
|---|---|---|
| `foreground()` | `win32gui.GetForegroundWindow` | `NSWorkspace` + 런루프 |
| `idle_seconds()` | `GetLastInputInfo` | `CGEventSourceSecondsSinceLastEventType` |
| `clipboard_serial()` | `GetClipboardSequenceNumber` | `NSPasteboard.changeCount` |
| `input_permission_hint()` | 없음 (권한 불필요) | 입력 모니터링 안내 |

`collector.py` 는 맨 위에서 맞는 파일을 불러올 뿐, **나머지 코드는 그대로**입니다.

```python
if sys.platform == "win32":
    import platform_win as osx
elif sys.platform == "darwin":
    import platform_mac as osx
```

`keys.py` 도 **수정자 키만** 나눴습니다 — 윈도우는 `Ctrl+V`, 맥은 `⌘V`.
(맥의 다시실행은 `Ctrl+Y` 가 아니라 `⌘⇧Z` 라 그것도 처리했습니다)

### 덤으로 고친 것 — 클립보드를 **덜 읽습니다**

전에는 `_tick()` 마다 `pyperclip.paste()` 로 **1초에 한 번씩 클립보드 내용을 읽었습니다.**
이제는 **번호(serial)만** 먼저 보고, 번호가 달라진 순간에만 내용을 읽습니다.

```
_tick() 10번, 클립보드 그대로  →  내용 읽은 횟수 0번   (전에는 10번)
번호가 바뀐 순간              →  그때 1번만 읽음
```

기획안 §11 "클립보드는 길이와 SHA256만" 을 **코드로** 지키는 방식입니다.
번호를 못 구하는 환경이면 예전처럼 매번 읽으므로 동작은 같습니다.

### 맥에서 못 하는 것

| | 윈도우 | 맥 |
|---|---|---|
| 앱 이름 | ✅ | ✅ |
| **창 제목** | ✅ | ❌ **'화면 기록' 권한이 필요해서 안 씁니다** |
| 유휴 시간 | ✅ | ✅ (권한 불필요) |
| 클립보드 | ✅ | ✅ |
| 입력·삭제 수 | ✅ | ✅ (입력 모니터링 권한 필요) |

**맥은 창 제목이 없어서 `domains.json` 의 `title_keywords` 가 동작하지 않습니다.**
그래서 브라우저(`Google Chrome`)는 항상 `other` 로 떨어집니다 — 어느 탭인지 알 수 없습니다.
**AI 창 판별이 맥에서는 `Claude`·`ChatGPT` 같은 전용 앱일 때만 됩니다.**
브라우저 탭 구분은 Tier 1 확장이 붙어야 합니다.

### 맥에서 확인한 것

```
16:55:32  session_start
16:55:32  window        [ai      ] Claude
16:55:32  heartbeat
16:55:42  session_end

→ core/derive.py "data/events-*.jsonl"
  세션 s_2026-09-19_165532  1분  이벤트 3건
  루트 해시 ae92c6e0f62bf08a…  →  data/session.json
```

수집기 → events jsonl → derive → session.json 까지 **맥에서 끝까지 돕니다.**

---

## ★ 고쳐야 할 것 — `derive.py` 구간 길이가 부풀려집니다

실데이터로 돌려보다 찾았습니다. **B 가 확인 후 고쳐주세요.**

```
세션 실제 길이   3분
구간 길이 합계  17분   ← 14분 더 많다
ai_min           6분   ← 3분짜리 세션인데
```

`derive.py` 의 이 줄이 원인입니다:

```python
segments.append({"s": cur[2], "e": max(cur[2] + 1, m), ...})
```

**모든 구간에 최소 1분을 줍니다.** 1분 안에 창을 5번 바꾸면 1분짜리 구간 5개 = 5분이 됩니다.
그리고 `other→ai→other→ai` 처럼 번갈아 나오면 병합 조건에 안 걸려 그대로 쌓입니다.

**윈도우에서도 똑같이 납니다.** VS Code ↔ Chrome ↔ Claude 를 1분 안에 오가는 게
정확히 우리 타깃 사용 패턴이라, **"AI 창에 6분 있었다" 같은 숫자가 발표에서 나오면 반박당합니다.**

관련해서 하나 더 — **`직접 입력 0자 (0%)`** 는 "안 쳤다" 와 "못 셌다" 를 구분하지 못합니다.
키 권한이 꺼져 있거나 `keys.enabled=false` 면 `typed` 가 아예 없는 것이므로,
**0% 가 아니라 "기록 없음" 으로 표시**해야 오해가 없습니다.
