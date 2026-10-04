# -*- coding: utf-8 -*-
"""Gemini variables test on the frozen engine benchmark (PR-18; spec ANEES-GEMINI-VARIABLES-TEST-SPEC-2026-10-04).

One idea at a time against the baseline listener (gemini-flash-t1 = Gemini 3.8 Flash, context +-40 s, temperature 1).
Every variable is its own engine id (gemini-flash-<vid>-t1), 3 runs, scored by scripts/bench_score.py like the baseline.
The answer key (truth.json) is never written here; the variables' prompts are frozen with hashes in a NEW folder
(bench/<date>/variables/) before the first paid call, and no prompt holds the truth, a correction row or a ruling.

    python scripts/bench_vars.py 2026-10-02 freeze [vid ...]     # variables.json + small prompt sets + manifest (sha)
    python scripts/bench_vars.py 2026-10-02 check                # re-hash every frozen variable (exit 1 on a change)
    python scripts/bench_vars.py 2026-10-02 run <vid> [runs=3] [--limit N]
    python scripts/bench_vars.py 2026-10-02 derive               # v1h / v4h: the same answers with the weak changes dropped (no call)

Variables that only touch some lines (v2 forced choice, v3 two clips, v6 Arabic span, v13 edge re-cut) are scored as
baseline + that step: run n keeps the baseline's run n on every other line.
"""
import collections, hashlib, json, os, random, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402

BASE = "gemini-flash-t1"
MODEL = "gemini-3.8-flash"
WRITE_MARK = "Write exactly what MEDI said in the target line:"
ANSWER_RE = re.compile(r"Answer JSON only: \{.*\}\s*$", re.S)
F_ARABIC = '"arabic": "his words in Arabic script (English words stay English)"'
F_ARABIZI = '"arabizi": "his words in Latin letters with 2 3 5 6 7 8 9 for ء ع خ ط ح غ ص"'
F_TAIL = '"engine_was_wrong": true|false, "changes": [{"engine": "...", "said": "..."}], "confidence": "high"|"medium"|"low", "why": "one short reason"'
F_HARAKAT = ('"arabic": "his words in Arabic script WITH the small vowel marks (harakat: fatha, damma, kasra, shadda, sukun) on every Arabic word, '
             'exactly as HE pronounced them - a learner may say a wrong vowel: write the vowel you hear, not the dictionary form (English words stay English)"')
LONG_WORDS = 12                  # v6: a "long line" = 12+ engine words (chosen by length alone, never by the key)
SPAN_PAD, MAX_SPANS = 0.4, 3
AMAL_NEXT_S = 15.0               # the hold rule of scripts/bench_rehear.py


def answer(*fields):
    return "Answer JSON only: {" + ", ".join(fields) + "}"


def engine_id(vid):
    return "gemini-flash-%s-t1" % vid


def vdir(date):
    return os.path.join(BC.bench_dir(date), "variables")


# ------------------------------------------------------------------ the variables (text frozen by `freeze`)

ACCENT = """Medi's accent (about his SOUNDS only; true of every lesson, no vocabulary):
- he often drops or weakens ع, and his ط is weak;
- his emphatic letters come out plain: ط sounds like ت, ض sounds like د;
- his ح sounds like ه (an English h);
- n before b comes out as m (nb -> mb).
A word that differs from a real word that fits the sentence only by these sounds is that word said in his accent
(pronunciation is not a wrong word): write it with its normal letters. Do not turn it into a different, more common
word or into English look-alike words because of his accent."""


def taught_list(date):
    """V8's list: the lesson's taught words from the lesson-type read (data/lesson-work/lesson-types/<date>.json) -
    word, her spelling, meaning. Never the notes (they describe his mistakes), never a correction row."""
    j = BC.J(os.path.join(BC.REPO, "data", "lesson-work", "lesson-types", date + ".json")) or {}
    return "\n".join("- %s%s: %s" % (w["arabic"], " (%s)" % w["latin"] if w.get("latin") else "", w["english"]) for w in j.get("taught_words") or [])


