// Trace 화면 (React) — 지금은 "한눈에" 하나. 데이터는 세 곳에서 온다:
//   ① 샘플(public/sample_session.json)  ② session.json 파일 드롭  ③ 서버 GET /api/sessions/{id}  (vite.config 의 proxy → 127.0.0.1:5000)
// A의 React 골격(라우터·로그인·Dashboard)이 생기면 <SessionView s={...}/> 만 그쪽 라우트에 끼우면 된다.
import { useState } from 'react';
import SessionView from './components/SessionView.jsx';

export default function App() {
  const [s, setS] = useState(null);
  const [sid, setSid] = useState('');
  const [err, setErr] = useState('');

  const loadSample = () => fetch('/sample_session.json').then((r) => r.json()).then(setS).catch((e) => setErr(String(e)));
  const loadServer = () => {
    if (!sid.trim()) return;
    setErr('');
    fetch(`/api/sessions/${sid.trim()}`).then((r) => (r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))).then(setS).catch((e) => setErr(`서버에서 못 가져옴: ${e}`));
  };
  const readFile = (f) => {
    if (!f) return;
    const r = new FileReader();
    r.onload = () => { try { setS(JSON.parse(r.result)); setErr(''); } catch (e) { setErr(`JSON 오류: ${e.message}`); } };
    r.readAsText(f, 'utf-8');
  };

  return (
    <div onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); readFile(e.dataTransfer.files[0]); }}>
      <header>
        <b>Trace</b><span className="sub">한눈에 · React</span>
        <span style={{ marginLeft: 'auto' }} />
        <input value={sid} onChange={(e) => setSid(e.target.value)} placeholder="서버 세션 id (UUID)" onKeyDown={(e) => e.key === 'Enter' && loadServer()} />
        <button className="btn" onClick={loadServer}>서버에서</button>
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
