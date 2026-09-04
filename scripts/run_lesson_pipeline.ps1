# Hourly: transcribe any new Meet recording with ElevenLabs and email Medi the transcript page.
$env:ELEVENLABS_API_KEY=[Environment]::GetEnvironmentVariable("ELEVENLABS_API_KEY","User")
$env:PYTHONIOENCODING="utf-8"
Set-Location C:\dev\anees
python scripts\lesson_pipeline.py *>> data\lessons\pipeline.log
