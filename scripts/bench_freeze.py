# -*- coding: utf-8 -*-
"""Freeze the benchmark answer key BEFORE any engine runs (PR-11, PR-18).

    python scripts/bench_freeze.py 2026-10-02            # truth.json + prompts.json + clips + manifest.json
    python scripts/bench_freeze.py 2026-10-02 --check    # re-hash everything against the manifest (exit 1 on a change)

Truth = the engine's raw text + every correction of Medi's (transcript-fixes.json rows `by: medi`, his page / chat
corrections through transcript_fixes.load, context_transcribe.answer_key / amal_key). A second freeze over an existing
manifest is refused: a changed key is a new benchmark version (--version N), never a silent edit.
"""
import json, os, re, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402

AR = BC.AR_LETTER
LISTEN_CTX_S, CHAT_S = 40.0, 60.0


def raw(u):
    return u.get("engine") or u["text"]


def error_class(engine_wrote, heard, note=""):
    """The moment's error class for the by-class table (spec 5)."""
    e, h = engine_wrote or "", heard or ""
    if "kept" in note:
        return "kept-slip"
    if "vowel" in note:
        return "vowel"
    if BC.has_foreign(e):
        return "foreign-script"
    if e and not AR.search(e) and re.search(r"(^|[^a-z])(this|the|you)([^a-z]|$)", e.lower()):
        return "short-repeat-english"                # English look-alike words for a short Arabic repeat (TR-19)
    et, ht = BC.tokens(e), BC.tokens(h)
    if any(BC._num(x) or BC._num(re.sub("^ال", "", x)) for x in ht) or "الساعا" in ht:
        return "number-time"
    if e and not AR.search(e) and not AR.search(h):
        return "vowel"                               # Latin -> Latin (al- -> el-): a vowel-level fix
    if e and not AR.search(e) and AR.search(h):
        from xscript import is_english
        words = re.findall("[A-Za-z']+", e)
        return "short-repeat-english" if words and all(is_english(w.lower()) for w in words) else "latin-arabic"
    strip = lambda t: re.sub("^ال", "", t)  # noqa: E731
    if [strip(x) for x in et] == [strip(x) for x in ht] and et != ht:
        return "el-"
    return "wrong-arabic-word"


