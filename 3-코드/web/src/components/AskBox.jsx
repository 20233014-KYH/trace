// 알약 위 질문칸 — 목업 13b/13c. 접힘: 알약 폭의 입력칸 하나. 펼침: 그 자리 위로 채팅 패널. ✕ 로 다시 접힘.
// PC 앱에서는 이게 pywebview 알약 창 안에 들어간다 (항상 위 · 결정 11). 웹 뼈대에서는 화면 오른쪽 아래에 띄운다.
// 서버 POST /chat 한 곳만 부른다. 대화는 서버가 세션 맥락(kind:"chat")으로도 남긴다.
// 디자인 기준(흑연): 알약만 어두운 바탕 예외. Learn 파랑은 점·아이콘·보내기 버튼에만.
import { useEffect, useRef, useState } from 'react';
import { ArrowUp, X } from 'lucide-react';

const SHADOW = '0 0 0 1px var(--line), 0 8px 24px rgba(0,0,0,.10)';

export default function AskBox({ onSend, open, setOpen, msgs, busy, error, seed, pill }) {
  const [q, setQ] = useState('');
  const inRef = useRef(null), endRef = useRef(null);
  useEffect(() => { if (seed) { setQ(seed); setOpen(true); } }, [seed]);           // 맥락 패널 "더 묻기" → 질문 미리 채움
  useEffect(() => { if (open) { inRef.current?.focus(); endRef.current?.scrollIntoView({ block: 'end' }); } }, [open, msgs.length]);

  const send = () => { const t = q.trim(); if (!t || busy) return; setQ(''); onSend(t); };
  const key = (e) => {
    if (e.nativeEvent.isComposing) return;                    // 한글 IME 조합 중 Enter 는 무시 (마지막 글자 두 번 보내는 버그 방지)
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    if (e.key === 'Escape') setOpen(false);
  };
  const Send = ({ className = '', ...p }) => <button {...p} className={`flex shrink-0 items-center justify-center rounded-full text-white disabled:opacity-40 ${className}`} style={{ background: 'var(--learn)' }}><ArrowUp className="size-3.5" strokeWidth={2.5} /></button>;

  return (
    <div className="fixed right-5 bottom-5 z-20 flex flex-col items-end gap-2">
      {open ? (
        <div className="flex w-[360px] max-w-[calc(100vw-40px)] flex-col overflow-hidden rounded-2xl" style={{ background: 'var(--surface)', boxShadow: SHADOW }}>
          <div className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-semibold" style={{ borderBottom: '1px solid var(--line)' }}>
            <i className="size-2 rounded-full" style={{ background: 'var(--learn)' }} />Learn AI · 물어보기
            <button className="ml-auto -mr-1 rounded-md p-1 text-muted-foreground hover:text-foreground" onClick={() => setOpen(false)} title="닫기 (Esc)"><X className="size-4" /></button>
          </div>
          <div className="flex max-h-[330px] flex-col gap-2.5 overflow-auto p-3.5 text-[13px] leading-relaxed">
            {msgs.length === 0 && <p className="text-[12px] text-muted-foreground">이 세션의 최근 오류·질문을 근거로 답합니다. 대화는 세션 맥락으로 남아 리포트에 반영됩니다.</p>}
            {msgs.map((m, i) => m.role === 'user'
              ? <div key={i} className="max-w-[88%] self-end rounded-2xl rounded-br-sm px-3 py-2 whitespace-pre-wrap text-white" style={{ background: 'var(--primary)' }}>{m.text}</div>
              : <div key={i} className="max-w-[92%] rounded-2xl rounded-bl-sm px-3 py-2 whitespace-pre-wrap" style={{ background: 'var(--bg)' }}>{m.text}</div>)}
            {busy && <div className="rounded-2xl rounded-bl-sm px-3 py-2 text-muted-foreground" style={{ background: 'var(--bg)' }}>답변 생성 중…</div>}
            {error && <div className="rounded-2xl rounded-bl-sm px-3 py-2" style={{ background: 'color-mix(in oklab, var(--ai) 8%, transparent)', color: 'var(--ai)' }}>{error}</div>}
            <div ref={endRef} />
          </div>
          <div className="flex items-end gap-2 p-3" style={{ borderTop: '1px solid var(--line)' }}>
            <textarea ref={inRef} rows={1} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={key} placeholder="이어서 묻기…"
                      className="max-h-[120px] min-h-[36px] flex-1 resize-none rounded-lg px-3 py-2 text-[13px] outline-none focus:ring-2" style={{ background: 'var(--bg)', '--tw-ring-color': 'var(--line)' }} />
            <Send className="size-8" onClick={send} disabled={busy || !q.trim()} />
          </div>
        </div>
      ) : (
        <button onClick={() => setOpen(true)} className="flex h-8 w-52 items-center gap-2 rounded-full pl-3 pr-1 text-[12.5px] text-muted-foreground" style={{ background: 'var(--surface)', boxShadow: SHADOW }}>
          <i className="flex size-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: 'var(--learn)' }}>?</i>
          <span className="flex-1 text-left">AI에게 물어보기…</span>
          <span className="flex size-6 items-center justify-center rounded-full text-white" style={{ background: 'var(--learn)' }}><ArrowUp className="size-3" strokeWidth={2.5} /></span>
        </button>
      )}
      {pill}
    </div>
  );
}

/** 알약 — 목업 13. 웹 뼈대에선 모양만 (시간·맥락 수). 실제 기록 제어는 수집기(PC 앱) 쪽 */
export function Pill({ elapsed, ctxCount }) {
  return (
    <div className="flex h-7 items-center gap-2 rounded-full px-3 text-[11.5px] text-white tabular-nums" style={{ background: 'rgba(24,24,27,.92)', boxShadow: '0 4px 14px rgba(0,0,0,.22)' }}>
      <i className="size-1.5 rounded-full" style={{ background: 'var(--learn)' }} /><b>{elapsed}</b><span className="text-white/60">맥락 {ctxCount}</span>
      <span className="ml-0.5 flex size-3.5 items-center justify-center rounded-full border border-white/50"><i className="block size-1.5 rounded-[1px] bg-white/80" /></span>
    </div>
  );
}
