param(
    [string]$PythonPath = "",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$entry = Join-Path $projectRoot 'campus_monitor.py'
if (-not $PythonPath) {
    $localPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $localPython) { $PythonPath = $localPython }
    else {
        $command = Get-Command python -ErrorAction SilentlyContinue
        if (-not $command) { throw 'Python not found; pass -PythonPath.' }
        $PythonPath = $command.Source
    }
}
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
if (-not (Test-Path -LiteralPath $entry)) { throw 'campus_monitor.py not found.' }
$backgroundPython = Join-Path (Split-Path -Parent $PythonPath) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $backgroundPython)) { throw 'pythonw.exe is required for hidden tasks.' }

$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$dailyAction = New-ScheduledTaskAction -Execute $backgroundPython -Argument ('"' + $entry + '" daily') -WorkingDirectory $projectRoot
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At '09:00'

$botSettings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$botAction = New-ScheduledTaskAction -Execute $backgroundPython -Argument ('"' + $entry + '" listen') -WorkingDirectory $projectRoot
$botTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
if ($DryRun) {
    [pscustomobject]@{Daily='09:00'; Listener='AtLogOn'; Python=$backgroundPython; Root=$projectRoot; Writes=$false} | ConvertTo-Json
    return
}
Register-ScheduledTask -TaskName 'DailyAutomation_CampusDaily' -Action $dailyAction -Trigger $dailyTrigger -Principal $principal -Settings $settings -Force | Out-Null
Register-ScheduledTask -TaskName 'DailyAutomation_DingTalkListener' -Action $botAction -Trigger $botTrigger -Principal $principal -Settings $botSettings -Force | Out-Null
# Replace only this project's earlier standalone schedule mail.
$legacy = Get-ScheduledTask -TaskName 'DailySchedule' -ErrorAction SilentlyContinue
if ($legacy -and ($legacy.Actions.Execute -like "*$projectRoot*" -or $legacy.Actions.Arguments -like "*$projectRoot*") -and ($legacy.Actions.Execute -match 'run_schedule' -or $legacy.Actions.Arguments -match 'run_schedule|schedule_manager')) {
    $legacy | Disable-ScheduledTask | Out-Null
}

$runtime = Join-Path $projectRoot 'runtime_local'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$record = [ordered]@{
    installed_at = (Get-Date).ToUniversalTime().ToString('o')
    tasks = @('DailyAutomation_CampusDaily', 'DailyAutomation_DingTalkListener')
    python = $backgroundPython
}
$marker = Join-Path $runtime 'tasks_installed.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($marker, ($record | ConvertTo-Json), $utf8)

Write-Host 'Registered campus check at 09:00 and DingTalk intake at logon.'
Write-Host 'Complete local login and encrypted credentials before enabling monitoring.'
