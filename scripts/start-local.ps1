param([switch]$EnableAI, [switch]$EnableOTP, [ValidateSet('gemini','openai')][string]$AIProvider = 'gemini')
$ErrorActionPreference = 'Stop'
$taskNames = @('HOST','PORT','APP_ORIGIN','DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD','COOKIE_SECURE','APP_ENV','OPENAI_API_KEY','GEMINI_API_KEY','AI_PROVIDER','TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_FROM_NUMBER')
$taskPrevious = @{}
foreach ($taskName in $taskNames) { $taskPrevious[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process') }
$taskSecret = $null
$taskAISecret = $null
$taskSmsSecret = $null
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $taskPython = Join-Path (Get-Location) '.venv-1\Scripts\python.exe'
    if (-not (Test-Path $taskPython)) { $taskPython = Join-Path (Get-Location) '.venv\Scripts\python.exe' }
    if (-not (Test-Path $taskPython)) { throw 'Create the project environment first: py -3 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt' }
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
    $env:APP_ENV = 'development'
    $env:AI_PROVIDER = $AIProvider
    $env:OPENAI_API_KEY = ''
    $env:GEMINI_API_KEY = ''
    if ($EnableAI) {
        $taskAISecret = Read-Host "$AIProvider API key (an / hidden)" -AsSecureString
        if ($taskAISecret.Length -eq 0) { throw 'API key is required with -EnableAI.' }
        $taskKeyName = if ($AIProvider -eq 'gemini') { 'GEMINI_API_KEY' } else { 'OPENAI_API_KEY' }
        [Environment]::SetEnvironmentVariable($taskKeyName, [System.Net.NetworkCredential]::new('', $taskAISecret).Password, 'Process')
    }
    if ($EnableOTP) {
        $env:TWILIO_ACCOUNT_SID = Read-Host 'Twilio Account SID'
        $taskSmsSecret = Read-Host 'Twilio Auth Token (an / hidden)' -AsSecureString
        if ($taskSmsSecret.Length -eq 0) { throw 'Twilio Auth Token is required with -EnableOTP.' }
        $env:TWILIO_AUTH_TOKEN = [System.Net.NetworkCredential]::new('', $taskSmsSecret).Password
        $env:TWILIO_FROM_NUMBER = Read-Host 'Twilio sender phone number in E.164 format (for example +1...)'
        if ($env:TWILIO_ACCOUNT_SID -notmatch '^AC[0-9a-fA-F]{32}$' -or $env:TWILIO_FROM_NUMBER -notmatch '^\+[1-9][0-9]{7,14}$') {
            throw 'Enter a valid Twilio Account SID and E.164 sender number.'
        }
    }
    & $taskPython -m backend.main
    if ($LASTEXITCODE -ne 0) { throw 'Khoi dong that bai / Startup failed. See error code above.' }
} finally {
    foreach ($taskName in $taskNames) { [Environment]::SetEnvironmentVariable($taskName, $taskPrevious[$taskName], 'Process') }
    if ($taskSecret) { $taskSecret.Dispose() }
    if ($taskAISecret) { $taskAISecret.Dispose() }
    if ($taskSmsSecret) { $taskSmsSecret.Dispose() }
    Pop-Location
}
