// Learn 세션 화면 — 목업 14(타임라인 + 맥락) · 16(Learning Report) · 13b/13c(알약 위 질문칸). 디자인 기준(흑연) — Doc.jsx 부품 위에.
// 입력: s(session.json · 계약 ②) · ctx(맥락 항목들 · 계약 ③ 5절) · report(GET /report 결과 또는 null)
// 서버 호출은 lib/api.js 만. 샘플 모드(public/sample_learn.json)면 서버 없이 가짜 답으로 돈다.
import { useMemo, useState } from 'react';
import { Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Timeline from './Timeline.jsx';
import ContextPanel from './ContextPanel.jsx';
import ReportView from './ReportView.jsx';
import AskBox, { Pill } from './AskBox.jsx';
import { Sheet, Head, Sec, Empty, Table, Foot, Dot, FlowLine } from './Doc.jsx';
import { markers, ctxCounts, KIND, LEGEND, clockS } from '../lib/learn.js';
import { COLORS, fmt } from '../lib/format.jsx';
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
  const openReport = () => { setTab('report'); if (rstate === 'none') loadReport(); };

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
    <>
      <Sheet wide>
        <Head kicker={`LEARN · ${s.date}`} title={s.work_id || '세션'}
              sub={<>{s.start.slice(0, 5)}–{s.end.slice(0, 5)} · {s.dur} · AI 질문 {cc.questions + cc.chats} · 참고 페이지 {cc.pages} · 오류 {cc.errors} → 해결 {cc.solved} · 직접 입력 {fmt(st.typed)}자 · 붙여넣기 {st.paste_count}건 {fmt(st.pasted)}자</>}
              right={<>
                <Badge variant="secondary"><Dot c="var(--learn)" />Learn</Badge>
                <Button variant="ghost" size="sm" title="목업 17 · 항목별 토글은 수집기 config.json (learn_context)"><Settings2 /> 수집 설정</Button>
                <Button size="sm" onClick={openReport}>Learning Report</Button>
              </>} />

        <Tabs value={tab} onValueChange={setTab} className="mb-2">
          <TabsList variant="line" className="-mb-px">
            <TabsTrigger value="timeline">타임라인 + 맥락</TabsTrigger>
            <TabsTrigger value="report" onClick={() => rstate === 'none' && loadReport()}>Learning Report</TabsTrigger>
            <TabsTrigger value="raw">이벤트 원본</TabsTrigger>
          </TabsList>
        </Tabs>

        {tab === 'timeline' && (
          <div className="grid gap-8 md:grid-cols-[1fr_320px]">
            <div className="min-w-0">
              <Sec n="01" title="학습 흐름" sub="마커를 누르면 오른쪽에 맥락">
                <Timeline s={s} markers={mks} selected={sel} onMarker={(id) => setSel(id === sel ? null : id)} />
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-[12.5px] text-muted-foreground">
                  {LEGEND.map((k) => <span key={k} className="flex items-center gap-1.5"><b style={{ color: KIND[k].c }}>{KIND[k].ic}</b>{KIND[k].t}</span>)}
                  <span className="flex items-center gap-1.5"><Dot c={COLORS.typed} />직접 입력</span>
                </div>
              </Sec>
              <Sec n="02" title="흐름을 묶으면" sub="이벤트를 AI 가 순서로 묶은 것">
                {rstate === 'ready' && report?.process?.length
                  ? <ol className="space-y-3">{report.process.map((line, i) => <FlowLine key={i} n={i + 1} line={line} />)}</ol>
                  : <div className="flex flex-wrap items-center gap-3"><Empty>Learning Report 를 열면 AI 가 흐름을 묶어 여기에도 보여줍니다.</Empty><Button variant="outline" size="sm" onClick={openReport}>열기</Button></div>}
              </Sec>
            </div>
            <div className="pt-8"><ContextPanel s={s} ctx={ctx} mk={mks.find((m) => m.id === sel)} onAsk={askFrom} /></div>
          </div>
        )}

        {tab === 'report' && <ReportView bare s={s} ctx={ctx} report={report} state={rstate} error={rerr} onOpen={() => loadReport(false)} onRegen={() => loadReport(true)} />}

        {tab === 'raw' && (
          <Sec n="01" title="맥락 원본" sub={`${ctx.length}건 · 계약 ③ 5절`}>
            <Table className="max-h-[560px] overflow-y-auto"
              head={[{ t: '시각' }, { t: '출처' }, { t: '종류' }, { t: '내용', wrap: true }]}
              rows={ctx.map((it) => {
                const k = KIND[it.kind];
                return { key: it.id, cells: [
                  <span className="font-mono text-muted-foreground">{clockS(it.ts)}</span>,
                  <span className="text-muted-foreground">{it.source}</span>,
                  <span className="whitespace-nowrap">{k && <b className="mr-1.5" style={{ color: k.c }}>{k.ic}</b>}{k?.t || it.kind}</span>,
                  <span className="whitespace-pre-wrap break-all">{it.text || <span className="font-mono text-[12px] text-muted-foreground">{JSON.stringify(it.meta)}</span>}</span>,
                ] };
              })} />
            <p className="mt-3 text-[12px] text-muted-foreground">이벤트 체인은 Proof 와 같은 형식 — 한눈에 화면의 "이벤트 원본"에서.</p>
          </Sec>
        )}

        {tab !== 'report' && <Foot><span>Learn Mode 는 AI 사용 여부를 판정하지 않습니다. 보는 것은 "AI 를 쓴 뒤 무엇을 했는가" 입니다.</span></Foot>}
      </Sheet>

      <AskBox open={askOpen} setOpen={setAskOpen} msgs={msgs} busy={busy} error={aerr} seed={seed} onSend={send}
              pill={<Pill elapsed={s.dur} ctxCount={ctx.length} />} />
    </>
  );
}

/** 서버 없을 때 — 열기 흉내 (1.2초 뒤 샘플 리포트) */
function fakeReport(sample, regen) {
  return new Promise((ok) => setTimeout(() => ok({ ...(sample || EMPTY), provider: 'fake', runs: regen ? (sample?.runs || 1) + 1 : 1, generated_at: new Date().toISOString(), _fake: true }), 1200));
}
const EMPTY = { status: 'ready', topics: ['(가짜) 예외 처리'], struggles: [], process: ['오류 발생 → AI에게 질문 → 답변 참고 → 직접 수정 → 재실행 → 해결'], points: [], todo: [] };
