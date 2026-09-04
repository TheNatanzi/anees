"""Shared helpers for paid-engine tests (ElevenLabs Scribe v2, Speechmatics ar_en)."""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "data" / "aug25" / "audio" / "aug25.mp3"
OUT = ROOT / "data" / "aug25"

def need_key(name):
    k = os.environ.get(name)
    if not k:
        sys.exit(f"MISSING {name} in environment")
    return k

def words_to_turns(words, gap=1.2):
    """words: list of dict(text,start,end,speaker). Merge into speaker turns."""
    turns = []
    for w in words:
        if not w.get("text", "").strip():
            continue
        if turns and turns[-1]["speaker"] == w["speaker"] and w["start"] - turns[-1]["end"] < gap:
            turns[-1]["text"] += " " + w["text"].strip()
            turns[-1]["end"] = w["end"]
        else:
            turns.append({"speaker": w["speaker"], "start": w["start"], "end": w["end"], "text": w["text"].strip()})
    return turns

def write_turns(turns, stem):
    (OUT / f"{stem}_turns.json").write_text(json.dumps(turns, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"[{t['start']:7.1f}-{t['end']:7.1f}] {t['speaker']}: {t['text']}" for t in turns]
    (OUT / f"{stem}_turns.txt").write_text("\n".join(lines), encoding="utf-8")
    spk = {}
    for t in turns:
        spk[t["speaker"]] = spk.get(t["speaker"], 0) + 1
    print(f"{stem}: {len(turns)} turns, words={sum(len(t['text'].split()) for t in turns)}, speakers={spk}")
