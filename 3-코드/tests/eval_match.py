"""
eval_match.py — 출처 잇기가 얼마나 맞나 (정확도 평가 · 11/19 박상진)

  python 3-코드/tests/eval_match.py                 # 콘솔에 표
  python 3-코드/tests/eval_match.py --md 결과.md     # 같은 표를 Markdown 파일로도

앱에는 점수 · 퍼센트를 보여 주지 않는다 (원칙 1). 이 숫자는 **우리가 앱을 재는 것** — 발표 · 문서용.

재료 = tests/fixtures/match_* 의 녹화 시험 (실제 AI 답 · 실제 Word · 실제 기록기 이벤트) + 문장마다 정답(report_truth.json).
앱과 똑같은 길로 잰다: test_source.py 의 학생_PC() 로 PC 기록을 만들고, 출처 보기 화면이 부르는 /local/source 를 그대로 부른다.

보는 것
  ① 표시가 정답과 같은 문장 수 (정답에 label_any 가 있으면 그중 하나면 맞음 · 유사 = 일치로 셈 — 화면에서 한 색)
  ② 잘못 짚음 — 정답은 "출처 기록 없음"(직접 씀)인데 AI 답 · 다른 곳 · 쓴 과정 없음으로 표시   ← 학생에게 가장 위험한 실수
  ③ 놓침 — 정답은 AI 답에서 옴(일치 · 고침 · 참고함)인데 "출처 기록 없음"으로 표시
  ④ 이은 AI 답이 맞나 — 정답에 어느 답(src)인지 있고 앱도 AI 답에 이었을 때, 같은 답인가
  ⑤ 정답 × 표시 표 (어디서 틀리는지)
"""
import argparse
import io
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "app"))
import test_source as T                          # noqa: E402  학생 PC 만들기 · 같은 자료 · 같은 앱

FX = T.FX
CASES = T.CASES
AI = {"exact", "edited", "viewed"}               # AI 답에서 온 것 (출처 보기의 빨강 · 파랑 묶음)
OTHER = {"web", "noproc"}                        # AI 답 말고 다른 곳 · 쓴 과정 기록 없음
NAME = {"exact": "일치·유사", "edited": "고침", "viewed": "참고함", "web": "다른 곳", "noproc": "과정 없음", "none": "기록 없음"}
ORDER = ["exact", "edited", "viewed", "web", "noproc", "none"]


def 표시(kind):
    return "exact" if kind == "similar" else kind


def 답_번호(q):
    """출처 보기 질문 한 턴 → 이어진 AI 답의 시험 자료 순서(k). 학생_PC() 가 답 이벤트를 evt_9{k:02d}a 로 만든다"""
    for r in (q.get("refs") or {}).values():
        e = str(r.get("event_id", ""))
        if e.startswith("evt_9") and e.endswith("a"):
            return int(e[5:-1])
    return None


def 재기():
    data = tempfile.mkdtemp(prefix="trace-eval-")
    rows = []                                    # 문장마다 {case, text, truth, truth_any, got, src, got_src}
    try:
        old = sys.stdout
        sys.stdout = io.StringIO()               # 학생_PC · 앱이 찍는 것 숨김
        try:
            T.학생_PC(data)
            T.ST.설정.update(server="http://127.0.0.1:9/api", data_dir=data)
        finally:
            sys.stdout = old
        c = T.ST.app.test_client()
        H, HOST = {"X-Trace-Local": "1"}, {"base_url": f"http://127.0.0.1:{T.ST.PORT}"}
        for case in CASES:
            raw = open(os.path.join(FX, case, "report.docx"), "rb").read()
            r = c.post("/local/source", data={"work_id": f"W-{case}", "file": (io.BytesIO(raw), "report.docx")}, headers=H,
                       content_type="multipart/form-data", **HOST)
            if r.status_code != 200:
                raise SystemExit(f"{case}: 출처 보기 응답 {r.status_code} {r.json}")
            d = r.json
            truth = json.load(open(os.path.join(FX, case, "report_truth.json"), encoding="utf-8"))
            flat = [t for p in truth["paragraphs"] for t in p]
            답id = [a.get("id") for a in T.L(case, "ai_answers")]
            if len(flat) != len(d["sentences"]):
                print(f"  ! {case}: 정답 {len(flat)}문장 · 앱 {len(d['sentences'])}문장 — 앞에서부터 맞춰 봄")
            for t, x in zip(flat, d["sentences"]):
                k = 답_번호(d["questions"][x["q"]]) if x.get("q") is not None else None
                rows.append({"case": case, "text": x["text"], "truth": t["label"], "any": t.get("label_any") or [t["label"]],
                             "got": 표시(x["kind"]), "src": t.get("src"),
                             "got_src": 답id[k] if k is not None and k < len(답id) else None, "how": t.get("how", "")})
    finally:
        shutil.rmtree(data, ignore_errors=True)
    return rows


