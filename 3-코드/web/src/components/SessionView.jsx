// 한눈에 화면 — 목업 07 구성: 두 숫자 → 구성 막대 → 타일 → 레인 그래프 → 앱별 활동 → (접힌) 상세 → 핵심 순간 → 체인
import { useState } from 'react';
import Timeline, { Legend } from './Timeline.jsx';
import { COLORS, TYPE, catColor, appName, winName, pasteText, fmt, clockAt, dur } from '../lib/format.jsx';
import { stats, appSummary, moments } from '../lib/stats.js';

export default function SessionView({ s }) {
  const st = stats(s);
  const clock = (m) => clockAt(s.start, m);
  const maxPaste = s.pastes.length ? Math.max(...s.pastes.map((p) => p.len)) : 0;

  return (
    <>
      <div className="head">
        <div>
          <h2>{s.date} 세션 <span className="badge proof">Proof</span> {s.anchor === 'none' || !s.anchor ? <span className="badge">봉인 전 · 테스트</span> : <span className="badge ok">봉인 · 앵커 {s.anchor}</span>}</h2>
          <div className="sub">{s.start} – {s.end} · {s.dur} · 이벤트 {st.events}건 · 루트 해시 <span className="mono">{s.root.slice(0, 12)}…{s.root.slice(-8)}</span></div>
        </div>
      </div>

      {/* 두 숫자 + 구성 막대 */}
      <div className="hero">
        <div className="h"><div className="lbl">직접 입력</div><div className="big" style={{ color: '#047857' }}>{st.typed_pct}%</div>
          <div className="sm">{fmt(st.typed)}자 · 활동 분 평균 {st.cpm}자/분 · 삭제 {fmt(st.deleted)}자({st.edit_ratio}%) · 되돌리기 {st.undo}회</div></div>
        <div className="h"><div className="lbl">붙여넣기</div><div className="big" style={{ color: '#b91c1c' }}>{st.pasted_pct}%</div>
          <div className="sm">{fmt(st.pasted)}자 · {st.paste_count}건 · 그중 <b style={{ color: '#b91c1c' }}>AI 앱·사이트에서 복사한 것 {fmt(st.pasted_ai)}자 ({st.paste_ai_count}건)</b></div></div>
        <div className="h full">
          <div className="comp">
            <i style={{ width: `${st.typed_pct}%`, background: COLORS.typed }} />
            <i style={{ width: `${st.total ? (st.pasted_ai / st.total) * 100 : 0}%`, background: COLORS.pasteAI }} />
            <i style={{ width: `${st.total ? (st.pasted_other / st.total) * 100 : 0}%`, background: COLORS.paste }} />
          </div>
          <div className="legend">
            <span><i style={{ background: COLORS.typed }} />직접 입력 {fmt(st.typed)}자</span>
            <span><i style={{ background: COLORS.pasteAI }} />붙여넣기 · AI에서 복사 {fmt(st.pasted_ai)}자</span>
            <span><i style={{ background: COLORS.paste }} />붙여넣기 · 기타 {fmt(st.pasted_other)}자</span>
            <span style={{ marginLeft: 'auto' }}>결과물 총 {fmt(st.total)}자 기준</span>
          </div>
        </div>
      </div>

      {/* 타일 3 */}
      <div className="tiles">
        <Tile k="AI에서 복사 → 붙여넣기" v={st.paste_ai_count} unit="건" h={`AI 앱·사이트 체류 ${st.ai_min}분(${st.ai_visits}회) · 붙여넣기 최대 ${maxPaste}자`} />
        <Tile k="입력 속도 · 수정" v={st.cpm} unit="자/분" h={`최대 ${st.max_cpm}자/분 · 삭제 ÷ 입력 ${st.edit_ratio}%`} />
        <Tile k="긴 멈춤" v={st.pauses} unit="회" h="작업 창에서 2분 이상 무입력 (AI 창 체류는 별도)" />
      </div>

      {/* 그래프 */}
      <div className="card"><h4>분당 활동</h4><Timeline s={s} /><Legend /></div>

      {/* 앱별 활동 */}
      <div className="card"><h4>앱별 활동 — 어디서 무엇을 했나</h4><AppTable rows={appSummary(s)} /></div>

      {/* 접힌 상세 */}
      <FlowDetails s={s} />

      {/* 핵심 순간 */}
      <h4 className="sect">핵심 순간 — 규칙으로 자동 추출</h4>
      <div className="moments">
        {moments(s, clock).map((m, i) => <Moment key={i} m={m} />)}
      </div>

      <details className="chain"><summary>체인 원본 {s.chain.length}건 (SHA-256 · hᵢ = SHA256(hᵢ₋₁ ‖ 시각 ‖ 종류 ‖ 요약))</summary>
        <div className="card scroll"><table>
          <thead><tr><th>#</th><th>시각</th><th>이벤트</th><th>요약</th><th>이전 해시</th><th>해시</th></tr></thead>
          <tbody>{s.chain.map((r, i) => (
            <tr key={i}><td className="dim">{i + 1}</td><td className="mono">{r[0]}</td><td>{TYPE[r[1]] || r[1]}</td><td className="sum">{r[2]}</td>
              <td className="mono dim">{(r[3] || '').slice(0, 8)}…</td><td className="mono">{(r[4] || '').slice(0, 8)}…{(r[4] || '').slice(-4)}</td></tr>
          ))}</tbody></table></div>
      </details>

      <div className="foot"><span>이 화면은 사실만 보여줍니다. "AI 사용 여부"를 판정하지 않습니다.</span></div>
    </>
  );
}

