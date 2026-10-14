#!/bin/bash
# 맥 서명 인증서 한 번 만들기 (10/14) — 저장소 주인(김용현)이 맥에서 한 번만 더블클릭
#
# 왜: 맥은 권한(손쉬운 사용 · 입력 모니터링)을 앱의 서명으로 기억한다. 지금까지는 임시(ad-hoc) 서명이라 빌드마다 지문이 달라
#     업데이트할 때마다 권한이 풀렸다 (기록이 조용히 덜 남음). 같은 인증서로 서명하면 버전이 바뀌어도 같은 Trace 로 알아본다.
# 하는 일:
#   1) 3-코드/data/mac-signing/ 에 코드 서명 인증서(스스로 서명 · 20년) 를 만든다 — data/ 는 .gitignore 라 저장소에 안 올라감
#   2) GitHub 비밀값 MAC_SIGN_P12 · MAC_SIGN_PASSWORD 에 넣는다 (gh 로그인 필요) — 릴리스 빌드(release.yml)가 이걸로 서명
# 이미 만들었으면 1) 은 건너뛰고 2) 만 다시 한다. 인증서를 새로 만들면 모두의 맥 권한이 한 번 더 풀리니 지우지 말 것.
# 애플 개발자 인증서가 아니라 처음 설치할 때 "확인되지 않은 개발자" 는 그대로 뜬다 (그건 애플 개발자 등록이 있어야 없어짐).
set -euo pipefail
cd "$(dirname "$0")/.."                                    # 3-코드
REPO="20233014-KYH/trace"
D="data/mac-signing"
SSL=/usr/bin/openssl                                        # 맥 기본(LibreSSL) — 맥 키체인이 읽는 p12 를 만든다

if [ -f "$D/trace-sign.p12" ]; then
  echo "인증서가 이미 있어요: $D/trace-sign.p12 — GitHub 비밀값만 다시 넣어요"
else
  mkdir -p "$D"
  chmod 700 "$D"
  umask 077
  "$SSL" rand -hex 24 | tr -d '\n' > "$D/p12-password.txt"
  "$SSL" req -x509 -newkey rsa:2048 -nodes -days 7300 -config packaging/mac-sign.cnf \
    -keyout "$D/key.pem" -out "$D/trace-sign-cert.pem"
  "$SSL" pkcs12 -export -inkey "$D/key.pem" -in "$D/trace-sign-cert.pem" -name "Trace Code Signing" \
    -out "$D/trace-sign.p12" -passout "file:$D/p12-password.txt"
  rm -f "$D/key.pem"
  echo "인증서를 만들었어요: $D/trace-sign.p12 (이 폴더는 지우지 마세요)"
fi

if ! command -v gh > /dev/null; then
  echo "gh 가 없어요 — brew install gh 후 gh auth login, 그리고 이 파일을 다시 열어 주세요"
  exit 1
fi
base64 -i "$D/trace-sign.p12" | tr -d '\n' | gh secret set MAC_SIGN_P12 --repo "$REPO"
gh secret set MAC_SIGN_PASSWORD --repo "$REPO" < "$D/p12-password.txt"
echo
echo "끝났어요. 다음 릴리스부터 같은 인증서로 서명돼요."
"$SSL" x509 -in "$D/trace-sign-cert.pem" -noout -subject -enddate
gh secret list --repo "$REPO" | grep MAC_SIGN || true
