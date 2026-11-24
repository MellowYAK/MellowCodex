Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$share=Split-Path $PSScriptRoot -Parent
$qa=Join-Path $share 'QA-LOGS'
if(!(Test-Path -LiteralPath $qa -PathType Container)){throw 'QA_LOGS_DIRECTORY_MISSING'}
$cs=Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
if([string]$cs.Manufacturer -notmatch '(?i)VMware'){throw 'VMWARE_GUEST_REQUIRED'}
if(!(Get-Service -Name VMTools -ErrorAction SilentlyContinue)){throw 'VMWARE_TOOLS_REQUIRED'}
$ident=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($ident)
if($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'RUN_NORMALLY_NOT_AS_ADMINISTRATOR'}
$id=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
$log=Join-Path $qa ('GUARD-DIAGNOSTICS-'+$id+'.log')
$summary=Join-Path $qa 'GUARD-DIAGNOSTICS-LATEST.json'
$started=$false
function SafeLine([string]$Line) {
 $s=[regex]::Replace($Line,'(?i)((?:password|api[_-]?key|token|secret|authorization|bearer|auth[_-]?key)\s*[:=]\s*)\S+','$1[REDACTED]')
 if($s.Length -gt 1500){$s=$s.Substring(0,1500)+'...[TRUNCATED]'}
 return $s
}
try{
 Start-Transcript -LiteralPath $log -ErrorAction Stop|Out-Null
 $started=$true
 Write-Host 'MELLOWCODEX_GUARD_DIAGNOSTIC_READ_ONLY=TRUE'
 Write-Host ('UTC='+[DateTime]::UtcNow.ToString('o'))
 $guardHome=Join-Path $env:ProgramData 'MellowGuard'
 $guardProcessId=0;$pidAlive=$false
 $receipt=Join-Path $guardHome 'state\process.json'
 if(Test-Path -LiteralPath $receipt -PathType Leaf){
  try{
   $r=Get-Content -LiteralPath $receipt -Encoding UTF8 -Raw|ConvertFrom-Json
   $guardProcessId=[int]$r.pid
   $proc=Get-Process -Id $guardProcessId -ErrorAction SilentlyContinue
   $pidAlive=[bool]$proc
  }catch{Write-Host ('PROCESS_RECEIPT_PARSE_ERROR='+ (SafeLine $_.Exception.Message))}
 }
 Write-Host ('GUARD_RECEIPT_EXISTS='+(Test-Path -LiteralPath $receipt -PathType Leaf))
 Write-Host ('GUARD_RECEIPT_PID='+$guardProcessId)
 Write-Host ('GUARD_RECEIPT_PID_ALIVE='+$pidAlive)
 $current=Join-Path $guardHome 'current.json'
 if(Test-Path -LiteralPath $current -PathType Leaf){
  try{
   $cfg=Get-Content -LiteralPath $current -Encoding UTF8 -Raw|ConvertFrom-Json
   Write-Host ('GUARD_RELEASE_ID='+[string]$cfg.release_id)
   Write-Host ('GUARD_CONFIG_PORT='+[string]$cfg.port)
   Write-Host ('GUARD_GATEWAY_ENABLED='+[string]$cfg.gateway_enabled)
  }catch{Write-Host ('GUARD_CURRENT_POINTER_READ_ERROR='+ (SafeLine $_.Exception.Message))}
 }
 foreach($port in @(8876,8897,8898,8896)){
  $listeners=@(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
  Write-Host ('LISTENER_127_0_0_1_'+$port+'='+[bool]($listeners.Count))
 }
 try{
  $scheduled=Get-ScheduledTask -TaskName 'Mellow Guard Standalone' -ErrorAction SilentlyContinue
  Write-Host ('GUARD_TASK_EXISTS='+[bool]$scheduled)
  if($scheduled){
   Write-Host ('GUARD_TASK_STATE='+[string]$scheduled.State)
   $info=Get-ScheduledTaskInfo -TaskName 'Mellow Guard Standalone' -ErrorAction SilentlyContinue
   if($info){Write-Host ('GUARD_TASK_LAST_RESULT='+[string]$info.LastTaskResult)}
  }
 }catch{Write-Host ('GUARD_TASK_QUERY_FAILED='+ (SafeLine $_.Exception.Message))}
 try{
  $broker=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction SilentlyContinue
  Write-Host ('OWNERBROKER_SERVICE_EXISTS='+[bool]$broker)
  if($broker){Write-Host ('OWNERBROKER_STATE='+[string]$broker.State);Write-Host ('OWNERBROKER_ACCOUNT='+[string]$broker.StartName)}
 }catch{Write-Host ('OWNERBROKER_QUERY_FAILED='+ (SafeLine $_.Exception.Message))}
 foreach($basename in @('guard.stderr.log','guard.stdout.log','gateway.stderr.log')){
  $f=Join-Path $guardHome ('logs\'+$basename)
  Write-Host ('SOURCE_LOG='+$basename+' EXISTS='+(Test-Path -LiteralPath $f -PathType Leaf))
  if(Test-Path -LiteralPath $f -PathType Leaf){
   try{
    $file=Get-Item -LiteralPath $f -ErrorAction Stop
    Write-Host ('SOURCE_LOG_BYTES='+$file.Length)
    $lines=Get-Content -LiteralPath $f -Tail 140 -ErrorAction Stop
    Write-Host ('SOURCE_LOG_TAIL_START '+$basename)
    foreach($line in $lines){Write-Host (SafeLine ([string]$line))}
    Write-Host ('SOURCE_LOG_TAIL_END '+$basename)
   }catch{Write-Host ('SOURCE_LOG_READ_FAILED='+ (SafeLine $_.Exception.Message))}
  }
 }
 $controller=Join-Path $env:LOCALAPPDATA 'MellowCodexData\state\service-actions\522005d8a8feddf66819abf0e32b6eed-guard.controller.log'
 Write-Host ('FAILED_GUARD_CONTROLLER_LOG_EXISTS='+(Test-Path -LiteralPath $controller -PathType Leaf))
 if(Test-Path -LiteralPath $controller -PathType Leaf){
  try{
   Write-Host 'FAILED_GUARD_CONTROLLER_TAIL_START'
   foreach($line in (Get-Content -LiteralPath $controller -Tail 120 -ErrorAction Stop)){Write-Host (SafeLine ([string]$line))}
   Write-Host 'FAILED_GUARD_CONTROLLER_TAIL_END'
  }catch{Write-Host ('CONTROLLER_LOG_READ_FAILED='+ (SafeLine $_.Exception.Message))}
 }
 foreach($marker in @('mcp-manual-stop','manual-stop','service-manual-stop')){
  $path=Join-Path $env:LOCALAPPDATA ('MellowCodexData\state\'+$marker)
  Write-Host ('OWNER_STOP_MARKER_'+$marker+'='+(Test-Path -LiteralPath $path))
 }
 $result=[ordered]@{schema=1;utc=[DateTime]::UtcNow.ToString('o');guard_receipt_pid=$guardProcessId;guard_process_alive=$pidAlive;guard_port_8898_listening=[bool](@(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 8898 -State Listen -ErrorAction SilentlyContinue).Count);log=[IO.Path]::GetFileName($log);read_only=$true}
 $json=$result|ConvertTo-Json -Depth 3
 $tmp=$summary+'.tmp-'+[Guid]::NewGuid().ToString('N')
 [IO.File]::WriteAllText($tmp,$json,[Text.UTF8Encoding]::new($false))
 Move-Item -LiteralPath $tmp -Destination $summary -Force
 Write-Host ('GUARD_DIAGNOSTIC_COMPLETE='+$log)
}finally{
 if($started){try{Stop-Transcript|Out-Null}catch{}}
}