# 알약 창 (시제품 · B · 9/22)

목업 03·13·13b·13c 를 실제 윈도우 창으로. **A 가 pywebview 골격을 만들 때 참고용** — 여기서 확인된 것과 안 된 것을 그대로 가져가면 된다.

```bat
0_서버시작.bat
.venv\Scripts\python.exe app\pill.py --mode learn      :: 콘솔 대신 오른쪽 아래에 알약이 뜬다
.venv\Scripts\python.exe app\pill.py --mode proof --dry-run
```

| 파일 | |
|---|---|
| `pill.py` | pywebview 창 + 수집기 스레드. `Api`(status · layout · chat · stop) 를 JS 에 노출 |
| `pill.html` | 알약 · 질문칸 · 채팅 패널 (목업 CSS 그대로). 상태는 1초마다 `api.status()` |

## 되는 것 (9/22 실측 · 윈도우 11 · 배율 200%)
- **항상 위** (`on_top`) — 다른 창 최대화해도 위에 있음
- **투명 배경** — 알약·질문칸만 보임. 방법: `transparent=True` + Form 바탕 검정 + `DwmExtendFrameIntoClientArea(-1)`
- **드래그** — 알약(`pywebview-drag-region`)을 잡고 끌면 옮겨짐
- 알약 클릭 → 점 하나 (최소 모드) · ■ → 봉인 후 창 닫힘
- 질문칸 → 패널 → Enter → 서버 `/chat` 답 → ✕ · Proof 는 질문칸 없음

## 삽질에서 알아낸 것 (A 가 반복하지 않게)
| 증상 | 원인 | 해결 |
|---|---|---|
| 창 주위 회색 네모 | pywebview `transparent` 는 WebView2 배경만 투명, WinForms Form 바탕은 회색 | Form.BackColor 검정 + DWM 프레임 확장(-1) — `_make_transparent()` |
| 클릭·드래그 전부 죽음 | `TransparencyKey`(색 키) 방식은 창이 레이어드 창이 되어 WebView2 가 마우스를 못 받음 | 색 키 쓰지 말 것 → DWM 방식 |
| 알약이 화면 밖으로 | pywebview 기본 `min_size=(200,100)` → 72px 창이 100px 로 커져 아래가 잘림 · 물리/논리 픽셀 혼용 | `min_size=(30,30)` · 크기 변경은 `resize(w,h,FixPoint.SOUTH\|EAST)` · 위치는 `_work_area()` 로 논리 px |
| 그림자가 회색 얼룩 | 투명 창에서 box-shadow 는 반투명 회색으로 남음 | 그림자 대신 1px 테두리 |
| pywebview "maximum recursion depth" | `js_api` 객체의 공개 속성(Collector · Window)을 JS 에 노출하려 듦 | 속성 이름을 `_c` `_win` 처럼 밑줄로 |

## 안 되는 것 · 미룬 것
- **크기 바뀔 때 한 프레임 튐** — 투명 창 크기를 바꾸면 WebView2 가 이전 화면을 늘려서 한 프레임 보여줌. 단계별로 키우면 더 심함. **모션은 나중에** (9/22 결정). 패널을 별도 창으로 두는 방법도 해봤는데 `hidden=True` 가 transparent 창에선 안 먹고 크기도 어긋나서 되돌림.
- 키보드 포커스 — 알약이 떠 있는 채로 다른 앱 타이핑에 방해는 없으나, "포커스를 절대 안 뺏는" 창 스타일(WS_EX_NOACTIVATE)은 안 넣음 → A 골격에서
- 독점 전체화면(게임) 위는 안 뜸 (결정 11 그대로)
- 트레이 아이콘 · 모드 선택 화면(목업 01) 없음 — 지금은 `--mode` 인자
