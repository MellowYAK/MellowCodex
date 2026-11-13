[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$root='E:\AI'
$state=Join-Path $root 'state\mcp-recovery-handoff.json'
$reconcile=Join-Path $PSScriptRoot 'reconcile-services.ps1'
function Save([string]$phase,[string]$detail) {
  $value=@{time=(Get-Date).ToUniversalTime().ToString('o');phase=$phase;detail=$detail;check_only=[bool]$CheckOnly}
  $tmp=$state+'.tmp';$value|ConvertTo-Json|Set-Content -LiteralPath $tmp -Encoding UTF8;Move-Item -LiteralPath $tmp -Destination $state -Force
}
function Probe {
  $result=@{}
  foreach($port in @(8876,8897,8898,8896)) {
    $tcp=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    $result["$port"]= [bool]$tcp
  }
  return $result
}
try {
  $before=Probe
  if(@($before.Values|Where-Object{!$_}).Count -eq 0){Save 'already_listening' 'All four local transports listening; no action';exit 0}
  if($CheckOnly){Save 'needs_recovery' ('Missing ports: '+(($before.Keys|Where-Object{-not $before[$_]}) -join ','));exit 2}
  if((Test-Path "$root\state\agent-manual-stop") -or (Test-Path "$root\state\mcp-manual-stop")) {Save 'owner_paused' 'Manual stop markers present; not overridden';exit 3}
  $last=@{};if(Test-Path $state){try{$last=Get-Content $state -Raw|ConvertFrom-Json}catch{}}
  if($last.time -and $last.phase -in @('reconciling','failed','cooldown')){try{if(((Get-Date).ToUniversalTime()-[datetime]$last.time).TotalSeconds -lt 90){Write-Output 'Recent recovery attempt; no automatic retry within cooldown';exit 4}}catch{}}
  Save 'reconciling' 'Invoking installed authorized reconcile policy once'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $reconcile -Action Reconcile -Service mcp
  if($LASTEXITCODE -ne 0){throw "Reconciler exited $LASTEXITCODE"}
  $after=Probe
  if(@($after.Values|Where-Object{!$_}).Count){throw ('Missing ports after reconcile: '+(($after.Keys|Where-Object{-not $after[$_]}) -join ','))}
  Save 'local_restored' 'Local listeners restored; external MCP/OAuth reconnection must be verified by actual remote round trip'
  exit 0
}catch{Save 'failed' $_.Exception.Message;Write-Error $_;exit 1}