# =============================================
# Trace 수집기 — 기록 담당 (3단계)
#
# 하는 일 : 수집기가 본 것을 파일에 한 줄씩 append 한다.
#           그리고 각 줄에 '지문(해시)'을 붙여서,
#           나중에 누가 파일을 고치면 티가 나게 만든다.
#
# 파일 위치 : trace/data/sessions/2026-09-19_154002.jsonl
#             (data 폴더는 깃에 올라가지 않는다 = 내 컴에만 있다)
#
# 왜 .jsonl 인가
#   json  : 하나의 큰 덩어리. 저장하려면 매번 전체를 다시 쓴다.
#   jsonl : 한 줄 = 기록 하나. 뒤에 붙이기만 한다.
#           → 도중에 컴퓨터가 꺼져도 앞부분은 멀쩡하다.
#
# 혼자 시험해 보기 :  python storage.py
# 기록 검사해 보기 :  python storage.py ../data/sessions/어떤파일.jsonl
# =============================================

import hashlib
import json
import os
import sys
from datetime import datetime


# 체인의 출발점. 맨 첫 줄은 '이전 지문'이 없으므로 0 을 64개 쓴다.
# (app.py 의 GENESIS 와 같은 값이다)
GENESIS = "0" * 64

# 이 파일이 있는 폴더 기준으로 data 폴더를 찾는다.
# 이렇게 해야 어느 폴더에서 실행하든 같은 곳에 저장된다.
여기 = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(여기, "..", "data", "sessions")


# ---------------------------------------------
# 지문 만들기 — 이 프로젝트의 심장
# ---------------------------------------------
def 지문(이전지문, 시각, 종류, 내용):
    """이전 지문 + 시각 + 종류 + 내용 을 이어붙여 SHA256 을 낸다.

    ★ 핵심은 '이전 지문'이 재료에 들어간다는 것이다.
      3번째 줄을 몰래 고치면 3번의 지문이 달라지고,
      4번은 3번의 지문을 재료로 썼으므로 4번도 어긋나고,
      그 뒤가 전부 도미노처럼 어긋난다.
      한 줄만 고치고 넘어가는 것이 불가능해진다.

    sort_keys=True  : 내용의 순서를 항상 똑같이 맞춘다.
                      안 그러면 같은 내용인데 지문이 달라질 수 있다.
    ensure_ascii=False : 한글을 한글 그대로 둔다.
    """
    내용_글자 = json.dumps(내용, sort_keys=True, ensure_ascii=False)
    재료 = f"{이전지문}|{시각}|{종류}|{내용_글자}"
    return hashlib.sha256(재료.encode("utf-8")).hexdigest()


# ---------------------------------------------
# 기록장 — 세션 하나가 파일 하나다
# ---------------------------------------------
class 기록장:
    """한 번 앉아서 작업한 구간(= 세션) 하나를 파일 하나에 담는다.

    쓰는 법:
        장부 = 기록장()
        장부.적기("app", {"app": "Chrome", "title": None})
        장부.닫기()
    """

    def __init__(self, 폴더=None):
        폴더 = 폴더 or SESSIONS_DIR
        os.makedirs(폴더, exist_ok=True)      # 폴더가 없으면 만든다

        시작시각 = datetime.now()
        파일이름 = 시작시각.strftime("%Y-%m-%d_%H%M%S") + ".jsonl"
        # normpath : 경로에 낀 "collector/../data" 같은 것을 깔끔하게 정리한다
        self.경로 = os.path.normpath(os.path.join(폴더, 파일이름))

        self.직전지문 = GENESIS
        self.줄번호 = 0

        # encoding="utf-8" 을 꼭 적어야 한다.
        # 윈도우는 안 적으면 cp949 로 저장해서 한글이 깨진다.
        self.파일 = open(self.경로, "a", encoding="utf-8")

        self.적기("session_start", {
            "os": __import__("platform").system(),
            "collector_version": "0.3",
        })

    def 적기(self, 종류, 내용):
        """기록 한 줄을 파일 맨 뒤에 붙인다. 돌려주는 값은 그 줄의 지문."""
        self.줄번호 += 1
        시각 = datetime.now().isoformat(timespec="seconds")

        이번지문 = 지문(self.직전지문, 시각, 종류, 내용)

        줄 = {
            "seq": self.줄번호,
            "time": 시각,
            "type": 종류,
            "data": 내용,
            "prev": self.직전지문,
            "hash": 이번지문,
        }

        self.파일.write(json.dumps(줄, ensure_ascii=False) + "\n")
        self.파일.flush()     # ★ 바로 디스크에 밀어 넣는다.
        #                       안 하면 컴퓨터가 꺼졌을 때 최근 기록이 날아간다.

        self.직전지문 = 이번지문
        return 이번지문

    def 닫기(self):
        """마지막 줄을 남기고 파일을 닫는다."""
        if self.파일.closed:
            return
        self.적기("session_end", {"lines": self.줄번호})
        self.파일.close()