def build_truth(date):
    sys.path.insert(0, HERE)
    import context_transcribe as CT
    import self_fix_timing as SFT
    page = BC.J(os.path.join(BC.REPO, "docs", "data", "lessons", date + ".json"))
    turns = page["turns"]
    fixes = [r for r in (BC.J(os.path.join(BC.REPO, "data", "lesson-work", "transcript-fixes.json")) or {}).get("rows", [])
             if str(r.get("date")) == date]
    try:
        import medi_corrections as MC
        fixes += [dict(r, by="medi") for r in MC.text_rows() if str(r.get("date")) == date and r.get("engine_wrote")]
    except Exception as e:  # noqa: BLE001
        print("page corrections not read:", type(e).__name__)
    off = SFT.offsets(turns, SFT.words(date))
    lines, by_i = [], {}
    for i, u in enumerate(turns):
        if u["who"] not in ("Medi", "Amal"):
            continue
        rows = [r for r in fixes if r.get("who", "Medi") == u["who"] and abs(float(r["t"]) - u["t"]) <= 1.0
                and r["engine_wrote"] in raw(u)]
        ln = {"i": i, "who": u["who"], "t": u["t"], "end": u.get("end") or u["t"] + 2, "engine": raw(u), "truth": u["text"],
              "corrected": any(r.get("by") == "medi" for r in rows), "overlay": bool(u.get("engine")),
              "fixes": [{"engine_wrote": r["engine_wrote"], "heard": r["heard"], "by": r.get("by"), "rule": r.get("rule")} for r in rows]}
        by_i[i] = ln
        lines.append(ln)
    medi = [ln for ln in lines if ln["who"] == "Medi"]

    def line_at(who, t):
        return min((ln for ln in lines if ln["who"] == who), key=lambda ln: abs(ln["t"] - t))

    # --- moments: every correction of his = one moment; the hand list of 10-02 keeps its alternatives
    moments, seen = [], set()
    hand = {round(t, 2): (w, g, n) for t, w, g, n in CT.BENCH} if date == "2026-10-02" else {}
    for ln in medi:
        hb = hand.get(round(ln["t"], 2))
        mine = [f for f in ln["fixes"] if f["by"] == "medi"]
        if hb:
            w, g, n = hb
            moments.append({"id": "M%03d" % len(moments), "i": ln["i"], "t": ln["t"], "who": "Medi", "want": w, "gone": g, "stem": True,
                            "source": "hand list (context_transcribe.BENCH)" + (" + his overlay row" if mine else ""), "note": n,
                            "class": error_class(mine[0]["engine_wrote"] if mine else "", mine[0]["heard"] if mine else w[0], n)})
            seen.add(ln["i"])
            mine = mine[1:] if len(mine) > 1 else []     # a second row on a hand-list line is its own moment
        for f in mine:
            moments.append({"id": "M%03d" % len(moments), "i": ln["i"], "t": ln["t"], "who": "Medi", "want": [f["heard"]],
                            "gone": [f["engine_wrote"]] if f["engine_wrote"] not in f["heard"] else [], "stem": False,
                            "source": "his overlay row", "note": "%s -> %s" % (f["engine_wrote"], f["heard"]),
                            "class": error_class(f["engine_wrote"], f["heard"])})
    amal = []
    for ln in lines:
        if ln["who"] != "Amal":
            continue
        for f in ln["fixes"]:
            if f["by"] == "medi":
                amal.append({"id": "A%02d" % len(amal), "i": ln["i"], "t": ln["t"], "who": "Amal", "want": [f["heard"]],
                             "gone": [f["engine_wrote"]] if f["engine_wrote"] not in f["heard"] else [], "stem": False,
                             "source": "his overlay row (Amal's line)", "note": "%s -> %s" % (f["engine_wrote"], f["heard"]),
                             "class": error_class(f["engine_wrote"], f["heard"])})

    # --- slips: the published slips of the lesson (wrong -> right). An engine that writes `right` where he said `wrong`
    # hides the slip (the worst fault).
    slips = []
    for m in page.get("marks") or []:
        near = [ln for ln in medi if abs(ln["t"] - m["t"]) <= 3.0]
        wt = set(BC.tokens(m["wrong"]))
        near.sort(key=lambda ln: (-len(wt & set(BC.tokens(ln["truth"]) + BC.tokens(BC.latin_to_arabic(ln["truth"])))), abs(ln["t"] - m["t"])))
        if near:
            slips.append({"i": near[0]["i"], "t": near[0]["t"], "kind": m["kind"], "wrong": m["wrong"], "right": m["right"]})

    # --- which lines get a clip / a listener call (the production filter of context_transcribe.lesson + every key line)
    key_i = {m["i"] for m in moments} | {s["i"] for s in slips}
    for ln in medi:
        ln["has_arabic"] = bool(AR.search(ln["truth"]) or AR.search(ln["engine"]))
        ln["listen"] = bool(ln["has_arabic"] or ln["i"] in key_i or BC.has_foreign(ln["engine"]) or len(ln["engine"].split()) <= 6)
        ln["should_stay"] = not ln["fixes"] and not ln["overlay"]
        ln["clip"] = "clips/medi-%04d.wav" % ln["i"]
    for a in amal:
        by_i[a["i"]]["clip"] = "clips/amal-%04d.wav" % a["i"]

    truth = {"date": date, "version": 1, "frozen": datetime.datetime.now().isoformat(timespec="seconds"),
             "offsets": off, "pad_s": BC.PAD,
             "counts": {"medi_lines": len(medi), "with_arabic": sum(ln["has_arabic"] for ln in medi), "corrected_lines": sum(ln["corrected"] for ln in medi),
                        "listen_lines": sum(ln["listen"] for ln in medi), "should_stay": sum(ln["should_stay"] for ln in medi),
                        "medi_moments": len(moments), "amal_moments": len(amal), "slips": len(slips)},
             "moments": moments, "amal_moments": amal, "slips": slips,
             "lines": medi, "amal_lines": [by_i[a["i"]] for a in amal],
             "amal_all": [{"t": ln["t"], "end": ln["end"], "text": ln["engine"]} for ln in lines if ln["who"] == "Amal"],
             "vowel": [v for v in (BC.J(os.path.join(BC.REPO, "data", "lesson-work", "gemini-tests.json")) or {}).get("vowel", []) if v["date"] == date]}

    # --- the listeners' frozen prompt per line: RAW engine text of +-40 s (both speakers) + Amal's chat +-60 s. Never the
    # overlay, the truth, a correction row or an audit ruling.
    prompts = {}
    for ln in medi:
        if not ln["listen"]:
            continue
        ctx = "\n".join("%+.1f s %s: %s" % (v["t"] - ln["t"], v["who"], raw(v)) for k, v in enumerate(turns)
                        if ln["t"] - LISTEN_CTX_S <= v["t"] <= ln["t"] + LISTEN_CTX_S and v["who"] != "chat" and k != ln["i"])
        chat = " | ".join(v["text"] for v in turns if v["who"] == "chat" and ln["t"] - CHAT_S <= v["t"] <= ln["t"] + CHAT_S) or "(none)"
        prompts[str(ln["i"])] = CT.PROMPT.format(context=ctx, chat=chat, target=ln["engine"])
    return truth, prompts, CT.PROMPT


