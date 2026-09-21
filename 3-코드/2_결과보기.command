#!/bin/bash
# 기록을 그림으로 본다 (맥). ★ 더블클릭.   윈도우는 2_결과보기.bat
cd "$(dirname "$0")"
. ./_conda_setup.sh
python core/derive.py "data/events-*.jsonl" --out data/session.json || exit 1
open ui/viewer.html
echo ""
echo "  뷰어가 열렸습니다. data/session.json 을 창에 끌어다 놓으세요."
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
