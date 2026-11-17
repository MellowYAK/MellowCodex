param([switch]$NoStart)
$ErrorActionPreference='Stop'
$name='MellowCodex Service Recovery'
$script=Join-Path $PSScriptRoot 'reconcile-services.ps1'
$exe="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments='-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$script+'"'
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if($existing){
 $a=@($existing.Actions)
 try{$owner=([Security.Principal.NTAccount]$existing.Principal.UserId).Translate([Security.Principal.SecurityIdentifier]).Value}catch{$owner=[string]$existing.Principal.UserId}
 if($a.Count -ne 1 -or $a[0].Execute -ne $exe -or $a[0].Arguments -ne $arguments -or $a[0].WorkingDirectory -ne $PSScriptRoot -or $owner -ne $sid -or [string]$existing.Principal.RunLevel -ne 'Limited' -or [string]$existing.Principal.LogonType -ne 'Interactive'){
  throw 'Existing recovery task has different ownership or command; no change made.'
 }
}
$action=New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $PSScriptRoot
$triggers=@((New-ScheduledTaskTrigger -AtLogOn -User $user),(New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)))
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Force | Out-Null
Enable-ScheduledTask -TaskName $name | Out-Null
if(!$NoStart){Start-ScheduledTask -TaskName $name}
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State,@{N='RunLevel';E={$_.Principal.RunLevel}}
