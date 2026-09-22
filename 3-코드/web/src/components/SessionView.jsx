// 한눈에 화면(Proof) — 목업 07 구성을 디자인 기준(흑연)으로 다시 그림: 두 숫자 → 구성 막대 → 숫자 세 개 → 01 분당 활동 → 02 앱별 → 03 핵심 순간 → (접힌) 상세 → 04 이벤트 원본
// 문서 부품은 Doc.jsx (Learn 리포트와 공유). 사실만 보여준다 — 판정 없음.
import { useState } from 'react';
import Timeline, { Legend } from './Timeline.jsx';
import { Badge } from '@/components/ui/badge';
import { Sheet, Head, Nums, Num, Sec, Empty, Table, Fold, Foot, Dot } from './Doc.jsx';
import { COLORS, TYPE, catColor, appName, winName, pasteText, fmt, clockAt, dur } from '../lib/format.jsx';
import { stats, appSummary, moments } from '../lib/stats.js';

export default function SessionView({ s }) {
  const st = stats(s);
  const clock = (m) => clockAt(s.start, m);
  const maxPaste = s.pastes.length ? Math.max(...s.pastes.map((p) => p.len)) : 0;
  const sealed = !(s.anchor === 'none' || !s.anchor);
  const pct = (n) => (st.total ? (n / st.total) * 100 : 0);

  return (
    <Sheet wide>
      <Head kicker={`PROOF · ${s.date}`} title={`${s.work_id || s.date} 세션`}
            sub={<>{s.start} – {s.end} · {s.dur} · 이벤트 {fmt(st.events)}건 · 루트 해시 <span className="font-mono">{s.root.slice(0, 12)}…{s.root.slice(-8)}</span></>}
            right={sealed ? <Badge variant="secondary"><Dot c="var(--typed)" />봉인 · 앵커 {s.anchor}</Badge> : <Badge variant="outline">봉인 전 · 테스트</Badge>} />

      {/* 두 숫자 + 구성 막대 */}
      <Nums cols={2}>
        <Num big k="직접 입력" v={st.typed_pct} unit="%" c="var(--typed)" h={`${fmt(st.typed)}자 · 활동 분 평균 ${st.cpm}자/분 · 삭제 ${fmt(st.deleted)}자(${st.edit_ratio}%) · 되돌리기 ${st.undo}회`} />
        <Num big k="붙여넣기" v={st.pasted_pct} unit="%" h={<>{fmt(st.pasted)}자 · {st.paste_count}건 · 그중 <b style={{ color: 'var(--ai)' }}>AI 앱·사이트에서 복사한 것 {fmt(st.pasted_ai)}자 ({st.paste_ai_count}건)</b></>} />
      </Nums>
      <div className="pb-6">
        <div className="flex h-2 overflow-hidden rounded-full" style={{ background: 'var(--bg)' }}>
          <i style={{ width: `${st.typed_pct}%`, background: COLORS.typed }} />
          <i style={{ width: `${pct(st.pasted_ai)}%`, background: COLORS.pasteAI }} />
          <i style={{ width: `${pct(st.pasted_other)}%`, background: COLORS.paste }} />
        </div>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[12.5px] text-muted-foreground">
          <span className="flex items-center gap-1.5"><Dot c={COLORS.typed} />직접 입력 {fmt(st.typed)}자</span>
          <span className="flex items-center gap-1.5"><Dot c={COLORS.pasteAI} />붙여넣기 · AI에서 복사 {fmt(st.pasted_ai)}자</span>
          <span className="flex items-center gap-1.5"><Dot c={COLORS.paste} />붙여넣기 · 기타 {fmt(st.pasted_other)}자</span>
          <span className="ml-auto">결과물 총 {fmt(st.total)}자 기준</span>
        </div>
      </div>

      {/* 숫자 세 개 */}
      <Nums cols={3}>
        <Num k="AI에서 복사 → 붙여넣기" v={st.paste_ai_count} unit="건" h={`AI 앱·사이트 체류 ${st.ai_min}분(${st.ai_visits}회) · 붙여넣기 최대 ${maxPaste}자`} />
        <Num k="입력 속도 · 수정" v={st.cpm} unit="자/분" h={`최대 ${st.max_cpm}자/분 · 삭제 ÷ 입력 ${st.edit_ratio}%`} />
        <Num k="긴 멈춤" v={st.pauses} unit="회" h="작업 창에서 2분 이상 무입력 (AI 창 체류는 별도)" />
      </Nums>

      <Sec n="01" title="분당 활동" sub="활성 창 · 직접 입력 · 붙여넣기 · 삭제">
        <Timeline s={s} /><Legend />
      </Sec>

      <Sec n="02" title="앱별 활동" sub="어디서 무엇을 했나">
        <AppTable rows={appSummary(s)} />
      </Sec>

      <Sec n="03" title="핵심 순간" sub="규칙으로 자동 추출">
        <ul className="space-y-3">{moments(s, clock).map((m, i) => <Moment key={i} m={m} />)}</ul>
      </Sec>

      <Fold title="상세 활동" sub="— 창이 바뀔 때마다 한 줄, 시간순" count={`창 전환 ${(s.flow || []).length}회`}>
        <FlowTable s={s} />
      </Fold>
      <Sec n="04" title="이벤트 원본" sub="체인 그대로 — 한 줄이 한 이벤트, 앞 줄 해시가 다음 줄에 들어간다">
        <ChainTable chain={s.chain} pastes={s.pastes} />
      </Sec>

      <Foot><span>이 화면은 사실만 보여줍니다. "AI 사용 여부"를 판정하지 않습니다.</span></Foot>
    </Sheet>
  );
}

