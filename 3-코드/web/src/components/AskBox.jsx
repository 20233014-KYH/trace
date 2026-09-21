// 알약 위 질문칸 — 목업 13b/13c. 접힘: 알약 폭의 입력칸 하나. 펼침: 그 자리 위로 채팅 패널. ✕ 로 다시 접힘.
// PC 앱에서는 이게 pywebview 알약 창 안에 들어간다 (항상 위 · 결정 11). 웹 뼈대에서는 화면 오른쪽 아래에 띄운다.
// 서버 POST /chat 한 곳만 부른다. 대화는 서버가 세션 맥락(kind:"chat")으로도 남긴다.
import { useEffect, useRef, useState } from 'react';

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

  return (
    <div className="askwrap">
      {open ? (
        <div className="askpanel">
          <div className="hd"><span className="dot learn" />Learn AI · 물어보기<button className="x" onClick={() => setOpen(false)} title="닫기 (Esc)">✕</button></div>
          <div className="msgs">
            {msgs.length === 0 && <p className="note">이 세션의 최근 오류·질문을 근거로 답합니다. 대화는 세션 맥락으로 남아 리포트에 반영됩니다.</p>}
            {msgs.map((m, i) => <div key={i} className={m.role === 'user' ? 'me' : 'ai'}>{m.text}</div>)}
            {busy && <div className="ai dim">답변 생성 중…</div>}
            {error && <div className="ai err">{error}</div>}
            <div ref={endRef} />
          </div>
          <div className="in">
            <textarea ref={inRef} rows={1} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={key} placeholder="이어서 묻기…" />
            <button className="send" onClick={send} disabled={busy || !q.trim()}>↑</button>
          </div>
        </div>
      ) : (
        <button className="ask" onClick={() => setOpen(true)}><span className="ic">?</span><span className="ph">AI에게 물어보기…</span><span className="send">↑</span></button>
      )}
      {pill}
    </div>
  );
}

/** 알약 — 목업 13. 웹 뼈대에선 모양만 (시간·맥락 수). 실제 기록 제어는 수집기(PC 앱) 쪽 */
export function Pill({ elapsed, ctxCount }) {
  return <div className="pill learn"><span className="dot learn" /><span className="t">{elapsed}</span><span className="n">맥락 {ctxCount}</span><span className="stop"><i /></span></div>;
}
