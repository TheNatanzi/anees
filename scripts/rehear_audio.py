# -*- coding: utf-8 -*-
"""Audio for the Gemini re-hear of a lesson (TR-22 / PR-18; overnight backfill spec 2026-10-04): which recording holds
each speaker at a lesson time, clips cut from it, and the cut of a track into segments by SILENCE ALONE.

Nothing here reads a transcript, an answer key or a correction. Nothing calls a network.

    lesson clock = the recording clock of the meeting (docs/data/lessons/<date>.json "clock"). Each speaker's own track
    starts `start.relative` seconds into it (tracks/tracks.json); a speaker who re-joined has two files. A lesson with no
    per-speaker tracks (08-25, 09-04, 09-18) has only the mixed recording: source "mix".

    python scripts/rehear_audio.py 2026-10-02            # the sources and the silence cut, printed
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_vars as BV  # noqa: E402  (wav_samples, frames_db, rms_db: the loudness code of the edge re-cut)

PAD = BC.PAD
# The silence cut. Every number was chosen from the AUDIO (loudness per 50 ms frame), never from a transcript.
SEG = {"frame_ms": 50,
       "speech_pct": 95,          # the speaker's speech level = this percentile of the frame loudness of the track (dB)
       "silence_below_db": 30.0,  # a frame is silent when it is this far under the speech level ...
       "floor_above_db": 8.0,     # ... or, on a track that is not noise-gated, within this many dB of its noise floor
       "floor_pct": 20,           # the noise floor = this percentile of the frames that are not digital silence
       "split_silence_s": 0.7,    # a silence this long ends a segment
       "min_speech_s": 0.15,      # a segment with less speech than this is a click, not a turn
       "pad_s": 0.3,              # audio kept before / after the speech (never past the middle of the gap to the neighbour)
       "max_len_s": 20.0,         # a longer segment is cut again at its longest inner silence ...
       "inner_silence_s": 0.25}   # ... which must be at least this long


def rdir(date):
    return os.path.join(BC.REPO, "data", "lesson-work", "rehear", date)


def cut(src, a, b, out):
    """[a, b] seconds of src -> 16 kHz mono 16-bit wav (bit-exact: the same input always gives the same bytes)."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % max(0.0, a), "-to", "%.3f" % b, "-i", src,
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", out], check=True)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def mix_file(date):
    """The lesson page's own recording (both speakers), on the lesson clock."""
    a = os.path.join(BC.REPO, "docs", "lessons", date, "audio")
    for name in ("lesson.mp3",):
        if os.path.exists(os.path.join(a, name)):
            return os.path.join(a, name)
    return None


def sources(date):
    """{"Medi": [{"file", "start", "dur"}], "Amal": [...]} - each speaker's own recordings with their start on the lesson
    clock, earliest first; {} for a speaker with no own track (then the mix is the only source).
    tracks.json is the meeting recorder's own manifest; a file it names is looked up by its base name in the raw archive
    (two manifests carry the path of the PC folder they were written in). A stitched copy is never used (its clock is not
    the recorder's)."""
    tr = os.path.join(BC.RAW, date, "tracks")
    out = {"Medi": [], "Amal": []}
    man = BC.J(os.path.join(tr, "tracks.json"))
    if man:
        for t in man.get("tracks") or []:
            who = "Medi" if str(t.get("participant", "")).startswith("Medi") else "Amal" if str(t.get("participant", "")).startswith("Amal") else None
            name = os.path.basename(str(t.get("file") or t.get("filename") or "").replace("\\", "/"))
            p = os.path.join(tr, name)
            if who and name and os.path.exists(p) and "stitched" not in name:
                out[who].append({"file": p, "start": float(t["start"]["relative"]), "dur": float(t.get("duration_s") or duration(p))})
    for who in out:
        out[who].sort(key=lambda s: s["start"])
    return {k: v for k, v in out.items() if v}