TEXT_CASES = ["match", "match3"]                 # 기록 없이 글자 비교만 하는 시험 (match3 = 기준을 정하기 전에 쓴 문장 · 함정 포함)


def 글자만_재기():
    """붙여넣기 · 타이핑 기록이 없을 때 — 글자 비교만으로 AI 답에 이을 수 있나. 앱은 이때 '참고함 · 일치' 로만 제안하고
    학생이 연결 확인에서 고른다. 정답 묶음: AI 답에서 옴(exact · edited · viewed) / 직접 씀(none)"""
    from core import match as M
    rows = []
    for case in TEXT_CASES:
        truth = json.load(open(os.path.join(FX, case, "report_truth.json"), encoding="utf-8"))
        answers = [{"id": a["id"], "text": a["text"]} for a in T.L(case, "ai_answers")]
        paras = [" ".join(t["text"] for t in p) for p in truth["paragraphs"]]
        got = [s for p in M.link_document(paras, answers) for s in p]
        flat = [t for p in truth["paragraphs"] for t in p]
        if len(got) != len(flat):
            print(f"  ! {case}: 정답 {len(flat)}문장 · 앱 {len(got)}문장 — 앞에서부터 맞춰 봄")
        for t, x in zip(flat, got):
            a = x.get("answer")
            src = answers[a]["id"] if isinstance(a, int) and a < len(answers) else (a if isinstance(a, str) else None)
            rows.append({"case": case, "text": t["text"], "truth": "ai" if t["label"] in AI else "none",
                         "got": "ai" if 표시(x["label"]) in AI else "none", "src": t.get("src"), "got_src": src,
                         "how": t.get("how", ""), "label": x["label"]})
    return rows


def 글자만_보고서(rows):
    직접 = [r for r in rows if r["truth"] == "none"]
    AI답 = [r for r in rows if r["truth"] == "ai"]
    잘못 = [r for r in 직접 if r["got"] == "ai"]
    놓침 = [r for r in AI답 if r["got"] == "none"]
    잇기 = [r for r in AI답 if r["got"] == "ai" and r["src"]]
    L = [f"\n## 기록 없이 글자만 비교할 때 — 시험 {len(TEXT_CASES)}개 · {len(rows)}문장\n",
         "> 붙여넣기 · 타이핑 기록이 없는 경우(옛 기록 · 휴대폰으로 보고 옮겨 침 등). 앱은 '참고함'으로 **제안만** 하고 학생이 연결 확인에서 고른다.",
         "> `match3` 는 기준을 정하기 **전에** 쓴 문장으로, 같은 주제를 직접 쓴 문장(잘못 짚는지)과 많이 고친 문장(놓치는지)을 일부러 넣었다.\n",
         "| 무엇 | 결과 |\n|---|---|",
         f"| 잘못 짚음 — 직접 쓴 문장을 AI 답에 이음 | **{비율(len(잘못), len(직접))}** |",
         f"| 놓침 — AI 답에서 온 문장을 못 이음 | **{비율(len(놓침), len(AI답))}** |",
         f"| 이은 AI 답이 맞음 | **{비율(sum(r['got_src'] == r['src'] for r in 잇기), len(잇기))}** |\n",
         "| 시험 | 문장 | 직접 씀 → 잘못 짚음 | AI 답 → 놓침 |\n|---|---|---|---|"]
    for case in TEXT_CASES:
        rs = [r for r in rows if r["case"] == case]
        L.append(f"| {case} | {len(rs)} | {sum(1 for r in rs if r['truth'] == 'none' and r['got'] == 'ai')}"
                 f"/{sum(1 for r in rs if r['truth'] == 'none')} | {sum(1 for r in rs if r['truth'] == 'ai' and r['got'] == 'none')}"
                 f"/{sum(1 for r in rs if r['truth'] == 'ai')} |")
    틀림 = 잘못 + 놓침
    if 틀림:
        L.append("\n| 시험 | 정답 | 앱 | 어떻게 썼나 (정답 파일) | 문장 앞부분 |\n|---|---|---|---|---|")
        for r in 틀림:
            L.append(f"| {r['case']} | {'AI 답' if r['truth'] == 'ai' else '직접 씀'} | {NAME.get(표시(r['label']), r['label'])} | "
                     f"{r['how']} | {r['text'][:40].replace('|', '/')}… |")
    return "\n".join(L) + "\n"


def 비율(a, b):
    return f"{a}/{b}" + (f" ({a / b:.0%})" if b else "")


