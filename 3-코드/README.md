# Trace — 시스템 코드

> 결과만 남는 과제에서, 과정을 남긴다.

학생이 과제를 하는 동안 AI 사용을 기록하고, 결과물의 문장마다 어디서 왔는지 보여 주는 **PC 앱 · 크롬 확장 · 서버**입니다.
점수나 확률로 판정하지 않고 기록된 사실만 보여 주며, 원문은 학생 PC에만 둡니다.

창의프로젝트1 · 1팀 김용현 · 박상진 · 최신판 v0.1.26 (2026-11)

| | |
|---|---|
| 설치판 내려받기 (Windows · Mac) | https://trace-server-8aa0.onrender.com/download |
| 교수 화면 데모 (설치 없이) | https://trace-server-8aa0.onrender.com/s/demo |
| 저장소 | https://github.com/20233014-KYH/trace |
| 릴리스 (exe · dmg · 크롬 확장 zip) | https://github.com/20233014-KYH/trace/releases |

서버는 무료 플랜이라 한동안 안 쓰면 잠들어, 첫 요청에 30초 ~ 1분 걸립니다.

---

## 1. 어떻게 돌아가나

```
학생 PC
  크롬 확장 (extension/)   ChatGPT · Claude · Gemini 웹의 질문 · 답 · 답에 달린 출처 링크
  기록기   (collector/)    창 · 복사 · 붙여넣기 · Word / 한글 글이 바뀌는 과정 · 데스크톱 AI 앱
        │  원문은 이 PC 에만 저장. 서버로는 해시 체인(core/chain.py)만
        ▼
  PC 앱    (app/)          출처 잇기(core/match.py) → 출처 보기 · 다듬기 · 연결 확인 · 내역서
        │  내보낼 때 학생이 고른 대화만, 개인 정보는 가린 뒤
        ▼
서버 (server/ · Render + Supabase PostgreSQL)
  체인을 다시 계산해 PC 쪽과 대조 · 로그인 · 내역서 PDF · 교수 링크
        ▼
교수 — 계정 · 설치 없이 링크로 읽기만
```

문장마다 붙는 표시: **AI 답과 일치 및 유사** · **붙여넣고 고침** · **AI 답 참고함** · **다른 곳에서 붙여넣음** · **쓴 과정 기록 없음** · **출처 기록 없음**.
기록이 없는 곳은 "직접 씀"이 아니라 "출처 기록 없음"으로 둡니다.

## 2. 폴더

| 폴더 | 무엇 | 주요 파일 |
|---|---|---|
| `app/` | PC 앱 화면 — 로컬 Flask(127.0.0.1:5079) + pywebview 창. 홈 · 새 과제 · 기록 다시 보기 · 출처 보기 · 연결 확인 · 내역서 · 설정 · 기록 창(알약) | `statement.py`(입구) · `source.py` · `record.py` · `confirm.py` · `export.py` · `pill.py` · `updater.py` |
| `collector/` | 기록기 — 창 · 클립보드 · 키 **횟수**(어떤 키인지는 안 남김) · Word(`office*.py`) · 한글(`hangul.py`) · 데스크톱 AI 앱(`desktop_ai*.py` · `mac_ax.py`) · 개인 정보 가림(`mask.py`) | `collector.py` |
| `core/` | 앱 · 서버가 같이 쓰는 것 — 해시 체인 · 출처 잇기 · 문서 읽기(`docx.py` · `hwp.py` · `pdftext.py`) · 요약 · AI 화면 읽기 점검(`readcheck.py`) · 버전 | `chain.py` · `match.py` · `version.py` |
| `server/` | 서버 — 기록 받기 · 체인 대조 · 로그인(구글 · 카카오) · 내역서 PDF(`statement_pdf.py`) · 교수 링크(`static/share.html`) · 내려받기 화면. DB 주소가 없으면 SQLite | `app.py` · `db.py` |
| `extension/` | 크롬 확장 (Manifest V3) — AI 웹 화면의 질문 · 답 · 출처 링크를 기록기로 | `content.js` · `background.js` |
| `packaging/` | 설치판 — PyInstaller · 윈도우 Inno Setup · 맥 dmg · 버전별 바뀐 것(`notes/`) | `trace_app.py`(입구) · `trace.spec` · `build.py` |
| `tests/` | 출처 잇기 · 한글 · 기록 시험, 팀이 실제로 녹화한 시험 자료(`fixtures/`), 출처 잇기 정확도 평가(`eval_match.py`) | |
| `web/` · `ui/` · `collector/dev_receiver.py` | 9 ~ 10월 초기 시제품 — 지금 앱에서는 쓰지 않음 (기록용으로 남김) | |

