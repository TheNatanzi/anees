# -*- coding: utf-8 -*-
"""Amal's listening check (Medi 2026-10-04 "make it for amal"): 40 of HER OWN lines where the second AI listen (Gemini)
wrote different words than the first engine (ElevenLabs). She plays her clip and taps which version is right.

    python scripts/build_amal_listen.py --src C:/dev/anees-wt-bench        # where data/lesson-work/rehear/<date>/amal lives

Reads (never writes) <src>/data/lesson-work/rehear/<date>/amal/proposals.json + clips/amal-<i>.wav. Writes
  docs/data/amal-listen.json               the page data: items {id, date, mmss, clip, a, b} - BLIND (no engine names)
  docs/lessons/<date>/clips/al-<sha1>.mp3  her clip, mono 32 kbps (force-add them: *.mp3 is git-ignored)
  data/lesson-work/amal-listen-key.json    the unblinding key (which of a/b is which engine, agree, line i) - not published

Sample: fixed seed, 20 lines where all 3 Gemini runs agreed + 20 where 2 of 3 did, split evenly over the lessons. Skipped:
either text longer than 140 characters, a clip longer than 15 s, the two texts equal once punctuation is stripped.
No AI call, no database. Re-running with the same sources gives the same sample and the same a/b order."""
import argparse, hashlib, json, random, subprocess, sys, unicodedata, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = "amal-listen-2026-10-04"
DATES = ("2026-09-28", "2026-10-02")
PER = 10            # per lesson, per agree level -> 2 lessons x 2 levels x 10 = 40
MAX_CHARS, MAX_SECS = 140, 15.0


def bare(s):
    """The text without punctuation, symbols or extra spaces (two lines that differ only there are 'equal')."""
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = "".join(" " if unicodedata.category(c)[0] in "PSZ" else c for c in s)
    return " ".join(s.lower().split())


def wav_secs(p):
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / float(w.getframerate() or 1)


def clip_name(date, i):
    return "al-" + hashlib.sha1(f"{date}|{i}".encode("utf-8")).hexdigest()[:10] + ".mp3"


def eligible(src, date):
    base = src / "data" / "lesson-work" / "rehear" / date / "amal"
    rows = json.loads((base / "proposals.json").read_text(encoding="utf-8"))["rows"]
    out = []
    for r in rows:
        if r.get("status") != "proposed" or r.get("kind") != "words" or r.get("agree") not in (2, 3):
            continue
        e, h = str(r.get("engine") or "").strip(), str(r.get("heard") or "").strip()
        wav = base / "clips" / f"amal-{int(r['i']):04d}.wav"
        if not e or not h or len(e) > MAX_CHARS or len(h) > MAX_CHARS or bare(e) == bare(h) or not wav.exists():
            continue
        secs = wav_secs(wav)
        if secs > MAX_SECS:
            continue
        out.append({"date": date, "i": int(r["i"]), "t": r.get("t"), "mmss": r.get("mmss"), "agree": r["agree"],
                    "engine": e, "heard": h, "wav": wav, "secs": round(secs, 2)})
    return sorted(out, key=lambda x: x["i"])


def sample(src, dates=DATES, seed=SEED, per=PER):
    rng = random.Random(seed)
    picked = []
    for date in dates:
        rows = eligible(src, date)
        for agree in (3, 2):
            pool = [r for r in rows if r["agree"] == agree]
            if len(pool) < per:
                raise SystemExit(f"{date}: only {len(pool)} usable lines with agree == {agree} (need {per})")
            picked += rng.sample(pool, per)
    rng.shuffle(picked)                       # the lessons and the agree levels are mixed on the page
    for r in picked:
        r["engine_is"] = "a" if rng.random() < 0.5 else "b"
    return picked


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT), help="checkout that holds data/lesson-work/rehear/<date>/amal")
    ap.add_argument("--no-audio", action="store_true", help="write the two JSON files only")
    a = ap.parse_args(argv)
    src = Path(a.src)
    picked = sample(src)
    items, key = [], []
    for r in picked:
        name = clip_name(r["date"], r["i"])
        rel = f"{r['date']}/clips/{name}"                       # under docs/lessons/, like amal-review.json
        out = ROOT / "docs" / "lessons" / rel
        if not a.no_audio:
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(r["wav"]), "-ac", "1", "-b:a", "32k", "-map_metadata", "-1",
                            "-fflags", "+bitexact", "-flags:a", "+bitexact", str(out)], check=True)
        iid = f"{r['date']}:{r['i']}"
        first, second = (r["engine"], r["heard"]) if r["engine_is"] == "a" else (r["heard"], r["engine"])
        items.append({"id": iid, "date": r["date"], "mmss": r["mmss"], "clip": rel, "a": first, "b": second})
        key.append({"id": iid, "word_key": "listen:" + iid, "date": r["date"], "i": r["i"], "t": r["t"], "mmss": r["mmss"], "agree": r["agree"],
                    "a": "elevenlabs" if r["engine_is"] == "a" else "gemini", "b": "gemini" if r["engine_is"] == "a" else "elevenlabs",
                    "elevenlabs": r["engine"], "gemini": r["heard"], "clip": rel, "clip_secs": r["secs"]})
    page = {"set": SEED, "lessons": list(DATES), "n": len(items),
            "note": "Amal's own lines, two versions each, order shuffled per line. Her tap: amal_rules source 'listen-check', "
                    "word_key 'listen:<id>', payload.choice a / b / both_wrong / same (+ typed). Built by scripts/build_amal_listen.py.",
            "items": items}
    (ROOT / "docs" / "data" / "amal-listen.json").write_text(json.dumps(page, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    keydoc = {"set": SEED, "about": "Unblinding key for docs/data/amal-listen.json (never published). a / b = which engine wrote that "
                                    "version; agree = how many of Gemini's 3 runs agreed; i = the line in rehear/<date>/amal/proposals.json.",
              "counts": {f"{d} agree {g}": sum(1 for k in key if k["date"] == d and k["agree"] == g) for d in DATES for g in (3, 2)},
              "items": key}
    (ROOT / "data" / "lesson-work" / "amal-listen-key.json").write_text(json.dumps(keydoc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"amal-listen: {len(items)} lines", keydoc["counts"], "| clips", "skipped" if a.no_audio else "written")


if __name__ == "__main__":
    main()
