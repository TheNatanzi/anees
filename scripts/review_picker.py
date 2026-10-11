"""Fast review mode picker (PG-50; Medi 2026-10-10: "It takes a lot of time to review in its current state" · "Is there
anyway we can simplify this so that it doesnt take as much time for amal and i").

    python scripts/review_picker.py 2026-10-08        -> docs/data/review-pick/2026-10-08.json
    python scripts/review_picker.py --all             -> one file per lesson with a built page (docs/data/lessons/*.json)

The Lessons page review mode (docs/js/review-mode.js) shows the student's lines that hold Arabic one at a time. This
file says which lines and in what order:
  - a line = one of his sentences as the page shows it (consecutive Student lines joined the PG-23 / PG-42 way: nobody
    else between, a pause of 6 s or less, or up to 15 s when the line goes on); it holds Arabic when
    scripts/word_coverage.py word_tokens finds an Arabic word in it (the grade book's count, PG-46);
  - three tiers (2026-10-11: with every second-listen change counted, 183 of 200 lines of 10-08 were 'unsure'):
    tier 1 unsure = (a) a ✗ chip sits on it (tmarks), (b) the two readers disagreed on it
    (data/lesson-work/full-audit/<date>.compare.json disputes), (c) the second listen held a change on it or no 2 of
    its 3 runs agree (data/lesson-work/rehear/<date>: apply-plan.json held / held_mix / held_tutor / no_agreement,
    proposals.json, base-run1..3.json + lines.json), or (d) it is one of 5 random tier-3 lines (ranked by a hash of the
    date and the line time, so the set is stable per date);
    tier 2 changed = the second listen changed it with 2 of 3 runs agreeing (apply-plan lines_changed, or a heard row by
    gemini-rehear on the turn);
    tier 3 confident = the rest. why[] lists every signal on the line, whatever its tier.
  - order: tier 1, tier 2, tier 3, each in time order. The blind block is the first 50 lines SHOWN in that order (no
    chips; protocol §2.2). The page's "Unsure only" toggle = tier 1; it stops at an end card offering tiers 2 + 3 for
    the grade book (council 2026-10-10: the answer key must not inherit the pipeline's confident errors).
  - propose: the robot's guess for key 3 (a mistake): vocab or grammar and the word, from the readers' rows on the line,
    else its chips, else the line's first Arabic word. He flips it with one key; never asked for a rule id.
A missing input file means that signal is absent, never a failure. Display only: nothing is scored from this file.
"""
import argparse, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
DOCS = os.path.join(REPO, "docs")
OUT_DIR = os.path.join(DOCS, "data", "review-pick")
RANDOM_N = 5
BLIND_N = 50
JOIN_GAP, JOIN_LONG = 6, 15          # docs/js/lessons-page.js sentences() (PG-23 / PG-42)


def J(p, d=None):
    if not p or not os.path.exists(p):
        return d
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def mmss(t):
    t = int(max(0, float(t or 0)))
    return "%d:%02d:%02d" % (t // 3600, t // 60 % 60, t % 60) if t >= 3600 else "%02d:%02d" % (t // 60, t % 60)


def sec(s):
    if isinstance(s, (int, float)):
        return float(s)
    try:
        p = [float(x) for x in str(s).strip().split(":")]
    except ValueError:
        return None
    v = 0.0
    for x in p:
        v = v * 60 + x
    return v


def letters(s):
    """Letters only (no harakat, punctuation, spaces), alef/ta-marbuta folded: two runs that differ only in commas agree."""
    s = re.sub(r"[ً-ْٰـ]", "", str(s or ""))
    s = re.sub(r"[أإآ]", "ا", s).replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"[^\w]|_|\d", "", s.lower())


# ------------------------------------------------------------------ his sentences (the page's join)
def _ends(s):
    s = re.sub(r"(?:[\s,،]*(?:um|uh|mm|mm-hmm|hmm|آآآ|امم)[.,!?؟]*)+\s*$", "", str(s or ""), flags=re.I).strip()
    return not s or bool(re.search(r"[.!?؟][\"”')]*$", s))


def _goes_on(prev, t, gap):
    return gap <= JOIN_GAP or (gap <= JOIN_LONG and (not _ends(prev.get("text")) or bool(re.match(r"^[a-z]", str(t.get("text") or "").strip()))))


def sentences(turns):
    """[[turn index, ...]] of his lines, joined like the page (a chat line between his pieces does not break them)."""
    out, cur, prev = [], None, None
    for i, t in enumerate(turns):
        who = t.get("who")
        if who == "chat":
            continue
        if who != "Medi":
            cur, prev = None, t
            continue
        gap = float(t["t"]) - float(prev["end"] if prev and prev.get("end") is not None else (prev or {}).get("t", -99))
        if cur is not None and prev is not None and prev.get("who") == "Medi" and _goes_on(prev, t, gap):
            cur.append(i)
        else:
            cur = [i]
            out.append(cur)
        prev = t
    return out