def variables(date):
    return {
        "v1": {"name": "evidence: heard or inferred", "kind": "full",
               "pre_answer": 'For every change you make, say what it rests on: "heard" = you can clearly hear that word in the audio itself; '
                             '"inferred" = the audio is unclear at that place and you chose the word mainly from the context, the chat or what would make sense.',
               "answer": answer(F_ARABIC, F_ARABIZI, '"engine_was_wrong": true|false, "changes": [{"engine": "...", "said": "...", "evidence": "heard"|"inferred"}], "confidence": "high"|"medium"|"low", "why": "one short reason"')},
        "v2": {"name": "forced choice on held / no-agreement lines", "kind": "subset"},
        "v3": {"name": "two clips: his line + Amal's next", "kind": "subset"},
        "v4": {"name": "confidence per changed word", "kind": "full",
               "pre_answer": 'For every change you make, give your confidence that the AUDIO ITSELF carries that word: "high" = clearly audible; '
                             '"medium" = probably; "low" = mostly a guess from the context.',
               "answer": answer(F_ARABIC, F_ARABIZI, '"engine_was_wrong": true|false, "changes": [{"engine": "...", "said": "...", "confidence": "high"|"medium"|"low"}], "confidence": "high"|"medium"|"low", "why": "one short reason"')},
        "v5": {"name": "second guess for unsure words", "kind": "full",
               "pre_answer": "For each word of your answer that you are not sure you heard right, also give your SECOND guess: the next most likely "
                             "word he said at that place (again what he said, not what he should have said).",
               "answer": answer(F_ARABIC, F_ARABIZI, F_TAIL, '"second_guess": [{"said": "the unsure word exactly as written in arabic", "second": "the next most likely word"}] (an empty list when you are sure of every word)')},
        "v6": {"name": "Arabic span inside long lines (two calls)", "kind": "subset"},
        # review ANEES-FABLE-53-TO-60-REVIEW-2026-10-04, experiment 3 (Medi 2026-10-04 "do all of your recommendations"):
        "v13": {"name": "edge re-cut: clips that start or end on speech, cut out to the nearest silence", "kind": "subset"},
        "v7": {"name": "accent note", "kind": "full", "insert": ACCENT},
        "v8": {"name": "taught-word list, SAID + MEANT", "kind": "full", "text_key": "said",
               "insert": "Words Amal taught or re-taught in THIS lesson (her list). He is still learning them, so he may say one of them WRONG (a wrong vowel or "
                         "ending, a wrong form, or a different word by mistake), and he also says many words that are not on the list:\n" + taught_list(date),
               "pre_answer": "Give TWO answers for the target line:\n"
                             "- SAID: exactly what he said, as it sounds, with his mistakes kept - even when it is not a real word or is the wrong word. The list is NOT a "
                             "reason to write a list word: write a list word in SAID only when that is what you hear.\n"
                             "- MEANT: the line as he intended it - the same line with the word(s) he was aiming for (from the list or the context) in place of his "
                             "mistakes. When he made no mistake, MEANT is the same as SAID.",
               "answer": answer('"said": "SAID, in Arabic script (English words stay English)"', '"meant": "MEANT, in Arabic script (English words stay English)"',
                                '"arabizi": "SAID in Latin letters with 2 3 5 6 7 8 9 for ء ع خ ط ح غ ص"', F_TAIL)},
        "v9": {"name": "thinking level high", "kind": "full", "cfg": {"thinkingConfig": {"thinkingLevel": "high"}, "maxOutputTokens": 8192}},
        "v10": {"name": "vowel marks (harakat)", "kind": "full", "answer": answer(F_HARAKAT, F_ARABIZI, F_TAIL)},
        # Gemini's own two untested ideas (scripts/bench_ask_gemini.py, 2026-10-04; Medi: "a" = test both):
        "v11": {"name": "one-field answer (the text only)", "kind": "full", "answer": answer(F_ARABIC)},
        "v12": {"name": "context advice without the guessing lines", "kind": "full", "replace": [
            ['- Medi often REPEATS Amal\'s previous sentence with small changes (her "you woke up late" -> his "I woke up late"): if his\n  line sounds like hers, expect her words in it.',
             "- Medi often tries to repeat Amal's previous sentence, but he changes, drops or mispronounces her words: write what he\n  actually said, not her words."],
            ['- An answer must fit the question just before it (asked "what time?", he answers with a time).\n', ""],
            ["- Amal's next reaction shows what she heard: if she only fixes one small piece, the rest was right as she heard it.\n", ""]]},
    }


def build(prompt, var):
    """The frozen base prompt of a line with one variable's text put in: `insert` goes before the "Write exactly..."
    block, `pre_answer` before the answer line, `answer` replaces the answer line."""
    if WRITE_MARK not in prompt or not ANSWER_RE.search(prompt):
        raise ValueError("base prompt shape changed")
    for old, new in var.get("replace") or []:          # a sentence of the base prompt reworded or removed
        if prompt.count(old) != 1:
            raise ValueError("base prompt shape changed (replace)")
        prompt = prompt.replace(old, new)
    if var.get("insert"):
        prompt = prompt.replace(WRITE_MARK, var["insert"] + "\n\n" + WRITE_MARK)
    if var.get("pre_answer"):
        prompt = ANSWER_RE.sub(lambda m: var["pre_answer"] + "\n" + m.group(0), prompt)
    if var.get("answer"):
        prompt = ANSWER_RE.sub(lambda m: var["answer"], prompt)
    return prompt


# ---- the three subset variables: which lines, and their prompts (built from the baseline's OUTPUTS, never the key)

V2_PROMPT = """You will hear one short clip: a learner of Levantine Arabic speaking one line in a lesson. He mixes English and
Arabic and makes learner mistakes (wrong words, wrong forms, wrong vowels).
Below are {n} candidate transcripts of this clip, in random order. Which ONE is closest to what he ACTUALLY says in the audio?
Judge by the sound only. A candidate that is better or more correct Arabic is NOT more likely to be right: he often says the wrong word.
{options}
Answer JSON only: {{"choice": "the letter of the closest candidate", "confidence": "high"|"medium"|"low", "why": "one short reason"}}"""

V3_PROMPT = """Two short clips from an online Arabic lesson.
CLIP 1: the learner (Medi), one line. He makes learner mistakes (wrong words, wrong forms).
CLIP 2: his teacher (Amal), a few seconds later. In clip 2 she says: {words}.
For each of those words: does the LEARNER say that same word in CLIP 1, or does he say something different at that place (for example a wrong
word or a wrong form that she then corrects)? Judge by the sound of clip 1 only: a teacher often corrects a learner, so her saying a word
does not mean he said it.
Answer JSON only: {{"words": [{{"word": "her word", "same": true|false, "learner_said": "what he says at that place in clip 1, in Arabic script (or English)"}}], "confidence": "high"|"medium"|"low", "why": "one short reason"}}"""

V6_SPAN_PROMPT = """This clip is ONE line spoken by a learner in an online Arabic lesson. A speech engine wrote the line as: «{target}».
He speaks mostly English in this line, but he may say some words in Arabic (the engine often writes his Arabic as English look-alike words).
Mark every stretch of the clip where he speaks ARABIC. Times are seconds from the start of the clip.
Answer JSON only: {{"spans": [{{"start": 0.0, "end": 0.0, "engine_piece": "the exact part of the engine's line that this stretch covers, copied letter for letter"}}]}} (an empty list when he speaks no Arabic)"""

V6_NOTE = ("NOTE: this audio clip is only a PART of the target line - the stretch the engine wrote as «{piece}». "
           "Write only what he says in this clip.")


