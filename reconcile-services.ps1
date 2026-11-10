[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
# Run with Windows PowerShell 5.1: the installed Guard validates Windows ACLs.
$mutex = New-Object Threading.Mutex($false, 'Local\MellowCodexServiceReconcile')
if (!$mutex.WaitOne(0)) { $mutex.Dispose(); exit 0 }
try {
  $root = 'E:\AI'
  $guardRoot = 'C:\ProgramData\MellowGuard'
  $env:LOCAL_AGENT_ROOT = $root
  $env:PYTHONUTF8 = '1'
  $env:OLLAMA_MODELS = "$root\models"
  $env:OLLAMA_HOST = '127.0.0.1:11434'
  $env:OLLAMA_NUM_PARALLEL = '1'
  $env:OLLAMA_MAX_LOADED_MODELS = '1'
  $env:OLLAMA_NO_CLOUD = '1'
  function Listening([int]$port) {
    $client = New-Object Net.Sockets.TcpClient
    try {
      $pending = $client.BeginConnect('127.0.0.1', $port, $null, $null)
      if (!$pending.AsyncWaitHandle.WaitOne(1500)) { return $false }
      $client.EndConnect($pending)
      return $true
    } catch { return $false } finally { $client.Dispose() }
  }
  function Archive-DeadReceipt([string]$path, [int]$port) {
    if (!(Test-Path -LiteralPath $path)) { return }
    if (Listening $port) { throw "Port $port is occupied; receipt retained" }
    $receipt = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
    $process = Get-Process -Id $receipt.pid -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq [long]$receipt.started_utc_ticks) {
      throw "Recorded process still exists; refusing duplicate launch on $port"
    }
    Move-Item -LiteralPath $path -Destination ($path + '.stale-' + [guid]::NewGuid().ToString('N'))
  }
  $failures = @()
  $components = @(
    @{port=11434;exe="$root\tools\ollama\ollama.exe";argv=@('serve');name='ollama'},
    @{port=8876;exe="$root\tools\hub-venv\Scripts\python.exe";argv=@('-m','uvicorn','hub.app:app','--host','127.0.0.1','--port','8876','--no-access-log');name='hub'},
    @{port=8897;exe="$root\tools\hub-venv\Scripts\python.exe";argv=@('-m','uvicorn','hub.mcp_gateway:app','--host','127.0.0.1','--port','8897','--no-access-log');name='gateway'}
  )
  foreach ($component in $components) {
    try {
      if (!(Listening $component.port)) {
        # A live process may still be starting; never create a second copy.
        $needle = if ($component.name -eq 'ollama') { 'ollama.exe' } elseif ($component.name -eq 'hub') { 'hub.app:app' } else { 'hub.mcp_gateway' }
        $existing = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($needle) -and $_.ExecutablePath -like "$root\tools\*" }
        if ($existing) { throw "$($component.name) process exists but is not listening; preserved for diagnosis" }
        Start-Process $component.exe -ArgumentList $component.argv -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$root\state\reconcile-$($component.name).stdout.log" -RedirectStandardError "$root\state\reconcile-$($component.name).stderr.log" | Out-Null
        for ($attempt=0; $attempt -lt 15 -and !(Listening $component.port); $attempt++) { Start-Sleep -Seconds 1 }
        if (!(Listening $component.port)) { throw "$($component.name) did not become ready" }
      }
    } catch { $failures += $_.Exception.Message }
  }
  try {
    $cfg = Get-Content -Raw "$guardRoot\current.json" | ConvertFrom-Json
    if ($cfg.release_id -notmatch '^[a-zA-Z0-9.-]+$') { throw 'Invalid Guard release ID' }
    $releasePath = Join-Path "$guardRoot\releases" $cfg.release_id
    . "$releasePath\scripts\common.ps1"
    $verifiedRelease = Read-GuardRelease $guardRoot
    $cfg = $verifiedRelease.config
    if (!(Listening ([int]$cfg.port))) {
      Archive-DeadReceipt "$guardRoot\state\process.json" ([int]$cfg.port)
      # start.ps1 also tries the gateway. An existing gateway is retained.
      try { & "$releasePath\scripts\start.ps1" -GuardHome $guardRoot } catch {
        if (!(Test-Path "$guardRoot\state\process.json")) { throw }
      }
    }
    if ($cfg.gateway_enabled -and !(Listening 8896)) {
      Archive-DeadReceipt "$guardRoot\state\gateway-process.json" 8896
      & "$releasePath\scripts\start-gateway.ps1" -GuardHome $guardRoot
    }
    if ($cfg.relay_enabled) {
      $env:MELLOW_GUARD_HOME = $guardRoot
      $env:MELLOW_GUARD_AUTH_FILE = [string]$cfg.auth_file
      Set-GuardRelayEnvironment -Config $cfg
      Push-Location $releasePath
      try {
        $relay = (& "$releasePath\venv\Scripts\python.exe" -m mellow_guard.relay reconcile | Out-String) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or !$relay.owned -or $relay.state -ne 'running') { throw 'Relay is not owned/running' }
      } finally { Pop-Location }
    }
  } catch { $failures += $_.Exception.Message }
  $report = @{time=(Get-Date).ToUniversalTime().ToString('o');listeners=@{};errors=@($failures)}
  foreach ($port in @(11434,8876,8897,8898,8896)) {
    $report.listeners["$port"] = Listening $port
    if (!$report.listeners["$port"]) { $failures += "Port $port is unavailable" }
  }
  $report.errors = @($failures)
  $report | ConvertTo-Json -Depth 5 | Set-Content "$root\state\service-reconcile.json" -Encoding UTF8
  if ($failures.Count) { throw ($failures -join '; ') }
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
