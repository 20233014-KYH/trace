# =============================================
# 맥에서 "지금 어떤 프로그램이 켜져 있나"를 알아내는 파일
#
# 윈도우용은 platform_win.py 에 따로 있다.
# 두 파일은 이름이 같은 함수를 하나씩 갖고, 같은 모양의 답을 돌려준다.
# 그래서 collector.py 는 지금이 맥인지 윈도우인지 신경 쓰지 않아도 된다.
# =============================================

from AppKit import NSWorkspace
from Foundation import NSRunLoop, NSDate


def active_app():
    """지금 맨 앞에 떠 있는 프로그램의 이름을 돌려준다.

    돌려주는 모양 (윈도우용도 똑같아야 한다) :
        {"app": "Google Chrome", "title": None}


    ★ 우편함 이야기 — 이 함수가 두 줄짜리가 아닌 이유 ★

    맥은 "지금 어떤 프로그램이 활성이다" 같은 소식을 우리 프로그램의
    우편함에 넣어 둔다. 그런데 우리가 우편함을 열어보지 않으면,
    맥에게 물어봐도 예전에 받아둔 옛날 소식을 그대로 돌려준다.

    그래서 창을 바꿔도 한 박자 늦게 따라오는 일이 생긴다.
    (직접 겪었다. 창을 바꿔도 직전 프로그램 이름이 계속 찍혔다)

    아래 NSRunLoop... 한 줄이 "우편함을 잠깐 열어본다"는 뜻이다.
    0.05초만 열었다 닫는다. 이 한 줄이 있고 없고가 정확도를 가른다.


    title(창 제목)이 None 인 이유 :
        맥은 다른 프로그램의 창 제목을 읽으려면 사용자가 시스템 설정에서
        '화면 기록' 권한을 켜줘야 한다. 1단계에서는 프로그램 이름만으로
        충분하므로 그냥 None 을 넣는다. (윈도우는 권한 없이도 읽힌다)
    """
    # 우편함을 0.05초 동안 열어 새 소식을 받는다
    NSRunLoop.currentRunLoop().runUntilDate_(
        NSDate.dateWithTimeIntervalSinceNow_(0.05)
    )

    # 켜져 있는 프로그램들을 훑어서 지금 활성인 것을 찾는다
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.isActive():
            return {"app": app.localizedName(), "title": None}

    # 아주 가끔 활성인 프로그램이 하나도 안 잡힐 때가 있다
    return {"app": None, "title": None}
