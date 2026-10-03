# Hourly one-way import of Amal's Google Doc into Supabase `words` (Task Scheduler "Anees vocab import").
# Source (rule AM-20): G:\My Drive\Anees doc sync\amal-vocab-doc.md, exported from Amal's Doc every hour by the Apps
# Script "Anees doc sync" under wc@adibs.com (scripts/apps_script/doc_sync) and synced here by Drive for desktop.
# An export older than 2 h is never imported: the log says why, and Progress/Lessons show the LS-04 line.
# ANEES_DOC_SYNC_DIR overrides the folder.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$log = Join-Path $root 'data\vocab\import.log'
$env:PYTHONIOENCODING = 'utf-8'
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') start" | Out-File -Append -Encoding utf8 $log
& python (Join-Path $root 'scripts\import_vocab.py') 2>&1 | Out-File -Append -Encoding utf8 $log
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') exit $LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