def source_at(srcs, who, a, b):
    """The speaker's own recording that holds ALL of lesson time [a, b], or None (a window that crosses a re-join is
    not on one file: it is cut from the mix and labelled so)."""
    for s in srcs.get(who) or []:
        if s["start"] - 0.05 <= a and b <= s["start"] + s["dur"] + 0.05:
            return s
    return None


def clip(date, who, a, b, out, srcs=None):
    """Lesson time [a, b] of one speaker -> wav. Returns "own" (the speaker's microphone) or "mix" (both speakers: the
    lesson has no own track there)."""
    srcs = sources(date) if srcs is None else srcs
    s = source_at(srcs, who, a, b)
    if s:
        cut(s["file"], a - s["start"], b - s["start"], out)
        return "own"
    m = mix_file(date)
    if not m:
        raise SystemExit("%s: no recording holds %s at %.1f s" % (date, who, a))
    cut(m, a, b, out)
    return "mix"


def whole_wav(date, who, k, s):
    """One whole track as 16 kHz mono wav (kept beside the lesson's re-hear files; *.wav is git-ignored)."""
    out = os.path.join(rdir(date), "audio", "%s-%d.wav" % (who.lower(), k))
    if not os.path.exists(out):
        cut(s["file"], 0.0, s["dur"] + 1.0, out)
    return out


# ------------------------------------------------------------------ the silence cut (audio alone)

def silent_frames(x, sr, rule=SEG):
    """(per-frame silent yes/no, speech level dB, silence threshold dB)."""
    import numpy as np
    db = BV.frames_db(x, sr, rule["frame_ms"])
    level = float(np.percentile(db, rule["speech_pct"]))
    live = db[db > -89.0]
    floor = float(np.percentile(live, rule["floor_pct"])) if len(live) else -90.0
    thr = max(level - rule["silence_below_db"], min(floor + rule["floor_above_db"], level - 12.0))
    return db < thr, level, thr


def _runs(flags):
    """[(first frame, one past the last)] of each run of True."""
    out, a = [], None
    for k, f in enumerate(flags):
        if f and a is None:
            a = k
        elif not f and a is not None:
            out.append((a, k))
            a = None
    if a is not None:
        out.append((a, len(flags)))
    return out


def _split_long(a, b, quiet, rule, fs):
    """A too-long stretch of speech frames [a, b) cut at its longest inner silence, again and again."""
    if (b - a) * fs <= rule["max_len_s"]:
        return [(a, b)]
    inner = [(q2 - q1, q1, q2) for q1, q2 in _runs(quiet[a:b]) if q1 > 0 and q2 < b - a and (q2 - q1) * fs >= rule["inner_silence_s"]]
    if not inner:
        return [(a, b)]
    # the longest silence that leaves at least a quarter of the stretch on each side; else simply the longest
    mid = [x for x in inner if (b - a) * 0.25 <= (x[1] + x[2]) / 2.0 <= (b - a) * 0.75] or inner
    _, q1, q2 = max(mid)
    return _split_long(a, a + q1, quiet, rule, fs) + _split_long(a + q2, b, quiet, rule, fs)


def segments(x, sr, rule=SEG):
    """One track -> [{"a", "b", "speech_a", "speech_b", "speech_s"}] in seconds on the TRACK clock: stretches of speech
    separated by `split_silence_s` of silence, padded by `pad_s`, clicks dropped, long stretches cut at an inner silence."""
    import numpy as np
    quiet, level, thr = silent_frames(x, sr, rule)
    fs = rule["frame_ms"] / 1000.0
    need = int(round(rule["split_silence_s"] / fs))
    speech = _runs(~quiet)
    merged = []
    for a, b in speech:                                       # speech runs with less than the split silence between them are one turn
        if merged and a - merged[-1][1] < need:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    pieces = []
    for a, b in merged:
        if int(np.sum(~quiet[a:b])) * fs < rule["min_speech_s"]:
            continue
        pieces += _split_long(a, b, quiet, rule, fs)
    out, end = [], len(x) / float(sr)
    for k, (a, b) in enumerate(pieces):
        sa, sb = a * fs, b * fs
        lo = max(0.0, sa - rule["pad_s"]) if k == 0 else max((pieces[k - 1][1] * fs + sa) / 2.0, sa - rule["pad_s"])
        hi = min(end, sb + rule["pad_s"]) if k == len(pieces) - 1 else min((sb + pieces[k + 1][0] * fs) / 2.0, sb + rule["pad_s"])
        out.append({"a": round(lo, 3), "b": round(hi, 3), "speech_a": round(sa, 3), "speech_b": round(sb, 3),
                    "speech_s": round(int(np.sum(~quiet[a:b])) * fs, 2)})
    return out, round(level, 1), round(thr, 1)