# ------------------------------------------------------------------ the signals
def _agree(runs):
    """How many of the runs say the same line (letters only)."""
    got = [letters(x) for x in runs or [] if x is not None]
    return max((got.count(g) for g in set(got)), default=0)


NO_AGREE = "second listen: no 2 of 3 runs agree"
HELD = "second listen held a change"
CHANGED = "second listen changed it"


def _rehear(date, repo):
    """[(t, why, tier)] from the second listen's files of this lesson. Tier 1 = it held a change or no 2 of 3 runs
    agree; tier 2 = it changed the line with 2 of 3 runs (or more) agreeing; None = a note only (why[] stays complete)."""
    d = os.path.join(repo, "data", "lesson-work", "rehear", date)
    out = []
    plan = J(os.path.join(d, "apply-plan.json"), {}) or {}
    for r in plan.get("lines_changed") or []:
        runs = r.get("runs") or []
        if runs and _agree(runs) < 2:
            out.append((r.get("t"), CHANGED + ", but no 2 of 3 runs agree", 1))
        else:
            out.append((r.get("t"), CHANGED, 2))
            if runs and _agree(runs) < len(runs):
                out.append((r.get("t"), "second listen: 2 of 3 runs agree", None))
    for key in ("held", "held_mix", "held_tutor"):
        for r in plan.get(key) or []:
            out.append((r.get("t"), HELD, 1))
    for r in plan.get("no_agreement") or []:
        out.append((r.get("t"), NO_AGREE, 1))
    for r in (J(os.path.join(d, "proposals.json"), {}) or {}).get("rows") or []:
        if r.get("status") == "no-agreement" or (r.get("runs") and _agree(r.get("runs")) < 2):
            out.append((r.get("t"), NO_AGREE, 1))
        elif r.get("status") in ("held", "held-mix", "held-tutor"):
            out.append((r.get("t"), HELD, 1))
    lines = (J(os.path.join(d, "lines.json"), {}) or {}).get("lines") or []
    at = {str(x.get("i")): x.get("t") for x in lines if isinstance(x, dict)}
    runs = [((J(os.path.join(d, "base-run%d.json" % k), {}) or {}).get("lines") or {}) for k in (1, 2, 3)]
    if at and any(runs):
        for i in set().union(*[set(r) for r in runs]):
            got = [(r.get(i) or {}).get("text") for r in runs if i in r]
            if len(got) == 3 and at.get(i) is not None and _agree(got) < 2:
                out.append((at[i], NO_AGREE, 1))
    return [(float(t), w, k) for t, w, k in out if isinstance(t, (int, float))]


def _readers(date, repo):
    """[(t, why, row)] where the two readers disagreed (full-audit compare.json disputes)."""
    c = J(os.path.join(repo, "data", "lesson-work", "full-audit", date + ".compare.json"), {}) or {}
    out = []
    for dsp in c.get("disputes") or []:
        for side in ("r1", "r2"):
            r = dsp.get(side)
            t = sec((r or {}).get("t"))
            if t is not None:
                out.append((t, "the two readers disagreed (%s: %s)" % (dsp.get("id") or "?", dsp.get("why") or "one reader only"), r))
    return out


def _readers_rows(date, repo):
    """Every reader row (agreed + disputed) with its time, for the key-3 proposal."""
    c = J(os.path.join(repo, "data", "lesson-work", "full-audit", date + ".compare.json"), {}) or {}
    rows = [r for r in c.get("agreed") or []]
    for dsp in c.get("disputes") or []:
        rows += [dsp[s] for s in ("r1", "r2") if dsp.get(s)]
    return [(sec(r.get("t")), r) for r in rows if sec(r.get("t")) is not None]


def _rank(date, t):
    return hashlib.sha1(("%s|%.2f" % (date, float(t))).encode("utf-8")).hexdigest()


