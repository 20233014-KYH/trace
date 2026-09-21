// 서버 호출 한 곳 — 계약 ③ (docs/api.md). vite.config 의 proxy 가 /api → 127.0.0.1:5000 으로 넘긴다.
// 화면은 여기 함수만 부른다. 주소·형식이 바뀌면 이 파일만 고친다.

async function call(method, path, body) {
  const r = await fetch(`/api${path}`, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  let data = null;
  try { data = await r.json(); } catch { /* 본문 없음 */ }
  if (!r.ok) { const e = new Error(data?.error || `HTTP ${r.status}`); e.status = r.status; e.data = data; throw e; }
  return data;
}

export const getSession = (id) => call('GET', `/sessions/${id}`);                      // 4절 · session.json
export const getContext = (id) => call('GET', `/sessions/${id}/context`);               // ★ 제안: 아직 계약에 없음 — {items:[…]} (Learn 만 · Proof 403)
export const getReport  = (id) => call('GET', `/sessions/${id}/report`);                // 5절 · 없으면 이때 생성
export const regenReport = (id) => call('POST', `/sessions/${id}/report`);              // 5절 · 세션당 3회 · 초과 429
export const chat = (id, question, selection = '') => call('POST', `/sessions/${id}/chat`, { selection, question });   // 5절 · 30회

/** 오류 → 사람 말. 계약의 상태 코드 그대로 */
export function explain(e) {
  if (e.status === 403) return 'Proof 세션에는 AI 기능이 없습니다.';
  if (e.status === 429) return '이 세션의 횟수 상한에 닿았습니다 (리포트 3회 · 채팅 30회).';
  if (e.status === 502) return 'AI 응답 실패 — 잠시 뒤 다시 시도하세요.';
  if (e.status === 404) return '세션이 없습니다.';
  return e.message || String(e);
}
