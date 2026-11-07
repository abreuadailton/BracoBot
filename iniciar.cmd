@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao encontrado. Execute instalar.cmd primeiro.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m bracobot %*
if errorlevel 1 pause
