// Trace 화면 (React) — Proof "한눈에"(SessionView) + Learn(LearnView). 데이터는 세 곳에서 온다:
//   ① 샘플(public/sample_session.json)  ② session.json 파일 드롭  ③ 서버 GET /api/sessions/{id}  (vite.config 의 proxy → 127.0.0.1:5000)
// A의 React 골격(라우터·로그인·Dashboard)이 생기면 <SessionView s={...}/> 만 그쪽 라우트에 끼우면 된다.
import { useState } from 'react';
import SessionView from './components/SessionView.jsx';
import LearnView from './components/LearnView.jsx';
import DesignGuide from './components/DesignGuide.jsx';
import * as api from './lib/api.js';

export default function App() {
  const [s, setS] = useState(null);
  const [learn, setLearn] = useState(null);   // {ctx, report, live} — Learn 세션일 때만
  const [sid, setSid] = useState('');
  const [err, setErr] = useState('');
  const [guide, setGuide] = useState(false); // 디자인 기준 페이지 (팔레트 후보 · 부품)

  const loadSample = () => fetch('/sample_session.json').then((r) => r.json()).then((d) => { setS(d); setLearn(null); }).catch((e) => setErr(String(e)));
  const loadLearnSample = () => fetch('/sample_learn.json').then((r) => r.json()).then((d) => { setS(d.session); setLearn({ ctx: d.context, report: d.report, live: false }); }).catch((e) => setErr(String(e)));
  const loadServer = () => {
    if (!sid.trim()) return;
    setErr('');
    api.getSession(sid.trim()).then(async (d) => {
      setS(d);
      if (d.mode === 'learn') {
        // 맥락은 GET /context (제안 · 서버에 아직 없으면 빈 채로) · 리포트는 열 때 GET (여기선 안 부름)
        const ctx = await api.getContext(d.id).then((r) => r.items || []).catch(() => []);
        setLearn({ ctx, report: null, live: true });
      } else setLearn(null);
    }).catch((e) => setErr(`서버에서 못 가져옴: ${api.explain(e)}`));
  };
  const readFile = (f) => {
    if (!f) return;
    const r = new FileReader();
    r.onload = () => { try { const d = JSON.parse(r.result); if (d.session) { setS(d.session); setLearn({ ctx: d.context || [], report: d.report || null, live: false }); } else { setS(d); setLearn(null); } setErr(''); } catch (e) { setErr(`JSON 오류: ${e.message}`); } };
    r.readAsText(f, 'utf-8');
  };

  if (guide) return <DesignGuide onClose={() => setGuide(false)} />;   // 디자인 기준은 자기 상단 줄을 가진 전체 화면
  return (
    <div onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); readFile(e.dataTransfer.files[0]); }}>
      <header>
        <b>Trace</b><span className="sub">{learn ? 'Learn' : '한눈에'} · React</span>
        <span style={{ marginLeft: 'auto' }} />
        <input value={sid} onChange={(e) => setSid(e.target.value)} placeholder="서버 세션 id (UUID)" onKeyDown={(e) => e.key === 'Enter' && loadServer()} />
        <button className="btn" onClick={loadServer}>서버에서</button>
        <button className="btn" onClick={() => setGuide(true)}>디자인 기준</button>
        <button className="btn" onClick={loadSample}>샘플 · Proof</button>
        <button className="btn" onClick={loadLearnSample}>샘플 · Learn</button>
        <label className="btn primary">session.json 열기<input type="file" accept=".json" hidden onChange={(e) => readFile(e.target.files[0])} /></label>
      </header>
      <main>
        {err && <p className="err">{err}</p>}
        {s ? (learn ? <LearnView key={s.id} s={s} ctx={learn.ctx} report={learn.report} live={learn.live} /> : <SessionView s={s} />) : (
          <div className="drop">
            <div style={{ fontSize: 28 }}>⇩</div>
            <b>session.json 을 여기에 끌어다 놓으세요</b><br />
            또는 [샘플 · Proof] [샘플 · Learn] · 서버가 켜져 있으면 세션 id 입력 후 [서버에서]<br /><br />
            <span className="mono">python core/derive.py "data/events-*.jsonl"</span> 이 만든 파일입니다.
          </div>
        )}
      </main>
    </div>
  );
}
