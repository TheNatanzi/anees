# -*- coding: utf-8 -*-
"""Source audio + transcript audit, per lesson and per person (engineering audit 2026-09-29, area 3).

For every lesson on the Lessons page it answers, from the RAW recordings (C:\\dev\\anees\\data\\lessons\\<date>, read-only):
  audio        is each person's audio present for the whole lesson? (recording-bot tracks: tracks.json offsets; a track
               file that was overwritten or never saved = a lost segment; mixed lessons = one recording)
  speech       when does each person actually talk? (energy on their OWN track; mixed lessons: not separable)
  holes        speech on a person's own track with no transcript line of that person nearby = untranscribed speech
  swap         are the speaker labels right?  track lessons: for each labelled line, is the labelled person's own track
               the loud one?  mixed lessons: the Meet recording's named caption track (English captions, 4-s blocks)
               where it exists, else voice pitch (Medi low, Amal high) - never the method that made the labels
  asr          was the speech recognition reviewed? (seconds compared with a second model; seconds a person listened)

    python scripts/source_audit.py              # all lessons -> data/accuracy/source-audit.json + a table
    python scripts/source_audit.py 2026-09-28   # one lesson (merged into the same file)

Output is a source layer for scripts/accuracy_gates.py (coverage reasons + unscoreable intervals). It never edits a
transcript (RULES.md S2) or a raw file. Offline, no paid calls.
"""
import datetime as dt, json, os, re, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RAW = os.environ.get("ANEES_RAW", r"C:\dev\anees\data\lessons")
MEET = os.environ.get("ANEES_MEET", r"G:\My Drive\Google Meet")
OUT = os.path.join(REPO, "data", "accuracy", "source-audit.json")
SR = 8000
HOP = 0.1                      # energy frame, seconds
PEOPLE = ("Medi", "Amal")
MIXED_AUDIO = {"2026-08-25": r"C:\dev\anees\data\aug25\audio\aug25.mp3"}
# cut-offs (stated, not tuned per lesson)
HOLE_MIN_S = 20.0              # untranscribed speech must add up to >= 20 s inside a 120-s window to be reported
HOLE_WINDOW_S = 120.0
TURN_PAD_S = 2.0               # a speech frame within 2 s of one of the person's own transcript lines counts as transcribed
LOUD_DB = 6.0                  # swap check: the labelled person's track must be >= 6 dB louder than the other's


def J(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def person(name):
    n = (name or "").lower()
    return "Medi" if n.startswith("medi") else "Amal" if n.startswith("amal") else None


def ffprobe_dur(p):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                           capture_output=True, text=True, timeout=120)
        return float(r.stdout.strip())
    except Exception:
        return None


