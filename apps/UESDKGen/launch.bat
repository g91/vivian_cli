@echo off
cd /d "%~dp0..\.."
python apps\UESDKGen\UESDKGen.py %*
