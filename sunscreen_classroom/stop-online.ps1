$ErrorActionPreference = 'Stop'
$recordPath = Join-Path $PSScriptRoot '.runtime\relay.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Output 'No recorded online classroom connection.'; return }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$processes = Get-CimInstance Win32_Process
$launcher = $processes | Where-Object { $_.ProcessId -eq $record.pid }
if ($launcher -and $launcher.CommandLine -and $launcher.CommandLine.Contains($record.python) -and $launcher.CommandLine.Contains($record.script)) {
    $children = $processes | Where-Object { $_.ParentProcessId -eq $record.pid -and $_.CommandLine -and $_.CommandLine.Contains($record.script) }
    foreach ($child in $children) { Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue }
    Stop-Process -Id $launcher.ProcessId -ErrorAction SilentlyContinue
}
Remove-Item -LiteralPath $recordPath
Write-Output 'Stopped only the online classroom connection. Saved classroom data remains on this computer.'
