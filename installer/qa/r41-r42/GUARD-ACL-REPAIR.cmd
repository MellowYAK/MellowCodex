@echo off
setlocal EnableExtensions
echo MellowCodex Guard scoped ACL repair for this VMware guest.
echo Stage1/Stage2 already PASS. This will request Windows UAC only for Guard release permissions.
pushd "%~dp0"
if errorlevel 1 goto BAD_SHARE
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%CD%\R41-SUPPORT\GUARD-ACL-REPAIR.ps1"
set "RC=%ERRORLEVEL%"
echo Guard ACL repair exit code %RC%.
echo Report: QA-LOGS\GUARD-ACL-REPAIR-LATEST.json
pause
popd
exit /b %RC%
:BAD_SHARE
echo Shared folder inaccessible
pause
exit /b 20
