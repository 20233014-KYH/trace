"""
match.py — 결과물 문장 ↔ AI 답 연결 "제안" (기록기·서버 공용 · chain.py 와 같은 원칙: 여기 말고 다른 데서 짜지 않는다)

결과물(보고서·코드)을 문장으로 나누고, 문장마다 저장해 둔 AI 답 원문과 비교해 넷 중 하나를 붙인다.

  exact   AI 답과 일치·유사 — 글자 순서까지 90% 이상 같음 (붙여넣기 기록이 있든 없든 · 화면에 기록 유무를 따로 보여 줌)
                         full=True(공백·문장부호 빼고 100% 같음)면 화면에 "일치", 아니면 "유사" (10/7 사용자 결정 · 숫자는 안 냄)
  edited  붙여넣고 고침    — 내용이 AI 답에서 왔고, 그 AI 답 문장을 복사해 붙여넣은 **기록이 있음**
  viewed  AI 답 보고 씀    — 내용이 AI 답에서 왔지만 붙여넣은 기록은 없음 (참고해 다시 씀 · 보고 옮겨 침 — 둘을 가르지 않는다)
  web     다른 곳에서 붙여넣음 — AI 답은 아니지만 다른 사이트·프로그램(나무위키 · 위키백과 · PDF …)에서 복사해 붙여넣은 글.
                         고쳤든 안 고쳤든 하나로 (10/5 결정 · 화면 색은 그대로와 같은 빨강 · 출처는 오른쪽 칸 맨 아래)
  noproc  쓴 과정 기록 없음 — 이 PC 에서 타이핑·붙여넣기 없이 문서에 나타난 글: 열었을 때 이미 있던 글(AI 가 만든 Word 파일 ·
                         다른 기기에서 만든 파일) 또는 키 입력 없이 한꺼번에 들어온 글(프로그램이 넣음). 화면 색 빨강 (10/7 결정).
                         AI 라고 단정하진 않는다 — "과정이 기록에 없다" 는 사실만. 학생이 내역서에서 설명한다.
  none    출처 기록 없음   — 이어지는 AI 답·붙여넣기가 없음 (타이핑 기록이 있으면 여기). "직접 씀" 이라고 단정하지 않는다 (원칙 2)

edited / viewed 는 글자 비교가 아니라 **과정 기록**으로 가른다 (10/5 결정 — 글자만으로는 "고쳤다" 와 "보고 다시 썼다" 를 못 가름).
과정 기록이 없으면(pasted=None) 둘을 가르지 않고 edited 로 둔다 (글자 비교만 한 시험용).

★ 판정이 아니라 **제안**이다. 학생이 화면에서 맞다/아니다를 고른다 (docs/api.md 10절).
★ 점수(ratio·cover)는 기준을 맞추는 데만 쓰고 **화면·PDF·API 어디에도 내지 않는다** (원칙 1 · 퍼센트 금지).

파이썬 기본 기능만 쓴다 (difflib · re). 한국어는 띄어쓰기·조사가 바뀌어도 잡히게 공백·문장부호를 빼고 글자 두 개씩(bigram) 본다.
"""
import bisect
import difflib
from collections import Counter
from functools import lru_cache
from itertools import chain
import hashlib
import re

EXACT_RATIO = 0.90     # 이 이상 같으면 "그대로"
EDIT_COVER = 0.30      # 결과 문장의 글자 조각 중 이만큼이 한 AI 답(문장 또는 이웃 두 문장)에 있으면 "이어짐"(고침·보고 씀)
# ↑ 10/5 시험 세 개로 정함 (tests/연결시제품.py):
#   match(문장 12) 로 0.50 → 0.35 (10/12 → 12/12) · match_rec(녹화 · 8) 0.35 에서 7/8 — 0.34 짜리를 놓침
#   → match3(경제 · 14 · 점수 보기 전에 정답을 씀) 로 0.30 확인: 9/14 → 10/14
#   세 시험 합계: 0.35 = 28/34 · 0.30 = 30/34. 직접 쓴 문장을 AI 로 잘못 잡은 건 둘 다 0개.
#   직접 쓴 문장 10개(같은 주제 4개 포함)는 가장 높아도 0.20 · 잡아야 할 문장은 0.34 부터 → 0.30 은 그 빈 틈 안.
#   ★ 말을 다 바꿔 쓴 문장(0.07 · 0.10 · 0.16)은 직접 쓴 문장보다도 낮다 → 글자 비교로는 어떤 기준으로도 못 잡는다.
#     이건 기준 문제가 아니라 방법의 한계. "출처 기록 없음" 으로 남고, 그래서 "직접 씀" 이라 쓰지 않는다 (원칙 2).
PAIR_GAIN = 1.2        # 이웃 두 문장이 한 문장보다 이만큼(배) 더 겹칠 때만 "두 문장을 합쳐 고침" 으로 본다
# ↑ 같은 10/5 시험: 두 문장을 합친 문장은 1.23배 · 한 문장만 고친 문장은 1.00~1.10배. 역시 새 자료로 다시 확인할 것.
MIN_CHARS = 8         # 이보다 짧은 문장(제목·한 단어)은 비교하지 않는다 — 우연히 겹치기 쉬움

_SENT_END = re.compile(r"(?<=[.!?。])\s+|\n+")


def split_sentences(text: str):
    """문장 나누기 — 마침표·물음표·느낌표 뒤 공백, 또는 줄바꿈. 마크다운 굵게(**)는 지운다(화면엔 안 보이는 글자)."""
    text = text.replace("**", "")
    return [s.strip() for s in _SENT_END.split(text) if s and s.strip()]


