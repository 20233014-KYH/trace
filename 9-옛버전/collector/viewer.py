# =============================================
# Trace 뷰어 — 4단계
#
# 기록 파일(.jsonl)을 읽어서 '시간 막대' 그림을 만든다.
#
#   python viewer.py              가장 최근 기록을 그린다
#   python viewer.py <파일>        그 기록을 그린다
#
# 결과는 data/viewer/timeline.html 로 저장되고 브라우저가 열린다.
#
# ★ 서버를 안 쓰는 이유 ★
#   서버를 켜야만 볼 수 있으면, 서버가 꺼져 있을 때 아무것도 못 본다.
#   포트가 겹치는 문제도 있었다 (5000번은 맥의 AirPlay 가 쓰고 있었다).
#   그냥 HTML 파일 하나를 만들면 더블클릭으로 언제든 열린다.
# =============================================

import glob
import html
import json
import os
import sys
import webbrowser
from datetime import datetime

import storage

여기 = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.normpath(os.path.join(여기, "..", "data", "sessions"))
VIEWER_DIR = os.path.normpath(os.path.join(여기, "..", "data", "viewer"))

# ★ '자리 비움'은 일부러 표시하지 않는다 ★
#   수집기는 '창이 바뀔 때'만 기록한다. 그래서 워드를 6분 동안 계속 보고 있어도,
#   자리를 비운 6분과 기록상 똑같이 보인다. 구분할 방법이 없다.
#   구분하려면 타자 수 같은 걸 같이 세야 하는데 아직 안 만들었다.
#   모르는 것을 아는 척 칠하면 그림이 거짓말을 한다. 그래서 안 칠한다.


# ---------------------------------------------
# 1. 기록 읽기
# ---------------------------------------------
def 최근_기록_찾기():
    파일들 = sorted(glob.glob(os.path.join(SESSIONS_DIR, "*.jsonl")))
    return 파일들[-1] if 파일들 else None


def 읽기(경로):
    줄들 = []
    with open(경로, "r", encoding="utf-8") as f:
        for 원본 in f:
            원본 = 원본.strip()
            if 원본:
                줄들.append(json.loads(원본))
    return 줄들


def 시각(줄):
    return datetime.fromisoformat(줄["time"])


# ---------------------------------------------
# 2. 줄들을 '그릴 수 있는 모양'으로 바꾼다
# ---------------------------------------------
def 정리하기(줄들):
    """돌려주는 것: 앱 구간 목록, 복사 목록, 붙임 목록, 시작·끝 시각"""
    if not 줄들:
        return [], [], [], None, None

    시작, 끝 = 시각(줄들[0]), 시각(줄들[-1])

    구간들 = []       # {"app":…, "from":…, "to":…}
    복사들 = []       # {"at":…, "length":…, "hash":…}
    붙임들 = []       # {"at":…, "length":…, "hash":…, "into":…}

    현재앱 = None
    for 줄 in 줄들:
        t = 시각(줄)
        종류 = 줄["type"]

        if 종류 == "app":
            if 현재앱 is not None:
                현재앱["to"] = t
                구간들.append(현재앱)
            현재앱 = {"app": 줄["data"].get("app") or "(알 수 없음)",
                      "title": 줄["data"].get("title"),
                      "from": t, "to": t}
        elif 종류 == "clipboard":
            복사들.append({"at": t, "length": 줄["data"].get("length"),
                           "hash": 줄["data"].get("hash")})
        elif 종류 == "paste":
            붙임들.append({"at": t, "length": 줄["data"].get("length"),
                           "hash": 줄["data"].get("hash"),
                           "into": 줄["data"].get("into") or "(알 수 없음)"})

    if 현재앱 is not None:
        현재앱["to"] = 끝
        구간들.append(현재앱)

    # 붙인 것이 '아까 복사한 그것'인지 맞춰 본다.
    # 지문이 같으면 같은 글이다. 내용을 보지 않고 알아낸다.
    for 붙임 in 붙임들:
        붙임["from_copy"] = None
        if not 붙임["hash"]:
            continue
        for 복사 in 복사들:
            if 복사["hash"] == 붙임["hash"] and 복사["at"] <= 붙임["at"]:
                붙임["from_copy"] = 복사       # 가장 마지막 것이 남는다
    return 구간들, 복사들, 붙임들, 시작, 끝


