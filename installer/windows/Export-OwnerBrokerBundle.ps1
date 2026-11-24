[CmdletBinding()]
param(
 [string]$BrokerHome=(Join-Path $env:ProgramData 'MellowOwnerBroker'),
 [string]$OutputDirectory=(Join-Path (Join-Path $env:USERPROFILE 'Downloads') 'MellowCodex-Install-Payload'),
 [switch]$DryRun
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$BrokerHome=[IO.Path]::GetFullPath($BrokerHome).TrimEnd('\')
$service=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction Stop
$expected=Join-Path $BrokerHome 'bin\MellowOwnerService.exe'
if(!$service -or [string]$service.PathName -ine $expected -or [string]$service.StartName -ine 'LocalSystem'){
 throw 'Only exact active MellowOwnerBroker LocalSystem service is accepted for binary source export'
}
$config=Join-Path $BrokerHome 'config.json'
if(!(Test-Path -LiteralPath $config -PathType Leaf)){throw 'Broker protocol manifest missing'}
$configuration=Get-Content -LiteralPath $config -Raw|ConvertFrom-Json
if([int]$configuration.protocol -lt 1 -or [int]$configuration.protocol -gt 10){throw 'Unknown broker wire protocol'}
$items=@('MellowOwnerService.exe','MellowOwnerClient.exe','MellowOwnerControl.exe')
$files=New-Object 'System.Collections.Generic.List[object]'
foreach($name in $items){
 $f=Join-Path (Join-Path $BrokerHome 'bin') $name
 if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw "Required broker binary missing: $name"}
 $info=Get-Item -LiteralPath $f -Force
 if(($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $info.Length -gt 20000000){throw 'Unsafe broker binary member'}
 $files.Add(@{path=('bin/'+$name);sha256=(Get-FileHash $f -Algorithm SHA256).Hash.ToLowerInvariant();size=$info.Length})
}
$out=Join-Path $OutputDirectory 'MellowOwnerBroker-unsigned-native-source.zip'
if((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath ($out+'.sha256'))){throw "Broker export already exists; refusing overwrite: $out"}
Write-Warning 'This locally built OwnerBroker service is NOT Authenticode-signed. It must not be published as a trusted binary or silently installed.'
Write-Host "Broker protocol=$($configuration.protocol), native_programs=$($files.Count)"
Write-Host 'The old owner SID, Guard secrets and configuration will NEVER be copied into the portable bundle.'
if($DryRun){Write-Host "DRY_RUN bundle=$out";return}
[IO.Directory]::CreateDirectory($OutputDirectory)|Out-Null
$stage=Join-Path $env:TEMP ('OwnerBroker-export-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory((Join-Path $stage 'bin'))|Out-Null
try{
 foreach($item in $files){
  $name=Split-Path ([string]$item.path) -Leaf
  $source=Join-Path (Join-Path $BrokerHome 'bin') $name
  $target=Join-Path (Join-Path $stage 'bin') $name
  Copy-Item -LiteralPath $source -Destination $target
  if((Get-FileHash $target -Algorithm SHA256).Hash -ine [string]$item.sha256){throw 'Broker bundle copy SHA mismatch'}
 }
 $manifest=@{
  schema=1;product='MellowOwnerBroker';protocol=[int]$configuration.protocol
  service='MellowOwnerBroker';run_as='LocalSystem'
  signed=$false;files=$files.ToArray();created_at=[DateTime]::UtcNow.ToString('o')
  owner_sid_policy='FRESH_ON_TARGET';source_kind='owner-workstation-native-binaries'
  verified_clean_pc='NOT_TESTED'
 }
 [IO.File]::WriteAllText((Join-Path $stage 'bundle-manifest.json'),($manifest|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
 Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $out -CompressionLevel Optimal
 $sha=(Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash.ToLowerInvariant()
 [IO.File]::WriteAllText(($out+'.sha256'),$sha,[Text.Encoding]::ASCII)
 Write-Host "BROKER_BUNDLE=$out"
 Write-Host "BROKER_BUNDLE_SHA256=$sha"
}finally{Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue}