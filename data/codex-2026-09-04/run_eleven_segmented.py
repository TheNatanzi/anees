from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


HERE = Path(__file__).resolve().parent
OUT = HERE / "results-elevenlabs-segmented.json"
PRICE_PER_HOUR = 0.22


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def call(clip: Path) -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing")
    last = None
    for attempt, delay in enumerate((0, 2, 5), start=1):
        if delay:
            time.sleep(delay)
        started = time.perf_counter()
        with clip.open("rb") as stream:
            response = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": key},
                data={
                    "model_id": "scribe_v2",
                    "diarize": "true",
                    "num_speakers": "2",
                    "timestamps_granularity": "word",
                    "tag_audio_events": "true",
                    "no_verbatim": "false",
                },
                files={"file": (clip.name, stream, "audio/mpeg")},
                timeout=300,
            )
        elapsed = round(time.perf_counter() - started, 3)
        last = {"status_code": response.status_code, "elapsed_seconds": elapsed, "attempt": attempt}
        if response.status_code == 200:
            return {**last, "raw": response.json()}
        last["error"] = response.text[:1000]
        if response.status_code != 429 and response.status_code < 500:
            return last
    return last or {"status_code": None, "error": "no attempt"}


def main():
    manifest = load(HERE / "manifest.json")
    rows = load(OUT) if OUT.exists() else []
    done = {row["index"] for row in rows}
    for window in manifest["windows"]:
        if window["index"] in done:
            continue
        print(f"CALL segmented-control clip {window['index']:02d}", flush=True)
        result = call(Path(window["clip"]))
        payload = result.get("raw", {})
        rows.append(
            {
                "index": window["index"],
                "arm": "elevenlabs_segmented_no_keyterms_posthoc",
                "model": "scribe_v2",
                "preregistered": False,
                "chat": window["message"],
                "window_start": window["window_start"],
                "window_end": window["window_end"],
                "duration": window["duration"],
                "clip_sha256": window["clip_sha256"],
                "estimated_audio_cost_usd": round(window["duration"] / 3600 * PRICE_PER_HOUR, 6),
                **result,
                "text": payload.get("text", "").strip(),
            }
        )
        rows.sort(key=lambda row: row["index"])
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"DONE segmented-control clip {window['index']:02d} status={result.get('status_code')} "
            f"chars={len(payload.get('text', ''))} elapsed={result.get('elapsed_seconds')}s",
            flush=True,
        )
    print("COMPLETE", flush=True)


if __name__ == "__main__":
    main()
