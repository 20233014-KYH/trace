@echo off
chcp 65001 >nul
REM Trace 테스트 1/2 — 수집기 켜기 (서버 없이 로컬 파일에만 기록)
cd /d "%~dp0"
if not exist .venv (
  echo [Trace] 가상환경 만드는 중... (처음 한 번, 1~2분)
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r collector\requirements.txt
)
echo.
echo [Trace] 기록 시작. 이 창을 켜둔 채 20분쯤 평소처럼 작업하세요.
echo         (PDF 읽기 - 코드/문서 작성 - AI에 묻기 - 답 붙여넣기 - 고치기)
echo         끝나면 이 창에서 Ctrl+C  ->  2_결과보기.bat
echo.
.venv\Scripts\python.exe collector\collector.py --dry-run
pause
