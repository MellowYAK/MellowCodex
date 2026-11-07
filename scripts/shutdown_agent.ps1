$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'))
    exit
}
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
& 'E:\AI\tools\hub-venv\Scripts\python.exe' (Join-Path $PSScriptRoot 'shutdown_agent.py') --execute
if ($LASTEXITCODE -eq 0) {
    Write-Host 'MellowCodex stopped. Managed models unloaded. Shared Ollama and other applications preserved.' -ForegroundColor Green
} else {
    Write-Host 'Shutdown incomplete. See the errors above and E:\AI\state\last-admin-shutdown.json' -ForegroundColor Red
}
Read-Host 'Press Enter to close'
