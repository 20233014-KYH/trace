# =============================================
# 윈도우에서 "지금 어떤 프로그램이 켜져 있나"를 알아내는 파일
#
#            ★ 팀원(B)이 채울 파일 ★
#
# 맥용은 platform_mac.py 에 이미 만들어져 있다. 그걸 열어보면
# 어떤 모양으로 답을 돌려줘야 하는지 볼 수 있다.
#
# 준비물 :  pip install pywin32
# =============================================

# 아래 두 줄의 # 을 지우면 사용할 수 있다
# import win32gui
# import win32process
# import psutil


def active_app():
    """지금 맨 앞에 떠 있는 프로그램의 이름과 창 제목을 돌려준다.

    반드시 이 모양으로 돌려줘야 한다 (맥용과 똑같아야 한다) :
        {"app": "chrome.exe", "title": "claude.ai - Claude"}

    만들 때 쓸 수 있는 것 :
        win32gui.GetForegroundWindow()   맨 앞 창의 번호를 알려준다
        win32gui.GetWindowText(번호)      그 창의 제목을 알려준다
        win32process.GetWindowThreadProcessId(번호)   그 창을 만든 프로그램 번호
        psutil.Process(프로그램번호).name()            프로그램 이름

    아무것도 못 찾으면 {"app": None, "title": None} 을 돌려준다.
    """
    # TODO: 여기를 채우세요.
    # 아직 안 만들었으니 지금은 빈 답을 돌려준다.
    return {"app": None, "title": None}
