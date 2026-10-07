"""
mask.py — 원문을 PC 에 저장하기 **전에** 비밀·개인정보를 가린다 (원칙 4 · docs/api.md 10-2 "자동 가리기 → 그다음 해시").

가린 자리는 ⟦가림:종류⟧ 로 바뀌고, 해시는 가린 뒤의 글로 계산한다.
그래서 API 키가 PC 파일에도 안 남고, 제출 때 서버가 같은 글로 해시를 맞춰 볼 수 있다.

  masked, n = mask("내 키는 sk-abc… 이고 메일은 a@b.com")
  → ("내 키는 ⟦가림:API키⟧ 이고 메일은 ⟦가림:이메일⟧", 2)

판정이 아니라 모양 맞추기다. 놓치는 것이 있을 수 있어서, 학생이 제출 전에 직접 가리는 단계(가리기 화면)가 따로 있다.
"""
import re

# (종류, 패턴) — 위에서부터 차례로. 긴 것(키)을 먼저 가려야 이메일·숫자 패턴이 키 일부를 먹지 않는다.
RULES = [
    ("API키", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_\-]{20,}")),        # OpenAI · Anthropic
    ("API키", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),                            # AWS 액세스 키
    ("API키", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),                      # Google
    ("API키", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),                  # GitHub
    ("API키", re.compile(r"\bxox[abpr]-[A-Za-z0-9\-]{10,}\b")),                # Slack
    ("비밀키", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("주민번호", re.compile(r"\b\d{6}-?[1-4]\d{6}\b")),
    ("이메일", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("전화번호", re.compile(r"\b01[016789][-. ]?\d{3,4}[-. ]?\d{4}\b")),
]


def mask(text: str):
    """(가린 글, 가린 개수)"""
    n = 0
    for kind, rx in RULES:
        text, k = rx.subn(f"⟦가림:{kind}⟧", text)
        n += k
    return text, n
