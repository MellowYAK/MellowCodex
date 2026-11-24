[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$AgentRoot,
 [ValidateSet('Start','Stop','Status')][string]$Action='Start'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$AgentRoot=[IO.Path]::GetFullPath($AgentRoot).TrimEnd('\')
$repo=Join-Path $AgentRoot 'repos\local-agent-hub'
$python=Join-Path $AgentRoot 'tools\hub-venv\Scripts\python.exe'
$ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
if(!(Test-Path -LiteralPath $python)){throw "MellowCodex Python is missing: $python"}
if(!(Test-Path -LiteralPath (Join-Path $repo 'reconcile-services.ps1'))){throw "MellowCodex source missing: $repo"}
Push-Location $repo
try{
 if($Action -eq 'Start'){
  Write-Host 'Starting MellowCodex with existing owner checks and Guard supervision...' -ForegroundColor Cyan
  & $ps -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'start.ps1')
  if($LASTEXITCODE -ne 0){throw 'MellowCodex native Start failed; inspect its output and Guard status.'}
 }elseif($Action -eq 'Stop'){
  Write-Host 'Stopping ONLY MellowCodex owned Hub, MCP, Guard, gateway, relay and Ollama.' -ForegroundColor Yellow
  Write-Host 'The original Stop confirmation and service ownership checks remain in force.'
  & $ps -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'stop.ps1')
  if($LASTEXITCODE -ne 0){throw 'MellowCodex native Stop was blocked; see error above.'}
 }else{
  & $ps -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'reconcile-services.ps1') -Action Status -Service all
  if($LASTEXITCODE -ne 0){throw 'MellowCodex status probe failed'}
 }
}finally{Pop-Location}