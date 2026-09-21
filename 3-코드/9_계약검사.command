#!/bin/bash
# 서버가 계약대로 도는지 검사한다 (서버를 먼저 켜 두세요). ★ 더블클릭.
cd "$(dirname "$0")"
. ./_conda_setup.sh
python server/test_contract.py
echo ""
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
