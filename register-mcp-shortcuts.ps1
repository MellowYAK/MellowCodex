$ErrorActionPreference='Stop'
$desktop=[Environment]::GetFolderPath('Desktop')
$shell=New-Object -ComObject WScript.Shell
$ps="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
foreach($action in @('Start','Stop','Status')){
 $script=if($action -eq 'Start'){'start.ps1'}elseif($action -eq 'Stop'){'stop.ps1'}else{'reconcile-services.ps1'}
 $args='-NoProfile -NoExit -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot $script)+'"'
 if($action -eq 'Status'){$args+=' -Action Status -Service all'}
 $path=Join-Path $desktop "MellowCodex - $action.lnk"
 if(Test-Path -LiteralPath $path){
  $old=$shell.CreateShortcut($path)
  if($old.TargetPath -ne $ps -or $old.WorkingDirectory -ne $PSScriptRoot -or $old.Arguments -notlike ('*'+$PSScriptRoot+'*')){throw "Unexpected existing shortcut: $path"}
 }
 $link=$shell.CreateShortcut($path)
 $link.TargetPath=$ps
 $link.Arguments=$args
 $link.WorkingDirectory=$PSScriptRoot
 $link.Description="MellowCodex $action (ordinary Windows user)"
 $link.Save()
 $bytes=[IO.File]::ReadAllBytes($path)
 if($bytes.Length -lt 76 -or ([BitConverter]::ToUInt32($bytes,20) -band 0x2000)){throw "Shortcut requests elevation: $path"}
 Write-Output $path
}
