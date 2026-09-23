$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskRootSecret = $null
$taskAppSecret = $null
$taskConfirmation = $null
try {
    $taskRootSecret = Read-Host 'Nhap mat khau MySQL root / MySQL root password' -AsSecureString
    $taskAppSecret = Read-Host 'Dat mat khau rieng cho ung dung (it nhat 12 ky tu) / New app password (12+ characters)' -AsSecureString
    $taskConfirmation = Read-Host 'Nhap lai mat khau ung dung / Confirm app password' -AsSecureString
    $taskAppPassword = [System.Net.NetworkCredential]::new('', $taskAppSecret).Password
    if ($taskAppPassword.Length -lt 12 -or $taskAppPassword -cne [System.Net.NetworkCredential]::new('', $taskConfirmation).Password) {
        throw 'Mat khau ung dung chua khop hoac ngan hon 12 ky tu / Password mismatch or too short.'
    }
    $env:VIETINCARE_SETUP_ROOT_PASSWORD = [System.Net.NetworkCredential]::new('', $taskRootSecret).Password
    $env:VIETINCARE_SETUP_APP_PASSWORD = $taskAppPassword
    & node (Join-Path $PSScriptRoot 'setup-db-user.js')
    if ($LASTEXITCODE -ne 0) { throw 'Thiet lap chua hoan tat / Setup did not complete. See error code above.' }
    Write-Host 'Da tao va kiem tra tai khoan. Chay scripts/start-local.ps1 / Account ready. Run scripts/start-local.ps1.'
} finally {
    Remove-Item Env:VIETINCARE_SETUP_ROOT_PASSWORD,Env:VIETINCARE_SETUP_APP_PASSWORD -ErrorAction SilentlyContinue
    $taskAppPassword = $null
    if ($taskRootSecret) { $taskRootSecret.Dispose() }
    if ($taskAppSecret) { $taskAppSecret.Dispose() }
    if ($taskConfirmation) { $taskConfirmation.Dispose() }
}
