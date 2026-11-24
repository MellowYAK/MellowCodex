. (Join-Path $PSScriptRoot 'QA-R41-Common.ps1')
Invoke-QAPhase 3 {
 Assert-PreviousPhase 2
 Assert-StagedSource
 $brokerDir=Join-Path $env:ProgramData 'MellowOwnerBroker'
 $brokerService=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction Stop
 if(!$brokerService -or [string]$brokerService.State -ne 'Running' -or [string]$brokerService.StartName -ne 'LocalSystem'){
  throw 'INSTALL3_BROKER_NOT_RUNNING'
 }
 $brokerConfig=Join-Path $brokerDir 'config.json'
 $binding=Get-Content -LiteralPath $brokerConfig -Raw -Encoding UTF8|ConvertFrom-Json
 if([string]$binding.owner_sid -cne $script:OwnerSid){throw 'INSTALL3_ORIGINAL_OWNER_IDENTITY_MISMATCH'}
 $guardHome=Join-Path $env:ProgramData 'MellowGuard'
 $release=Get-Content -LiteralPath (Join-Path $guardHome 'current.json') -Raw -Encoding UTF8|ConvertFrom-Json
 if([string]$release.release_id -notmatch '^0\.1\.1-[a-f0-9]{16}$'){throw 'INSTALL3_GUARD_RELEASE_ID_INVALID'}
 $releaseRoot=Join-Path (Join-Path $guardHome 'releases') ([string]$release.release_id)
 foreach($relative in @('scripts\register-startup.ps1','scripts\start.ps1')){
  if(!(Test-Path -LiteralPath (Join-Path $releaseRoot $relative) -PathType Leaf)){
   throw ('INSTALL3_GUARD_SCRIPT_MISSING_'+$relative)
  }
 }
  # The installed Guard venv is immutable and admin-installed; ordinary yak must only read/execute.
  $aclReceipt=Join-Path $script:QaLogs 'GUARD-ACL-REPAIR-LATEST.json'
  if(!(Test-Path -LiteralPath $aclReceipt -PathType Leaf)){throw 'INSTALL3_GUARD_ACL_REPAIR_FIRST_REQUIRED'}
  $acl=Get-Content -LiteralPath $aclReceipt -Raw -Encoding UTF8|ConvertFrom-Json
  if([string]$acl.status -cne 'PASS'){throw 'INSTALL3_GUARD_ACL_REPAIR_NOT_VERIFIED'}
  $py=Join-Path $releaseRoot 'venv\Scripts\python.exe'
  $uv=@(& $py -m uvicorn --version 2>&1)
  $uv|ForEach-Object {Write-Host ('GUARD_PYTHON_IMPORT_CHECK='+[string]$_)}
  if($LASTEXITCODE -ne 0){throw 'INSTALL3_PINNED_GUARD_PYTHON_IMPORT_FAILED'}
  foreach($marker in @('mcp-manual-stop','manual-stop','service-manual-stop')){
   if(Test-Path -LiteralPath (Join-Path $script:AgentRoot ('state\'+$marker))){throw ('INSTALL3_OWNER_STOP_MARKER_PRESERVED_'+$marker)}
  }
  $existing=Get-ScheduledTask -TaskName 'Mellow Guard Standalone' -ErrorAction SilentlyContinue
  if($existing){
       $actions=@($existing.Actions)
    $startPath=Join-Path $releaseRoot 'scripts\start.ps1'
    $userSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $scheduledUser=[string]$existing.Principal.UserId
    $scheduledSid=''
    try {
      if($scheduledUser -match '^S-\d+-'){ $scheduledSid=([Security.Principal.SecurityIdentifier]::new($scheduledUser)).Value }
      else{ $scheduledSid=([Security.Principal.NTAccount]::new($scheduledUser)).Translate([Security.Principal.SecurityIdentifier]).Value }
    }catch{Write-Host ('INSTALL3_TASK_SID_RESOLUTION_FAILED='+$_.Exception.GetType().Name)}
    $ownerOk=($scheduledSid -ceq $userSid)
    $runLevel=([string]$existing.Principal.RunLevel)
    $runOk=($runLevel -in @('LeastPrivilege','Limited'))
    $logonType=([string]$existing.Principal.LogonType)
    $logonOk=($logonType -in @('Interactive','InteractiveToken'))
    $actionCountOk=($actions.Count -eq 1)
    $executeOk=$false;$argumentOk=$false
    if($actionCountOk){
      $exe=[string]$actions[0].Execute
      $args=[string]$actions[0].Arguments
      $executeOk=($exe -match '(?i)(^|\\)powershell\.exe$')
      $expectedArgs='-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$startPath+'" -Home "'+$guardHome+'"'
      # TaskScheduler may normalize whitespace or quote case, never change command targets.
      $argumentOk=([regex]::Replace($args,'\s+',' ').Trim().Equals(
        [regex]::Replace($expectedArgs,'\s+',' ').Trim(),[StringComparison]::OrdinalIgnoreCase))
    }
    Write-Host ('INSTALL3_TASK_OWNER_SID_MATCH='+$ownerOk)
    Write-Host ('INSTALL3_TASK_RUNLEVEL_LEAST_PRIVILEGE='+$runOk)
    Write-Host ('INSTALL3_TASK_LOGON_INTERACTIVE='+$logonOk)
    Write-Host ('INSTALL3_TASK_ACTION_COUNT_ONE='+$actionCountOk)
    Write-Host ('INSTALL3_TASK_EXECUTABLE_POWERSHELL='+$executeOk)
    Write-Host ('INSTALL3_TASK_ARGUMENTS_EXACT_PINNED='+$argumentOk)
    if(!$ownerOk -or !$runOk -or !$logonOk -or !$actionCountOk -or !$executeOk -or !$argumentOk){
      Write-Host ('INSTALL3_TASK_REPORTED_PRINCIPAL='+$scheduledUser)
      Write-Host ('INSTALL3_TASK_REPORTED_RUNLEVEL='+$runLevel)
      Write-Host ('INSTALL3_TASK_REPORTED_LOGON='+$logonType)
      if($actionCountOk){
        Write-Host ('INSTALL3_TASK_ACTUAL_EXECUTABLE='+[string]$actions[0].Execute)
        Write-Host ('INSTALL3_TASK_ACTUAL_ARGUMENTS='+[string]$actions[0].Arguments)
        Write-Host ('INSTALL3_TASK_EXPECTED_ARGUMENTS='+$expectedArgs)
      }
      throw 'INSTALL3_EXISTING_GUARD_TASK_OWNERSHIP_OR_ACTION_MISMATCH'
    }
    Write-Host 'INSTALL3_EXISTING_GUARD_TASK_VERIFIED_NO_REPLACEMENT=TRUE'
  }else{
   & (Join-Path $releaseRoot 'scripts\register-startup.ps1') -GuardHome $guardHome
   if(!$?){throw 'INSTALL3_GUARD_STARTUP_REGISTRATION_FAILED'}
  }
  $state=Join-Path $guardHome 'state'
  $processReceipt=Join-Path $state 'process.json'
  $alreadyRunning=$false
  if(Test-Path -LiteralPath $processReceipt -PathType Leaf){
   $info=Get-Item -LiteralPath $processReceipt -Force
   if(($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'INSTALL3_GUARD_RECEIPT_LINKED'}
   $oldProcess=Get-Content -LiteralPath $processReceipt -Raw -Encoding UTF8|ConvertFrom-Json
   $expectedExe=[IO.Path]::GetFullPath($py)
   if([string]$oldProcess.release_id -cne [string]$release.release_id -or
      [int]$oldProcess.port -ne 8898 -or
      !([IO.Path]::GetFullPath([string]$oldProcess.executable)).Equals($expectedExe,[StringComparison]::OrdinalIgnoreCase) -or
      [int]$oldProcess.pid -le 0){throw 'INSTALL3_STALE_GUARD_PROCESS_RECEIPT_INVALID'}
   $existingProcess=Get-Process -Id ([int]$oldProcess.pid) -ErrorAction SilentlyContinue
   if($existingProcess){
    if($existingProcess.StartTime.ToUniversalTime().Ticks -ne [int64]$oldProcess.started_utc_ticks){throw 'INSTALL3_GUARD_RECEIPT_PID_REUSED'}
    $alreadyRunning=$true
    Write-Host 'INSTALL3_GUARD_PROCESS_ALREADY_ALIVE_NOT_RESTARTED=TRUE'
   }else{
    if(Test-Path -LiteralPath (Join-Path $state 'gateway-process.json')){throw 'INSTALL3_GUARD_GATEWAY_RECEIPT_UNEXPECTED'}
    if(Test-Path -LiteralPath (Join-Path $state 'relay-owned.json')){throw 'INSTALL3_RELAY_RECEIPT_UNEXPECTED'}
    $history=Join-Path $guardHome 'history'
    if(!(Test-Path -LiteralPath $history -PathType Container)){throw 'INSTALL3_GUARD_HISTORY_MISSING'}
    $archive=Join-Path $history ('stale-guard-process-'+[Guid]::NewGuid().ToString('N')+'.json')
    Move-Item -LiteralPath $processReceipt -Destination $archive -ErrorAction Stop
    Write-Host ('INSTALL3_STALE_DEAD_PROCESS_RECEIPT_ARCHIVED='+$archive)
   }
  }
  if(!$alreadyRunning){
   Write-Host 'INSTALL3_GUARD_START_AS_ORIGINAL_ORDINARY_USER'
   & (Join-Path $releaseRoot 'scripts\start.ps1') -GuardHome $guardHome
   if(!$?){throw 'INSTALL3_GUARD_START_FAILED'}
  }
  $listening=$false
  for($i=0;$i -lt 40;$i++){
   $port=@(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 8898 -State Listen -ErrorAction SilentlyContinue)
   if($port.Count -gt 0){$listening=$true;break}
   Start-Sleep -Milliseconds 400
  }
  if(!$listening){throw 'INSTALL3_GUARD_NOT_LISTENING_8898_AFTER_START'}
  Write-Host 'INSTALL3_GUARD_LISTENER_8898_VERIFIED=TRUE'
 $installed=Join-Path $script:AgentRoot 'repos\local-agent-hub'
 $finish=Join-Path $installed 'installer\windows\Finish-OrdinaryUserSetup.ps1'
 if(!(Test-Path -LiteralPath $finish -PathType Leaf)){throw 'INSTALL3_USER_FINISH_SCRIPT_MISSING'}
 Write-Host 'INSTALL3_FINISH_ACTUAL_GUI_HUB_AND_MCP_RUNTIME'
 $result=@(& $finish -InstallRoot $script:AgentRoot)
 $result|ForEach-Object {Write-Host $_}
 if($result -notcontains 'MELLOWCODEX_ORDINARY_USER_FINALIZATION_VERIFIED=TRUE' -or
    $result -notcontains 'MELLOWCODEX_INSTALL_SCRIPT_COMPLETED=TRUE'){
   throw 'INSTALL3_FINAL_RUNTIME_ACCEPTANCE_MARKERS_MISSING'
 }
 Write-Host 'INSTALL3_ACTUAL_RUNTIME_VERIFIED=TRUE'
}