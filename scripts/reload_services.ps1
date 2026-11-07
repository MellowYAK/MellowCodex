$ErrorActionPreference='Stop'
& 'E:\AI\tools\hub-venv\Scripts\python.exe' 'E:\AI\repos\local-agent-hub\scripts\reload_services.py'
if ($LASTEXITCODE -ne 0) { exit 1 }
& 'E:\AI\repos\local-agent-hub\start.ps1' -SkipDesktop
