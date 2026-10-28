$ErrorActionPreference = 'Stop'
$taskSecret = $null
$taskPrevious = [Environment]::GetEnvironmentVariable('VIETINCARE_LIST_APP_PASSWORD', 'Process')
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $taskPython = Join-Path (Get-Location) '.venv-1\Scripts\python.exe'
    if (-not (Test-Path $taskPython)) { $taskPython = Join-Path (Get-Location) '.venv\Scripts\python.exe' }
    if (-not (Test-Path $taskPython)) { throw 'Python environment not found.' }
    $taskSecret = Read-Host 'Mat khau vietincare_app / App database password' -AsSecureString
    $env:VIETINCARE_LIST_APP_PASSWORD = [System.Net.NetworkCredential]::new('', $taskSecret).Password
    & $taskPython -m backend.list_accounts
    if ($LASTEXITCODE -ne 0) { throw 'Khong doc duoc danh sach tai khoan / Account check failed.' }
} finally {
    [Environment]::SetEnvironmentVariable('VIETINCARE_LIST_APP_PASSWORD', $taskPrevious, 'Process')
    if ($taskSecret) { $taskSecret.Dispose() }
    Pop-Location
}
