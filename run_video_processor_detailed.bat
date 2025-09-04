@echo off
chcp 65001 >nul

REM Video Processor Runner for Windows - Detailed Log
REM Script nay chay tu thu muc goc cua du an

echo ================================
echo    VIDEO PROCESSOR RUNNER - DETAILED
echo ================================
echo.

REM Check if we're in the right directory
echo [INFO] Kiem tra cau truc du an...
if not exist "run\all_in_one.py" (
    echo [ERROR] Khong tim thay file all_in_one.py trong thu muc run\
    echo [ERROR] Vui long chay script nay tu thu muc goc cua du an
    pause
    exit /b 1
)
echo [INFO] Cau truc du an hop le!
echo.

REM Check Python
echo [INFO] Kiem tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python khong duoc tim thay. Vui long cai dat Python.
    pause
    exit /b 1
)
echo [INFO] Python da san sang!
echo.

REM Setup virtual environment
echo [INFO] Kiem tra virtual environment...
if not exist "venv" (
    echo [WARNING] Khong tim thay virtual environment. Tao moi...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Khong the tao virtual environment
        pause
        exit /b 1
    )
)

echo [INFO] Kich hoat virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Khong the kich hoat virtual environment
    pause
    exit /b 1
)
echo [INFO] Virtual environment da duoc kich hoat!
echo.

REM Install requirements
echo [INFO] Kiem tra dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Khong the cai dat dependencies
        pause
        exit /b 1
    )
    echo [INFO] Dependencies OK!
) else (
    echo [WARNING] Khong tim thay requirements.txt
)
echo.

REM Show menu
echo ================================
echo    CHON LUA CHON:
echo ================================
echo.
echo 1. Chay video tu folder mac dinh (log chi tiet)
echo 2. Chay video tu folder tuy chon (log chi tiet)
echo 3. Thoat
echo.

:choice_loop
set /p "choice=Nhap lua chon cua ban (1-3): "

if "%choice%"=="1" goto run_default
if "%choice%"=="2" goto run_custom
if "%choice%"=="3" goto exit_script

echo [ERROR] Lua chon khong hop le. Vui long chon 1, 2 hoac 3.
goto choice_loop

:run_default
echo.
echo ================================
echo    CHAY VIDEO TU FOLDER MAC DINH
echo ================================
echo.
echo [INFO] Bat dau xu ly video voi log chi tiet...
echo [INFO] Se hien thi:
echo [INFO] - So luong video trong folder
echo [INFO] - Ten video dang xu ly
echo [INFO] - Tien trinh xu ly (%%)
echo [INFO] - Trang thai tung buoc
echo.
python run\all_in_one.py
if errorlevel 1 (
    echo [ERROR] Xu ly video that bai!
    pause
    exit /b 1
)
echo [INFO] Xu ly video thanh cong!
goto end_script

:run_custom
echo.
echo ================================
echo    CHAY VIDEO TU FOLDER TUY CHON
echo ================================
echo.
echo [INFO] Nhap Google Drive link hoac Folder ID:
set /p "input_link="

REM Extract folder ID from Google Drive link
set "folder_id=%input_link%"
if "%input_link%"=="" (
    echo [ERROR] Khong duoc de trong
    pause
    exit /b 1
)

REM Check if it's a Google Drive link
echo %input_link% | findstr /c:"drive.google.com" >nul
if %errorlevel% equ 0 (
    echo [INFO] Phat hien Google Drive link, dang trich xuat Folder ID...
    REM Extract folder ID from Google Drive link using PowerShell for better accuracy
    for /f "delims=" %%a in ('powershell -Command "if ('%input_link%' -match 'folders/([a-zA-Z0-9_-]+)') { $matches[1] } else { '%input_link%' }"') do set "folder_id=%%a"
    echo [INFO] Da trich xuat Folder ID: %folder_id%
) else (
    echo [INFO] Su dung input truc tiep lam Folder ID
)

echo [INFO] Folder ID: %folder_id%
echo [INFO] Bat dau xu ly video tu folder: %folder_id% voi log chi tiet...
echo [INFO] Se hien thi:
echo [INFO] - So luong video trong folder
echo [INFO] - Ten video dang xu ly
echo [INFO] - Tien trinh xu ly (%%)
echo [INFO] - Trang thai tung buoc
echo.

REM Note: Custom folder ID will be passed directly to Python script

REM Run with custom folder ID
python run\all_in_one.py --custom-folder %folder_id%
if errorlevel 1 (
    echo [ERROR] Xu ly video that bai!
    pause
    exit /b 1
)
echo [INFO] Xu ly video thanh cong!
goto end_script

:exit_script
echo [INFO] Tam biet!
exit /b 0

:end_script
echo.
echo [INFO] Hoan thanh!
pause