# ---------------------------------------------
# 3. 그림 그리기
# ---------------------------------------------
폭 = 1040
왼쪽여백 = 170
줄높이 = 34


def 엑스(t, 시작, 전체초):
    if 전체초 <= 0:
        return 왼쪽여백
    비율 = (t - 시작).total_seconds() / 전체초
    return 왼쪽여백 + 비율 * (폭 - 왼쪽여백 - 30)


def 그리기(경로, 줄들, 검사결과):
    구간들, 복사들, 붙임들, 시작, 끝 = 정리하기(줄들)
    전체초 = (끝 - 시작).total_seconds() if 시작 and 끝 else 0

    # 앱마다 한 줄씩. 처음 나온 순서대로.
    앱순서 = []
    for 구간 in 구간들:
        if 구간["app"] not in 앱순서:
            앱순서.append(구간["app"])
    막대끝 = 60 + max(len(앱순서), 1) * 줄높이
    표시선 = 막대끝 + 30          # 복사·붙임 표시를 놓을 줄. 막대와 겹치지 않게 아래로.
    높이 = 표시선 + 44

    조각 = []

    # 시간 눈금 — 5칸
    for i in range(6):
        t초 = 전체초 * i / 5
        x = 왼쪽여백 + (폭 - 왼쪽여백 - 30) * i / 5
        라벨 = (시작.strftime("%H:%M:%S") if i == 0 else
                f"+{int(t초 // 60)}분" if t초 >= 60 else f"+{int(t초)}초")
        조각.append(f'<line class="grid" x1="{x:.1f}" y1="46" '
                    f'x2="{x:.1f}" y2="{막대끝 + 6}"/>')
        조각.append(f'<text class="tick" x="{x:.1f}" y="38">{라벨}</text>')

    # 앱 이름과 막대
    for i, 앱 in enumerate(앱순서):
        y = 60 + i * 줄높이
        조각.append(f'<text class="appname" x="{왼쪽여백 - 12}" y="{y + 15}">'
                    f'{html.escape(앱[:20])}</text>')
        조각.append(f'<rect class="lane" x="{왼쪽여백}" y="{y}" '
                    f'width="{폭 - 왼쪽여백 - 30}" height="22"/>')

    for 구간 in 구간들:
        i = 앱순서.index(구간["app"])
        y = 60 + i * 줄높이
        x1, x2 = 엑스(구간["from"], 시작, 전체초), 엑스(구간["to"], 시작, 전체초)
        너비 = max(x2 - x1, 3)
        제목 = html.escape(구간.get("title") or "")
        분 = (구간["to"] - 구간["from"]).total_seconds() / 60
        조각.append(
            f'<rect class="seg" x="{x1:.1f}" y="{y}" '
            f'width="{너비:.1f}" height="22" rx="4">'
            f'<title>{html.escape(구간["app"])}'
            f'{" — " + 제목 if 제목 else ""}\n'
            f'{구간["from"].strftime("%H:%M:%S")} → {구간["to"].strftime("%H:%M:%S")}'
            f'  ({분:.1f}분)</title></rect>')

    # 복사 → 붙임 잇는 선 (지문이 같은 것만)
    조각.append(f'<text class="appname" x="{왼쪽여백 - 12}" y="{표시선 + 4}">'
                f'복사 · 붙여넣기</text>')
    for 붙임 in 붙임들:
        if not 붙임["from_copy"]:
            continue
        x1 = 엑스(붙임["from_copy"]["at"], 시작, 전체초)
        x2 = 엑스(붙임["at"], 시작, 전체초)
        조각.append(f'<path class="link" d="M {x1:.1f} {표시선} '
                    f'C {x1:.1f} {표시선 + 16}, {x2:.1f} {표시선 + 16}, '
                    f'{x2:.1f} {표시선}"/>')

    # 복사 표시 (동그라미)
    for 복사 in 복사들:
        x = 엑스(복사["at"], 시작, 전체초)
        길이 = 복사["length"]
        설명 = (f'{길이}글자' if 길이 else '글자가 아닌 것')
        지문 = (복사["hash"] or "")[:12]
        조각.append(f'<circle class="copy" cx="{x:.1f}" cy="{표시선}" r="6">'
                    f'<title>복사  {복사["at"].strftime("%H:%M:%S")}\n{설명}'
                    f'{chr(10) + "지문 " + 지문 + "…" if 지문 else ""}</title></circle>')

    # 붙임 표시 (세모)
    for 붙임 in 붙임들:
        x = 엑스(붙임["at"], 시작, 전체초)
        길이 = 붙임["length"]
        설명 = (f'{길이}글자' if 길이 else '글자가 아닌 것')
        같음 = 붙임["from_copy"] is not None
        꼬리 = ""
        if 같음:
            꼬리 = (f'\n★ {붙임["from_copy"]["at"].strftime("%H:%M:%S")} 에 '
                    f'복사한 것과 지문이 같습니다')
        조각.append(
            f'<polygon class="paste{" matched" if 같음 else ""}" '
            f'points="{x - 6:.1f},{표시선 + 7} {x + 6:.1f},{표시선 + 7} {x:.1f},{표시선 - 5}">'
            f'<title>붙여넣기  {붙임["at"].strftime("%H:%M:%S")}\n{설명}\n'
            f'→ {html.escape(붙임["into"])}{꼬리}</title></polygon>')

    맞은것 = sum(1 for p in 붙임들 if p["from_copy"])
    총분 = 전체초 / 60

    요약 = [
        ("기록된 시간", f"{총분:.0f}분"),
        ("건드린 프로그램", f"{len(앱순서)}개"),
        ("복사", f"{len(복사들)}번"),
        ("붙여넣기", f"{len(붙임들)}번"),
        ("그중 복사한 것을 그대로", f"{맞은것}번"),
    ]
    요약칸 = "".join(
        f'<div class="card"><div class="k">{html.escape(k)}</div>'
        f'<div class="v">{html.escape(v)}</div></div>' for k, v in 요약)

    if 검사결과["ok"]:
        배지 = (f'<span class="ok">✅ 고쳐진 곳 없음 · {검사결과["lines"]}줄</span>')
    else:
        배지 = (f'<span class="bad">❌ {검사결과["broken_at"]}번째 줄이 어긋납니다 — '
                f'{html.escape(검사결과["reason"])}</span>')

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>Trace — {html.escape(os.path.basename(경로))}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin:0; padding:28px; background:#fafaf9; color:#171717;
         font-family:-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif; }}
  .wrap {{ max-width:1100px; margin:0 auto; }}
  h1 {{ font-size:20px; margin:0 0 4px; letter-spacing:-.02em; }}
  .sub {{ color:#78716c; font-size:13px; margin-bottom:18px; }}
  .ok {{ color:#15803d; font-weight:600; }}
  .bad {{ color:#b91c1c; font-weight:600; }}
  .cards {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:18px; }}
  .card {{ background:#fff; border:1px solid #e7e5e4; border-radius:10px;
           padding:12px 16px; min-width:112px; }}
  .k {{ font-size:11px; color:#78716c; margin-bottom:4px; }}
  .v {{ font-size:19px; font-weight:600; letter-spacing:-.02em; }}
  .panel {{ background:#fff; border:1px solid #e7e5e4; border-radius:12px;
            padding:12px; overflow-x:auto; }}
  svg {{ display:block; }}
  .grid {{ stroke:#f0efed; stroke-width:1; }}
  .tick {{ fill:#a8a29e; font-size:10px; text-anchor:middle; }}
  .appname {{ fill:#57534e; font-size:12px; text-anchor:end; }}
  .lane {{ fill:#f7f6f4; rx:4; }}
  .seg {{ fill:#2563eb; opacity:.85; }}
  .copy {{ fill:#fff; stroke:#0d9488; stroke-width:2.5; }}
  .paste {{ fill:#fbbf24; }}
  .paste.matched {{ fill:#ea580c; }}
  .link {{ fill:none; stroke:#ea580c; stroke-width:1.5; opacity:.55;
           stroke-dasharray:3 3; }}
  .legend {{ display:flex; gap:18px; font-size:12px; color:#57534e;
             margin-top:12px; flex-wrap:wrap; }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%;
          margin-right:5px; vertical-align:-1px; }}
  .note {{ margin-top:18px; font-size:12px; color:#78716c; line-height:1.7; }}
  @media (max-width:700px) {{ body {{ padding:16px; }} }}
</style></head><body><div class="wrap">
  <h1>Trace — 작업 기록</h1>
  <div class="sub">{html.escape(os.path.basename(경로))} ·
    {시작.strftime("%Y-%m-%d %H:%M:%S") if 시작 else "?"} →
    {끝.strftime("%H:%M:%S") if 끝 else "?"} · {배지}</div>
  <div class="cards">{요약칸}</div>
  <div class="panel">
    <svg width="{폭}" height="{높이}" viewBox="0 0 {폭} {높이}">{"".join(조각)}</svg>
    <div class="legend">
      <span><span class="dot" style="background:#2563eb"></span>그 프로그램을 보고 있던 구간</span>
      <span><span class="dot" style="background:#fff;border:2px solid #0d9488"></span>복사</span>
      <span><span class="dot" style="background:#fbbf24"></span>붙여넣기</span>
      <span><span class="dot" style="background:#ea580c"></span>복사한 것을 그대로 붙임</span>
    </div>
  </div>
  <div class="note">
    막대나 표시에 <b>마우스를 올리면</b> 자세한 내용이 나옵니다.<br>
    주황색 세모와 점선은 <b>아까 복사한 것과 지문이 같다</b>는 뜻입니다 —
    내용을 하나도 보지 않고 알아낸 것입니다.<br>
    <b>막대가 길다고 계속 작업했다는 뜻은 아닙니다.</b> 수집기는 창이 바뀔 때만
    기록하므로, 그 앱을 계속 보고 있던 것과 자리를 비운 것이 지금은 똑같아 보입니다.<br>
    이 그림이 보장하는 것은 <b>“기록이 만들어진 뒤에 고쳐지지 않았다”</b>뿐입니다.
    기록된 내용이 사실이라거나, 이 사람이 직접 했다는 뜻은 아닙니다.
  </div>
</div></body></html>"""


# ---------------------------------------------
def main():
    경로 = sys.argv[1] if len(sys.argv) > 1 else 최근_기록_찾기()

    if not 경로 or not os.path.exists(경로):
        print()
        print("  기록 파일이 없습니다.")
        print("  먼저 수집기를 켜고 잠깐 작업해 보세요:  python collector.py")
        print()
        return 1

    줄들 = 읽기(경로)
    if not 줄들:
        print(f"\n  {경로} 가 비어 있습니다.\n")
        return 1

    검사결과 = storage.검사(경로)

    os.makedirs(VIEWER_DIR, exist_ok=True)
    결과경로 = os.path.join(VIEWER_DIR, "timeline.html")
    with open(결과경로, "w", encoding="utf-8") as f:
        f.write(그리기(경로, 줄들, 검사결과))

    print()
    print(f"  그렸습니다: {결과경로}")
    print(f"  기록 {len(줄들)}줄 · "
          f"{'✅ 고쳐진 곳 없음' if 검사결과['ok'] else '❌ ' + 검사결과['reason']}")
    print()
    webbrowser.open("file://" + 결과경로)
    return 0


if __name__ == "__main__":
    sys.exit(main())
