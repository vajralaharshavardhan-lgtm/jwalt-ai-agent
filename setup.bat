@echo off
REM Double-click this file to set up the J-WALT AI agent -- no PowerShell
REM knowledge needed. This just launches setup.ps1 with the one PowerShell
REM flag (-ExecutionPolicy Bypass) that Windows needs to let a downloaded
REM script run for THIS command only; it does not change any system setting.
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

echo.
echo ============================================================
echo Setup finished. You can close this window, or press any key.
echo ============================================================
pause >nul
