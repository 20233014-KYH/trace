"""
test_updater.py — 앱 안 업데이트(app/updater.py) · 이슈 #79

  python app/test_updater.py

  · 개발판(저장소 · packaging/dist · 제거 프로그램 없는 exe)은 앱 안 업데이트 안 함 · 설치판(옆에 unins000.exe)만
  · /local/update 가 dev 를 알려 줌 (화면이 알림을 숨김)
  · 윈도우: 바꾸기.cmd 가 파이프(tasklist | find) 없이 Wait-Process 로 기다리고 · DETACHED_PROCESS 를 쓰지 않음
  · 윈도우: 그 cmd 를 실제로 돌려 — 기다리는 프로그램이 끝난 뒤에야 설치 · 다시 열기로 넘어감 (가짜 설치 파일)
"""
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import updater as U                              # noqa: E402
from core import settings                        # noqa: E402

통과 = 실패 = 0


def 검사(이름, 조건, 설명=""):
    global 통과, 실패
    통과, 실패 = (통과 + 1, 실패) if 조건 else (통과, 실패 + 1)
    print(f"  {'✅' if 조건 else '❌'} {이름:<46} {설명}")


def 설치판인_척(exe):
    settings.FROZEN, sys.executable = True, exe
    return U.개발판(), U.앱_자리()


def main():
    print("\n  앱 안 업데이트 검사 (이슈 #79)\n  " + "─" * 70)
    옛 = (settings.FROZEN, sys.executable)
    t = tempfile.mkdtemp(prefix="trace-upd-")
    try:
        검사("저장소에서 돌리면 개발판 · 바꿀 자리 없음", U.개발판() and U.앱_자리() is None)
        dist = os.path.join(t, "Trace", "3-코드", "packaging", "dist", "Trace", "Trace.exe")
        os.makedirs(os.path.dirname(dist)); open(dist, "w").close()
        검사("저장소에서 묶은 packaging/dist exe = 개발판", 설치판인_척(dist) == (True, None))
        if os.name == "nt":
            깐곳 = os.path.join(t, "Programs", "Trace", "Trace.exe")
            os.makedirs(os.path.dirname(깐곳)); open(깐곳, "w").close()
            검사("제거 프로그램 없는 exe = 개발판", 설치판인_척(깐곳) == (True, None))
            open(os.path.join(os.path.dirname(깐곳), "unins000.exe"), "w").close()
            검사("옆에 unins000.exe (Inno 가 깐 것) = 설치판 · 그 자리로 다시 엶", 설치판인_척(깐곳) == (False, os.path.realpath(깐곳)))
        settings.FROZEN, sys.executable = 옛

        import statement as ST
        c = ST.app.test_client()
        U.최신 = lambda 새로=False: {"version": "99.0.0", "windows": {"name": "x.exe", "url": "http://127.0.0.1:9/x"}}
        d = c.get("/local/update", base_url=f"http://127.0.0.1:{ST.PORT}").json
        검사("/local/update: 새 버전이 있어도 개발판이면 dev · 바로 못 바꿈", d["newer"] and d["dev"] is True and d["can_install"] is False)
        txt = open(os.path.join(HERE, "shell.js"), encoding="utf-8").read()
        검사("화면(왼쪽 메뉴 알림)은 dev 면 안 띄움", "u.dev" in txt)

        if os.name == "nt":
            print("\n  ━━ 윈도우 바꾸기.cmd 실제로 돌려 보기")
            기다릴 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(4)"])
            흔적 = os.path.join(t, "흔적.txt")
            # 가짜 설치 파일 = 흔적만 남기는 .cmd (한글 · 띄어쓰기 경로). 진짜는 .exe 라 끝나면 다음 줄(다시 열기)로 돌아오지만
            # .cmd 는 cmd 가 그쪽으로 넘어가 안 돌아온다 → 여기선 "기다린 뒤 설치 줄까지 감" 만 보고, 다시 열기는 줄 글로 확인
            가짜설치 = os.path.join(t, "가짜 설치.cmd")
            open(가짜설치, "w", encoding="utf-8").write(f'@echo off\necho installed >> "{흔적}"\n')     # 글 모드 — \n 이 \r\n 이 됨
            가짜앱 = os.path.join(t, "Trace.exe")             # 실제로 켜지지 않음 (위 설치 줄에서 cmd 가 넘어감)
            띄움 = {}
            진짜 = subprocess.Popen

            def 엿보기(args, **kw):
                띄움.update(args=args, flags=kw.get("creationflags", 0))
                return 진짜(args, **kw)
            U.subprocess.Popen, U.os.getpid, U.앱_자리 = 엿보기, (lambda: 기다릴.pid), (lambda: 가짜앱)
            곳 = os.path.join(t, "updates"); os.makedirs(곳)
            시작 = time.time()
            U._윈도우(가짜설치, 곳)
            cmd = open(os.path.join(곳, "바꾸기.cmd"), encoding="utf-8").read()
            검사("파이프(tasklist | find) 없이 Wait-Process 로 기다림", "Wait-Process -Id" in cmd and "| find" not in cmd and str(기다릴.pid) in cmd)
            검사("DETACHED_PROCESS 안 씀 · 창 없이 (CREATE_NO_WINDOW)",
                 not 띄움["flags"] & subprocess.DETACHED_PROCESS and 띄움["flags"] & subprocess.CREATE_NO_WINDOW)
            time.sleep(1.5)
            검사("기다리는 프로그램이 살아 있는 동안엔 넘어가지 않음", not os.path.exists(흔적))
            for _ in range(60):
                if os.path.exists(흔적):
                    break
                time.sleep(0.25)
            걸림 = time.time() - 시작
            검사("끝나면 설치 줄로 넘어감 (한글 · 띄어쓰기 경로 · 멈추지 않음)",
                 os.path.exists(흔적) and "installed" in open(흔적).read() and 걸림 >= 3.5, f"{걸림:.1f}초 (기다린 프로그램 4초)")
            검사("설치 다음 줄 = 설치판 자리를 다시 엶", cmd.strip().splitlines()[-1] == f'start "" "{가짜앱}"')
            U.subprocess.Popen = 진짜
        print(f"\n  {'─' * 70}\n  통과 {통과} · 실패 {실패}\n")
    finally:
        settings.FROZEN, sys.executable = 옛
    return 실패 == 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(0 if main() else 1)
