# -*- coding: utf-8 -*-
"""Side columns for scoreboard A (PR-18; review ANEES-FABLE-53-TO-60-REVIEW-2026-10-04, experiment 1; Medi 2026-10-04
"do all of your recommendations"). NEVER the headline: the strict number is bench_score's own and is asserted here.

Pure side code: it imports the frozen scorer (bench_score.py) and normaliser (bench_common.py) and changes neither.
Same runs, same answer key, the 2-of-3 rule stays. Per engine with complete line runs:

  strict       bench_score's number (asserted equal, moment by moment)
  cutoff_ok    a moment also counts when the engine wrote a clearly CUT-OFF form of the wanted word: an Arabic prefix
               of the wanted word, 3+ letters (at least 2 of them after a leading ال: الغـ alone could be any word),
               followed by a break mark (ـ  -  --  …  ..): المصـ-- for المصاري.
               A wanted Latin fragment ("تنتين و ro--") must be kept as a fragment (any script), never completed.
  spelling_ok  the final enclitic ـه / ـو of the same word is one spelling: بده = بدو. ONLY that one equivalence:
               never the article ال, never any other letter (ة and ا are not ه).
  both         either relaxation.

A run that bench_score calls a hidden slip or an error is never turned into a hit by a side column.

    python scripts/bench_side.py 2026-10-02      # variables/side-columns.json + side-columns.md (and the table printed)
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402

BASE = "gemini-flash-t1"
MIN_PREFIX, MIN_STEM = 3, 2
_FRAG = {"r": "ر", "o": "و", "u": "و", "a": "ا", "i": "ي", "e": "ي", "b": "ب", "t": "ت", "d": "د", "s": "س", "k": "ك", "l": "ل", "m": "م", "n": "ن", "h": "ه", "w": "و", "y": "ي", "z": "ز", "f": "ف", "j": "ج"}
_PIECE = re.compile(r"[0-9A-Za-zء-ْ٠-٩ٰکگی'’`]+")      # the pieces bench_common.tokens keeps
_BREAK_AFTER = re.compile(r"(-+|–+|—+|…|\.{2,})(?![0-9A-Za-zء-ي])")              # a break mark right after the piece
_HARAKAT = re.compile("[ً-ْٰ]")
ENCLITIC = {"ه", "و"}


def _plain(piece):
    """Letters of one piece, folded like the normaliser but WITHOUT its alias table and its final ه -> ا fold (a cut-off
    prefix is not a whole word, and the ending rule needs the real last letter)."""
    return re.sub("[^0-9a-zء-ي]", "", BC.DIAC.sub("", piece).translate(BC._MAP).lower())


def _last_raw(piece):
    """The last letter as written (before any folding): ة stays ة, so it is never taken for the enclitic ه."""
    s = re.sub("[^ء-يکگی]", "", BC.DIAC.sub("", piece))
    return s[-1:] if s else ""


def pieces(text):
    """The words of a line as bench_common.tokens sees them, before the lone-و gluing, each with what the normaliser
    throws away: {"tok" (normalised), "plain", "last", "cut" (a break mark follows / a final tatweel)}."""
    out = []
    text = text or ""
    for m in _PIECE.finditer(text):
        raw = m.group(0)
        tok = BC.norm_token(raw)
        if not tok or BC.AR_FILLER.match(tok) or tok in BC.LAT_FILLER:
            continue
        cut = _HARAKAT.sub("", raw).endswith("ـ") or bool(_BREAK_AFTER.match(text, m.end()))
        out.append({"tok": tok, "plain": _plain(raw), "last": _last_raw(raw), "cut": cut})
    return out


def glued(ps):
    """The same list after bench_common.tokens' lone-و rule (و + the next Arabic piece = one token)."""
    out = [dict(p) for p in ps]
    k = 0
    while k < len(out) - 1:
        if out[k]["tok"] == "و" and BC.AR_LETTER.search(out[k + 1]["tok"]):
            b = out[k + 1]
            out[k:k + 2] = [{"tok": "و" + b["tok"], "plain": "و" + b["plain"], "last": b["last"], "cut": b["cut"]}]
        k += 1
    return out


