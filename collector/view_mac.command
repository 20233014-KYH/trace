#!/bin/bash
# 기록을 그림으로 본다. ★ 이 파일을 더블클릭하면 된다.
cd "$(dirname "$0")"
. ./_conda_setup.sh
python viewer.py
echo ""
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