저장소 맨 위의 `render.yaml`(서버 배포)과 `.github/workflows/release.yml`(태그를 올리면 윈도우 · 맥 설치판을 묶어 릴리스)도 시스템의 일부입니다.

## 3. 직접 돌려 보기

가장 쉬운 길은 위 **설치판**입니다. 저장소에서 돌리려면 (Python 3.11):

```bash
pip install -r 3-코드/requirements.txt
python 3-코드/packaging/trace_app.py            # PC 앱 — 홈 · 출처 보기 · 내역서
python 3-코드/packaging/trace_app.py record     # 기록 창 + 기록기
python 3-코드/server/app.py                     # 서버를 이 PC 에서 (http://127.0.0.1:5000/api)
```

- PC 앱은 기본으로 인터넷 서버(`core/settings.py`)에 붙습니다.
- 크롬 확장: `chrome://extensions` → 개발자 모드 → "압축해제된 확장 프로그램을 로드합니다" → `3-코드/extension`
- 맥은 처음에 손쉬운 사용 · 입력 모니터링 권한을 켜야 기록됩니다.
- 서버를 인터넷 DB 에 붙일 때만 `server/.env.example` 을 `.env` 로 복사해 채웁니다. 비밀 값은 저장소에 없습니다.

## 4. 시험

각 파일이 "통과 N · 실패 M" 을 출력합니다.

```bash
python 3-코드/app/test_record.py          # 앱 화면 (app/test_*.py 12개)
python 3-코드/tests/test_hangul_watch.py  # 한글 기록 (tests/test_*.py 17개)
python 3-코드/tests/eval_match.py --md    # 출처 잇기 정확도
python 3-코드/server/test_contract.py     # 서버 계약 (server/test_*.py 10개 · 서버를 먼저 켬)
```

설치판은 빌드할 때마다 `trace_app.py --selftest` 로 묶인 것이 다 열리는지 확인합니다.

## 5. 코드 곳곳에서 지키는 원칙

- **판정하지 않는다** — 점수 · 확률 없이 기록된 사실만 보여 준다.
- **원문은 학생 PC 에** — 서버에는 해시와 학생이 고른 것만. 기록하는 것이 늘면 그 버전 안내에 꼭 적는다.
- **문장을 대신 써 주지 않는다** — 다듬기는 어디를 · 왜 · 어떻게 고칠지 안내만.
- **외부 AI API 를 부르지 않는다** — 출처 잇기는 기록과 글자 비교로만. `core/llm.py` · `server/compare_llm.py` 는 초기 비교 실험용이라 설치판에 넣지 않는다.

## 6. 알려진 한계

- ChatGPT · Claude **데스크톱 앱** 답에 달린 출처 링크는 아직 못 읽는다 (웹은 읽음).
- 한글은 화면 글을 밖에서 읽을 수 없어 저장 · 자동 저장 파일로 기록한다. 윈도우 한글은 시험이 더 필요하다.
- AI 답을 완전히 다른 말로 바꾼 문장은 놓칠 수 있다 → 단정하지 않고 "출처 기록 없음"으로 둔다.
- 맥 설치판은 Apple 칩만 지원한다.

## 7. 기술 스택

Python 3.11 · Flask · pywebview · pynput · pywin32 / comtypes(윈도우) · PyObjC(맥) · olefile · pypdf · reportlab · SQLAlchemy · PostgreSQL(Supabase) · gunicorn · Render · Chrome Extension MV3 · PyInstaller · Inno Setup · GitHub Actions
