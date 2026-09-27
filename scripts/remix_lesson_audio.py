# -*- coding: utf-8 -*-
"""Lesson audio with BOTH voices all the way through (Medi 2026-09-26: "for these clips we need the conversation with
both of us").

load_lesson.py mixed only the recordings it transcribed, so when an app reconnect split a person into two recordings
the untranscribed one was silent on docs/lessons/<date>/audio/lesson.mp3 (09-23: Medi 0:00-22:37; 09-26: Amal
0:00-18:33). This mixes EVERY Amal/Medi recording in tracks.json at its own start time (the page clock), checks the
new file lines up with the old one (cross-correlation on a stretch both have), swaps it in and deletes that lesson's
cut clips and re-cuts them (pages + the After-lesson links in Supabase) from the full mix.

    python scripts/remix_lesson_audio.py [DATE ...]     # default: every lesson with tracks/tracks.json
    python scripts/remix_lesson_audio.py --check DATE   # report only
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_lesson_page import mix_tracks  # noqa: E402
from load_lesson import _person  # noqa: E402
RAW = r"C:\dev\anees\data\lessons"


def pcm(path, start, secs, rate=8000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(secs), "-i", path, "-f", "s16le", "-ac", "1",
                          "-ar", str(rate), "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32)


def lag(old, new, rate=8000, win=60.0, at=None):
    """Seconds new is late vs old on a window where both have audio (0 = same clock)."""
    a, b = pcm(old, at, win, rate), pcm(new, at, win, rate)
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    f = np.fft.irfft(np.fft.rfft(b, 2 * n) * np.conj(np.fft.rfft(a, 2 * n)))
    k = int(np.argmax(f)); k = k - 2 * n if k > n else k
    return k / rate


def tracks(date):
    m = json.load(open(os.path.join(RAW, date, "tracks", "tracks.json"), encoding="utf-8"))
    out = []
    for t in m["tracks"]:
        if _person(t["participant"]) is None:
            continue
        p = os.path.join(RAW, date, "tracks", os.path.basename(t["file"]))
        if os.path.exists(p):
            out.append((p, float(t["start"]["relative"])))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dates", nargs="*"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    dates = a.dates or sorted(os.path.basename(os.path.dirname(os.path.dirname(p))) for p in glob.glob(os.path.join(RAW, "20*", "tracks", "tracks.json")))
    done = []
    for d in dates:
        old = os.path.join(REPO, "docs", "lessons", d, "audio", "lesson.mp3")
        if not os.path.exists(old):
            print(d, "no lesson.mp3 - skipped"); continue
        T = tracks(d)
        new = old + ".all.mp3"
        mix_tracks(T, new)
        # align on the middle of the lesson, where every lesson has both voices on the old mix
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", old], capture_output=True, text=True).stdout)
        L = lag(old, new, at=round(dur / 2))
        print(d, len(T), "recordings", "lag %.3f s" % L)
        if abs(L) > 0.05:
            print(d, "NOT swapped: the new mix is off the page clock"); os.remove(new); continue
        if a.check:
            os.remove(new); continue
        os.replace(new, old)
        gone = 0
        for c in glob.glob(os.path.join(REPO, "docs", "lessons", d, "clips", "gc-*.mp3")):  # audit clips; word-bank context-* clips already mix every recording
            os.remove(c); gone += 1
        print(d, "swapped; clips removed for re-cut:", gone)
        done.append(d)
    if done:
        recut(done)


def recut(dates):
    """Re-cut every gc- clip a page or a live link uses (same names: they hash the times), from the new mix."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for s in ("build_grammar_console.py", "build_amal_review.py"):
        subprocess.run([sys.executable, os.path.join(HERE, s)], cwd=REPO, env=env)
    import db
    from build_amal_review import cut_clip
    from full_audit_compare import sec
    A = {r["uid"]: r for r in json.load(open(os.path.join(REPO, "data", "full-audit-2026-09-26.json"), encoding="utf-8"))["rows"]}
    for L in db.select("amal_links", {"select": "lesson_date,payload", "kind": "eq.after", "lesson_date": "in.(%s)" % ",".join(dates)}):
        for q in (L.get("payload") or {}).get("questions", []):
            r = A.get(q.get("audit_uid"))
            if q.get("clip") and r:
                c = cut_clip(L["lesson_date"], q["t"], sec(r.get("t_amal")))
                print(L["lesson_date"], "after question", q.get("n"), "clip ok" if c == q["clip"] else "clip MISMATCH " + str(c))


if __name__ == "__main__":
    main()
