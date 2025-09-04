@echo off
chcp 65001 >nul

echo ================================
echo    DEBUG ALL_IN_ONE.PY
echo ================================
echo.

REM Check if we're in the right directory
if not exist "run\all_in_one.py" (
    echo [ERROR] Khong tim thay file all_in_one.py trong thu muc run\
    echo [ERROR] Vui long chay script nay tu thu muc goc cua du an
    pause
    exit /b 1
)

REM Setup virtual environment
if exist "venv" (
    echo [INFO] Kich hoat virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] Khong tim thay virtual environment. Vui long chay run_video_processor.bat truoc
    pause
    exit /b 1
)

echo [INFO] Bat dau chay all_in_one.py voi log chi tiet...
echo [INFO] Nhan Ctrl+C de dung neu can
echo.

REM Run all_in_one.py with detailed logging
python run\all_in_one.py

if errorlevel 1 (
    echo.
    echo [ERROR] Xu ly video that bai! Kiem tra log o tren.
) else (
    echo.
    echo [INFO] Xu ly video thanh cong!
)

echo.
pause

