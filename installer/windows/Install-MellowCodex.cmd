@echo off
setlocal
title MellowCodex Setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-MellowCodex.ps1" %*
if errorlevel 1 (
 echo.
 echo Installation is incomplete. Read the error above and installer log.
 pause
 exit /b 1
)
echo.
echo Installation complete.
pause