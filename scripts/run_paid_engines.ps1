# Overnight runner: waits for API keys in User env, runs each engine once, logs to data/aug25/engines.log
$root = "C:\dev\anees"
$log = "$root\data\aug25\engines.log"
function L($m){ "$(Get-Date -Format 'HH:mm:ss') $m" | Tee-Object -FilePath $log -Append }
L "runner start"
$done = @{}
for ($i=0; $i -lt 480; $i++) {
  foreach ($e in @("eleven_auto","eleven_ara","speechmatics")) {
    if ($done[$e]) { continue }
    $key = if ($e -like "eleven*") { [Environment]::GetEnvironmentVariable("ELEVENLABS_API_KEY","User") } else { [Environment]::GetEnvironmentVariable("SPEECHMATICS_API_KEY","User") }
    if (-not $key) { continue }
    if ($e -like "eleven*") { $env:ELEVENLABS_API_KEY = $key } else { $env:SPEECHMATICS_API_KEY = $key }
    L "running $e"
    $args = if ($e -eq "eleven_auto") { "engine_eleven.py auto" } elseif ($e -eq "eleven_ara") { "engine_eleven.py ara" } else { "engine_speechmatics.py" }
    $out = & python ($args.Split(" ") | ForEach-Object { if ($_ -like "*.py") { "$root\scripts\$_" } else { $_ } }) 2>&1
    $out | ForEach-Object { L "  $_" }
    $done[$e] = $true
  }
  if ($done.Count -eq 3) { L "all done"; break }
  Start-Sleep -Seconds 60
}
L "runner exit"