def norm(s: str) -> str:
    """비교용: 소문자 · 공백·문장부호 제거 (한글·영문·숫자만)"""
    return re.sub(r"[\W_]+", "", s.lower())


def _bigrams(s: str):
    return {s[i:i + 2] for i in range(len(s) - 1)}


def compare(result: str, ai: str):
    """(ratio, cover) — ratio: 순서까지 본 유사도 · cover: result 의 글자 조각 중 ai 에도 있는 비율"""
    r, a = norm(result), norm(ai)
    if len(r) < 2 or len(a) < 2:
        return 0.0, 0.0
    ratio = difflib.SequenceMatcher(None, r, a, autojunk=False).ratio()
    br = _bigrams(r)
    cover = len(br & _bigrams(a)) / len(br)
    return ratio, cover


def _prep(c):
    """후보의 비교용 글(norm) · 글자 조각을 한 번만 만든다 (10/14 · 22쪽 문서에서 문장마다 다시 만들어 27초 걸림)"""
    if "_n" not in c:
        c["_n"] = norm(c["text"])
        c["_b"] = _bigrams(c["_n"])
    return c


def _빠른_비교(r, br, c, need_ratio):
    """compare() 와 같은 값 — 다만 ratio 는 need_ratio 이고 90% 에 닿을 수 있을 때만 셈 (못 닿으면 0.0).
    difflib ratio = 2·맞은 글자 / 두 길이 합 ≤ 2·짧은 길이 / 두 길이 합 → 이게 기준 아래면 "그대로" 가 될 수 없다.
    ratio 는 "그대로" 판단에만 쓰이고(나머지는 시험 출력용 _ratio) 결과는 compare() 로 돌린 것과 같다."""
    a = c["_n"]
    if len(r) < 2 or len(a) < 2:
        return 0.0, 0.0
    cover = len(br & c["_b"]) / len(br)
    ratio = 0.0
    if need_ratio and 2 * min(len(r), len(a)) >= EXACT_RATIO * (len(r) + len(a)):
        sm = difflib.SequenceMatcher(None, r, a, autojunk=False)
        if sm.quick_ratio() >= EXACT_RATIO:            # 글자 모음만 본 위 한계 — 이것도 못 넘으면 순서 비교 생략
            ratio = sm.ratio()
    return ratio, cover


class _후보들(list):
    """candidates() 결과 — 글자 조각(bigram) → 후보 번호 색인을 처음 쓸 때 한 번 만든다 (10/14).
    100쪽 문서(문장 2,600)에서 문장마다 후보 전부(수천)를 훑어 38초 걸렸다 → 글자 조각이 하나라도 겹친 후보만 본다.
    하나도 안 겹친 후보는 cover 0 · ratio 0 이라 결과에 영향이 없다 (그래서 결과가 전과 같다)"""

    def 색인(self):
        idx = getattr(self, "_색인", None)
        if idx is None:
            idx = {}
            for i, c in enumerate(self):
                for g in _prep(c)["_b"]:
                    idx.setdefault(g, []).append(i)
            self._색인 = idx
        return idx


def _겹침(br, cands):
    """{후보 번호: 겹친 글자 조각 수} — 하나라도 겹친 후보만 (= len(br & 후보 조각))"""
    idx = cands.색인()
    return Counter(chain.from_iterable(idx[g] for g in br if g in idx))


def _그대로_될_수(r, D, a, k):
    """이 후보가 90% 이상 같을(ratio ≥ EXACT_RATIO) 수 있나 — 겹친 글자 조각 수 k 로 먼저 거른다 (못 되면 difflib 을 아예 안 부름).
    증명 (n = len(r) · m = len(a) · T = n + m · D = r 의 서로 다른 글자 조각 수 · M = 맞은 글자 수):
      ratio = 2M/T ≥ E(0.9) → M ≥ (E/2)T. 맞은 덩어리(block) 수 b 는 덩어리 사이마다 안 맞은 글자가 하나 이상 → b ≤ T − 2M + 1.
      덩어리 안의 글자 조각 자리 = M − b ≥ 3M − T − 1 ≥ (1.5E − 1)T − 1 = 0.35T − 1 — 이 자리들의 글자 조각은 a 에도 있다.
      r 에서 같은 조각이 되풀이된 자리는 많아야 (n − 1 − D) 이니 서로 다른 겹친 조각 k ≥ 0.35T − n + D.
    그러니 k 가 이보다 작으면 90% 가 될 수 없다 — 결과는 전과 같다"""
    return k >= (1.5 * EXACT_RATIO - 1) * (len(r) + len(a)) - len(r) + D - 1e-9      # 0.9 → 0.35 (위 식의 일반형)


def _문턱(r, D):
    """겹친 글자 조각 수가 이보다 적은 후보는 결론(그대로 · 고침)에 들 수 없다 (10/14 · AI 대화가 아주 많으면 문장마다 수천 개를 훑었다).
      고침: cover = k/D ≥ EDIT_COVER 여야 함
      그대로: 길이 조건(2·짧은 길이 ≥ E·두 길이 합)이 후보 길이 m ≥ E·n/(2−E) 를 요구하고, _그대로_될_수 의 한계는 m 이 클수록
             커지니 그 가장 작은 m 의 한계보다 적게 겹친 후보는 그대로가 될 수 없다
    둘 다 못 되는 후보는 "가장 가까운 것"(시험 출력용 _cover · _ratio)에만 쓰이던 것 — 그 값만 달라질 수 있고 결론은 같다.
    1e-6 은 소수 계산 오차 여유 (조금 더 많이 보는 쪽)"""
    n = len(r)
    m = EXACT_RATIO * n / (2 - EXACT_RATIO)
    return min(EDIT_COVER * D, (1.5 * EXACT_RATIO - 1) * (n + m) - n + D) - 1e-6


