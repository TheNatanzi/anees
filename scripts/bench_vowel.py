# -*- coding: utf-8 -*-
"""Vowel mini-test of the engine benchmark (PR-18, spec 5): can a listener hear WHICH vowel Medi said?

The two items of data/lesson-work/gemini-tests.json (10-02): he said 5ottatet, Amal recast 5attatet; he said oowla, she
recast oola. Each listener hears his clip and her clip of the same word, blind (the prompt names the word in Arabic
script, which carries no short vowel, and never the expected vowel), 3 runs each. A pronunciation note only (S4): never scored
as a missed word. Not run on any other lesson.

    python scripts/bench_vowel.py 2026-10-02 gemini-3.8-flash|gemini-3.1-pro-preview|gpt-audio-1.5
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_freeze as BF  # noqa: E402
import bench_run as BR  # noqa: E402

# word in Arabic script (no short vowels), gloss, and how each expected answer is recognised (never sent to the model)
ITEMS = {"5attatet": {"ar": "خططت", "en": "I planned", "medi": ("o", "u"), "amal": ("a",)},
         "oola": {"ar": "أولى", "en": "first (feminine)", "medi": ("ow", "aw", "au", "ou"), "amal": ("oo", "u", "o", "uu")}}
PROMPT = """This short clip has ONE speaker in an Arabic lesson. Somewhere in it the speaker says the Arabic word «{ar}» ({en}).
Listen only to how THIS speaker pronounces that word in THIS clip (a learner may pronounce it in a non-standard way; a
teacher may not). Do not answer from the dictionary form.
Answer JSON only: {{"word_as_pronounced": "the word in Latin letters exactly as it sounds here", "first_vowel": "the first vowel sound of the word as pronounced, in Latin letters (for example a, i, u, o, e, oo, ow, aw)", "confidence": "high"|"medium"|"low"}}"""


def clips(date):
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    out = []
    for v in truth["vowel"]:
        for who, key in (("Medi", "medi_t"), ("Amal", "amal_t")):
            p = os.path.join(d, "vowel", "%s-%s.wav" % (v["word"], who.lower()))
            if not os.path.exists(p):
                off = truth["offsets"][who]
                BF.cut(BF.track_file(date, who), v[key][0] - 0.3 - off, v[key][1] + 0.3 - off, p)
            out.append((v["word"], who.lower(), p))
    return out


def right(word, who, ans):
    fv = str((ans or {}).get("first_vowel") or "").lower().strip()
    exp = ITEMS[word][who]
    if word == "oola":
        return fv in exp
    return fv[:1] in exp


def main(argv):
    date, model = argv[0], argv[1]
    d = BC.bench_dir(date)
    p = os.path.join(d, "vowel", "%s.json" % model)
    rec = BC.J(p) or {"model": model, "rows": [], "cost_usd": 0.0}
    done = {(r["word"], r["who"], r["run"]) for r in rec["rows"]}
    lock = None
    if model.startswith("gemini"):
        lock = os.path.join(d, ".gemini.lock")
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            raise SystemExit("another Gemini job is running")
    try:
        for word, who, path in clips(date):
            prompt = PROMPT.format(ar=ITEMS[word]["ar"], en=ITEMS[word]["en"])
            for n in (1, 2, 3):
                if (word, who, n) in done:
                    continue
                out = BR.tried(lambda: BR.openai_audio(model, path, prompt) if model.startswith("gpt") else BR.gemini(model, path, prompt))
                ans = out.get("raw") if isinstance(out.get("raw"), dict) else None
                usd = out.get("usd", 0.0)
                if usd:
                    BR.paid(date, "vowel-" + model, "vowel", n, model, usd, BR.wav_seconds(path), provider="openai" if model.startswith("gpt") else "google")
                rec["cost_usd"] = round(rec["cost_usd"] + usd, 6)
                rec["rows"].append({"word": word, "who": who, "run": n, "answer": ans, "error": out.get("error"), "ok": right(word, who, ans)})
                BC.W(p, rec)
    finally:
        if lock and os.path.exists(lock):
            os.unlink(lock)
    for word in ITEMS:
        for who in ("medi", "amal"):
            rows = [r for r in rec["rows"] if r["word"] == word and r["who"] == who]
            print(model, word, who, "%d/%d" % (sum(r["ok"] for r in rows), len(rows)), [((r["answer"] or {}).get("word_as_pronounced"), (r["answer"] or {}).get("first_vowel")) for r in rows])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
