$ErrorActionPreference = 'Stop'
$agentRoot = 'E:\AI'
$env:UV_CACHE_DIR = "$agentRoot\cache\uv"
$env:UV_PYTHON_INSTALL_DIR = "$agentRoot\tools\python"
$env:TEMP = "$agentRoot\cache"
$env:TMP = "$agentRoot\cache"
if (!(Test-Path "$agentRoot\tools\uv\uv.exe")) { & "$PSScriptRoot\download-tools.ps1" -AgentRoot $agentRoot }
& "$agentRoot\tools\uv\uv.exe" python install 3.12.16
if ($LASTEXITCODE -ne 0) { throw 'Python installation failed' }
if (!(Test-Path "$agentRoot\tools\hub-venv\Scripts\python.exe")) {
  & "$agentRoot\tools\uv\uv.exe" venv --python 3.12.16 "$agentRoot\tools\hub-venv"
  if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed' }
}
& "$agentRoot\tools\uv\uv.exe" pip sync --python "$agentRoot\tools\hub-venv\Scripts\python.exe" "$PSScriptRoot\requirements.lock.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& "$PSScriptRoot\start.ps1"
Write-Output 'To download the model if missing: E:\AI\tools\ollama\ollama.exe pull qwen3.5:4b (set OLLAMA_MODELS=E:\AI\models).'
