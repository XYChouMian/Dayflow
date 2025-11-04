@echo off
echo Starting Dayflow Windows...
echo.

REM Check if venv exists
if not exist "venv\" (
    echo Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Set PYTHONPATH to include src directory
set PYTHONPATH=%~dp0src;%PYTHONPATH%

REM Activate venv and run
call venv\Scripts\activate.bat
python src\dayflow\main.py

pause
