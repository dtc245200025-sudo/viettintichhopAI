$ErrorActionPreference = 'Stop'
$taskAdminSecret = $null
$taskAppSecret = $null
$taskConfirmation = $null
try {
    $taskPython = Join-Path (Split-Path -Parent $PSScriptRoot) '.venv-1\Scripts\python.exe'
    if (-not (Test-Path $taskPython)) { $taskPython = Join-Path (Split-Path -Parent $PSScriptRoot) '.venv\Scripts\python.exe' }
    if (-not (Test-Path $taskPython)) { throw 'Create the project environment first: py -3 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt' }
    $taskAdminSecret = Read-Host 'Nhap mat khau MySQL root / MySQL root password' -AsSecureString
    $taskAppSecret = Read-Host 'Dat mat khau rieng cho ung dung (it nhat 12 ky tu) / New app password (12+ characters)' -AsSecureString
    $taskConfirmation = Read-Host 'Nhap lai mat khau ung dung / Confirm app password' -AsSecureString
    $taskAppPassword = [System.Net.NetworkCredential]::new('', $taskAppSecret).Password
    if ($taskAppPassword.Length -lt 12 -or $taskAppPassword -cne [System.Net.NetworkCredential]::new('', $taskConfirmation).Password) {
        throw 'Mat khau ung dung chua khop hoac ngan hon 12 ky tu / Password mismatch or too short.'
    }
    $env:VIETINCARE_SETUP_ROOT_PASSWORD = [System.Net.NetworkCredential]::new('', $taskAdminSecret).Password
    $env:VIETINCARE_SETUP_APP_PASSWORD = $taskAppPassword
    & $taskPython -m backend.setup_db_user
    if ($LASTEXITCODE -ne 0) { throw 'Thiet lap chua hoan tat / Setup did not complete. See error code above.' }
    Write-Host 'Da tao va kiem tra tai khoan. Chay scripts/start-local.ps1 / Account ready. Run scripts/start-local.ps1.'
} finally {
    Remove-Item Env:VIETINCARE_SETUP_ROOT_PASSWORD,Env:VIETINCARE_SETUP_APP_PASSWORD -ErrorAction SilentlyContinue
    $taskAppPassword = $null
    if ($taskAdminSecret) { $taskAdminSecret.Dispose() }
    if ($taskAppSecret) { $taskAppSecret.Dispose() }
    if ($taskConfirmation) { $taskConfirmation.Dispose() }
}
