# =============================================
# 윈도우에서 "지금 무슨 프로그램?" 과 "뭔가 복사했나?" 를 알아내는 파일
#
#            ★ 팀원(B)이 채울 파일 ★
#
# 맥용은 platform_mac.py 에 이미 만들어져 있다. 그걸 열어보면
# 어떤 모양으로 답을 돌려줘야 하는지 볼 수 있다.
# 함수 이름과 돌려주는 모양이 맥용과 똑같아야 한다.
#
# 준비물 :  pip install pywin32 psutil
# =============================================

import hashlib

# 아래 줄들의 # 을 지우면 사용할 수 있다
# import win32gui
# import win32process
# import win32clipboard
# import psutil


def active_app():
    """지금 맨 앞에 떠 있는 프로그램의 이름과 창 제목을 돌려준다.

    반드시 이 모양으로 (맥용과 똑같이) :
        {"app": "chrome.exe", "title": "claude.ai - Claude"}
        못 찾으면  {"app": None, "title": None}

    쓸 수 있는 것 :
        번호   = win32gui.GetForegroundWindow()          맨 앞 창의 번호
        제목   = win32gui.GetWindowText(번호)             그 창의 제목
        _, pid = win32process.GetWindowThreadProcessId(번호)
        이름   = psutil.Process(pid).name()               프로그램 이름

    맥과 달리 윈도우는 창 제목까지 권한 없이 읽힌다.
    그래서 title 에 실제 제목을 넣을 수 있다.
    """
    # TODO: 여기를 채우세요
    return {"app": None, "title": None}


def clipboard_serial():
    """클립보드가 바뀔 때마다 1씩 오르는 번호를 돌려준다. 내용은 읽지 않는다.

    방법 1 (추천) :
        win32clipboard.GetClipboardSequenceNumber()
        윈도우가 직접 세어주는 번호. 내용을 열지 않아도 된다.

    방법 2 (위 함수가 없으면) :
        클립보드 글자를 읽어서 해시를 만들고, 그 해시가 바뀌면
        번호를 1 올린다. 직접 세는 방식.

    돌려주는 것 : 정수 하나
    """
    # TODO: 여기를 채우세요
    return 0


def clipboard_digest():
    """지금 클립보드의 '길이'와 '지문'만 돌려준다. 내용은 돌려주지 않는다.

    반드시 이 모양으로 (맥용과 똑같이) :
        {"length": 240, "hash": "a3f9c2d1..."}
        글자가 아니면  {"length": None, "hash": None}

    쓸 수 있는 것 :
        win32clipboard.OpenClipboard()
        글자 = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()        ← 반드시 닫아야 한다

        지문 = hashlib.sha256(글자.encode("utf-8")).hexdigest()

    주의 : 클립보드에 글자가 없으면 GetClipboardData 가 오류를 낸다.
           try / except 로 감싸고, 오류면 {"length": None, "hash": None} 을 돌려준다.
           그리고 오류가 나도 CloseClipboard() 는 꼭 불러야 한다.
    """
    # TODO: 여기를 채우세요
    return {"length": None, "hash": None}
