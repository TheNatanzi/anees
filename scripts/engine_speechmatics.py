"""Speechmatics batch test (ar_en bilingual, enhanced, speaker diarization) on Aug 25 audio."""
import json, sys, requests
from engine_common import *

key = need_key("SPEECHMATICS_API_KEY")
lang = sys.argv[1] if len(sys.argv) > 1 else "ar_en"
stem = f"speechmatics_{lang}" + os.environ.get("RUN_TAG", "")
H = {"Authorization": f"Bearer {key}"}
BASE = "https://asr.api.speechmatics.com/v2"
cfg = {"type": "transcription",
       "transcription_config": {"language": lang, "operating_point": "enhanced",
                                "diarization": "speaker", "enable_entities": False}}
t0 = time.time()
with open(AUDIO, "rb") as f:
    r = requests.post(f"{BASE}/jobs", headers=H, data={"config": json.dumps(cfg)},
                      files={"data_file": ("aug25.mp3", f, "audio/mpeg")}, timeout=600)
print("submit", r.status_code, r.text[:300])
if r.status_code not in (200, 201):
    sys.exit(1)
job = r.json()["id"]
while True:
    time.sleep(15)
    s = requests.get(f"{BASE}/jobs/{job}", headers=H, timeout=60).json()["job"]["status"]
    print(f"  {s} {time.time()-t0:.0f}s")
    if s == "done":
        break
    if s in ("rejected", "deleted", "expired"):
        sys.exit(f"job {s}: " + json.dumps(requests.get(f'{BASE}/jobs/{job}', headers=H).json())[:1500])
r = requests.get(f"{BASE}/jobs/{job}/transcript", headers=H, params={"format": "json-v2"}, timeout=120)
res = r.json()
(OUT / f"{stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
words = []
for it in res.get("results", []):
    if it.get("type") != "word":
        continue
    a = it["alternatives"][0]
    words.append({"text": a["content"], "start": it["start_time"], "end": it["end_time"],
                  "speaker": a.get("speaker", "?")})
write_turns(words_to_turns(words), stem)
