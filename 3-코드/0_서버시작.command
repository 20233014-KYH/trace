#!/bin/bash
# 서버를 켠다 (맥). ★ 더블클릭.   윈도우는 0_서버시작.bat
cd "$(dirname "$0")"
. ./_conda_setup.sh
python server/app.py
echo ""
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
