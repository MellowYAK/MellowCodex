[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$AgentRoot,
 [string]$GuardBundle='',
 [string]$OwnerBrokerBundle='',
 [string]$OwnerBrokerMsi='',
 [string]$OwnerBrokerSha256='',
 [string]$ExpectedUserSid='',
 [switch]$SkipGuard,
 [switch]$DryRun
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
 $args='-NoProfile -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -AgentRoot "'+$AgentRoot+'" -ExpectedUserSid '+$ExpectedUserSid
 if($OwnerBrokerBundle){$args+=' -OwnerBrokerBundle "'+$OwnerBrokerBundle+'"'}
 else{$args+=' -OwnerBrokerMsi "'+$OwnerBrokerMsi+'" -OwnerBrokerSha256 '+$OwnerBrokerSha256}
 if(!$SkipGuard){$args+=' -GuardBundle "'+$GuardBundle+'"'}else{$args+=' -SkipGuard'}
 $p=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Verb RunAs -ArgumentList $args -Wait -PassThru
 if($p.ExitCode -ne 0){throw "Protected installer rejected or failed with exit code $($p.ExitCode)"}
 return
}
if($identity.User.Value -ne $ExpectedUserSid){
 throw 'UAC changed Windows account identity. Run initial setup from the intended admin account; credentials cannot be granted to another user silently.'
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
  $basePython=(& $uv python find 3.12.16 | Select-Object -Last 1).Trim()
  if($LASTEXITCODE -ne 0 -or !(Test-Path $basePython)){throw 'Pinned independent Python 3.12.16 could not be resolved'}
  if(!$basePython.StartsWith((Join-Path $AgentRoot 'tools\python')+'\',[StringComparison]::OrdinalIgnoreCase)){
   throw 'Guard base interpreter must be pinned inside the new installation'
  }
  & (Join-Path $payload 'scripts\install.ps1') -SourceRoot $payload -GuardHome $guardHome -HubRoot $AgentRoot -HubSource $repo -HubPython $python -StagingRoot (Join-Path $AgentRoot 'candidates') -BasePython $basePython -UvExe $uv -TestPython $basePython -AllowedPaths $allowed -AllowedTestTargets $targets
  if($LASTEXITCODE -ne 0){throw 'Independent Guard source installer reported failure'}
  & (Join-Path $payload 'scripts\register-startup.ps1') -GuardHome $guardHome
  if($LASTEXITCODE -ne 0){throw 'Guard owned startup task registration failed'}
 }
 if($OwnerBrokerBundle){
  $brokerScript=Join-Path $PSScriptRoot 'Install-PortableOwnerBroker.ps1'
  Require-File $brokerScript
  & $brokerScript -BrokerBundle $OwnerBrokerBundle -ExpectedUserSid $ExpectedUserSid
  if(!$?){throw 'Portable protected broker installation did not complete'}
 }else{
  Write-Host 'Installing signed owner-approved OwnerBroker MSI...' -ForegroundColor Cyan
  $p=Start-Process -FilePath 'msiexec.exe' -ArgumentList @('/i',('"' + $OwnerBrokerMsi + '"'),'/passive','/norestart') -Wait -PassThru
  if($p.ExitCode -ne 0){throw "OwnerBroker MSI returned exit code $($p.ExitCode)"}
 }
 if(!$SkipGuard){
  $release=Get-Content -LiteralPath (Join-Path $guardHome 'current.json') -Raw|ConvertFrom-Json
  $script=Join-Path (Join-Path (Join-Path $guardHome 'releases') ([string]$release.release_id)) 'scripts\start.ps1'
  Require-File $script
  & $script -GuardHome $guardHome
  if($LASTEXITCODE -ne 0){throw 'Guard start was not verified'}
 }
 Write-Host 'Protected installation step finished. Normal MellowCodex first-run remains under ordinary user token.' -ForegroundColor Green
}finally{
 if($payload -and (Test-Path $payload)){Remove-Item -LiteralPath $payload -Recurse -Force -ErrorAction SilentlyContinue}
}