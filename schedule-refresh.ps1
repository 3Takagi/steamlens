[CmdletBinding()]
param(
  [ValidateSet("Daily", "Weekly")]
  [string]$Frequency = "Daily",
  [ValidatePattern("^(?:[01]\d|2[0-3]):[0-5]\d$")]
  [string]$Time = "09:00",
  [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
  [string]$DayOfWeek = "Monday",
  [switch]$Disable,
  [switch]$Status
)

$ErrorActionPreference = "Stop"
$TaskName = "SteamLens Review Refresh"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RefreshScript = Join-Path $ProjectRoot "scripts\scheduled-refresh.ps1"

if ($Status) {
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if (!$task) {
    Write-Host "SteamLens automatic refresh is not enabled."
    exit 0
  }
  $info = Get-ScheduledTaskInfo -TaskName $TaskName
  Write-Host "Task: $TaskName"
  Write-Host "State: $($task.State)"
  Write-Host "Next run: $($info.NextRunTime)"
  Write-Host "Last run: $($info.LastRunTime)"
  Write-Host "Last result: $($info.LastTaskResult)"
  exit 0
}

if ($Disable) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "SteamLens automatic refresh has been disabled."
  exit 0
}

if (!(Test-Path -LiteralPath $RefreshScript)) { throw "Refresh script was not found: $RefreshScript" }

$runAt = [datetime]::Today.Add([timespan]::Parse($Time))
$trigger = if ($Frequency -eq "Weekly") {
  New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $DayOfWeek -At $runAt
} else {
  New-ScheduledTaskTrigger -Daily -At $runAt
}

$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RefreshScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $ProjectRoot
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Refresh SteamLens public review samples." -Force | Out-Null
Write-Host "SteamLens automatic refresh is enabled."
Write-Host "Schedule: $Frequency at $Time$(if ($Frequency -eq 'Weekly') { " on $DayOfWeek" })"
Write-Host "Missed runs will start after the next sign-in."
