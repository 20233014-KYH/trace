// Learning Session Report — 목업 16 을 디자인 기준(흑연)으로 다시 그림. 서버 GET /report 가 준 JSON 5항목을 읽는 문서처럼 놓는다. 점수 없음.
// 문서 부품은 Doc.jsx (Proof 한눈에와 공유). 상태: none(열면 생성) → loading → ready | error. 다시 생성은 POST (세션당 3회).
import { Circle, LoaderCircle, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, Head, Nums, Num, Sec, Empty, Foot, FlowLine } from './Doc.jsx';
import { fmt } from '../lib/format.jsx';
import { stats } from '../lib/stats.js';
import { ctxCounts, clock } from '../lib/learn.js';

export default function ReportView({ s, ctx, report, state, error, onOpen, onRegen, bare = false }) {
  const st = stats(s), cc = ctxCounts(s, ctx);
  const runs = report?.runs || 1;
  const Wrap = bare ? Bare : Sheet;   // bare: LearnView 시트 안에 들어갈 때 (머리는 LearnView 가 그림)

  return (
    <Wrap>
      {!bare && <Head kicker={`LEARNING REPORT · ${s.date}`} title={`${s.work_id || '세션'} 학습 리포트`}
            sub={`${s.start.slice(0, 5)}–${s.end.slice(0, 5)} · ${s.dur} · 이벤트 ${fmt(st.events)}건 · 맥락 ${ctx.length}건`} />}

      <Nums>
        <Num k="직접 입력" v={st.typed} unit="자" c="var(--typed)" h={`붙여넣기 ${fmt(st.pasted)}자 · ${st.paste_count}건${st.paste_ai_count ? ` (AI ${st.paste_ai_count})` : ''}`} />
        <Num k="AI 질문" v={cc.questions + cc.chats} h={`사이트 ${cc.questions} · 물어보기 ${cc.chats}`} />
        <Num k="오류 → 해결" v={cc.solved} unit={`/ ${cc.errors}`} h={cc.errors ? '실행 결과가 정상이 된 횟수' : '오류 기록 없음'} />
        <Num k="참고 페이지" v={cc.pages} h={`학습자료 체류 ${cc.resMin}분`} />
      </Nums>

      {state === 'none' && (
        <Center title="아직 리포트가 없습니다" desc="열면 그때 AI 가 이 세션의 이벤트와 맥락으로 정리합니다. 세션이 끝나도 자동 생성하지 않음 — 안 보는 세션엔 비용 0.">
          <Button onClick={onOpen}>Learning Report 열기</Button>
        </Center>
      )}
      {state === 'loading' && (
        <Center title={<span className="inline-flex items-center gap-2"><LoaderCircle className="size-4 animate-spin text-muted-foreground" /> AI 가 정리하는 중</span>} desc={`이벤트 흐름 + 맥락 ${ctx.length}건. 보통 10초 안팎.`} />
      )}
      {state === 'error' && (
        <Center title="리포트를 못 만들었습니다" desc={error}><Button variant="outline" onClick={onOpen}>다시 시도</Button></Center>
      )}

      {state === 'ready' && report && (
        <>
          <Sec n="01" title="이번 세션의 주요 학습 내용"><List items={report.topics} /></Sec>

          <Sec n="02" title="학습 과정" sub="이벤트를 AI 가 순서로 묶음">
            <ol className="space-y-3">
              {(report.process || []).map((line, i) => <FlowLine key={i} n={i + 1} line={line} />)}
              {!report.process?.length && <Empty />}
            </ol>
          </Sec>

          <Sec n="03" title="가장 많은 어려움을 겪은 부분">
            {report.struggles?.length
              ? <div className="space-y-2">{report.struggles.map((x, i) => <p key={i} className="rounded-xl px-5 py-4 text-[15px] leading-relaxed" style={{ background: 'var(--bg)' }}>{x}</p>)}</div>
              : <Empty />}
          </Sec>

          <Sec n="04" title="학습 포인트"><List items={report.points} /></Sec>

          <Sec n="05" title="추가 학습이 필요한 부분" sub="다음 세션에서 확인할 것">
            {report.todo?.length
              ? <ul className="space-y-2.5">{report.todo.map((x, i) => <li key={i} className="flex gap-3 text-[15px] leading-relaxed"><Circle className="mt-[7px] size-3 shrink-0 text-muted-foreground" strokeWidth={1.5} />{x}</li>)}</ul>
              : <Empty />}
          </Sec>

          <Foot>
            <span className="max-w-md">이 리포트는 세션의 이벤트와 맥락(AI 질문·답변 발췌·참고 페이지·오류·문서 변화)을 AI 가 정리한 것입니다. 점수·등급이 아니며, 내 PC 와 내 계정에만 저장됩니다.</span>
            <span className="ml-auto flex items-center gap-3 whitespace-nowrap tabular-nums">
              {report.generated_at ? clock(report.generated_at) : ''} · {report.provider}{report._fake || report.provider === 'fake' ? ' (가짜 · 키 없음)' : ''} · {runs}/3회
              <Button size="sm" variant="ghost" onClick={onRegen} disabled={runs >= 3}><RotateCcw /> 다시 생성</Button>
            </span>
          </Foot>
        </>
      )}
    </Wrap>
  );
}
const Bare = ({ children }) => <div>{children}</div>;

function List({ items = [] }) {
  if (!items.length) return <Empty />;
  return <ol className="space-y-2.5">{items.map((x, i) => <li key={i} className="flex gap-3 text-[15px] leading-relaxed"><span className="w-5 shrink-0 pt-[3px] font-mono text-[12px] text-muted-foreground">{i + 1}</span>{x}</li>)}</ol>;
}
function Center({ title, desc, children }) {
  return (
    <div className="my-6 rounded-2xl px-6 py-12 text-center" style={{ background: 'var(--bg)' }}>
      <div className="text-[16px] font-semibold">{title}</div>
      <p className="mx-auto mt-2 max-w-md text-[13.5px] leading-relaxed text-muted-foreground">{desc}</p>
      {children && <div className="mt-5">{children}</div>}
    </div>
  );
}
