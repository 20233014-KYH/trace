#!/bin/bash
# 붙여넣기가 왜 안 잡히는지 진단한다. ★ 이 파일을 더블클릭하면 된다.
cd "$(dirname "$0")"
. ./_conda_setup.sh
python check_permission.py
echo ""
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
