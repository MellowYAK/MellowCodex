@echo off
setlocal EnableExtensions
echo MellowCodex VM Guard diagnostics. READ ONLY, no service changes.
pushd "%~dp0"
if errorlevel 1 goto NO_SHARE
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%CD%\R41-SUPPORT\GUARD-DIAGNOSE.ps1"
set "DIAG_RC=%ERRORLEVEL%"
echo Diagnostic exit code: %DIAG_RC%
echo Check QA-LOGS for GUARD-DIAGNOSTICS-LATEST.json and GUARD-DIAGNOSTICS-*.log
pause
popd
exit /b %DIAG_RC%
:NO_SHARE
echo VMware shared folder is unavailable.
pause
exit /b 20
