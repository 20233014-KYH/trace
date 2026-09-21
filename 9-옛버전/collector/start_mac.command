#!/bin/bash
# 맥에서 수집기를 켠다. ★ 이 파일을 더블클릭하면 된다.
#    conda activate trace 를 매번 안 쳐도 되게 하려고 만들었다.
cd "$(dirname "$0")"
. ./_conda_setup.sh
python collector.py
echo ""
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
