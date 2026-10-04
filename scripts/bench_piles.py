# -*- coding: utf-8 -*-
"""A better pile rule for the re-hear proposals, replayed on the saved runs (PR-18; review
ANEES-FABLE-53-TO-60-REVIEW-2026-10-04, experiment 2; Medi 2026-10-04 "do all of your recommendations").

No call of any kind: the 3 frozen baseline runs and the 3 frozen two-clip (V3) runs are read. scripts/bench_rehear.py
stays as it is; its rule is replayed here as "old" and asserted equal to its own output.

  old   a line's change is proposed only when 2 of 3 runs agree on the WHOLE line; held when a word it adds is said by
        Amal in the next 15 s
  (a)   where the whole line has no 2-of-3 agreement: each run is aligned against the engine's line word by word and
        every changed span that 2 of 3 runs wrote the same is kept, even when the rest of the line differs between runs.
        A span no run wrote is never built.
  (b)   a held line is released when the two-clip check already run (V3) says in 2 of 3 runs that the learner said
        Amal's word himself (`took` true); otherwise it stays held.

THE ANSWER KEY DECIDES NOTHING. `decide()` and everything it calls see only `bare()` lines (the engine's text and the
times), Amal's raw lines, the runs and the V3 verdicts - they take no truth object. `measure()` is the only place the
key is read, after every pile is final (tests/test_bench_piles.py asserts both).

    python scripts/bench_piles.py 2026-10-02     # variables/piles.json + piles.md (and the table printed)
"""
import collections, difflib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402

BASE = "gemini-flash-t1"
V3 = "gemini-flash-v3-t1"
AMAL_NEXT_S = 15.0               # the hold rule of scripts/bench_rehear.py
BARE = ("i", "t", "end", "engine")
RULES = (("old", False, False), ("a", True, False), ("b", False, True), ("a+b", True, True))


# ------------------------------------------------------------------ the decision (never the key)

def bare(lines):
    """Only what a pile decision may see of a line: its id, its times and the engine's raw text."""
    return [{k: ln[k] for k in BARE} for ln in lines]


def words(text):
    """[(key, raw, a, b)] - the raw words of a line with their normalised key and their place a..b in text.split(); a
    lone و joins the next Arabic word (as bench_common.tokens does) and pieces with no letters (punctuation, fillers)
    are left out of the alignment (they keep their place in the engine's line)."""
    raw = (text or "").split()
    out, k = [], 0
    while k < len(raw):
        w, a = raw[k], k
        if BC.tokens(w, fillers=True) == ["و"] and k + 1 < len(raw) and any(BC.is_ar(x) for x in BC.tokens(raw[k + 1])[:1]):
            w, k = w + " " + raw[k + 1], k + 1
        key = " ".join(BC.tokens(w))
        if key:
            out.append((key, w, a, k + 1))
        k += 1
    return out


def _blocks(i1, i2, keys, raw):
    """One replaced stretch in its smallest safe pieces: a same-length replacement and a deletion go word by word; an
    insertion or an uneven replacement stays one span (its inside cannot be lined up)."""
    if not keys:
        return [(i, i + 1, (), ()) for i in range(i1, i2)]
    if i2 - i1 == len(keys):
        return [(i1 + n, i1 + n + 1, (keys[n],), (raw[n],)) for n in range(i2 - i1)]
    return [(i1, i2, tuple(keys), tuple(raw))]


def run_changes(engine_keys, run_words):
    """One run against the engine's line: [(i1, i2, keys, raw)] - engine words i1..i2 replaced by `raw`."""
    rk = [w[0] for w in run_words]
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, engine_keys, rk, autojunk=False).get_opcodes():
        if tag != "equal":
            out += _blocks(i1, i2, rk[j1:j2], [w[1] for w in run_words[j1:j2]])
    return out


def split_on_others(per_run):
    """An uneven replacement hides what two runs share ("this suck" -> "لسه" in one run, "this suck today" -> "لسه
    tonight" in another). A run's span is cut in two where ANOTHER run's whole span sits at its left or right edge with
    the same words: the shared piece and the rest, both still this run's own words in this run's own order."""
    for _ in range(8):
        moved = False
        for r, mine in enumerate(per_run):
            others = {(c[0], c[1], c[2]) for q, cs in enumerate(per_run) if q != r for c in cs if c[2]}
            for b in list(mine):
                i1, i2, keys, raw = b
                for a1, a2, ck in sorted(others):
                    n = len(ck)
                    if (a1, a2, ck) == (i1, i2, keys) or not (i1 <= a1 and a2 <= i2) or n > len(keys) or (n == len(keys) and (a1, a2) != (i1, i2)):
                        continue
                    if a1 == i1 and keys[:n] == ck and (a2 < i2 or n < len(keys)):
                        parts = [(i1, a2, ck, raw[:n])] + (_blocks(a2, i2, keys[n:], raw[n:]) if (a2 < i2 or n < len(keys)) else [])
                    elif a2 == i2 and keys[len(keys) - n:] == ck and (i1 < a1 or n < len(keys)):
                        parts = _blocks(i1, a1, keys[:len(keys) - n], raw[:len(keys) - n]) + [(a1, i2, ck, raw[len(keys) - n:])]
                    else:
                        continue
                    k = mine.index(b)
                    mine[k:k + 1] = parts
                    moved = True
                    break
        if not moved:
            break
    return per_run


