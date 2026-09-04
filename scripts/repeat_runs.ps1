$root="C:\dev\anees"; $log="$root\data\aug25\repeat.log"
function L($m){ "$(Get-Date -Format 'HH:mm:ss') $m" | Out-File -FilePath $log -Append -Encoding utf8 }
$env:ELEVENLABS_API_KEY=[Environment]::GetEnvironmentVariable("ELEVENLABS_API_KEY","User")
$env:SPEECHMATICS_API_KEY=[Environment]::GetEnvironmentVariable("SPEECHMATICS_API_KEY","User")
$env:PYTHONIOENCODING="utf-8"
foreach ($tag in @("_r2","_r3")) {
  $env:RUN_TAG=$tag
  L "eleven auto $tag"; & python "$root\scripts\engine_eleven.py" auto 2>&1 | ForEach-Object { L "  $_" }
  L "speechmatics $tag"; & python "$root\scripts\engine_speechmatics.py" 2>&1 | ForEach-Object { L "  $_" }
}
L "REPEAT DONE"
