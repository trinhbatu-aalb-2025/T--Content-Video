@echo off
chcp 65001 >nul

REM Video Processor Runner - Windows Wrapper
REM Script này chạy từ thư mục gốc của dự án

echo ================================
echo VIDEO PROCESSOR RUNNER - WINDOWS
echo ================================
echo.

REM Kiểm tra xem có đang ở thư mục gốc không
if not exist "run\all_in_one.py" (
    echo [ERROR] Không tìm thấy file all_in_one.py trong thư mục run\
    echo [ERROR] Vui lòng chạy script này từ thư mục gốc của dự án
    pause
    exit /b 1
)

REM Chạy script Windows
echo [INFO] Đang chạy Video Processor Runner cho Windows...
echo.

REM Chạy PowerShell script nếu có PowerShell
powershell -Command "Get-Command powershell" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Sử dụng PowerShell script...
    powershell -ExecutionPolicy Bypass -File "video_processor_runners\windows\run_video_processor.ps1"
) else (
    echo [INFO] Sử dụng Batch script...
    call "video_processor_runners\windows\run_video_processor.bat"
)

echo.
echo [INFO] Hoàn thành!
pause



