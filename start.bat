@echo off
REM Launcher for Qwen3-TTS Studio (Windows)

setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

if not exist ".venv\.deps_installed" (
    echo [setup] Installing dependencies...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    echo. > .venv\.deps_installed
)

python main.py %*

endlocal
