@echo off
setlocal EnableExtensions
echo MellowCodex R41 - INSTALL 1 of 3
echo All status and errors are written automatically to QA-LOGS in this shared folder.
pushd "%~dp0"
if errorlevel 1 (
  echo ERROR: VMware shared folder is unavailable.
  pause
  exit /b 20
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%CD%\R41-SUPPORT\INSTALL-1.ps1"
set "INSTALL_STATUS=%ERRORLEVEL%"
echo INSTALL-1 finished with exit code %INSTALL_STATUS%.
echo See QA-LOGS for the exact failure or success.
pause
popd
exit /b %INSTALL_STATUS%