def voiced_times(x, sr, a, b, n, rule=SEG, quiet=None):
    """n word times inside track stretch [a, b]: the words are laid over the VOICED frames of the stretch in order, each
    word weighted the same - a model that writes text without times gets its words placed by the audio alone.
    Returns [(start, end)] * n."""
    fs = rule["frame_ms"] / 1000.0
    if quiet is None:
        quiet = silent_frames(x, sr, rule)[0]
    fa, fb = int(a / fs), min(len(quiet), int(b / fs) + 1)
    voiced = [k for k in range(fa, fb) if not quiet[k]] or list(range(fa, max(fa + 1, fb)))
    out = []
    for w in range(n):
        i1 = voiced[min(len(voiced) - 1, int(w * len(voiced) / float(n)))]
        i2 = voiced[min(len(voiced) - 1, max(0, int((w + 1) * len(voiced) / float(n)) - 1))]
        out.append((round(i1 * fs, 3), round((i2 + 1) * fs, 3)))
    return out


def lesson_segments(date, rule=SEG):
    """Every speaker's tracks cut by silence, on the LESSON clock: [{"id", "who", "k" (track), "a", "b", "speech_a",
    "speech_b", "speech_s", "track_a", "track_b"}], by start. Lessons with no own tracks return [] (the mix cannot be
    cut per speaker by silence)."""
    srcs = sources(date)
    out, meta = [], {}
    for who in ("Medi", "Amal"):
        for k, s in enumerate(srcs.get(who) or []):
            x, sr = BV.wav_samples(whole_wav(date, who, k, s))
            segs, level, thr = segments(x, sr, rule)
            meta["%s-%d" % (who, k)] = {"file": os.path.basename(s["file"]), "start": s["start"], "dur": s["dur"], "speech_level_db": level, "silence_below_db": thr, "segments": len(segs)}
            for g in segs:
                out.append({"who": who, "k": k, "a": round(g["a"] + s["start"], 3), "b": round(g["b"] + s["start"], 3),
                            "speech_a": round(g["speech_a"] + s["start"], 3), "speech_b": round(g["speech_b"] + s["start"], 3),
                            "speech_s": g["speech_s"], "track_a": g["a"], "track_b": g["b"]})
    out.sort(key=lambda g: (g["speech_a"], g["who"]))
    n = {"Medi": 0, "Amal": 0}
    for g in out:
        g["id"] = "%s%04d" % (g["who"][0], n[g["who"]])
        n[g["who"]] += 1
    return out, meta


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    date = sys.argv[1]
    srcs = sources(date)
    for who, ss in srcs.items():
        for s in ss:
            print("%-5s %-45s starts %8.2f s, %7.1f s long" % (who, os.path.basename(s["file"]), s["start"], s["dur"]))
    print("mix:", mix_file(date))
    segs, meta = lesson_segments(date)
    print(json.dumps(meta, indent=1))
    import statistics
    for who in ("Medi", "Amal"):
        L = [g["b"] - g["a"] for g in segs if g["who"] == who]
        if L:
            print("%s: %d segments, median %.1f s, longest %.1f s, %d over 20 s, speech %.0f s" % (who, len(L), statistics.median(L), max(L), sum(1 for v in L if v > 20.5), sum(g["speech_s"] for g in segs if g["who"] == who)))
