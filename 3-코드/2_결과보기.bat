@echo off
chcp 65001 >nul
REM Trace 테스트 2/2 — 가장 최근 세션을 session.json 으로 바꾸고 뷰어 열기
cd /d "%~dp0"
.venv\Scripts\python.exe core\derive.py "data\events-*.jsonl" --out data\session.json
if errorlevel 1 ( pause & exit /b )
echo.
echo [Trace] 뷰어가 열립니다. data\session.json 을 뷰어에 끌어다 놓으세요.
start "" ui\viewer.html
start "" data
pause