def _순서_비교(r, c):
    """difflib ratio — 90% 에 닿을 수 있을 때만 (quick_ratio 로 먼저 거름). 후보 쪽 준비(SequenceMatcher 의 b)는 한 번만:
    전엔 비교마다 SequenceMatcher 를 새로 만들어 후보 글자표(b2j)를 다시 만들었다 — 값은 같다"""
    sm = c.get("_sm")
    if sm is None:
        sm = c["_sm"] = difflib.SequenceMatcher(None, autojunk=False)
        sm.set_seq2(c["_n"])
    sm.set_seq1(r)
    return sm.ratio() if sm.quick_ratio() >= EXACT_RATIO else 0.0


def candidates(answers):
    """AI 답들 → 비교 후보: 문장 하나씩 + 이웃한 두 문장을 합친 것 (두 문장을 합쳐 다시 쓴 경우용)
    answers: [{"id", "text", ...}] → [{"answer": id, "sents": (i,) | (i, i+1), "text"}]"""
    out = _후보들()
    for a in answers:
        ss = split_sentences(a["text"])
        for i, s in enumerate(ss):
            out.append({"answer": a["id"], "sents": (i,), "text": s})
            if i + 1 < len(ss):
                out.append({"answer": a["id"], "sents": (i, i + 1), "text": s + " " + ss[i + 1]})
    return out


def link_sentence(sentence: str, cands, keep=None):
    """한 문장 → {"label", "answer", "sents", "ai_text", "_ratio", "_cover"}  (밑줄 칸은 시험용 · 화면에 안 냄)
    keep(후보) 가 있으면 그게 참인 후보만 본다 (전엔 걸러 낸 목록을 새로 만들어 넘겼다 — 그러면 색인을 못 씀)"""
    best = {"label": "none", "answer": None, "sents": None, "ai_text": None, "_ratio": 0.0, "_cover": 0.0}
    r = norm(sentence)
    if len(r) < MIN_CHARS:
        return best
    br = _bigrams(r)
    one = two = None                    # "고침" 후보: 가장 잘 맞는 한 문장 · 가장 잘 맞는 이웃 두 문장
    if isinstance(cands, _후보들):           # 색인: 겹친 후보만 · 원래 차례대로 (같은 값이면 먼저 나온 후보가 이기는 규칙 그대로)
        겹, D = _겹침(br, cands), len(br)
        문턱 = _문턱(r, D)
        보기 = ((cands[i], 겹[i] / D) for i in sorted(i for i, k in 겹.items() if k >= 문턱))
    else:
        보기 = ((c, None) for c in cands)
    for c, cover in 보기:
        if keep is not None and not keep(c):
            continue
        if cover is None:
            ratio, cover = _빠른_비교(r, br, _prep(c), len(c["sents"]) == 1)
        else:
            a = c["_n"]
            ratio = (_순서_비교(r, c) if len(c["sents"]) == 1 and 2 * min(len(r), len(a)) >= EXACT_RATIO * (len(r) + len(a))
                     and _그대로_될_수(r, len(br), a, round(cover * len(br))) else 0.0)
        if len(c["sents"]) == 1 and ratio >= EXACT_RATIO and ratio > best["_ratio"]:
            best = {"label": "exact", "answer": c["answer"], "sents": c["sents"], "ai_text": c["text"], "_ratio": ratio, "_cover": cover}
        elif cover >= EDIT_COVER:
            hit = {"label": "edited", "answer": c["answer"], "sents": c["sents"], "ai_text": c["text"], "_ratio": ratio, "_cover": cover}
            if len(c["sents"]) == 1 and (one is None or cover > one["_cover"]):
                one = hit
            elif len(c["sents"]) == 2 and (two is None or cover > two["_cover"]):
                two = hit
        elif best["label"] == "none" and cover > best["_cover"]:
            best.update(_ratio=max(best["_ratio"], ratio), _cover=cover)   # 기준엔 못 미친 가장 가까운 것 (시험 출력용)
    if best["label"] == "exact":
        return best
    # 두 문장은 한 문장을 품으니 늘 조금 더 겹친다 → 확실히 더 겹칠 때만 두 문장 (화면에서 어느 부분을 칠할지가 달라짐)
    if two and (one is None or two["_cover"] >= one["_cover"] * PAIR_GAIN):
        return two
    return one or best


def _라벨들(sentence, cands):
    """{후보의 answer: "exact" | "edited"} — answer 마다 link_sentence(sentence, 그 answer 의 후보들) 의 결론과 같다:
    한 문장 후보 중 90% 이상 같은 게 있으면 exact · 아니면 글자 조각이 EDIT_COVER 넘게 겹친 후보가 있으면 edited"""
    r = norm(sentence)
    if len(r) < MIN_CHARS:
        return {}
    br = _bigrams(r)
    out = {}
    문턱 = _문턱(r, len(br))
    for i, k in _겹침(br, cands).items():
        if k < 문턱:
            continue
        c = cands[i]
        if out.get(c["answer"]) == "exact":
            continue
        a = c["_n"]
        if (len(c["sents"]) == 1 and 2 * min(len(r), len(a)) >= EXACT_RATIO * (len(r) + len(a))
                and _그대로_될_수(r, len(br), a, k) and _순서_비교(r, c) >= EXACT_RATIO):
            out[c["answer"]] = "exact"
        elif k / len(br) >= EDIT_COVER:
            out[c["answer"]] = "edited"
    return out