# ---------------------------------------------
# 검사 — 이 파일이 나중에 고쳐졌나?
# ---------------------------------------------
def 검사(경로):
    """기록 파일을 처음부터 다시 계산해 보고, 어긋나는 첫 줄을 찾는다.

    돌려주는 모양:
        {"ok": True,  "lines": 12, "broken_at": None}
        {"ok": False, "lines": 12, "broken_at": 5, "reason": "..."}
    """
    직전 = GENESIS
    줄수 = 0

    with open(경로, "r", encoding="utf-8") as f:
        for 번호, 원본줄 in enumerate(f, start=1):
            원본줄 = 원본줄.strip()
            if not 원본줄:
                continue
            줄수 = 번호

            try:
                줄 = json.loads(원본줄)
            except json.JSONDecodeError:
                return {"ok": False, "lines": 줄수, "broken_at": 번호,
                        "reason": "줄이 깨져 있어 읽을 수 없습니다"}

            # ① 이 줄이 기억하는 '이전 지문'이, 실제 이전 줄의 지문과 같은가
            if 줄.get("prev") != 직전:
                return {"ok": False, "lines": 줄수, "broken_at": 번호,
                        "reason": "앞줄과의 연결이 끊어졌습니다 (줄을 지웠거나 끼워넣었습니다)"}

            # ② 이 줄의 내용으로 지문을 다시 계산하면 적혀 있는 지문과 같은가
            다시계산 = 지문(줄["prev"], 줄["time"], 줄["type"], 줄["data"])
            if 다시계산 != 줄.get("hash"):
                return {"ok": False, "lines": 줄수, "broken_at": 번호,
                        "reason": "줄의 내용이 고쳐졌습니다"}

            직전 = 줄["hash"]

    return {"ok": True, "lines": 줄수, "broken_at": None, "last_hash": 직전}


# ---------------------------------------------
# 직접 실행했을 때
# ---------------------------------------------
def _자가진단():
    import shutil
    import tempfile

    임시폴더 = tempfile.mkdtemp()
    print()
    print("  storage.py 자가진단")
    print("  " + "─" * 58)

    try:
        # 1. 써 보기
        장부 = 기록장(폴더=임시폴더)
        장부.적기("app", {"app": "Google Chrome", "title": "테스트"})
        장부.적기("clipboard", {"length": 251, "hash": "aa87047e"})
        장부.닫기()
        print(f"  ✅ 기록 만들기      {os.path.basename(장부.경로)}")

        # 2. 멀쩡한 파일 검사
        결과 = 검사(장부.경로)
        if 결과["ok"]:
            print(f"  ✅ 검사 (정상)      {결과['lines']}줄 모두 정상")
        else:
            print(f"  ❌ 검사 (정상)      {결과}")
            return

        # 3. 일부러 한 글자 고쳐 보기
        고친파일 = 장부.경로 + ".tampered"
        shutil.copy(장부.경로, 고친파일)
        줄들 = open(고친파일, encoding="utf-8").read().splitlines()
        줄들[2] = 줄들[2].replace('"length": 251', '"length": 999')
        open(고친파일, "w", encoding="utf-8").write("\n".join(줄들) + "\n")

        결과 = 검사(고친파일)
        if not 결과["ok"] and 결과["broken_at"] == 3:
            print(f"  ✅ 검사 (조작)      {결과['broken_at']}번째 줄에서 잡아냄")
            print(f"                      이유: {결과['reason']}")
        else:
            print(f"  ❌ 검사 (조작)      못 잡아냈습니다 → {결과}")
            return

        # 4. 일부러 한 줄 지워 보기
        지운파일 = 장부.경로 + ".deleted"
        줄들 = open(장부.경로, encoding="utf-8").read().splitlines()
        del 줄들[1]
        open(지운파일, "w", encoding="utf-8").write("\n".join(줄들) + "\n")

        결과 = 검사(지운파일)
        if not 결과["ok"]:
            print(f"  ✅ 검사 (삭제)      {결과['broken_at']}번째 줄에서 잡아냄")
            print(f"                      이유: {결과['reason']}")
        else:
            print("  ❌ 검사 (삭제)      못 잡아냈습니다")
            return

        print()
        print("  전부 통과했습니다.")
        print()

    finally:
        shutil.rmtree(임시폴더, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # python storage.py <파일>  → 그 파일을 검사한다
        경로 = sys.argv[1]
        결과 = 검사(경로)
        print()
        if 결과["ok"]:
            print(f"  ✅ 정상입니다. {결과['lines']}줄, 고쳐진 곳 없음.")
            print(f"     마지막 지문 {결과['last_hash'][:16]}…")
        else:
            print(f"  ❌ {결과['broken_at']}번째 줄이 어긋납니다.")
            print(f"     {결과['reason']}")
        print()
    else:
        _자가진단()
