@echo off
setlocal EnableExtensions EnableDelayedExpansion

title BR-JARVIS Environment Setup
cd /d "%~dp0"

echo ========================================================
echo   BR-JARVIS reproducible Windows environment setup
echo ========================================================

set "PYTHON_CMD="
for %%V in (3.12 3.11 3.13) do (
    if not defined PYTHON_CMD (
        py -%%V --version >nul 2>&1
        if !errorlevel! equ 0 set "PYTHON_CMD=py -%%V"
    )
)
if not defined PYTHON_CMD (
    python --version >nul 2>&1 || (
        echo [ERROR] Python 3.11-3.13 is required.
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

echo [INFO] Using !PYTHON_CMD!
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating .venv...
    !PYTHON_CMD! -m venv .venv || exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel || exit /b 1

set "INSTALL_TARGET=.[documents,web,llm-backends,windows]"
if /i "%~1"=="--dev" set "INSTALL_TARGET=.[documents,web,llm-backends,windows,dev]"

echo [INFO] Installing %INSTALL_TARGET% from pyproject.toml...
"%VENV_PY%" -m pip install -e "%INSTALL_TARGET%" || (
    echo [ERROR] Dependency installation failed. No --no-deps fallback was attempted.
    exit /b 1
)
"%VENV_PY%" -m pip check || exit /b 1

if not exist ".env" (
    copy /y ".env.template" ".env" >nul || exit /b 1
    echo [ACTION REQUIRED] .env was created. Replace the JARVIS_SERVER_API_KEY placeholder.
)

echo [OK] Environment ready.
echo      Optional voice/desktop bundle: "%VENV_PY%" -m pip install -e ".[voice,automation]"
echo      Run: .venv\Scripts\python.exe start.py status
echo      Web: .venv\Scripts\python.exe start.py web
exit /b 0
