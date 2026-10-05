// 팝업 — 수집기가 켜져 있는지, 무엇을 담는지(항목별 토글)만 보여준다. 설정은 수집기 config.json 의 capture.
// 9/28 개정: Learn/Proof 모드 없음. 원문은 전부 이 PC 에만 저장되고 서버로는 해시만 간다.
chrome.runtime.sendMessage({ type: "status" }).then((s) => {
  const el = document.getElementById("body");
  if (!s || !s.recording) { el.innerHTML = '<span class="dot" style="background:#9ca3af"></span>수집기가 꺼져 있습니다.<br><span class="muted">3-코드/1_기록시작.bat 을 실행하세요.</span>'; return; }
  let html = `<div class="row"><span><span class="dot" style="background:#ef4444"></span><b>기록 중</b></span><span class="muted">${(s.session_id || "").slice(0, 8)}…</span></div>`;
  html += `<div class="row"><span>탭 전환</span><span>보냄</span></div>`;
  const cap = s.capture || s.learn_context || {};
  const names = { ai_question: "AI 질문", ai_answer: "AI 답 원문", ai_answer_excerpt: "복사한 발췌", selection: "선택 텍스트" };
  const on = (k) => (k === "ai_question" || k === "ai_answer") ? cap[k] !== false : !!cap[k];
  for (const k of Object.keys(names)) html += `<div class="row"><span>${names[k]}</span><span style="color:${on(k) ? "#047857" : "#9ca3af"}">${on(k) ? "켜짐" : "꺼짐"}</span></div>`;
  html += `<div class="row muted">원문은 이 PC 에만 · 서버엔 해시만${s.ai_count ? ` · AI ${s.ai_count}건` : ""}</div>`;
  el.innerHTML = html;
}).catch(() => { document.getElementById("body").textContent = "수집기 연결 실패"; });
