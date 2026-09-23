# -*- coding: utf-8 -*-
"""Build docs/data/grammar-console.json from tally.json + lesson transcripts.

Only real data. Rules with no recorded use are emitted as status "Untested"
with uses=0 so the console can show an honest empty row.
"""
import json, os, re, glob

ROOT = r"C:\dev\anees-hourly"
DOCS = os.path.join(ROOT, "docs")
LESSONS = r"C:\dev\anees\data\lessons"
OUT = os.path.join(DOCS, "data", "grammar-console.json")

tally = json.load(open(os.path.join(DOCS, "data", "tally.json"), encoding="utf-8"))
buckets = json.load(open(os.path.join(DOCS, "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]

# ---- Medi sentence counts per lesson, straight from the transcripts ----
def medi_sentences(date):
    p = os.path.join(LESSONS, date, "transcript.txt")
    if not os.path.exists(p):
        return None
    t = open(p, encoding="utf-8", errors="replace").read()
    turns = re.findall(r"\[\d+:\d+\]\s*Medi:\s*([^\n]+)", t)
    n = 0
    for turn in turns:
        turn = re.sub(r"\(pause[^)]*\)", " ", turn)
        for part in re.split(r"[.!?؟]+", turn):
            if len(part.strip()) >= 3:
                n += 1
    return n or None

lesson_dates = list(tally["lessons"])
lessons = []
for d in lesson_dates:
    lessons.append({
        "date": d,
        "medi_sentences": medi_sentences(d),
        "slips": tally["totals"]["per_lesson"].get(d, 0),
    })

# ---- roll the tally rules onto buckets ----
by_rule = {r["id"]: r for r in tally["rules"]}

def event(kind, e):
    return {
        "kind": kind,                      # slip | right | ask
        "date": e.get("date"),
        "mmss": e.get("mmss"),
        "t": e.get("t"),
        "said": e.get("said"),
        "recast": e.get("recast"),
        "recast_at": e.get("recast_at"),
        "clip": e.get("clip"),
        "offset": e.get("offset"),
        "audio_note": e.get("audio"),
        "verified": e.get("verified", False),
    }

def status(uses, mistakes):
    if not uses:
        return "Untested"
    pct = round(100 * (uses - mistakes) / uses)
    if uses >= 4 and pct >= 90:
        return "Mastered"
    if pct >= 70:
        return "Good"
    if pct >= 40:
        return "Shaky"
    return "Wrong"

rows = []
for b in buckets:
    rid = b.get("tally_rule")
    r = by_rule.get(rid) if rid else None
    events = []
    if r:
        for e in r.get("slips", []):
            events.append(event("slip", e))
        for e in r.get("rights", []):
            events.append(event("right", e))
        for e in r.get("asks", []):
            events.append(event("ask", e))
    events.sort(key=lambda e: (str(e["date"]), e["t"] if isinstance(e["t"], (int, float)) else 0), reverse=True)
    uses = len(events)
    mistakes = sum(1 for e in events if e["kind"] == "slip")
    asks = sum(1 for e in events if e["kind"] == "ask")
    rows.append({
        "id": b["id"], "family": b["family"], "name": b["name"],
        "one_line": b["one_line"], "examples": b["examples"],
        "why": b["why"], "more": b["more"],
        "tally_rule": rid,
        "tally_title": r["title"] if r else None,
        "kind": r.get("kind") if r else None,
        "uses": uses, "mistakes": mistakes, "asks": asks,
        "pct": round(100 * (uses - mistakes) / uses) if uses else None,
        "status": status(uses, mistakes),
        "events": events,
    })

# ---- per-lesson derived series ----
for L in lessons:
    d = L["date"]
    # One tally rule can feed two buckets (R1 -> B2+B3). Count each recorded
    # event once per lesson, keyed by its source rule and timestamp.
    seen, ev, sound = set(), [], []
    for row in rows:
        for e in row["events"]:
            if e["date"] != d:
                continue
            key = (row["tally_rule"], e["kind"], e["t"], e["mmss"])
            if key in seen:
                continue
            seen.add(key)
            # Family F is pronunciation, not grammar (wiki/18 rule M4).
            (sound if row["family"] == "F" else ev).append(e)
    L["slips_counted"] = sum(1 for e in ev if e["kind"] == "slip")
    L["sound_slips"] = sum(1 for e in sound if e["kind"] == "slip")
    L["unique_rules"] = len({row["id"] for row in rows for e in row["events"] if e["date"] == d})
    L["rights"] = sum(1 for e in ev if e["kind"] == "right")
    L["asks"] = sum(1 for e in ev if e["kind"] == "ask")
    L["mistakes_per_sentence"] = (
        round(L["slips_counted"] / L["medi_sentences"], 4) if L["medi_sentences"] else None
    )
    denom = L["slips_counted"] + L["asks"]
    L["self_correction_rate"] = round(100 * L["asks"] / denom) if denom else None

scored = [r for r in rows if r["uses"]]
payload = {
    "updated": "2026-09-22",
    "source": "docs/data/tally.json (hand-curated, rule M1) + transcripts in C:/dev/anees/data/lessons",
    "coverage": {
        "buckets_total": len(rows),
        "buckets_scored": len(scored),
        "lessons_scored": len(lessons),
        "lessons_recorded": 11,
        "note": "A use is counted only when Amal recast it or Medi asked (rule M1). "
                "39 buckets have no detector yet and show as Untested.",
    },
    "lessons": lessons,
    "rules": rows,
}
json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("wrote", OUT)
print("buckets:", len(rows), "scored:", len(scored))
for L in lessons:
    print(" ", L["date"], "sentences=", L["medi_sentences"], "slips=", L["slips_counted"],
          "asks=", L["asks"], "rights=", L["rights"], "uniq=", L["unique_rules"],
          "m/s=", L["mistakes_per_sentence"], "selfcorr=", L["self_correction_rate"])
from collections import Counter
print(Counter(r["status"] for r in rows))
