from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests


HERE = Path(__file__).resolve().parent
OUT = HERE / "results-elevenlabs-keyterms.json"
PRICE_PER_HOUR = 0.22 + 0.05  # Scribe v2 base + keyterm prompting, official API list price.


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(value):
    OUT.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def keyterms(manifest: dict) -> list[str]:
    components = manifest["openai"]["lexicon_components"]
    values = list(components["chat_forms"])
    for transliteration, arabic in components["document_pairs"]:
        values.extend((transliteration, arabic))
    cleaned = []
    seen = set()
    for value in values:
        value = " ".join(str(value).split()).strip()
        if not value or len(value) >= 50 or len(value.split()) > 5:
            continue
        if re.search(r"[<>{}\[\]\\]", value):
            continue
        folded = value.casefold()
        if folded not in seen:
            seen.add(folded)
            cleaned.append(value)
    return cleaned[:1000]


def call(clip: Path, terms: list[str]) -> dict:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing")
    last = None
    for attempt, delay in enumerate((0, 2, 5), start=1):
        if delay:
            time.sleep(delay)
        started = time.perf_counter()
        with clip.open("rb") as stream:
            response = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": api_key},
                data=[
                    ("model_id", "scribe_v2"),
                    ("diarize", "true"),
                    ("num_speakers", "2"),
                    ("timestamps_granularity", "word"),
                    ("tag_audio_events", "true"),
                    ("no_verbatim", "false"),
                    *(("keyterms", term) for term in terms),
                ],
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
    terms = keyterms(manifest)
    existing = load(OUT) if OUT.exists() else []
    done = {row["index"] for row in existing}
    for window in manifest["windows"]:
        if window["index"] in done:
            continue
        print(f"CALL keyterms clip {window['index']:02d}", flush=True)
        result = call(Path(window["clip"]), terms)
        payload = result.get("raw", {})
        existing.append(
            {
                "index": window["index"],
                "arm": "elevenlabs_keyterms_posthoc",
                "model": "scribe_v2",
                "preregistered": False,
                "chat": window["message"],
                "window_start": window["window_start"],
                "window_end": window["window_end"],
                "duration": window["duration"],
                "clip_sha256": window["clip_sha256"],
                "keyterms": terms,
                "estimated_audio_cost_usd": round(window["duration"] / 3600 * PRICE_PER_HOUR, 6),
                **result,
                "text": payload.get("text", "").strip(),
            }
        )
        existing.sort(key=lambda row: row["index"])
        save(existing)
        print(
            f"DONE keyterms clip {window['index']:02d} status={existing[-1].get('status_code')} "
            f"chars={len(payload.get('text', ''))} elapsed={existing[-1].get('elapsed_seconds')}s",
            flush=True,
        )
    print(f"COMPLETE keyterms={len(terms)}", flush=True)


if __name__ == "__main__":
    main()
