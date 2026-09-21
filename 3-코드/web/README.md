# Trace 화면 (React · Vite)

`3-코드/ui/viewer.html` 을 React 로 옮긴 것 + Learn 화면. Proof 는 목업 07 (두 숫자 → 구성 막대 → 타일 3 → 레인 그래프 → 앱별 활동 → 접힌 상세 → 핵심 순간 → 체인), Learn 은 목업 13b·13c·14·16.

```bash
npm install        # 처음 한 번
npm run dev        # http://localhost:5173  (/api 는 127.0.0.1:5000 으로 프록시 → dev_receiver.py 또는 A의 Backend)
npm run build      # dist/
```

## 구조
```
src/
├─ App.jsx                    데이터 불러오기: 샘플(Proof·Learn) · session.json 드롭 · 서버 GET /api/sessions/{id} → mode 가 learn 이면 LearnView
├─ components/
│  ├─ SessionView.jsx         "한눈에" 화면 전체 (Hero · Tiles · AppTable · FlowDetails · Moments · 체인)
│  ├─ Timeline.jsx            레인 그래프 SVG + Legend   ← A의 앱에 끼울 핵심 컴포넌트. markers= 를 주면 '학습 흐름' 레인 추가 (Learn)
│  ├─ LearnView.jsx           Learn 세션 화면 — 탭 3개(타임라인+맥락 · Learning Report · 이벤트 원본) + 알약·질문칸
│  ├─ ContextPanel.jsx        마커 하나의 맥락: 직전 오류 → 질문 → 답변 발췌 → 이후 (목업 14 오른쪽)
│  ├─ ReportView.jsx          Learning Session Report — 타일 4 + AI 5항목. 열 때 GET, 다시 생성 POST (목업 16)
│  └─ AskBox.jsx              알약 위 질문칸 → 펼치면 채팅 패널, ✕ 로 접힘 (목업 13b/13c). POST /chat
├─ lib/
│  ├─ format.jsx              앱 이름 · 창 이름 · 붙여넣기 문구 · 색  (문구는 여기서만)
│  ├─ stats.js                stats · appSummary · moments  (core/derive.py 와 같은 정의)
│  ├─ learn.js                맥락 항목 → 마커 · 마커 주변 맥락 · 숫자 (판정 없음)
│  └─ api.js                  서버 호출 한 곳 (계약 ③). 주소·형식 바뀌면 여기만
└─ index.css                  러프 스타일. 디자인 확정 후 :root 토큰만 교체
public/sample_session.json    Proof 샘플 (데이터 없이 화면 볼 때)
public/sample_learn.json      Learn 샘플 — {session, context[9], report}. 픽스처 세션 + 맥락 + 리포트
```

## A의 React 골격에 끼우는 법
```jsx
import SessionView from './components/SessionView.jsx';
// 라우트 /sessions/:id 에서
const s = await fetch(`/api/sessions/${id}`).then(r => r.json());   // 계약 ② 그대로
<SessionView s={s} />
```
`Timeline` 만 따로 쓰려면 `<Timeline s={s} />`. 입력 형식은 `3-코드/README.md` 4절(session.json).

## Learn 화면이 서버에서 쓰는 것 (계약 ③ 5절)
| 호출 | 언제 | 비고 |
|---|---|---|
| `GET /sessions/{id}` | 세션 열 때 | `mode:"learn"` 이면 LearnView |
| `GET /sessions/{id}/context` | 세션 열 때 | **★ 제안 · 아직 계약에 없음.** 응답 `{items:[…]}` (5절 context 항목 그대로). 없으면 마커 없이 뜸 |
| `GET /sessions/{id}/report` | Learning Report 탭을 열 때 | 없으면 이때 생성. 403(Proof) · 429 · 502 는 `lib/api.js explain()` 으로 문장 |
| `POST /sessions/{id}/report` | [다시 생성] | 3/3 이면 버튼 비활성 |
| `POST /sessions/{id}/chat` | 질문칸 · 맥락 패널 [더 묻기] | `{selection, question}` → `{answer, turns}` |

샘플 모드(`샘플 · Learn`)는 서버 없이 가짜 답으로 돈다. 서버 세션을 열면(`live`) 위 호출을 실제로 한다 — 9/21 A 서버(SQLite)로 report·chat·403 확인.

## 다음
- Proof 체인 원본 탭 · 증명서 화면 — 목업 08·11
