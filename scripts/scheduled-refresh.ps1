[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LogDir = Join-Path $ProjectRoot "logs"
$Collector = Join-Path $ProjectRoot "scripts\collect.py"
$Analyzer = Join-Path $ProjectRoot "scripts\analyze.py"
$AnalysisPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BundledPython = "E:\codex\tools\Python310\python.exe"
$Python = if (Test-Path -LiteralPath $BundledPython) { $BundledPython } else { "python" }

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("refresh-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

function Write-RefreshLog([string]$Message) {
  $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value $line
}

try {
  Write-RefreshLog "Starting Steam review refresh."
  $output = & $Python $Collector 2>&1
  foreach ($line in $output) { Write-RefreshLog ([string]$line) }
  if ($LASTEXITCODE -ne 0) { throw "Collector exited with code $LASTEXITCODE." }
  if (Test-Path -LiteralPath $AnalysisPython) {
    Write-RefreshLog "Starting local model analysis."
    $analysisOutput = & $AnalysisPython $Analyzer 2>&1
    foreach ($line in $analysisOutput) { Write-RefreshLog ([string]$line) }
    if ($LASTEXITCODE -ne 0) { throw "Analyzer exited with code $LASTEXITCODE." }
  } else {
    Write-RefreshLog "Analysis skipped because the local analysis environment is not installed."
  }
  Write-RefreshLog "Refresh completed successfully."
} catch {
  Write-RefreshLog "Refresh failed: $($_.Exception.Message)"
  exit 1
}

Get-ChildItem -LiteralPath $LogDir -Filter "refresh-*.log" -File -ErrorAction SilentlyContinue |
  Where-Object LastWriteTime -lt (Get-Date).AddDays(-30) |
  Remove-Item -Force -ErrorAction SilentlyContinue
