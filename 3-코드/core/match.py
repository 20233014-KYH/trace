"""
match.py — 결과물 문장 ↔ AI 답 연결 "제안" (기록기·서버 공용 · chain.py 와 같은 원칙: 여기 말고 다른 데서 짜지 않는다)

결과물(보고서·코드)을 문장으로 나누고, 문장마다 저장해 둔 AI 답 원문과 비교해 넷 중 하나를 붙인다.

  exact   AI 답 그대로     — 글자 순서까지 거의 같음 (붙여넣기 기록이 있든 없든 · 화면에 기록 유무를 따로 보여 줌)
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
import difflib
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


def candidates(answers):
    """AI 답들 → 비교 후보: 문장 하나씩 + 이웃한 두 문장을 합친 것 (두 문장을 합쳐 다시 쓴 경우용)
    answers: [{"id", "text", ...}] → [{"answer": id, "sents": (i,) | (i, i+1), "text"}]"""
    out = []
    for a in answers:
        ss = split_sentences(a["text"])
        for i, s in enumerate(ss):
            out.append({"answer": a["id"], "sents": (i,), "text": s})
            if i + 1 < len(ss):
                out.append({"answer": a["id"], "sents": (i, i + 1), "text": s + " " + ss[i + 1]})
    return out


def link_sentence(sentence: str, cands):
    """한 문장 → {"label", "answer", "sents", "ai_text", "_ratio", "_cover"}  (밑줄 칸은 시험용 · 화면에 안 냄)"""
    best = {"label": "none", "answer": None, "sents": None, "ai_text": None, "_ratio": 0.0, "_cover": 0.0}
    if len(norm(sentence)) < MIN_CHARS:
        return best
    one = two = None                    # "고침" 후보: 가장 잘 맞는 한 문장 · 가장 잘 맞는 이웃 두 문장
    for c in cands:
        ratio, cover = compare(sentence, c["text"])
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


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8", "surrogatepass")).hexdigest()   # 수집기 sha256_text 와 같게


def pasted_from_ai(events, context):
    """과정 기록 → AI 답에서 복사해 붙여넣은 글 [{"text", "copied_at", "pasted_at", "file", "where"}]

    고리는 해시 셋이 **똑같은지**만 본다 (창 이름·시간으로 추측하지 않음):
      확장이 AI 사이트에서 받은 복사 발췌(context kind=ai_answer_excerpt) 의 sha256
        = 수집기 copy 이벤트 해시  = 수집기 paste 이벤트 해시
    붙여넣은 문서·자리는 paste 직후(10초 안) 첫 doc_paste_at 에서 가져온다 (없으면 빈칸)."""
    excerpts = {}
    for c in context:
        if c.get("kind") == "ai_answer_excerpt" and c.get("text"):
            excerpts.setdefault(_sha256(c["text"]), c)
    copies = {e["hash"]: e for e in events if e.get("type") == "copy" and e.get("hash") in excerpts}
    out = []
    evs = sorted(events, key=lambda e: e.get("ts", ""))
    for i, e in enumerate(evs):
        if e.get("type") != "paste" or e.get("hash") not in copies:
            continue
        at = _paste_spot(evs, i) or {}
        out.append({"text": excerpts[e["hash"]]["text"], "copied_at": copies[e["hash"]]["ts"], "pasted_at": e["ts"],
                    "file": at.get("file", ""), "where": at.get("where", ""), "domain": excerpts[e["hash"]].get("meta", {}).get("domain", "")})
    return out


BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "whale.exe", "google chrome", "microsoft edge", "firefox", "safari"}


def pasted_from_other(events, context):
    """과정 기록 → AI 답이 **아닌** 곳에서 복사해 문서에 붙여넣은 글 [{"text", "source", "category", "copied_at", "pasted_at", "file", "where"}]

    · AI 답 붙여넣기(pasted_from_ai 의 해시 고리)는 뺀다.
    · 출처: 복사한 순간의 앱이 브라우저면 그때 보던 탭 도메인(확장 tab 이벤트), 아니면 앱 이름. 복사 기록이 없으면(기록 시작 전 복사) "".
    · **자기 글 옮기기는 뺀다**: 복사한 곳 = 붙여넣은 곳(같은 앱 · 브라우저면 같은 도메인) — Word 안에서 잘라 붙이기 등.
    · 글자: 원문이 따로 없어서 붙여넣은 순간 문서에 새로 들어온 글(context kind=diff · doc_paste_at 과 같은 시각·자리)을 쓴다.
      capture.office 가 꺼져 있으면 글자가 없어서 문장과 잇지 못한다 (붙여넣기 사실은 과정 기록 화면에 그대로 남음)."""
    ai = {_sha256(c["text"]) for c in context if c.get("kind") == "ai_answer_excerpt" and c.get("text")}
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
            text = " ".join(d["text"] for d in diffs if d["ts"] == at["ts"] and d.get("meta", {}).get("where") == at.get("where"))
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
    keys = sorted(([e["ts"], int(e.get("count", 0))] for e in events if e.get("type") == "keys" and e.get("app", "").upper() in OFFICE_EXE.values()),
                  key=lambda k: k[0])
    typed, noproc = [], []
    for c in sorted(context, key=lambda c: c.get("ts", "")):
        meta = c.get("meta", {})
        if c.get("kind") == "doc_open" and c.get("text", "").strip():
            noproc.append({"text": c["text"], "how": "open", "ts": c["ts"], "file": meta.get("file", "")})
        elif c.get("kind") == "diff" and c.get("text", "").strip() and (c["ts"], meta.get("where")) not in pastes:
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


def _paste_spot(evs, i):
    """evs[i](paste) 의 붙여넣은 자리 = 그 뒤 10초 안의 첫 doc_paste_at. 단 다음 붙여넣기보다 앞이어야 한다
    (10/7: 빨리 연달아 붙여넣으면 뒤 붙여넣기의 자리를 앞 것이 가져가던 위험)."""
    for d in evs[i + 1:i + 40]:
        if d.get("type") == "paste":
            return None
        if d.get("type") == "doc_paste_at":
            return d if _secs(evs[i]["ts"], d["ts"]) <= 10 else None
    return None


def _secs(a: str, b: str) -> float:
    from datetime import datetime
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()


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
    wcands = candidates([{"id": k, "text": p["text"]} for k, p in enumerate(others or [])])
    tcands = candidates([{"id": k, "text": t} for k, t in enumerate((proc or {}).get("typed", []))])
    ncands = candidates([{"id": k, "text": x["text"]} for k, x in enumerate((proc or {}).get("noproc", []))])
    # 붙여넣은 글이 어느 AI 답의 몇 번째 문장인지 — 붙여넣은 글도 같은 규칙으로 잇는다
    pasted_at = {}
    for p in pasted or []:
        for s in split_sentences(p["text"]):
            hit = link_sentence(s, cands)
            if hit["label"] != "none":
                for i in hit["sents"]:
                    pasted_at.setdefault((hit["answer"], i), p)
    out = []
    for para in paragraphs:
        row = []
        for s in split_sentences(para):
            r = {"text": s, **link_sentence(s, cands), "paste": None}
            if r["label"] != "none" and pasted is not None:
                r["paste"] = next((pasted_at[(r["answer"], i)] for i in r["sents"] if (r["answer"], i) in pasted_at), None)
                if r["label"] == "edited" and r["paste"] is None:
                    r["label"] = "viewed"
            if wcands and r["paste"] is None:
                w = link_sentence(s, wcands)
                if w["label"] != "none":
                    r.update(label="web", answer=None, sents=None, ai_text=w["ai_text"], paste=others[w["answer"]])
            # 붙여넣기 기록이 없는데 타이핑 기록도 없이 문서에 나타난 글 → 쓴 과정 기록 없음 (10/7)
            if ncands and r["label"] in ("none", "viewed") and link_sentence(s, tcands)["label"] == "none":
                x = link_sentence(s, ncands)
                if x["label"] != "none":
                    r.update(label="noproc", answer=None, sents=None, ai_text=x["ai_text"], proc=proc["noproc"][x["answer"]])
            row.append(r)
        out.append(row)
    return out