def latest_messages(records):
    """ai-messages 기록 → 생성 도중 잘린 답을 뺀 것 (이슈 #26-4).
    · 기록기가 "replaces"(이 글이 대체한 앞 글의 해시)를 남겼으면 그 앞 글을 뺀다
    · 예전 기록(replaces 없음)도: 같은 도구·턴·역할에서 뒤 글이 앞 글을 그대로 품으면 앞 글을 뺀다
      — 눈에 안 보이는 글자(\\u200b 등)·띄어쓰기·빈 줄 차이는 무시한다. ChatGPT 앱은 답을 다 쓴 뒤
        문단 끝에 \\u200b 와 빈 줄만 더 넣어서, 같은 답이 두 번 남아 문장이 앞 답에 붙는 일이 있었다 (10/12 실제 시험)"""
    gone = {r["replaces"] for r in records if r.get("replaces")}
    키 = lambda r: (r.get("session_id"), r.get("tool"), r.get("turn"), r.get("role"))     # 같은 기록 안에서만
    # 뒤에서부터 · 같은 키의 뒤 글들을 정렬해 두고 찾는다 (10/14 · 전엔 글마다 뒤 글 전부를 훑어 대화가 많으면 몇 초)
    # 정렬된 목록에서 t 로 시작하는 글은 t 가 들어갈 자리 바로 뒤에 모여 있다
    뒤, 뺄 = {}, set()
    for i in range(len(records) - 1, -1, -1):
        t = _보이는_글(records[i].get("text", ""))
        글들 = 뒤.setdefault(키(records[i]), [])
        j = bisect.bisect_left(글들, t)
        if j < len(글들) and 글들[j].startswith(t):
            뺄.add(i)
        글들.insert(j, t)
    return [r for i, r in enumerate(records) if r.get("hash") not in gone and i not in 뺄]


_안보임 = re.compile(r"[​-‏⁠﻿]")


def _보이는_글(s):
    return " ".join(_안보임.sub("", s).split())


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8", "surrogatepass")).hexdigest()   # 수집기 sha256_text 와 같게


def pasted_from_ai(events, context):
    """과정 기록 → AI 답에서 복사해 붙여넣은 글 [{"text", "copied_at", "pasted_at", "file", "where"}]

    고리는 해시 셋이 **똑같은지**만 본다 (창 이름·시간으로 추측하지 않음):
      확장이 AI 사이트에서 받은 복사 발췌(context kind=ai_answer_excerpt) 의 sha256
        = 수집기 copy 이벤트 해시  = 수집기 paste 이벤트 해시
    붙여넣은 문서·자리는 paste 직후(10초 안) 첫 doc_paste_at 에서 가져온다 (없으면 빈칸)."""
    excerpts, copies = _ai_copies(events, context)
    out = []
    evs = sorted(events, key=lambda e: e.get("ts", ""))
    for i, e in enumerate(evs):
        if e.get("type") != "paste" or e.get("hash") not in copies:
            continue
        at = _paste_spot(evs, i) or {}
        if not at and (e.get("app") or "").lower() in BROWSERS | AI_APPS:
            continue                         # 문서가 아니라 웹 · AI 앱 입력칸에 붙여넣음 (10/14: Claude 답을 구글 AI 에 질문으로 → 문서의 구글 답이 Claude 로 잡힘)
        out.append({"text": excerpts[e["hash"]]["text"], "copied_at": copies[e["hash"]]["ts"], "pasted_at": e["ts"],
                    "file": at.get("file", ""), "where": at.get("where", ""), "domain": excerpts[e["hash"]].get("meta", {}).get("domain", "")})
    return out


def _ai_copies(events, context):
    """AI 답에서 복사한 것 → ({copy 해시: 발췌}, {copy 해시: copy 이벤트})
    ① 해시 고리: 발췌 sha256 = copy 해시 (기본 · 확실)
    ② 해시가 안 맞는 브라우저 복사: 같은 순간(3초 안) 확장이 보낸 발췌가 있으면 그것 (10/14 실제 시험 — ChatGPT 웹의 복사 단추는
       표 · 굵게(**)를 화면 글과 다르게 클립보드에 넣어 해시가 달랐다. 그 뒤 기록기가 클립보드 글로 발췌를 남겨 ① 로 잡힘)"""
    excerpts = {}
    for c in context:
        if c.get("kind") == "ai_answer_excerpt" and c.get("text"):
            excerpts.setdefault(_sha256(c["text"]), c)
    copies = {e["hash"]: e for e in events if e.get("type") == "copy" and e.get("hash") in excerpts}
    웹발췌 = sorted((c for c in context if c.get("kind") == "ai_answer_excerpt" and c.get("text") and c.get("source") == "browser"),
                 key=lambda c: c.get("ts", ""))
    쓴 = {id(excerpts[h]) for h in copies}
    for e in events:
        if e.get("type") != "copy" or not e.get("hash") or e["hash"] in copies or (e.get("app") or "").lower() not in BROWSERS:
            continue
        c = next((c for c in 웹발췌 if id(c) not in 쓴 and abs(_secs(e["ts"], c["ts"])) <= 3), None)
        if c is not None:
            쓴.add(id(c))
            excerpts[e["hash"]], copies[e["hash"]] = c, e
    return excerpts, copies


BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "whale.exe", "google chrome", "microsoft edge", "firefox", "safari"}


