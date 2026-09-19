@echo off
chcp 65001 >nul
rem 기록을 그림으로 본다. ★ 이 파일을 더블클릭하면 된다.
cd /d "%~dp0"
call conda activate trace 2>nul
if errorlevel 1 (
  echo.
  echo   'trace' 환경이 없습니다. README 를 보세요.
  pause
  exit /b 1
)
python viewer.py
echo.
pause
