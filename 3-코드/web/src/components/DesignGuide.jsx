// 디자인 기준 — 팔레트 후보 4개를 실제 부품(shadcn/ui · Magic UI · React Bits) 위에서 바꿔 보는 페이지.
// 헤더의 [디자인 기준] 으로 열린다. 후보를 고르면 :root 의 Trace 토큰(--ink --line --proof …)과 shadcn 토큰(--background --primary --border …)을
// 같이 바꾸므로 이 페이지뿐 아니라 실제 화면(SessionView/LearnView)도 같은 색으로 보인다. 확정되면 [CSS 복사] 해서 index.css :root 에 붙인다.
import { useEffect, useMemo, useState } from 'react';
import { Check, Copy, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';                    // shadcn/ui
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { NumberTicker } from '@/components/ui/number-ticker';        // Magic UI
import { ShimmerButton } from '@/components/ui/shimmer-button';
import { BlurFade } from '@/components/ui/blur-fade';
import { DotPattern } from '@/components/ui/dot-pattern';
import BlurText from '@/components/BlurText';                        // React Bits
import ShinyText from '@/components/ShinyText';

// ── 후보 4개 (2-디자인/디자인 기준.html 과 같은 값) ──
const PRESETS = {
  jagug: { name: '자국', num: '①', desc: '지금 쓰던 색을 정리한 것. 보라(Proof)·하늘(Learn), 흰 바탕, 회색 중립. 무난하고 앱 같음 — 학생용 화면에 맞음.',
    tokens: { primary: '#7c3aed', proof: '#7c3aed', learn: '#0ea5e9', bg: '#f3f4f7', surface: '#ffffff', ink: '#1c1f24', muted: '#6b7280', line: '#e5e7eb', soft: '#f9fafb', typed: '#10b981', paste: '#f59e0b', ai: '#ef4444', resource: '#3b82f6', work: '#10b981', other: '#cbd5e1', radius: 14, head: 'sans' } },
  meokji: { name: '먹지', num: '②', desc: '기록·증명 느낌. 남색(Proof)·청록(Learn), 따뜻한 종이색 바탕, 제목은 세리프. 검증자·교수에게 보이는 증명서·검증 화면에 강함.',
    tokens: { primary: '#1e3a8a', proof: '#1e3a8a', learn: '#0f766e', bg: '#f4f2ec', surface: '#fffdf8', ink: '#1f2328', muted: '#6b6f76', line: '#e6e2d8', soft: '#faf8f2', typed: '#15803d', paste: '#d97706', ai: '#dc2626', resource: '#2563eb', work: '#15803d', other: '#c8c4b8', radius: 8, head: 'serif' } },
  heukyeon: { name: '흑연', num: '③', desc: '미니멀. 주색은 거의 검정, Proof는 흑연 회색, Learn만 파랑. 유채색은 사실 표기(초록·주황·빨강)에만 써서 데이터가 제일 먼저 보임.',
    tokens: { primary: '#18181b', proof: '#52525b', learn: '#2563eb', bg: '#f5f5f5', surface: '#ffffff', ink: '#18181b', muted: '#71717a', line: '#e4e4e7', soft: '#fafafa', typed: '#16a34a', paste: '#f59e0b', ai: '#ef4444', resource: '#60a5fa', work: '#16a34a', other: '#d4d4d8', radius: 10, head: 'sans' } },
  notion: { name: '차분한 자국', num: '④', desc: '거의 무채색. 글자는 완전 검정이 아닌 #37352f, 선은 연하게, 둥글기 6px, 여백 넉넉히. 모드 색은 낮은 채도 보라·파랑, 사실 표기도 같은 톤으로. 색은 "가끔, 작게".',
    tokens: { primary: '#37352f', proof: '#9065b0', learn: '#337ea9', bg: '#ffffff', surface: '#ffffff', ink: '#37352f', muted: '#787774', line: '#e9e9e7', soft: '#f7f7f5', typed: '#448361', paste: '#d9730d', ai: '#d44c47', resource: '#7b9fd6', work: '#448361', other: '#d3d1cb', radius: 6, head: 'sans' } },
};
const GROUPS = [
  { title: '바탕 · 글자 · 선', note: '화면의 95%. 테두리 대신 바탕 차이와 여백으로 나눈다', keys: [['bg', '페이지 바탕'], ['surface', '카드 바탕'], ['soft', '연한 바탕'], ['line', '선'], ['ink', '글자'], ['muted', '보조 글자']] },
  { title: '모드', note: '로고·주요 버튼·모드 배지에만. 큰 면적 금지', keys: [['primary', '주색'], ['proof', 'Proof'], ['learn', 'Learn']] },
  { title: '사실 표기 — 고정', note: '후보가 바뀌어도 의미는 안 바뀐다. 초록=직접, 주황=붙여넣기, 빨강=AI', keys: [['typed', '직접 입력'], ['paste', '붙여넣기 · 기타'], ['ai', 'AI 출처']] },
  { title: '창 분류', note: '앱 표·타임라인의 점', keys: [['resource', '학습자료 창'], ['work', '작업 창'], ['other', '기타 창']] },
];
const HEAD = { sans: "'Pretendard Variable', sans-serif", serif: "'Noto Serif KR', Georgia, serif" };
const STORE = 'trace-design-v3';

// :root 에 적용 — Trace 토큰 + shadcn 토큰 매핑
function applyTokens(t) {
  const r = document.documentElement.style;
  // 주의: shadcn 의 --muted 는 '연한 바탕'이라 Trace 의 보조 글자색(muted)은 --muted-foreground 로 넣는다
  for (const [k, v] of Object.entries(t)) if (!['radius', 'head', 'muted'].includes(k)) r.setProperty(`--${k}`, v);
  r.setProperty('--radius', `${t.radius}px`);
  r.setProperty('--head', HEAD[t.head]);
  const map = { background: t.surface, card: t.surface, popover: t.surface, foreground: t.ink, 'card-foreground': t.ink, 'popover-foreground': t.ink,
    primary: t.primary, 'primary-foreground': '#ffffff', secondary: t.soft, 'secondary-foreground': t.ink, accent: t.soft, 'accent-foreground': t.ink,
    muted: t.soft, 'muted-foreground': t.muted, border: t.line, input: t.line, ring: t.muted };
  for (const [k, v] of Object.entries(map)) r.setProperty(`--${k}`, v);
  document.body.style.background = t.bg;
}
function toCss(t) {
  const keys = Object.keys(t).filter((k) => !['radius', 'head', 'muted'].includes(k));
  return `:root{\n${keys.map((k) => `  --${k}:${t[k]};`).join('\n')}\n  --muted-foreground:${t.muted};\n  --radius:${t.radius}px;\n  --font-sans:'Pretendard Variable',sans-serif;\n  --head:${HEAD[t.head]};\n}`;
}
function toTokensStudio(t) {       // Tokens Studio for Figma 형식
  const o = { trace: {} };
  for (const g of GROUPS) for (const [k, label] of g.keys) o.trace[k] = { value: t[k], type: 'color', description: label };
  o.trace.radius = { value: `${t.radius}px`, type: 'borderRadius' };
  o.trace.fontBody = { value: 'Pretendard', type: 'fontFamilies' };
  o.trace.fontHead = { value: t.head === 'serif' ? 'Noto Serif KR' : 'Pretendard', type: 'fontFamilies' };
  return JSON.stringify(o, null, 2);
}

function useCopy() {
  const [done, setDone] = useState('');
  const copy = (id, text) => navigator.clipboard.writeText(text).then(() => { setDone(id); setTimeout(() => setDone(''), 1200); });
  return [done, copy];
}

export default function DesignGuide({ onClose }) {
  const [cur, setCur] = useState(() => { try { return localStorage.getItem(STORE) || 'heukyeon'; } catch { return 'heukyeon'; } });
  const t = PRESETS[cur].tokens;
  const [done, copy] = useCopy();
  const [replay, setReplay] = useState(0);
  useEffect(() => { applyTokens(t); try { localStorage.setItem(STORE, cur); } catch {} }, [cur, t]);
  const css = useMemo(() => toCss(t), [t]);
  const json = useMemo(() => toTokensStudio(t), [t]);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen" style={{ fontFamily: 'var(--font-sans)', color: 'var(--ink)' }}>

        {/* 상단 줄 — 후보 전환 · 내보내기 · 화면으로 */}
        <div className="sticky top-0 z-10 border-b backdrop-blur-md" style={{ background: 'color-mix(in oklab, var(--bg) 82%, transparent)', borderColor: 'var(--line)' }}>
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-6 py-2.5">
            <span className="mr-2 flex items-center gap-2 text-[15px] font-bold tracking-tight"><span className="flex gap-0.5"><i className="size-1.5 rounded-full opacity-40" style={{ background: t.primary }} /><i className="size-1.5 rounded-full opacity-70" style={{ background: t.primary }} /><i className="size-1.5 rounded-full" style={{ background: t.primary }} /></span>Trace<span className="font-normal text-muted-foreground">디자인 기준</span></span>
            <ToggleGroup type="single" value={cur} onValueChange={(v) => v && setCur(v)} variant="outline" size="sm" className="flex-wrap">
              {Object.entries(PRESETS).map(([k, p]) => (
                <ToggleGroupItem key={k} value={k} className="gap-2 px-3 data-[state=on]:bg-(--surface) data-[state=on]:shadow-sm">
                  <span className="flex -space-x-1"><i className="size-2.5 rounded-full ring-1 ring-white" style={{ background: p.tokens.proof }} /><i className="size-2.5 rounded-full ring-1 ring-white" style={{ background: p.tokens.learn }} /></span>
                  {p.num} {p.name}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            <span className="ml-auto flex gap-1.5">
              <Button size="sm" variant="ghost" onClick={() => copy('css', css)}>{done === 'css' ? <Check /> : <Copy />} CSS</Button>
              <Button size="sm" variant="ghost" onClick={() => copy('json', json)}>{done === 'json' ? <Check /> : <Copy />} 피그마 JSON</Button>
              {onClose && <Button size="sm" variant="outline" onClick={onClose}>화면으로</Button>}
            </span>
          </div>
        </div>

        <div className="mx-auto max-w-5xl px-6 pb-24">

          {/* 머리 */}
          <section className="relative overflow-hidden py-20">
            <DotPattern className="[mask-image:radial-gradient(420px_circle_at_center,white,transparent)] text-(--line)" width={18} height={18} cr={1.2} />
            <div className="relative">
              <Badge variant="outline" className="mb-5 font-mono text-[11px] tracking-wide">DESIGN GUIDE · v3 · {new Date().toISOString().slice(0, 10)}</Badge>
              <div style={{ fontFamily: 'var(--head)' }}><BlurText key={cur} text="결과만 남는 작업에서, 과정을 남긴다." delay={70} animateBy="words" className="text-[44px] font-bold leading-[1.15] tracking-[-0.03em]" /></div>
              <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-muted-foreground">
                Trace 화면이 지켜야 할 것. 색·글자·부품·모션. 남의 디자인을 따라하지 않고 규칙만 참고한다 —
                <b className="text-foreground"> {PRESETS[cur].num} {PRESETS[cur].name}</b> 을 보고 있음. {PRESETS[cur].desc}
              </p>
            </div>
          </section>

          {/* 01 원칙 */}
          <Section n="01" title="원칙" sub="네 줄이면 된다. 나머지는 전부 여기서 나온다">
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ['테두리 대신 여백·머리선', '카드에 선을 두르지 않는다. 바탕색 한 단계 차이와 넉넉한 여백, 위쪽 머리선 하나로 나눈다.'],
                ['색은 의미 있을 때만, 작게', '점·배지·숫자처럼 작은 곳에만. 큰 면적의 유채색은 없다. 모드 색도 배지와 버튼 하나까지.'],
                ['위계는 글자로', '크기·굵기·회색 단계로 중요도를 만든다. 박스를 쌓아 올리지 않는다.'],
                ['사실 3색은 고정', '초록 = 직접 입력, 주황 = 붙여넣기, 빨강 = AI 출처. 팔레트가 바뀌어도 이 의미는 바뀌지 않는다.'],
              ].map(([h, d], i) => (
                <BlurFade key={h} delay={0.08 * i} inView>
                  <div className="h-full rounded-2xl p-6" style={{ background: 'var(--soft)' }}>
                    <div className="mb-3 font-mono text-[11px] text-muted-foreground">0{i + 1}</div>
                    <div className="text-[17px] font-semibold tracking-tight" style={{ fontFamily: 'var(--head)' }}>{h}</div>
                    <p className="mt-2 text-[13.5px] leading-relaxed text-muted-foreground">{d}</p>
                  </div>
                </BlurFade>
              ))}
            </div>
          </Section>

          {/* 02 색 */}
          <Section n="02" title="색" sub="누르면 hex 복사. 이 값이 그대로 index.css :root 로 간다">
            <div className="space-y-10">
              {GROUPS.map((g) => (
                <div key={g.title}>
                  <div className="mb-4 flex items-baseline gap-3">
                    <h3 className="text-[15px] font-semibold">{g.title}</h3>
                    <span className="text-[13px] text-muted-foreground">{g.note}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
                    {g.keys.map(([k, label]) => (
                      <Tooltip key={k}>
                        <TooltipTrigger asChild>
                          <button onClick={() => copy(k, t[k])} className="group text-left">
                            <div className="aspect-[4/3] rounded-xl transition-transform group-hover:scale-[1.03] group-active:scale-[0.98]" style={{ background: t[k], boxShadow: 'inset 0 0 0 1px rgba(0,0,0,.06)' }} />
                            <div className="mt-2 text-[13px] font-medium">{label}</div>
                            <div className="font-mono text-[11.5px] text-muted-foreground">{done === k ? '복사됨' : t[k]}</div>
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>--{k}</TooltipContent>
                      </Tooltip>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Section>

          {/* 03 글자 */}
          <Section n="03" title="글자" sub={`본문 Pretendard · 제목 ${t.head === 'serif' ? 'Noto Serif KR' : 'Pretendard'} · 숫자는 tabular-nums`}>
            <div className="grid gap-8 md:grid-cols-[1fr_1.2fr]">
              <div className="space-y-5">
                {[
                  ['Display 44 · 800', '한눈에 두 숫자', 'text-[44px] font-extrabold tracking-[-0.03em] leading-none'],
                  ['H1 30 · 700', '2026-09-22 세션', 'text-[30px] font-bold tracking-[-0.02em]'],
                  ['H2 20 · 700', '핵심 순간', 'text-[20px] font-bold tracking-tight'],
                  ['Body 14 · 400', '오후 2시 이후 AI 창에 머문 시간이 늘었다.', 'text-[14px]'],
                  ['Caption 12.5 · muted', '검증 파일 · 체인 원본 · 30건', 'text-[12.5px] text-muted-foreground'],
                  ['Mono 13', 'python core/derive.py "data/events-*.jsonl"', 'font-mono text-[13px]'],
                ].map(([k, s, cls]) => (
                  <div key={k} className="grid grid-cols-[130px_1fr] items-baseline gap-4">
                    <span className="font-mono text-[11px] text-muted-foreground">{k}</span>
                    <span className={cls} style={k.startsWith('H') || k.startsWith('Display') ? { fontFamily: 'var(--head)' } : undefined}>{s}</span>
                  </div>
                ))}
              </div>
              <div className="rounded-2xl p-7" style={{ background: 'var(--surface)', boxShadow: '0 0 0 1px var(--line)' }}>
                <div className="text-[13px] font-semibold text-muted-foreground">한눈에 — 두 숫자</div>
                <div className="mt-4 grid grid-cols-2 gap-6">
                  <div><div className="text-[13px] text-muted-foreground">직접 입력</div><div className="text-[44px] font-extrabold leading-none tracking-[-0.03em] tabular-nums" style={{ fontFamily: 'var(--head)' }}><NumberTicker key={`a${replay}`} value={42} />%</div></div>
                  <div><div className="text-[13px] text-muted-foreground">붙여넣기</div><div className="text-[44px] font-extrabold leading-none tracking-[-0.03em] tabular-nums" style={{ fontFamily: 'var(--head)' }}><NumberTicker key={`b${replay}`} value={58} delay={0.15} />%</div></div>
                </div>
                <div className="mt-6 flex h-2 overflow-hidden rounded-full"><i style={{ width: '42%', background: t.typed }} /><i style={{ width: '40%', background: t.paste }} /><i style={{ width: '18%', background: t.ai }} /></div>
                <div className="mt-3 flex flex-wrap gap-4 text-[12.5px] text-muted-foreground">
                  {[['직접 입력 42%', t.typed], ['붙여넣기 40%', t.paste], ['AI 출처 18%', t.ai]].map(([l, c]) => <span key={l} className="flex items-center gap-1.5"><i className="size-2 rounded-full" style={{ background: c }} />{l}</span>)}
                </div>
                <Separator className="my-5" />
                <div className="grid grid-cols-3 gap-4">
                  {[['이벤트', 1287, ''], ['AI 창 체류', 23, '분'], ['삭제 · 되돌리기', 41, '회']].map(([k, v, u]) => (
                    <div key={k}><div className="text-[12.5px] font-medium text-muted-foreground">{k}</div><div className="text-[24px] font-bold tracking-tight tabular-nums"><NumberTicker key={`${k}${replay}`} value={v} delay={0.3} /><small className="ml-0.5 text-[13px] font-medium text-muted-foreground">{u}</small></div></div>
                  ))}
                </div>
                <Button variant="ghost" size="sm" className="mt-5 -ml-2 text-muted-foreground" onClick={() => setReplay((n) => n + 1)}><RotateCcw /> 다시 재생</Button>
              </div>
            </div>
          </Section>

          {/* 04 부품 */}
          <Section n="04" title="부품" sub="shadcn/ui 기본 + Magic UI · React Bits 는 딱 필요한 곳에만">
            <div className="space-y-10">
              <Row label="버튼" note="주요 동작 하나만 채움. 나머지는 outline·ghost">
                <Button>세션 시작</Button>
                <Button variant="outline">검증 파일</Button>
                <Button variant="secondary">체인 원본</Button>
                <Button variant="ghost">취소</Button>
                <ShimmerButton className="h-8 px-4 text-[13px]" shimmerSize="0.08em" background={t.primary}>증명서 만들기</ShimmerButton>
                <span className="w-full text-[12px] text-muted-foreground">Shimmer 는 "증명서 만들기" 처럼 세션의 끝, 한 화면에 하나만.</span>
              </Row>
              <Row label="배지" note="모드는 연한 바탕 + 진한 글자, 사실은 점 하나">
                <Pill bg={t.proof}>Proof</Pill>
                <Pill bg={t.learn}>Learn</Pill>
                <Badge variant="outline">30건</Badge>
                <Badge variant="secondary">검증됨</Badge>
                <span className="mx-1 h-4 w-px bg-border" />
                {[['직접 입력', t.typed], ['붙여넣기', t.paste], ['AI 출처', t.ai]].map(([l, c]) => <span key={l} className="flex items-center gap-1.5 text-[13px]"><i className="size-2 rounded-full" style={{ background: c }} />{l}</span>)}
              </Row>
              <Row label="탭" note="밑줄 하나. 박스 탭 금지">
                <Tabs defaultValue="a"><TabsList variant="line"><TabsTrigger value="a">한눈에</TabsTrigger><TabsTrigger value="b">흐름</TabsTrigger><TabsTrigger value="c">리포트</TabsTrigger></TabsList></Tabs>
              </Row>
              <Row label="표" note="머리선 하나, 행 사이는 아주 연한 선, 숫자는 오른쪽">
                <div className="w-full overflow-hidden rounded-xl" style={{ background: 'var(--surface)', boxShadow: '0 0 0 1px var(--line)' }}>
                  <table className="w-full text-[13px]">
                    <thead><tr className="text-[12px] text-muted-foreground">{['창', '분류', '체류', '입력'].map((h, i) => <th key={h} className={`px-4 py-2.5 font-semibold ${i > 1 ? 'text-right' : 'text-left'}`} style={{ borderBottom: '1px solid var(--line)' }}>{h}</th>)}</tr></thead>
                    <tbody>
                      {[['Word — 보고서.docx', '작업', t.work, '38분', '1,204'], ['ChatGPT', 'AI', t.ai, '12분', '96'], ['강의노트.pdf', '학습자료', t.resource, '9분', '—']].map(([n, c, col, a, b]) => (
                        <tr key={n} style={{ borderTop: '1px solid color-mix(in oklab, var(--line) 55%, transparent)' }}>
                          <td className="px-4 py-2.5 font-medium">{n}</td>
                          <td className="px-4 py-2.5 text-muted-foreground"><i className="mr-2 inline-block size-2 rounded-full align-middle" style={{ background: col }} />{c}</td>
                          <td className="px-4 py-2.5 text-right tabular-nums">{a}</td><td className="px-4 py-2.5 text-right tabular-nums">{b}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Row>
              <Row label="알약" note="항상 위 · 투명 창. 어두운 바탕 하나만 예외">
                <div className="flex h-7 items-center gap-2 rounded-full px-3 text-[11.5px] text-white tabular-nums" style={{ background: 'rgba(28,31,36,.92)', boxShadow: '0 4px 14px rgba(0,0,0,.22)' }}>
                  <i className="size-1.5 rounded-full" style={{ background: t.learn }} /><b>Learn</b><span className="text-white/60">01:24:05</span><span className="ml-1 flex size-3.5 items-center justify-center rounded-full border border-white/50"><i className="block size-1.5 rounded-[1px] bg-white/80" /></span>
                </div>
                <div className="flex h-7 w-48 items-center gap-2 rounded-full pl-3 pr-1 text-[12px] text-muted-foreground" style={{ background: 'var(--surface)', boxShadow: '0 0 0 1px var(--line), 0 4px 14px rgba(0,0,0,.08)' }}>
                  <i className="flex size-3.5 items-center justify-center rounded-full text-[9px] font-bold text-white" style={{ background: t.learn }}>?</i>이거 왜 이래요<span className="ml-auto flex size-5 items-center justify-center rounded-full text-white" style={{ background: t.learn }}>↑</span>
                </div>
              </Row>
            </div>
          </Section>

          {/* 05 모션 */}
          <Section n="05" title="모션" sub="빠르고 조용하게. 눈에 띄는 모션은 숫자 하나, 제목 한 줄">
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                ['150ms', '상태 변화', 'hover · 열림 · 탭. ease-out. 알아채기 전에 끝난다.'],
                ['400ms', '등장', '카드·섹션은 아래에서 6px + blur 로. 한 번만, 스크롤마다 반복 안 함. (BlurFade)'],
                ['800ms', '숫자', '한눈에의 큰 숫자만 굴린다. 표 안 숫자는 안 굴린다. (NumberTicker)'],
              ].map(([ms, h, d], i) => (
                <BlurFade key={ms} delay={0.08 * i} inView>
                  <div className="h-full rounded-2xl p-6" style={{ background: 'var(--soft)' }}>
                    <div className="font-mono text-[22px] font-semibold tracking-tight tabular-nums">{ms}</div>
                    <div className="mt-1 text-[15px] font-semibold">{h}</div>
                    <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{d}</p>
                  </div>
                </BlurFade>
              ))}
            </div>
            <p className="mt-6 text-[13px] text-muted-foreground">
              쓰지 않는 것 — 배경 그라데이션 애니메이션, 네온 카드, 마우스 따라오는 빛. <ShinyText text="반짝이는 글자" color={t.muted} shineColor={t.ink} speed={3} className="font-medium" /> 도 로고 옆 한 단어까지만.
            </p>
          </Section>

          {/* 06 적용 */}
          <Section n="06" title="적용" sub="확정되면 이 CSS 를 3-코드/web/src/index.css 의 :root 에 붙인다">
            <div className="grid gap-4 md:grid-cols-2">
              <CodeBox title=":root" text={css} onCopy={() => copy('css2', css)} done={done === 'css2'} />
              <CodeBox title="Tokens Studio (Figma)" text={json} onCopy={() => copy('json2', json)} done={done === 'json2'} />
            </div>
            <p className="mt-4 text-[12.5px] leading-relaxed text-muted-foreground">
              피그마: Plugins → Tokens Studio for Figma → Load from JSON. 부품 가져오기: <code className="font-mono">npx shadcn@latest add badge tabs</code> · <code className="font-mono">@magicui/blur-fade</code> · <code className="font-mono">@react-bits/BlurText-JS-TW</code>
            </p>
          </Section>
        </div>
      </div>
    </TooltipProvider>
  );
}

function Section({ n, title, sub, children }) {
  return (
    <section className="py-14" style={{ borderTop: '1px solid var(--line)' }}>
      <BlurFade inView>
        <div className="mb-8 flex items-baseline gap-4">
          <span className="font-mono text-[12px] text-muted-foreground">{n}</span>
          <h2 className="text-[26px] font-bold tracking-[-0.02em]" style={{ fontFamily: 'var(--head)' }}>{title}</h2>
          <span className="hidden text-[13.5px] text-muted-foreground sm:inline">{sub}</span>
        </div>
      </BlurFade>
      {children}
    </section>
  );
}
function Row({ label, note, children }) {
  return (
    <div className="grid gap-3 md:grid-cols-[160px_1fr]">
      <div><div className="text-[14px] font-semibold">{label}</div><div className="mt-0.5 text-[12.5px] leading-snug text-muted-foreground">{note}</div></div>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  );
}
function Pill({ bg, children }) {
  return <span className="inline-flex h-5 items-center rounded-full px-2 text-[12px] font-semibold" style={{ background: `color-mix(in oklab, ${bg} 12%, transparent)`, color: bg }}>{children}</span>;
}
function CodeBox({ title, text, onCopy, done }) {
  return (
    <div className="overflow-hidden rounded-xl" style={{ background: 'var(--surface)', boxShadow: '0 0 0 1px var(--line)' }}>
      <div className="flex items-center px-4 py-2 text-[12px] font-medium text-muted-foreground" style={{ borderBottom: '1px solid var(--line)' }}>{title}<Button size="sm" variant="ghost" className="ml-auto -mr-2 h-7" onClick={onCopy}>{done ? <Check /> : <Copy />}{done ? '복사됨' : '복사'}</Button></div>
      <pre className="max-h-72 overflow-auto p-4 font-mono text-[12px] leading-relaxed">{text}</pre>
    </div>
  );
}
