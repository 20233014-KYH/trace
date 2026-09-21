// 분당 활동 레인 그래프 — 활성 창 / 직접 입력 / 붙여넣기 / 삭제·되돌리기
// viewer.html 의 lanes() 를 그대로 옮김. 입력: session (계약 ②). 출력: SVG.
import { COLORS, CAT, catColor, appName, srcName } from '../lib/format.jsx';

const LANE = { win: 26, typed: 110, paste: 90, edit: 40 };
const GAP = 18;

export default function Timeline({ s, width = 1000 }) {
  const W = width, L = 110, R = 20, M = s.minutes;
  const X = (m) => L + (m / M) * (W - L - R);
  const bw = Math.max(1.5, (W - L - R) / M - 2);
  const y = { win: 8 };
  y.typed = y.win + LANE.win + GAP; y.paste = y.typed + LANE.typed + GAP; y.edit = y.paste + LANE.paste + GAP;
  const H = y.edit + LANE.edit + 34;
  const maxT = Math.max(...s.typed) || 1, maxP = Math.max(...s.pastes.map((p) => p.len)) || 1, maxD = Math.max(...s.deleted) || 1;
  const step = M > 120 ? 30 : M > 60 ? 15 : M > 30 ? 10 : 5;
  const [h0, m0] = s.start.split(':').map(Number);
  const yt0 = y.typed + LANE.typed, yp0 = y.paste + LANE.paste, ye0 = y.edit;

  const Label = ({ yy, t, sub }) => (
    <>
      <text x={L - 12} y={yy} fontSize="12.5" fontWeight="600" fill="#374151" textAnchor="end">{t}</text>
      {sub && <text x={L - 12} y={yy + 15} fontSize="11" fill="#9ca3af" textAnchor="end">{sub}</text>}
    </>
  );
  const ticks = [];
  for (let m = 0; m <= M; m += step) {
    const tot = h0 * 60 + m0 + m;
    ticks.push({ x: X(m), label: `${String(Math.floor(tot / 60) % 24).padStart(2, '0')}:${String(tot % 60).padStart(2, '0')}` });
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {ticks.map((t) => (
        <g key={t.x}>
          <line x1={t.x} y1={y.win} x2={t.x} y2={H - 26} stroke="#eef0f3" />
          <text x={t.x} y={H - 8} fontSize="11.5" fill="#6b7280" textAnchor="middle">{t.label}</text>
        </g>
      ))}

      {/* 1 활성 창 */}
      <Label yy={y.win + 17} t="활성 창" />
      {s.segments.map((seg, i) => {
        const w = X(seg.e) - X(seg.s);
        return (
          <g key={i}>
            <rect x={X(seg.s)} y={y.win} width={Math.max(1, w - 1)} height={LANE.win} rx="4" fill={catColor(seg.cat)} />
            {w > 60 && (
              <text x={X(seg.s) + 8} y={y.win + 17} fontSize="11.5" fill="#fff" fontWeight="700">
                {CAT[seg.cat] || seg.cat}{w > 120 && seg.title ? ` · ${seg.title.slice(0, 28)}` : ''}
              </text>
            )}
          </g>
        );
      })}

      {/* 2 직접 입력 */}
      <Label yy={y.typed + LANE.typed / 2} t="직접 입력" sub="자/분" />
      <line x1={L} y1={yt0} x2={W - R} y2={yt0} stroke="#d1d5db" />
      {s.typed.map((v, m) => v ? <rect key={m} x={X(m) + 1} y={yt0 - (v / maxT) * LANE.typed} width={bw} height={(v / maxT) * LANE.typed} rx="1.5" fill={COLORS.typed} /> : null)}
      <text x={W - R} y={y.typed + 10} fontSize="11" fill="#9ca3af" textAnchor="end">최대 {maxT}자/분</text>

      {/* 3 붙여넣기 */}
      <Label yy={y.paste + LANE.paste / 2} t="붙여넣기" sub="글자 수" />
      <line x1={L} y1={yp0} x2={W - R} y2={yp0} stroke="#d1d5db" />
      {s.pastes.map((p, i) => {
        const x = X(p.m) + bw / 2 + 1, h = Math.max(14, (p.len / maxP) * (LANE.paste - 16));
        const c = p.ai ? COLORS.pasteAI : COLORS.paste;
        const prev = s.pastes[i - 1];
        const lift = prev && p.m - prev.m <= 1 && Math.abs(prev.len - p.len) / maxP * (LANE.paste - 16) < 16 ? 14 : 0;
        return (
          <g key={i}>
            <line x1={x} y1={yp0} x2={x} y2={yp0 - h} stroke={c} strokeWidth="3" />
            <circle cx={x} cy={yp0 - h} r="7" fill={c}>
              <title>{p.ts} {p.len}자 → {appName(p.target)}{p.src ? ` ← ${srcName(p.src)}` : ''}</title>
            </circle>
            <text x={x} y={yp0 - h - 11 - lift} fontSize="12" fontWeight="700" fill={p.ai ? '#b91c1c' : '#b45309'} textAnchor="middle">{p.len}</text>
          </g>
        );
      })}

      {/* 4 삭제 · 되돌리기 */}
      <Label yy={y.edit + LANE.edit / 2} t="삭제 · 되돌리기" sub="자/분 · ▲" />
      {s.deleted.map((v, m) => v ? <rect key={m} x={X(m) + 1} y={ye0} width={bw} height={(v / maxD) * (LANE.edit - 14)} rx="1.5" fill={COLORS.del} /> : null)}
      {s.undos.map((m, i) => {
        const x = X(m) + bw / 2 + 1;
        return <polygon key={i} points={`${x},${ye0 + LANE.edit - 12} ${x - 5},${ye0 + LANE.edit - 3} ${x + 5},${ye0 + LANE.edit - 3}`} fill={COLORS.undo} />;
      })}
    </svg>
  );
}

export function Legend() {
  const I = ({ c }) => <i style={{ background: c }} />;
  return (
    <div className="legend">
      <span><I c={COLORS.resource} />학습자료</span><span><I c={COLORS.work} />작업</span><span><I c={COLORS.ai} />AI</span><span><I c={COLORS.other} />기타</span>
      <span style={{ marginLeft: 10 }}><I c={COLORS.typed} />직접 입력</span>
      <span><I c={COLORS.pasteAI} />붙여넣기 · AI 앱·사이트에서 복사한 것</span>
      <span><I c={COLORS.paste} />붙여넣기 · 기타</span><span><I c={COLORS.del} />삭제</span><span><I c={COLORS.undo} />되돌리기</span>
    </div>
  );
}
