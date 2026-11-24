[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$BrokerBundle,
 [Parameter(Mandatory=$true)][string]$ExpectedUserSid,
 [switch]$DryRun
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(!(Test-Path -LiteralPath $BrokerBundle -PathType Leaf)){throw 'OwnerBroker package missing'}
if(!(Test-Path -LiteralPath ($BrokerBundle+'.sha256') -PathType Leaf)){throw 'OwnerBroker SHA256 sidecar missing'}
$sha=(Get-Content -LiteralPath ($BrokerBundle+'.sha256') -Raw).Trim()
if($sha -notmatch '^[0-9a-fA-F]{64}$' -or (Get-FileHash -LiteralPath $BrokerBundle -Algorithm SHA256).Hash -ine $sha){
 throw 'OwnerBroker package SHA256 mismatch'
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$expectedMembers=@('bundle-manifest.json','bin/MellowOwnerService.exe','bin/MellowOwnerControl.exe','bin/MellowOwnerClient.exe')
$z=[IO.Compression.ZipFile]::OpenRead($BrokerBundle)
try{
 $members=@($z.Entries|Where-Object { $_.FullName -notin @('bin/','bin\') }|ForEach-Object {$_.FullName.Replace('\','/')})
 if($members.Count -ne $expectedMembers.Count){throw 'Broker bundle contains unexpected files'}
 foreach($member in $members){if($member -notin $expectedMembers){throw "Broker bundle contains untrusted member: $member"}}
}finally{$z.Dispose()}
$stage=Join-Path $env:TEMP ('MC-OwnerBroker-install-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($stage)|Out-Null
try{
 [IO.Compression.ZipFile]::ExtractToDirectory($BrokerBundle,$stage)
 $manifest=Get-Content -LiteralPath (Join-Path $stage 'bundle-manifest.json') -Raw|ConvertFrom-Json
 if([int]$manifest.schema -ne 1 -or [string]$manifest.product -cne 'MellowOwnerBroker' -or
    [string]$manifest.service -cne 'MellowOwnerBroker' -or [string]$manifest.run_as -cne 'LocalSystem' -or
    [int]$manifest.protocol -lt 1 -or [int]$manifest.protocol -gt 10 -or
    $manifest.signed -ne $false){throw 'Unexpected broker source/privilege protocol'}
 $files=@($manifest.files)
 if($files.Count -ne 3){throw 'Broker package must contain exactly three native executables'}
 foreach($item in $files){
  $rel=([string]$item.path).Replace('\','/')
  if($rel -notin @('bin/MellowOwnerService.exe','bin/MellowOwnerControl.exe','bin/MellowOwnerClient.exe')){
   throw 'Broker source member outside exact allowlist'
  }
  $f=Join-Path $stage ($rel.Replace('/','\'))
  if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw "Missing broker source: $rel"}
  if([string]$item.sha256 -notmatch '^[0-9a-fA-F]{64}$' -or
     (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash -ine [string]$item.sha256){
    throw "Broker member SHA256 mismatch: $rel"
  }
 }
 $home=Join-Path $env:ProgramData 'MellowOwnerBroker'
 $service=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction SilentlyContinue
 if($service -or (Test-Path -LiteralPath $home)){throw 'Existing owner service or directory must not be overwritten'}
 if($DryRun){Write-Host "DRY_RUN verified unsigned native broker bundle protocol=$($manifest.protocol)";return}
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 $principal=New-Object Security.Principal.WindowsPrincipal($identity)
 if(!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'OwnerBroker installation requires explicit Windows admin authorization'}
 if($identity.User.Value -cne $ExpectedUserSid){throw 'Windows elevation switched the user; refusing broker owner identity mismatch'}
 Write-Warning 'This is an UNSIGNED owner-provided broker. Install only if the verified source machine and bundle SHA256 are trusted.'
 $approved=Read-Host 'Type INSTALL UNSIGNED BROKER to authorize this exact package'
 if($approved -cne 'INSTALL UNSIGNED BROKER'){throw 'Owner declined unsigned protected service installation'}
 [IO.Directory]::CreateDirectory((Join-Path $home 'bin'))|Out-Null
 $acl=New-Object System.Security.AccessControl.DirectorySecurity
 $acl.SetAccessRuleProtection($true,$false)
 $inherit=[Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
 foreach($sid in @(
   (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')),
   (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')))){
  $rule=New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl',$inherit,[Security.AccessControl.PropagationFlags]::None,'Allow')
  $acl.AddAccessRule($rule)
 }
 $ownerSid=New-Object System.Security.Principal.SecurityIdentifier($ExpectedUserSid)
 $readRule=New-Object System.Security.AccessControl.FileSystemAccessRule($ownerSid,'ReadAndExecute',$inherit,[Security.AccessControl.PropagationFlags]::None,'Allow')
 $acl.AddAccessRule($readRule)
 (Get-Item -LiteralPath $home).SetAccessControl($acl)
 (Get-Item -LiteralPath (Join-Path $home 'bin')).SetAccessControl($acl)
 foreach($name in @('MellowOwnerService.exe','MellowOwnerControl.exe','MellowOwnerClient.exe')){
  Copy-Item -LiteralPath (Join-Path (Join-Path $stage 'bin') $name) -Destination (Join-Path (Join-Path $home 'bin') $name)
 }
 $config=@{protocol=[int]$manifest.protocol;owner_sid=$ExpectedUserSid}
 [IO.File]::WriteAllText((Join-Path $home 'config.json'),($config|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
 $exe=Join-Path (Join-Path $home 'bin') 'MellowOwnerService.exe'
 $sc=Join-Path $env:SystemRoot 'System32\sc.exe'
 & $sc create 'MellowOwnerBroker' ('binPath= '+$exe) 'start= auto' 'obj= LocalSystem'
 if($LASTEXITCODE -ne 0){throw 'Windows service installation rejected; inspect SCM rights'}
 & $sc start 'MellowOwnerBroker'
 if($LASTEXITCODE -ne 0){throw 'Windows OwnerBroker startup failed; do not claim installation complete'}
 $installed=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction Stop
 if([string]$installed.PathName -ine $exe -or [string]$installed.StartName -ine 'LocalSystem' -or
    [string]$installed.State -ine 'Running'){throw 'Broker Windows service readback identity or readiness mismatch'}
 Write-Host 'Owned MellowOwnerBroker service installed with newly generated owner SID; no old state copied.' -ForegroundColor Green
}finally{Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue}