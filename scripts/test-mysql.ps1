$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv-1\Scripts\python.exe'
if (-not (Test-Path $taskPython)) { $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path $taskPython)) { throw 'Create the project environment first: py -3 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt' }
$taskNames = @('DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD','APP_ORIGIN','COOKIE_SECURE','AI_PROVIDER','RUN_MYSQL_TESTS')
$taskPrevious = @{}
foreach ($taskName in $taskNames) { $taskPrevious[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process') }
$taskSecret = $null
Push-Location $taskRoot
try {
    $taskSecret = Read-Host 'Mat khau MySQL root cho database test tam / MySQL root password for isolated test database' -AsSecureString
    $env:DB_HOST = '127.0.0.1'
    $env:DB_PORT = '3306'
    $env:DB_USER = 'root'
    $env:DB_PASSWORD = [System.Net.NetworkCredential]::new('', $taskSecret).Password
    $env:APP_ORIGIN = 'http://localhost:3000'
    $env:COOKIE_SECURE = 'false'
    $env:AI_PROVIDER = 'gemini'
    $env:RUN_MYSQL_TESTS = '1'
    & $taskPython -m pytest tests/test_mysql_integration.py -q -rs
    if ($LASTEXITCODE -ne 0) { throw 'MySQL integration test failed. The test removes only its uniquely named isolated database.' }
} finally {
    foreach ($taskName in $taskNames) { [Environment]::SetEnvironmentVariable($taskName, $taskPrevious[$taskName], 'Process') }
    if ($taskSecret) { $taskSecret.Dispose() }
    Pop-Location
}