def span_vote(engine, texts):
    """The engine's line with every changed span that MORE THAN HALF of the runs wrote the same (same engine words
    replaced by the same normalised words). Returns (text, [kept spans]); text is None when nothing was agreed. Each
    kept span is copied from a run that wrote it; two kept spans that overlap are both dropped (never a span no run wrote)."""
    ew = words(engine)
    ek = [w[0] for w in ew]
    votes, raw_of = collections.Counter(), {}
    for mine in split_on_others([run_changes(ek, words(t)) for t in texts]):
        seen = set()
        for i1, i2, keys, raw in mine:
            c = (i1, i2, keys)
            if c not in seen:
                seen.add(c)
                votes[c] += 1
                raw_of.setdefault(c, raw)
    kept = sorted(c for c, n in votes.items() if n * 2 > len(texts))
    clash = set()
    for a, b in zip(kept, kept[1:]):
        if b[0] < a[1] or (a[0] == a[1] == b[0] == b[1]):         # overlapping, or two different insertions at one place
            clash |= {a, b}
    kept = [c for c in kept if c not in clash]
    if not kept:
        return None, []
    raw = (engine or "").split()
    at = lambda i: ew[i][2] if i < len(ew) else len(raw)  # noqa: E731  (the place of engine word i in the raw line)
    out, pos = [], 0
    for c in kept:
        a = at(c[0])
        out += raw[pos:a] + list(raw_of[c])
        pos = ew[c[1] - 1][3] if c[1] > c[0] else a
    out += raw[pos:]
    return " ".join(out), [{"engine": " ".join(w[1] for w in ew[c[0]:c[1]]), "said": " ".join(raw_of[c]), "runs": votes[c]} for c in kept]


def amal_words_next(line, amal_all):
    hers = set()
    for a in amal_all:
        if line["t"] < a["t"] <= line["end"] + AMAL_NEXT_S:
            hers |= set(BC.tokens(a["text"]))
    return hers


def added_words(engine, heard):
    old = set(BC.tokens(engine)) | set(BC.tokens(BC.latin_to_arabic(engine)))
    return [w for w in BC.tokens(heard) if BC.is_ar(w) and w not in old]


def decide(lines, runs, amal_all, spans=False, v3_took=None):
    """The piles. lines = bare(); runs = [{line_i: {"text", "alt"?}}]; amal_all = Amal's raw lines with times;
    v3_took = {line_i: [took per V3 run]} or None. Returns one row per line the listener changed:
    status proposed / held / no-agreement, `heard` (None when nothing is proposed), how (whole-line / spans), released."""
    assert all(set(ln) == set(BARE) for ln in lines), "a pile decision sees only the bare line"
    rows = []
    for ln in lines:
        outs = [r.get(str(ln["i"])) for r in runs]
        if all(o is None for o in outs):
            continue
        outs = [o if o is not None else {"text": ln["engine"]} for o in outs]
        keys = [" ".join(BC.tokens(o.get("text") or "")) for o in outs]
        k, n = collections.Counter(keys).most_common(1)[0]
        ekey = " ".join(BC.tokens(ln["engine"]))
        if k == ekey:
            continue                                              # the listener agrees with the engine
        row = {"i": ln["i"], "t": ln["t"], "engine": ln["engine"], "agree": n, "runs": [o.get("text") or "" for o in outs],
               "status": "no-agreement", "heard": None, "alt": "", "how": None, "released": False}
        if n * 2 > len(outs):
            o = outs[keys.index(k)]
            row.update(heard=o.get("text") or "", alt=o.get("alt") or "", how="whole-line")
        elif spans:
            text, kept = span_vote(ln["engine"], [o.get("text") or "" for o in outs])
            tkey = " ".join(BC.tokens(text or ""))
            if text is not None and tkey != ekey:
                row.update(heard=text, how="spans", spans=kept)
                if tkey in keys:                                  # the agreed spans add up to one run's own line: its text and Arabizi
                    o = outs[keys.index(tkey)]
                    row.update(heard=o.get("text") or "", alt=o.get("alt") or "")
        if row["heard"] is not None:
            danger = [w for w in added_words(ln["engine"], row["heard"]) if w in amal_words_next(ln, amal_all)]
            row.update(amal_next=danger, status="held" if danger else "proposed")
            took = (v3_took or {}).get(str(ln["i"]))
            # (b) only for a whole-line change: that is the text the two-clip check was asked about
            if danger and took and row["how"] == "whole-line" and sum(1 for x in took if x is True) * 2 > len(took):
                row.update(status="proposed", released=True)
        rows.append(row)
    return rows


