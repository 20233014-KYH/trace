// Learn 세션 화면 — 목업 14(타임라인 + 맥락) · 16(Learning Report) · 13b/13c(알약 위 질문칸).
// 입력: s(session.json · 계약 ②) · ctx(맥락 항목들 · 계약 ③ 5절) · report(GET /report 결과 또는 null)
// 서버 호출은 lib/api.js 만. 샘플 모드(public/sample_learn.json)면 서버 없이 가짜 답으로 돈다.
import { useMemo, useState } from 'react';
import Timeline from './Timeline.jsx';
import ContextPanel from './ContextPanel.jsx';
import ReportView from './ReportView.jsx';
import AskBox, { Pill } from './AskBox.jsx';
import { markers, ctxCounts, KIND, LEGEND, clockS } from '../lib/learn.js';
import { fmt } from '../lib/format.jsx';
import { stats } from '../lib/stats.js';
import * as api from '../lib/api.js';

export default function LearnView({ s, ctx = [], report: report0 = null, live = false }) {
  const [tab, setTab] = useState('timeline');
  const [sel, setSel] = useState(null);
  const mks = useMemo(() => markers(s, ctx), [s, ctx]);
  const st = stats(s), cc = ctxCounts(s, ctx);

  // ── 리포트: 열 때 생성 (GET) · 다시 생성 (POST)
  const [report, setReport] = useState(report0);
  const [rstate, setRstate] = useState(report0 ? 'ready' : 'none');
  const [rerr, setRerr] = useState('');
  const loadReport = async (regen = false) => {
    setRstate('loading'); setRerr('');
    try {
      const r = live ? await (regen ? api.regenReport(s.id) : api.getReport(s.id)) : await fakeReport(report0, regen);
      setReport(r); setRstate('ready');
    } catch (e) { setRerr(api.explain(e)); setRstate(report ? 'ready' : 'error'); }
  };

  // ── 물어보기 (Side Chat 과 같은 /chat)
  const [askOpen, setAskOpen] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [aerr, setAerr] = useState('');
  const [seed, setSeed] = useState('');
  const send = async (q) => {
    setMsgs((m) => [...m, { role: 'user', text: q }]); setBusy(true); setAerr('');
    try {
      const r = live ? await api.chat(s.id, q) : { answer: `(가짜 답변) "${q.slice(0, 30)}" — 서버가 켜져 있으면 GPT-5.6 Luna 가 이 세션의 최근 오류·질문을 근거로 답합니다.` };
      setMsgs((m) => [...m, { role: 'ai', text: r.answer }]);
    } catch (e) { setAerr(api.explain(e)); }
    setBusy(false);
  };
  const askFrom = (text) => { setSeed(text ? `${text.slice(0, 80)}\n\n이 부분이 왜 그런지 설명해줘` : ''); setAskOpen(true); };

  return (
    <div className="learn">
      <div className="head">
        <div>
          <h2>{s.date} · {s.work_id || '세션'} <span className="badge learn">Learn</span></h2>
          <div className="sub">{s.start.slice(0, 5)}–{s.end.slice(0, 5)} · {s.dur} · AI 질문 {cc.questions + cc.chats} · 참고 페이지 {cc.pages} · 오류 {cc.errors} → 해결 {cc.solved} · 직접 입력 {fmt(st.typed)}자 · 붙여넣기 {st.paste_count}건 {fmt(st.pasted)}자</div>
        </div>
        <span style={{ marginLeft: 'auto' }} />
        <button className="btn" title="목업 17 · 항목별 토글은 수집기 config.json (learn_context)">수집 설정</button>
        <button className="btn primary" onClick={() => { setTab('report'); if (rstate === 'none') loadReport(); }}>Learning Report</button>
      </div>

      <nav className="tabs">
        {[['timeline', '타임라인 + 맥락'], ['report', 'Learning Report'], ['raw', '이벤트 원본']].map(([k, t]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{t}</button>
        ))}
      </nav>

      {tab === 'timeline' && (
        <div className="split">
          <div>
            <div className="card">
              <h4>학습 흐름 — 마커를 누르면 오른쪽에 맥락</h4>
              <Timeline s={s} markers={mks} selected={sel} onMarker={(id) => setSel(id === sel ? null : id)} />
              <div className="legend">
                {LEGEND.map((k) => <span key={k}><b style={{ color: KIND[k].c }}>{KIND[k].ic}</b> {KIND[k].t}</span>)}
                <span><i style={{ background: '#10b981' }} />직접 입력</span>
              </div>
            </div>
            <h4 className="sect">이 세션의 학습 흐름 — 이벤트를 AI 가 묶은 것</h4>
            {rstate === 'ready' && report?.process?.length ? report.process.map((line, i) => (
              <div key={i} className="card flowcard"><span className="n">{i + 1}</span><span>{line}</span></div>
            )) : (
              <div className="card center sm"><span className="sub">Learning Report 를 열면 AI 가 흐름을 묶어 여기에도 보여줍니다.</span> <button className="btn sm" onClick={() => { setTab('report'); if (rstate === 'none') loadReport(); }}>열기</button></div>
            )}
          </div>
          <ContextPanel s={s} ctx={ctx} mk={mks.find((m) => m.id === sel)} onAsk={askFrom} />
        </div>
      )}

      {tab === 'report' && <ReportView s={s} ctx={ctx} report={report} state={rstate} error={rerr} onOpen={() => loadReport(false)} onRegen={() => loadReport(true)} />}

      {tab === 'raw' && (
        <div className="card scroll"><table>
          <thead><tr><th>시각</th><th>출처</th><th>종류</th><th>내용</th></tr></thead>
          <tbody>{ctx.map((it) => (
            <tr key={it.id}><td className="mono dim">{clockS(it.ts)}</td><td>{it.source}</td><td>{KIND[it.kind]?.t || it.kind}</td><td className="sum">{it.text || <span className="dim">{JSON.stringify(it.meta)}</span>}</td></tr>
          ))}</tbody>
        </table><p className="note">맥락 원본 {ctx.length}건 (계약 ③ 5절). 이벤트 체인은 Proof 와 같은 형식 — "한눈에" 탭에서.</p></div>
      )}

      <div className="foot">Learn Mode 는 AI 사용 여부를 판정하지 않습니다. 보는 것은 "AI 를 쓴 뒤 무엇을 했는가" 입니다.</div>

      <AskBox open={askOpen} setOpen={setAskOpen} msgs={msgs} busy={busy} error={aerr} seed={seed} onSend={send}
              pill={<Pill elapsed={s.dur} ctxCount={ctx.length} />} />
    </div>
  );
}

/** 서버 없을 때 — 열기 흉내 (1.2초 뒤 샘플 리포트) */
function fakeReport(sample, regen) {
  return new Promise((ok) => setTimeout(() => ok({ ...(sample || EMPTY), provider: 'fake', runs: regen ? (sample?.runs || 1) + 1 : 1, generated_at: new Date().toISOString(), _fake: true }), 1200));
}
const EMPTY = { status: 'ready', topics: ['(가짜) 예외 처리'], struggles: [], process: ['오류 발생 → AI에게 질문 → 답변 참고 → 직접 수정 → 재실행 → 해결'], points: [], todo: [] };
