#!/bin/bash
# 맥에서 수집기를 켠다. ★ 이 파일을 더블클릭하면 된다.
#   (윈도우는 1_기록시작.bat)
cd "$(dirname "$0")"
. ./_conda_setup.sh
python collector/collector.py --dry-run
echo ""
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
