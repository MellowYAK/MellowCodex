[CmdletBinding()]
param([ValidateSet('Status','Enable','Disable')][string]$Action='Status')
$ErrorActionPreference='Stop'
$name='Local Agent Hub'
$root=$PSScriptRoot
$python='E:\AI\tools\hub-venv\Scripts\pythonw.exe'
$startupArguments='-m hub.power --autostart'
$current=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
$owned=$true
if($current){
 $a=@($current.Actions)
 $new=($a.Count -eq 1 -and $a[0].Execute -eq $python -and $a[0].Arguments -eq $startupArguments -and $a[0].WorkingDirectory -eq $root)
 $oldArgs=@(('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File '+$root+'\start.ps1'),('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$root+'\start.ps1"'))
 $old=($a.Count -eq 1 -and $a[0].Execute -in @('powershell.exe',"$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe") -and $a[0].Arguments -in $oldArgs -and $a[0].WorkingDirectory -eq $root)
 $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 try{$owner=([Security.Principal.NTAccount]$current.Principal.UserId).Translate([Security.Principal.SecurityIdentifier]).Value}catch{$owner=[string]$current.Principal.UserId}
 $owned=($new -or $old) -and $owner -eq $sid -and [string]$current.Principal.RunLevel -eq 'Limited'
}
if($Action -ne 'Status'){
 if(!$owned){throw 'Existing startup task has different ownership or command; no change made'}
 $user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
 $taskAction=New-ScheduledTaskAction -Execute $python -Argument $startupArguments -WorkingDirectory $root
 $trigger=New-ScheduledTaskTrigger -AtLogOn -User $user
 $principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
 $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
 Register-ScheduledTask -TaskName $name -Action $taskAction -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
 if($Action -eq 'Disable'){Disable-ScheduledTask -TaskName $name|Out-Null}else{Enable-ScheduledTask -TaskName $name|Out-Null}
 $current=Get-ScheduledTask -TaskName $name
}
@{verified=$true;exists=($null -ne $current);owned=$owned;enabled=($null -ne $current -and [string]$current.State -ne 'Disabled');task_name=$name;scope='Current user logon; Limited; no elevation'}|ConvertTo-Json -Compress
