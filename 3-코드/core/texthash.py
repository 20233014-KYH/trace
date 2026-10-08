"""
texthash.py — 글(원문)의 해시. 기록기(PC) · 서버가 이 함수 하나를 쓴다 (docs/api.md 10-7 ②).

  sha256_text(s) = "sha256:" + SHA-256(UTF-8)

기록하는 순간 PC 는 원문의 해시만 체인(ai_msg.hash 등)에 넣고, 원문은 PC 에 둔다.
내역서를 만들 때 원문이 서버로 오면 서버가 이 함수로 다시 계산해 체인의 해시와 비교한다.
→ 두 곳에서 계산 방법이 1바이트라도 다르면 진짜 원문도 "조작됨"이 된다. 그래서 여기 하나만 둔다.

(collector.sha256_text · match._sha256 은 같은 식이다. 그쪽도 이걸 import 하도록 옮기면 된다 — 박상진)
"""
import hashlib


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8", "surrogatepass")).hexdigest()
