@echo off
chcp 65001 >nul
rem 윈도우에서 수집기를 켠다. ★ 이 파일을 더블클릭하면 된다.
cd /d "%~dp0"

call conda activate trace 2>nul
if errorlevel 1 (
  echo.
  echo   --------------------------------------------------------------
  echo   'trace' 환경이 없습니다. Anaconda Prompt 에서 처음 한 번만:
  echo.
  echo       conda create -n trace python=3.11 -y
  echo       conda activate trace
  echo       pip install pywin32 psutil
  echo   --------------------------------------------------------------
  echo.
  pause
  exit /b 1
)

python collector.py
echo.
pause
