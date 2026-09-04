$env:SPEECHMATICS_API_KEY=[Environment]::GetEnvironmentVariable("SPEECHMATICS_API_KEY","User")
$env:PYTHONIOENCODING="utf-8"
Set-Location C:\dev\anees
python scripts\engine_speechmatics.py ar *>> data\aug25\sm_ar.log
"exit $LASTEXITCODE" | Out-File -Append data\aug25\sm_ar.log
