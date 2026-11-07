@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Instale Python 3.12 ou superior e tente novamente.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 (
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -c "import tiktoken; tiktoken.get_encoding('o200k_base'); from bracobot.policy import Settings; Settings.load(); print('BracoBot pronto. Execute iniciar.cmd ou demonstracao.cmd.')"
if errorlevel 1 pause
