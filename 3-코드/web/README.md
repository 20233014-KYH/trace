# Trace 화면 (React · Vite)

`3-코드/ui/viewer.html` 을 React 로 옮긴 것. 화면 구성은 목업 07 과 같다 (두 숫자 → 구성 막대 → 타일 3 → 레인 그래프 → 앱별 활동 → 접힌 상세 → 핵심 순간 → 체인).

```bash
npm install        # 처음 한 번
npm run dev        # http://localhost:5173  (/api 는 127.0.0.1:5000 으로 프록시 → dev_receiver.py 또는 A의 Backend)
npm run build      # dist/
```

## 구조
```
src/
├─ App.jsx                    데이터 불러오기 3가지: 샘플 · session.json 드롭 · 서버 GET /api/sessions/{id}
├─ components/
│  ├─ SessionView.jsx         "한눈에" 화면 전체 (Hero · Tiles · AppTable · FlowDetails · Moments · 체인)
│  └─ Timeline.jsx            레인 그래프 SVG + Legend   ← A의 앱에 끼울 핵심 컴포넌트
├─ lib/
│  ├─ format.jsx              앱 이름 · 창 이름 · 붙여넣기 문구 · 색  (문구는 여기서만)
│  └─ stats.js                stats · appSummary · moments  (core/derive.py 와 같은 정의)
└─ index.css                  러프 스타일. 디자인 확정 후 :root 토큰만 교체
public/sample_session.json    데이터 없이 화면 볼 때
```

## A의 React 골격에 끼우는 법
```jsx
import SessionView from './components/SessionView.jsx';
// 라우트 /sessions/:id 에서
const s = await fetch(`/api/sessions/${id}`).then(r => r.json());   // 계약 ② 그대로
<SessionView s={s} />
```
`Timeline` 만 따로 쓰려면 `<Timeline s={s} />`. 입력 형식은 `3-코드/README.md` 4절(session.json).

## 다음
- Learn 화면(맥락 패널 · Report) — 목업 14·16 기준, 서버의 `/context` `/report` 가 생기면
- Proof 체인 원본 탭 · 증명서 화면 — 목업 08·11
