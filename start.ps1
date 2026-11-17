param([switch]$WithOpenCode,[switch]$SkipDesktop)
$ErrorActionPreference='Stop'
$agentRoot='E:\AI'
$python=Join-Path $agentRoot 'tools\hub-venv\Scripts\python.exe'
$env:LOCAL_AGENT_ROOT=$agentRoot
$env:OLLAMA_MODELS=Join-Path $agentRoot 'models'
$env:OLLAMA_HOST='127.0.0.1:11434'
$env:OLLAMA_NUM_PARALLEL='1'
$env:OLLAMA_MAX_LOADED_MODELS='1'
$env:OLLAMA_NO_CLOUD='1'
$env:UV_CACHE_DIR=Join-Path $agentRoot 'cache\uv'
$env:TEMP=Join-Path $agentRoot 'cache'
$env:TMP=$env:TEMP
$env:PATH="$agentRoot\tools\hub-venv\Scripts;$agentRoot\tools\ollama;$agentRoot\tools\opencode;$env:PATH"
$ps="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
Push-Location $PSScriptRoot
try {
  & $python -m hub.admin_startup --existing
  if($LASTEXITCODE -ne 0){throw 'Startup identity check failed; no services changed.'}
  & $python -m hub.power --manual-session
  if($LASTEXITCODE -ne 0){throw 'Could not record explicit manual start.'}
  & $ps -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'reconcile-services.ps1') -Action Start -Service all
  if($LASTEXITCODE -ne 0){throw 'Owned service startup needs attention; inspect service health.'}
  & $python -m hub.admin_startup --ready
  if($LASTEXITCODE -ne 0){throw 'Services are not verified ready. See the diagnostic above.'}
  if($WithOpenCode){
    try {Invoke-RestMethod 'http://127.0.0.1:4096/global/health' -TimeoutSec 2 | Out-Null}
    catch {
      $env:OPENCODE_CONFIG=Join-Path $PSScriptRoot 'opencode.json'
      $env:OPENCODE_SERVER_PASSWORD=(Get-Content -Raw "$agentRoot\state\hub.key").Trim()
      $env:XDG_DATA_HOME="$agentRoot\state\opencode"
      $env:XDG_CACHE_HOME="$agentRoot\cache\opencode"
      $env:OPENCODE_DISABLE_DEFAULT_PLUGINS='true'
      Start-Process "$agentRoot\tools\opencode\opencode.exe" -ArgumentList 'serve','--hostname','127.0.0.1','--port','4096' -WorkingDirectory "$agentRoot\repos\sandbox" -WindowStyle Hidden -RedirectStandardOutput "$agentRoot\state\opencode.stdout.log" -RedirectStandardError "$agentRoot\state\opencode.stderr.log" | Out-Null
    }
  }
  if(!$SkipDesktop){
    Start-Process "$agentRoot\tools\hub-venv\Scripts\pythonw.exe" -ArgumentList '-m','hub.desktop_app','--background' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
  }
  Write-Output 'MellowCodex ready: ordinary-user Hub/Gateway and verified protected OwnerBroker.'
} finally {Pop-Location}
