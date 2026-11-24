[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$InstallRoot,
 [Parameter(Mandatory=$true)][string]$SourceRoot
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$venv=Join-Path $InstallRoot 'tools\hub-venv\Scripts\python.exe'
$installed=Join-Path $InstallRoot 'repos\local-agent-hub'
foreach($rel in @('install.ps1','install-startup.ps1','installer\windows\Finish-OrdinaryUserSetup.ps1','requirements.lock.txt','tools-download-lock.json')){
 $actual=Join-Path $installed $rel
 $expected=Join-Path $SourceRoot $rel
 if(!(Test-Path -LiteralPath $actual -PathType Leaf) -or !(Test-Path -LiteralPath $expected -PathType Leaf)){throw ('QA_INSTALLED_SOURCE_MISSING_'+$rel)}
 if((Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $expected -Algorithm SHA256).Hash){
  throw ('QA_INSTALLED_SOURCE_HASH_MISMATCH_'+$rel)
 }
}
Write-Host 'QA_INSTALLED_SOURCE_MATCHES_R41=PASS'
if(!(Test-Path -LiteralPath $venv -PathType Leaf)){throw 'QA_PRIVATE_PYTHON_EXE_MISSING'}
$version=((& $venv --version 2>&1 | Out-String).Trim())
if($LASTEXITCODE -ne 0 -or $version -ne 'Python 3.12.16'){throw ('QA_PYTHON_VERSION_INCORRECT_'+$version)}
Write-Host ('QA_PYTHON_PINNED_VERSION='+$version)
$lock=Join-Path $SourceRoot 'requirements.lock.txt'
$scanner=Join-Path $SourceRoot 'installer\windows\Scan-PinnedPythonPackages.py'
if(!(Test-Path -LiteralPath $scanner -PathType Leaf)){throw 'QA_PACKAGE_SCANNER_MISSING'}
$raw=(& $venv -u $scanner $lock | Out-String)
if($LASTEXITCODE -ne 0){throw ('QA_PYTHON_PACKAGE_SCAN_EXIT='+$LASTEXITCODE)}
$report=$raw|ConvertFrom-Json
if([int]$report.schema -ne 1 -or [int]$report.checked -ne 127 -or [int]$report.ready -ne 127){throw ('QA_PACKAGE_COUNT_MISMATCH_READY_'+$report.ready)}
if(@($report.packages|Where-Object {-not $_.ready}).Count -ne 0){throw 'QA_PACKAGE_VERSION_MISMATCH'}
$qt=@($report.packages|Where-Object {$_.name -in @('pyside6-essentials','pyside6-addons','pyside6-webengine','shiboken6')})
if($qt.Count -ne 4 -or @($qt|Where-Object {-not $_.ready}).Count -ne 0){throw 'QA_QT_COMPONENT_MISMATCH'}
Write-Host 'QA_127_PINNED_PACKAGES=PASS'
Write-Host 'QA_QT_DESKTOP_AND_WEBENGINE=PASS'
$browser=Join-Path $InstallRoot 'tools\ms-playwright'
$chrome=Join-Path $browser 'chromium-1248'
if(!(Test-Path (Join-Path $chrome 'chrome-win64\chrome.exe') -PathType Leaf) -and
   !(Test-Path (Join-Path $chrome 'chrome-win\chrome.exe') -PathType Leaf)){
 throw 'QA_PINNED_CHROMIUM_1248_MISSING'
}
foreach($sub in @('chromium_headless_shell-1248','ffmpeg-1013','winldd-1007')){
 if(!(Test-Path -LiteralPath (Join-Path $browser $sub) -PathType Container)){throw ('QA_BROWSER_DEPENDENCY_MISSING_'+$sub)}
}
Write-Host 'QA_PLAYWRIGHT_BROWSER_AND_HELPERS=PASS'
$tools=Get-Content -LiteralPath (Join-Path $SourceRoot 'tools-download-lock.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($entry in @($tools.components)){
 $exe=Join-Path $InstallRoot ('tools\'+$entry.name+'\'+$entry.name+'.exe')
 if(!(Test-Path -LiteralPath $exe -PathType Leaf)){throw ('QA_TOOL_EXE_MISSING_'+$entry.name)}
 $detected=((& $exe --version 2>&1|Out-String).Trim())
 $pin=([string]$entry.version).TrimStart('v')
 if($LASTEXITCODE -ne 0 -or $detected -notmatch ('(?<![0-9])'+[regex]::Escape($pin)+'(?![0-9])')){throw ('QA_TOOL_VERSION_MISMATCH_'+$entry.name)}
 Write-Host ('QA_PINNED_TOOL_'+$entry.name+'=PASS')
}
$vcOk=$false
foreach($key in @('HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64','HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64')){
 $vc=Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
 if($vc -and [int]$vc.Installed -eq 1 -and [int]$vc.Major -ge 14 -and [int]$vc.Minor -ge 40){$vcOk=$true;break}
}
if(!$vcOk){throw 'QA_MICROSOFT_VC_RUNTIME_NOT_VERIFIED'}
Write-Host 'QA_VC_RUNTIME_14_40_PLUS=PASS'
Write-Host 'INSTALL1_ALL_PREREQUISITES_VERIFIED=TRUE'