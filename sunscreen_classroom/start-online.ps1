param()
$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$runtime = Join-Path $appRoot '.runtime'
$configPath = Join-Path $appRoot 'data\relay-config.json'
$pythonPath = Join-Path $appRoot '.venv\Scripts\python.exe'
$relayPath = Join-Path $appRoot 'scripts\local_relay.py'
$recordPath = Join-Path $runtime 'relay.json'
if (-not (Test-Path -LiteralPath $configPath)) { throw 'Missing data/relay-config.json. Configure the online classroom connection first.' }
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run setup-local.ps1 first.' }
if (Test-Path -LiteralPath $recordPath) {
    $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)" -ErrorAction SilentlyContinue
    if ($existing -and $existing.CommandLine -and $existing.CommandLine.Contains($relayPath)) {
        Write-Output 'Online classroom connection is already running.'
        return
    }
}
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$server = Start-Process -FilePath $pythonPath -ArgumentList @('-u',"`"$relayPath`"",'--config',"`"$configPath`"") -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'relay.stdout.log') -RedirectStandardError (Join-Path $runtime 'relay.stderr.log')
@{pid=$server.Id;python=$pythonPath;script=$relayPath} | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding utf8
Write-Output 'Online classroom connection started. Keep this computer awake and online during class.'
Write-Output 'Teacher: https://sunscreen-classroom.onrender.com/teacher'
Write-Output "Connection log: $runtime\relay.stdout.log"
