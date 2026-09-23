param([switch]$EnableAI, [ValidateSet('gemini','openai')][string]$AIProvider = 'gemini')
$ErrorActionPreference = 'Stop'
$taskNames = @('HOST','PORT','APP_ORIGIN','DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD','COOKIE_SECURE','NODE_ENV','OPENAI_API_KEY','GEMINI_API_KEY','AI_PROVIDER')
$taskPrevious = @{}
foreach ($taskName in $taskNames) { $taskPrevious[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process') }
$taskSecret = $null
$taskAISecret = $null
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $taskSecret = Read-Host 'Mat khau MySQL vietincare_app / App database password' -AsSecureString
    $env:HOST = '127.0.0.1'
    $env:PORT = '3000'
    $env:APP_ORIGIN = 'http://localhost:3000'
    $env:DB_HOST = '127.0.0.1'
    $env:DB_PORT = '3306'
    $env:DB_NAME = 'qlkhviettin'
    $env:DB_USER = 'vietincare_app'
    $env:DB_PASSWORD = [System.Net.NetworkCredential]::new('', $taskSecret).Password
    $env:COOKIE_SECURE = 'false'
    $env:NODE_ENV = 'development'
    $env:AI_PROVIDER = $AIProvider
    $env:OPENAI_API_KEY = ''
    $env:GEMINI_API_KEY = ''
    if ($EnableAI) {
        $taskAISecret = Read-Host "$AIProvider API key (an / hidden)" -AsSecureString
        if ($taskAISecret.Length -eq 0) { throw 'API key is required with -EnableAI.' }
        $taskKeyName = if ($AIProvider -eq 'gemini') { 'GEMINI_API_KEY' } else { 'OPENAI_API_KEY' }
        [Environment]::SetEnvironmentVariable($taskKeyName, [System.Net.NetworkCredential]::new('', $taskAISecret).Password, 'Process')
    }
    & node server/index.js
    if ($LASTEXITCODE -ne 0) { throw 'Khoi dong that bai / Startup failed. See error code above.' }
} finally {
    foreach ($taskName in $taskNames) { [Environment]::SetEnvironmentVariable($taskName, $taskPrevious[$taskName], 'Process') }
    if ($taskSecret) { $taskSecret.Dispose() }
    if ($taskAISecret) { $taskAISecret.Dispose() }
    Pop-Location
}