def v3_verdicts(v3_runs):
    """{line_i: [took in run 1, 2, 3]} for the lines the two-clip check was sent (its `called` list)."""
    out = collections.defaultdict(list)
    for r in v3_runs:
        for i in r.get("called") or []:
            out[i].append((r["lines"].get(i) or {}).get("took"))
    return dict(out)


# ------------------------------------------------------------------ the measurement (the ONLY place the key is read)

def measure(truth, rows):
    lines = {ln["i"]: ln for ln in truth["lines"]}
    by_i = {r["i"]: r for r in rows}
    took = lambda held: {i: r for i, r in by_i.items() if r["status"] == "proposed" or (held and r["status"] == "held")}  # noqa: E731

    def fixed(held):
        P = took(held)
        return sorted(m["id"] for m in truth["moments"] if m["i"] in P and BS.has_want(m, P[m["i"]]["heard"], P[m["i"]]["alt"], truth_line=lines[m["i"]]["truth"]))

    def hidden(held):
        P = took(held)
        return [s for s in truth["slips"] if BS.slip_hidden(s, lines[s["i"]]["truth"], P[s["i"]]["heard"] if s["i"] in P else lines[s["i"]]["engine"])]

    def untouched(status):
        return sorted(r["i"] for r in rows if r["status"] == status and lines[r["i"]]["should_stay"] and BS.content_change(lines[r["i"]]["truth"], r["heard"]))

    def delivered():                                              # the transcript the proposed pile would make: right moments in it
        P = took(False)
        return sorted(m["id"] for m in truth["moments"] if BS.has_want(m, P[m["i"]]["heard"] if m["i"] in P else lines[m["i"]]["engine"],
                                                                        P[m["i"]]["alt"] if m["i"] in P else "", truth_line=lines[m["i"]]["truth"]))

    c = collections.Counter(r["status"] for r in rows)
    prop = [r for r in rows if r["status"] == "proposed"]
    wordy = sum(1 for r in prop if BS.content_change(r["engine"], r["heard"]))
    f, fh = fixed(False), fixed(True)
    return {"lines_changed": len(rows), "proposed": c["proposed"], "proposed_words": wordy, "proposed_alphabet": c["proposed"] - wordy,
            "proposed_by_spans": sum(1 for r in prop if r["how"] == "spans"), "released_by_v3": sum(1 for r in rows if r["released"]),
            "held": c["held"], "no_agreement": c["no-agreement"],
            "moments": len(truth["moments"]), "moments_fixed_by_proposed": len(f), "moments_fixed_with_held": len(fh),
            "moments_right_in_delivered_transcript": len(delivered()), "moment_ids_proposed": f, "moment_ids_only_in_held": sorted(set(fh) - set(f)),
            "slips_hidden_by_proposed": len(hidden(False)), "slips_hidden_with_held": len(hidden(True)),
            "slips_hidden_rows": [{"t": s["t"], "wrong": s["wrong"], "right": s["right"]} for s in hidden(False)],
            "untouched_lines_word_changed_proposed": len(untouched("proposed")), "untouched_lines_word_changed_held": len(untouched("held")),
            "untouched_proposed_i": untouched("proposed")}


NAMES = {"old": "Old rule (whole line, 2 of 3)", "a": "(a) word / span agreement", "b": "(b) release by the two-clip check", "a+b": "(a) + (b)"}


def table(res):
    out = ["| Rule | Proposed lines | of them words / alphabet | Held | No agreement | Moments fixed by proposed (of %d) | ... with held | Right in the delivered transcript | Slips hidden by proposed | ... with held | Untouched lines with a word changed, proposed | ... held |" % res["old"]["moments"],
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, _, _ in RULES:
        r = res[k]
        out.append("| %s | %d | %d / %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            NAMES[k], r["proposed"], r["proposed_words"], r["proposed_alphabet"], r["held"], r["no_agreement"], r["moments_fixed_by_proposed"],
            r["moments_fixed_with_held"], r["moments_right_in_delivered_transcript"], r["slips_hidden_by_proposed"], r["slips_hidden_with_held"],
            r["untouched_lines_word_changed_proposed"], r["untouched_lines_word_changed_held"]))
    return "\n".join(out)


