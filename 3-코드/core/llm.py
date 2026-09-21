"""
llm.py — Learn Mode 의 AI 호출 한 곳. 리포트 · 학습 흐름 묶기 · Side Chat.

교수 추천(9/20): 알리바바 Qwen. ★ 추천이지 결정이 아니다 — 최종 선택은 팀이 한다.
그래서 어댑터로 감쌌다. 같은 세션을 여러 공급자로 돌려 보고 정한다 (server/compare_llm.py).
키는 **서버 환경변수에만** 있다. 수집기·확장·화면은 이 모듈을 부르지 못한다 (서버가 부른다).

  LLM_PROVIDER = qwen | openai | claude | fake   (기본 fake — 키 없으면 가짜 리포트, 화면 개발용)
  DASHSCOPE_API_KEY                           Qwen (알리바바 Model Studio)
  DASHSCOPE_BASE_URL                          기본 국제(싱가포르) 엔드포인트 — 학생 데이터는 중국 리전으로 보내지 않는다
  QWEN_MODEL                                  기본 qwen-plus
  OPENAI_API_KEY · OPENAI_MODEL               GPT 비교용 (기본 gpt-5.6-luna — 가장 싼 급)
  ANTHROPIC_API_KEY · CLAUDE_MODEL            Claude 비교용 (기본 claude-opus-5)

Proof 세션은 이 모듈을 부르면 안 된다 — 부르는 쪽(dev_receiver)이 mode 를 확인한다.
보내는 것: 세션 id · flow(창별 요약) · 맥락 항목. 학생 이름·계정·이메일은 넣지 않는다.
"""
import json
import os
import re

PROVIDER = os.environ.get("LLM_PROVIDER", "fake").lower()
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")
QWEN_BASE = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")

REPORT_KEYS = ["topics", "struggles", "process", "points", "todo"]

REPORT_SYSTEM = """당신은 학생의 학습 세션 기록을 정리하는 조교다.
주어진 것은 (1) 이벤트 흐름 — 어떤 창에서 무엇을 했나, (2) 맥락 — AI에게 한 질문, 답변 중 복사한 부분, 참고 페이지, 오류, 문서에서 바뀐 부분이다.
이것으로 Learning Session Report 를 만든다. 반드시 아래 키만 가진 JSON 하나로만 답한다. 설명 문장, 코드 블록 표시, 다른 텍스트를 붙이지 않는다.
{
  "topics":    ["이번 세션의 주요 학습 내용 — 개념·주제 이름, 2~5개"],
  "struggles": ["가장 어려움을 겪은 부분 — 오류·반복 질문·반복 수정에서 드러난 것, 1~3개, 근거 시각 포함"],
  "process":   ["학습 과정 — 시간순 단계, '오류 발생 → AI에게 질문 → 답변 참고 → 직접 수정 → 재실행 → 해결' 처럼 화살표로, 흐름마다 하나"],
  "points":    ["학습 포인트 — 이 세션에서 새로 다뤄진 개념, 2~5개"],
  "todo":      ["추가 학습이 필요한 부분 — 답은 얻었지만 직접 적용·이해가 부족한 것, 1~3개"]
}
규칙:
- 점수·등급·"AI 사용 비율" 같은 판정을 만들지 않는다. AI 를 썼는지가 아니라 쓴 뒤 무엇을 직접 했는지를 본다.
- 기록에 없는 사실을 지어내지 않는다. 근거가 없으면 그 항목은 짧게 쓰거나 비운다.
- 한국어로, 각 항목은 한 문장. 학생을 비난하는 표현을 쓰지 않는다."""

CHAT_SYSTEM = """당신은 학생이 작업 중인 코드·문서 옆에서 답하는 학습 도우미(Side Chat)다.
학생이 선택한 부분과 이 세션에서 최근 겪은 오류·질문이 함께 주어진다. 정답 코드를 통째로 주기보다 왜 그런지 설명하고, 학생이 직접 고칠 수 있게 한다.
한국어로, 짧게. 이 세션의 기록(오류·질문 시각)을 근거로 말할 수 있으면 언급한다."""


# ─────────────────────────── 어댑터 ───────────────────────────
def _qwen():
    from openai import OpenAI   # Model Studio 는 OpenAI 호환 엔드포인트
    return OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=QWEN_BASE)


def _openai():
    from openai import OpenAI
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _claude():
    import anthropic
    return anthropic.Anthropic()


