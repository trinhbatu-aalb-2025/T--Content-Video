@echo off
chcp 65001 >nul

echo ================================
echo    SO SANH CAC CACH CHAY
echo ================================
echo.

echo [TEST 1] Chay truc tiep tu thu muc run:
echo ----------------------------------------
cd run
python all_in_one.py --help
echo.

echo [TEST 2] Chay tu thu muc goc:
echo ----------------------------------------
cd ..
python run\all_in_one.py --help
echo.

echo [TEST 3] Chay voi virtual environment:
echo ----------------------------------------
call venv\Scripts\activate.bat
python run\all_in_one.py --help
echo.

pause

