@echo off
title NotiSync Launcher
echo ============================================================
echo               Starting NotiSync Service...
echo ============================================================
cd /d "%~dp0"
.venv\Scripts\python.exe run.py
pause
