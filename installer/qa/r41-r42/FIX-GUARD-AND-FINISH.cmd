@echo off
setlocal EnableExtensions
echo ========================================
echo MellowCodex VMware GUARD ACL repair + Stage3 final verification
echo INSTALL-1 and INSTALL-2 remain untouched and verified.
echo Windows UAC will request administrator credentials ONLY for scoped Guard immutable release ACL.
echo The rest runs as your original ordinary Windows account.
echo All new diagnostic results are saved into QA-LOGS automatically.
echo ========================================
pushd "%~dp0"
if errorlevel 1 goto NO_SHARE
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%CD%\R41-SUPPORT\GUARD-ACL-REPAIR.ps1"
if errorlevel 1 goto REPAIR_FAILED
echo Scoped Guard read-access repair verified. Continuing Stage 3 in ordinary account.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%CD%\R41-SUPPORT\INSTALL-3.ps1"
if errorlevel 1 goto STAGE3_FAILED
echo INSTALL-3 PASS. Review QA-LOGS to confirm final runtime, UI and service health.
pause
popd
exit /b 0
:REPAIR_FAILED
echo Guard ACL repair failed. Stage3 was NOT run. Detailed errors are saved in QA-LOGS.
pause
popd
exit /b 31
:STAGE3_FAILED
echo Guard ACL repair passed, but Stage3 runtime verification failed. See QA-LOGS.
pause
popd
exit /b 32
:NO_SHARE
echo Shared folder is unavailable. Nothing was changed.
pause
exit /b 20
