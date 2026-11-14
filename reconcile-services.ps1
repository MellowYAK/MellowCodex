[CmdletBinding()]
param([ValidateSet('Start','Stop','Restart','Status','Reconcile')][string]$Action='Reconcile',[ValidateSet('mcp','all','hub','gateway','guard','guard_gateway','relay','ollama')][string]$Service='mcp',[switch]$ConfirmTasks,[switch]$PowerTransition)
$ErrorActionPreference = 'Stop'
# Run with Windows PowerShell 5.1: the installed Guard validates Windows ACLs.
$mutex = New-Object Threading.Mutex($false, 'Local\MellowCodexServiceReconcile')
$lockWaitMs = if ($Action -eq 'Reconcile') { 0 } else { 30000 }
if (!$mutex.WaitOne($lockWaitMs)) { $mutex.Dispose(); if ($Action -eq 'Reconcile') { exit 75 }; throw 'Another service operation is active' }
try {
  $root = 'E:\AI'
  $guardRoot = 'C:\ProgramData\MellowGuard'
  $pauseFile = "$root\state\mcp-manual-stop"
  $servicePause = "$root\state\service-manual-stop-$Service"
  Set-Location -LiteralPath $PSScriptRoot
  if ($Action -eq 'Status') {
    & "$root\tools\hub-venv\Scripts\python.exe" -m hub.service_health --status
    if ($LASTEXITCODE -ne 0) { throw 'Health inspection failed' }
    return
  }
  if ($Action -eq 'Reconcile' -and ((Test-Path $pauseFile) -or (Test-Path "$root\state\agent-manual-stop"))) { return }
  if ($PowerTransition) {
    if ($Action -ne 'Stop' -or $Service -ne 'all') { throw 'Transient power stop only supports Stop all' }
    & "$root\tools\hub-venv\Scripts\python.exe" -m hub.power --transition-required
    if ($LASTEXITCODE -ne 0) { throw 'No active owned power transition' }
  }
  if ($Action -eq 'Reconcile') {
    & "$root\tools\hub-venv\Scripts\python.exe" -m hub.power --recovery-allowed
    if ($LASTEXITCODE -eq 75) { return }
    if ($LASTEXITCODE -ne 0) { throw 'Recovery policy unavailable; no launch attempted' }
  }
  $confirmed = if ($ConfirmTasks) { 'true' } else { 'false' }
  Push-Location $PSScriptRoot
  try {
    & "$root\tools\hub-venv\Scripts\python.exe" -m hub.service_health --preflight $Action $Service $confirmed
    if ($LASTEXITCODE -ne 0) { throw 'Preflight rejected; no service changed' }
  } finally { Pop-Location }
  $dependents = switch ($Service) {
    'guard' { @('guard','guard_gateway','relay') }
    'guard_gateway' { @('guard_gateway','relay') }
    default { @($Service) }
  }
  $wanted = switch ($Service) {
    'mcp' { @('hub','gateway','guard','guard_gateway','relay') }
    'all' { @('hub','gateway','guard','guard_gateway','relay','ollama') }
    'relay' { @('hub','gateway','guard','guard_gateway','relay') }
    'guard' { @('guard','guard_gateway','relay') }
    'guard_gateway' { @('guard','guard_gateway','relay') }
    'gateway' { @('hub','gateway') }
    default { @($Service) }
  }
  if ($Action -in @('Stop','Restart')) {
    if (!$PowerTransition -and $Service -in @('mcp','all')) { Set-Content $pauseFile 'MCP intentionally stopped by owner' }
    if (!$PowerTransition -and $Service -eq 'all') { Set-Content "$root\state\agent-manual-stop" 'All agent services intentionally stopped' }
    if (!$PowerTransition -and $Service -notin @('mcp','all')) { foreach($item in $dependents) { Set-Content "$root\state\service-manual-stop-$item" 'Service intentionally stopped by owner' } }
    $stopArgs=@("$PSScriptRoot\scripts\stop-mcp-transports.py",'--service',$Service)
    if($ConfirmTasks){$stopArgs+='--confirm-tasks'}
    & "$root\tools\hub-venv\Scripts\python.exe" @stopArgs
    if ($LASTEXITCODE -ne 0) { throw 'MCP stop incomplete; automatic restart remains paused. See output.' }
    if ($Action -eq 'Stop') {
      @{time=(Get-Date).ToUniversalTime().ToString('o');state='stopped_by_owner';service=$Service} | ConvertTo-Json | Set-Content "$root\state\service-reconcile.json"
      return
    }
  }
  if ($Action -in @('Start','Restart')) {
    if ($Service -in @('mcp','all') -and (Test-Path $pauseFile)) { Remove-Item -LiteralPath $pauseFile }
    foreach($item in @($wanted)+@($dependents)) { Remove-Item "$root\state\service-manual-stop-$item" -ErrorAction SilentlyContinue }
    if ($Service -eq 'all') {
      Remove-Item "$root\state\agent-manual-stop" -ErrorAction SilentlyContinue
      Get-ChildItem "$root\state\service-manual-stop-*" -ErrorAction SilentlyContinue | Remove-Item
    }
  }

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
  # One owner after Windows logon: Guard starts Hub+Gateway as a signed pair.
  # Both scheduled recovery tasks already share the reconciliation mutex.
  # A legacy or partially running pair is preserved, never adopted or killed.
  $guardPairWanted = ($Action -in @('Start','Reconcile')) -and
                     ('hub' -in $wanted -or 'gateway' -in $wanted)
  if ($guardPairWanted) {
    $hubListening = Listening 8876
    $gatewayListening = Listening 8897
    $hubPaused = Test-Path "$root\state\service-manual-stop-hub"
    $gatewayPaused = Test-Path "$root\state\service-manual-stop-gateway"
    if (!$hubListening -and !$gatewayListening -and !$hubPaused -and !$gatewayPaused) {
      $lastAttempt = "$root\state\guard-autostart-last-attempt.json"
      $allowAttempt = $true
      if (Test-Path $lastAttempt) {
        try {
          $record = Get-Content $lastAttempt -Raw | ConvertFrom-Json
          if (([DateTime]::UtcNow - [DateTime]::Parse($record.time).ToUniversalTime()).TotalSeconds -lt 90) {
            $allowAttempt = $false
          }
        } catch {}
      }
      if ($allowAttempt) {
        @{time=([DateTime]::UtcNow.ToString('o'));action='Guard-owned Hub pair start'} |
          ConvertTo-Json | Set-Content -LiteralPath $lastAttempt -Encoding UTF8
        try {
          & "$root\tools\hub-venv\Scripts\python.exe" "$PSScriptRoot\scripts\guard_owned_autostart.py" --start
          if ($LASTEXITCODE -ne 0) { throw 'Guard-owned Hub pair health verification failed' }
        } catch { $failures += ('Guard-owned startup failed: '+$_.Exception.Message) }
      } else { $failures += 'Guard-owned startup cooldown (90 seconds); no duplicate attempt' }
    } elseif ($hubListening -ne $gatewayListening) {
      $failures += 'Partial Hub/Gateway pair: owner intervention required; no legacy duplicate startup'
    }
  }
  foreach ($component in $components) {
    if ($guardPairWanted -and $component.name -in @('hub','gateway')) {
      if (!(Listening $component.port) -and !(Test-Path "$root\state\service-manual-stop-$($component.name)")) {
        $failures += "$($component.name) not listening after Guard-owned start; legacy launch forbidden"
      }
      continue
    }

    if ($component.name -notin $wanted) { continue }
    if (Test-Path "$root\state\service-manual-stop-$($component.name)") { continue }
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
    if ('guard' -in $wanted -and !(Test-Path "$root\state\service-manual-stop-guard") -and !(Listening ([int]$cfg.port))) {
      if ((Test-Path "$root\state\service-manual-stop-guard_gateway") -or (Test-Path "$root\state\service-manual-stop-relay")) { throw 'Guard dependency intentionally stopped; explicit Start required' }
      Archive-DeadReceipt "$guardRoot\state\process.json" ([int]$cfg.port)
      # start.ps1 also tries the gateway. An existing gateway is retained.
      try { & "$releasePath\scripts\start.ps1" -GuardHome $guardRoot } catch {
        if (!(Test-Path "$guardRoot\state\process.json")) { throw }
      }
    }
    if ('guard_gateway' -in $wanted -and $cfg.gateway_enabled -and !(Test-Path "$root\state\service-manual-stop-guard_gateway") -and !(Listening 8896)) {
      Archive-DeadReceipt "$guardRoot\state\gateway-process.json" 8896
      & "$releasePath\scripts\start-gateway.ps1" -GuardHome $guardRoot
    }
    if ('relay' -in $wanted -and $cfg.relay_enabled -and !(Test-Path "$root\state\service-manual-stop-relay")) {
      $env:MELLOW_GUARD_HOME = $guardRoot
      $env:MELLOW_GUARD_AUTH_FILE = [string]$cfg.auth_file
      Set-GuardRelayEnvironment -Config $cfg
      Push-Location $releasePath
      try {
        $probe = New-Object Net.Sockets.TcpClient
        try {
          $connect = $probe.BeginConnect([string]$cfg.relay.host,22,$null,$null)
          if (!$connect.AsyncWaitHandle.WaitOne(5000)) {
            $duplicates = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object AddressState -eq 'Duplicate')
            if ($duplicates.Count) { throw 'IPv4 address conflict detected by Windows (Duplicate); fix network address. Services are local-only; will retry automatically.' }
            throw 'SSH relay unreachable on port 22; retrying next scheduled run'
          }
          $probe.EndConnect($connect)
        } finally { $probe.Dispose() }
        $relay = (& "$releasePath\venv\Scripts\python.exe" -m mellow_guard.relay reconcile | Out-String) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or !$relay.owned -or $relay.state -ne 'running') { throw ('Relay: '+$relay.state+'; '+$relay.reason) }
        Start-Sleep -Seconds 2
        $relay = (& "$releasePath\venv\Scripts\python.exe" -m mellow_guard.relay status | Out-String) | ConvertFrom-Json
        if (!$relay.owned -or $relay.state -ne 'running') { throw ('Relay exited after launch: '+$relay.state+'; '+$relay.reason) }
      } finally { Pop-Location }
    }
  } catch { $failures += $_.Exception.Message }
  $report = @{time=(Get-Date).ToUniversalTime().ToString('o');listeners=@{};errors=@($failures)}
  foreach ($port in @(11434,8876,8897,8898,8896)) {
    $report.listeners["$port"] = Listening $port
    # Missing listeners are reported individually; intentionally stopped components are not overall failures.
  }
  $report.errors = @($failures)
  $report | ConvertTo-Json -Depth 5 | Set-Content "$root\state\service-reconcile.json" -Encoding UTF8
  if ($failures.Count) { throw ($failures -join '; ') }
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