function AppTable({ rows }) {
  if (!rows.length) return <Empty>앱별 요약 없음 (derive.py 를 다시 실행하세요)</Empty>;
  const N = ({ n, unit, c }) => n ? <span style={c ? { color: c } : undefined}>{fmt(n)}{unit}</span> : <span className="text-muted-foreground/60">—</span>;
  return (
    <Table head={[{ t: '앱' }, { t: '체류', r: true }, { t: '직접 입력', r: true }, { t: '삭제', r: true }, { t: '복사', r: true }, { t: '붙여넣기', r: true }]}
      rows={rows.map((a) => ({ key: a.key, cells: [
        <span className="font-medium"><Dot c={catColor(a.cat)} className="mr-2" />{a.key}</span>,
        dur(a.dwell),
        <N n={a.typed} unit="자" c="var(--typed)" />,
        <N n={a.deleted} unit="자" c="var(--muted-foreground)" />,
        <N n={a.copy} unit="건" />,
        a.paste ? <><b style={{ color: a.pasteAI ? 'var(--ai)' : 'var(--paste)' }}>{a.paste}건 {fmt(a.pasteLen)}자</b>{a.pasteAI ? <span className="text-[12px]" style={{ color: 'var(--ai)' }}> (AI {a.pasteAI})</span> : null}</> : <span className="text-muted-foreground/60">—</span>,
      ] }))} />
  );
}

/** 창 전환 한 줄씩 — 이벤트는 사실 색(초록=입력 · 빨강=AI 붙여넣기 · 주황=기타 붙여넣기·복사) */
function FlowTable({ s }) {
  const flow = s.flow || [];
  if (!flow.length) return <Empty>창 전환 기록 없음</Empty>;
  const sep = <span className="text-muted-foreground/60"> · </span>;
  return (
    <Table head={[{ t: '시각', w: 80 }, { t: '창', w: 300 }, { t: '이벤트', wrap: true }]}
      rows={flow.map((w, i) => {
        const acts = [];
        if (w.typed || w.deleted) acts.push(<span key="k"><span style={{ color: 'var(--typed)' }}>입력 {w.typed}자</span>{w.deleted ? <> · <span className="text-muted-foreground">삭제 {w.deleted}자</span></> : null}</span>);
        w.items.forEach((it, j) => {
          if (it.kind === 'paste') { const p = { matched: !!it.src, src: it.src, ai: !!(it.src && it.src.category === 'ai') }; acts.push(<span key={j}><b style={{ color: p.ai ? 'var(--ai)' : 'var(--paste)' }}>{it.text}</b> <span className="text-muted-foreground">— {pasteText(p)}</span></span>); }
          else if (it.kind === 'copy') acts.push(<span key={j} style={{ color: 'var(--paste)' }}>{it.text}</span>);
          else if (it.kind === 'commit') acts.push(<b key={j}>{it.text}</b>);
          else acts.push(<span key={j} className={['undo', 'redo', 'cut'].includes(it.kind) ? 'text-muted-foreground' : ''}>{it.text}</span>);
        });
        return { key: i, cells: [
          <span className="font-mono text-muted-foreground">{w.ts}</span>,
          <span><Dot c={catColor(w.cat)} className="mr-2" /><b>{winName(w.app, w.title)}</b>{w.cat === 'other' && !w.title ? <span className="text-[11.5px] text-muted-foreground"> (화이트리스트 밖 · 제목 없음)</span> : null}</span>,
          acts.length ? acts.reduce((acc, a, k) => (k ? [...acc, <span key={`s${k}`}>{sep}</span>, a] : [a]), []) : <span className="text-muted-foreground/60">—</span>,
        ] };
      })} />
  );
}

