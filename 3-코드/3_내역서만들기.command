#!/bin/bash
# AI 활용 내역서 만들기 (맥). ★ 더블클릭.   윈도우는 3_내역서만들기.bat
# 브라우저에 화면이 뜬다. 이 PC 의 기록과 과제 파일을 맞춰 보고, 고른 것만 서버로 보낸다.
cd "$(dirname "$0")"
. ./_conda_setup.sh
python app/statement.py