# ---- v13, the edge re-cut: lines chosen by AUDIO ALONE (never the key, never a text). His microphone track is noise-gated
# (digital silence between his turns), so a clip that is all speech has no noise floor of its own (the 10-02 clip of
# "e7na biddna" is one): loudness is measured against his own speech level on the whole track instead.
V13 = {"edge_ms": 150,             # the very start / end of the clip that is measured
       "frame_ms": 50,             # loudness frames on the track
       "speech_pct": 95,           # his speech level = this percentile of the track's frame loudness (dB)
       "edge_within_db": 20.0,     # an edge is ON SPEECH when it is within this many dB of his speech level
       "silence_below_db": 30.0,   # a frame is SILENT when it is at least this many dB under his speech level
       "min_silence_s": 0.2,       # the nearest silence = the first run of silent frames this long
       "max_extend_s": 2.0}        # never more than this much extra audio per side


def wav_samples(path):
    """(int16 samples, rate) of a 16-bit mono wav."""
    import wave
    import numpy as np
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("not a 16-bit mono wav: %s" % path)
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2"), w.getframerate()


def rms_db(x):
    """Loudness of a stretch in dB (of the 16-bit sample scale); digital silence = -90."""
    import numpy as np
    if len(x) == 0:
        return -90.0
    e = float(np.mean(np.square(np.asarray(x, dtype=np.float64))))
    return float(10.0 * np.log10(e)) if e > 1e-9 else -90.0


def frames_db(x, sr, ms):
    """Loudness per whole frame of `ms` milliseconds."""
    import numpy as np
    n = int(sr * ms / 1000)
    k = len(x) // n
    out = np.full(k, -90.0)
    step = 4000                                                    # frames per block (keeps the memory small on a whole track)
    for a in range(0, k, step):
        b = min(k, a + step)
        e = np.mean(np.square(np.asarray(x[a * n:b * n], dtype=np.float64).reshape(b - a, n)), axis=1)
        out[a:b] = np.where(e > 1e-9, 10.0 * np.log10(np.maximum(e, 1e-9)), -90.0)
    return out


def speech_level(track, sr, rule=V13):
    import numpy as np
    return float(np.percentile(frames_db(track, sr, rule["frame_ms"]), rule["speech_pct"]))


def edge_speech(clip, sr, level, rule=V13):
    """Which ends of a clip sit on speech: (edges, {"start": dB, "end": dB}); edges is "", "start", "end" or "both"."""
    n = int(sr * rule["edge_ms"] / 1000)
    db = {"start": round(rms_db(clip[:n]), 1), "end": round(rms_db(clip[-n:]), 1)}
    on = [k for k in ("start", "end") if db[k] >= level - rule["edge_within_db"]]
    return ("both" if len(on) == 2 else on[0] if on else ""), db


def extend_to_silence(track, sr, t, direction, level, rule=V13):
    """From time t on the track outward (direction -1 = earlier, +1 = later): how many seconds to add so the cut lands
    in the nearest silence - the first run of `min_silence_s` silent frames, which is taken in whole as the lead-in /
    tail. Returns (seconds, capped): capped when no silence is found within `max_extend_s` (then the cap is the cut)."""
    n = int(sr * rule["frame_ms"] / 1000)
    need = int(round(rule["min_silence_s"] * 1000 / rule["frame_ms"]))
    top = int(round(rule["max_extend_s"] * 1000 / rule["frame_ms"]))
    p0 = int(round(t * sr))
    quiet = []
    for k in range(top):
        a, b = (p0 - (k + 1) * n, p0 - k * n) if direction < 0 else (p0 + k * n, p0 + (k + 1) * n)
        if a < 0 or b > len(track):
            quiet.append(True)                                     # before the start / after the end of the recording: silence
        else:
            quiet.append(rms_db(track[a:b]) < level - rule["silence_below_db"])
        if len(quiet) >= need and all(quiet[-need:]):
            return round(len(quiet) * rule["frame_ms"] / 1000.0, 3), False
    return float(rule["max_extend_s"]), True


def edge_lines(windows, clips, track, sr, rule=V13):
    """THE SELECTOR OF V13 - audio alone. windows = {line_i: (start, end)} of each existing clip on the track clock;
    clips = {line_i: samples of that clip}; track = his whole track. It is given no text, no answer key, no moment:
    a line is chosen when the first or last `edge_ms` of its clip is on speech, and its new window runs outward to the
    nearest silence. Returns ({line_i: {"edge", "edge_db", "old_window", "new_window", "extended_s", "capped"}}, level)."""
    level = speech_level(track, sr, rule)
    out = {}
    for i in sorted(windows):
        edge, db = edge_speech(clips[i], sr, level, rule)
        if not edge:
            continue
        a, b = windows[i]
        ea, ca = extend_to_silence(track, sr, a, -1, level, rule) if edge in ("start", "both") else (0.0, False)
        eb, cb = extend_to_silence(track, sr, b, +1, level, rule) if edge in ("end", "both") else (0.0, False)
        na, nb = max(0.0, a - ea), min(len(track) / float(sr), b + eb)
        out[i] = {"edge": edge, "edge_db": db, "old_window": [round(a, 3), round(b, 3)], "new_window": [round(na, 3), round(nb, 3)],
                  "extended_s": [round(a - na, 3), round(nb - b, 3)], "capped": [ca, cb]}
    return out, round(level, 1)


def v13_rows(date, truth):
    """{line_i: row} of v13. Only each listen line's id, times and clip name are read from truth.json (the same fields
    bench_freeze.make_clips cut the clips from) - never a moment, a slip, a text."""
    d = BC.bench_dir(date)
    off, pad = truth["offsets"]["Medi"], truth.get("pad_s", BC.PAD)
    listen = [(ln["i"], ln["t"], ln["end"], ln["clip"]) for ln in truth["lines"] if ln["listen"]]
    track, sr = wav_samples(os.path.join(d, "clips", "medi-whole.wav"))        # his own track, 16 kHz mono (hashed in the main manifest)
    windows = {i: (max(0.0, t - pad - off), end + pad - off) for i, t, end, _ in listen}
    clips = {i: wav_samples(os.path.join(d, c))[0] for i, _, _, c in listen}
    sel, level = edge_lines(windows, clips, track, sr)
    base = BC.J(os.path.join(d, "prompts.json"))["arms"]["ctx"]
    clip_of = {i: c for i, _, _, c in listen}
    return {str(i): {"clip": "variables/clips/v13-medi-%04d.wav" % i, "old_clip": clip_of[i], "edge": r["edge"], "edge_db": r["edge_db"],
                     "old_window_track_s": r["old_window"], "new_window_track_s": r["new_window"], "extended_s": r["extended_s"], "capped": r["capped"],
                     "speech_level_db": level, "prompt": "prompts.json arms.ctx (unchanged)", "prompt_sha256": BC.sha_text(base[str(i)])}
            for i, r in sel.items()}


