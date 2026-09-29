"""
기술테스트_제안서.py — 서비스 제안서 4장 "핵심 기술 테스트" 의 증거 코드. pytest 없이 그냥 실행.

  python tests/기술테스트_제안서.py

테스트 2개 (입력: tests/fixtures/events_basic.jsonl — 미리 만든 기록 38개):
  ① 붙여넣은 글의 출처 찾기 — 붙여넣기 4건이 각각 어디서 복사됐는지 맞게 나오는가
  ② 기록 조작 찾기 (해시 체인) — 글자 수 하나 바꾸기 / 기록 하나 지우기를 둘 다 잡아내는가
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import chain as C          # noqa: E402
from core.derive import derive       # noqa: E402

with open(os.path.join(HERE, "fixtures", "events_basic.jsonl"), encoding="utf-8") as f:
    ev = [json.loads(l) for l in f if l.strip()]

ok = True

# ① 출처 찾기 — 픽스처를 만들 때 정한 정답과 비교
answer = [  # (글자 수, AI 답인가, 출처를 찾았나)
    (200, True, True),    # chatgpt.com → Main.java
    (14, False, True),    # 파일 탐색기 → 코드
    (77, False, False),   # 복사 기록 없음 → "출처 없음" 이 정답
    (120, True, True),    # chatgpt.com → 보고서.docx
]
pastes = derive(ev)["pastes"]
got = [(p["len"], p["ai"], p["matched"]) for p in pastes]
hit = sum(g == a for g, a in zip(got, answer))
print(f"① 출처 찾기: {hit}/{len(answer)} 맞음")
for p in pastes:
    src = p.get("src") or {}
    where = f"{src['app']} ({src.get('category')})" if p["matched"] else "없음"
    print(f"   {p['len']:>4}자  출처={where:<22} AI 답={p['ai']!s:<5} → {p['target_title']}")
ok &= hit == len(answer) == len(got)

# ② 조작 찾기
print(f"② 원본 검증: {C.verify(ev)}")
first = next(i for i, e in enumerate(ev) if e["type"] == "paste")

t = copy.deepcopy(ev)
t[first]["len"] += 1                      # 붙여넣은 글자 수를 1 바꿈
r1 = C.verify(t)
print(f"   글자 수 1 바꿈 → {r1}")

t = copy.deepcopy(ev)
del t[first]                              # 기록 하나 지움
r2 = C.verify(t)
print(f"   기록 하나 지움 → {r2}")

ok &= C.verify(ev)[0] and not r1[0] and not r2[0]
print("✓ 통과" if ok else "✗ 실패")
sys.exit(0 if ok else 1)