function Moment({ m }) {
  const c = { typed: COLORS.typed, ai: COLORS.pasteAI, other: COLORS.paste }[m.kind];
  let body;
  if (m.paste) {
    const p = m.paste;
    body = <><b>{m.biggest ? `가장 긴 붙여넣기 ${p.len}자 → ${appName(p.target)}` : m.aiMin != null ? `${m.aiMin}분 → ${appName(p.target)}에 ${p.len}자 붙여넣기` : `${p.len}자 붙여넣기 → ${appName(p.target)}`}</b> · {pasteText(p)} · 이후 3분 직접 입력 {p.after_typed ?? '–'}자</>;
  } else body = <><b>{m.title}</b> · {m.desc}</>;
  return (
    <li className="flex gap-3 text-[14px] leading-relaxed">
      <Dot c={c} className="mt-[9px]" />
      <span className="w-[92px] shrink-0 pt-[1px] font-mono text-[12.5px] text-muted-foreground tabular-nums">{m.when}</span>
      <span>{body}</span>
    </li>
  );
}

/** 이벤트 원본 — 체인 전체. 종류로 거르고, 해시는 앞 8자만 (앞 줄 해시 = 이 줄 이전 해시가 눈으로 확인됨) */
const KINDS = [['all', '전체'], ['window', '창 전환'], ['keys', '입력'], ['copy', '복사'], ['paste', '붙여넣기'], ['edit', '되돌리기 · 잘라내기'], ['doc', '문서'], ['etc', '기타']];
const kindOf = (t) => (['undo', 'redo', 'cut'].includes(t) ? 'edit' : t.startsWith('doc_') ? 'doc' : ['window', 'keys', 'copy', 'paste'].includes(t) ? t : 'etc');
const kindColor = { keys: 'var(--typed)', copy: 'var(--paste)', paste: 'var(--paste)' };
function ChainTable({ chain, pastes = [] }) {
  const [k, setK] = useState('all');
  const aiTs = new Set(pastes.filter((p) => p.ai).map((p) => p.ts));   // 체인 요약엔 출처가 없어서 pastes 로 AI 붙여넣기를 찾는다
  const rows = chain.map((r, i) => ({ i, r })).filter(({ r }) => k === 'all' || kindOf(r[1]) === k);
  const count = (kk) => (kk === 'all' ? chain.length : chain.filter((r) => kindOf(r[1]) === kk).length);
  return (
    <>
      <div className="mb-4 flex flex-wrap gap-1.5">
        {KINDS.filter(([kk]) => count(kk)).map(([kk, label]) => (
          <button key={kk} onClick={() => setK(kk)} className={`rounded-md px-2.5 py-1 text-[12.5px] transition-colors ${k === kk ? 'font-semibold' : 'text-muted-foreground hover:text-foreground'}`}
                  style={{ background: k === kk ? 'var(--bg)' : 'transparent' }}>{label} <span className="ml-0.5 tabular-nums opacity-60">{count(kk)}</span></button>
        ))}
      </div>
      <Table className="max-h-[520px] overflow-y-auto"
        head={[{ t: '#' }, { t: '시각' }, { t: '이벤트' }, { t: '요약', wrap: true }, { t: '이전 해시' }, { t: '해시' }]}
        rows={rows.map(({ i, r }) => {
          const isAI = r[1] === 'paste' && aiTs.has(r[0]);
          const c = isAI ? 'var(--ai)' : kindColor[r[1]];
          return { key: i, cells: [
            <span className="text-muted-foreground tabular-nums">{i + 1}</span>,
            <span className="font-mono text-muted-foreground">{r[0]}</span>,
            <span style={c ? { color: c } : undefined}>{c && <Dot c={c} className="mr-1.5" />}{TYPE[r[1]] || r[1]}</span>,
            r[2],
            <span className="font-mono text-muted-foreground">{(r[3] || '').slice(0, 8)}</span>,
            <span className="font-mono">{(r[4] || '').slice(0, 8)}</span>,
          ] };
        })} />
      <p className="mt-3 text-[12px] leading-relaxed text-muted-foreground">
        hᵢ = SHA256(hᵢ₋₁ ‖ 시각 ‖ 종류 ‖ 요약). 어느 한 줄을 고치면 그 뒤 해시가 전부 달라져 루트 해시가 맞지 않는다. 전체 해시는 session.json 에 그대로 있다.
      </p>
    </>
  );
}