def v13_clips(date, P, cut_missing=False):
    """Every re-cut clip is the frozen one: a clip on disk must have its frozen hash; a missing clip (wav files are not in
    git) is cut again from his track when cut_missing, and must then hash the same. Returns the lines that are wrong."""
    import bench_freeze as BF
    d, bad = BC.bench_dir(date), []
    for i, row in P.items():
        out = os.path.join(d, row["clip"])
        if not os.path.exists(out):
            if not cut_missing:
                continue
            BF.cut(BF.track_file(date, "Medi"), row["new_window_track_s"][0], row["new_window_track_s"][1], out)
        if BC.sha_file(out) != row.get("clip_sha256"):
            bad.append(i)
    return bad


def subset_prompts(date, truth, want=None):
    """{vid: {line_i: {...}}} for v2, v3, v6 (and v13 when asked for in `want`: it reads every clip). v2 / v3 come from the
    baseline re-hear piles (rehear/<BASE>.json: lines the 3 baseline runs disagreed on, and lines held because Amal says
    the added word next); v13 comes from the audio alone (edge_lines)."""
    d = BC.bench_dir(date)
    rows = (BC.J(os.path.join(d, "rehear", BASE + ".json")) or {}).get("rows") or []
    lines = {ln["i"]: ln for ln in truth["lines"]}
    out = {"v2": {}, "v3": {}, "v6": {}}
    for r in rows:
        if r["status"] not in ("held", "no-agreement"):
            continue
        cands, seen = [], set()
        for t in [r["engine"]] + ([r["heard"]] if r["status"] == "held" else r["runs"]):
            k = " ".join(BC.tokens(t or ""))
            if t and k not in seen:
                seen.add(k)
                cands.append(t)
        if len(cands) < 2:
            continue
        random.Random("v2-%d" % r["i"]).shuffle(cands)             # the same order in every run; no hint which is the engine's
        opts = {chr(65 + k): c for k, c in enumerate(cands)}
        out["v2"][str(r["i"])] = {"status": r["status"], "options": opts,
                                  "prompt": V2_PROMPT.format(n=len(opts), options="\n".join("%s) %s" % kv for kv in opts.items()))}
    for r in rows:
        if r["status"] != "held":
            continue
        ln = lines[r["i"]]
        hers = [a for a in truth["amal_all"] if ln["t"] < a["t"] <= ln["end"] + AMAL_NEXT_S and set(r["amal_next"]) & set(BC.tokens(a["text"]))]
        if not hers:
            continue
        words = []                                                 # her words as she said them (raw form), in order
        for a in hers:
            for w in re.split(r"[^ء-ْA-Za-z']+", a["text"]):
                if w and BC.norm_token(w) in r["amal_next"] and w not in words:
                    words.append(w)
        out["v3"][str(r["i"])] = {"amal_words": words, "amal_span": [min(a["t"] for a in hers), max(a["end"] for a in hers)],
                                  "amal_clip": "variables/clips/v3-amal-%04d.wav" % r["i"],
                                  "prompt": V3_PROMPT.format(words=", ".join("«%s»" % w for w in words))}
    for ln in truth["lines"]:
        if ln["listen"] and len(ln["engine"].split()) >= LONG_WORDS:
            out["v6"][str(ln["i"])] = {"prompt": V6_SPAN_PROMPT.format(target=ln["engine"])}
    if want and "v13" in want:
        out["v13"] = v13_rows(date, truth)
    return out


def materialise(date, vid, V, base):
    """{line_i: prompt} of a full variable (every listen line)."""
    return {i: build(p, V[vid]) for i, p in base.items()}


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def leak_check(truth, texts):
    """No frozen variable text may hold a correction: a `heard` of an overlay row that the engine did not write, in a
    text that is not a line's own base prompt. Returns the offending (word, where) pairs (empty = clean)."""
    bad = []
    for name, t in texts.items():
        for ln in truth["lines"]:
            for f in ln["fixes"]:
                h = f["heard"]
                if len(h) > 3 and h in t and h not in ln["engine"]:
                    bad.append((h, name))
    return bad


