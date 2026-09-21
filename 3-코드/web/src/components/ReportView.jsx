// Learning Session Report — 목업 16. 서버 GET /report 가 준 JSON 5항목을 그대로 놓는다. 점수 없음.
// 상태: none(열면 생성) → loading → ready | error. 다시 생성은 POST (세션당 3회).
import { fmt } from '../lib/format.jsx';
import { stats } from '../lib/stats.js';
import { ctxCounts } from '../lib/learn.js';

export default function ReportView({ s, ctx, report, state, error, onOpen, onRegen }) {
  const st = stats(s), cc = ctxCounts(s, ctx);

  return (
    <>
      <div className="tiles four">
        <Tile k="직접 입력" v={fmt(st.typed)} unit="자" c="#047857" h={`붙여넣기 ${fmt(st.pasted)}자 · ${st.paste_count}건${st.paste_ai_count ? ` · 그중 AI에서 ${st.paste_ai_count}건` : ''}`} />
        <Tile k="AI 질문" v={cc.questions + cc.chats} c="#0369a1" h={`사이트에서 ${cc.questions} · 물어보기 ${cc.chats}`} />
        <Tile k="오류 → 해결" v={<>{cc.solved}<small>/{cc.errors}</small></>} h={cc.errors ? '실행 결과가 정상이 된 횟수' : '오류 기록 없음'} />
        <Tile k="참고 페이지" v={cc.pages} h={`학습자료 체류 ${cc.resMin}분`} />
      </div>

      {state === 'none' && (
        <div className="card center">
          <b>아직 리포트가 없습니다</b>
          <p className="sub">열면 그때 AI 가 이 세션의 이벤트와 맥락으로 정리합니다 (세션 종료 시 자동 생성 안 함 — 안 보는 세션엔 비용 0).</p>
          <button className="btn primary" onClick={onOpen}>Learning Report 열기</button>
        </div>
      )}
      {state === 'loading' && <div className="card center"><b>AI 가 정리하는 중…</b><p className="sub">이벤트 흐름 + 맥락 {ctx.length}건. 보통 10초 안팎.</p></div>}
      {state === 'error' && <div className="card center"><p className="err">{error}</p><button className="btn" onClick={onOpen}>다시 시도</button></div>}

      {state === 'ready' && report && (
        <>
          <div className="rep2">
            <Box t="이번 세션의 주요 학습 내용" items={report.topics} />
            <Box t="가장 많은 어려움을 겪은 부분" items={report.struggles} />
          </div>
          <div className="card">
            <h4>학습 과정 — 이벤트를 AI 가 순서로 묶음</h4>
            {(report.process || []).map((line, i) => <Flow key={i} n={i + 1} line={line} />)}
          </div>
          <div className="rep2">
            <Box t="학습 포인트" items={report.points} />
            <Box t="추가 학습이 필요한 부분" items={report.todo} warn />
          </div>
          <div className="foot rep">
            <span>이 리포트는 세션의 이벤트와 맥락(AI 질문·답변 발췌·참고 페이지·오류·문서 변화)을 AI 가 정리한 것입니다. 점수·등급이 아니며, 내 PC 와 내 계정에만 저장됩니다.</span>
            <span style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}>
              생성 {report.generated_at ? report.generated_at.slice(11, 16) : ''} · {report.provider}{report._fake || report.provider === 'fake' ? ' (가짜 · 키 없음)' : ''} · {report.runs || 1}/3회
              <button className="btn sm" onClick={onRegen} disabled={(report.runs || 1) >= 3}>다시 생성</button>
            </span>
          </div>
        </>
      )}
    </>
  );
}

function Tile({ k, v, unit, h, c }) {
  return <div className="tile"><div className="k">{k}</div><div className="v" style={{ color: c }}>{v}{unit && <small>{unit}</small>}</div><div className="h">{h}</div></div>;
}
function Box({ t, items = [], warn }) {
  return (
    <div className={`card ${warn ? 'warn' : ''}`}><h4>{t}</h4>
      {items.length ? <ul className="rep">{items.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="dim">근거가 없어 비움</p>}
    </div>
  );
}
/** "오류 발생 → AI에게 질문 → …" 한 줄을 칩 나열로 */
function Flow({ n, line }) {
  const steps = line.split('→').map((x) => x.trim()).filter(Boolean);
  const strong = (x) => /직접|해결|재실행/.test(x);
  return (
    <div className="flowline"><span className="n">{n}</span>
      {steps.map((x, i) => <span key={i}><span className={`chip ${strong(x) ? 'on' : ''}`}>{x}</span>{i < steps.length - 1 && <span className="arr">→</span>}</span>)}
    </div>
  );
}
