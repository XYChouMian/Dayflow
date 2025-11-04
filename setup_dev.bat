@echo off
echo Setting up Dayflow development environment...
echo.

REM Check if venv exists, create if not
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created.
    echo.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies!
    pause
    exit /b 1
)

REM Install package in editable mode
echo Installing Dayflow in editable mode...
pip install -e .
if errorlevel 1 (
    echo Failed to install package!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo You can now run Dayflow using:
echo   run.bat
echo.
echo Or directly:
echo   venv\Scripts\python -m dayflow.main
echo.
pause