def decode(p, sr=SR, stream=None):
    cmd = ["ffmpeg", "-v", "error", "-i", p]
    if stream:
        cmd += ["-map", stream]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=900)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def frame_db(x, sr=SR, hop=HOP):
    n = int(sr * hop)
    k = len(x) // n
    if k == 0:
        return np.zeros(0)
    e = np.sqrt(np.mean(x[: k * n].reshape(k, n) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(e)


# ---------------------------------------------------------------------------------------------------- sources
def segments(date, raw=RAW):
    """Per person: the recording segments on the lesson clock, and whether the file for each one still exists.
    Recall's tracks.json lists every segment; older lessons saved several segments under ONE file name, so only the
    segment whose length matches the file survived (the others are 'lost' unless tracks/recovered/ holds them)."""
    d = os.path.join(raw, date)
    tj = os.path.join(d, "tracks", "tracks.json")
    if not os.path.exists(tj):
        return None
    T = J(tj)["tracks"]
    rec = {}
    rj = os.path.join(d, "tracks", "recovered", "recovery.json")
    if os.path.exists(rj):
        for r in J(rj).get("recovered", []):
            rec[(person(r["participant"]), round(float(r["start"]["relative"]), 1))] = r["file"]
    out = {p: [] for p in PEOPLE}
    durs = {}
    for t in T:
        p = person(t["participant"])
        if p not in PEOPLE:
            continue
        f = t["file"]
        if not os.path.exists(f):
            f = os.path.join(d, "tracks", os.path.basename(f))
        if f not in durs:
            durs[f] = ffprobe_dur(f) if os.path.exists(f) else None
        off, dur = float(t["start"]["relative"]), float(t["duration_s"])
        status = "ok"
        if durs[f] is None:
            status = "lost"
        elif abs(durs[f] - dur) > 3.0:
            status = "lost"
        if status == "lost" and (p, round(off, 1)) in rec:
            f, status = rec[(p, round(off, 1))], "recovered"
        out[p].append({"file": f, "offset": round(off, 3), "duration_s": round(dur, 1), "status": status})
    st = os.path.join(d, "tracks", "stitched.json")
    if os.path.exists(st):                       # 09-14: Medi's two files concatenated on the true timeline
        S = J(st)
        p = person(S["participant"])
        f = os.path.join(d, "tracks", os.path.basename(S["stitched"]["file"]))
        if os.path.exists(f):
            out[p] = [{"file": f, "offset": round(float(S["stitched"]["start"]["relative"]), 3),
                       "duration_s": round(float(S["stitched"]["duration_s"]), 1), "status": "ok", "stitched": True,
                       "gap": [round(float(S["segments"][0]["start"]["relative"]) + float(S["segments"][0]["duration_s"]), 1),
                               round(float(S["segments"][1]["start"]["relative"]), 1)]}]
    return out


def meet_file(date, meet=MEET):
    if not os.path.isdir(meet):
        return None
    y, m, dd = date.split("-")
    for f in os.listdir(meet):
        if f" {y} {m} {dd} " in f:
            sub = os.path.join(meet, f)
            for g in os.listdir(sub):
                if g.endswith(")") and "Chat" not in g and "Notes" not in g:
                    return os.path.join(sub, g)
    return None


# ---------------------------------------------------------------------------------------------------- analysis
def speech_frames(db):
    """Frames where this person talks on their own track: above the track's noise floor by 15 dB and above -50 dBFS."""
    if not len(db):
        return np.zeros(0, bool)
    floor = np.percentile(db, 20)
    return (db > max(floor + 15.0, -50.0))


def intervals(mask, t0=0.0, hop=HOP, join=1.5, min_len=0.5):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        if not v and start is not None:
            out.append([t0 + start * hop, t0 + i * hop])
            start = None
    if start is not None:
        out.append([t0 + start * hop, t0 + len(mask) * hop])
    merged = []
    for a, b in out:
        if merged and a - merged[-1][1] < join:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [[round(a, 1), round(b, 1)] for a, b in merged if b - a >= min_len]


def turn_mask(turns, who, n, hop=HOP, pad=TURN_PAD_S):
    m = np.zeros(n, bool)
    for t in turns:
        if t.get("who") != who:
            continue
        a, b = t["t"], max(t.get("end") or t["t"], t["t"] + 1.0)
        m[max(0, int((a - pad) / hop)): min(n, int((b + pad) / hop) + 1)] = True
    return m


def holes(untx, hop=HOP, window=HOLE_WINDOW_S, min_s=HOLE_MIN_S):
    """Clusters of untranscribed speech: a sliding 120-s window holding >= 20 s of it. Returns [[from, to, speech_s]]."""
    idx = np.flatnonzero(untx)
    if not len(idx):
        return []
    w = int(window / hop)
    csum = np.concatenate([[0], np.cumsum(untx)])
    hot = np.zeros(len(untx), bool)
    for i in idx:
        lo, hi = max(0, i - w // 2), min(len(untx), i + w // 2)
        if (csum[hi] - csum[lo]) * hop >= min_s:
            hot[i] = True
    out = []
    for a, b in intervals(hot, hop=hop, join=window / 2, min_len=0):
        s = float(untx[int(a / hop): int(b / hop) + 1].sum() * hop)
        if s >= min_s:
            out.append([a, b, round(s, 1)])
    return out


def captions(path):
    """Meet caption track -> [(start, end, speaker)] (English only; the speaker name is the block label)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:s:0", "-f", "srt", "-"], capture_output=True, timeout=300)
    txt = r.stdout.decode("utf-8", "replace")
    out = []
    for block in re.split(r"\n\s*\n", txt):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+) --> (\d+):(\d+):(\d+)[,.](\d+)\s*\n(.*)", block, re.S)
        if not m:
            continue
        g = [int(x) for x in m.groups()[:8]]
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        b = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        body = m.group(9).strip()
        sp = re.match(r"^\(([^)\n]{2,40})\)", body) or re.match(r"^([^:\n]{2,40}):", body)
        who = person(sp.group(1)) if sp else None
        if who:
            out.append((a, b, who))
    return out


def pitch_label(x, sr=SR):
    """Median F0 of a line: < 155 Hz Medi, > 180 Hz Amal, else None (the validated 09-04 cut-offs)."""
    import librosa
    if len(x) < sr * 0.6:
        return None, None
    f0 = librosa.yin(x, fmin=70, fmax=400, sr=sr, frame_length=512)
    rms = librosa.feature.rms(y=x, frame_length=512, hop_length=128)[0][: len(f0)]
    keep = f0[(rms > np.percentile(rms, 60))] if len(rms) == len(f0) else f0
    keep = keep[(keep > 75) & (keep < 380)]
    if len(keep) < 5:
        return None, None
    med = float(np.median(keep))
    return ("Medi" if med < 155 else "Amal" if med > 180 else None), round(med, 1)


def audit_lesson(date, lesson, detail, wb_checks=None, evidence_dates=None, raw=RAW, meet=MEET):
    turns = [t for t in detail.get("turns", []) if t.get("who") in PEOPLE and t.get("t") is not None]
    lesson_s = float((lesson.get("duration_min") or 0) * 60) or max([t.get("end") or t["t"] for t in turns] + [0])
    n = int(lesson_s / HOP) + 1
    src = lesson.get("source") or {}
    res = {"date": date, "lesson_s": round(lesson_s, 1), "attribution": src.get("attribution"), "timing": src.get("timing"),
           "people": {}, "flags": []}
    segs = segments(date, raw)
    per_track = segs is not None and src.get("attribution") == "per-speaker-tracks"
    res["recording"] = "per-person tracks" if per_track else ("one mixed recording" + (" (per-person tracks also on disk, not used for the transcript)" if segs else ""))
    tracks_db = {}
    if segs:
        for p in PEOPLE:
            db = np.full(n, -120.0)
            have = np.zeros(n, bool)
            info = []
            for s in segs[p]:
                a = int(s["offset"] / HOP)
                b = min(n, int((s["offset"] + s["duration_s"]) / HOP))
                if s["status"] != "lost" and os.path.exists(s["file"]):
                    fd = frame_db(decode(s["file"]))
                    k = min(len(fd), n - a)
                    if k > 0:
                        db[a: a + k] = np.maximum(db[a: a + k], fd[:k])
                        have[a: a + k] = True
                    if s.get("gap"):
                        have[int(s["gap"][0] / HOP): int(s["gap"][1] / HOP)] = False
                info.append({k2: s[k2] for k2 in ("offset", "duration_s", "status")} | {"file": os.path.basename(s["file"])})
            tracks_db[p] = (db, have)
            no_audio = intervals(~have, hop=HOP, join=0.5, min_len=5.0)
            lost = [[s["offset"], round(s["offset"] + s["duration_s"], 1)] for s in segs[p] if s["status"] == "lost"]
            res["people"][p] = {"segments": info, "audio_s": round(have.sum() * HOP, 1),
                                "audio_pct": round(100 * have.sum() / n, 1), "no_audio": no_audio, "lost_segments": lost}
    for p in PEOPLE:
        P = res["people"].setdefault(p, {})
        tm = turn_mask(turns, p, n)
        P["lines"] = sum(1 for t in turns if t["who"] == p)
        P["first_line"] = min([t["t"] for t in turns if t["who"] == p], default=None)
        if per_track and p in tracks_db:
            db, have = tracks_db[p]
            sp = speech_frames(db[have]) if have.any() else np.zeros(0, bool)
            speech = np.zeros(n, bool)
            speech[np.flatnonzero(have)] = sp
            untx = speech & ~tm
            P["speech_s"] = round(speech.sum() * HOP, 1)
            P["speech_transcribed_pct"] = round(100 * (speech & tm).sum() / speech.sum(), 1) if speech.sum() else None
            P["untranscribed_s"] = round(untx.sum() * HOP, 1)
            P["holes"] = holes(untx)
            P["empty_audio"] = intervals(have & ~(np.convolve(speech, np.ones(int(300 / HOP)), "same") > 0), hop=HOP, join=1, min_len=300)
        else:
            P["speech_s"] = P["speech_transcribed_pct"] = P["untranscribed_s"] = None
            P["holes"], P["empty_audio"] = [], []
    # ---- swap / label check
    sw = {"method": None, "checked": 0, "agree_pct": None, "by_person": {}}
    if segs and all(p in tracks_db for p in PEOPLE):
        sw["method"] = "own-track loudness (each labelled line: is the labelled person's own track >= 6 dB louder?)"
        tally = {p: [0, 0] for p in PEOPLE}
        for t in turns:
            a, b = int(t["t"] / HOP), int(max(t.get("end") or t["t"], t["t"] + 1.0) / HOP) + 1
            me = tracks_db[t["who"]][0][a:b]
            other = tracks_db["Amal" if t["who"] == "Medi" else "Medi"][0][a:b]
            if not len(me):
                continue
            dme, doth = float(np.percentile(me, 90)), float(np.percentile(other, 90))
            if dme - doth >= LOUD_DB:
                tally[t["who"]][0] += 1
            elif doth - dme >= LOUD_DB:
                tally[t["who"]][1] += 1
        sw["by_person"] = {p: {"own_track_louder": a, "other_track_louder": b} for p, (a, b) in tally.items()}
        ok = sum(a for a, _ in tally.values())
        bad = sum(b for _, b in tally.values())
        sw["checked"] = ok + bad
        sw["agree_pct"] = round(100 * ok / (ok + bad), 1) if ok + bad else None
    else:
        mf = meet_file(date, meet)
        cap = captions(mf) if mf else []
        if cap and src.get("attribution") in ("pitch-guess", "diarized-mixed"):
            sw["method"] = "Meet caption track (named 4-s English caption blocks) vs the transcript's labels"
            ok = bad = 0
            for t in turns:
                mid = (t["t"] + max(t.get("end") or t["t"], t["t"] + 1.0)) / 2
                c = [w for a, b, w in cap if a <= mid <= b]
                if len(set(c)) != 1:
                    continue
                if c[0] == t["who"]:
                    ok += 1
                else:
                    bad += 1
            sw["checked"], sw["agree_pct"] = ok + bad, (round(100 * ok / (ok + bad), 1) if ok + bad else None)
            sw["meet_file"] = os.path.basename(mf)
        if (not cap or not sw["checked"]) and src.get("attribution") != "pitch-guess":
            audio = MIXED_AUDIO.get(date) or os.path.join(REPO, "docs", "lessons", date, "audio", "lesson.mp3")
            if os.path.exists(audio):
                x = decode(audio)
                sw["method"] = "voice pitch per line (Medi < 155 Hz, Amal > 180 Hz) vs the engine's diarization labels"
                ok = bad = 0
                for t in turns:
                    a, b = int(t["t"] * SR), int(max(t.get("end") or t["t"], t["t"] + 1.0) * SR)
                    lab, _ = pitch_label(x[a:b])
                    if lab is None:
                        continue
                    ok += lab == t["who"]
                    bad += lab != t["who"]
                sw["checked"], sw["agree_pct"] = ok + bad, (round(100 * ok / (ok + bad), 1) if ok + bad else None)
    # the caption check on EVERY lesson with a Meet recording: on lessons whose labels come from the tracks it gives
    # the baseline agreement of right labels (captions are English-only 4-s blocks, so it is never near 100 %)
    mf = meet_file(date, meet)
    if mf and not sw.get("meet_file"):
        cap = captions(mf)
        best = (None, 0, 0)
        for off in range(-180, 181):          # the Meet recording and the recording bot start at different moments
            ok = bad = 0
            for t in turns:
                mid = (t["t"] + max(t.get("end") or t["t"], t["t"] + 1.0)) / 2 + off
                c = [w for a, b, w in cap if a <= mid <= b]
                if len(set(c)) == 1:
                    ok += c[0] == t["who"]
                    bad += c[0] != t["who"]
            if ok + bad and (best[0] is None or ok / (ok + bad) > best[1] / max(1, best[1] + best[2])):
                best = (off, ok, bad)
        off, ok, bad = best
        sw["caption_agree_pct"] = round(100 * ok / (ok + bad), 1) if ok + bad else None
        sw["caption_checked"], sw["caption_offset_s"] = ok + bad, off
    res["swap_check"] = sw
    # ---- ASR review
    ivs = [(c["start"], c["end"]) for c in (wb_checks or {}).get("comparisons", []) if (evidence_dates or {}).get(c.get("event_id")) == date]
    res["asr_review"] = {"second_model_excerpts": len(ivs), "second_model_s": round(sum(b - a for a, b in ivs), 1), "human_listened_s": 0}
    # ---- flags (plain words; accuracy_gates.py turns them into reasons)
    for p in PEOPLE:
        P = res["people"][p]
        for a, b in P.get("lost_segments", []):
            res["flags"].append({"who": p, "kind": "audio-lost", "from": a, "to": b, "text": f"{p}'s recording {mmss(a)}-{mmss(b)} was not saved (its file was overwritten by a later segment)"})
        for a, b, s in P.get("holes", []):
            res["flags"].append({"who": p, "kind": "untranscribed", "from": a, "to": b, "speech_s": s,
                                 "text": f"{p} talks {mmss(a)}-{mmss(b)} ({s:.0f} s of speech on their own track) with no transcript line"})
    # cut-offs per method: loudness and pitch give ~91-96 % on right labels; the caption check gives only 59-67 % on right
    # labels (09-19 / 09-21 / 09-28 track lessons, English-only 4-s blocks), so its own cut-offs are lower
    cap_m = (sw.get("method") or "").startswith("Meet caption")
    swapped_below, doubtful_below = (35.0, 55.0) if cap_m else (50.0, 90.0)
    sw["cutoffs"] = {"swapped_below": swapped_below, "doubtful_below": doubtful_below}
    if sw["agree_pct"] is not None and sw["agree_pct"] < swapped_below:
        res["flags"].append({"who": None, "kind": "swapped", "text": f"speaker labels look SWAPPED: {sw['agree_pct']} % of {sw['checked']} lines agree ({sw['method']})"})
    elif sw["agree_pct"] is not None and sw["agree_pct"] < doubtful_below:
        res["flags"].append({"who": None, "kind": "labels-doubtful", "text": f"speaker labels agree with an independent check on only {sw['agree_pct']} % of {sw['checked']} lines ({sw['method']})"})
    return res


def mmss(t):
    t = int(round(t or 0))
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def gapfill_windows(repo=REPO):
    """Stretches filled from the mixed Meet recording (data/backfill/meet_gaps.json): speakers there come from diarization."""
    p = os.path.join(repo, "data", "backfill", "meet_gaps.json")
    out = {}
    if not os.path.exists(p):
        return out
    for e in J(p).get("entries", []):
        r = e.get("result") or {}
        if e.get("status") == "done":
            out.setdefault(e["date"], []).append({"who": "Medi" if e["missing"] == "medi" else "Amal", "from": e["window"]["from_s"], "to": e["window"]["to_s"],
                                                   "source": r.get("primary_source"), "diarization_confidence": r.get("diarization_confidence")})
    return out


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    doc = J(os.path.join(REPO, "docs", "data", "lessons.json"))
    sys.path.insert(0, HERE)
    import accuracy_gates as G
    cp = os.path.join(REPO, "docs", "data", "word-bank-transcription-checks.json")
    wbc = J(cp) if os.path.exists(cp) else None
    ed = G.evidence_date_index(REPO)
    cur = J(OUT) if os.path.exists(OUT) else {"lessons": {}}
    dates = [a for a in argv if re.fullmatch(r"\d{4}-\d{2}-\d{2}", a)] or [L["date"] for L in doc["lessons"]]
    gf = gapfill_windows()
    for L in doc["lessons"]:
        if L["date"] not in dates:
            continue
        D = J(os.path.join(REPO, "docs", "data", "lessons", L["date"] + ".json"))
        r = audit_lesson(L["date"], L, D, wbc, ed)
        r["gap_fill"] = gf.get(L["date"], [])
        for g in r["gap_fill"]:
            if g["source"] == "meet_mixed":
                r["flags"].append({"who": g["who"], "kind": "diarized-window", "from": g["from"], "to": g["to"],
                                   "text": f"{g['who']} {mmss(g['from'])}-{mmss(g['to'])} comes from the mixed Meet recording, speakers split by diarization (their own track is silent there)"})
        cur["lessons"][L["date"]] = r
        P = r["people"]
        print(f"{L['date']}  {r['recording'][:18]:18} swap {r['swap_check']['agree_pct']}% ({r['swap_check']['checked']})  "
              + "  ".join(f"{p}: audio {P[p].get('audio_pct')}% speech {P[p].get('speech_s')}s tx {P[p].get('speech_transcribed_pct')}% holes {len(P[p].get('holes', []))}" for p in PEOPLE))
        for f in r["flags"]:
            print("   -", f["text"])
    cur["about"] = ("Per lesson x per person source audit (scripts/source_audit.py): audio present, speech on each person's own "
                    "track, untranscribed speech, independent speaker-label check, ASR review. Read by scripts/accuracy_gates.py.")
    cur["cutoffs"] = {"hole_min_s": HOLE_MIN_S, "hole_window_s": HOLE_WINDOW_S, "turn_pad_s": TURN_PAD_S, "loud_db": LOUD_DB,
                      "speech": "own-track frame energy > max(20th percentile + 15 dB, -50 dBFS), 0.1-s frames"}
    cur["built"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    cur["lessons"] = dict(sorted(cur["lessons"].items()))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main(sys.argv[1:])
