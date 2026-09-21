@echo off
chcp 65001 >nul
REM (선택) 계약 ③ 참고 서버. 수집기가 여기로 batch 를 보내고, 서버는 체인을 재계산해 대조한다.
cd /d "%~dp0"
if not exist .venv ( echo 먼저 1_기록시작.bat 을 한 번 실행해 .venv 를 만드세요 & pause & exit /b )
.venv\Scripts\python.exe collector\dev_receiver.py
pause
