[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$AgentRoot,[switch]$DryRun)
$ErrorActionPreference='Stop'
$AgentRoot=[IO.Path]::GetFullPath($AgentRoot).TrimEnd('\')
$repo=Join-Path $AgentRoot 'repos\local-agent-hub'
$handler=Join-Path $repo 'installer\windows\Invoke-MellowCodex.ps1'
if(!(Test-Path -LiteralPath $handler -PathType Leaf)){throw "Shortcut target missing: $handler"}
$desktop=[Environment]::GetFolderPath('DesktopDirectory')
if(-not $desktop){throw 'Interactive Windows desktop is unavailable'}
$ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$specs=@(
 @{Name='MellowCodex Start';Action='Start';Description='Start the owned MellowCodex services and Qt desktop'},
 @{Name='MellowCodex Stop';Action='Stop';Description='Stop MellowCodex owned services using protected ownership checks'}
)
if($DryRun){$specs|ForEach-Object{"DRY_RUN "+(Join-Path $desktop ($_.Name+'.lnk'))};return}
$shell=New-Object -ComObject WScript.Shell
foreach($spec in $specs){
 $linkFile=Join-Path $desktop ($spec.Name+'.lnk')
 $args='-NoProfile -ExecutionPolicy Bypass -NoExit -File "'+$handler+'" -AgentRoot "'+$AgentRoot+'" -Action '+$spec.Action
 if(Test-Path -LiteralPath $linkFile){
  $old=$shell.CreateShortcut($linkFile)
  if([string]$old.TargetPath -ine $ps -or [string]$old.Arguments -cne $args){
   throw "Existing unrelated desktop shortcut not overwritten: $linkFile"
  }
  continue
 }
 $link=$shell.CreateShortcut($linkFile)
 $link.TargetPath=$ps
 $link.Arguments=$args
 $link.WorkingDirectory=$repo
 $link.Description=$spec.Description
 $link.Save()
 $read=$shell.CreateShortcut($linkFile)
 if([string]$read.TargetPath -ine $ps -or [string]$read.Arguments -cne $args){
  throw "Shortcut readback mismatch: $linkFile"
 }
 Write-Host "Desktop shortcut installed: $linkFile" -ForegroundColor Green
}