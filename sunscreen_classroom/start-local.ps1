param([int]$Port = 8010, [switch]$Lan)
$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$runtime = Join-Path $appRoot '.runtime'
$pythonPath = Join-Path $appRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run setup-local.ps1 first.' }
if (-not (Test-Path -LiteralPath (Join-Path $appRoot 'frontend\dist\index.html'))) { throw 'Missing frontend build. Run setup-local.ps1.' }
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { throw "Port $Port is already occupied. Choose another -Port." }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$existingRecordPath = Join-Path $runtime 'server.json'
if (Test-Path -LiteralPath $existingRecordPath) {
    $existingRecord = Get-Content -LiteralPath $existingRecordPath -Raw | ConvertFrom-Json
    $existingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($existingRecord.pid)" -ErrorAction SilentlyContinue
    if ($existingProcess -and $existingProcess.CommandLine -and $existingProcess.CommandLine.Contains($pythonPath) -and $existingProcess.CommandLine.Contains('backend.app:app')) {
        throw 'This classroom already has a recorded server. Stop it with stop-local.ps1 first.'
    }
}
$bindAddress = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }
$server = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','backend.app:app','--host',$bindAddress,'--port',"$Port") -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'server.stdout.log') -RedirectStandardError (Join-Path $runtime 'server.stderr.log')
@{pid=$server.Id;port=$Port;python=$pythonPath;root=$appRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'server.json') -Encoding utf8
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    Start-Sleep -Milliseconds 500
    $server.Refresh()
    if ($server.HasExited) { throw "Startup failed. Check $runtime\server.stderr.log" }
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
        if ($health.status -eq 'ok') {
            Write-Output "Student: http://127.0.0.1:$Port/"
            Write-Output "Teacher: http://127.0.0.1:$Port/teacher"
            Write-Output "Teacher login details: $appRoot\data\local-credentials.json"
            return
        }
    } catch { }
}
throw "Startup timed out. Check $runtime\server.stderr.log; stop only this app with stop-local.ps1."
