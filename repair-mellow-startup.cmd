@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\AI\repos\local-agent-hub\repair-mellow-startup.ps1"
if errorlevel 1 (echo Repair failed. Review E:\AI\state\service-reconcile.json & pause & exit /b 1)
echo Repair succeeded.
pause