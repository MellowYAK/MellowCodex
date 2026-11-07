# Optional, explicit installation. Runs after user logon, not on a locked desktop.
$ErrorActionPreference = 'Stop'
$taskName = 'Local Agent Hub'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  throw 'The startup task already exists. Inspect it before replacing it.'
}
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File E:\AI\repos\local-agent-hub\start.ps1' -WorkingDirectory 'E:\AI\repos\local-agent-hub'
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State
