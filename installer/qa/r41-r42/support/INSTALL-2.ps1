. (Join-Path $PSScriptRoot 'QA-R41-Common.ps1')
Invoke-QAPhase 2 {
 Assert-PreviousPhase 1
 Assert-StagedSource
 $python=Join-Path $script:AgentRoot 'tools\hub-venv\Scripts\python.exe'
 if(!(Test-Path -LiteralPath $python -PathType Leaf)){throw 'INSTALL2_STAGE1_PYTHON_MISSING'}
 $guardHome=Join-Path $env:ProgramData 'MellowGuard'
 $brokerHome=Join-Path $env:ProgramData 'MellowOwnerBroker'
 $brokerService=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction SilentlyContinue
 if($brokerService -or (Test-Path -LiteralPath $brokerHome) -or (Test-Path -LiteralPath (Join-Path $guardHome 'current.json'))){
  throw 'INSTALL2_INSTALLED_PROTECTED_COMPONENT_ALREADY_PRESENT'
 }
 if(Test-Path -LiteralPath $guardHome){
  Write-Host 'INSTALL2_PARTIAL_GUARD_PRESENT: elevated R42 will verify exact orphan and preserve it as backup'
 }
 $broker=Join-Path $script:StageSource 'payload\MellowOwnerBroker-unsigned-native-source.zip'
 $digest=(Get-FileHash -LiteralPath $broker -Algorithm SHA256).Hash
 Write-Host 'INSTALL2_REQUIRES_WINDOWS_UAC_FOR_GUARD_AND_BROKER'
 Write-Host ('UNSIGNED_BROKER_LOCAL_SYSTEM_PACKAGE_SHA256='+$digest)
 Write-Host 'This component is unsigned and runs as LocalSystem. Windows will request Administrator credentials separately.'
 $decision=Read-Host 'Type YES to authorize this exact unsigned protected package'
 if($decision -cne 'YES'){throw 'INSTALL2_UNSIGNED_BROKER_NOT_APPROVED'}
 $hotZip=Join-Path $PSScriptRoot 'MellowCodex-R42-Phase2-Hotfix.zip'
 $hotHash='76AE0374957B06E95B1EC1DFA04763A97D343A34C3F6FAFF2D754A4C75DAF87A'
 if(!(Test-Path -LiteralPath $hotZip -PathType Leaf)){throw 'INSTALL2_R42_HOTFIX_NOT_PRESENT'}
 if((Get-FileHash -LiteralPath $hotZip -Algorithm SHA256).Hash -ne $hotHash){throw 'INSTALL2_R42_HASH_MISMATCH'}
 if((Get-Content -LiteralPath ($hotZip+'.sha256') -Raw).Trim().ToUpperInvariant() -ne $hotHash){throw 'INSTALL2_R42_SIDECAR_MISMATCH'}
 $hotSource=Join-Path $env:LOCALAPPDATA 'MellowCodexQA\R42\source'
 if(!(Test-Path -LiteralPath $hotSource -PathType Container)){
  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $archive=[IO.Compression.ZipFile]::OpenRead($hotZip)
  try{
   $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
   foreach($x in $archive.Entries){
    $name=$x.FullName.Replace('\','/')
    if(!$name -or $name.StartsWith('/') -or $name.Contains(':') -or $name -match '(^|/)\.\.?(/|$)' -or !$seen.Add($name)){throw ('INSTALL2_R42_ZIP_PATH_UNSAFE '+$name)}
   }
  }finally{$archive.Dispose()}
  [IO.Directory]::CreateDirectory((Split-Path $hotSource -Parent))|Out-Null
  [IO.Compression.ZipFile]::ExtractToDirectory($hotZip,$hotSource)
  Write-Host 'INSTALL2_R42_HOTFIX_SOURCE_EXTRACTED=TRUE'
 }
 $manifest=Get-Content -LiteralPath (Join-Path $hotSource 'SOURCE-MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
 if([int]$manifest.schema -ne 1 -or @($manifest.files).Count -ne 626){throw 'INSTALL2_R42_MANIFEST_MISMATCH'}
 foreach($entry in $manifest.files){
  $rel=[string]$entry.path
  if(!$rel -or [IO.Path]::IsPathRooted($rel) -or $rel -match '(^|[/\\])\.\.([/\\]|$)'){throw 'INSTALL2_R42_MANIFEST_PATH_UNSAFE'}
  $f=Join-Path $hotSource $rel
  if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw ('INSTALL2_R42_SOURCE_MISSING '+$rel)}
  if((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash -ine [string]$entry.sha256){throw ('INSTALL2_R42_SOURCE_SHA_INVALID '+$rel)}
 }
 if((Get-FileHash (Join-Path $hotSource 'installer\windows\Install-ProtectedComponents.ps1') -Algorithm SHA256).Hash -ne '7808B9EDC1CBE1674546F2F82917B8C77183E62BE7923ECE34E53ECFE1E890E8'){throw 'INSTALL2_R42_APPROVED_HELPER_SHA_MISMATCH'}
 Write-Host 'INSTALL2_R42_ALL_SOURCE_HASHES_VERIFIED=TRUE'
 $installer=Join-Path $hotSource 'install.ps1'
 # This is an early, protected-only entry point. It NEVER redownloads Python, Chromium, or packages.
 # Run the already hash-verified installed source in its OWN ordinary-user PowerShell process.
 # Native UAC's secure origin attestation expects exactly -File install.ps1, not -File INSTALL-2.ps1.
 $powerShell=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 $runId=[Guid]::NewGuid().ToString('N')
 $stdout=Join-Path $script:QaLogs ('INSTALL-2-protected-'+$runId+'.stdout.log')
 $stderr=Join-Path $script:QaLogs ('INSTALL-2-protected-'+$runId+'.stderr.log')
 $arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$installer+'" -ProtectedOnly -InstallRoot "'+$script:AgentRoot+'" -OwnerBrokerGuiConsent'
 Write-Host 'INSTALL2_ORIGIN_COMMAND_VERIFIED=PowerShell -File install.ps1 -ProtectedOnly'
 Write-Host ('INSTALL2_PROTECTED_CHILD_STDOUT='+$stdout)
 Write-Host ('INSTALL2_PROTECTED_CHILD_STDERR='+$stderr)
 $child=Start-Process -FilePath $powerShell -ArgumentList $arguments -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr -ErrorAction Stop
 $output=@(Get-Content -LiteralPath $stdout -ErrorAction Stop)
 $output|ForEach-Object {Write-Host $_}
 if($child.ExitCode -ne 0){
  Write-Host ('INSTALL2_CHILD_EXIT_CODE='+$child.ExitCode)
  Write-Host ('INSTALL2_ERROR_DETAILS_IN='+$stderr)
  throw ('INSTALL2_PRIVILEGED_CHILD_FAILED_EXIT_'+$child.ExitCode)
 }
 if($output -notcontains 'MELLOWCODEX_PHASE2_PROTECTED_COMPLETED=TRUE'){throw 'INSTALL2_PROTECTED_COMPLETION_MARKER_MISSING'}
 $service=Get-CimInstance Win32_Service -Filter "Name='MellowOwnerBroker'" -ErrorAction Stop
 if(!$service -or [string]$service.State -ne 'Running' -or [string]$service.StartName -ne 'LocalSystem'){
  throw 'INSTALL2_BROKER_NOT_RUNNING_AS_LOCAL_SYSTEM'
 }
 $cfg=Join-Path $brokerHome 'config.json'
 if(!(Test-Path -LiteralPath $cfg -PathType Leaf)){throw 'INSTALL2_BROKER_CONFIG_NOT_FOUND'}
 $binding=Get-Content -LiteralPath $cfg -Encoding UTF8 -Raw|ConvertFrom-Json
 if([string]$binding.owner_sid -cne $script:OwnerSid){throw 'INSTALL2_BROKER_OWNER_SID_MISMATCH'}
 $release=Join-Path $guardHome 'current.json'
 if(!(Test-Path -LiteralPath $release -PathType Leaf)){throw 'INSTALL2_GUARD_RELEASE_MISSING'}
 Write-Host 'INSTALL2_PROTECTED_COMPONENTS_VERIFIED=TRUE'
}