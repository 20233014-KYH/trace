# 설치판 (v0.1 · 10/13)

학생은 **https://trace-server-8aa0.onrender.com/download** 에서 `Trace-Setup-<버전>.exe` 를 받아 깐다.

| 무엇 | 어디 |
|---|---|
| 버전 | `core/version.py` 하나 |
| 입구 (Trace.exe) | `packaging/trace_app.py` — 그냥 열면 내역서 화면(앱 창) · `record` 면 알약+기록기 · `--selftest` |
| 묶기 | `packaging/trace.spec` (PyInstaller) · `packaging/build.py` |
| 설치 파일 | `packaging/trace.iss` (Inno Setup · 관리자 권한 없이 `%LOCALAPPDATA%\Programs\Trace`) |
| 바뀐 것 글 | `packaging/notes/v<버전>.md` → 릴리스 본문 · 내려받기 화면 · 앱의 새 버전 알림 |
| 빌드 | `.github/workflows/release.yml` — 윈도우에서 묶고 자체 시험 |
| 서버 | `GET /api/app/latest` (GitHub 최신 릴리스 · 10분마다) · `GET /download` |

## 새 버전 내기

1. `core/version.py` 의 `VERSION` 올리기 · `packaging/notes/v<버전>.md` 쓰기 → PR → 머지
2. ```
   git tag v0.1.1 && git push origin v0.1.1
   ```
3. GitHub Actions "설치판" 이 끝나면(10분쯤) 릴리스에 `.exe` · 확장 `.zip` 이 붙고, 내려받기 화면과 앱 알림이 바로 새 버전을 가리킨다.

태그와 `version.py` 가 다르면 빌드가 멈춘다. PC 앱 코드를 바꾼 PR 은 릴리스 없이 윈도우 묶기·자체 시험만 돈다.

## 설치판에서 달라지는 것

- **우리 코드는 원본 그대로 싣는다** (`_internal/trace/…`). 각 파일이 자기 위치로 html·config·글꼴을 찾으므로 저장소에서 돌릴 때와 같다. 라이브러리는 `trace.spec` 이 우리 코드의 import 를 읽어 모은다 — 새 라이브러리를 써도 spec 을 안 고쳐도 된다. 실행 중에 고르는 모듈(백엔드)만 `collect_submodules` 에 적는다.
- **처음 켤 때** `~/trace-config.json` 을 만든다 — 인터넷 서버 · 이 PC 만의 과제 id (`W-…`). 이미 있으면 그대로.
- **기록 · 로그**는 설치 폴더 밖 `%LOCALAPPDATA%\Trace\` (`data\` · `logs\`) — 새 버전을 깔아도 남는다.
- 창만 있는 exe 라 print 는 `logs\home.log` · `logs\record.log` 로. 문제가 생기면 이 파일을 받는다.

## 손으로 묶어 보기

```
pip install -r 3-코드/packaging/requirements-build.txt
python 3-코드/packaging/build.py          # 윈도우는 Inno Setup 6 이 있어야 설치 파일까지
```
맥에서도 `packaging/dist/Trace/Trace` 까지 묶고 자체 시험은 돈다 (맥 설치판은 아직).

## 알려진 것 (v0.1)

- 코드 서명 전 — "Windows의 PC 보호" → 추가 정보 → 실행
- 기록기가 키 입력 횟수를 세서 백신이 키로거로 오인할 수 있음 — 실제 윈도우에서 확인 필요
- 크롬 확장은 따로 (zip 받아 개발자 모드로 불러오기)
- 과제 고르기 화면 전 — 기록은 설정의 과제 id 로 모이고, 내역서 화면에서 옮긴다
