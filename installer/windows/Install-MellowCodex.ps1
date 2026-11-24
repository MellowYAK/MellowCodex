[CmdletBinding()]
param(
 [string]$AgentRoot=(Join-Path $env:LOCALAPPDATA 'MellowCodex'),
 [string]$SourceRoot=(Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
 [string]$GuardBundle='',
 [string]$OwnerBrokerBundle='',
 [string]$OwnerBrokerMsi='',
 [string]$OwnerBrokerSha256='',
 [switch]$SkipBrowser,
 [switch]$SkipGuard,
 [switch]$NoLaunch,
 [switch]$DryRun
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
Set-StrictMode -Version Latest
$AgentRoot=[IO.Path]::GetFullPath($AgentRoot).TrimEnd('\')
$SourceRoot=[IO.Path]::GetFullPath($SourceRoot).TrimEnd('\')
$repo=Join-Path $AgentRoot 'repos\local-agent-hub'
$log=Join-Path $AgentRoot 'state\installer'
function Phase([int]$Number,[string]$Message){
 Write-Host ("[{0}/8] {1}" -f $Number,$Message) -ForegroundColor Cyan
}
function Check-File([string]$Path){
 if(-not (Test-Path -LiteralPath $Path -PathType Leaf)){throw "Required file missing: $Path"}
}
function Check-Exit([string]$What){
 if($LASTEXITCODE -ne 0){throw "$What failed (exit code $LASTEXITCODE)"}
}
function Download-Locked([object]$Entry){
 if([string]$Entry.sha256 -notmatch '^[0-9a-fA-F]{64}$'){throw "No pinned SHA256 for $($Entry.name)"}
 $u=[uri]$Entry.url
 if($u.Scheme -cne 'https' -or $u.Host -cne 'github.com'){throw "Untrusted download host: $($Entry.name)"}
 $folder=Join-Path $AgentRoot 'downloads'
 [IO.Directory]::CreateDirectory($folder)|Out-Null
 $zip=Join-Path $folder ([string]$Entry.asset)
 if(Test-Path $zip){
  if((Get-FileHash $zip -Algorithm SHA256).Hash -ine [string]$Entry.sha256){
   throw "Existing download SHA mismatch: $zip"
  }
 }else{
  $temp="$zip.partial"
  try{
   [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
   Invoke-WebRequest -Uri $u.AbsoluteUri -OutFile $temp -UseBasicParsing
   if((Get-FileHash $temp -Algorithm SHA256).Hash -ine [string]$Entry.sha256){
    throw "Downloaded $($Entry.name) did not match pinned SHA256"
   }
   Move-Item -LiteralPath $temp -Destination $zip
  }finally{if(Test-Path $temp){Remove-Item -LiteralPath $temp -Force}}
 }
 $dest=Join-Path $AgentRoot ("tools\"+[string]$Entry.name)
 if(!(Test-Path $dest)){
  [IO.Directory]::CreateDirectory($dest)|Out-Null
  Expand-Archive -LiteralPath $zip -DestinationPath $dest
 }
 Write-Host ("  Verified: {0} {1}" -f $Entry.name,$Entry.version)
}
function Copy-Source(){
 if(Test-Path (Join-Path $repo 'hub\app.py')){
  throw "Existing source tree detected at $repo. Refusing overwrite or in-place upgrade."
 }
 [IO.Directory]::CreateDirectory($repo)|Out-Null
 foreach($folder in @('hub','scripts','chrome-session-bridge','docs','tests','installer','deploy')){
  $from=Join-Path $SourceRoot $folder
  if(!(Test-Path -LiteralPath $from -PathType Container)){continue}
  $dest=Join-Path $repo $folder
  [IO.Directory]::CreateDirectory($dest)|Out-Null
  & robocopy.exe $from $dest /E /NFL /NDL /NJH /NJS /NC /NS /XD __pycache__ .pytest_cache .git .venv venv state cache backups artifacts node_modules /XF *.pyc *.log *.db *.sqlite3 *.pem *.key *.pfx .env .env.*
  if($LASTEXITCODE -ge 8){throw "Source copy failed: $folder"}
 }
 foreach($f in @(Get-ChildItem -LiteralPath $SourceRoot -File)){
  if($f.Name -match '^(?:\.env(?:\..*)?|.*\.(?:key|pfx|pem|sqlite3|db|log|zip|exe|dll))$'){continue}
  if($f.Extension.ToLowerInvariant() -notin @('.py','.ps1','.psm1','.psd1','.cmd','.bat','.json','.toml','.txt','.md','.lock','.yaml','.yml','.ini')){continue}
  Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $repo $f.Name)
 }
 Check-File (Join-Path $repo 'hub\app.py')
 Check-File (Join-Path $repo 'requirements.lock.txt')
 Check-File (Join-Path $repo 'reconcile-services.ps1')
}
function Relocate-InstalledSource(){
 $fromA='E:\\AI'
 $fromB='E:\AI'
 $rootEscaped=$AgentRoot.Replace('\','\\')
 $n=0
 foreach($f in @(Get-ChildItem -LiteralPath $repo -File -Recurse)){
  if($f.FullName -match '\\(?:tests|docs|installer|deploy)\\'){continue}
  $ext=$f.Extension.ToLowerInvariant()
  if($ext -notin @('.ps1','.py','.json','.toml','.mjs','.js','.cjs','.cmd','.bat','.ini','.txt')){continue}
  $raw=[IO.File]::ReadAllText($f.FullName)
  $new=$raw.Replace($fromA,$rootEscaped)
  if($ext -in @('.py','.json','.toml','.mjs','.js','.cjs')){
    $new=$new.Replace($fromB,$rootEscaped)
  }else{
    $new=$new.Replace($fromB,$AgentRoot)
  }
  $new=$new.Replace('E:/AI',$AgentRoot.Replace('\','/'))
  if($new -cne $raw){
    [IO.File]::WriteAllText($f.FullName,$new,[Text.UTF8Encoding]::new($false))
    $n++
  }
  if($new.Contains($fromB) -or $new.Contains($fromA) -or $new.Contains('E:/AI')){
    throw "Unresolved historical installation path: $($f.FullName)"
  }
 }
 Write-Host "  Relocated $n source/config files in the copied installation only."
}
try{
 Phase 1 'Check Windows platform and destination'
 if([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT){throw 'Windows required'}
 if(-not [Environment]::Is64BitOperatingSystem){throw '64-bit Windows required'}
 Check-File (Join-Path $SourceRoot 'tools-download-lock.json')
 Check-File (Join-Path $SourceRoot 'requirements.lock.txt')
 if($AgentRoot -ieq $SourceRoot -or $SourceRoot.StartsWith("$AgentRoot\",[StringComparison]::OrdinalIgnoreCase)){
  throw 'Installation destination overlaps active source checkout'
 }
 if($AgentRoot -match '^[A-Za-z]:\\?$' -or $AgentRoot.Contains('"')){
  throw 'Choose a normal writable Windows folder, not a drive root'
 }
 if(Test-Path (Join-Path $repo 'hub\app.py')){throw "Existing installation detected: $repo"}
 $lock=Get-Content (Join-Path $SourceRoot 'tools-download-lock.json') -Raw|ConvertFrom-Json
 if(@($lock.components).Count -lt 3){throw 'Incomplete binary dependency lock'}

 $payloadDir=Join-Path $SourceRoot 'payload'
 if(Test-Path -LiteralPath $payloadDir -PathType Container){
  if(!$GuardBundle){
   $choices=@(Get-ChildItem -LiteralPath $payloadDir -Filter 'MellowGuard-source-*.zip' -File)
   if($choices.Count -eq 1){$GuardBundle=$choices[0].FullName}
  }
  if(!$OwnerBrokerBundle -and !$OwnerBrokerMsi){
   $bundle=Join-Path $payloadDir 'MellowOwnerBroker-unsigned-native-source.zip'
   if(Test-Path -LiteralPath $bundle){$OwnerBrokerBundle=$bundle}
  }
 }
 if(!$DryRun){
  if(!$GuardBundle -and !$SkipGuard){throw 'Protected Guard bundle absent. The installation kit must contain payload/MellowGuard-source-*.zip'}
  if(!$OwnerBrokerBundle -and !$OwnerBrokerMsi){throw 'OwnerBroker package absent. Provide the private owner-approved broker bundle or an authorized signed MSI'}
 }
 if($DryRun){
  Write-Host "DRY_RUN source=$SourceRoot destination=$AgentRoot"
  Write-Host ("Locked prerequisites: "+(@($lock.components|ForEach-Object {"$($_.name)=$($_.version)"}) -join ', '))
  Write-Host 'Pinned Python 3.12.16, Qt via requirements.lock.txt, optional Chromium.'
  if(!$GuardBundle -and !$SkipGuard){Write-Warning 'A separate authorized Guard source bundle is required.'}
  return
 }
 [IO.Directory]::CreateDirectory($log)|Out-Null
 $logFile=Join-Path $log ('install-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
 Start-Transcript -Path $logFile -ErrorAction Stop|Out-Null
 Phase 2 'Copy source files only (no models, state, secrets, caches)'
 Copy-Source
 Relocate-InstalledSource
 foreach($folder in @('models','cache','downloads','candidates','state')){
  [IO.Directory]::CreateDirectory((Join-Path $AgentRoot $folder))|Out-Null
 }
 Phase 3 'Download and verify pinned UV, Ollama and OpenCode'
 foreach($entry in @($lock.components)){Download-Locked $entry}
 Phase 4 'Provision Python 3.12.16 and locked Python/Qt packages'
 $uv=Join-Path $AgentRoot 'tools\uv\uv.exe'
 Check-File $uv
 $env:UV_PYTHON_INSTALL_DIR=Join-Path $AgentRoot 'tools\python'
 $env:UV_CACHE_DIR=Join-Path $AgentRoot 'cache\uv'
 $env:UV_LINK_MODE='copy'
 & $uv python install 3.12.16
 Check-Exit 'Pinned Python download'
 $venv=Join-Path $AgentRoot 'tools\hub-venv'
 & $uv venv --python 3.12.16 $venv
 Check-Exit 'Python virtual environment'
 $python=Join-Path $venv 'Scripts\python.exe'
 Check-File $python
 & $uv pip sync --python $python (Join-Path $repo 'requirements.lock.txt')
 Check-Exit 'Pinned Python dependencies'
 & $python -c 'import PySide6.QtWebEngineWidgets,fastapi,uvicorn,playwright; print("Python, Qt and browser imports OK")'
 Check-Exit 'Core imports'
 Phase 5 'Install the native Chromium engine for browser tools'
 if(!$SkipBrowser){
  $env:PLAYWRIGHT_BROWSERS_PATH=Join-Path $AgentRoot 'tools\playwright-browsers'
  & $python -m playwright install chromium
  Check-Exit 'Playwright Chromium'
  [Environment]::SetEnvironmentVariable('PLAYWRIGHT_BROWSERS_PATH',$env:PLAYWRIGHT_BROWSERS_PATH,'User')
 }else{Write-Warning 'Browser support explicitly skipped.'}
 Phase 6 'Install separately controlled Guard and OwnerBroker'
 $protected=Join-Path $PSScriptRoot 'Install-ProtectedComponents.ps1'
 Check-File $protected
 & $protected -AgentRoot $AgentRoot -GuardBundle $GuardBundle -OwnerBrokerBundle $OwnerBrokerBundle -OwnerBrokerMsi $OwnerBrokerMsi -OwnerBrokerSha256 $OwnerBrokerSha256 -SkipGuard:$SkipGuard
 Phase 7 'Register owned startup/Watchdog and shortcuts'
 Push-Location $repo
 try{
  & $python -c 'from hub.owner_broker import owner_status; import sys; sys.exit(0 if owner_status().get("server_identity_verified") is True else 3)'
  Check-Exit 'OwnerBroker not verified, complete its authorized installer first'
  & (Join-Path $repo 'install-startup.ps1')
  if($LASTEXITCODE -ne 0){throw 'MellowCodex startup registration failed'}
 }finally{Pop-Location}
 & (Join-Path $PSScriptRoot 'New-DesktopShortcuts.ps1') -AgentRoot $AgentRoot
 Phase 8 'Write the installation receipt'
 $receipt=@{
  version='0.27.0';installed_at=[DateTime]::UtcNow.ToString('o')
  root=$AgentRoot;python='3.12.16';with_guard=(-not $SkipGuard)
  browser_installed=(-not $SkipBrowser);owner_acceptance='NOT_TESTED'
 }
 [IO.File]::WriteAllText((Join-Path $log 'setup-complete.json'),($receipt|ConvertTo-Json -Depth 4),[Text.UTF8Encoding]::new($false))
 Write-Host "Files and startup registration complete. Log: $logFile" -ForegroundColor Green
 if(!$NoLaunch){& (Join-Path $PSScriptRoot 'Invoke-MellowCodex.ps1') -AgentRoot $AgentRoot -Action Start}
}catch{
 Write-Host "SETUP BLOCKED: $($_.Exception.Message)" -ForegroundColor Red
 Write-Host "No existing installation overwritten. Log directory: $log"
 throw
}finally{try{Stop-Transcript|Out-Null}catch{}}