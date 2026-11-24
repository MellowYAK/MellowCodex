[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$shared=Split-Path $PSScriptRoot -Parent
$qa=Join-Path $shared 'QA-LOGS'
$started=$false
$runId=[Guid]::NewGuid().ToString('N')
if(!(Test-Path -LiteralPath $qa -PathType Container)){throw 'SHARED_QA_LOGS_MISSING'}
$log=Join-Path $qa ('GUARD-ACL-REPAIR-'+$runId+'.log')
$latest=Join-Path $qa 'GUARD-ACL-REPAIR-LATEST.json'
$status='FAIL';$detail='NOT_STARTED';$elevatedLog=''
try{
 Start-Transcript -LiteralPath $log -Force -ErrorAction Stop|Out-Null
 $started=$true
 Write-Host ('GUARD_ACL_REPAIR_RUN='+$runId)
 Write-Host 'ONLY immutable Guard release ACL changes through explicit Windows UAC; owner ReadExecute, SYSTEM and Admin FullControl.'
 $cs=Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
 if([string]$cs.Manufacturer -notmatch '(?i)VMware' -or !(Get-Service VMTools -ErrorAction SilentlyContinue)){throw 'REPAIR_ONLY_INSIDE_VMWARE_GUEST'}
 $who=[Security.Principal.WindowsIdentity]::GetCurrent()
 $user=[Security.Principal.WindowsPrincipal]::new($who)
 if($user.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'REPAIR_LAUNCH_NORMALLY_NOT_AS_ADMIN'}
 foreach($n in @(1,2)){
  $receipt=Join-Path $qa ('INSTALL-'+$n+'-SUCCESS.json')
  if(!(Test-Path $receipt -PathType Leaf)){throw ('REQUIRED_PREVIOUS_INSTALL_PHASE_MISSING_'+$n)}
  $rec=Get-Content -LiteralPath $receipt -Raw -Encoding UTF8|ConvertFrom-Json
  if([string]$rec.status -cne 'PASS' -or [string]$rec.owner_sid -cne $who.User.Value){throw ('PRIOR_PHASE_OWNER_MISMATCH_'+$n)}
 }
 $guardHome=Join-Path $env:ProgramData 'MellowGuard'
 $current=Join-Path $guardHome 'current.json'
 $cfg=Get-Content -LiteralPath $current -Raw -Encoding UTF8|ConvertFrom-Json
 if([string]$cfg.release_id -cne '0.1.1-7f046faa989a23b6'){throw 'GUARD_PINNED_RELEASE_DIFFERENT'}
 $source=Join-Path $PSScriptRoot 'GUARD-ACL-REPAIR-ELEVATED.ps1'
 $shaFile=$source+'.sha256'
 $sourceHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
 if($sourceHash -ine 'A569F99E50C971B6A8C1D3862C34D071075A3C1498F18AE80DA2E7B8A0D15BFF' -or
    (Get-Content -LiteralPath $shaFile -Raw).Trim() -ine $sourceHash){throw 'PINNED_ELEVATED_REPAIR_SCRIPT_HASH_BAD'}
 $install=Join-Path $env:LOCALAPPDATA ('MellowCodexQA\GuardAclRepair\'+$runId)
 if(Test-Path -LiteralPath $install){throw 'REPAIR_STAGING_COLLISION'}
 [IO.Directory]::CreateDirectory($install)|Out-Null
 $copy=Join-Path $install 'GUARD-ACL-REPAIR-ELEVATED.ps1'
 Copy-Item -LiteralPath $source -Destination $copy -ErrorAction Stop
 if((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash -ne $sourceHash){throw 'ELEVATED_SCRIPT_COPY_CHANGED'}
 $origin=Get-Process -Id $PID -ErrorAction Stop
 $adminPowershell=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 $arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$copy+
  '" -ExpectedOwnerSid '+$who.User.Value+
  ' -OriginProcessId '+$PID+
  ' -OriginStartedUtcTicks '+$origin.StartTime.ToUniversalTime().Ticks+
  ' -ExpectedScriptSha256 '+$sourceHash+
  ' -RunId '+$runId
 Write-Host ('GUARD_ACL_REPAIR_ORIGINAL_USER_SID='+$who.User.Value)
 Write-Host ('GUARD_ACL_REPAIR_EXPECTED_RELEASE='+[string]$cfg.release_id)
 Write-Host 'Windows will request administrator approval for a scoped immutable Guard release read-access repair.'
 $child=Start-Process -FilePath $adminPowershell -ArgumentList $arguments -Verb RunAs -Wait -PassThru -ErrorAction Stop
 Write-Host ('ELEVATED_REPAIR_EXIT_CODE='+$child.ExitCode)
 $privilegedJson=Join-Path $guardHome ('logs\acl-repair-'+$runId+'.json')
 $privilegedLog=Join-Path $guardHome ('logs\acl-repair-'+$runId+'.log')
 $privCopy=Join-Path $qa ('GUARD-ACL-REPAIR-ELEVATED-'+$runId+'.json')
 if(Test-Path -LiteralPath $privilegedJson -PathType Leaf){
  Copy-Item -LiteralPath $privilegedJson -Destination $privCopy -ErrorAction Stop
  $priv=Get-Content -LiteralPath $privCopy -Raw|ConvertFrom-Json
  Write-Host ('ELEVATED_REPAIR_REPORT_STATUS='+[string]$priv.status)
  Write-Host ('ELEVATED_REPAIR_REPORT_DETAILS='+[string]$priv.details)
 }else{throw 'ELEVATED_REPAIR_DIAGNOSTIC_REPORT_MISSING'}
 if(Test-Path -LiteralPath $privilegedLog -PathType Leaf){
  $elevatedLog=Join-Path $qa ('GUARD-ACL-REPAIR-ELEVATED-'+$runId+'.log')
  Copy-Item -LiteralPath $privilegedLog -Destination $elevatedLog -ErrorAction Stop
 }
 if($child.ExitCode -ne 0 -or [string]$priv.status -ne 'PASS'){throw ('ELEVATED_REPAIR_FAILED_'+[string]$priv.details)}
 $python=Join-Path $guardHome 'releases\0.1.1-7f046faa989a23b6\venv\Scripts\python.exe'
 Write-Host 'TEST_GUARD_PYTHON_UVICORN_IMPORT_AS_ORIGINAL_USER'
 $uvOutput=@(& $python -m uvicorn --version 2>&1)
 $uvOutput|ForEach-Object {Write-Host ([string]$_)}
 if($LASTEXITCODE -ne 0){throw ('ORIGINAL_USER_UVICORN_IMPORT_FAILED_EXIT_'+$LASTEXITCODE)}
 $status='PASS';$detail='Guard immutable release owner read/execute; original yak imported uvicorn'
 Write-Host 'GUARD_VENV_IMPORT_AS_YAK=PASS'
 Write-Host 'NEXT_ACTION=INSTALL-3_AFTER_SAFE_STALE_PROCESS_RECEIPT_CHECK'
}catch{
 $detail=[string]$_.Exception.Message
 if($detail.Length -gt 1500){$detail=$detail.Substring(0,1500)}
 Write-Host ('GUARD_ACL_REPAIR_FAILURE='+$detail)
}finally{
 $report=[ordered]@{schema=1;utc=[DateTime]::UtcNow.ToString('o');run_id=$runId;status=$status;details=$detail;log=[IO.Path]::GetFileName($log);elevated_log=([IO.Path]::GetFileName($elevatedLog))}
 try{
  $tmp=$latest+'.tmp-'+[Guid]::NewGuid().ToString('N')
  [IO.File]::WriteAllText($tmp,($report|ConvertTo-Json -Depth 3),[Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $latest -Force
 }catch{Write-Host ('QA_RESULT_SAVE_FAILED='+$_.Exception.Message)}
 if($started){try{Stop-Transcript|Out-Null}catch{}}
}
if($status -eq 'PASS'){exit 0}else{exit 1}