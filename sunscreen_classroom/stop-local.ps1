$ErrorActionPreference = 'Stop'
$recordPath = Join-Path $PSScriptRoot '.runtime\server.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Output 'No recorded classroom process.'; return }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$processes = Get-CimInstance Win32_Process
$launcher = $processes | Where-Object { $_.ProcessId -eq $record.pid }
$matches = $processes | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains('backend.app:app') -and
    $_.CommandLine -match ('--port\s+' + [regex]::Escape([string]$record.port) + '(\s|$)') -and
    ($_.CommandLine.Contains($record.python) -or ($_.ParentProcessId -eq $record.pid -and $launcher -and $launcher.CommandLine.Contains($record.python)))
}
foreach ($target in $matches) { Stop-Process -Id $target.ProcessId -ErrorAction SilentlyContinue }
if ($launcher -and $launcher.CommandLine -and $launcher.CommandLine.Contains($record.python) -and $launcher.CommandLine.Contains('backend.app:app')) { Stop-Process -Id $launcher.ProcessId -ErrorAction SilentlyContinue }
Remove-Item -LiteralPath $recordPath
Write-Output 'Stopped only the recorded sunscreen classroom processes.'
