# Explicit owner request; shared UI/MCP preference and owned scheduled task.
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
 & 'E:\AI\tools\hub-venv\Scripts\python.exe' -c "import json;from hub.power import settings,set_startup;print(json.dumps(set_startup(True,settings()['revision'])))"
 if($LASTEXITCODE -ne 0){throw 'Startup registration failed; inspect ownership or Windows authorization'}
} finally {Pop-Location}
