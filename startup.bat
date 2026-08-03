@echo off
title BR JARVIS
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
)

:: Select stable Python version (3.12 preferred — avoids Python 3.14 alpha crashes)
set PYEXE=python
py -3.12 --version >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    set PYEXE=py -3.12
    goto :launch
)
py -3.13 --version >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    set PYEXE=py -3.13
    goto :launch
)
py -3.11 --version >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    set PYEXE=py -3.11
    goto :launch
)
python --version >nul 2>&1
if "%ERRORLEVEL%" NEQ "0" (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.12 and run: py -3.12 -m pip install -r requirements.txt
    pause
    exit /b 1
)

:launch
echo [BR] Using Python: %PYEXE%

:: Silent mode (auto-startup) - launch voice assistant directly, no menu
if "%~1"=="--silent" (
    echo [BR] Auto-startup - launching voice assistant...
    %PYEXE% ui_mark.py
    goto :end
)

:: Voice-safe mode: run audio diagnostics first, then voice assistant
if "%~1"=="--voice-safe" (
    echo [BR] Running audio diagnostics...
    %PYEXE% start.py audio
    echo [BR] Launching voice assistant...
    %PYEXE% ui_mark.py
    goto :end
)

:: Menu / Interactive mode - show launcher menu
if "%~1"=="--menu" (
    %PYEXE% start.py
    goto :end
)
if "%~1"=="--interactive" (
    %PYEXE% start.py
    goto :end
)

:: If mode arguments were passed, use them directly
if "%~1" NEQ "" (
    %PYEXE% start.py %*
    goto :end
)

:: Default execution - Launch Cyberpunk HUD Voice Assistant directly
echo [BR] Launching BR JARVIS Cyberpunk HUD...
%PYEXE% ui_mark.py

:end
:: Keep window open if it crashes
if "%ERRORLEVEL%" NEQ "0" (
    echo.
    echo [ERROR] BR JARVIS exited with code %ERRORLEVEL%
    echo Press any key to close...
    pause >nul
)
