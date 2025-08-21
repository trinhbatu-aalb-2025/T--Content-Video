@echo off
echo ========================================
echo Video to Audio Converter - Installer
echo ========================================
echo.

echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
) else (
    echo ✓ Python is installed
    python --version
)

echo.
echo [2/5] Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: FFmpeg not found!
    echo Please install FFmpeg using one of these methods:
    echo 1. Using Chocolatey: choco install ffmpeg
    echo 2. Download from: https://ffmpeg.org/download.html
    echo.
    echo After installing FFmpeg, restart this script
    pause
    exit /b 1
) else (
    echo ✓ FFmpeg is installed
    ffmpeg -version | findstr "ffmpeg version"
)

echo.
echo [3/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    echo ✓ Virtual environment created
)

echo.
echo [4/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [5/5] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo Installation completed!
echo ========================================
echo.
echo Next steps:
echo 1. Create Google Cloud Project
echo 2. Download credentials.json
echo 3. Update video_to_audio_converter.py with your File IDs
echo 4. Run: python video_to_audio_converter.py
echo.
echo See INSTALL_GUIDE.md for detailed instructions
echo.
pause 