def pasted_from_other(events, context):
    """과정 기록 → AI 답이 **아닌** 곳에서 복사해 문서에 붙여넣은 글 [{"text", "source", "category", "copied_at", "pasted_at", "file", "where"}]

    · AI 답 붙여넣기(pasted_from_ai 의 해시 고리)는 뺀다.
    · 출처: 복사한 순간의 앱이 브라우저면 그때 보던 탭 도메인(확장 tab 이벤트), 아니면 앱 이름. 복사 기록이 없으면(기록 시작 전 복사) "".
    · **자기 글 옮기기는 뺀다**: 복사한 곳 = 붙여넣은 곳(같은 앱 · 브라우저면 같은 도메인) — Word 안에서 잘라 붙이기 등.
    · 글자: 원문이 따로 없어서 붙여넣은 순간 문서에 새로 들어온 글(context kind=diff · doc_paste_at 과 같은 시각·자리)을 쓴다.
      capture.office 가 꺼져 있으면 글자가 없어서 문장과 잇지 못한다 (붙여넣기 사실은 과정 기록 화면에 그대로 남음)."""
    ai = set(_ai_copies(events, context)[0])
    diffs = [c for c in context if c.get("kind") == "diff" and c.get("text")]
    evs = sorted(events, key=lambda e: e.get("ts", ""))
    tab = ("", "other")                      # 지금 보던 탭 (domain, category)
    copies, out = {}, []
    for i, e in enumerate(evs):
        t = e.get("type")
        if t == "tab":
            tab = (e.get("domain", ""), e.get("category", "other"))
        elif t == "copy":
            browser = e.get("app", "").lower() in BROWSERS
            copies[e.get("hash")] = {"ts": e["ts"], "app": e.get("app", ""), "domain": tab[0] if browser else "",
                                     "category": tab[1] if browser else e.get("category", "other")}
        elif t == "paste" and e.get("hash") and e["hash"] not in ai:
            c = copies.get(e["hash"])
            if c and c["app"].lower() == e.get("app", "").lower() and (c["app"].lower() not in BROWSERS or c["domain"] == tab[0]):
                continue                     # 같은 곳에서 복사해 같은 곳에 붙임 = 자기 글 옮기기
            at = _paste_spot(evs, i)
            if not at:
                continue
            text = "\n".join(d["text"] for d in _붙인_글(at, diffs, int(e.get("len") or 0)))
            if not text.strip():
                continue
            src = (c["domain"] or c["app"].removesuffix(".exe").removesuffix(".EXE")) if c else ""
            out.append({"text": text.strip(), "source": src, "category": c["category"] if c else "",
                        "copied_at": c["ts"] if c else "", "pasted_at": e["ts"], "file": at.get("file", ""), "where": at.get("where", "")})
    return out


OFFICE_EXE = {"Word": "WINWORD.EXE", "PowerPoint": "POWERPNT.EXE"}
TYPED_KEYS = 0.3       # 새로 생긴 글자 1자당 이만큼 이상 키를 눌렀으면 "타이핑" (한글은 1자에 2~3번 · 영어는 1번 · 넉넉히)
KEYS_WINDOW = (-15, 12)  # 글 변화(diff) 시각 기준으로 이 구간(초)의 그 앱 키 입력을 본다 (Word 는 2초마다 · 키는 10초마다 모아 냄)


def process_evidence(events, context):
    """과정 기록 → 문서에 글이 생긴 길 {"typed": [글], "noproc": [{"text","how","ts","file"}]}

    · 타이핑: 붙여넣기 아닌 글 변화(diff) 중 그 무렵 그 앱에서 키를 충분히 누른 것 (키는 한 번 쓰면 깎는다 —
      타이핑 직후 프로그램이 한꺼번에 넣은 글이 그 키를 또 쓰지 않게)
    · 과정 없음: ① 문서를 처음 볼 때 이미 있던 글(doc_open) ② 키 입력 없이 들어온 글 변화
    붙여넣기 글 변화(doc_paste_at 과 같은 시각·자리)는 여기서 빼고 pasted_from_ai / pasted_from_other 가 다룬다."""
    pastes = {(d["ts"], d.get("where")) for d in events if d.get("type") == "doc_paste_at"}
    붙인 = {id(d) for _, _, ds in paste_groups(events, context) for d in ds}      # 여러 문단 붙여넣기의 나머지 문단까지 (10/14)
    keys = sorted(([e["ts"], int(e.get("count", 0))] for e in events if e.get("type") == "keys" and e.get("app", "").upper() in OFFICE_EXE.values()),
                  key=lambda k: k[0])
    typed, noproc = [], []
    # 같은 파일을 여러 번 받았으면 하나만 — 받은 곳이 확실한 것(AI 사이트 · 사이트 이름 있음) → 그중 먼저 받은 것 (10/17 · 글이 같아
    # 어느 것에 이어질지는 순서로 정해지는데, 받은 곳을 모르는 앞 기록에 이어져 "Chrome" 으로만 보였다)
    받기 = {}
    for c in context:
        h = (c.get("meta") or {}).get("hash")
        if c.get("kind") == "download" and h:
            m = c["meta"]
            k = (m.get("category") != "ai", not m.get("domain"), c.get("ts", ""))
            if h not in 받기 or k < 받기[h][0]:
                받기[h] = (k, id(c))
    고른_받기 = {i for _, i in 받기.values()}
    for c in sorted(context, key=lambda c: c.get("ts", "")):
        meta = c.get("meta", {})
        if c.get("kind") == "doc_open" and c.get("text", "").strip():
            noproc.append({"text": c["text"], "how": "open", "ts": c["ts"], "file": meta.get("file", "")})
        elif c.get("kind") == "download" and meta.get("hash") in 받기 and id(c) not in 고른_받기:
            continue
        elif c.get("kind") == "download" and c.get("text", "").strip():
            # 기록하는 동안 AI 앱 · 브라우저에서 받은 결과물 파일의 글 (collector/downloads.py · 10/15) — 결과물 문장이 여기서 왔으면 빨강
            noproc.append({"text": c["text"], "how": "download", "ts": c["ts"], "file": meta.get("name", ""),
                           "app": meta.get("app", ""), "domain": meta.get("domain", ""), "category": meta.get("category", "")})
        elif c.get("kind") == "diff" and c.get("text", "").strip() and (c["ts"], meta.get("where")) not in pastes and id(c) not in 붙인:
            n, got = len(c["text"].strip()), 0
            need = max(2, int(n * TYPED_KEYS))
            for k in keys:
                if k[1] and KEYS_WINDOW[0] <= _secs(c["ts"], k[0]) <= KEYS_WINDOW[1]:
                    take = min(k[1], 2 * n - got)          # 진짜 타이핑이면 1자에 2번 정도까지 쓴 것으로 깎는다
                    k[1] -= take; got += take
                    if got >= 2 * n:
                        break
            (typed.append(c["text"]) if got >= need else
             noproc.append({"text": c["text"], "how": "nokeys", "ts": c["ts"], "file": meta.get("file", "")}))
    return {"typed": typed, "noproc": noproc}


