@echo off
title BR
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

:: Check Python is available
python --version >nul 2>&1
if "%ERRORLEVEL%" NEQ "0" (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Silent mode (auto-startup) - launch voice assistant directly, no menu
if "%~1"=="--silent" (
    echo [BR] Auto-startup - launching voice assistant...
    python start.py voice
    goto :end
)

:: Voice-safe mode: run audio diagnostics first, then voice assistant
if "%~1"=="--voice-safe" (
    echo [BR] Running audio diagnostics...
    python start.py audio
    echo [BR] Launching voice assistant...
    python start.py voice
    goto :end
)

:: Menu / Interactive mode - show launcher menu
if "%~1"=="--menu" (
    python start.py
    goto :end
)
if "%~1"=="--interactive" (
    python start.py
    goto :end
)

:: If mode arguments were passed, use them directly
if "%~1" NEQ "" (
    python start.py %*
    goto :end
)

:: Default execution - Launch Voice Assistant directly
echo [BR] Launching BR Voice Assistant...
python start.py voice

:end
:: Keep window open if it crashes
if "%ERRORLEVEL%" NEQ "0" (
    echo.
    echo [ERROR] BR exited with code %ERRORLEVEL%
    echo Press any key to close...
    pause >nul
)
