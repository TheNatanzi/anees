# Hourly lesson job (replaces run_lesson_pipeline.ps1). Runs from a CLEAN clone of master; the raw lesson archive stays
# in C:\dev\anees\data\lessons. Loads new lessons, checks the numbers, publishes only through scripts\publish_guard.py
# (Medi decision 7, 2026-09-29), never emails or sends anything.
# Log: UTF-8 lines in $ANEES_RAW\hourly.log. Before 2026-09-29 `*>>` wrote UTF-16 and wrapped git's progress text in
# PowerShell error records, so the log was hard to read and grep; the exit code was never logged.
$env:ELEVENLABS_API_KEY=[Environment]::GetEnvironmentVariable("ELEVENLABS_API_KEY","User")
$env:PYTHONIOENCODING="utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}   # read python's UTF-8 output as UTF-8 (not the OEM code page)
if (-not $env:ANEES_RAW) { $env:ANEES_RAW="C:\dev\anees\data\lessons" }
$log = Join-Path $env:ANEES_RAW "hourly.log"
function Write-Log([string]$line) { $line | Out-File -Append -Encoding utf8 $log }
function Invoke-Logged([string]$exe, [string[]]$argv) {
  # cmd /c merges stderr into stdout as plain text (no PowerShell error records)
  $quoted = ($argv | ForEach-Object { '"' + $_ + '"' }) -join ' '
  cmd /c "`"$exe`" $quoted 2>&1" | ForEach-Object { Write-Log "$_" }
  return $LASTEXITCODE
}
Set-Location (Join-Path $PSScriptRoot "..")
Write-Log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') === hourly run"
$pull = Invoke-Logged "git" @("pull", "--ff-only", "origin", "master")
if ($pull -ne 0) {
  # usually: local commits an earlier blocked run kept (the publish guard said no). The job still runs; its guarded
  # push rebases them onto master and re-checks the numbers first.
  Write-Log "$(Get-Date -Format 'HH:mm:ss') git pull --ff-only failed (exit $pull): local commits wait for the publish guard"
}
$rc = Invoke-Logged "python" @("scripts\hourly_lessons.py")
$why = if ($rc -ne 0) { " (a failure or a publish block: see the lines above and data\publish-guard\state.json)" } else { "" }
Write-Log "$(Get-Date -Format 'HH:mm:ss') hourly_lessons exit $rc$why"
exit $rc