def freeze(date, only=()):
    d, v = BC.bench_dir(date), vdir(date)
    main = BC.J(os.path.join(d, "manifest.json"))
    if BC.sha_file(os.path.join(d, "truth.json")) != main["truth_sha256"]:
        raise SystemExit("truth.json does not match its manifest")
    truth = BC.J(os.path.join(d, "truth.json"))
    base = BC.J(os.path.join(d, "prompts.json"))["arms"]["ctx"]
    man = BC.J(os.path.join(v, "manifest.json")) or {"date": date, "truth_sha256": main["truth_sha256"], "base_prompts_sha256": main["prompts_sha256"], "base_engine": BASE, "vars": {}}
    frozen = BC.J(os.path.join(v, "variables.json")) or {}
    V = variables(date)
    V.update(extra(date))
    todo = [k for k in V if k not in man["vars"] and (not only or k in only)]
    sub = subset_prompts(date, truth, todo) if any(V[k]["kind"] == "subset" for k in todo) else {}
    for vid in todo:
        var = V[vid]
        if var["kind"] == "full":
            texts = {k: var.get(k) or "" for k in ("insert", "pre_answer", "answer")}
            texts["replace"] = " ".join(new for _, new in var.get("replace") or [])
            if vid != "v8" and not var.get("allow_list"):          # v8 / best carry the taught-word list on purpose
                leak = leak_check(truth, texts)
                if leak:
                    raise SystemExit("%s holds a correction: %s" % (vid, leak[:3]))
            P = materialise(date, vid, V, base)
            man["vars"][vid] = {"name": var["name"], "kind": "full", "engine": var.get("engine") or engine_id(vid), "lines": len(P), "prompts_sha256": sha_obj(P), "spec_sha256": sha_obj(var)}
        else:
            P = sub[vid]
            if vid == "v3":
                import bench_freeze as BF
                for i, row in P.items():
                    out = os.path.join(d, row["amal_clip"])
                    if not os.path.exists(out):
                        off = truth["offsets"]["Amal"]
                        BF.cut(BF.track_file(date, "Amal"), row["amal_span"][0] - BC.PAD - off, row["amal_span"][1] + BC.PAD - off, out)
                    row["amal_clip_sha256"] = BC.sha_file(out)
            if vid == "v13":                                       # the new clips, cut from his own track like the first ones
                import bench_freeze as BF
                for i, row in P.items():
                    out = os.path.join(d, row["clip"])
                    BF.cut(BF.track_file(date, "Medi"), row["new_window_track_s"][0], row["new_window_track_s"][1], out)
                    row["clip_sha256"] = BC.sha_file(out)
            BC.W(os.path.join(v, "prompts-%s.json" % vid), P)
            man["vars"][vid] = {"name": var["name"], "kind": "subset", "engine": engine_id(vid), "lines": len(P), "prompts_sha256": sha_obj(P)}
            if vid == "v13":
                man["vars"][vid].update(rule=dict(V13), chosen_by="audio alone (bench_vars.edge_lines): no text, no answer key",
                                        track_wav_sha256=BC.sha_file(os.path.join(d, "clips", "medi-whole.wav")),
                                        source_track_sha256=main["source_tracks"]["Medi"])
        frozen[vid] = var
        man["vars"][vid]["frozen"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        print("frozen %-5s %-45s %3d lines  %s" % (vid, var["name"], man["vars"][vid]["lines"], man["vars"][vid]["prompts_sha256"][:16]))
    BC.W(os.path.join(v, "variables.json"), frozen)
    BC.W(os.path.join(v, "manifest.json"), man)


def load(date, vid):
    """(variable, {line_i: prompt or row}) after re-hashing against the manifest: a prompt changed after its freeze never runs."""
    d, v = BC.bench_dir(date), vdir(date)
    man = BC.J(os.path.join(v, "manifest.json")) or {"vars": {}}
    if vid not in man["vars"]:
        raise SystemExit("%s is not frozen: run `freeze` first" % vid)
    if BC.sha_file(os.path.join(d, "truth.json")) != man["truth_sha256"]:
        raise SystemExit("the answer key changed")
    V = BC.J(os.path.join(v, "variables.json"))
    var = V[vid]
    P = materialise(date, vid, V, BC.J(os.path.join(d, "prompts.json"))["arms"]["ctx"]) if var["kind"] == "full" else BC.J(os.path.join(v, "prompts-%s.json" % vid))
    if sha_obj(P) != man["vars"][vid]["prompts_sha256"]:
        raise SystemExit("%s: prompts do not match the frozen hash" % vid)
    if vid == "v13" and v13_clips(date, P):
        raise SystemExit("v13: a re-cut clip does not match its frozen hash")
    return var, P, man["vars"][vid]["engine"]


def check(date):
    man = BC.J(os.path.join(vdir(date), "manifest.json")) or {"vars": {}}
    for vid in man["vars"]:
        load(date, vid)
    print("variables freeze: OK (%d variables, truth %s)" % (len(man["vars"]), man.get("truth_sha256", "")[:16]))
    return 0


F_MARKED = ('"said_marked": "SAID again, in Arabic script WITH the small vowel marks (harakat: fatha, damma, kasra, shadda, sukun) on every Arabic word, '
            'exactly as HE pronounced them - a learner may say a wrong vowel: write the vowel you hear, not the dictionary form (English words stay English)"')


def extra(date):
    """The best recipe, written after the 10 single variables were scored (2026-10-04): V8 (the taught-word list with
    SAID + MEANT) was the only full variable with the same total (53: +M027 +M040, -M004 -M017), no extra hidden slip and
    fewer changed untouched lines;
    the vowel marks (Medi's decision: always asked for, never scored) go in their own field because V10 showed that
    marks written INTO the scored text cost 4 moments. `bestoa` = the same prompt on OpenAI gpt-audio-1.5.
    `v0` = the baseline's own runs cut to the lines V9 was sent (no call) so V9 is compared like for like."""
    v8 = variables(date)["v8"]
    best = {"name": "best recipe: word list, SAID + MEANT, vowel marks in their own field", "kind": "full", "text_key": "said", "allow_list": True,
            "insert": v8["insert"], "pre_answer": v8["pre_answer"],
            "answer": answer('"said": "SAID, in Arabic script without vowel marks (English words stay English)"', F_MARKED,
                             '"meant": "MEANT, in Arabic script (English words stay English)"',
                             '"arabizi": "SAID in Latin letters with 2 3 5 6 7 8 9 for ء ع خ ط ح غ ص"', F_TAIL)}
    return {"best": best, "bestoa": dict(best, name="best recipe on OpenAI gpt-audio-1.5", engine="openai-audio-best", provider="openai")}


EXTRA = {}


# ------------------------------------------------------------------ pure pieces of the derived rows

def drop_changes(text, engine_line, changes, keep):
    """The listener's line with some of its own changes taken back. changes = [{"engine", "said", ...}]; keep(c) says
    which stay. Every change dropped -> the engine's line; some dropped -> each dropped `said` goes back to its `engine`
    piece; a dropped change that cannot be found in the text, or a changed line with no itemised change, sends the whole
    line back to the engine's text (Codex audit 2026-10-04: an unfiltered change must never score). Returns (text,
    n_dropped, n_whole_line_fallbacks)."""
    changes = [c for c in changes or [] if isinstance(c, dict) and c.get("said") is not None]
    drop = [c for c in changes if not keep(c)]
    if not changes:                                   # words differ but no change was itemised: nothing vouches for it.
        import bench_score as BS                      # A change of alphabet only (his Arabic in English letters) is not a word change.
        same = BC.tokens(text) == BC.tokens(engine_line) or not BS.content_change(engine_line, text)
        return (text, 0, 0) if same else (engine_line, 0, 1)
    if not drop:
        return text, 0, 0
    if len(drop) == len(changes):
        return engine_line, len(drop), 0
    for c in drop:
        said, eng = str(c.get("said") or ""), str(c.get("engine") or "")
        if said and said in text:
            text = text.replace(said, eng, 1)
        else:                                         # cannot be taken back alone: the whole line goes back to the engine
            return engine_line, len(drop), 1
    return re.sub(r"\s+", " ", text).strip(), len(drop), 0


def second_text(text, guesses):
    """V5: the line with each unsure word swapped for its second guess."""
    for g in guesses or []:
        if isinstance(g, dict) and g.get("said") and g.get("second") and str(g["said"]) in text:
            text = text.replace(str(g["said"]), str(g["second"]), 1)
    return text


def merge_span(line, piece, said):
    """V6: the engine's line with one stretch replaced by what the span re-hear wrote. None when the piece is not in the
    line. The cut clip is padded, so the re-hear often repeats the words just before / after the stretch: words of
    `said` that only repeat the line's own words next to the piece are trimmed (pilot 2026-10-04: "form for form for")."""
    piece, said = (piece or "").strip(), (said or "").strip()
    if not piece or piece not in line or not said:
        return None
    k = line.index(piece)
    before, after, words = line[:k].split(), line[k + len(piece):].split(), said.split()
    key = lambda w: "".join(BC.tokens(w))  # noqa: E731
    for n in range(min(len(before), len(words) - 1), 0, -1):          # the longest run of `said`'s first words that ends `before`
        if [key(w) for w in before[-n:]] == [key(w) for w in words[:n]]:
            words = words[n:]
            break
    for n in range(min(len(after), len(words) - 1), 0, -1):
        if [key(w) for w in after[:n]] == [key(w) for w in words[-n:]]:
            words = words[:-n]
            break
    return " ".join(before + words + after)


def v6_text(line, pieces):
    """The line after every placed span of one v6 call."""
    for x in pieces or []:
        m = merge_span(line, x.get("piece"), x.get("said"))
        if m is not None:
            line = m
    return line


def v3_take(raw):
    """V3: the baseline's held change stays only when the learner says every one of her words himself; else the line
    goes back to the engine's text. The step can only take a change back, never add one."""
    w = (raw or {}).get("words")
    return bool(w) and all(isinstance(x, dict) and x.get("same") is True for x in w)


# ------------------------------------------------------------------ the runner

def unreached(err):
    """The engine never answered: this PC's connection, an empty account, the day's request limit or a rate limit (429).
    Such a line is never stored as the engine's miss; it is re-sent when the job is run again."""
    e = str(err or "")
    return bool(e) and (BR.transport(e) or e.startswith(("429", "402")) or "credits are depleted" in e or "per_day" in e.lower() or "perday" in e.lower())


_lock = threading.Lock()


def money_base(date, path, svc="gemini"):
    """Dollars already against the service's cap, without this run file's own."""
    import pipeline_ext as PE
    own = (BC.J(path) or {}).get("cost_usd") or 0.0
    return PE.ledger().get(svc, 0.0) + sum(x["usd"] for x in BR.spent(date, svc).values()) - own, PE.CAPS[svc] * PE.STOP_AT + BR.BENCH_EXTRA.get(svc, 0.0)


def cut_span(src, a, b, out):
    import bench_freeze as BF
    BF.cut(src, a, b, out)


def arabic_lines(truth):
    """The lines a budget-limited job is sent (the rule of the first benchmark's Gemini Pro run): every line with Arabic
    in it and every answer-key / slip line; the short English-only lines are left to the engine's text."""
    keep = {m["i"] for m in truth["moments"]} | {x["i"] for x in truth["slips"]} | {ln["i"] for ln in truth["lines"] if ln["has_arabic"]}
    return {str(i) for i in keep}


def run(date, vid, runs=3, limit=None, only=None):
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    var, P, engine = load(date, vid)
    if only == "arabic":
        keep = arabic_lines(truth)
        P = {i: x for i, x in P.items() if i in keep}
    oa = var.get("provider") == "openai"
    model = "gpt-audio-1.5" if oa else MODEL
    svc = "openai" if oa else "gemini"
    lines = {str(ln["i"]): ln for ln in truth["lines"]}
    base_prompts = BC.J(os.path.join(d, "prompts.json"))["arms"]["ctx"]
    if vid == "v13":                                               # before any call: the frozen clips and the unchanged prompts
        if v13_clips(date, P, cut_missing=True):
            raise SystemExit("v13: a re-cut clip does not match its frozen hash")
        if any(BC.sha_text(base_prompts[i]) != P[i]["prompt_sha256"] for i in P):
            raise SystemExit("v13: a baseline prompt changed since the freeze")
    # One Gemini job at a time by default. Medi 2026-10-04, when the test was slow: "Go as many as possible at once, all
    # if you can" -> ANEES_BENCH_PARALLEL=1: one lock per variable (never two jobs on the same files); every job writes
    # only its own run files and re-reads the others' spend once a minute for the cap.
    par = os.environ.get("ANEES_BENCH_PARALLEL") == "1"
    job_max = float(os.environ["ANEES_BENCH_JOB_MAX"]) / max(1, runs) if os.environ.get("ANEES_BENCH_JOB_MAX") else None   # per run
    lockf = os.path.join(d, ".%s-%s.lock" % (svc, vid) if (par or oa) else ".gemini.lock")
    if par and not oa and os.path.exists(os.path.join(d, ".gemini.lock")):
        raise SystemExit("a one-at-a-time Gemini job is running")
    try:
        os.close(os.open(lockf, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        raise SystemExit("another Gemini job is running (%s)" % lockf)
    os.environ["ANEES_RUNS_DIR"] = os.path.join(d, "runs", engine)
    try:
        for n in range(1, runs + 1):
            p = os.path.join(d, engine, "line-run%d.json" % n)
            rec = BC.J(p) or {"engine": engine, "mode": "line", "run": n, "lines": {}, "cost_usd": 0.0, "seconds": 0.0, "model": model, "variable": vid}
            if only:
                rec["lines_sent_rule"] = only
                rec["lines"] = {i: o for i, o in rec["lines"].items() if i in P}     # a pilot's lines outside the rule are not scored
            if rec.get("complete") and not any(unreached(x.get("error")) for x in rec["lines"].values()):
                continue
            rec["lines"] = {i: o for i, o in rec["lines"].items() if not unreached(o.get("error"))}
            rec["complete"] = False
            base_run = (BC.J(os.path.join(d, BASE, "line-run%d.json" % n)) or {}).get("lines") if var["kind"] == "subset" else None
            if var["kind"] == "subset" and not base_run:
                raise SystemExit("no baseline run %d" % n)
            spent0, limit_usd = money_base(date, p, svc)
            money = {"base": spent0, "t": time.time(), "own0": rec["cost_usd"]}
            todo = [i for i in P if i not in rec["lines"]]
            if limit:
                todo = todo[:limit]
            stop, t0, hold = [], time.time(), [0.0]
            est = 0.09 if (var.get("cfg") or vid == "v6") else 0.03      # 3 tries of a capped thinking call / up to 4 calls of v6

            def pay(usd, secs):
                if usd:
                    BR.paid(date, engine, "line", n, model, usd, secs, provider="openai" if oa else "google")

            def g(path, prompt, **kw):
                if oa:
                    kw.pop("cfg_extra", None)
                    out = BR.tried(lambda: BR.openai_audio(model, path, prompt))
                else:
                    out = BR.tried(lambda: BR.gemini(MODEL, path, prompt, temp=1, **kw))
                pay(out.get("usd", 0.0), BR.wav_seconds(path))
                return out

            def one(i):
                if stop:
                    return i, None
                with _lock:                                        # the call's worst case is reserved before it is sent
                    if par and time.time() - money["t"] > 60:      # the other jobs' run files, re-read once a minute
                        BC.W(p, rec)
                        money.update(base=money_base(date, p, svc)[0], t=time.time())
                    # Codex audit 2: parallel jobs see each other's spend up to a minute late, so near the cap a job may
                    # also be given its own dollar ceiling (ANEES_BENCH_JOB_MAX; the ceilings must add up to the room left).
                    if job_max is not None and rec["cost_usd"] - money["own0"] + hold[0] + est > job_max:
                        stop.append(1)
                        return i, None
                    if money["base"] + rec["cost_usd"] + hold[0] + est * (8 if par else 1) > limit_usd:
                        stop.append(1)
                        return i, None
                    hold[0] += est
                clip = os.path.join(d, lines[i]["clip"])
                if var["kind"] == "full":
                    out = g(clip, P[i], cfg_extra=var.get("cfg"))
                    if var.get("text_key") and isinstance(out.get("raw"), dict):
                        out["text"] = out["raw"].get(var["text_key"]) or ""
                elif vid == "v2":
                    out = g(clip, P[i]["prompt"])
                    ch = str((out.get("raw") or {}).get("choice") or "").strip().upper()[:1] if isinstance(out.get("raw"), dict) else ""
                    out["text"] = P[i]["options"].get(ch) or (base_run.get(i) or {}).get("text") or lines[i]["engine"]
                    out["alt"], out["chose"] = "", ch if ch in P[i]["options"] else None
                elif vid == "v3":
                    out = g(clip, P[i]["prompt"], more_audio=[os.path.join(d, P[i]["amal_clip"])])
                    take = v3_take(out.get("raw") if isinstance(out.get("raw"), dict) else None)
                    b = base_run.get(i) or {"text": lines[i]["engine"]}     # this run's own baseline answer for the line
                    keep = take or bool(out.get("error"))                   # a failed check changes nothing
                    out["text"], out["alt"], out["took"] = (b.get("text") or "") if keep else lines[i]["engine"], (b.get("alt") or "") if keep else "", take
                elif vid == "v13":                                 # the unchanged baseline prompt, the re-cut clip
                    out = g(os.path.join(d, P[i]["clip"]), base_prompts[i])
                    out["recut"] = P[i]["edge"]
                else:                                              # v6: mark the Arabic stretches, then re-hear each one alone
                    out = g(clip, P[i]["prompt"])
                    spans = (out.get("raw") or {}).get("spans") if isinstance(out.get("raw"), dict) else None
                    text, pieces, usd = lines[i]["engine"], [], out.get("usd", 0.0)
                    for k, s in enumerate((spans or [])[:MAX_SPANS]):
                        try:
                            a, b = float(s["start"]) - SPAN_PAD, float(s["end"]) + SPAN_PAD
                        except Exception:  # noqa: BLE001
                            continue
                        piece = str(s.get("engine_piece") or "")
                        if b - a < 0.5 or not piece:
                            continue
                        sp = os.path.join(d, "variables", "clips", "v6-%s-%d-run%d.wav" % (i, k, n))
                        cut_span(clip, max(0.0, a), b, sp)
                        o2 = g(sp, build(base_prompts[i], {"pre_answer": V6_NOTE.format(piece=piece)}))
                        usd += o2.get("usd", 0.0)
                        m = merge_span(text, piece, o2.get("text"))
                        pieces.append({"span": [s.get("start"), s.get("end")], "piece": piece, "said": o2.get("text"), "placed": m is not None, "error": o2.get("error")})
                        if m is not None:
                            text = m
                    err = out.get("error")
                    out = {"text": text if not err else "", "alt": "", "raw": {"spans": spans, "pieces": pieces}, "usd": usd, "tokens": out.get("tokens")}
                    if err:
                        out["error"] = err
                with _lock:
                    hold[0] -= est
                if unreached(out.get("error")):                    # the account / the day's limit / a rate limit: stop the job; the
                    stop.append(2)                                 # line is not stored, so it is never the engine's miss
                    with _lock:
                        rec["cost_usd"] = round(rec["cost_usd"] + (out.get("usd") or 0.0), 6)
                    return i, None
                return i, out

            done = 0
            try:
                with ThreadPoolExecutor(6 if oa else 8) as ex:
                    for i, out in ex.map(one, todo):
                        if out is None:
                            continue
                        with _lock:
                            rec["lines"][i] = out
                            rec["cost_usd"] = round(rec["cost_usd"] + (out.get("usd") or 0.0), 6)
                        done += 1
                        if done % 40 == 0:
                            rec["seconds"] += time.time() - t0
                            t0 = time.time()
                            with _lock:                            # never two writers on the run file (Codex audit 2)
                                BC.W(p, rec)
                            print(engine, "run", n, len(rec["lines"]), "/", len(P), "$%.3f" % rec["cost_usd"], flush=True)
            finally:
                rec["seconds"] += time.time() - t0
                BC.W(p, rec)
            if stop:
                raise SystemExit(("the provider account / daily limit" if 2 in stop else "budget cap (PR-10) reached") + " for %s: stopped at %d lines" % (engine, len(rec["lines"])))
            if limit:
                print("%s run %d: pilot of %d lines, $%.3f" % (engine, n, len(rec["lines"]), rec["cost_usd"]), flush=True)
                continue
            if not all(i in rec["lines"] for i in P) or any(unreached(x.get("error")) for x in rec["lines"].values()):
                BC.W(p, rec)
                raise SystemExit("%s run %d: lines never reached the engine - run the job again" % (engine, n))
            if vid == "v6":                                        # one merge rule for every line (also the pilot's)
                for i in P:
                    o = rec["lines"][i]
                    if not o.get("error"):
                        o["text"] = v6_text(lines[i]["engine"], (o.get("raw") or {}).get("pieces"))
            if var["kind"] == "subset":                            # baseline + this step: every other line is the baseline's run n
                rec["called"] = sorted(P, key=int)
                for i, o in base_run.items():
                    if i not in rec["lines"]:
                        rec["lines"][i] = {"text": o.get("text") or "", "alt": o.get("alt") or "", "error": o.get("error"), "from": BASE} if o.get("error") else {"text": o.get("text") or "", "alt": o.get("alt") or "", "from": BASE}
            rec["complete"] = True
            BC.W(p, rec)
            errs = sum(1 for x in rec["lines"].values() if x.get("error"))
            print("%s run %d: %d lines, %d errors, %.0f s, $%.3f" % (engine, n, len(rec["lines"]), errs, rec["seconds"], rec["cost_usd"]), flush=True)
    finally:
        if os.path.exists(lockf):
            os.unlink(lockf)


DERIVED = {"v1h": ("v1", "only the changes Gemini says it HEARD", lambda c: str(c.get("evidence") or "").lower() == "heard"),
           "v4h": ("v4", "only the changes at HIGH confidence", lambda c: str(c.get("confidence") or "").lower() == "high")}


def derive(date):
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    eng = {str(ln["i"]): ln["engine"] for ln in truth["lines"]}
    keep_i = arabic_lines(truth)
    for n in (1, 2, 3):                               # v0: the baseline on the lines V9 was sent
        r = BC.J(os.path.join(d, BASE, "line-run%d.json" % n))
        v9 = BC.J(os.path.join(d, engine_id("v9"), "line-run%d.json" % n)) or {}
        if r and v9.get("lines_sent_rule") == "arabic":
            BC.W(os.path.join(d, engine_id("v0"), "line-run%d.json" % n), {"engine": engine_id("v0"), "mode": "line", "run": n, "cost_usd": 0.0, "seconds": 0.0, "model": MODEL,
                 "variable": "v0", "derived_from": BASE, "rule": "the baseline's run, only the lines V9 was sent", "complete": True,
                 "lines": {i: {k: v for k, v in o.items() if k in ("text", "alt", "error")} for i, o in r["lines"].items() if i in keep_i}})
    for vid, (src, name, keep) in DERIVED.items():
        for n in (1, 2, 3):
            r = BC.J(os.path.join(d, engine_id(src), "line-run%d.json" % n))
            if not r or not r.get("complete"):
                continue
            out = {"engine": engine_id(vid), "mode": "line", "run": n, "lines": {}, "cost_usd": 0.0, "seconds": 0.0, "model": MODEL, "variable": vid,
                   "derived_from": engine_id(src), "rule": name, "complete": True}
            st = collections.Counter()
            for i, o in r["lines"].items():
                raw = o.get("raw") if isinstance(o.get("raw"), dict) else {}
                text, nd, miss = drop_changes(o.get("text") or "", eng[i], raw.get("changes"), keep)
                st["dropped"] += nd
                st["unplaced"] += miss
                st["lines_changed_back"] += bool(nd)
                row = {"text": text, "alt": "" if (nd or miss) else (o.get("alt") or "")}     # a line changed back loses its Arabizi echo too
                if o.get("error"):
                    row["error"] = o["error"]
                out["lines"][i] = row
            out["stats"] = dict(st)
            BC.W(os.path.join(d, engine_id(vid), "line-run%d.json" % n), out)
            print(engine_id(vid), "run", n, dict(st))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    lim = None
    if "--limit" in argv:
        k = argv.index("--limit")
        lim = int(argv[k + 1])
        del argv[k:k + 2]
    only = None
    if "--only" in argv:
        k = argv.index("--only")
        only = argv[k + 1]
        del argv[k:k + 2]
    date, cmd = argv[0], argv[1]
    if cmd == "freeze":
        freeze(date, argv[2:])
    elif cmd == "check":
        sys.exit(check(date))
    elif cmd == "run":
        run(date, argv[2], int(argv[3]) if len(argv) > 3 else 3, lim, only)
    elif cmd == "derive":
        derive(date)