def pick(date, d=None, repo=REPO):
    """-> the review-pick JSON for one lesson (see the module doc)."""
    import word_coverage as WC
    d = d if d is not None else (J(os.path.join(DOCS if repo == REPO else os.path.join(repo, "docs"), "data", "lessons", date + ".json"), {}) or {})
    turns, tm = d.get("turns") or [], d.get("tmarks") or {}
    rehear, readers, rrows = _rehear(date, repo), _readers(date, repo), _readers_rows(date, repo)
    items = []
    for parts in sentences(turns):
        P = [turns[i] for i in parts]
        toks = [x for p in P for x in WC.word_tokens(p.get("text") or "") if not x.get("cut")]
        if not toks:
            continue
        t0, t1 = float(P[0]["t"]), float(P[-1].get("end") if P[-1].get("end") is not None else P[-1]["t"])
        why, tier = [], 3

        def on(t, pad=0.6):
            return any(float(p["t"]) - pad <= t <= float(p.get("end") if p.get("end") is not None else p["t"]) + pad for p in P)

        for t, w, k in rehear:
            if on(t):
                if w not in why:
                    why.append(w)
                if k:
                    tier = min(tier, k)
        if any(h.get("by") == "gemini-rehear" for p in P for h in p.get("heard") or []):
            tier = min(tier, 2)
            if not any(w.startswith(CHANGED) for w in why):
                why.append(CHANGED)
        for t, w, _r in readers:
            if on(t, 1.0):                       # the readers write whole seconds
                tier = 1
                if w not in why:
                    why.append(w)
        chips = [c for i in parts for c in (tm.get(str(i)) or {}).get("c") or []]
        for c in chips:
            if c.get("s") == "wrong" and c.get("k") in ("vocab", "grammar"):
                w = "✗ chip on it (%s)" % (c.get("ar") or c.get("said") or c.get("k"))
                tier = 1
                if w not in why:
                    why.append(w)
        # key 3: the robot's proposal (vocab or grammar + the word); the readers first, then the chips, then the line
        prop = None
        for t, r in rrows:
            if on(t, 1.0) and r.get("wrong"):
                prop = {"k": "grammar" if str(r.get("kind") or "").startswith("grammar") else "vocab",
                        "said": str(r.get("wrong"))[:80], "right": (str(r.get("right"))[:80] if r.get("right") else None), "from": "readers"}
                break
        if not prop:
            c = next((c for c in chips if c.get("k") in ("vocab", "grammar") and c.get("s") in ("wrong", "partial", "asked", "repeat")), None) \
                or next((c for c in chips if c.get("k") in ("vocab", "grammar")), None)
            if c:
                prop = {"k": c["k"], "said": str(c.get("said") or c.get("ar") or "")[:80] or toks[0]["ar"], "right": c.get("right"), "from": "chip"}
        if not prop:
            prop = {"k": "vocab", "said": toks[0]["shown"], "right": None, "from": "line"}
        items.append({"i": parts[0], "parts": parts, "t": round(t0, 2), "end": round(t1, 2), "mmss": mmss(t0),
                      "words": len(toks), "tier": tier, "unsure": tier == 1, "why": why, "propose": prop})
    # (d) 5 random tier-3 lines, seeded by the date (a hash per line time: stable when other lines change)
    conf = sorted((x for x in items if x["tier"] == 3), key=lambda x: _rank(date, x["t"]))
    for x in conf[:RANDOM_N]:
        x["tier"], x["unsure"], x["random"] = 1, True, True
        x["why"].insert(0, "random check: one of %d confident lines picked by the date" % RANDOM_N)
    shown = sorted(items, key=lambda x: (x["tier"], x["t"]))     # tier 1, tier 2, tier 3; each in time order
    for n, x in enumerate(shown, 1):
        x["order"] = n
        x["blind"] = n <= BLIND_N
    tn = {str(k): sum(1 for x in items if x["tier"] == k) for k in (1, 2, 3)}
    un = tn["1"]
    return {"about": "Fast review mode (PG-50): the student's lines that hold Arabic in three tiers (1 unsure, 2 changed by "
                     "the second listen, 3 confident; why listed), shown tier by tier; blind = the first %d shown, without "
                     "chips. Built by scripts/review_picker.py; display only." % BLIND_N,
            "date": date, "all": len(items), "unsure": un, "unsure_n": un, "changed_n": tn["2"], "confident_n": tn["3"],
            "tier_n": tn,
            "tiers": {"1": "unsure: a ✗ chip, the two readers disagree, the second listen held a change or no 2 of its 3 runs "
                           "agree, or one of 5 random confident lines",
                      "2": "changed: the second listen changed the line with 2 of 3 runs agreeing",
                      "3": "confident"},
            "blind_n": BLIND_N, "random_n": min(RANDOM_N, len(conf)),
            "secs": round(sum(x["end"] - x["t"] for x in items), 1),
            "unsure_secs": round(sum(x["end"] - x["t"] for x in items if x["unsure"]), 1),
            "lines": items}


def dates(repo=REPO):
    p = os.path.join(repo, "docs", "data", "lessons")
    return sorted(f[:10] for f in os.listdir(p) if re.match(r"\d{4}-\d\d-\d\d\.json$", f)) if os.path.isdir(p) else []


def run(date, repo=REPO, log=print):
    out = pick(date, repo=repo)
    W(os.path.join(repo, "docs", "data", "review-pick", date + ".json"), out)
    log("review_picker %s: %d lines with Arabic; tier 1 unsure %d, tier 2 changed %d, tier 3 confident %d" % (date, out["all"], out["unsure_n"], out["changed_n"], out["confident_n"]))
    return out


def run_all(repo=REPO, log=print):
    return [run(d, repo, log) for d in dates(repo)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("date", nargs="?")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    if a.all or not a.date:
        run_all()
    else:
        run(a.date)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
