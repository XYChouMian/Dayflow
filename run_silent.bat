@echo off
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

REM Activate venv and run with pythonw (no console window)
call venv\Scripts\activate.bat
start /B pythonw src\dayflow\main.py
