#!/bin/bash
# 이 맥의 "시험 서버" 를 켠다 (맥 · ★ 더블클릭). 127.0.0.1:5000 · 기록은 이 맥의 server/trace.db (SQLite) 에만.
# ★ 0_서버시작.command 와 다르다 — 그건 server/.env 가 있으면 인터넷 서버의 DB(Supabase)에 붙는다.
#   Trace 앱을 "이 PC 의 시험 서버" 로 쓸 때(시험 계정 · 시험 기록)는 이 파일로 켠다. 창을 닫으면 서버도 꺼진다.
cd "$(dirname "$0")"
. ./_conda_setup.sh
export TRACE_PORT=5000
export TRACE_DB_URL="sqlite:///$(pwd)/server/trace.db"
python server/app.py
echo ""
read -n 1 -s -r -p "  아무 키나 누르면 창이 닫힙니다..."