def main(argv):
    date = argv[0]
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    runs = [r["lines"] for r in BS.load_runs(d, BASE, "line")]
    v3_runs = BS.load_runs(d, V3, "line")
    took = v3_verdicts(v3_runs)
    lines, amal = bare(truth["lines"]), truth.get("amal_all") or []

    piles = {k: decide(lines, runs, amal, spans=a, v3_took=took if b else None) for k, a, b in RULES}     # every pile is final here ...
    res = {k: measure(truth, piles[k]) for k, _, _ in RULES}                                               # ... before the key is opened

    # the old rule here is bench_rehear's own rule: same piles, same texts
    import bench_rehear as RH
    theirs = {r["i"]: (r["status"], r.get("heard")) for r in RH.proposals(truth, runs)}
    assert theirs == {r["i"]: (r["status"], r["heard"]) for r in piles["old"]}, "the replayed old rule is not bench_rehear's"
    held_old = {str(r["i"]) for r in piles["old"] if r["status"] == "held"}
    assert set(took) <= held_old, "the two-clip check was run on lines that are not in the old held pile"
    assert all(len(v) == len(v3_runs) for v in took.values())

    old = res["old"]
    moves = {}
    for k, _, _ in RULES[1:]:
        was = {r["i"]: r for r in piles["old"]}
        moves[k] = [{"i": r["i"], "mmss": "%02d:%02d" % (int(r["t"]) // 60, int(r["t"]) % 60), "from": was[r["i"]]["status"], "to": r["status"], "how": r["how"],
                     "engine": r["engine"], "heard": r["heard"], "spans": r.get("spans"), "runs": r["runs"] if r["how"] == "spans" else None,
                     "amal_next": r.get("amal_next"), "v3_took": took.get(str(r["i"]))}
                    for r in piles[k] if (r["status"], r["heard"]) != (was[r["i"]]["status"], was[r["i"]]["heard"])]
        res[k]["moments_gained_vs_old"] = sorted(set(res[k]["moment_ids_proposed"]) - set(old["moment_ids_proposed"]))
        res[k]["moments_lost_vs_old"] = sorted(set(old["moment_ids_proposed"]) - set(res[k]["moment_ids_proposed"]))
    held_no_check = sum(1 for r in piles["a+b"] if r["status"] == "held" and str(r["i"]) not in took)
    BC.W(os.path.join(d, "variables", "piles.json"),
         {"date": date, "engine": BASE, "runs": len(runs), "v3_engine": V3, "v3_runs": len(v3_runs), "v3_lines_checked": len(took),
          "v3_lines_released": sorted(int(i) for i, v in took.items() if sum(1 for x in v if x is True) * 2 > len(v)),
          "held_lines_with_no_two_clip_check_under_a+b": held_no_check,
          "key_use": "measure() only; decide() sees bare lines (i, t, end, engine), Amal's raw lines, the runs and the V3 verdicts",
          "rules": res, "moved_lines": moves})
    md = ["# Pile rules replayed on the saved runs (%s, %s, %d runs)" % (date, BASE, len(runs)), "",
          "No call was made. The answer key scores the piles after they are final; it decides none. \"Right in the delivered transcript\" = the proposed pile applied, the engine's text everywhere else (it also counts moments the engine already had right).", "", table(res), ""]
    for k, _, _ in RULES[1:]:
        md.append("- %s: gains %s; loses %s; %d lines moved pile." % (NAMES[k], " ".join(res[k]["moments_gained_vs_old"]) or "none",
                                                                    " ".join(res[k]["moments_lost_vs_old"]) or "none", len(moves[k])))
    md.append("- Two-clip check (V3): %d held lines were checked, %d released (2 of 3 runs said he said the word himself). Under (a) + (b), %d held lines have no two-clip check (new span-vote lines) and stay held." % (
        len(took), res["b"]["released_by_v3"], held_no_check))
    for k, _, _ in RULES:
        md.append("- Slips hidden by the proposed pile, %s: %s" % (NAMES[k], "; ".join("%02d:%02d %s -> %s" % (int(s["t"]) // 60, int(s["t"]) % 60, s["wrong"], s["right"]) for s in res[k]["slips_hidden_rows"]) or "none"))
    md = "\n".join(md) + "\n"
    with open(os.path.join(d, "variables", "piles.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