def cut(src, a, b, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % max(0.0, a), "-to", "%.3f" % b, "-i", src,
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", out], check=True)


def track_file(date, who):
    tr = os.path.join(BC.RAW, date, "tracks")
    f = [x for x in os.listdir(tr) if x.lower().endswith(".mp3") and x.lower().startswith(who.lower()[:4])]
    if len(f) != 1:
        raise SystemExit("expected one %s track in %s, found %d" % (who, tr, len(f)))
    return os.path.join(tr, f[0])


def make_clips(date, truth):
    d = BC.bench_dir(date)
    for who, lines in (("Medi", truth["lines"]), ("Amal", truth["amal_lines"])):
        src, off = track_file(date, who), truth["offsets"][who]
        for ln in lines:
            out = os.path.join(d, ln["clip"])
            if not os.path.exists(out):
                cut(src, ln["t"] - BC.PAD - off, ln["end"] + BC.PAD - off, out)
    whole = os.path.join(d, "clips", "medi-whole.wav")
    if not os.path.exists(whole):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", track_file(date, "Medi"), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", whole], check=True)


def hashes(date, truth):
    d = BC.bench_dir(date)
    clips = {ln["clip"]: BC.sha_file(os.path.join(d, ln["clip"])) for ln in truth["lines"] + truth["amal_lines"]}
    clips["clips/medi-whole.wav"] = BC.sha_file(os.path.join(d, "clips", "medi-whole.wav"))
    return {"truth_sha256": BC.sha_file(os.path.join(d, "truth.json")),
            "prompts_sha256": BC.sha_file(os.path.join(d, "prompts.json")),
            "clips_sha256": BC.sha_text(json.dumps(clips, sort_keys=True)), "clips": clips,
            "source_tracks": {who: BC.sha_file(track_file(date, who)) for who in ("Medi", "Amal")}}


def main(argv):
    date = argv[0]
    d = BC.bench_dir(date)
    mp = os.path.join(d, "manifest.json")
    if "--check" in argv:
        man = BC.J(mp)
        if not man:
            raise SystemExit("no manifest: not frozen")
        now = hashes(date, BC.J(os.path.join(d, "truth.json")))
        bad = [k for k in ("truth_sha256", "prompts_sha256", "clips_sha256") if now[k] != man[k]]
        print("bench freeze: %s" % ("CHANGED " + ", ".join(bad) if bad else "OK (truth %s)" % man["truth_sha256"][:16]))
        return 1 if bad else 0
    if os.path.exists(mp):
        raise SystemExit("already frozen (%s). A changed key is a new benchmark version, never a silent edit." % mp)
    truth, prompts, prompt = build_truth(date)
    BC.W(os.path.join(d, "truth.json"), truth)
    BC.W(os.path.join(d, "prompts.json"), {"template": prompt, "template_sha256": BC.sha_text(prompt), "context_s": LISTEN_CTX_S, "chat_s": CHAT_S, "by_line": prompts})
    make_clips(date, truth)
    man = dict({"date": date, "version": truth["version"], "frozen": truth["frozen"], "counts": truth["counts"],
                "normaliser_sha256": BC.sha_file(os.path.join(HERE, "bench_common.py"))}, **hashes(date, truth))
    BC.W(mp, man)
    print(json.dumps(truth["counts"]), "\ntruth", man["truth_sha256"][:16], "clips", man["clips_sha256"][:16], "prompts", man["prompts_sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
