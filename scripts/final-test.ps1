$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv-1\Scripts\python.exe'
if (-not (Test-Path $taskPython)) { $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path $taskPython)) { throw 'Create the project Python environment and install requirements-dev.txt first.' }
Push-Location $taskRoot
try {
    & $taskPython -m backend.final_acceptance --isolated-server
    if ($LASTEXITCODE -ne 0) { throw 'Acceptance failed. Inspect docs/reports/final-acceptance-20261029/result.json and pytest.log.' }
} finally { Pop-Location }
