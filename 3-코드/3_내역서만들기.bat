@echo off
chcp 65001 >nul
REM AI 활용 내역서 만들기 — 브라우저에 화면이 뜬다. 이 PC 의 기록과 과제 파일을 맞춰 보고, 고른 것만 서버로 보낸다
cd /d "%~dp0"
.venv\Scripts\python.exe app\statement.py
pause
