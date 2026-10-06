# -*- coding: utf-8 -*-
"""TR-26 (Medi 2026-10-05: "you are having a really hard time with 3ala and ala and allah ... Can we cue gemini for similar
sounding words?" / "but maybe we get in front of it too"): the sound-alike groups in data/lesson-work/confusables.json as one
cue block for every prompt that hears or reads Medi's Arabic (the second listen in scripts/context_transcribe.py, the
readers' brief). Hand-kept list; add a group when the Lessons page shows a new 'Recording engine wrote ... fixed' swap.

    python scripts/confusables.py        -> prints the cue block
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
PATH = os.path.join(REPO, "data", "lesson-work", "confusables.json")


def load(path=PATH):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"groups": []}


def cue(path=PATH):
    """The cue block, or '' when the list is missing (a prompt never breaks on it)."""
    G = load(path).get("groups") or []
    if not G:
        return ""
    lines = ["Sound-alike words the engine keeps swapping in Medi's Arabic - when you hear one of a group, consider the others and pick by the word after it:"]
    for g in G:
        ws = " / ".join(f"{w.get('arabic')} ({w.get('arabizi')} = {w.get('english')})" for w in g.get("words") or [])
        lines.append(f"- {ws}." + (f" {g['cue']}" if g.get("cue") else ""))
    return "\n".join(lines)


if __name__ == "__main__":
    print(cue())
