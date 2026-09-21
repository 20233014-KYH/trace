// 맥락 패널 — 목업 14 오른쪽. 마커 하나를 누르면: 직전 오류 → 질문(또는 항목) → 답변 발췌 → 이후.
// 사실만 늘어놓는다. "AI 를 썼다/안 썼다" 판정 없음.
import { KIND, contextAround, clock } from '../lib/learn.js';
import { pasteText } from '../lib/format.jsx';

export default function ContextPanel({ s, ctx, mk, onAsk }) {
  if (!mk) {
    return (
      <aside className="ctxpanel empty">
        <b>학습 흐름 마커를 누르면 여기에 맥락이 보입니다</b>
        <p className="sub">직전 오류 → 내 질문 → 답변 발췌 → 이후 무엇을 직접 했나.</p>
        <p className="note">이 맥락은 Learn 모드 · 맥락 수집 켜짐 상태에서 확장·Office 모듈이 저장한 것입니다. Proof 세션에는 없습니다.</p>
      </aside>
    );
  }
  const k = KIND[mk.kind] || KIND.selection;
  const it = mk.item;
  const c = contextAround(s, ctx, mk);
  const where = it?.meta?.domain || it?.meta?.file || it?.meta?.app || (mk.paste ? mk.paste.target : '');

  return (
    <aside className="ctxpanel">
      <div className="hd"><span className="ic" style={{ background: k.c }}>{k.ic}</span><b>{clock(mk.ts)} {k.t}</b>{where && <span className="badge">{where}</span>}</div>

      {c.before && mk.kind !== 'error' && (
        <section><h5>직전 — {clock(c.before.ts)} 오류</h5><pre className="errbox">{c.before.text}</pre></section>
      )}

      {mk.kind === 'error' && <section><h5>오류</h5><pre className="errbox">{it.text}</pre></section>}
      {mk.kind === 'ai_question' && <section><h5>질문 — 내가 입력한 것</h5><blockquote>"{it.text}"</blockquote></section>}
      {mk.kind === 'chat' && <section><h5>물어보기 — 알약 위 질문칸</h5><pre className="quote">{it.text}</pre></section>}
      {mk.kind === 'page' && <section><h5>참고 페이지</h5><blockquote>{it.text}</blockquote></section>}
      {mk.kind === 'selection' && <section><h5>선택한 부분</h5><pre className="quote">{it.text}</pre></section>}
      {mk.kind === 'diff' && <section><h5>직접 수정 — {it.meta?.where || it.meta?.file}{it.meta?.chars != null ? ` · ${it.meta.chars > 0 ? '+' : ''}${it.meta.chars}자` : ''}</h5><pre className="quote">{it.text}</pre></section>}
      {mk.kind === 'paste_at' && <section><h5>문서에 붙여넣음 — {it.meta?.file} {it.meta?.where} · {it.meta?.chars}자</h5><pre className="quote">{it.text}</pre></section>}
      {(mk.kind === 'run_result' || mk.kind === 'solved') && <section><h5>실행 결과</h5><blockquote>{it.text}</blockquote></section>}
      {mk.paste && (
        <section><h5>붙여넣기 {mk.paste.len}자 → {mk.paste.target_title || mk.paste.target}</h5>
          <p>{pasteText(mk.paste)}{mk.paste.after_typed != null && <> · 이후 3분 직접 입력 <b style={{ color: '#047857' }}>{mk.paste.after_typed}자</b></>}</p></section>
      )}

      {c.answer && <section><h5>답변 발췌 — 복사한 {c.answer.text.length}자</h5><blockquote className="ans">{c.answer.text}</blockquote></section>}

      {c.after.length > 0 && (
        <section><h5>이후</h5>
          <ul className="after">{c.after.map((a, i) => (
            <li key={i}><span className="mono dim">{a.ts}</span> <span style={{ color: a.kind === 'typed' || a.kind === 'diff' ? '#047857' : a.kind === 'solved' ? '#059669' : a.kind === 'error' ? '#b91c1c' : a.ai ? '#b91c1c' : undefined, fontWeight: a.kind === 'typed' || a.kind === 'diff' || a.kind === 'solved' ? 600 : 400 }}>{a.text}</span></li>
          ))}</ul></section>
      )}

      <div className="acts">
        <button className="btn ask" onClick={() => onAsk && onAsk(it?.text || (mk.paste ? `${mk.paste.len}자 붙여넣기` : ''))}>물어보기에서 더 묻기</button>
      </div>
      <p className="note">이 맥락은 Learn 모드 · 맥락 수집 켜짐 상태에서 저장된 것입니다. Proof 세션에는 없습니다.</p>
    </aside>
  );
}
