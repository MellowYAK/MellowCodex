$ErrorActionPreference = 'Stop'
$root = 'E:\AI\repos\local-agent-hub'
& (Join-Path $root 'reconcile-services.ps1') -Action Start -Service all
if ($LASTEXITCODE -ne 0) { throw "Start failed with exit code $LASTEXITCODE" }
$ports = @(8876,8897,8898,8896)
$missing = @($ports | Where-Object { -not (Get-NetTCPConnection -State Listen -LocalPort $_ -ErrorAction SilentlyContinue) })
if ($missing.Count -gt 0) {
  Write-Host ('Missing service ports: ' + ($missing -join ', '))
  Get-Content 'E:\AI\state\service-reconcile.json' -ErrorAction SilentlyContinue
  exit 2
}
Write-Host 'All four local service ports are listening.'