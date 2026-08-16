@echo off
:: BR JARVIS MK40.2+ -- Environment Setup Script
:: Detects Python, creates .venv, installs all requirements
:: Run once after cloning: setup_env.bat

setlocal EnableDelayedExpansion
title BR JARVIS MK40.2+ -- Environment Setup

echo.
echo  ========================================================
echo   BR JARVIS MK40.2+ -- Environment Setup
echo  ========================================================
echo.

:: Find Python (prefer stable 3.12, also try 3.11, 3.13, 3.10, 3.14)
set PYTHON_CMD=

for %%V in (3.12 3.11 3.13 3.10 3.14) do (
    if "!PYTHON_CMD!"=="" (
        py -%%V --version >nul 2>&1
        if !errorlevel!==0 (
            set PYTHON_CMD=py -%%V
            echo [OK] Found Python %%V
        )
    )
)

if "!PYTHON_CMD!"=="" (
    python --version >nul 2>&1
    if !errorlevel!==0 (
        set PYTHON_CMD=python
        echo [OK] Found Python (system default)
    ) else (
        echo [ERR] Python not found. Install from https://python.org
        pause & exit /b 1
    )
)

echo [INFO] Using: !PYTHON_CMD!
echo.

:: Create virtual environment
if exist .venv (
    echo [SKIP] .venv already exists. Delete it to force reinstall.
) else (
    echo [INFO] Creating .venv...
    !PYTHON_CMD! -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERR] Failed to create .venv
        pause & exit /b 1
    )
    echo [OK] .venv created
)

:: Activate venv
call .venv\Scripts\activate.bat

:: Upgrade pip
echo.
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install requirements
echo [INFO] Installing requirements.txt...
pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [WARN] Some packages failed. Retrying with --no-deps for known-good...
    pip install -r requirements.txt --no-deps 2>nul
)

:: Install fpdf2 separately (sometimes conflicts)
pip install fpdf2>=2.7.0 --quiet 2>nul

set /p INSTALL_DEV="Do you want to install development/testing dependencies (requirements-dev.txt)? (y/n): "
if /i "!INSTALL_DEV!"=="y" (
    echo [INFO] Installing requirements-dev.txt...
    pip install -r requirements-dev.txt
)


:: Copy .env.template -> .env if not present
if not exist .env (
    if exist .env.template (
        copy .env.template .env >nul
        echo [OK] .env created from template. Edit it to add your API keys.
    )
) else (
    echo [SKIP] .env already exists
)

echo.
echo  ========================================================
echo   Setup complete!
echo   Activate venv: .venv\Scripts\activate.bat
echo   Run JARVIS:    python start.py
echo   Run Floating:  python start.py floating
echo   Run Web:       python start.py web
echo  ========================================================
echo.
pause
