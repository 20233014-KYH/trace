// 이름·문구 도우미 — viewer.html 과 같은 규칙. 화면 문구는 여기서만 바꾼다.

// 디자인 기준(흑연) 값과 같다 — index.css :root 의 --resource --work --ai --other --typed --paste. SVG 안에서도 써야 해서 hex 로 둔다.
export const COLORS = {
  resource: '#60a5fa', work: '#16a34a', ai: '#ef4444', other: '#d4d4d8', gap: '#e4e4e7',
  typed: '#16a34a', del: '#a1a1aa', pasteAI: '#ef4444', paste: '#f59e0b', undo: '#71717a',
};
export const CAT = { resource: '학습자료', work: '작업', ai: 'AI', other: '기타' };
export const TYPE = {
  session_start: '세션 시작', session_end: '세션 종료', window: '창 전환', copy: '복사', paste: '붙여넣기',
  file: '파일', keys: '입력', undo: '되돌리기', redo: '다시 실행', cut: '잘라내기', idle_start: '유휴', idle_end: '복귀',
  tab: '탭', heartbeat: '살아있음', doc_change: '문서 변화', doc_paste_at: '붙여넣은 자리', doc_save: '문서 저장', commit: '커밋', push: '푸시',
};
const APP = {
  'claude.exe': 'Claude 앱', 'ChatGPT.exe': 'ChatGPT 앱', 'chrome.exe': 'Chrome', 'msedge.exe': 'Edge', 'firefox.exe': 'Firefox',
  'KakaoTalk.exe': '카카오톡', 'Code.exe': 'VS Code', 'pycharm64.exe': 'PyCharm', 'explorer.exe': '탐색기',
  'WINWORD.EXE': 'Word', 'POWERPNT.EXE': 'PowerPoint', 'EXCEL.EXE': 'Excel', 'Acrobat.exe': 'Acrobat', 'AcroRd32.exe': 'Acrobat',
  'SumatraPDF.exe': 'PDF 뷰어', 'notepad++.exe': 'Notepad++', 'WindowsTerminal.exe': '터미널', '?': '(알 수 없음)',
};
const BROWSERS = ['chrome.exe', 'msedge.exe', 'firefox.exe'];

export const fmt = (n) => (n || 0).toLocaleString('ko-KR');
export const catColor = (c) => COLORS[CAT[c] ? c : 'other'];
export const appName = (a) => APP[a] || (a || '').replace(/\.exe$/i, '');

/** 창 이름: 브라우저·편집기는 "Chrome · ChatGPT" 처럼 제목 앞부분을 붙인다 */
export function winName(app, title) {
  const n = appName(app);
  if (!title) return n;
  const t = title.replace(/ [-–—] (Google Chrome|Chrome|Microsoft Edge|Mozilla Firefox|Visual Studio Code)$/, '').trim();
  const base = n.replace(/ 앱$/, '').toLowerCase();
  return t && t.toLowerCase() !== base && t.toLowerCase() !== n.toLowerCase() ? `${n} · ${t.slice(0, 40)}` : n;
}
export const isBrowser = (app) => BROWSERS.includes(app);
export const srcName = (src) => (src ? winName(src.app, src.title) : '');

/** 붙여넣기 한 줄 설명 (JSX 조각) */
export function pasteText(p) {
  if (!p.matched) return '복사 기록 없음 (다른 기기·이전 세션·이미지)';
  const w = srcName(p.src);
  return p.ai ? <><b style={{ color: 'var(--ai)' }}>{w}</b>에서 복사한 것 (AI)</> : <>{w}에서 복사한 것</>;
}

export const clockAt = (start, m) => {
  const [h0, m0] = start.split(':').map(Number);
  const tot = h0 * 60 + m0 + m;
  return `${String(Math.floor(tot / 60) % 24).padStart(2, '0')}:${String(tot % 60).padStart(2, '0')}`;
};
export const dur = (sec) => (sec >= 60 ? `${Math.floor(sec / 60)}분 ${Math.round(sec % 60)}초` : `${Math.round(sec)}초`);
