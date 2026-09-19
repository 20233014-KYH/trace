# =============================================
# 맥에서 "지금 무슨 프로그램?" 과 "뭔가 복사했나?" 를 알아내는 파일
#
# 윈도우용은 platform_win.py 에 따로 있다.
# 두 파일은 이름이 같은 함수를 갖고, 같은 모양의 답을 돌려준다.
# 그래서 collector.py 는 맥인지 윈도우인지 신경 쓰지 않아도 된다.
# =============================================

import hashlib

from AppKit import NSWorkspace, NSPasteboard, NSPasteboardTypeString
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


    title(창 제목)이 None 인 이유 :
        맥은 다른 프로그램의 창 제목을 읽으려면 '화면 기록' 권한이 필요하다.
        1단계에서는 프로그램 이름만으로 충분하므로 None 을 넣는다.
    """
    NSRunLoop.currentRunLoop().runUntilDate_(
        NSDate.dateWithTimeIntervalSinceNow_(0.05)
    )

    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.isActive():
            return {"app": app.localizedName(), "title": None}

    return {"app": None, "title": None}


# ---------------------------------------------
# 복사(클립보드) 관련 함수 두 개
#
# 왜 두 개로 나눴나 :
#   1초마다 클립보드 "내용"을 읽으면 남의 비밀번호까지 계속 들여다보는 셈이다.
#   그래서 평소에는 번호만 본다. 번호가 바뀌었을 때만 길이를 잰다.
#   이게 기획안 4.3 "내용을 읽지 않는다" 원칙을 코드로 지키는 방법이다.
# ---------------------------------------------
def clipboard_serial():
    """클립보드가 바뀔 때마다 1씩 오르는 번호를 돌려준다.

    내용은 전혀 읽지 않는다. 번호만 본다.
    (윈도우에도 똑같은 번호가 있다 — GetClipboardSequenceNumber)
    """
    return NSPasteboard.generalPasteboard().changeCount()


def clipboard_digest():
    """지금 클립보드의 '길이'와 '지문'만 돌려준다. 내용은 돌려주지 않는다.

    돌려주는 모양 :
        {"length": 240, "hash": "a3f9c2d1..."}
        글자가 아니면 (사진 등)  {"length": None, "hash": None}

    지문(해시)이란 :
        아무리 긴 글이라도 넣으면 64자리 암호 같은 값이 나온다.
        같은 글은 언제나 같은 값, 한 글자만 달라도 완전히 다른 값이 나온다.
        그래서 "AI 탭에서 복사한 것"과 "워드에 붙여넣은 것"이 같은지를
        내용을 보지 않고도 비교할 수 있다.
    """
    text = NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)

    if text is None:                       # 사진·파일 등 글자가 아닌 것
        return {"length": None, "hash": None}

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {"length": len(text), "hash": digest}
