"""
reset_password.py — 비밀번호를 잊은 계정의 비밀번호를 새로 정한다 (관리자용 · 김용현 PC 에서)

  python 3-코드/server/reset_password.py 이메일

server/.env 의 DB(=인터넷 서버와 같은 Supabase)에 바로 쓴다. 새 비밀번호는 화면에 안 보이게 두 번 입력받는다.
바꾸면 그 계정의 로그인(토큰)을 전부 끊는다 → 학생 화면에서 새 비밀번호로 다시 로그인.
★ 비밀번호를 채팅·명령어 줄에 쓰지 않는다 (명령어 기록에 남는다). 이 스크립트가 직접 묻는다.
"""
import getpass
import sys
import unicodedata

from werkzeug.security import generate_password_hash

import db


def main():
    if len(sys.argv) != 2:
        sys.exit("쓰는 법: python 3-코드/server/reset_password.py 이메일")
    이메일 = sys.argv[1].strip().lower()
    print(f"DB: {db.DB_URL_SAFE}")
    with db.Session() as d:
        u = d.query(db.User).filter(db.User.email == 이메일).first()
        if not u:
            sys.exit(f"이 DB 에 {이메일} 계정이 없습니다 — 다른 서버(이 PC 의 시험 서버 등)에서 가입했을 수 있습니다.")
        새 = getpass.getpass("새 비밀번호 (8자 이상): ")
        if len(새) < 8 or 새 != getpass.getpass("한 번 더: "):
            sys.exit("8자 이상이어야 하고 두 번 같아야 합니다. 바꾸지 않았습니다.")
        u.password_hash = generate_password_hash(unicodedata.normalize("NFC", 새))
        끊음 = d.query(db.Token).filter(db.Token.user_id == u.id).delete()
        이름 = u.name
        d.commit()
    print(f"바꿨습니다: {이메일} ({이름}) · 끊은 로그인 {끊음}개 — 새 비밀번호로 다시 로그인하세요.")


if __name__ == "__main__":
    main()
