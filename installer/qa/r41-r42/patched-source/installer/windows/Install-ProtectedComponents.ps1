[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$AgentRoot,
 [string]$GuardBundle='',
 [string]$OwnerBrokerBundle='',
 [string]$OwnerBrokerMsi='',
 [string]$OwnerBrokerSha256='',
 [string]$ExpectedUserSid='',
  [int]$OriginalProcessId=0,
  [long]$OriginalStartedUtcTicks=0,
  [string]$AdminDiagnosticId='',
 [string]$RelayPlan='',
 [switch]$SkipGuard,
 [switch]$DryRun,[switch]$OwnerBrokerConsentFromWizard
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$AgentRoot=[IO.Path]::GetFullPath($AgentRoot).TrimEnd('\')
$repo=Join-Path $AgentRoot 'repos\local-agent-hub'
$uv=Join-Path $AgentRoot 'tools\uv\uv.exe'
$python=Join-Path $AgentRoot 'tools\hub-venv\Scripts\python.exe'
$state=Join-Path $env:ProgramData 'MellowGuard\state'
$guardHome=Join-Path $env:ProgramData 'MellowGuard'
function Require-File([string]$Name){if(!(Test-Path -LiteralPath $Name -PathType Leaf)){throw "File missing: $Name"}}
function Enforce-Sha([string]$Path,[string]$Value){
 if($Value -notmatch '^[0-9a-fA-F]{64}$'){throw "Invalid pinned SHA256 for $Path"}
 if((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ine $Value){throw "SHA256 mismatch: $Path"}
}
function Protect-State([string]$Path){
 [IO.Directory]::CreateDirectory($Path)|Out-Null
 $acl=New-Object System.Security.AccessControl.DirectorySecurity
 $acl.SetAccessRuleProtection($true,$false)
 $me=[Security.Principal.WindowsIdentity]::GetCurrent().User
 $system=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
 $flags=[Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
 foreach($sid in @($me,$system)){
  $r=New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl',$flags,[Security.AccessControl.PropagationFlags]::None,'Allow')
  $acl.AddAccessRule($r)
 }
 (Get-Item -LiteralPath $Path).SetAccessControl($acl)
}
function Rebind-GuardOwnerAccess([string]$GuardFolder,[string]$OwnerSid){
 $owner=New-Object System.Security.Principal.SecurityIdentifier($OwnerSid)
 $system=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
 $admins=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
 $inherit=[Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
 function ApplyOwnerAcl([string]$Path,[object[]]$Principals,[bool]$Directory){
  $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'GUARD_ACL_LINKED_PATH_REFUSED'}
  $acl=if($Directory){New-Object System.Security.AccessControl.DirectorySecurity}else{New-Object System.Security.AccessControl.FileSecurity}
  $acl.SetAccessRuleProtection($true,$false)
  foreach($sid in $Principals){
   $flags=if($Directory){$inherit}else{[Security.AccessControl.InheritanceFlags]::None}
   $ace=New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl',$flags,[Security.AccessControl.PropagationFlags]::None,'Allow')
   $acl.AddAccessRule($ace)
  }
  $item.SetAccessControl($acl)
 }
 $normal=@($owner,$system,$admins)
 $private=@($owner,$system)
 foreach($dir in @($GuardFolder,(Join-Path $GuardFolder 'releases'),(Join-Path $GuardFolder 'state'),(Join-Path $GuardFolder '.incoming'),(Join-Path $GuardFolder 'history'),(Join-Path $GuardFolder 'logs'))){
  if(!(Test-Path -LiteralPath $dir -PathType Container)){[IO.Directory]::CreateDirectory($dir)|Out-Null}
  ApplyOwnerAcl $dir $normal $true
 }
 $privateDir=Join-Path $GuardFolder 'state\private'
 if(!(Test-Path -LiteralPath $privateDir -PathType Container)){throw 'GUARD_PRIVATE_STATE_MISSING'}
 ApplyOwnerAcl $privateDir $private $true
 $auth=Join-Path $GuardFolder 'state\auth.key'
 if(!(Test-Path -LiteralPath $auth -PathType Leaf)){throw 'GUARD_AUTH_KEY_MISSING'}
 ApplyOwnerAcl $auth $private $false
}
if([string]::IsNullOrWhiteSpace($ExpectedUserSid)){
 $ExpectedUserSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
}
if($SkipGuard -and !$OwnerBrokerMsi -and !$OwnerBrokerBundle){throw 'Full MellowCodex install requires Guard and OwnerBroker; no protected packages supplied.'}
if(!$SkipGuard){
 if(!$GuardBundle){throw 'Guard source bundle is required. Export it from the current verified Guard release; do not copy credentials or VENV.'}
 Require-File $GuardBundle
 Require-File ($GuardBundle+'.sha256')
 $sidecar=(Get-Content -LiteralPath ($GuardBundle+'.sha256') -Raw).Trim()
 Enforce-Sha $GuardBundle $sidecar
}
if($OwnerBrokerBundle -and $OwnerBrokerMsi){throw 'Specify one OwnerBroker package, ZIP or signed MSI, not both'}
if($OwnerBrokerBundle){
 Require-File $OwnerBrokerBundle
 Require-File ($OwnerBrokerBundle+'.sha256')
 Enforce-Sha $OwnerBrokerBundle ((Get-Content -LiteralPath ($OwnerBrokerBundle+'.sha256') -Raw).Trim())
}else{
 if(!$OwnerBrokerMsi){throw 'A user-approved OwnerBroker bundle or signed MSI is required before full installation'}
 Require-File $OwnerBrokerMsi
 Enforce-Sha $OwnerBrokerMsi $OwnerBrokerSha256
 if([IO.Path]::GetExtension($OwnerBrokerMsi) -ine '.msi'){throw 'Only MSI packages are accepted for signed OwnerBroker setup'}
 $signature=Get-AuthenticodeSignature -FilePath $OwnerBrokerMsi
 if($signature.Status -ne 'Valid'){throw 'Broker MSI must have a valid Authenticode signature'}
}
Require-File $uv
Require-File $python
if($DryRun){
 Write-Host 'DRY_RUN protected Guard and OwnerBroker install preflight OK, no changes.'
 return
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin=(New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(!$isAdmin){
 Write-Host 'Windows administrator authorization is required only for protected Guard/OwnerBroker installation.' -ForegroundColor Cyan
  $diagnosticId=[Guid]::NewGuid().ToString('N')
  $originalProcess=Get-Process -Id $PID -ErrorAction Stop
 $args='-NoProfile -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -AgentRoot "'+$AgentRoot+'" -ExpectedUserSid '+$ExpectedUserSid+
    ' -OriginalProcessId '+$PID+' -OriginalStartedUtcTicks '+$originalProcess.StartTime.ToUniversalTime().Ticks+' -AdminDiagnosticId '+$diagnosticId
  if($OwnerBrokerBundle){
   $args+=' -OwnerBrokerBundle "'+$OwnerBrokerBundle+'"'
  }elseif($OwnerBrokerMsi){
   $args+=' -OwnerBrokerMsi "'+$OwnerBrokerMsi+'" -OwnerBrokerSha256 '+$OwnerBrokerSha256
  }else{
   throw 'APPROVED_OWNER_BROKER_PACKAGE_REQUIRED'
  }
  if($OwnerBrokerConsentFromWizard){$args+=' -OwnerBrokerConsentFromWizard'}
 if(!$SkipGuard){$args+=' -GuardBundle "'+$GuardBundle+'"'}else{$args+=' -SkipGuard'}
  if($RelayPlan){
    if($SkipGuard){throw 'RELAY_REQUIRES_GUARD_INSTALL'}
    $requested=[IO.Path]::GetFullPath($RelayPlan)
    $expected=[IO.Path]::GetFullPath((Join-Path $AgentRoot 'state\relay-onboarding.json'))
    if(!$requested.Equals($expected,[StringComparison]::OrdinalIgnoreCase) -or
       !(Test-Path -LiteralPath $requested -PathType Leaf) -or
       ((Get-Item -LiteralPath $requested -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){
       throw 'RELAY_PLAN_MUST_BE_LOCAL_VERIFIED_INSTALL_CONFIG'
    }
    $args+=' -RelayPlan "'+$requested+'"'
  }
 $p=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Verb RunAs -ArgumentList $args -Wait -PassThru
  $diagName='protected-'+$diagnosticId+'.error.json'
  $protectedDir=Join-Path $env:ProgramData 'MellowCodexProtectedDiagnostics'
  $diagSource=Join-Path $protectedDir $diagName
  if(Test-Path -LiteralPath $diagSource -PathType Leaf){
    $localDir=Join-Path $env:LOCALAPPDATA 'MellowCodex\setup-logs'
    [IO.Directory]::CreateDirectory($localDir)|Out-Null
    $localFile=Join-Path $localDir $diagName
    Copy-Item -LiteralPath $diagSource -Destination $localFile -ErrorAction Stop
    if($env:MELLOWCODEX_QA_LOG_DIR -and (Test-Path -LiteralPath $env:MELLOWCODEX_QA_LOG_DIR -PathType Container)){
      Copy-Item -LiteralPath $localFile -Destination (Join-Path $env:MELLOWCODEX_QA_LOG_DIR $diagName) -Force -ErrorAction Continue
    }
    Write-Output ('PROTECTED_FAILURE_DIAGNOSTIC='+$localFile)
  }
 if($p.ExitCode -ne 0){throw "Protected installer rejected or failed with exit code $($p.ExitCode)"}
 return
}
function Write-ProtectedInstallerDiagnostic($Failure){
 if($AdminDiagnosticId -notmatch '^[a-f0-9]{32}$'){throw 'DIAGNOSTIC_ID_INVALID'}
 $root=Join-Path $env:ProgramData 'MellowCodexProtectedDiagnostics'
 $adminSid=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
 $systemSid=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
 $userSid=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-545')
 $callerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User
 if(!(Test-Path -LiteralPath $root -PathType Container)){[IO.Directory]::CreateDirectory($root)|Out-Null}
 $item=Get-Item -LiteralPath $root -Force -ErrorAction Stop
 if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'DIAGNOSTIC_ROOT_LINKED'}
 $existingAcl=Get-Acl -LiteralPath $root
 $existingOwner=([Security.Principal.NTAccount]$existingAcl.Owner).Translate([Security.Principal.SecurityIdentifier]).Value
 if($existingOwner -notin @($adminSid.Value,$systemSid.Value,$callerSid.Value)){throw 'DIAGNOSTIC_ROOT_OWNER_NOT_TRUSTED'}
 $acl=New-Object System.Security.AccessControl.DirectorySecurity
 $acl.SetAccessRuleProtection($true,$false)
 $inherit=[Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
 foreach($setting in @(@($adminSid,'FullControl'),@($systemSid,'FullControl'),@($userSid,'ReadAndExecute'))){
  $rule=New-Object System.Security.AccessControl.FileSystemAccessRule($setting[0],$setting[1],$inherit,[Security.AccessControl.PropagationFlags]::None,'Allow')
  $acl.AddAccessRule($rule)
 }
 $acl.SetOwner($adminSid)
 $item.SetAccessControl($acl)
 $id=[string]$Failure.FullyQualifiedErrorId
 $msg=[string]$Failure.Exception.Message
 $msg=[regex]::Replace($msg,'(?i)(password|secret|token|auth.key)\s*[:=]\s*[^\s;]+','$1=[REDACTED]')
 if($msg.Length -gt 2048){$msg=$msg.Substring(0,2048)}
 $location=[IO.Path]::GetFileName([string]$Failure.InvocationInfo.ScriptName)
 $record=[ordered]@{
  schema=1;severity='error';phase='protected_uac';utc=[DateTime]::UtcNow.ToString('o')
  error_id=$id;message=$msg;script=$location;line=[int]$Failure.InvocationInfo.ScriptLineNumber
  run_id=$AdminDiagnosticId;owner_binding_requested=$true
 }
 $body=$record|ConvertTo-Json -Depth 4
 $dest=Join-Path $root ('protected-'+$AdminDiagnosticId+'.error.json')
 $bytes=[Text.Encoding]::UTF8.GetBytes($body)
 $stream=[IO.FileStream]::new($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
trap {
 $failure=$_
 if($AdminDiagnosticId -match '^[a-f0-9]{32}$'){
  try{Write-ProtectedInstallerDiagnostic $failure}catch{Write-Output ('PROTECTED_DIAGNOSTIC_WRITE_FAILED: '+$_.Exception.GetType().Name)}
 }else{
  Write-Output 'PROTECTED_PARENT_EXIT_FAILURE; original elevated diagnostic is in QA-LOGS when available'
 }
 Write-Output ('PROTECTED_STEP_FAILED: '+$failure.FullyQualifiedErrorId)
 exit 1
}
$originVerified=$false
if($identity.User.Value -cne $ExpectedUserSid){
 if($OriginalProcessId -le 0 -or $OriginalStartedUtcTicks -le 0){throw 'ORIGINAL_USER_PROOF_REQUIRED'}
 $original=Get-CimInstance Win32_Process -Filter ('ProcessId='+$OriginalProcessId) -ErrorAction Stop
 if(!$original){throw 'ORIGINAL_INSTALLER_EXITED'}
 $sidResult=Invoke-CimMethod -InputObject $original -MethodName GetOwnerSid -ErrorAction Stop
 if([string]$sidResult.Sid -cne $ExpectedUserSid){throw 'ORIGINAL_USER_SID_MISMATCH'}
 $originProc=Get-Process -Id $OriginalProcessId -ErrorAction Stop
 if($originProc.StartTime.ToUniversalTime().Ticks -ne $OriginalStartedUtcTicks){throw 'ORIGINAL_INSTALLER_START_MISMATCH'}
 $mySession=(Get-Process -Id $PID -ErrorAction Stop).SessionId
 if([int]$original.SessionId -ne $mySession -or $mySession -le 0){throw 'ORIGINAL_INTERACTIVE_SESSION_MISMATCH'}
 $exe=[IO.Path]::GetFullPath([string]$original.ExecutablePath)
 $trustedExe=[IO.Path]::GetFullPath((Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'))
 if(!$exe.Equals($trustedExe,[StringComparison]::OrdinalIgnoreCase)){throw 'ORIGINAL_PROCESS_IMAGE_INVALID'}
 if([string]$original.CommandLine -notmatch '(?i)-File\s+"?[^"]*install\.ps1(?:\"|\s|$)'){throw 'ORIGINAL_INSTALLER_COMMAND_MISMATCH'}
 Add-Type -AssemblyName System.Windows.Forms
 $brokerFile=if($OwnerBrokerBundle){$OwnerBrokerBundle}else{$OwnerBrokerMsi}
 $message='Authorize protected services for the ORIGINAL, different Windows account?'+[Environment]::NewLine+
  'Owner SID: '+$ExpectedUserSid+[Environment]::NewLine+
  'Guard SHA256: '+(Get-FileHash -LiteralPath $GuardBundle -Algorithm SHA256).Hash+[Environment]::NewLine+
  'Broker SHA256: '+(Get-FileHash -LiteralPath $brokerFile -Algorithm SHA256).Hash
  $dialogOwner=New-Object System.Windows.Forms.Form
  $dialogOwner.TopMost=$true
  $dialogOwner.ShowInTaskbar=$false
  $dialogOwner.Opacity=0.01
  $dialogOwner.Size=[Drawing.Size]::new(2,2)
  $dialogOwner.StartPosition=[Windows.Forms.FormStartPosition]::CenterScreen
  try {
   $dialogOwner.Show()
   $dialogOwner.Activate() | Out-Null
   $choice=[Windows.Forms.MessageBox]::Show($dialogOwner,$message,'MellowCodex administrator approval',
    [Windows.Forms.MessageBoxButtons]::YesNo,[Windows.Forms.MessageBoxIcon]::Warning)
  }finally{
   $dialogOwner.Close()
   $dialogOwner.Dispose()
  }
 if($choice -ne [Windows.Forms.DialogResult]::Yes){throw 'ADMIN_DECLINED_ORIGINAL_OWNER_BINDING'}
 $originVerified=$true
}
# BEFORE ANY Guard auth.key/service write, resolve only the fixed original-user pinned interpreter.
$managedPinnedPython=Join-Path $AgentRoot 'tools\python\cpython-3.12.16-windows-x86_64-none\python.exe'
Require-File $managedPinnedPython
$exeItem=Get-Item -LiteralPath $managedPinnedPython -Force
if(($exeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'PINNED_PYTHON_REPARSE_FORBIDDEN'}
$version=(( & $managedPinnedPython --version 2>&1 )|Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $version -cne 'Python 3.12.16'){throw ('PINNED_INTERPRETER_VERSION_MISMATCH '+$version)}
Write-Output 'PROTECTED_ORIGINAL_OWNER_PYTHON_PREFLIGHT=PASS'
# Recover only the exact known incomplete state left by previous Guard stage 6
# after the user approved UAC. Never remove or overwrite a real Guard installation.
if(!$SkipGuard -and (Test-Path -LiteralPath $guardHome -PathType Container)){
 $guardItem=Get-Item -LiteralPath $guardHome -Force -ErrorAction Stop
 if(($guardItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'GUARD_ORPHAN_LINKED_DIRECTORY_REFUSED'}
 if(Test-Path -LiteralPath (Join-Path $guardHome 'current.json')){throw 'PROTECTED_GUARD_ALREADY_INSTALLED'}
 if(Test-Path -LiteralPath (Join-Path $env:ProgramData 'MellowOwnerBroker')){throw 'PROTECTED_BROKER_STATE_PRESENT_NO_AUTOMATIC_REPAIR'}
 $brokerSvc=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction Stop
 if($brokerSvc){throw 'PROTECTED_BROKER_SERVICE_PRESENT_NO_AUTOMATIC_REPAIR'}
 $task=@(Get-ScheduledTask -TaskName 'MellowGuard*' -ErrorAction SilentlyContinue)
 if($task.Count){throw 'PROTECTED_GUARD_SCHEDULED_TASK_PRESENT_NO_AUTOMATIC_REPAIR'}
 $children=@(Get-ChildItem -LiteralPath $guardHome -Force -ErrorAction Stop)
 if($children.Count -ne 1 -or $children[0].Name -cne 'state' -or !$children[0].PSIsContainer){throw 'GUARD_ORPHAN_UNEXPECTED_HOME_CONTENTS'}
 $stateItem=Get-Item -LiteralPath $state -Force -ErrorAction Stop
 if(($stateItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'GUARD_ORPHAN_LINKED_STATE_REFUSED'}
 $stateChildren=@(Get-ChildItem -LiteralPath $state -Force -ErrorAction Stop)
 if($stateChildren.Count -ne 1 -or $stateChildren[0].Name -cne 'auth.key' -or $stateChildren[0].PSIsContainer){throw 'GUARD_ORPHAN_UNEXPECTED_STATE_CONTENTS'}
 if(($stateChildren[0].Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'GUARD_ORPHAN_LINKED_AUTH_REFUSED'}
 $orphanBackup=$guardHome+'.QA-orphan-'+[DateTime]::UtcNow.ToString('yyyyMMddHHmmss')+'-'+[guid]::NewGuid().ToString('N')
 if(Test-Path -LiteralPath $orphanBackup){throw 'GUARD_ORPHAN_BACKUP_COLLISION'}
 Move-Item -LiteralPath $guardHome -Destination $orphanBackup -ErrorAction Stop
 if(!(Test-Path -LiteralPath (Join-Path $orphanBackup 'state\auth.key'))){throw 'GUARD_ORPHAN_BACKUP_VERIFY_FAILED'}
 Write-Output ('GUARD_INCOMPLETE_AUTH_STATE_SAFELY_QUARANTINED='+$orphanBackup)
}
$payload=$null
try{
 if(!$SkipGuard){
  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $zip=[IO.Compression.ZipFile]::OpenRead($GuardBundle)
  try{
   $found=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
   foreach($entry in $zip.Entries){
    $rel=$entry.FullName.Replace('\','/')
    if(!$rel -or $rel.StartsWith('/') -or $rel -match '(^|/)\.\.?(/|$)|:|[?*<>|]' -or !$found.Add($rel)){throw 'Unsafe or duplicated Guard bundle member'}
    if($entry.Length -gt 4000000){throw 'Guard source bundle contains oversized non-source file'}
   }
  }finally{$zip.Dispose()}
  $payload=Join-Path $env:TEMP ('MellowGuard-source-'+[guid]::NewGuid().ToString('N'))
  [IO.Directory]::CreateDirectory($payload)|Out-Null
  Expand-Archive -LiteralPath $GuardBundle -DestinationPath $payload
  $manifestFile=Join-Path $payload 'bundle-manifest.json'
  Require-File $manifestFile
  $manifest=Get-Content -LiteralPath $manifestFile -Raw |ConvertFrom-Json
  if([int]$manifest.schema -ne 1 -or [string]$manifest.version -ne '0.1.1'){throw 'Unsupported Guard bundle manifest'}
  $files=@($manifest.files)
  if($files.Count -lt 14){throw 'Guard release source manifest incomplete'}
  foreach($item in $files){
   $rel=[string]$item.path
   if($rel -notmatch '^(mellow_guard|scripts)/[A-Za-z0-9_.\/-]+$|^(VERSION|pyproject.toml|requirements.lock.txt|source-manifest.json)$' -or $rel.Contains('..')){
    throw "Guard source path not allowed: $rel"
   }
   $f=Join-Path $payload ($rel.Replace('/','\'))
   Require-File $f
   Enforce-Sha $f ([string]$item.sha256)
  }
   if($RelayPlan){
     $expected=Join-Path $AgentRoot 'state\relay-onboarding.json'
     if(![IO.Path]::GetFullPath($RelayPlan).Equals([IO.Path]::GetFullPath($expected),[StringComparison]::OrdinalIgnoreCase)){
       throw 'RELAY_PLAN_MUST_BELONG_TO_NEW_INSTALLATION'
     }
     $binder=Join-Path $PSScriptRoot '..\relay\windows\Bind-NewGuardRelayPlan.ps1'
     Require-File $binder
     & $binder -GuardExtractedSource $payload -RelayPlan $RelayPlan
     if(!$?){throw 'GUARD_OAUTH_ISSUER_BINDING_FAILED'}
   }
  $allowed=@($manifest.allowed_paths)
  $targets=@($manifest.allowed_test_targets)
  if(!$allowed.Count -or !$targets.Count){throw 'Guard source manifest lacks required owner repair/test allowlists'}
  if(Test-Path (Join-Path $guardHome 'current.json')){throw 'An installed protected Guard already exists; refusing override'}
  Protect-State $state
  $auth=Join-Path $state 'auth.key'
  if(Test-Path $auth){throw 'An owner credential exists. Refusing to reuse or overwrite.'}
  $random=New-Object byte[] 48
  $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
  try{$rng.GetBytes($random)}finally{$rng.Dispose()}
  $text=[Convert]::ToBase64String($random)
  [IO.File]::WriteAllText($auth,$text,[Text.Encoding]::ASCII)
  $fileAcl=Get-Acl -LiteralPath $auth
  $fileAcl.SetAccessRuleProtection($true,$false)
  foreach($sid in @(
    [Security.Principal.WindowsIdentity]::GetCurrent().User,
    (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')))){
    $rule=New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl','Allow')
    $fileAcl.AddAccessRule($rule)
  }
  Set-Acl -LiteralPath $auth -AclObject $fileAcl
   $basePython=$managedPinnedPython
   Write-Output 'PROTECTED_MANAGED_PYTHON_RESOLVED=TRUE'
   $relayArgs=@{}
   if($RelayPlan){
     $r=Get-Content -LiteralPath $RelayPlan -Raw|ConvertFrom-Json
     $relayArgs=@{
       EnableOAuth=$true;EnableGateway=$true;EnableRelay=$true
       AllowedRedirectUris=@($r.allowed_redirect_uris)
       RelaySSH=[string]$r.ssh_executable
       RelayIdentityFile=[string]$r.identity_file
       RelayKnownHosts=[string]$r.known_hosts
       RelayUser=[string]$r.ssh_user
       RelayHost=[string]$r.ssh_host
       RelayRemotePort=18897;RelayLocalPort=8896
     }
   }
  & (Join-Path $payload 'scripts\install.ps1') -SourceRoot $payload -GuardHome $guardHome -HubRoot $AgentRoot -HubSource $repo -HubPython $python -StagingRoot (Join-Path $AgentRoot 'candidates') -BasePython $basePython -UvExe $uv -TestPython $basePython -AllowedPaths $allowed -AllowedTestTargets $targets @relayArgs
  if($LASTEXITCODE -ne 0){throw 'Independent Guard source installer reported failure'}
   Write-Output 'GUARD_TASK_DEFERRED_TO_ORIGINAL_ORDINARY_USER'
 }
 if($OwnerBrokerBundle){
  $brokerScript=Join-Path $PSScriptRoot 'Install-PortableOwnerBroker.ps1'
  Require-File $brokerScript
  & $brokerScript -BrokerBundle $OwnerBrokerBundle -ExpectedUserSid $ExpectedUserSid -ConsentFromVisibleWizard:$OwnerBrokerConsentFromWizard -OriginalOwnerVerified:$originVerified
  if(!$?){throw 'Portable protected broker installation did not complete'}
 }else{
  Write-Host 'Installing signed owner-approved OwnerBroker MSI...' -ForegroundColor Cyan
  $p=Start-Process -FilePath 'msiexec.exe' -ArgumentList @('/i',('"' + $OwnerBrokerMsi + '"'),'/passive','/norestart') -Wait -PassThru
  if($p.ExitCode -ne 0){throw "OwnerBroker MSI returned exit code $($p.ExitCode)"}
 }
  if($RelayPlan){
    if($SkipGuard){throw 'RELAY_REQUIRES_GUARD_INSTALL'}
    $plan=Get-Content -LiteralPath $RelayPlan -Raw|ConvertFrom-Json
    $installed=Get-Content -LiteralPath (Join-Path $guardHome 'current.json') -Raw|ConvertFrom-Json
    if(-not [bool]$installed.oauth.enabled -or -not [bool]$installed.gateway_enabled -or
       -not [bool]$installed.relay_enabled -or
       [string]$installed.relay.host -cne [string]$plan.ssh_host -or
       [string]$installed.relay.user -cne [string]$plan.ssh_user -or
       [int]$installed.relay.remote_port -ne 18897 -or [int]$installed.relay.local_port -ne 8896){
       throw 'GUARD_RELAY_INSTALLED_SETTINGS_MISMATCH'
    }
    $redirects=@($installed.oauth.allowed_redirect_uris)
    if($redirects.Count -ne @($plan.allowed_redirect_uris).Count){
       throw 'RELAY_REDIRECT_ALLOWLIST_MISMATCH'
    }
    foreach($callback in @($plan.allowed_redirect_uris)){
       if($redirects -cnotcontains [string]$callback){throw 'RELAY_REDIRECT_ALLOWLIST_MISMATCH'}
    }
    if([string]$installed.release_id -notmatch '^0\.1\.1-[a-f0-9]{16}$'){throw 'RELAY_RELEASE_ID_INVALID'}
    $oauth=Join-Path (Join-Path (Join-Path $guardHome 'releases') ([string]$installed.release_id)) 'mellow_guard\oauth.py'
    Require-File $oauth
    if(!([IO.File]::ReadAllText($oauth).Contains(('BASE = "'+[string]$plan.public_url+'"')))){
       throw 'RELAY_PUBLIC_OAUTH_ISSUER_MISMATCH'
    }
    Write-Output 'GUARD_RELAY_OAUTH_SSH_CONFIG_READBACK=VERIFIED; remote transport/consent NOT TESTED'
  }
  if(!$SkipGuard){
   Rebind-GuardOwnerAccess $guardHome $ExpectedUserSid
   Write-Output 'GUARD_ACL_BOUND_TO_ORIGINAL_USER_START_DEFERRED=TRUE'
  }
 Write-Host 'Protected installation step finished. Normal MellowCodex first-run remains under ordinary user token.' -ForegroundColor Green
}finally{
 if($payload -and (Test-Path $payload)){Remove-Item -LiteralPath $payload -Recurse -Force -ErrorAction SilentlyContinue}
}
