@echo off
:: MemEdit DMA Memory Editor launcher
:: Run from the vivian_cli root directory

cd /d "%~dp0\..\.."
python apps\MemEdit\MemEdit.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: MemEdit exited with code %ERRORLEVEL%
    pause
)
