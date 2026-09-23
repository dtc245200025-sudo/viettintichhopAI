param([ValidateSet('migrate','create-agent','create-admin')][string]$Action = 'migrate')
$ErrorActionPreference = 'Stop'
$taskNames = @('DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD','VC_AGENT_EMAIL','VC_AGENT_NAME','VC_AGENT_PASSWORD','VC_ADMIN_EMAIL','VC_ADMIN_NAME','VC_ADMIN_PASSWORD')
$taskPrevious = @{}
foreach ($taskName in $taskNames) { $taskPrevious[$taskName] = [Environment]::GetEnvironmentVariable($taskName,'Process') }
$taskSecret = $null
$taskAgentSecret = $null
$taskConfirm = $null
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $taskSecret = Read-Host 'Mat khau MySQL root / MySQL root password' -AsSecureString
    $env:DB_HOST='127.0.0.1'
    $env:DB_PORT='3306'
    $env:DB_NAME='qlkhviettin'
    $env:DB_USER='root'
    $env:DB_PASSWORD=[System.Net.NetworkCredential]::new('', $taskSecret).Password
    if ($Action -eq 'migrate') {
        & node server/migrate.js --check
        if ($LASTEXITCODE -ne 0) { throw 'Kiem tra that bai / Preflight failed. No migration applied.' }
        & node server/migrate.js
        if ($LASTEXITCODE -ne 0) { throw 'Migration failed. Do not rerun without inspecting the error.' }
    } else {
        $env:VC_AGENT_NAME=Read-Host 'Ho ten tai khoan / Account name'
        $env:VC_AGENT_EMAIL=Read-Host 'Email dang nhap / Login email'
        $taskAgentSecret=Read-Host 'Mat khau website (12-128 ky tu) / Agent website password' -AsSecureString
        $taskConfirm=Read-Host 'Nhap lai mat khau / Confirm password' -AsSecureString
        $env:VC_AGENT_PASSWORD=[System.Net.NetworkCredential]::new('', $taskAgentSecret).Password
        if ($env:VC_AGENT_PASSWORD -cne [System.Net.NetworkCredential]::new('', $taskConfirm).Password) { throw 'Mat khau khong khop / Password mismatch' }
        if ($Action -eq 'create-admin') {
            $env:VC_ADMIN_NAME=$env:VC_AGENT_NAME
            $env:VC_ADMIN_EMAIL=$env:VC_AGENT_EMAIL
            $env:VC_ADMIN_PASSWORD=$env:VC_AGENT_PASSWORD
            & node server/provision-admin.js
        } else { & node server/provision-agent.js }
        if ($LASTEXITCODE -ne 0) { throw 'Tao nhan vien that bai / Agent creation failed. See code above.' }
    }
} finally {
    foreach ($taskName in $taskNames) { [Environment]::SetEnvironmentVariable($taskName,$taskPrevious[$taskName],'Process') }
    if ($taskSecret) { $taskSecret.Dispose() }
    if ($taskAgentSecret) { $taskAgentSecret.Dispose() }
    if ($taskConfirm) { $taskConfirm.Dispose() }
    Pop-Location
}