PASTE_TICK = 1          # 초 — 붙여넣기 직후 Word 를 읽은 그 한 번(같은 순간)에 생긴 글 변화는 모두 그 붙여넣기 (10/14)
AI_APPS = {"claude", "chatgpt", "claude.exe", "chatgpt.exe"}   # 여기에 붙여넣은 건 AI 에게 한 질문 — 문서에 들어간 글이 아님


def _문단번호(where):
    m = re.search(r"\d+", where or "")
    return int(m.group()) if m else 10 ** 6


def _붙인_글(at, diffs, n):
    """붙여넣은 자리(doc_paste_at)와 같은 순간 · 같은 문서에 새로 생긴 글 변화들 (문단 순서).
    여러 문단을 한 번에 붙여넣으면 문단마다 diff 가 하나씩 생기는데 전엔 커서가 놓인 문단 하나만 붙여넣은 글로 봤다
    (10/14 맥 시험: 구글 AI 답 14문단을 붙여넣었는데 13문단이 '쓴 과정 기록 없음' · 일부는 비슷한 Claude 답으로 감).
    커서 문단에서 가까운 것부터 붙여넣은 글자 수(n · 표 칸 · 줄바꿈 여유 1.3배)를 넘지 않을 만큼만 — 그 사이 친 글이 섞이지 않게"""
    f, p0 = at.get("file"), _문단번호(at.get("where"))
    같은때 = [d for d in diffs if d.get("meta", {}).get("file", f) == f and abs(_secs(at["ts"], d["ts"])) <= PASTE_TICK]
    같은때.sort(key=lambda d: (abs(_문단번호(d["meta"].get("where")) - p0), d["meta"].get("where") != at.get("where")))
    한도 = n * 1.3 + 30 if n else None
    out, 합 = [], 0
    for d in 같은때:
        if out and 한도 is not None and 합 + len(d["text"]) > 한도:
            continue
        out.append(d)
        합 += len(d["text"])
    return sorted(out, key=lambda d: _문단번호(d["meta"].get("where")))


def paste_groups(events, context):
    """붙여넣기마다 그때 문서에 들어온 글 변화 → [(paste 이벤트, doc_paste_at, [diff 맥락])]"""
    diffs = [c for c in context if c.get("kind") == "diff" and c.get("text")]
    evs = sorted(events, key=lambda e: e.get("ts", ""))
    out = []
    for i, e in enumerate(evs):
        if e.get("type") == "paste":
            at = _paste_spot(evs, i)
            if at:
                out.append((e, at, _붙인_글(at, diffs, int(e.get("len") or 0))))
    return out


def _paste_spot(evs, i):
    """evs[i](paste) 의 붙여넣은 자리 = 그 뒤 10초 안의 첫 doc_paste_at. 단 다음 붙여넣기보다 앞이어야 한다
    (10/7: 빨리 연달아 붙여넣으면 뒤 붙여넣기의 자리를 앞 것이 가져가던 위험)."""
    for d in evs[i + 1:i + 40]:
        if d.get("type") == "paste":
            return None
        if d.get("type") == "doc_paste_at":
            return d if _secs(evs[i]["ts"], d["ts"]) <= 10 else None
    return None


def _더하기(ts: str, sec: int) -> str:
    from datetime import datetime, timedelta
    try:
        return (datetime.fromisoformat(ts) + timedelta(seconds=sec)).isoformat()
    except ValueError:
        return ts


@lru_cache(maxsize=65536)
def _시각(ts: str):
    from datetime import datetime
    return datetime.fromisoformat(ts)


def _secs(a: str, b: str) -> float:
    return (_시각(b) - _시각(a)).total_seconds()


