# Hourly lesson job (replaces run_lesson_pipeline.ps1). Runs from a CLEAN clone of master; the raw lesson archive stays
# in C:\dev\anees\data\lessons. Loads new lessons, publishes, never emails or sends anything.
$env:ELEVENLABS_API_KEY=[Environment]::GetEnvironmentVariable("ELEVENLABS_API_KEY","User")
$env:PYTHONIOENCODING="utf-8"
if (-not $env:ANEES_RAW) { $env:ANEES_RAW="C:\dev\anees\data\lessons" }
Set-Location (Join-Path $PSScriptRoot "..")
git pull --ff-only origin master *>> (Join-Path $env:ANEES_RAW "hourly.log")
python scripts\hourly_lessons.py *>> (Join-Path $env:ANEES_RAW "hourly.log")
