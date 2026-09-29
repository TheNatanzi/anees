# Every 15 minutes: has Amal answered anything new? (scripts/amal_trigger.py, Medi M3 2026-09-29)
# Detects a new/changed answer in any of her sources, re-pulls it, rebuilds, rescores, logs the firing, and pushes ONLY
# through the publish guard. Skips quietly when the hourly job holds the shared lock. Never sends anything to anyone.
$env:PYTHONIOENCODING="utf-8"
if (-not $env:ANEES_RAW) { $env:ANEES_RAW="C:\dev\anees\data\lessons" }
$log = Join-Path $env:ANEES_RAW "amal-trigger.log"
Set-Location (Join-Path $PSScriptRoot "..")
"$(Get-Date -Format s) start" | Out-File -FilePath $log -Append -Encoding utf8
git pull --ff-only origin master 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
python scripts\amal_trigger.py --publish 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
$code = $LASTEXITCODE
"$(Get-Date -Format s) exit $code" | Out-File -FilePath $log -Append -Encoding utf8
exit $code