def link_document(paragraphs, answers, pasted=None, others=None, proc=None):
    """paragraphs: [문단 텍스트] · answers: [{"id","text",...}] · pasted: pasted_from_ai() 결과 (없으면 None = 과정 기록 없음)
    others: pasted_from_other() 결과 (AI 아닌 곳에서 붙여넣은 글)
    → [[{"text", "label", "answer", "sents", "ai_text", "paste", ...} 문장마다] 문단마다]
    paste = 이 문장을 붙여넣은 기록 (없으면 None) — 화면에 "어디서 · 언제 복사 → 언제 붙여넣음" 으로 보여 준다.

    proc: process_evidence() 결과 — 타이핑한 글 / 과정 없이 나타난 글
    순서: AI 답 붙여넣기(기록 있음) > 다른 곳 붙여넣기(기록 있음) > 타이핑 기록 있음(그대로 둠)
          > 쓴 과정 없이 나타남(noproc) > AI 답 보고 씀·옮겨 침(글자만) > 출처 기록 없음.
    다른 곳 붙여넣기 · 과정 없는 글도 같은 글자 비교 규칙으로 잇는다 (고쳐도 이어짐 기준을 넘으면)."""
    cands = candidates(answers)
    # 답이 언제부터 있었나 = 그 답의 **질문 시각** (asked). 답 시각(ts)은 기록한 때라 실제보다 늦다 — 확장은 답이 다 그려지고
    # 멈춘 뒤에 보낸다 (10/14: ChatGPT 웹 답 기록 15:20:21 · 학생이 복사 15:20:04). 질문을 모르면 답 시각에 2분 여유
    답시각 = {a["id"]: a.get("asked") or (a.get("ts") and _더하기(a["ts"], -120)) for a in answers}

    def 앞서(answer_id, p):
        """이 답이 붙여넣은 글의 출처일 수 있나 — 복사(붙여넣기)보다 늦게 물어본 답은 출처가 될 수 없다 (10/14 실제 시험:
        14:17 에 웹에서 붙여넣은 글이 14:28 에 Claude 가 보고서를 요약한 답과 글자가 겹쳐 Claude 에서 온 것으로 잡힘).
        시각을 모르면(옛 기록 · 시험) 막지 않는다"""
        t, c = 답시각.get(answer_id), (p or {}).get("copied_at") or (p or {}).get("pasted_at")
        return not t or not c or _secs(t, c) >= -5
    wcands = candidates([{"id": k, "text": p["text"]} for k, p in enumerate(others or [])])
    tcands = candidates([{"id": k, "text": t} for k, t in enumerate((proc or {}).get("typed", []))])
    ncands = candidates([{"id": k, "text": x["text"]} for k, x in enumerate((proc or {}).get("noproc", []))])
    # 붙여넣은 글이 어느 AI 답의 몇 번째 문장인지 — 붙여넣은 글도 같은 규칙으로 잇는다
    pasted_at, 붙인답 = {}, {}                 # 붙인답: 붙여넣기(id) → 그 글이 이어진 AI 답 id 들
    답_id = {c["answer"] for c in cands}
    for p in pasted or []:
        된다 = {i for i in 답_id if 앞서(i, p)}               # 붙여넣기보다 늦게 물어본 답은 빼고 — 답마다 한 번만 셈
        이른 = lambda c, 된다=된다: c["answer"] in 된다     # noqa: E731
        for s in split_sentences(p["text"]):
            hit = link_sentence(s, cands, keep=이른)
            if hit["label"] != "none":
                붙인답.setdefault(id(p), set()).add(hit["answer"])
                for i in hit["sents"]:
                    pasted_at.setdefault((hit["answer"], i), p)
    # 문장을 담은 붙여넣기 찾기용 (AI 답 붙여넣기 · 다른 곳 붙여넣기 모두) — 붙여넣은 시각 순
    붙여넣기들 = sorted([(p, True) for p in pasted or []] + [(p, False) for p in others or []], key=lambda x: x[0].get("pasted_at") or "")
    붙후보 = candidates([{"id": k, "text": p["text"]} for k, (p, _) in enumerate(붙여넣기들)])   # 한 색인 · answer = 붙여넣기 번호

    def 처음_붙인(s, 그대로):
        """이 문장을 담은 가장 이른 붙여넣기 (p, AI 답 붙여넣기인가) — 문장이 문서에 처음 들어온 때.
        그대로=True 면 거의 그대로(90% 이상) 들어 있을 때만 (주제만 비슷한 글 · 날짜처럼 글자 조각만 겹치는 글로 바꾸지 않게)
        (10/14) 붙여넣기마다 link_sentence 를 따로 부르던 것을 한 번에 — 붙여넣기마다의 결론(그대로 · 고침)은 같다"""
        라벨 = _라벨들(s, 붙후보)
        for k, (p, ai) in enumerate(붙여넣기들):
            if 라벨.get(k) == "exact" or (라벨.get(k) == "edited" and not 그대로):
                return p, ai
        return None, None
    out = []
    for para in paragraphs:
        row = []
        for s in split_sentences(para):
            r = {"text": s, **link_sentence(s, cands), "paste": None}
            r["full"] = r["label"] == "exact" and norm(s) == norm(r["ai_text"])     # 100% 같음 → "일치" · 90~99% → "유사"
            if r["label"] != "none" and pasted is not None:
                r["paste"] = next((pasted_at[(r["answer"], i)] for i in r["sents"] if (r["answer"], i) in pasted_at), None)
                if r["label"] == "edited" and r["paste"] is None:
                    r["label"] = "viewed"
            # 이 문장이 문서에 처음 들어온 붙여넣기가 지금 이은 것보다 이르면 그게 출처 (10/14 실제 시험: 14:17 웹에서 붙여넣은 글이
            # 14:28 Claude 가 보고서를 요약한 답 · 그 답을 붙여넣은 기록과 글자가 겹쳐 Claude 에서 온 것으로 잡힘)
            if 붙여넣기들 and (r["label"] != "none" or pasted is not None):
                e, e_ai = 처음_붙인(s, True)        # 거의 그대로일 때만 — "2026년 10월 14일" 이 표의 "2026년 7월 24일" 에 걸리던 것
                기준 = (r["paste"] or {}).get("pasted_at") or (답시각.get(r["answer"]) if r["label"] != "none" else None)
                if e is not None and (r["label"] == "none" or (기준 and _secs(e.get("pasted_at") or 기준, 기준) > 0)):
                    if e_ai and r["label"] != "none" and r["answer"] in 붙인답.get(id(e), ()):
                        r["paste"] = e                                        # 같은 답 — 더 이른 붙여넣기로
                    elif e_ai and 붙인답.get(id(e)):
                        pass                                                  # 다른 AI 답에서 온 붙여넣기 — 드묾 · 그대로 둠
                    elif e_ai:                                                # AI 탭에서 복사했는데 그 대화 기록이 없음 (웹 화면을 못 읽음)
                        r.update(label="web", full=False, answer=None, sents=None, ai_text=e["text"],
                                 paste={**e, "source": e.get("domain") or "AI", "category": "ai"})
                    elif r["label"] != "none":                               # 다른 곳에서 먼저 붙여넣은 글
                        r.update(label="web", full=False, answer=None, sents=None, ai_text=e["text"], paste=e)
            if wcands and r["paste"] is None:
                w = link_sentence(s, wcands)
                # AI 답과 거의 그대로(exact) 이어진 문장은 다른 곳 붙여넣기가 '고쳐 씀' 정도로만 닮았을 땐 안 바꾼다
                # (10/14: 표 칸 "M5 Pro / M5 Max" 가 긴 구글 답 문장과 글자 조각만 겹쳐 '다른 곳' 으로 넘어감)
                if w["label"] != "none" and (r["label"] != "exact" or w["label"] == "exact"):
                    r.update(label="web", full=False, answer=None, sents=None, ai_text=w["ai_text"], paste=others[w["answer"]])
            # 붙여넣기 기록이 없는데 타이핑 기록도 없이 문서에 나타난 글 → 쓴 과정 기록 없음 (10/7)
            if ncands and r["label"] in ("none", "viewed") and link_sentence(s, tcands)["label"] == "none":
                x = link_sentence(s, ncands)
                if x["label"] != "none":
                    r.update(label="noproc", full=False, answer=None, sents=None, ai_text=x["ai_text"], proc=proc["noproc"][x["answer"]])
            row.append(r)
        out.append(row)
    _link_short_lines(out, cands)
    return out


