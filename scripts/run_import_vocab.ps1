# Hourly one-way import of Amal's Google Doc into Supabase `words` (Task Scheduler "Anees vocab import").
# Needs ANEES_DOC_PUBLISHED_URL in the User env (the Doc's publish-to-web URL). Without it the script uses the newest
# saved snapshot and logs that no live source is configured, so nothing changes.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$log = Join-Path $root 'data\vocab\import.log'
$env:PYTHONIOENCODING = 'utf-8'
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') start" | Out-File -Append -Encoding utf8 $log
& python (Join-Path $root 'scripts\import_vocab.py') 2>&1 | Out-File -Append -Encoding utf8 $log
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') exit $LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
