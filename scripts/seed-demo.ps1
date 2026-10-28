param([string]$Database = 'qlkhviettin')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv-1\Scripts\python.exe'
if (-not (Test-Path $taskPython)) { $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe' }
$taskNames = @('DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD','VC_DEMO_PASSWORD')
$taskPrevious = @{}
foreach ($taskName in $taskNames) { $taskPrevious[$taskName] = [Environment]::GetEnvironmentVariable($taskName,'Process') }
$taskDbSecret = $null; $taskDemoSecret = $null
Push-Location $taskRoot
try {
    $taskDbSecret = Read-Host 'Mat khau MySQL vietincare_app / Application MySQL password' -AsSecureString
    $taskDemoSecret = Read-Host 'Mat khau chi cho tai khoan demo (12-128 ky tu) / Demo-only password' -AsSecureString
    $env:DB_HOST='127.0.0.1'; $env:DB_PORT='3306'; $env:DB_NAME=$Database; $env:DB_USER='vietincare_app'
    $env:DB_PASSWORD=[System.Net.NetworkCredential]::new('', $taskDbSecret).Password
    $env:VC_DEMO_PASSWORD=[System.Net.NetworkCredential]::new('', $taskDemoSecret).Password
    & $taskPython -m backend.demo_data --confirm-demo-data
    if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed; existing rows were not deleted. Ensure migrations are applied.' }
} finally {
    foreach ($taskName in $taskNames) { [Environment]::SetEnvironmentVariable($taskName,$taskPrevious[$taskName],'Process') }
    if ($taskDbSecret) { $taskDbSecret.Dispose() }; if ($taskDemoSecret) { $taskDemoSecret.Dispose() }
    Pop-Location
}
