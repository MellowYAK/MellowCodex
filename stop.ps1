$ErrorActionPreference='Stop'
$python='E:\AI\tools\hub-venv\Scripts\python.exe'
$ps="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
Write-Host 'Stop MellowCodex and its managed services. Windows, Yak and the protected owner broker are not shut down.'
if((Read-Host 'Type STOP to confirm safe service shutdown') -cne 'STOP'){Write-Host 'Cancelled.';return}
Push-Location $PSScriptRoot
try{
  & $ps -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'reconcile-services.ps1') -Action Stop -Service all -ConfirmTasks -ResumeOnNextBoot
  if($LASTEXITCODE -ne 0){
    Write-Host 'Safe stop refused. No unverified process will be killed.' -ForegroundColor Yellow
    Write-Host 'If upgrading a legacy elevated installation, restart Windows from its Start menu and sign in normally. Do not run MellowCodex Start as administrator.' -ForegroundColor Yellow
    throw 'Stop was not verified. See the ownership or task blocker above.'
  }
  & $python -c "from hub.power import close_desktop; close_desktop()"
  if($LASTEXITCODE -ne 0){throw 'Managed services stopped, but desktop shutdown was not verified.'}
  Write-Host 'MellowCodex stopped. Use MellowCodex Start to resume.'
}finally{Pop-Location}
