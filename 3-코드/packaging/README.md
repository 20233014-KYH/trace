# 설치판 (v0.1 · 10/13)

학생은 **https://trace-server-8aa0.onrender.com/download** 에서 윈도우 `Trace-Setup-<버전>.exe` · 맥 `Trace-<버전>-mac.dmg` (Apple 칩) 를 받아 깐다.

| 무엇 | 어디 |
|---|---|
| 버전 | `core/version.py` 하나 |
| 입구 (Trace.exe) | `packaging/trace_app.py` — 그냥 열면 내역서 화면(앱 창) · `record` 면 알약+기록기 · `--selftest` |
| 묶기 | `packaging/trace.spec` (PyInstaller) · `packaging/build.py` |
| 설치 파일 | 윈도우 `packaging/trace.iss` (Inno Setup · 관리자 권한 없이 `%LOCALAPPDATA%\Programs\Trace`) · 맥 `trace.spec` 의 `Trace.app` → `build.py` 가 `.dmg` |
| 바뀐 것 글 | `packaging/notes/v<버전>.md` → 릴리스 본문 · 내려받기 화면 · 앱의 새 버전 알림 |
| 빌드 | `.github/workflows/release.yml` — 윈도우 · 맥에서 묶고 자체 시험 → 둘 다 되면 릴리스 한 번 |
| 서버 | `GET /api/app/latest` (GitHub 최신 릴리스 · 10분마다 · API 대신 웹 주소로 — 파일 이름은 build.py 와 같아야) · `GET /download` |

## 릴리스 글 (`packaging/notes/v<버전>.md`) 쓰는 법

앱의 "바뀐 것" 창(업데이트 누르기 전 · 업데이트 뒤 처음)과 내려받기 화면에 나온다. **첫 `---` 위는 학생이 읽는다** — 쉬운 말로.

```
업데이트하기 전에 무엇이 바뀌는지 먼저 보여 줘요.        ← 첫 줄: 한 줄 소개
- 바뀐 것 하나                                          ← "- " 로 시작: 바뀐 것 (6개까지)
- 바뀐 것 둘
기록: 이제 Word 글이 바뀌는 과정도 남겨요               ← 기록하는 것이 바뀔 때만 (창에서 따로 강조)
할 일: 업데이트 뒤 설정 › 기록 에서 권한을 다시 켜 주세요   ← 학생이 할 일이 있을 때만

---
개발 메모 (앱엔 안 나옴 · 파일 · 함수 이름 · PR 번호는 여기에)
```
**기록하는 것이 늘거나 바뀌면 꼭 `기록:` 줄을 쓴다** — 모르는 사이에 기록이 늘지 않게.

## 새 버전 내기

1. `core/version.py` 의 `VERSION` 올리기 · `packaging/notes/v<버전>.md` 쓰기 → PR → 머지
2. ```
   git tag v0.1.1 && git push origin v0.1.1
   ```
3. GitHub Actions "설치판" 이 끝나면(10분쯤) 릴리스에 `.exe` · `.dmg` · 확장 `.zip` 이 붙고, 내려받기 화면과 앱 알림이 바로 새 버전을 가리킨다.

태그와 `version.py` 가 다르면 빌드가 멈춘다. PC 앱 코드를 바꾼 PR 은 릴리스 없이 윈도우 묶기·자체 시험만 돈다.

## 맥 서명 인증서 (한 번만 · 10/14)

`packaging/맥_서명_준비.command` 를 저장소 주인 맥에서 한 번 더블클릭 → `3-코드/data/mac-signing/` (저장소에 안 올라감)에 인증서를 만들고 GitHub 비밀값 `MAC_SIGN_P12` · `MAC_SIGN_PASSWORD` 에 넣는다. 릴리스(태그) 빌드는 이 비밀값이 없으면 멈춘다 — 임시 서명으로 내보내면 모두의 맥 권한이 풀리므로. PR 빌드는 비밀값 없이 그때만 쓰는 인증서로 서명 길만 시험한다.
**인증서를 새로 만들면 모두의 맥 권한이 한 번 더 풀린다** — `data/mac-signing/` 은 지우지 말 것 (다른 맥에서 릴리스를 낼 일은 없음 — 태그만 올리면 GitHub 이 서명).

## 설치판에서 달라지는 것

- **우리 코드는 원본 그대로 싣는다** (`_internal/trace/…`). 각 파일이 자기 위치로 html·config·글꼴을 찾으므로 저장소에서 돌릴 때와 같다. 라이브러리는 `trace.spec` 이 우리 코드의 import 를 읽어 모은다 — 새 라이브러리를 써도 spec 을 안 고쳐도 된다. 실행 중에 고르는 모듈(백엔드)만 `collect_submodules` 에 적는다.
- **처음 켤 때** `~/trace-config.json` 을 만든다 — 인터넷 서버 · 이 PC 만의 과제 id (`W-…`). 이미 있으면 그대로.
- **기록 · 로그**는 설치 폴더 밖 — 윈도우 `%LOCALAPPDATA%\Trace\` · 맥 `~/Library/Application Support/Trace/` (`data` · `logs`) — 새 버전을 깔아도 남는다.
- **맥**: 애플 개발자 등록 전이라 처음 열 때 "그래도 열기". 서명은 우리 인증서(스스로 서명 · 0.1.9~) — 맥은 권한(손쉬운 사용 · 입력 모니터링)을 서명으로 기억해서, 빌드마다 지문이 다른 임시(ad-hoc) 서명 때는 업데이트할 때마다 권한이 풀렸다. 같은 인증서로 서명하면 안 풀린다 (아래 "맥 서명 인증서"). 그래도 꺼져 있으면 왼쪽 메뉴에 알림 → 설정 › 기록 [설정 열기] 가 예전 권한 줄(`tccutil reset … kr.trace.app`)을 지우고 다시 물어 켜기만 하면 되게 한다 (`app/options.py`). 파이썬 HTTP 서버가 켤 때 PC 이름을 거꾸로 찾는 것(getfqdn)을 끔 — 새 앱은 로컬 네트워크 허락 전이라 30초 넘게 멈췄다 (`trace_app._이름_안_찾기`).
- 창만 있는 exe 라 print 는 `logs\home.log` · `logs\record.log` 로. 문제가 생기면 이 파일을 받는다.

## 손으로 묶어 보기

```
pip install -r 3-코드/packaging/requirements-build.txt
python 3-코드/packaging/build.py          # 윈도우는 Inno Setup 6 이 있어야 설치 파일까지
```
맥에서는 `packaging/dist/Trace.app` 과 `Trace-<버전>-mac.dmg` 까지 만든다.

## 알려진 것 (v0.1)

- 코드 서명 전 — "Windows의 PC 보호" → 추가 정보 → 실행
- 기록기가 키 입력 횟수를 세서 백신이 키로거로 오인할 수 있음 — 실제 윈도우에서 확인 필요
- 크롬 확장은 따로 (zip 받아 개발자 모드로 불러오기)
- 과제 고르기 화면 전 — 기록은 설정의 과제 id 로 모이고, 내역서 화면에서 옮긴다