function Tile({ k, v, unit, h }) {
  return <div className="tile"><div className="k">{k}</div><div className="v">{v}<small>{unit}</small></div><div className="h">{h}</div></div>;
}

function Dot({ cat }) { return <i className="dot" style={{ background: catColor(cat) }} />; }

function AppTable({ rows }) {
  if (!rows.length) return <p className="sub">앱별 요약 없음 (derive.py 를 다시 실행하세요)</p>;
  const R = ({ n, unit, color }) => n ? <span style={{ color }}>{n}{unit}</span> : <span className="dim">—</span>;
  return (
    <table className="apps">
      <thead><tr><th>앱</th><th className="r">체류</th><th className="r">직접 입력</th><th className="r">삭제</th><th className="r">복사</th><th className="r">붙여넣기</th></tr></thead>
      <tbody>{rows.map((a) => (
        <tr key={a.key}>
          <td className="n"><Dot cat={a.cat} />{a.key}</td>
          <td className="r">{dur(a.dwell)}</td>
          <td className="r"><R n={a.typed} unit="자" color="#047857" /></td>
          <td className="r"><R n={a.deleted} unit="자" color="#6b7280" /></td>
          <td className="r"><R n={a.copy} unit="건" color="#b45309" /></td>
          <td className="r">{a.paste ? <><span style={{ color: a.pasteAI ? '#b91c1c' : '#b45309', fontWeight: 600 }}>{a.paste}건 {a.pasteLen}자</span>{a.pasteAI ? <span style={{ color: '#b91c1c', fontSize: 12 }}> (AI에서 {a.pasteAI})</span> : null}</> : <span className="dim">—</span>}</td>
        </tr>
      ))}</tbody>
    </table>
  );
}

function FlowDetails({ s }) {
  const [open, setOpen] = useState(false);
  const flow = s.flow || [];
  return (
    <div className="flowwrap">
      <button className={`toggle ${open ? 'open' : ''}`} onClick={() => setOpen(!open)}>
        <span className="arr">▶</span>상세 활동 보기 <span className="sub2">— 창이 바뀔 때마다 한 줄, 시간순</span><span className="cnt">창 전환 {flow.length}회</span>
      </button>
      {open && (
        <div className="flowbox"><table>
          <thead><tr><th style={{ width: 80 }}>시각</th><th style={{ width: 300 }}>창</th><th>이벤트</th></tr></thead>
          <tbody>{flow.map((w, i) => {
            const acts = [];
            if (w.typed || w.deleted) acts.push(<span key="k"><span style={{ color: '#047857' }}>입력 {w.typed}자</span>{w.deleted ? <> · <span style={{ color: '#6b7280' }}>삭제 {w.deleted}자</span></> : null}</span>);
            w.items.forEach((it, j) => {
              if (it.kind === 'paste') { const p = { matched: !!it.src, src: it.src, ai: !!(it.src && it.src.category === 'ai') }; acts.push(<span key={j}><span style={{ color: p.ai ? '#b91c1c' : '#b45309', fontWeight: 600 }}>{it.text}</span> <span style={{ color: '#6b7280' }}>— {pasteText(p)}</span></span>); }
              else if (it.kind === 'copy') acts.push(<span key={j} style={{ color: '#b45309' }}>{it.text}</span>);
              else if (it.kind === 'commit') acts.push(<span key={j} style={{ color: '#0f766e', fontWeight: 600 }}>{it.text}</span>);
              else if (['undo', 'redo', 'cut'].includes(it.kind)) acts.push(<span key={j} style={{ color: '#6d28d9' }}>{it.text}</span>);
              else acts.push(<span key={j}>{it.text}</span>);
            });
            return (
              <tr key={i}>
                <td className="mono dim">{w.ts}</td>
                <td><Dot cat={w.cat} /><b>{winName(w.app, w.title)}</b>{w.cat === 'other' && !w.title ? <span className="note"> (화이트리스트 밖 · 제목 없음)</span> : null}</td>
                <td className="sum">{acts.length ? acts.reduce((acc, a, k) => (k ? [...acc, <span key={`s${k}`} className="dim"> · </span>, a] : [a]), []) : <span className="dim">—</span>}</td>
              </tr>
            );
          })}</tbody>
        </table></div>
      )}
    </div>
  );
}

function Moment({ m }) {
  const color = { typed: COLORS.typed, ai: COLORS.pasteAI, other: COLORS.paste }[m.kind];
  let body;
  if (m.paste) {
    const p = m.paste;
    body = <><b>{m.biggest ? `가장 긴 붙여넣기 ${p.len}자 → ${appName(p.target)}` : m.aiMin != null ? `${m.aiMin}분 → ${appName(p.target)}에 ${p.len}자 붙여넣기` : `${p.len}자 붙여넣기 → ${appName(p.target)}`}</b> · {pasteText(p)} · 이후 3분 직접 입력 {p.after_typed ?? '–'}자</>;
  } else body = <><b>{m.title}</b> · {m.desc}</>;
  return <div className="mom"><span className="ic" style={{ background: color }} /><span className="t">{m.when}</span><span className="x">{body}</span></div>;
}
