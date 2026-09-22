// 맥락 패널 — 목업 14 오른쪽. 마커 하나를 누르면: 직전 오류 → 질문(또는 항목) → 답변 발췌 → 이후.
// 사실만 늘어놓는다. "AI 를 썼다/안 썼다" 판정 없음. 디자인 기준(흑연): 테두리 없는 연한 블록, 색은 사실(오류·AI=빨강, 직접=초록)에만.
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { KIND, contextAround, clock } from '../lib/learn.js';
import { pasteText } from '../lib/format.jsx';

export default function ContextPanel({ s, ctx, mk, onAsk }) {
  if (!mk) {
    return (
      <aside className="rounded-2xl p-5 md:sticky md:top-4" style={{ background: 'var(--bg)' }}>
        <div className="text-[14px] font-semibold">마커를 누르면 여기에 맥락이 보입니다</div>
        <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">직전 오류 → 내 질문 → 답변 발췌 → 이후 무엇을 직접 했나.</p>
        <Note />
      </aside>
    );
  }
  const k = KIND[mk.kind] || KIND.selection;
  const it = mk.item;
  const c = contextAround(s, ctx, mk);
  const where = it?.meta?.domain || it?.meta?.file || it?.meta?.app || (mk.paste ? mk.paste.target : '');

  return (
    <aside className="rounded-2xl p-5 text-[13.5px] md:sticky md:top-4" style={{ background: 'var(--bg)' }}>
      <div className="flex items-center gap-2.5">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white" style={{ background: k.c }}>{k.ic}</span>
        <b className="text-[14px]">{clock(mk.ts)} {k.t}</b>
        {where && <Badge variant="outline" className="ml-auto max-w-[150px] truncate font-mono text-[10.5px]">{where}</Badge>}
      </div>

      {c.before && mk.kind !== 'error' && <Sec t={`직전 — ${clock(c.before.ts)} 오류`}><Err>{c.before.text}</Err></Sec>}

      {mk.kind === 'error' && <Sec t="오류"><Err>{it.text}</Err></Sec>}
      {mk.kind === 'ai_question' && <Sec t="질문 — 내가 입력한 것"><Quote>"{it.text}"</Quote></Sec>}
      {mk.kind === 'chat' && <Sec t="물어보기 — 알약 위 질문칸"><Quote mono>{it.text}</Quote></Sec>}
      {mk.kind === 'page' && <Sec t="참고 페이지"><Quote>{it.text}</Quote></Sec>}
      {mk.kind === 'commit' && <Sec t={`커밋 ${it.meta?.hash?.slice(0, 7)} · ${it.meta?.repo} (${it.meta?.branch})`}><Quote mono>{it.text}</Quote></Sec>}
      {mk.kind === 'selection' && <Sec t="선택한 부분"><Quote mono>{it.text}</Quote></Sec>}
      {mk.kind === 'diff' && <Sec t={`직접 수정 — ${it.meta?.where || it.meta?.file}${it.meta?.chars != null ? ` · ${it.meta.chars > 0 ? '+' : ''}${it.meta.chars}자` : ''}`}><Quote mono>{it.text}</Quote></Sec>}
      {mk.kind === 'paste_at' && <Sec t={`문서에 붙여넣음 — ${it.meta?.file} ${it.meta?.where} · ${it.meta?.chars}자`}><Quote mono>{it.text}</Quote></Sec>}
      {(mk.kind === 'run_result' || mk.kind === 'solved') && <Sec t="실행 결과"><Quote>{it.text}</Quote></Sec>}
      {mk.paste && (
        <Sec t={`붙여넣기 ${mk.paste.len}자 → ${mk.paste.target_title || mk.paste.target}`}>
          <p className="leading-relaxed">{pasteText(mk.paste)}{mk.paste.after_typed != null && <> · 이후 3분 직접 입력 <b style={{ color: 'var(--typed)' }}>{mk.paste.after_typed}자</b></>}</p>
        </Sec>
      )}

      {c.answer && <Sec t={`답변 발췌 — 복사한 ${c.answer.text.length}자`}><Quote className="max-h-40 overflow-auto">{c.answer.text}</Quote></Sec>}

      {c.after.length > 0 && (
        <Sec t="이후">
          <ul className="space-y-1">{c.after.map((a, i) => {
            const good = a.kind === 'typed' || a.kind === 'diff' || a.kind === 'solved';
            const bad = a.kind === 'error' || a.ai;
            return <li key={i} className="flex gap-2 leading-snug"><span className="shrink-0 font-mono text-[12px] text-muted-foreground tabular-nums">{a.ts}</span><span className={good ? 'font-semibold' : ''} style={good ? { color: 'var(--typed)' } : bad ? { color: 'var(--ai)' } : undefined}>{a.text}</span></li>;
          })}</ul>
        </Sec>
      )}

      <Button variant="outline" className="mt-5 w-full" onClick={() => onAsk && onAsk(it?.text || (mk.paste ? `${mk.paste.len}자 붙여넣기` : ''))}>물어보기에서 더 묻기</Button>
      <Note />
    </aside>
  );
}

function Sec({ t, children }) { return <section className="mt-4"><h5 className="mb-1.5 text-[12px] font-semibold text-muted-foreground">{t}</h5>{children}</section>; }
function Quote({ children, mono, className = '' }) {
  return <blockquote className={`rounded-lg px-3 py-2.5 leading-relaxed whitespace-pre-wrap ${mono ? 'font-mono text-[12.5px]' : ''} ${className}`} style={{ background: 'var(--surface)' }}>{children}</blockquote>;
}
function Err({ children }) {
  return <pre className="rounded-lg px-3 py-2.5 font-mono text-[12.5px] leading-relaxed whitespace-pre-wrap break-all" style={{ background: 'color-mix(in oklab, var(--ai) 8%, transparent)', color: 'var(--ai)' }}>{children}</pre>;
}
function Note() { return <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">이 맥락은 Learn 모드 · 맥락 수집 켜짐 상태에서 확장·Office 모듈이 저장한 것입니다. Proof 세션에는 없습니다.</p>; }
