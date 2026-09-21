"""
test_derive.py — 계약 ①(이벤트) → 계약 ②(session.json) 변환이 골든과 같은지.
A 가 derive/chain 을 서버로 옮긴 뒤 "같은 입력 → 같은 출력" 을 확인하는 용도. pytest 없이 그냥 실행.

  python tests/test_derive.py            # 검사
  python tests/test_derive.py --update   # 골든 갱신 (의도한 변경일 때만 · 이유를 커밋 메시지에)
  python tests/test_derive.py --json     # 실패 상세를 JSON 으로 (다른 언어 구현과 비교할 때)

검사 3개:
  1. chain.verify — 픽스처 이벤트에 붙은 h 를 재계산해 전부 일치하는가 (서버가 해야 할 일 그대로)
  2. derive(events) == expected_basic.json  (segments · typed · deleted · pastes · undos · flow · chain · root · stats)
  3. root 가 골든과 같은가 (한 글자만 달라도 봉인 검증이 실패한다)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from core import chain as C          # noqa: E402
from core.derive import derive       # noqa: E402

FX = os.path.join(HERE, "fixtures")


def load_events(name="events_basic.jsonl"):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def diff(a, b, path="", out=None):
    """골든(a) 와 결과(b) 의 차이를 경로별로 모은다."""
    out = out if out is not None else []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: out.append((path + "." + k, "<없음>", b[k]))
            elif k not in b: out.append((path + "." + k, a[k], "<없음>"))
            else: diff(a[k], b[k], path + "." + k, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append((path + ".len", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append((path, a, b))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    update = "--update" in sys.argv
    as_json = "--json" in sys.argv
    events = load_events()
    fails = []

    # 1. 체인 재계산 = 이벤트의 h
    ok, bad = C.verify(events)
    if not ok:
        fails.append(("chain.verify", "일치", f"불일치 at {bad}"))

    # 2. derive 골든
    got = derive(events)
    gold_path = os.path.join(FX, "expected_basic.json")
    if update:
        with open(gold_path, "w", encoding="utf-8") as f:
            json.dump(got, f, ensure_ascii=False, indent=1)
        print("골든 갱신:", gold_path); return 0
    with open(gold_path, encoding="utf-8") as f:
        gold = json.load(f)
    fails += diff(gold, got)

    # 3. root
    rows, root = C.build(events)
    if root != gold["root"]:
        fails.append(("chain.root", gold["root"][:16] + "…", root[:16] + "…"))

    if as_json:
        print(json.dumps({"ok": not fails, "failures": [{"path": p, "expected": e, "got": g} for p, e, g in fails]}, ensure_ascii=False, indent=1))
    elif fails:
        print(f"✗ {len(fails)}곳 다름")
        for p, e, g in fails[:40]:
            print(f"  {p}\n     기대: {e!r}\n     결과: {g!r}")
    else:
        s = got["stats"]
        print(f"✓ 통과 — 이벤트 {len(events)} · 체인 {s['events']} · root {root[:16]}… · 직접 입력 {s['typed']}자({s['typed_pct']}%) · 붙여넣기 {len(got['pastes'])}건")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
