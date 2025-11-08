@echo off
echo ========================================
echo FFmpeg Automatic Installer for Dayflow
echo ========================================
echo.

REM Create tools directory
set TOOLS_DIR=%~dp0tools
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

REM Check if ffmpeg already exists
if exist "%TOOLS_DIR%\ffmpeg\bin\ffmpeg.exe" (
    echo FFmpeg already installed!
    echo Location: %TOOLS_DIR%\ffmpeg\bin
    echo.
    goto :add_to_path
)

echo Downloading FFmpeg...
echo This may take a few minutes...
echo.

REM Download FFmpeg using PowerShell
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%TOOLS_DIR%\ffmpeg.zip'}"

if not exist "%TOOLS_DIR%\ffmpeg.zip" (
    echo.
    echo Download failed!
    echo Please manually download from: https://ffmpeg.org/download.html
    pause
    exit /b 1
)

echo.
echo Extracting FFmpeg...
powershell -Command "& {Expand-Archive -Path '%TOOLS_DIR%\ffmpeg.zip' -DestinationPath '%TOOLS_DIR%' -Force}"

REM Find and rename the extracted folder
for /d %%i in ("%TOOLS_DIR%\ffmpeg-*") do (
    move "%%i" "%TOOLS_DIR%\ffmpeg" >nul 2>&1
)

REM Clean up
del "%TOOLS_DIR%\ffmpeg.zip"

echo.
echo FFmpeg installed successfully!
echo Location: %TOOLS_DIR%\ffmpeg\bin
echo.

:add_to_path
echo ========================================
echo Adding FFmpeg to PATH
echo ========================================
echo.

REM Add to user PATH (no admin required)
set FFMPEG_PATH=%TOOLS_DIR%\ffmpeg\bin

REM Get current user PATH
for /f "usebackq tokens=2,*" %%A in (`reg query "HKCU\Environment" /v PATH 2^>nul`) do set CURRENT_PATH=%%B

REM Check if already in PATH
echo %CURRENT_PATH% | find /i "%FFMPEG_PATH%" >nul
if %errorlevel%==0 (
    echo FFmpeg is already in PATH!
    goto :verify
)

REM Add to PATH
if defined CURRENT_PATH (
    setx PATH "%CURRENT_PATH%;%FFMPEG_PATH%"
) else (
    setx PATH "%FFMPEG_PATH%"
)

echo FFmpeg added to PATH!
echo.
echo IMPORTANT: You need to restart your terminal/command prompt
echo for the PATH changes to take effect.
echo.

:verify
echo ========================================
echo Verifying Installation
echo ========================================
echo.

"%FFMPEG_PATH%\ffmpeg.exe" -version
if %errorlevel%==0 (
    echo.
    echo ========================================
    echo FFmpeg installation complete! ✓
    echo ========================================
    echo.
    echo You can now run Dayflow!
) else (
    echo.
    echo Verification failed. Please restart your terminal.
)

echo.
pause
