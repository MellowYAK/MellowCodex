[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$ExpectedOwnerSid,
 [Parameter(Mandatory=$true)][int]$OriginProcessId,
 [Parameter(Mandatory=$true)][long]$OriginStartedUtcTicks,
 [Parameter(Mandatory=$true)][string]$ExpectedScriptSha256,
 [Parameter(Mandatory=$true)][string]$RunId
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$guardHome=Join-Path $env:ProgramData 'MellowGuard'
$logs=Join-Path $guardHome 'logs'
$logPath=Join-Path $logs ('acl-repair-'+$RunId+'.log')
$reportPath=Join-Path $logs ('acl-repair-'+$RunId+'.json')
$transcriptStarted=$false
$installedRelease='0.1.1-7f046faa989a23b6'
$adminSid=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
$systemSid=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
function Assert-NotLinked([string]$Path){
 $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
 if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw ('REPARSE_POINT_NOT_ALLOWED '+$Path)}
}
function Set-ImmutableReleaseAcl([string]$Path,[bool]$Directory,[Security.Principal.SecurityIdentifier]$Owner) {
 Assert-NotLinked $Path
 $flags=if($Directory){
  [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
 }else{[Security.AccessControl.InheritanceFlags]::None}
 $acl=if($Directory){New-Object System.Security.AccessControl.DirectorySecurity}else{New-Object System.Security.AccessControl.FileSecurity}
 $acl.SetAccessRuleProtection($true,$false)
 foreach($pair in @(@($systemSid,[Security.AccessControl.FileSystemRights]::FullControl),
                    @($adminSid,[Security.AccessControl.FileSystemRights]::FullControl),
                    @($Owner,[Security.AccessControl.FileSystemRights]::ReadAndExecute))){
  $rule=[Security.AccessControl.FileSystemAccessRule]::new(
    [Security.Principal.IdentityReference]$pair[0],
    [Security.AccessControl.FileSystemRights]$pair[1],
    $flags,
    [Security.AccessControl.PropagationFlags]::None,
    [Security.AccessControl.AccessControlType]::Allow)
  $acl.AddAccessRule($rule)
 }
 (Get-Item -LiteralPath $Path -Force).SetAccessControl($acl)
}
function Write-Outcome([string]$Status,[string]$Detail,[int]$Files){
 if(!(Test-Path $logs -PathType Container)){return}
 $data=[ordered]@{
  schema=1;phase='guard_release_acl_repair';utc=[DateTime]::UtcNow.ToString('o')
  run_id=$RunId;status=$Status;details=$Detail;release_id=$installedRelease
  files_checked=$Files;owner_read_execute_only=$true
 }
 [IO.File]::WriteAllText($reportPath,($data|ConvertTo-Json -Depth 3),[Text.UTF8Encoding]::new($false))
}
$filesCount=0
try{
 $admin=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
 if(!$admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'NATIVE_WINDOWS_UAC_ADMIN_REQUIRED'}
 if($RunId -notmatch '^[a-f0-9]{32}$' -or $ExpectedScriptSha256 -notmatch '^[A-Fa-f0-9]{64}$'){throw 'EXPECTED_REPAIR_IDENTIFIERS_INVALID'}
 if((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash -ine $ExpectedScriptSha256){throw 'ELEVATED_REPAIR_SOURCE_HASH_CHANGED'}
 if($ExpectedOwnerSid -notmatch '^S-1-5-21-(?:\d+-){3}\d+$'){throw 'EXPECTED_OWNER_SID_INVALID'}
 $origin=Get-CimInstance Win32_Process -Filter ("ProcessId="+$OriginProcessId) -ErrorAction Stop
 if(!$origin){throw 'ORIGINAL_USER_PROCESS_ENDED'}
 $sid=(Invoke-CimMethod -InputObject $origin -MethodName GetOwnerSid -ErrorAction Stop).Sid
 if([string]$sid -cne $ExpectedOwnerSid){throw 'ORIGINAL_USER_SID_NOT_VERIFIED'}
 $proc=Get-Process -Id $OriginProcessId -ErrorAction Stop
 if($proc.StartTime.ToUniversalTime().Ticks -ne $OriginStartedUtcTicks){throw 'ORIGINAL_USER_PROCESS_REUSED'}
 if([int]$origin.SessionId -le 0 -or [int]$origin.SessionId -ne (Get-Process -Id $PID).SessionId){throw 'ORIGINAL_USER_SESSION_MISMATCH'}
 if([string]$origin.ExecutablePath -notmatch '(?i)\\WindowsPowerShell\\v1\.0\\powershell\.exe$'){throw 'ORIGINAL_USER_EXECUTABLE_INVALID'}
 if([string]$origin.CommandLine -notmatch '(?i)-File\s+"?[^"]*GUARD-ACL-REPAIR\.ps1(?:\"|\s|$)'){throw 'ORIGINAL_USER_COMMAND_MISMATCH'}
 $broker=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction Stop
 if(!$broker -or [string]$broker.State -ne 'Running' -or [string]$broker.StartName -ne 'LocalSystem'){throw 'VERIFIED_PROTECTED_BROKER_NOT_RUNNING'}
 $brokerCfg=Join-Path $env:ProgramData 'MellowOwnerBroker\config.json'
 $binding=Get-Content -LiteralPath $brokerCfg -Raw -Encoding UTF8|ConvertFrom-Json
 if([string]$binding.owner_sid -cne $ExpectedOwnerSid){throw 'PROTECTED_BROKER_OWNER_SID_MISMATCH'}
 $releasePointer=Join-Path $guardHome 'current.json'
 Assert-NotLinked $releasePointer
 $pointer=Get-Content -LiteralPath $releasePointer -Raw -Encoding UTF8|ConvertFrom-Json
 if([string]$pointer.release_id -cne $installedRelease){throw 'GUARD_RELEASE_ID_NOT_EXPECTED'}
 if([string]$pointer.port -ne '8898' -or [string]$pointer.bind -ne '127.0.0.1'){throw 'GUARD_BIND_CONFIG_NOT_EXPECTED'}
 $releases=Join-Path $guardHome 'releases'
 $release=Join-Path $releases $installedRelease
 if(!(Test-Path -LiteralPath $release -PathType Container)){throw 'PINNED_GUARD_RELEASE_MISSING'}
 $manifest=Join-Path $release 'source-manifest.json'
 Assert-NotLinked $manifest
 $m=Get-Content -LiteralPath $manifest -Raw -Encoding UTF8|ConvertFrom-Json
 if([string]$m.release_id -cne $installedRelease){throw 'GUARD_SOURCE_MANIFEST_RELEASE_MISMATCH'}
 $uvicorn=Join-Path $release 'venv\Lib\site-packages\uvicorn\__init__.py'
 $interpreter=Join-Path $release 'venv\Scripts\python.exe'
 foreach($path in @($uvicorn,$interpreter)){
  if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw ('EXPECTED_GUARD_RUNTIME_MISSING '+$path)}
  Assert-NotLinked $path
 }
 # Preflight the ENTIRE exact immutable release before any ACL mutation.
 Assert-NotLinked $releases
 Assert-NotLinked $release
 $children=@(Get-ChildItem -LiteralPath $release -Recurse -Force -ErrorAction Stop)
 foreach($child in $children){
  if(($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw ('IMMUTABLE_RELEASE_CONTAINS_LINK '+$child.FullName)}
 }
 foreach($property in @($m.files.PSObject.Properties)){
  $rel=[string]$property.Name
  if($rel -match '(^|/)\.\.?(/|$)' -or $rel -notmatch '^(mellow_guard|scripts)/[a-zA-Z0-9_./-]+$|^(VERSION|pyproject\.toml|requirements\.lock\.txt)$'){throw 'SOURCE_MANIFEST_PATH_UNTRUSTED'}
  $path=Join-Path $release ($rel.Replace('/','\'))
  if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw ('IMMUTABLE_RELEASE_FILE_MISSING '+$rel)}
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ine [string]$property.Value){throw ('IMMUTABLE_RELEASE_SOURCE_HASH_MISMATCH '+$rel)}
 }
 [IO.Directory]::CreateDirectory($logs)|Out-Null
 Assert-NotLinked $logs
 Start-Transcript -LiteralPath $logPath -Force|Out-Null
 $transcriptStarted=$true
 Write-Host ('GUARD_ACL_REPAIR_BEGIN_RELEASE='+$installedRelease)
 Write-Host ('GUARD_ACL_REPAIR_ORDINARY_OWNER_SID='+$ExpectedOwnerSid)
 $owner=New-Object System.Security.Principal.SecurityIdentifier($ExpectedOwnerSid)
 # Protect parent and the exact release, and recursively bind every existing file and directory.
 Set-ImmutableReleaseAcl $releases $true $owner
 Set-ImmutableReleaseAcl $release $true $owner
 $folders=@($children|Where-Object {$_.PSIsContainer}|Sort-Object {$_.FullName.Length})
 $files=@($children|Where-Object {-not $_.PSIsContainer})
 foreach($folder in $folders){Set-ImmutableReleaseAcl $folder.FullName $true $owner}
 foreach($file in $files){Set-ImmutableReleaseAcl $file.FullName $false $owner;$filesCount++}
 $testAcl=Get-Acl -LiteralPath $uvicorn -ErrorAction Stop
 if(!$testAcl.AreAccessRulesProtected){throw 'GUARD_VENV_TARGET_INHERITANCE_NOT_PROTECTED'}
 $ownerRule=@($testAcl.Access|Where-Object {
  $_.AccessControlType -eq 'Allow' -and $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -eq $ExpectedOwnerSid
 })
 if($ownerRule.Count -ne 1 -or ($ownerRule[0].FileSystemRights -band [Security.AccessControl.FileSystemRights]::WriteData)){throw 'GUARD_OWNER_ACL_GRANTS_WRITE_OR_READ_MISSING'}
 Write-Host ('GUARD_ACL_REPAIR_FILES_VERIFIED='+$filesCount)
 Write-Host 'GUARD_ACL_REPAIR_READ_EXECUTE_ONLY=PASS'
 Write-Outcome 'PASS' 'User read/execute to immutable release, SYSTEM/Admin write' $filesCount
 exit 0
}catch{
 $detail=[string]$_.Exception.Message
 if($detail.Length -gt 1300){$detail=$detail.Substring(0,1300)}
 Write-Host ('GUARD_ACL_REPAIR_FAILED='+$detail)
 try{Write-Outcome 'FAIL' $detail $filesCount}catch{}
 exit 1
}finally{
 if($transcriptStarted){try{Stop-Transcript|Out-Null}catch{}}
}