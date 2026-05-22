@echo off
set VIVIAN_LAUNCH_DIR=%CD%
cd /d "C:\Users\admin\vivian_cli"
python cli_main.py --cwd "%VIVIAN_LAUNCH_DIR%" %*
