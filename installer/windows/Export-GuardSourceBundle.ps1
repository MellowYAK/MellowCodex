[CmdletBinding()]
param(
 [string]$GuardHome=(Join-Path $env:ProgramData 'MellowGuard'),
 [string]$OutputDirectory=(Join-Path (Join-Path $env:USERPROFILE 'Downloads') 'MellowCodex-Install-Payload'),
 [switch]$DryRun
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$GuardHome=[IO.Path]::GetFullPath($GuardHome).TrimEnd('\')
$current=Join-Path $GuardHome 'current.json'
if(!(Test-Path -LiteralPath $current -PathType Leaf)){throw 'There is no installed Guard release to export'}
$c=Get-Content -LiteralPath $current -Raw|ConvertFrom-Json
$id=[string]$c.release_id
if($id -notmatch '^0\.1\.1-[0-9a-f]{16}$'){throw 'Only the currently approved Guard 0.1.1 source release may be exported'}
$release=[IO.Path]::GetFullPath((Join-Path (Join-Path $GuardHome 'releases') $id))
$prefix=[IO.Path]::GetFullPath((Join-Path $GuardHome 'releases')).TrimEnd('\')+'\'
if(!$release.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Guard release is outside its immutable store'}
if(!(Test-Path (Join-Path $release 'mellow_guard\core.py'))){throw 'Guard source release incomplete'}
$allowed=@($c.allowed_paths)
$targets=@($c.allowed_test_targets)
if(!$allowed.Count -or !$targets.Count){throw 'Installed Guard repair/test allowlists unavailable'}
$files=New-Object 'System.Collections.Generic.List[object]'
$allowedRoots=@('mellow_guard','scripts')
foreach($part in $allowedRoots){
 $folder=Join-Path $release $part
 if(!(Test-Path $folder -PathType Container)){throw "Missing required Guard source: $part"}
 foreach($file in @(Get-ChildItem -LiteralPath $folder -File -Recurse)){
  if(($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Linked Guard source file forbidden'}
  if($file.FullName -match '\\__pycache__\\' -or $file.Extension -notin @('.py','.ps1','.json','.txt')){continue}
  $relative=$file.FullName.Substring($release.Length+1).Replace('\','/')
  $files.Add(@{path=$relative;sha256=(Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant();size=$file.Length})
 }
}
foreach($name in @('VERSION','requirements.lock.txt','pyproject.toml','source-manifest.json')){
 $f=Join-Path $release $name
 if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw "Required Guard release manifest missing: $name"}
 $files.Add(@{path=$name;sha256=(Get-FileHash $f -Algorithm SHA256).Hash.ToLowerInvariant();size=(Get-Item $f).Length})
}
if($files.Count -lt 14){throw 'Insufficient source members for Guard bundle'}
$out=Join-Path $OutputDirectory ('MellowGuard-source-'+$id+'.zip')
if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath ($out+'.sha256'))){throw "Output exists, refusing overwrite: $out"}
Write-Host "Guard version=$($c.version), source_files=$($files.Count), repair_allowlist=$($allowed.Count), test_allowlist=$($targets.Count)"
Write-Host 'No installed Python runtime, Guard state DB, auth token, password, secrets, or user credentials will be included.'
if($DryRun){Write-Host "DRY_RUN output=$out";return}
[IO.Directory]::CreateDirectory($OutputDirectory)|Out-Null
$staging=Join-Path $env:TEMP ('MC-Guard-Export-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($staging)|Out-Null
try{
 foreach($entry in $files){
  $src=Join-Path $release ([string]$entry.path).Replace('/','\')
  $dst=Join-Path $staging ([string]$entry.path).Replace('/','\')
  [IO.Directory]::CreateDirectory((Split-Path -Parent $dst))|Out-Null
  Copy-Item -LiteralPath $src -Destination $dst
  if((Get-FileHash $dst -Algorithm SHA256).Hash -ine [string]$entry.sha256){throw 'Guard export source mismatch after copy'}
 }
 $manifest=@{
  schema=1;version='0.1.1';release_id=$id;created_at=[DateTime]::UtcNow.ToString('o')
  allowed_paths=$allowed;allowed_test_targets=$targets
  files=$files.ToArray()
  source_kind='installed-immutable-Guard-code-only';owner_acceptance='PENDING'
 }
 [IO.File]::WriteAllText((Join-Path $staging 'bundle-manifest.json'),($manifest|ConvertTo-Json -Depth 7),[Text.UTF8Encoding]::new($false))
 Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $out -CompressionLevel Optimal
 if(!(Test-Path -LiteralPath $out)){throw 'Guard bundle not created'}
 $sha=(Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash.ToLowerInvariant()
 [IO.File]::WriteAllText(($out+'.sha256'),$sha,[Text.Encoding]::ASCII)
 Write-Host "GUARD_SOURCE_BUNDLE=$out"
 Write-Host "GUARD_SOURCE_SHA256=$sha"
}finally{
 Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
}