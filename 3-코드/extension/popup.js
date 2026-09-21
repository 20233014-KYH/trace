// 팝업 — 수집기가 켜져 있는지, 어느 모드인지, 맥락 항목이 뭐가 켜졌는지만 보여준다. 설정은 수집기 config.json 에서.
chrome.runtime.sendMessage({ type: "status" }).then((s) => {
  const el = document.getElementById("body");
  if (!s || !s.recording) { el.innerHTML = '<span class="dot" style="background:#9ca3af"></span>수집기가 꺼져 있습니다.<br><span class="muted">3-코드/1_기록시작.bat 을 실행하세요.</span>'; return; }
  const mode = s.mode === "learn" ? "Learn" : "Proof";
  const color = s.mode === "learn" ? "#0ea5e9" : "#ef4444";
  let html = `<div class="row"><span><span class="dot" style="background:${color}"></span><b>${mode} 기록 중</b></span><span class="muted">${(s.session_id || "").slice(0, 8)}…</span></div>`;
  html += `<div class="row"><span>탭 전환</span><span>보냄</span></div>`;
  if (s.mode === "learn") {
    const lc = s.learn_context || {};
    const names = { ai_question: "AI 질문", ai_answer_excerpt: "답변 발췌", selection: "선택 텍스트", page: "학습 페이지" };
    for (const k of Object.keys(names)) html += `<div class="row"><span>${names[k]}</span><span style="color:${lc[k] ? "#047857" : "#9ca3af"}">${lc[k] ? "켜짐" : "꺼짐"}</span></div>`;
  } else {
    html += `<div class="row muted">Proof 모드 — 내용(맥락)은 보내지 않습니다.</div>`;
  }
  el.innerHTML = html;
}).catch(() => { document.getElementById("body").textContent = "수집기 연결 실패"; });