def _link_short_lines(out, cands):
    """8자 미만 짧은 줄("나이: 24세" · "예를 들어") — 유사도 비교는 여전히 안 한다. 다만 바로 앞·뒤 문장이 붙여넣기(AI 답 · 다른 곳)에
    이어졌고 **그 붙여넣은 원문 안에 이 줄이 그대로 있으면** 같은 붙여넣기로 잇는다 (이슈 #26-3).
    붙여넣은 글 안에서만 찾으니 우연히 겹칠 위험이 없다 — 직접 친 짧은 제목("어린 시절")은 붙여넣은 글에 없으니 그대로 둔다."""
    flat = [r for row in out for r in row]
    조각 = {}                                        # 과정 없이 나타난 글(받은 파일 등) → 그 글의 줄 · 줄 안 문장 (norm)
    for k, r in enumerate(flat):
        n = norm(r["text"])
        if r["label"] != "none" or not n or len(n) >= MIN_CHARS:
            continue
        for nb in (_near(flat, k, -1), _near(flat, k, 1)):
            # 받은 파일 · 열었을 때 있던 글(noproc) 사이의 제목 · 번호 · 표 머리글 — 그 글 안에 이 줄이 한 줄 · 한 문장으로 있으면 같은 글 (10/15
            # 실제 시험: Claude 가 준 PDF 를 그대로 냈는데 "1." "서론" "유형" 같은 조각만 출처 기록 없음 13개로 남음)
            pr = nb.get("proc") if nb and nb["label"] == "noproc" else None
            if pr:
                t = pr.get("text", "")
                if t not in 조각:
                    조각[t] = {norm(x) for line in re.split(r"[\n\t]", t) for x in (line, *split_sentences(line))}
                if n in 조각[t]:
                    r.update(label="noproc", full=False, answer=None, sents=None, ai_text=r["text"], proc=pr)
                    break
                continue
            p = nb.get("paste") if nb else None
            # 붙여넣은 원문의 **한 줄 전체**와 같을 때만 — 글 안 어딘가에 들어 있기만 하면(부분 문자열) 직접 친 소제목
            # "현재" 가 붙여넣은 "현재 하린은 23살." 에 걸렸다 (10/7 첫 연결 보고서에서 찾음)
            if not p or not any(norm(line) == n for line in re.split(r"[\n\t]", p.get("text", ""))):     # 표 칸(탭)도 한 줄 (10/14)
                continue
            if nb["label"] == "web":
                r.update(label="web", full=False, answer=None, sents=None, ai_text=r["text"], paste=p)
            else:                                   # AI 답 붙여넣기 — 원문에서 이 줄이 든 문장을 칠한다
                i = next((c["sents"][0] for c in cands
                          if c["answer"] == nb["answer"] and len(c["sents"]) == 1 and n in norm(c["text"])), None)
                r.update(label="exact", full=True, answer=nb["answer"], sents=(i,) if i is not None else nb["sents"],
                         ai_text=r["text"], paste=p)
            break


def _near(flat, k, step):
    """k 에서 step 쪽으로 가장 가까운 짧지 않은 문장 — 짧은 줄이 연달아 있어도 붙여넣은 덩어리의 양 끝 문장을 본다"""
    j = k + step
    while 0 <= j < len(flat):
        if len(norm(flat[j]["text"])) >= MIN_CHARS:
            return flat[j]
        j += step
    return None
