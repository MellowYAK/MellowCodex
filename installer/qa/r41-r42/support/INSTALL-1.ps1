. (Join-Path $PSScriptRoot 'QA-R41-Common.ps1')
Invoke-QAPhase 1 {
 Assert-ArchiveHash
 $verifier=Join-Path $PSScriptRoot 'QA-R41-VerifyPrerequisites.ps1'
 if(!(Test-Path -LiteralPath $verifier -PathType Leaf)){throw 'PHASE1_STRICT_VERIFIER_MISSING'}
 if(Test-Path -LiteralPath $script:AgentRoot -PathType Container){
  Write-Host 'INSTALL1_EXISTING_ROOT_FOUND_NO_DELETE_NO_REDOWNLOAD=TRUE'
  Assert-StagedSource
  & $verifier -InstallRoot $script:AgentRoot -SourceRoot $script:StageSource
  if(!$?){throw 'INSTALL1_REUSE_STRICT_VERIFICATION_FAILED'}
  Write-Host 'INSTALL1_RESUMED_EXISTING_PREREQUISITES=TRUE'
  return
 }
 if(Test-Path -LiteralPath $script:AgentRoot){
  $broker=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction SilentlyContinue
  $guardDir=Join-Path $env:ProgramData 'MellowGuard'
  $brokerDir=Join-Path $env:ProgramData 'MellowOwnerBroker'
  $guardFound=Test-Path -LiteralPath $guardDir
  $brokerFolderFound=Test-Path -LiteralPath $brokerDir
  Write-Host ('PREFLIGHT_PREVIOUS_GUARD_DIRECTORY_EXISTS='+$guardFound)
  Write-Host ('PREFLIGHT_PREVIOUS_GUARD_RELEASE_EXISTS='+(Test-Path -LiteralPath (Join-Path $guardDir 'current.json')))
  Write-Host ('PREFLIGHT_PREVIOUS_BROKER_DIRECTORY_EXISTS='+$brokerFolderFound)
  Write-Host ('PREFLIGHT_PREVIOUS_BROKER_SERVICE_EXISTS='+[bool]$broker)
  if($broker){
   Write-Host ('PREFLIGHT_PREVIOUS_BROKER_SERVICE_STATE='+[string]$broker.State)
   Write-Host ('PREFLIGHT_PREVIOUS_BROKER_SERVICE_ACCOUNT='+[string]$broker.StartName)
  }
  if($broker -or $guardFound -or $brokerFolderFound){
   throw 'PREVIOUS_PROTECTED_INSTALL_STATE_FOUND: no old user directories were changed. Guard or Broker must be diagnosed/removed using owner-approved administration before a clean reinstall.'
  }
  $old=$script:AgentRoot
  $backup=$old+'.QA-PREVIOUS-'+[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
  if(Test-Path -LiteralPath $backup){throw 'PREVIOUS_USER_BACKUP_COLLISION'}
  Move-Item -LiteralPath $old -Destination $backup -ErrorAction Stop
  Write-Host ('PREVIOUS_USER_ROOT_SAFELY_ARCHIVED='+$backup)
  $cfg=Join-Path $env:LOCALAPPDATA 'MellowCodex\installation.json'
  if(Test-Path -LiteralPath $cfg){
   $backupCfg=$cfg+'.QA-PREVIOUS-'+[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
   Move-Item -LiteralPath $cfg -Destination $backupCfg -ErrorAction Stop
   Write-Host ('PREVIOUS_CONFIG_SAFELY_ARCHIVED='+$backupCfg)
  }
 }
 if(!(Test-Path -LiteralPath $script:StageSource -PathType Container)){
  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $archive=[IO.Compression.ZipFile]::OpenRead($script:Zip)
  try{
   $names=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
   $total=[long]0
   foreach($e in $archive.Entries){
    $name=$e.FullName.Replace('\','/')
    if(!$name -or $name.StartsWith('/') -or $name.Contains(':') -or
       $name -match '(^|/)\.\.?(/|$)' -or !$names.Add($name)){throw ('ZIP_MEMBER_UNSAFE '+$name)}
    if($e.Length -gt 250000000){throw 'ZIP_ENTRY_SIZE_LIMIT'}
    $total+=$e.Length
    if($total -gt 1100000000){throw 'ZIP_TOTAL_SIZE_LIMIT'}
   }
  }finally{$archive.Dispose()}
  [IO.Directory]::CreateDirectory((Split-Path $script:StageSource -Parent))|Out-Null
  [IO.Compression.ZipFile]::ExtractToDirectory($script:Zip,$script:StageSource)
  Write-Host 'INSTALL1_R41_BUNDLE_EXTRACTED=TRUE'
 }
 Assert-StagedSource
 $installer=Join-Path $script:StageSource 'install.ps1'
 Write-Host 'INSTALL1_ONLY_DEPENDENCIES_NO_ADMIN_NO_SERVICES'
 $result=@(& $installer -InstallRoot $script:AgentRoot -SkipStartup)
 $result|ForEach-Object {Write-Host $_}
 if($result -notcontains 'DEPENDENCIES_INSTALLED_STARTUP_NOT_CONFIGURED' -or
    $result -notcontains 'MELLOWCODEX_INSTALL_SCRIPT_COMPLETED=TRUE'){throw 'INSTALL1_SUCCESS_MARKERS_NOT_FOUND'}
 & $verifier -InstallRoot $script:AgentRoot -SourceRoot $script:StageSource
 if(!$?){throw 'INSTALL1_STRICT_VERIFICATION_FAILED'}
}