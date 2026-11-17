# Installer finalization. Run as the intended interactive user AFTER protected
# Guard and OwnerBroker packages have been installed by their owner workflow.
$ErrorActionPreference='Stop'
$python='E:\AI\tools\hub-venv\Scripts\python.exe'
Push-Location $PSScriptRoot
try{
 & $python -m hub.admin_startup --launcher
 if($LASTEXITCODE -ne 0){throw 'Run installation finalization as the intended ordinary Windows user.'}
 & $python -c "from hub.owner_broker import owner_status; import sys; sys.exit(0 if owner_status().get('server_identity_verified') is True else 3)"
 if($LASTEXITCODE -ne 0){throw 'OwnerBroker is not verified. Complete the protected owner installation first; no authorization settings were changed.'}
 & $python -c "from hub.power import settings, set_startup; s=settings(); print(set_startup(s['start_with_windows'], s['revision']))"
 if($LASTEXITCODE -ne 0){throw 'Logon task registration/readback failed.'}
 & (Join-Path $PSScriptRoot 'register-service-recovery.ps1') -NoStart
 & (Join-Path $PSScriptRoot 'register-mcp-shortcuts.ps1')
 Write-Output 'Startup tasks and ordinary-user desktop shortcuts registered. Start MellowCodex to verify readiness.'
}finally{Pop-Location}
