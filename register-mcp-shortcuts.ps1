$ErrorActionPreference='Stop'
$desktop=[Environment]::GetFolderPath('Desktop')
$shell=New-Object -ComObject WScript.Shell
foreach($action in @('Start','Stop','Restart','Status')) {
  $link=$shell.CreateShortcut((Join-Path $desktop "Mellow MCP - $action.lnk"))
  $link.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
  $link.Arguments='-NoProfile -NoExit -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'reconcile-services.ps1')+'" -Action '+$action
  $link.WorkingDirectory=$PSScriptRoot
  $link.Description="Mellow MCP $action"
  $link.Save()
}

# Native offline rescue: remains usable while Hub and MCP are stopped.
$link=$shell.CreateShortcut((Join-Path $desktop 'Mellow Health and Services.lnk'))
$link.TargetPath='E:\AI\tools\hub-venv\Scripts\pythonw.exe'
$link.Arguments='-m hub.service_health_ui'
$link.WorkingDirectory=$PSScriptRoot
$link.Description='Local service rescue, independent of Hub/MCP'
$link.Save()
