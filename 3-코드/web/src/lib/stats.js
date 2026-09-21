// 숫자·요약 계산 — core/derive.py 와 같은 정의. 판정 없음, 사실만.
import { appName, winName, isBrowser } from './format.jsx';

/** session.json 에 stats 가 없을 때만 계산 (서버가 주면 그걸 쓴다) */
export function stats(s) {
  if (s.stats) return s.stats;
  const typed = s.typed.reduce((a, b) => a + b, 0);
  const deleted = s.deleted.reduce((a, b) => a + b, 0);
  const pasted = s.pastes.reduce((a, p) => a + p.len, 0);
  const pasted_ai = s.pastes.filter((p) => p.ai).reduce((a, p) => a + p.len, 0);
  const act = s.typed.filter((x) => x > 0);
  const total = typed + pasted;
  return {
    typed, deleted, pasted, pasted_ai, pasted_other: pasted - pasted_ai, total,
    typed_pct: total ? Math.round((typed / total) * 100) : 0,
    pasted_pct: total ? Math.round((pasted / total) * 100) : 0,
    cpm: act.length ? Math.round(act.reduce((a, b) => a + b, 0) / act.length) : 0,
    max_cpm: Math.max(0, ...s.typed),
    edit_ratio: typed ? Math.round((deleted / typed) * 100) : 0,
    undo: s.undos.length, pauses: 0,
    paste_count: s.pastes.length, paste_ai_count: s.pastes.filter((p) => p.ai).length,
    ai_min: s.segments.filter((g) => g.cat === 'ai').reduce((a, g) => a + g.e - g.s, 0),
    ai_visits: s.segments.filter((g) => g.cat === 'ai').length,
    events: s.chain.length,
  };
}

/** 앱별 요약 — flow 를 앱 단위로 합침. 체류 = 다음 창 전환까지 */
export function appSummary(s) {
  if (!s.flow || !s.flow.length) return [];
  const sec = (t) => { const [h, m, x] = t.split(':').map(Number); return h * 3600 + m * 60 + x; };
  const end = sec(s.end);
  const agg = {};
  s.flow.forEach((w, i) => {
    const key = w.cat === 'ai' && isBrowser(w.app) ? winName(w.app, w.title) : appName(w.app);
    const a = agg[key] || (agg[key] = { key, cat: w.cat, dwell: 0, typed: 0, deleted: 0, copy: 0, paste: 0, pasteAI: 0, pasteLen: 0 });
    const next = s.flow[i + 1] ? sec(s.flow[i + 1].ts) : end;
    a.dwell += Math.max(0, next - sec(w.ts));
    a.typed += w.typed; a.deleted += w.deleted;
    w.items.forEach((it) => {
      if (it.kind === 'copy') a.copy++;
      if (it.kind === 'paste') { a.paste++; a.pasteLen += it.len || 0; if (it.src && it.src.category === 'ai') a.pasteAI++; }
    });
    if (w.cat !== 'other') a.cat = w.cat;
  });
  return Object.values(agg).sort((x, y) => y.dwell - x.dwell);
}

/** 핵심 순간 — 단순 규칙. 4개까지 */
export function moments(s, clock) {
  const t = s.typed; const out = [];
  let best = [0, 0]; let cur = null;
  t.forEach((v, i) => { if (v > 0) { if (!cur) cur = [i, i]; cur[1] = i; if (cur[1] - cur[0] > best[1] - best[0]) best = [...cur]; } else cur = null; });
  if (best[1] > best[0]) {
    const run = t.slice(best[0], best[1] + 1); const d = s.deleted.slice(best[0], best[1] + 1);
    const u = s.undos.filter((m) => m >= best[0] && m <= best[1]).length;
    out.push({ kind: 'typed', when: `${clock(best[0])}–${clock(best[1] + 1)}`, title: `${best[1] - best[0] + 1}분 연속 직접 입력`, desc: `분당 ${Math.min(...run)}~${Math.max(...run)}자, 삭제 ${Math.min(...d)}~${Math.max(...d)}자, 되돌리기 ${u}회` });
  }
  const ai = s.pastes.filter((p) => p.ai);
  if (ai.length) {
    const p = ai[0];
    const seg = [...s.segments].reverse().find((g) => g.cat === 'ai' && g.s <= p.m);
    out.push({ kind: 'ai', when: clock(p.m), paste: p, aiMin: seg ? (seg.e - seg.s).toFixed(1) : null });
  }
  const big = [...s.pastes].sort((a, b) => b.len - a.len)[0];
  if (big && big !== ai[0]) out.push({ kind: big.ai ? 'ai' : 'other', when: clock(big.m), paste: big, biggest: true });
  const oth = s.pastes.filter((p) => !p.ai);
  if (oth.length) { const p = oth[oth.length - 1]; if (p !== big) out.push({ kind: 'other', when: clock(p.m), paste: p }); }
  if (!s.pastes.length) out.push({ kind: 'typed', when: '—', title: '붙여넣기 없음', desc: '이 세션의 결과물은 전부 직접 입력' });
  return out.slice(0, 4);
}
