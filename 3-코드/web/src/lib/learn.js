// Learn 모드 도우미 — 맥락 항목(계약 ③ 5절 context) 을 타임라인 마커·맥락 패널용으로 정리한다.
// 판정 없음. AI 가 "흐름을 묶는" 일은 서버 리포트(report.process)가 하고, 여기선 사실만 늘어놓는다.

/** 맥락 kind → 마커 모양. 목업 14 범례와 같은 순서 */
export const KIND = {
  error:             { ic: '✕', c: '#ef4444', t: '오류' },
  ai_question:       { ic: '?', c: '#0ea5e9', t: 'AI 질문' },
  ai_answer_excerpt: { ic: '“', c: '#0ea5e9', t: '답변 발췌' },
  page:              { ic: '▤', c: '#3b82f6', t: '참고' },
  selection:         { ic: '▭', c: '#6b7280', t: '선택' },
  paste:             { ic: '▼', c: '#f59e0b', t: '붙여넣기' },
  paste_at:          { ic: '▼', c: '#f59e0b', t: '붙여넣기 (문서)' },
  diff:              { ic: '✎', c: '#10b981', t: '직접 수정' },
  run_result:        { ic: '▶', c: '#6b7280', t: '실행' },
  solved:            { ic: '✓', c: '#059669', t: '해결' },
  save_stats:        { ic: '💾', c: '#6b7280', t: '저장' },
  chat:              { ic: '💬', c: '#0ea5e9', t: '물어보기' },
};
export const LEGEND = ['error', 'ai_question', 'page', 'paste', 'diff', 'run_result', 'solved', 'chat'];

/** ISO ts → 세션 시작 기준 분 (float) */
export function minuteOf(s, ts) {
  const [h0, m0, s0 = 0] = s.start.split(':').map(Number);
  const [h, m, sec = 0] = ts.slice(11, 19).split(':').map(Number);
  return h * 60 + m + sec / 60 - (h0 * 60 + m0 + s0 / 60);
}
export const clock = (ts) => ts.slice(11, 16);

/** 마커 = 맥락 항목(답변 발췌·저장 제외) + 세션의 붙여넣기. 시간순 */
export function markers(s, ctx = []) {
  const out = [];
  for (const it of ctx) {
    if (it.kind === 'ai_answer_excerpt' || it.kind === 'save_stats') continue;      // 답변은 질문에 붙고, 저장은 마커로 안 씀
    const kind = it.kind === 'run_result' && it.meta?.ok ? 'solved' : it.kind;
    out.push({ id: it.id, m: minuteOf(s, it.ts), ts: it.ts, kind, item: it });
  }
  for (const p of s.pastes || []) {
    out.push({ id: `p-${p.ts}`, m: p.m + 0.5, ts: `${s.date}T${p.ts}`, kind: 'paste', paste: p });
  }
  return out.sort((a, b) => a.m - b.m);
}

/** 마커 하나의 맥락 — 직전 오류 · 질문 · 답변 · 이후 (목업 14 오른쪽 패널) */
export function contextAround(s, ctx, mk) {
  if (!mk) return null;
  const t = mk.m;
  const byKind = (k) => ctx.filter((it) => it.kind === k).map((it) => ({ it, m: minuteOf(s, it.ts) }));
  const before = byKind('error').filter((x) => x.m <= t && t - x.m <= 15).pop()?.it || null;
  const answer = mk.kind === 'ai_question' ? byKind('ai_answer_excerpt').find((x) => x.m >= t && x.m - t <= 5)?.it || null : null;

  // 이후 — 마커 뒤 10분 안의 사실: 붙여넣기 · 직접 입력 · 실행 · 문서 변화
  const after = [];
  for (const p of s.pastes || []) if (p.m >= t && p.m - t <= 10) after.push({ ts: p.ts.slice(0, 5), text: `${p.len}자 붙여넣기 → ${p.target_title || p.target}`, kind: 'paste', ai: p.ai });
  for (const w of s.flow || []) {
    const wm = minuteOf(s, `${s.date}T${w.ts}`);
    if (wm >= t && wm - t <= 10 && w.typed) after.push({ ts: w.ts.slice(0, 5), text: `직접 입력 ${w.typed}자 — ${w.title || w.app}`, kind: 'typed' });
  }
  for (const x of ctx.map((it) => ({ it, m: minuteOf(s, it.ts) }))) {
    if (x.m <= t || x.m - t > 10 || x.it.id === mk.id) continue;
    if (x.it.kind === 'run_result') after.push({ ts: clock(x.it.ts), text: `실행 → ${x.it.text}`, kind: x.it.meta?.ok ? 'solved' : 'run_result' });
    if (x.it.kind === 'diff') after.push({ ts: clock(x.it.ts), text: `직접 수정 ${x.it.meta?.chars ?? ''}자 — ${x.it.meta?.where || x.it.meta?.file || ''}`, kind: 'diff' });
    if (x.it.kind === 'error') after.push({ ts: clock(x.it.ts), text: '다시 오류', kind: 'error' });
  }
  after.sort((a, b) => a.ts.localeCompare(b.ts));
  return { before, answer, after: after.slice(0, 6) };
}

/** 세션 요약 숫자 (헤더 · 리포트 타일) */
export function ctxCounts(s, ctx = []) {
  const n = (k) => ctx.filter((it) => it.kind === k).length;
  const errors = n('error'), solved = ctx.filter((it) => it.kind === 'run_result' && it.meta?.ok).length;
  const pages = new Set(ctx.filter((it) => it.kind === 'page').map((it) => it.meta?.domain)).size;
  const resMin = (s.segments || []).filter((g) => g.cat === 'resource').reduce((a, g) => a + g.e - g.s, 0);
  return { questions: n('ai_question'), chats: n('chat'), errors, solved, pages, resMin: Math.round(resMin) };
}
