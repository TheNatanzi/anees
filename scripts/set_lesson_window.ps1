# Medi 2026-10-26 ("we can turn off the hourly, amal and I always have our lessons between noon-5pm"):
# the "Anees lesson pipeline" task runs only from 12:15 to 21:15 (every hour, 10 runs a day): the lesson window plus
# 4 hours for late recordings. The Amal trigger (every 15 min) is a separate task and keeps running all day.
# Re-run this file to restore the window; Undo (back to all day): schtasks /Change /TN "Anees lesson pipeline" /RI 60 /DU 24:00
$ErrorActionPreference = "Stop"
$name = "Anees lesson pipeline"
$t = New-ScheduledTaskTrigger -Daily -At "12:15"
$t.Repetition = (New-ScheduledTaskTrigger -Once -At "12:15" -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Hours 9 -Minutes 1)).Repetition
Set-ScheduledTask -TaskName $name -Trigger $t | Out-Null
$i = Get-ScheduledTaskInfo -TaskName $name
Write-Host "Lesson job: every hour 12:15-21:15. Next run: $($i.NextRunTime)"
