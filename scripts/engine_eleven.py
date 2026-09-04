"""ElevenLabs Scribe v2 batch test on Aug 25 audio. Usage: python engine_eleven.py [auto|ara]"""
import json, sys, requests
from engine_common import *

key = need_key("ELEVENLABS_API_KEY")
lang = sys.argv[1] if len(sys.argv) > 1 else "auto"
stem = f"eleven_scribe_{lang}"
data = {"model_id": "scribe_v2", "diarize": "true", "num_speakers": "2",
        "timestamps_granularity": "word", "tag_audio_events": "true"}
if lang != "auto":
    data["language_code"] = lang
t0 = time.time()
with open(AUDIO, "rb") as f:
    r = requests.post("https://api.elevenlabs.io/v1/speech-to-text",
                      headers={"xi-api-key": key}, data=data,
                      files={"file": ("aug25.mp3", f, "audio/mpeg")}, timeout=1800)
print("status", r.status_code, f"{time.time()-t0:.0f}s")
if r.status_code != 200:
    sys.exit(r.text[:2000])
res = r.json()
(OUT / f"{stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
words = [{"text": w["text"], "start": w.get("start", 0), "end": w.get("end", 0),
          "speaker": w.get("speaker_id", "?")} for w in res.get("words", []) if w.get("type") == "word"]
write_turns(words_to_turns(words), stem)
print("language_code:", res.get("language_code"), "prob:", res.get("language_probability"))
