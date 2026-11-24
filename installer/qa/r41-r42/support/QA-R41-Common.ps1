Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$script:Share=Split-Path -Parent $PSScriptRoot
$script:QaLogs=Join-Path $script:Share 'QA-LOGS'
$script:Zip=Join-Path $PSScriptRoot 'MellowCodex-R41-3STEP-complete-source.zip'
$script:ExpectedZipSha='580E647F4CA3E8C936FDF0170874CB8F0AA189B612936CF1F6851FC41AE7C53A'
$script:StageSource=Join-Path $env:LOCALAPPDATA 'MellowCodexQA\R41\source'
$script:AgentRoot=Join-Path $env:LOCALAPPDATA 'MellowCodexData'
$script:OwnerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
function Assert-OrdinaryGuestUser {
 if(!$env:LOCALAPPDATA -or !$env:USERPROFILE){throw 'QA_LOCAL_WINDOWS_USER_PROFILE_REQUIRED'}
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 $principal=[Security.Principal.WindowsPrincipal]::new($identity)
 if($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
  throw 'QA_INSTALL_PHASE_REQUIRES_ORIGINAL_NON_ELEVATED_USER'
 }
 $manufacturer=Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
 if([string]$manufacturer.Manufacturer -notmatch '(?i)VMware'){throw 'QA_VMWARE_GUEST_REQUIRED'}
 if(!(Get-Service -Name VMTools -ErrorAction SilentlyContinue)){throw 'QA_VMWARE_TOOLS_SERVICE_REQUIRED'}
}
function Assert-ArchiveHash {
 if(!(Test-Path -LiteralPath $script:Zip -PathType Leaf)){throw 'QA_R41_ARCHIVE_NOT_FOUND'}
 $sha=(Get-FileHash -LiteralPath $script:Zip -Algorithm SHA256).Hash
 if($sha -ne $script:ExpectedZipSha){throw 'QA_R41_SOURCE_ZIP_SHA256_MISMATCH'}
 $side=$script:Zip+'.sha256'
 if(!(Test-Path -LiteralPath $side -PathType Leaf)){throw 'QA_R41_SOURCE_SHA_SIDECAR_MISSING'}
 if((Get-Content -LiteralPath $side -Raw).Trim() -ine $sha){throw 'QA_R41_SOURCE_SIDECAR_INVALID'}
}
function Assert-StagedSource {
 Assert-ArchiveHash
 $manifestFile=Join-Path $script:StageSource 'SOURCE-MANIFEST.json'
 if(!(Test-Path -LiteralPath $manifestFile -PathType Leaf)){throw 'QA_STAGE1_SOURCE_EXTRACT_MISSING'}
 $m=Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8|ConvertFrom-Json
 if($m.schema -ne 1 -or $m.repository -ne 'MellowCodex' -or @($m.files).Count -ne 626){throw 'QA_SOURCE_MANIFEST_INVALID'}
 foreach($row in $m.files){
  $rel=[string]$row.path
  if(!$rel -or $rel -match '(^|[/\\])\.\.([/\\]|$)' -or [IO.Path]::IsPathRooted($rel)){throw 'QA_SOURCE_MEMBER_UNSAFE'}
  $file=Join-Path $script:StageSource $rel
  if(!(Test-Path -LiteralPath $file -PathType Leaf)){throw ('QA_SOURCE_FILE_MISSING '+$rel)}
  if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ine [string]$row.sha256){throw ('QA_SOURCE_SHA_MISMATCH '+$rel)}
 }
 $bundles=@(Get-ChildItem -LiteralPath (Join-Path $script:StageSource 'payload') -File -Filter 'MellowGuard-source-*.zip')
 $bundles+=@(Get-Item -LiteralPath (Join-Path $script:StageSource 'payload\MellowOwnerBroker-unsigned-native-source.zip') -ErrorAction Stop)
 if($bundles.Count -ne 2){throw 'QA_PROTECTED_PACKAGES_MISSING'}
 foreach($file in $bundles){
  $side=$file.FullName+'.sha256'
  if(!(Test-Path $side) -or (Get-FileHash $file.FullName -Algorithm SHA256).Hash -ine (Get-Content $side -Raw).Trim()){throw ('QA_PROTECTED_PACKAGE_HASH_INVALID '+$file.Name)}
 }
}
function Assert-PreviousPhase([int]$Number){
 $file=Join-Path $script:QaLogs ('INSTALL-'+$Number+'-SUCCESS.json')
 if(!(Test-Path -LiteralPath $file -PathType Leaf)){throw ('QA_PREVIOUS_PHASE_NOT_SUCCESSFUL_'+$Number)}
 $receipt=Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
 if($receipt.status -ne 'PASS' -or [string]$receipt.owner_sid -cne $script:OwnerSid -or
    [string]$receipt.source_sha256 -cne $script:ExpectedZipSha){throw ('QA_PREVIOUS_PHASE_OWNER_OR_SOURCE_MISMATCH_'+$Number)}
}
function Invoke-QAPhase([int]$Phase,[scriptblock]$Action){
 if($Phase -notin @(1,2,3)){throw 'QA_PHASE_NUMBER_INVALID'}
 [IO.Directory]::CreateDirectory($script:QaLogs)|Out-Null
 $env:MELLOWCODEX_QA_LOG_DIR=$script:QaLogs
 $runId=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
 $file=Join-Path $script:QaLogs ('INSTALL-'+$Phase+'-'+$runId+'.log')
 $ok=$false;$message='';$transcribing=$false
 try{
  Start-Transcript -LiteralPath $file -Force -ErrorAction Stop|Out-Null
  $transcribing=$true
  Write-Host ('INSTALL-'+$Phase+' START '+[DateTime]::Now.ToString('o'))
  Write-Host ('QA_LOG_PATH='+$file)
  Assert-OrdinaryGuestUser
  & $Action
  $ok=$true
  Write-Host ('INSTALL-'+$Phase+' PASS')
 }catch{
  $message=([string]$_.Exception.Message)
  Write-Host ('INSTALL-'+$Phase+' FAILED: '+$message) -ForegroundColor Red
  Write-Host ('ERROR_ID='+$_.FullyQualifiedErrorId)
  Write-Host ('ERROR_LOCATION='+[IO.Path]::GetFileName([string]$_.InvocationInfo.ScriptName)+':'+$_.InvocationInfo.ScriptLineNumber)
 }finally{
  $receipt=[ordered]@{
   phase=$Phase;status=$(if($ok){'PASS'}else{'FAIL'});run_id=$runId;utc=[DateTime]::UtcNow.ToString('o')
   owner_sid=$script:OwnerSid;source_sha256=$script:ExpectedZipSha
   error=$message;transcript=[IO.Path]::GetFileName($file)
  }
  $json=$receipt|ConvertTo-Json -Depth 3
  $latest=Join-Path $script:QaLogs ('INSTALL-'+$Phase+'-LATEST.json')
  try{
   $temp=$latest+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
   [IO.File]::WriteAllText($temp,$json,[Text.UTF8Encoding]::new($false))
   Move-Item -LiteralPath $temp -Destination $latest -Force -ErrorAction Stop
   if($ok){
    Copy-Item -LiteralPath $latest -Destination (Join-Path $script:QaLogs ('INSTALL-'+$Phase+'-SUCCESS.json')) -Force
   }
  }catch{Write-Host ('QA_RECEIPT_WRITE_ERROR='+$_.Exception.Message)}
  if($transcribing){try{Stop-Transcript|Out-Null}catch{}}
 }
 if($ok){exit 0}else{exit 1}
}