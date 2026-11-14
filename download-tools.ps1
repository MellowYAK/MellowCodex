[CmdletBinding()]
param([string]$AgentRoot='E:\AI')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$lock=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'tools-download-lock.json') -Raw |ConvertFrom-Json
$dirs=@('downloads','tools','state','cache')
foreach($d in $dirs){New-Item -ItemType Directory -Path (Join-Path $AgentRoot $d) -Force|Out-Null}
foreach($item in $lock.components){
  $uri=[uri]$item.url
  if($uri.Scheme -ne 'https' -or $uri.Host -ne 'github.com'){throw 'Untrusted tool-download host'}
  if($item.sha256 -notmatch '^[a-f0-9]{64}$'){throw 'Malformed locked SHA256'}
  $archive=Join-Path (Join-Path $AgentRoot 'downloads') $item.asset
  if(!(Test-Path -LiteralPath $archive)){
    & curl.exe --fail --location --retry 3 --silent --show-error --output $archive $item.url
    if($LASTEXITCODE -ne 0){throw ('Download failed: '+$item.name)}
  }
  $digest=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
  if($digest -cne $item.sha256){throw ('SHA256 mismatch for '+$item.name)}
  $target=Join-Path (Join-Path $AgentRoot 'tools') $item.name
  New-Item -ItemType Directory -Path $target -Force|Out-Null
  Expand-Archive -LiteralPath $archive -DestinationPath $target -Force
  Write-Output ($item.name+' '+$item.version+' verified')
}
