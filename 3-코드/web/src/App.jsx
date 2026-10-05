// Trace 화면 (React) — "한눈에"(SessionView). 데이터는 세 곳에서 온다:
//   ① 샘플(public/sample_session.json)  ② session.json 파일 드롭  ③ 서버 GET /api/sessions/{id}  (vite.config 의 proxy → 127.0.0.1:5000)
// 9/28 개정: Learn 화면(LearnView·ReportView·AskBox)은 삭제. 내역서·연결 확인 화면이 생기면 여기에 붙인다.
// A의 React 골격(라우터·로그인·Dashboard)이 생기면 <SessionView s={...}/> 만 그쪽 라우트에 끼우면 된다.
import { useState } from 'react';
import SessionView from './components/SessionView.jsx';
import DesignGuide from './components/DesignGuide.jsx';
import * as api from './lib/api.js';

export default function App() {
  const [s, setS] = useState(null);
  const [sid, setSid] = useState('');
  const [err, setErr] = useState('');
  const [guide, setGuide] = useState(false); // 디자인 기준 페이지 (팔레트 후보 · 부품)

  const loadSample = () => fetch('/sample_session.json').then((r) => r.json()).then(setS).catch((e) => setErr(String(e)));
  const loadServer = () => {
    if (!sid.trim()) return;
    setErr('');
    api.getSession(sid.trim()).then(setS).catch((e) => setErr(`서버에서 못 가져옴: ${api.explain(e)}`));
  };
  const readFile = (f) => {
    if (!f) return;
    const r = new FileReader();
    // 옛 Learn 샘플({session, context, report}) 을 끌어다 놓아도 session 만 보여 준다
    r.onload = () => { try { const d = JSON.parse(r.result); setS(d.session || d); setErr(''); } catch (e) { setErr(`JSON 오류: ${e.message}`); } };
    r.readAsText(f, 'utf-8');
  };

  if (guide) return <DesignGuide onClose={() => setGuide(false)} />;   // 디자인 기준은 자기 상단 줄을 가진 전체 화면
  return (
    <div onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); readFile(e.dataTransfer.files[0]); }}>
      <header>
        <b>Trace</b><span className="sub">한눈에 · React</span>
        <span style={{ marginLeft: 'auto' }} />
        <input value={sid} onChange={(e) => setSid(e.target.value)} placeholder="서버 세션 id (UUID)" onKeyDown={(e) => e.key === 'Enter' && loadServer()} />
        <button className="btn" onClick={loadServer}>서버에서</button>
        <button className="btn" onClick={() => setGuide(true)}>디자인 기준</button>
        <button className="btn" onClick={loadSample}>샘플</button>
        <label className="btn primary">session.json 열기<input type="file" accept=".json" hidden onChange={(e) => readFile(e.target.files[0])} /></label>
      </header>
      <main>
        {err && <p className="err">{err}</p>}
        {s ? <SessionView s={s} /> : (
          <div className="drop">
            <div style={{ fontSize: 28 }}>⇩</div>
            <b>session.json 을 여기에 끌어다 놓으세요</b><br />
            또는 [샘플] · 서버가 켜져 있으면 세션 id 입력 후 [서버에서]<br /><br />
            <span className="mono">python core/derive.py "data/events-*.jsonl"</span> 이 만든 파일입니다.
          </div>
        )}
      </main>
    </div>
  );
}