def is_cut_prefix(want, have):
    """`have` is a break-marked Arabic prefix (3+ letters, shorter than the word) of the wanted word."""
    p = have["plain"]
    stem = p[2:] if p.startswith("ال") else p                       # the article alone tells nothing about the word
    return bool(have["cut"] and BC.is_ar(have["tok"]) and MIN_PREFIX <= len(p) < len(want["plain"]) and len(stem) >= MIN_STEM
                and want["plain"].startswith(p))


def same_enclitic(want, have):
    """The same word with its final ـه written ـو or the other way round - nothing else differs."""
    a, b = want["plain"], have["plain"]
    return bool(len(a) >= 3 and len(a) == len(b) and a[:-1] == b[:-1] and BC.is_ar(a) and BC.is_ar(b)
                and {want["last"], have["last"]} == ENCLITIC)


def _eq(want, have, cutoff, spelling):
    return BC.tok_eq(want["tok"], have["tok"]) or (cutoff and is_cut_prefix(want, have)) or (spelling and same_enclitic(want, have))


def _find(seq, toks, cutoff, spelling):
    n = len(seq)
    return bool(n) and any(all(_eq(seq[j], toks[k + j], cutoff, spelling) for j in range(n)) for k in range(len(toks) - n + 1))


def alts(want, conv=BC.latin_to_arabic):
    """bench_score._alts with the pieces kept: [(pieces, fragment or None)]. fragment = the truth's own broken-off Latin
    piece after its Arabic words ("تنتين و ro--" -> ro)."""
    out = []
    for w in want:
        ps = pieces(w)
        if any(BC.is_ar(p["tok"]) for p in ps):
            frag = ps[-1] if (not BC.is_ar(ps[-1]["tok"]) and ps[-1]["cut"]) else None
            out.append(([p for p in glued(ps) if BC.is_ar(p["tok"])], [p for p in ps if BC.is_ar(p["tok"])] if frag else None, frag))
        elif ps:
            out.append((glued(ps), None, None))
            c = [p for p in glued(pieces(conv(w))) if BC.is_ar(p["tok"])]
            if c:
                out.append((c, None, None))
    return out


def kept_fragment(arabic, frag, text):
    """The truth's Arabic words, then its broken-off piece KEPT as a broken-off piece (same sound, a break mark after
    it; Arabic or Latin letters) - not finished into a word. Read on the unglued pieces, so a faithful 'و رو--' counts."""
    ps = pieces(text)
    n = len(arabic)
    want = BC.skel(frag["tok"])
    for k in range(len(ps) - n):
        if all(BC.tok_eq(arabic[j]["tok"], ps[k + j]["tok"]) for j in range(n)):
            h = ps[k + n]
            if h["cut"] and want and BC.skel(h["tok"]) == want:
                return True
    return False


def has_want_side(m, text, cutoff=False, spelling=False, conv=BC.latin_to_arabic, truth_line=""):
    """bench_score.has_want on the listener's text field, with the two relaxations switched on or off. With both off it
    is bench_score.has_want(m, text, "") (asserted over every saved run in main)."""
    text = text or ""
    if BS.has_gone(m, text, truth_line):
        return False
    raw = glued(pieces(text))
    cv = glued(pieces(conv(text))) if re.search("[A-Za-z]", text) else raw
    for seq, arabic, frag in alts(m["want"], conv):
        if _find(seq, raw, cutoff, spelling) or _find(seq, cv, cutoff, spelling):
            return True
        if cutoff and frag is not None and kept_fragment(arabic, frag, text):
            return True
    return False