def complete(system: str, messages: list, json_mode: bool = False, max_tokens: int = 4000) -> str:
    """messages = [{"role":"user"|"assistant","content":str}, …] → 텍스트. 공급자 차이는 여기서만."""
    if PROVIDER == "qwen":
        r = _qwen().chat.completions.create(
            model=QWEN_MODEL, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}] + messages,
            **({"response_format": {"type": "json_object"}} if json_mode else {}),
        )
        return r.choices[0].message.content or ""
    if PROVIDER == "openai":                       # Qwen 과 같은 OpenAI 호환 호출 — 엔드포인트·키만 다름
        r = _openai().chat.completions.create(
            model=OPENAI_MODEL, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}] + messages,
            **({"response_format": {"type": "json_object"}} if json_mode else {}),
        )
        return r.choices[0].message.content or ""
    if PROVIDER == "claude":
        r = _claude().messages.create(
            model=CLAUDE_MODEL, max_tokens=max(max_tokens, 4000),
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        return next((b.text for b in r.content if b.type == "text"), "")
    return _fake(system, messages, json_mode)


def _fake(system, messages, json_mode):
    """키 없을 때 — 화면·API 개발용. 입력을 흉내만 낸다."""
    if json_mode:
        return json.dumps({
            "topics": ["(가짜) 예외 처리", "(가짜) 객체 초기화"],
            "struggles": ["(가짜) 14:05 NullPointerException — 질문 뒤 4분 만에 해결"],
            "process": ["오류 발생 → AI에게 질문 → 답변 참고 → 붙여넣기 → 직접 수정 → 재실행 → 해결"],
            "points": ["(가짜) 선언과 생성의 차이"],
            "todo": ["(가짜) 참조 변수와 객체의 관계를 코드로 직접 확인하기"],
            "_fake": True,
        }, ensure_ascii=False)
    return "(가짜 답변) LLM_PROVIDER 를 qwen 또는 claude 로 설정하고 키를 넣으면 실제 답이 옵니다."


# ─────────────────────────── Learn 작업 3개 ───────────────────────────
def _pack(session: dict, context: list) -> str:
    """서버가 AI 에 보내는 것 — 이름·계정 없음. flow 는 창별 요약, 맥락은 항목 텍스트."""
    flow_lines = []
    for w in session.get("flow", []):
        acts = [f"입력 {w['typed']}자·삭제 {w['deleted']}자"] if (w.get("typed") or w.get("deleted")) else []
        acts += [it.get("text", "") for it in w.get("items", [])]
        flow_lines.append(f"{w['ts']} [{w.get('cat','')}] {w.get('app','')} {w.get('title','')} — {' · '.join(a for a in acts if a) or '-'}")
    ctx_lines = [f"{it.get('ts','')[11:19]} {it.get('kind','')} ({it.get('meta',{}).get('domain') or it.get('meta',{}).get('app','')}): {(it.get('text') or '')[:500]}"
                 for it in context]
    return (f"[세션] {session.get('date')} {session.get('start')}–{session.get('end')} · {session.get('dur')}\n"
            f"[이벤트 흐름]\n" + "\n".join(flow_lines) + "\n\n[맥락]\n" + ("\n".join(ctx_lines) or "(없음)"))


def make_report(session: dict, context: list, retries: int = 2) -> dict:
    """Learning Session Report. JSON 이 깨지면 다시 부른다 (Qwen 이 가끔 형식을 어김)."""
    user = _pack(session, context)
    last_err = None
    for _ in range(retries + 1):
        raw = complete(REPORT_SYSTEM, [{"role": "user", "content": user}], json_mode=True)
        try:
            data = _parse_json(raw)
            if all(k in data and isinstance(data[k], list) for k in REPORT_KEYS):
                return {k: [str(x) for x in data[k]] for k in REPORT_KEYS} | ({"_fake": True} if data.get("_fake") else {})
            last_err = f"키 누락: {[k for k in REPORT_KEYS if k not in data]}"
        except ValueError as e:
            last_err = str(e)
        user = user + "\n\n(앞 응답이 JSON 형식을 어겼다. 지정된 키만 가진 JSON 하나로만 답하라.)"
    raise RuntimeError(f"리포트 JSON 실패: {last_err}")


def side_chat(selection: str, question: str, history: list, recent_context: list) -> str:
    """Side Chat 한 턴. history = [{"role","content"}], recent_context = 이 세션의 최근 맥락 몇 개."""
    ctx = "\n".join(f"- {it.get('ts','')[11:19]} {it.get('kind','')}: {(it.get('text') or '')[:200]}" for it in recent_context[-6:])
    first = f"[선택한 부분]\n{selection}\n\n[이 세션의 최근 기록]\n{ctx or '(없음)'}\n\n[질문]\n{question}"
    msgs = history + [{"role": "user", "content": first if not history else question}]
    return complete(CHAT_SYSTEM, msgs, max_tokens=1500)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"\{.*\}", raw, re.S)   # 앞뒤에 딴 말이 붙어도 JSON 부분만
    if not m:
        raise ValueError("JSON 없음")
    return json.loads(m.group(0))
