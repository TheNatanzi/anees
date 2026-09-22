# ONE-TIME, run by Medi: move the hourly lesson job off the stale C:\dev\anees working copy.
#  1. makes C:\dev\anees-hourly = a clean checkout of master (a git worktree: no download, C:\dev\anees files untouched)
#  2. dry-runs the new job (lists what it would do; spends nothing)
#  3. points the "Anees lesson pipeline" scheduled task at scripts\run_hourly_lessons.ps1 in that checkout
# Undo: schtasks /Change /TN "Anees lesson pipeline" /TR "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\dev\anees\scripts\run_lesson_pipeline.ps1"
$ErrorActionPreference = "Stop"
$dest = "C:\dev\anees-hourly"
git -C C:\dev\anees fetch origin
if (-not (Test-Path $dest)) { git -C C:\dev\anees worktree add -B hourly $dest origin/master } else { git -C $dest pull --ff-only origin master }
$env:ANEES_RAW = "C:\dev\anees\data\lessons"; $env:PYTHONIOENCODING = "utf-8"
python "$dest\scripts\hourly_lessons.py" --dry-run
schtasks /Change /TN "Anees lesson pipeline" /TR "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $dest\scripts\run_hourly_lessons.ps1"
Write-Host "Done. The hourly job now runs $dest\scripts\run_hourly_lessons.ps1 (log: C:\dev\anees\data\lessons\hourly.log)."