def 보고서(rows):
    n = len(rows)
    맞음 = [r for r in rows if r["got"] in r["any"]]
    직접 = [r for r in rows if r["truth"] == "none"]
    잘못 = [r for r in 직접 if r["got"] != "none"]
    AI답 = [r for r in rows if r["truth"] in AI]
    놓침 = [r for r in AI답 if r["got"] == "none"]
    잇기 = [r for r in rows if r["src"] and r["got"] in AI and r["got_src"]]
    같은답 = [r for r in 잇기 if r["got_src"] == r["src"]]
    L = []
    L.append(f"# 출처 잇기 정확도 — 녹화 시험 {len(CASES)}개 · {n}문장\n")
    L.append("> 앱에는 점수 · 퍼센트를 보여 주지 않는다. 이 표는 **우리가 앱을 잰 것**이다.")
    L.append("> 재료: `tests/fixtures/match_*` (팀원이 실제 AI · Word 로 녹화한 과제) + 문장마다 정답 `report_truth.json`.")
    L.append("> 문장 수가 적고 팀이 만든 시험이라 **경향만** 본다 — 실제 학생 수치는 사용 테스트(연결 확인 '아니다' 비율)로.")
    L.append("> ⚠️ 이 녹화 시험들은 출처 잇기 규칙을 고칠 때마다 맞춰 본 자료다 → 여기서 100% 는 '이 경우들은 된다'는 확인이지 실제 정확도가 아니다."
             " 규칙을 정하기 전에 만든 함정 시험은 아래 '글자만 비교' 의 match3.\n")
    L.append("| 무엇 | 결과 |\n|---|---|")
    L.append(f"| ① 표시가 정답과 같음 | **{비율(len(맞음), n)}** |")
    L.append(f"| ② 잘못 짚음 — 직접 쓴 문장을 AI 답 · 다른 곳으로 | **{비율(len(잘못), len(직접))}** |")
    L.append(f"| ③ 놓침 — AI 답에서 온 문장을 '출처 기록 없음'으로 | **{비율(len(놓침), len(AI답))}** |")
    L.append(f"| ④ 이은 AI 답이 맞음 (어느 답인지 정답이 있는 문장만) | **{비율(len(같은답), len(잇기))}** |\n")

    L.append("## 시험마다\n\n| 시험 | 문장 | 정답과 같음 | 잘못 짚음 | 놓침 |\n|---|---|---|---|---|")
    for case in CASES:
        rs = [r for r in rows if r["case"] == case]
        L.append(f"| {case} | {len(rs)} | {sum(r['got'] in r['any'] for r in rs)} | "
                 f"{sum(1 for r in rs if r['truth'] == 'none' and r['got'] != 'none')} | "
                 f"{sum(1 for r in rs if r['truth'] in AI and r['got'] == 'none')} |")

    L.append("\n## 정답 × 앱 표시 (문장 수)\n")
    표 = defaultdict(Counter)
    for r in rows:
        표[r["truth"]][r["got"]] += 1
    열 = [k for k in ORDER if any(표[t][k] for t in 표)]
    L.append("| 정답 \\ 앱 | " + " | ".join(NAME[k] for k in 열) + " |")
    L.append("|---|" + "---|" * len(열))
    for t in [k for k in ORDER if k in 표]:
        L.append(f"| {NAME[t]} | " + " | ".join(str(표[t][k] or "·") for k in 열) + " |")

    틀림 = [r for r in rows if r["got"] not in r["any"]]
    if 틀림:
        L.append("\n## 정답과 다른 문장\n\n| 시험 | 정답 | 앱 | 어떻게 썼나 (정답 파일) | 문장 앞부분 |\n|---|---|---|---|---|")
        for r in 틀림:
            L.append(f"| {r['case']} | {NAME.get(r['truth'], r['truth'])} | {NAME.get(r['got'], r['got'])} | {r['how']} | "
                     f"{r['text'][:40].replace('|', '/')}… |")
    다른답 = [r for r in 잇기 if r["got_src"] != r["src"]]
    if 다른답:
        L.append("\n## 다른 AI 답에 이은 문장\n\n| 시험 | 정답 답 | 앱이 이은 답 | 문장 앞부분 |\n|---|---|---|---|")
        for r in 다른답:
            L.append(f"| {r['case']} | {r['src']} | {r['got_src']} | {r['text'][:40].replace('|', '/')}… |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="출처 잇기 정확도 평가 (녹화 시험 · 정답 파일)")
    ap.add_argument("--md", help="결과를 Markdown 파일로도 저장")
    a = ap.parse_args()
    md = 보고서(재기()) + 글자만_보고서(글자만_재기())
    print(md)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"  → {a.md}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
