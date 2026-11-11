param([switch]$WithOpenCode,[switch]$SkipDesktop)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try { & 'E:\AI\tools\hub-venv\Scripts\python.exe' -m hub.power --manual-session; if ($LASTEXITCODE -ne 0) { throw 'Could not record explicit manual start' } } finally { Pop-Location }
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\reconcile-services.ps1"
if ($LASTEXITCODE -ne 0) { Write-Warning 'Service reconciliation needs attention; see E:\AI\state\service-reconcile.json' }
$agentRoot = 'E:\AI'
$env:LOCAL_AGENT_ROOT = $agentRoot
$env:OLLAMA_MODELS = "$agentRoot\models"
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_NO_CLOUD = '1'
$env:UV_CACHE_DIR = "$agentRoot\cache\uv"
$env:TEMP = "$agentRoot\cache"
$env:TMP = "$agentRoot\cache"
$env:PATH = "$agentRoot\tools\hub-venv\Scripts;$agentRoot\tools\ollama;$agentRoot\tools\opencode;$env:PATH"
function Test-AgentEndpoint($url) {
  try { Invoke-RestMethod -Uri $url -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}
Push-Location $PSScriptRoot
try {
  & "$agentRoot\tools\hub-venv\Scripts\python.exe" -m hub.admin_startup
  if ($LASTEXITCODE -eq 75) {
    Write-Output 'Updating background agent services. Approve the Windows administrator prompt to continue.'
    $restartArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'))
    if ($SkipDesktop) { $restartArgs += '-SkipDesktop' }
    if ($WithOpenCode) { $restartArgs += '-WithOpenCode' }
    try {
      $restart = Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $restartArgs -Wait -PassThru
    } catch { throw 'Windows administrator approval was canceled or unavailable. The update was not applied; existing tasks were not stopped.' }
    if ($restart.ExitCode -ne 0) { throw 'Background service update failed. Existing tasks may need to finish before retrying.' }
    exit 0
  }
  if ($LASTEXITCODE -ne 0) { throw 'Could not align agent service permissions; startup stopped.' }
} finally { Pop-Location }
if (!(Test-AgentEndpoint 'http://127.0.0.1:11434/api/version')) {
  $process = Start-Process "$agentRoot\tools\ollama\ollama.exe" -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$agentRoot\state\ollama.stdout.log" -RedirectStandardError "$agentRoot\state\ollama.stderr.log"
  $process.Id | Set-Content "$agentRoot\state\ollama.pid"
}
if (!(Test-AgentEndpoint 'http://127.0.0.1:8876/')) {
  $process = Start-Process "$agentRoot\tools\hub-venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','hub.app:app','--host','127.0.0.1','--port','8876','--no-access-log' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "$agentRoot\state\hub.stdout.log" -RedirectStandardError "$agentRoot\state\hub.stderr.log"
  $process.Id | Set-Content "$agentRoot\state\hub.pid"
}
if ($WithOpenCode -and !(Test-AgentEndpoint 'http://127.0.0.1:4096/global/health')) {
  $env:OPENCODE_CONFIG = "$PSScriptRoot\opencode.json"
  $env:OPENCODE_SERVER_PASSWORD = (Get-Content -Raw "$agentRoot\state\hub.key").Trim()
  $env:XDG_DATA_HOME = "$agentRoot\state\opencode"
  $env:XDG_CACHE_HOME = "$agentRoot\cache\opencode"
  $env:OPENCODE_DISABLE_DEFAULT_PLUGINS = 'true'
  $process = Start-Process "$agentRoot\tools\opencode\opencode.exe" -ArgumentList 'serve','--hostname','127.0.0.1','--port','4096' -WorkingDirectory "$agentRoot\repos\sandbox" -WindowStyle Hidden -PassThru -RedirectStandardOutput "$agentRoot\state\opencode.stdout.log" -RedirectStandardError "$agentRoot\state\opencode.stderr.log"
  $process.Id | Set-Content "$agentRoot\state\opencode.pid"
}
if (!$SkipDesktop -and !(Test-AgentEndpoint 'http://127.0.0.1:9223/json/version')) {
  Start-Process "$agentRoot\tools\hub-venv\Scripts\pythonw.exe" -ArgumentList '-m','hub.desktop_app','--background' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
}
Write-Output 'Local Agent services and browser run in background. E:\AI\Start-Local-Agent.cmd opens the interface.'
