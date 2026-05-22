@echo off
REM MemEdit Remote API Server — Windows launcher
REM Usage: launch_server.bat [--host 0.0.0.0] [--port 8765] [--token mysecret] [--device native]
REM
REM Install server deps first:
REM   pip install fastapi uvicorn

cd /d "%~dp0..\.."
python apps\MemEdit\server.py %*
pause