def side(truth, runs, conv=BC.latin_to_arabic):
    """One engine. runs = [{line_i: {"text", "alt"?}}]. Returns the four counts and which moments each column adds."""
    s = BS.score(truth, runs, conv=conv)
    lines = {ln["i"]: ln for ln in truth["lines"]}
    mom = {m["id"]: m for m in truth["moments"]}
    cols = {"cutoff_ok": (True, False), "spelling_ok": (False, True), "both": (True, True)}
    hit = {c: [] for c in cols}
    once = 0
    for p in s["per_moment"]:
        m = mom[p["id"]]
        tl = lines[m["i"]]["truth"]
        once += any(v == "hit" for v in p["runs"])
        for c, (cut, sp) in cols.items():
            n = sum(1 for v, text in zip(p["runs"], p["heard"])
                    if v == "hit" or (v not in ("hidden-slip", "error") and has_want_side(m, text, cut, sp, conv, tl)))
            if n * 2 > len(p["runs"]):
                hit[c].append(p["id"])
    strict = [p["id"] for p in s["per_moment"] if p["final"] == "hit"]
    assert len(strict) == s["hit"], "strict must be bench_score's own number"
    out = {"runs": len(runs), "moments": s["moments"], "strict": s["hit"], "at_least_once": once, "hidden_slips": s["hidden_slips"]}
    for c in cols:
        assert set(strict) <= set(hit[c])
        out[c] = len(hit[c])
        out[c + "_adds"] = sorted(set(hit[c]) - set(strict))
    return out


def strict_agrees(truth, runs, conv=BC.latin_to_arabic):
    """Self-check: with both relaxations off, this file's matcher gives bench_score.has_want's answer on every moment
    of every run (text field). Returns the disagreements (must be empty)."""
    lines = {ln["i"]: ln for ln in truth["lines"]}
    bad = []
    for m in truth["moments"]:
        ln = lines[m["i"]]
        for n, run in enumerate(runs):
            o = run.get(str(m["i"]))
            text = ln["engine"] if o is None else (o.get("text") or "")
            if has_want_side(m, text, False, False, conv, ln["truth"]) != BS.has_want(m, text, "", conv, ln["truth"]):
                bad.append((m["id"], n + 1, text))
            assert [p["tok"] for p in glued(pieces(text))] == BC.tokens(text), text
    return bad


def trap_note(truth, all_runs, conv=BC.latin_to_arabic):
    """The scorer trap at a truth like 'تنتين و ro--' (M020): bench_common.tokens glues a lone و to the next Arabic
    piece, so a faithful Arabic cut-off scores a miss, while the same words finished in Latin letters score a hit.
    Reported, never patched. all_runs = {engine: runs}."""
    lines = {ln["i"]: ln for ln in truth["lines"]}
    notes = []
    for m in truth["moments"]:
        for w in m["want"]:
            ps = pieces(w)
            ar = [p for p in ps if BC.is_ar(p["tok"])]
            if not ar or ar[-1]["tok"] != "و" or BC.is_ar(ps[-1]["tok"]) or not ps[-1]["cut"]:
                continue
            frag = ps[-1]["tok"]
            stem = " ".join(x for x in re.split(r"\s+", w)[:-1])
            faithful = "%s %s--" % (stem, "".join(_FRAG.get(c, "") for c in frag) or frag)                 # the same words, the fragment in Arabic letters
            finished = "%s %sb3" % (stem, frag)                                       # the fragment finished into a word, Latin letters
            tl = lines[m["i"]]["truth"]
            kept = total = 0
            for e, runs in all_runs.items():
                for run in runs:
                    o = run.get(str(m["i"]))
                    if o is None:
                        continue
                    total += 1
                    kept += kept_fragment(ar, ps[-1], o.get("text") or "")
            notes.append({"moment": m["id"], "want": w,
                          "faithful_arabic_cutoff": faithful, "strict_scores_it": BS.has_want(m, faithful, "", conv, tl),
                          "cutoff_column_scores_it": has_want_side(m, faithful, True, False, conv, tl),
                          "finished_in_latin": finished, "strict_scores_finished": BS.has_want(m, finished, "", conv, tl),
                          "cutoff_column_adds_nothing_for_finished": not kept_fragment(ar, ps[-1], finished),
                          "runs_that_kept_the_fragment": kept, "runs_looked_at": total,
                          "why": "bench_common.tokens glues a lone و to the next Arabic piece (و + رو = ورو), so the truth's "
                                 "'... و' is found only when Latin letters or nothing follow the و; and the Latin fragment itself is "
                                 "not required, so a finished Latin word still scores. Not patched: the normaliser is frozen."})
    return notes


