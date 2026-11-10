$ErrorActionPreference = 'Stop'
# Changes service startup only. Does not alter owner permissions or UAC.
Set-Service -Name MellowOwnerBroker -StartupType Automatic
Start-Service -Name MellowOwnerBroker
Get-Service -Name MellowOwnerBroker | Select-Object Name,Status,StartType | ConvertTo-Json | Set-Content E:\AI\state\broker-startup-result.json
