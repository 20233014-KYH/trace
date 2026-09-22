// 문서 부품 — Proof 한눈에(SessionView)·Learn 리포트(ReportView)가 같이 쓴다. 디자인 기준(흑연):
// 흰 종이 한 장 위에 머리선으로 나눈 섹션, 테두리 없음, 위계는 글자 크기·굵기, 색은 사실(초록·주황·빨강)에만, 큰 숫자만 굴린다.
import { NumberTicker } from '@/components/ui/number-ticker';
import { BlurFade } from '@/components/ui/blur-fade';

/** 흰 시트. 안쪽 블록은 페이지 바탕색(--bg)으로 구분한다 */
export function Sheet({ children, wide = false }) {
  return <article className={`mx-auto ${wide ? 'max-w-5xl' : 'max-w-3xl'} rounded-2xl px-6 py-8 sm:px-12 sm:py-10`} style={{ color: 'var(--ink)', background: 'var(--surface)' }}>{children}</article>;
}

/** 문서 머리 — 모노 캡션 → 제목 → 한 줄 요약. right 에 배지·버튼 */
export function Head({ kicker, title, sub, right }) {
  return (
    <div className="flex flex-wrap items-start gap-4 pb-8">
      <div className="min-w-0 flex-1">
        <div className="font-mono text-[11px] tracking-wide text-muted-foreground">{kicker}</div>
        <h1 className="mt-2 text-[28px] font-bold leading-tight tracking-[-0.02em]">{title}</h1>
        {sub && <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{sub}</p>}
      </div>
      {right && <div className="flex items-center gap-2 pt-1">{right}</div>}
    </div>
  );
}

/** 숫자 한 줄 — 머리선 아래 2~4개 */
export function Nums({ cols = 4, children }) {
  return <div className={`grid grid-cols-2 gap-x-6 gap-y-6 py-6 ${cols === 3 ? 'sm:grid-cols-3' : cols === 2 ? 'sm:grid-cols-2' : 'sm:grid-cols-4'}`} style={{ borderTop: '1px solid var(--line)' }}>{children}</div>;
}
export function Num({ k, v, unit, h, c, big = false }) {
  return (
    <div>
      <div className="text-[12.5px] font-medium text-muted-foreground">{k}</div>
      <div className={`mt-1 font-bold leading-none tracking-[-0.02em] tabular-nums ${big ? 'text-[44px]' : 'text-[30px]'}`} style={c ? { color: c } : undefined}>
        {typeof v === 'number' ? <NumberTicker value={v} /> : v}{unit && <span className="ml-1 text-[14px] font-medium text-muted-foreground">{unit}</span>}
      </div>
      {h && <div className="mt-1.5 text-[12px] leading-relaxed text-muted-foreground">{h}</div>}
    </div>
  );
}

/** 번호 섹션 — 왼쪽 여백에 모노 번호 */
export function Sec({ n, title, sub, children }) {
  return (
    <BlurFade inView>
      <section className="grid gap-x-6 gap-y-3 py-8 md:grid-cols-[56px_1fr]" style={{ borderTop: '1px solid var(--line)' }}>
        <span className="font-mono text-[12px] text-muted-foreground">{n}</span>
        <div className="min-w-0">
          <h2 className="text-[17px] font-semibold tracking-tight">{title}{sub && <span className="ml-2 text-[13px] font-normal text-muted-foreground">{sub}</span>}</h2>
          <div className="mt-4">{children}</div>
        </div>
      </section>
    </BlurFade>
  );
}

export function Empty({ children = '근거가 없어 비움' }) { return <p className="text-[14px] text-muted-foreground">{children}</p>; }

/** 표 — 머리선 하나, 행 사이 아주 연한 선, 숫자 오른쪽. head: [{t, r}] · rows: [{key, cells:[node]}] */
export function Table({ head, rows, className = '' }) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-[13px]">
        <thead><tr className="text-[12px] text-muted-foreground">{head.map((h, i) => <th key={i} className={`px-3 py-2 font-semibold whitespace-nowrap ${h.r ? 'text-right' : 'text-left'}`} style={{ borderBottom: '1px solid var(--line)', width: h.w }}>{h.t}</th>)}</tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.key} style={{ borderTop: '1px solid color-mix(in oklab, var(--line) 55%, transparent)' }}>
            {r.cells.map((c, i) => <td key={i} className={`px-3 py-2 align-top ${head[i]?.r ? 'text-right tabular-nums whitespace-nowrap' : ''} ${head[i]?.wrap ? '' : 'whitespace-nowrap'}`}>{c}</td>)}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

/** 접힌 상세 — 제목 줄 하나, 열면 아래로 */
export function Fold({ title, sub, count, children }) {
  return (
    <details className="group py-4" style={{ borderTop: '1px solid var(--line)' }}>
      <summary className="flex cursor-pointer list-none items-center gap-2 text-[14px] font-semibold select-none [&::-webkit-details-marker]:hidden">
        <span className="inline-block text-[11px] text-muted-foreground transition-transform group-open:rotate-90">▶</span>{title}
        {sub && <span className="font-normal text-muted-foreground">{sub}</span>}
        {count != null && <span className="ml-auto text-[12.5px] font-normal text-muted-foreground">{count}</span>}
      </summary>
      <div className="pt-4">{children}</div>
    </details>
  );
}

export function Foot({ children }) {
  return <footer className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3 pt-6 text-[12.5px] leading-relaxed text-muted-foreground" style={{ borderTop: '1px solid var(--line)' }}>{children}</footer>;
}

export function Dot({ c, className = '' }) { return <i className={`inline-block size-2 shrink-0 rounded-full align-middle ${className}`} style={{ background: c }} />; }

/** "오류 발생 → AI에게 질문 → …" 한 줄 — 직접 한 일(직접·해결·재실행)만 초록으로 */
export function FlowLine({ n, line }) {
  const steps = line.split('→').map((x) => x.trim()).filter(Boolean);
  const strong = (x) => /직접|해결|재실행/.test(x);
  return (
    <li className="flex gap-3">
      <span className="mt-[3px] flex size-5 shrink-0 items-center justify-center rounded-full font-mono text-[11px] text-muted-foreground" style={{ background: 'var(--bg)' }}>{n}</span>
      <span className="flex flex-wrap items-center gap-x-1.5 gap-y-1.5 text-[14px] leading-snug">
        {steps.map((x, i) => (
          <span key={i} className="contents">
            <span className={`rounded-md px-2 py-0.5 ${strong(x) ? 'font-semibold' : ''}`} style={strong(x) ? { background: 'color-mix(in oklab, var(--typed) 12%, transparent)', color: 'var(--typed)' } : { background: 'var(--bg)' }}>{x}</span>
            {i < steps.length - 1 && <span className="text-muted-foreground/60">→</span>}
          </span>
        ))}
      </span>
    </li>
  );
}
