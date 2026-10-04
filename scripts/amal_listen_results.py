# -*- coding: utf-8 -*-
"""Amal's listening check: her answers against the key (Medi 2026-10-04 "make it for amal"). READ-ONLY.

    python scripts/amal_listen_results.py            # the table
    python scripts/amal_listen_results.py --lines    # + every line with her answer
    python scripts/amal_listen_results.py --json

Reads Supabase amal_rules (source 'listen-check'; an undone tap is left out and the latest tap per line wins - scripts/db.py,
AM-17) and data/lesson-work/amal-listen-key.json (which of a/b was ElevenLabs / Gemini, how many Gemini runs agreed).
Prints, for agree == 3 and agree == 2 separately: ElevenLabs right / Gemini right / both wrong / same or can't tell /
not answered. Counts only - nothing is written anywhere."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
KEY = ROOT / "data" / "lesson-work" / "amal-listen-key.json"
SOURCE = "listen-check"
COLS = ("elevenlabs", "gemini", "both_wrong", "same", "unanswered")
LABEL = {"elevenlabs": "ElevenLabs right", "gemini": "Gemini right", "both_wrong": "both wrong", "same": "same / can't tell",
         "unanswered": "not answered"}


def latest(rows):
    """{word_key: her latest tap} (rows in id order; undone taps already left out by db.select)."""
    out = {}
    for r in sorted(rows or [], key=lambda r: (r.get("id") or 0, str(r.get("created_at") or ""))):
        if r.get("kind") != "undo" and r.get("word_key"):
            out[r["word_key"]] = r
    return out


def verdict(k, row):
    """elevenlabs | gemini | both_wrong | same | unanswered for one key item and her row (or None)."""
    c = ((row or {}).get("payload") or {}).get("choice")
    if c in ("a", "b"):
        return k[c]
    return c if c in ("both_wrong", "same") else "unanswered"


def tally(key_items, rows):
    ans = latest(rows)
    table = {g: {c: 0 for c in COLS} for g in (3, 2)}
    lines = []
    for k in key_items:
        row = ans.get(k["word_key"])
        v = verdict(k, row)
        table.setdefault(k["agree"], {c: 0 for c in COLS})[v] += 1
        lines.append({"id": k["id"], "agree": k["agree"], "result": v, "elevenlabs": k["elevenlabs"], "gemini": k["gemini"],
                      "typed": ((row or {}).get("payload") or {}).get("typed"), "at": (row or {}).get("created_at")})
    return table, lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    key = json.loads(KEY.read_text(encoding="utf-8"))["items"]
    import db
    rows = db.select("amal_rules", {"select": "id,kind,word_key,payload,created_at", "source": f"eq.{SOURCE}", "order": "id.asc"})
    table, lines = tally(key, rows)
    if a.json:
        print(json.dumps({"table": {str(g): t for g, t in table.items()}, "lines": lines}, ensure_ascii=False, indent=1))
        return
    for g in (3, 2):
        t = table[g]; n = sum(t.values()); done = n - t["unanswered"]
        print(f"Gemini runs agreed {g} of 3 - {n} lines, {done} answered")
        for c in COLS:
            pct = f"  ({round(100 * t[c] / done)}% of answered)" if done and c != "unanswered" else ""
            print(f"   {LABEL[c]:<18} {t[c]:>3}{pct}")
    if a.lines:
        for x in lines:
            print(f"{x['id']:<16} agree {x['agree']}  {LABEL[x['result']]:<18} EL: {x['elevenlabs']} | GM: {x['gemini']}" + (f" | she typed: {x['typed']}" if x["typed"] else ""))


if __name__ == "__main__":
    main()
