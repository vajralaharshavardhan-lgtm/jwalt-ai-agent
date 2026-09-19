@echo off
REM Double-click this file to run the J-WALT AI agent -- no PowerShell
REM knowledge needed. Runs the standard first live test (3 Dubai hotel
REM leads) after checking your .env keys and running both smoke tests.
REM
REM To pass options instead (dry run, a different objective, etc.), open
REM Command Prompt in this folder and run this file with arguments, e.g.:
REM     run-agent.bat -DryRun
REM     run-agent.bat -Objective "Find 5 Dubai retail companies opening new stores" -NonInteractive
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-agent.ps1" %*

echo.
echo ============================================================
echo Run finished. You can close this window, or press any key.
echo ============================================================
pause >nul