def table(rows):
    out = ["| Engine | Runs | Strict | + cut-off | + ending (ه = و) | + both | At least 1 run | Cut-off adds | Ending adds |",
           "|---|---|---|---|---|---|---|---|---|"]
    for e, r in rows:
        out.append("| %s | %d | %d | %d | %d | %d | %d | %s | %s |" % (
            e + (" (baseline)" if e == BASE else ""), r["runs"], r["strict"], r["cutoff_ok"], r["spelling_ok"], r["both"], r["at_least_once"],
            " ".join(r["cutoff_ok_adds"]) or "-", " ".join(r["spelling_ok_adds"]) or "-"))
    return "\n".join(out)


def main(argv):
    date = argv[0]
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    man = BC.J(os.path.join(d, "manifest.json"))
    if BC.sha_file(os.path.join(d, "truth.json")) != man["truth_sha256"]:
        raise SystemExit("truth.json does not match the manifest")
    published = BC.J(os.path.join(d, "scores.json")) or {}
    engines = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and x not in ("clips", "scratch", "runs", "vowel", "b"))
    res, all_runs = {}, {}
    for e in engines:
        runs = [r["lines"] for r in BS.load_runs(d, e, "line")]
        if not runs:
            continue
        bad = strict_agrees(truth, runs)
        assert not bad, "the side matcher with no relaxation disagrees with bench_score on %s: %s" % (e, bad[:3])
        r = side(truth, runs)
        pub = published.get(e + "|line")
        if pub is not None:
            assert pub["hit"] == r["strict"], "%s: strict %d is not the published %d" % (e, r["strict"], pub["hit"])
        r["matches_scores_json"] = pub is not None
        res[e], all_runs[e] = r, runs
    order = sorted(res, key=lambda e: (e != BASE, -res[e]["both"], -res[e]["strict"], e))
    notes = trap_note(truth, all_runs)
    BC.W(os.path.join(d, "variables", "side-columns.json"),
         {"date": date, "truth_sha256": man["truth_sha256"], "scorer_sha256": BC.sha_file(os.path.join(HERE, "bench_score.py")),
          "normaliser_sha256": BC.sha_file(os.path.join(HERE, "bench_common.py")), "headline": "strict (the side columns are never the headline)",
          "rule": {"cutoff_ok": "an Arabic prefix of the wanted word (3+ letters, 2+ after a leading ال) followed by a break mark; a wanted Latin fragment kept as a fragment",
                   "spelling_ok": "final enclitic ه = و on the same word, nothing else", "vote": "2 of 3 runs"},
          "engines": {e: res[e] for e in order}, "scorer_trap": notes})
    md = ["# Side columns for scoreboard A (%s)" % date, "",
          "Strict is the headline and is bench_score's own number (asserted). The other columns use the same runs, the same key and the same 2-of-3 rule.",
          "", table([(e, res[e]) for e in order]), "", "## Scorer trap (reported, not patched)", ""]
    for n in notes:
        md.append("- %s, truth `%s`: a faithful Arabic cut-off `%s` scores %s under the strict scorer (%s in the cut-off column); the fragment finished "
                  "in Latin letters `%s` scores %s under the strict scorer. %d of %d saved runs kept the fragment. %s" % (
                      n["moment"], n["want"], n["faithful_arabic_cutoff"], "a hit" if n["strict_scores_it"] else "a MISS",
                      "a hit" if n["cutoff_column_scores_it"] else "a miss", n["finished_in_latin"],
                      "a HIT" if n["strict_scores_finished"] else "a miss", n["runs_that_kept_the_fragment"], n["runs_looked_at"], n["why"]))
    md = "\n".join(md) + "\n"
    with open(os.path.join(d, "variables", "side-columns.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
