# -*- coding: utf-8 -*-
"""The benchmark scorer (PR-18). Pure: text in, verdicts out; no network, no clock, no file writes in the scoring
functions (the CLI at the bottom only reads the frozen truth and the engines' raw run files and prints / writes the table).

Scoreboard A - words heard right, per answer-key moment (spec 5):
  hit          the truth word(s) are in the engine's text for that line (whole-file mode: or the line before / after)
  miss-engine  the engine wrote the same wrong word ElevenLabs wrote (a `gone` word is there, or the line equals the raw line)
  miss-other   another wrong word, or nothing
  hidden-slip  the engine wrote Amal's CORRECT form where Medi's truth is his slip (worst fault)
  error        the call failed (recorded as a miss with the error)
A moment counts for A only when 2 of 3 runs hit. Separately: false changes on the should-stay lines, all-lines word
recall, language switches (TR-25), speaker bleed, stability.

    python scripts/bench_score.py 2026-10-02                 # every engine dir with run files -> scores.json + table
"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402

DONE_AT_ONCE = ("eleven-raw", "cohere-open", "audar-open", "audar-open-ar")     # their run file is written once, when the run ends
VERDICTS = ("hit", "miss-engine", "miss-other", "hidden-slip", "error")


def views(text, conv=BC.latin_to_arabic):
    """(raw tokens, tokens with Latin-letter Arabic read as Arabic)."""
    raw = BC.tokens(text)
    return raw, (BC.tokens(conv(text)) if re.search("[A-Za-z]", text or "") else raw)


def find_seq(seq, toks):
    """Is the word sequence in the token list, in order and adjacent? Whole words only (no substring credit:
    عشر is not in عشرين)."""
    n = len(seq)
    return bool(n) and any(all(BC.tok_eq(seq[j], toks[k + j]) for j in range(n)) for k in range(len(toks) - n + 1))


def _alts(want, conv):
    """[(tokens, latin?)] - each accepted variant of the truth; a Latin-letter truth (a vowel-level fix: nafs el-ishi,
    5otatet) also matches its Arabic script."""
    out = []
    for w in want:
        t = BC.tokens(w)
        if any(BC.is_ar(x) for x in t):
            out.append(([x for x in t if BC.is_ar(x)], False))   # a broken-off Latin piece ("ro--") is not required
        elif t:
            out.append((t, True))
            c = [x for x in BC.tokens(conv(w)) if BC.is_ar(x)]
            if c:
                out.append((c, False))
    return out


def count_seq(seq, toks):
    n = len(seq)
    return sum(1 for k in range(len(toks) - n + 1) if all(BC.tok_eq(seq[j], toks[k + j]) for j in range(n))) if n else 0


def has_gone(m, text, truth_line=""):
    """The rejected word (what ElevenLabs wrote and Medi corrected) is still there - more often than in the truth line
    itself (10-02 42:08: he fixed the first 'awwal' of a line and left the second)."""
    raw, tr = BC.tokens(text or ""), BC.tokens(truth_line or "")
    return any(count_seq(BC.tokens(g), raw) > count_seq(BC.tokens(g), tr) for g in m.get("gone") or [])


def has_want(m, text, alt="", conv=BC.latin_to_arabic, truth_line=""):
    """The truth word(s) in the engine's text, and the rejected word gone from that same field. The second field of a
    listener (its Arabizi) is read ONLY for a truth that is itself in Latin letters (a vowel-level fix), and then the
    veto runs on that field: a listener gets no second chance on an Arabic word, and its Arabizi echo cannot veto a
    right Arabic answer."""
    raw, cv = views(text or "", conv)
    if not has_gone(m, text, truth_line):
        for a, latin in _alts(m["want"], conv):
            if find_seq(a, raw) or find_seq(a, cv):
                return True
    if alt and not has_gone(m, alt, truth_line):
        for a, latin in _alts(m["want"], conv):
            if latin and find_seq(a, BC.tokens(alt)):
                return True
    return False


def _set(text, conv):
    raw, cv = views(text, conv)
    return set(raw) | set(cv)


def slip_hidden(slip, truth_line, text, conv=BC.latin_to_arabic):
    """Did the engine write Amal's right form where he said the wrong one? None = cannot be judged from text (the right
    form adds no word the truth line lacks)."""
    truth = _set(truth_line, conv)
    eng = _set(text, conv)
    wrong = _set(re.sub(r"\([^)]*\)", " ", slip["wrong"]), conv)
    judged = False
    for alt in re.split(r"\s*/\s*", re.sub(r"\([^)]*\)", " ", slip["right"])):
        right = _set(alt, conv)
        right_d = right - truth
        if not right_d:
            continue
        judged = True
        wrong_d = (wrong - right) & truth
        if right_d <= eng and not (wrong_d and wrong_d <= eng):
            return True
    return False if judged else None


def score_moment(m, out, neighbours=(), engine_line="", slip=None, truth_line="", conv=BC.latin_to_arabic):
    """One moment, one run. out = {"text", "alt"?, "error"?} or None (the line was not sent: the raw engine text stands)."""
    if out is None:
        out = {"text": engine_line}
    if out.get("error") and not out.get("text"):
        return "error"
    text, alt = out.get("text") or "", out.get("alt") or ""
    if slip is not None and slip_hidden(slip, truth_line, text, conv):
        return "hidden-slip"
    if has_want(m, text, alt, conv, truth_line) or (not has_gone(m, text, truth_line) and any(has_want(m, n, "", conv) for n in neighbours)):
        return "hit"
    if has_gone(m, text, truth_line) or BC.tokens(text) == BC.tokens(engine_line):
        return "miss-engine"
    return "miss-other"


def consensus(verdicts):
    """3 runs -> the verdict that counts: 2 of 3 agree, else 'unstable' (a miss)."""
    v, n = collections.Counter(verdicts).most_common(1)[0]
    return v if n * 2 > len(verdicts) else "unstable"


def line_words(truth_text, text, conv=BC.latin_to_arabic):
    """(truth Arabic words, how many the engine has, engine Arabic words that are not in the truth line). Each engine
    word is used once (truth غير غير needs two)."""
    want = [t for t in BC.tokens(truth_text) if BC.is_ar(t)]
    raw, cv = views(text, conv)
    pool = collections.Counter(raw)
    for t, n in collections.Counter(cv).items():
        pool[t] = max(pool[t], n)
    found = 0
    for w in want:
        k = next((h for h in pool if pool[h] > 0 and BC.tok_eq(w, h)), None)
        if k is not None:
            pool[k] -= 1
            found += 1
    left = collections.Counter(want)
    extra = []
    for h in raw:
        if not BC.is_ar(h):
            continue
        k = next((w for w in left if left[w] > 0 and BC.tok_eq(h, w)), None)
        if k is None:
            extra.append(h)
        else:
            left[k] -= 1
    return len(want), found, extra


def content_change(truth_text, text, conv=BC.latin_to_arabic):
    """Is the line changed in its WORDS, not only in its script? A truth Arabic word the engine wrote in Latin letters
    (or a Latin-letter Arabic word of the truth the engine wrote in Arabic script) is the same word by sound."""
    w, f, extra = line_words(truth_text, text, conv)
    t_raw, e_raw = BC.tokens(truth_text), BC.tokens(text)
    t_lat = [x for x in t_raw if not BC.is_ar(x) and not x.isdigit()]
    e_lat = [x for x in e_raw if not BC.is_ar(x) and not x.isdigit()]
    extra = [x for x in extra if not any(BC.same_sound(x, y) for y in t_lat)]
    missing = 0
    if f < w:
        raw, cv = views(text, conv)
        have = raw + cv
        for x in [t for t in t_raw if BC.is_ar(t)]:
            if not any(BC.tok_eq(x, h) for h in have) and not any(BC.same_sound(x, y) for y in e_lat):
                missing += 1
    return bool(missing or extra)


def bleed(extra, line, amal_all):
    """Extra words on his line that Amal said within 2 s of it."""
    near = set()
    for a in amal_all:
        if a["t"] <= line["end"] + 2 and a["end"] >= line["t"] - 2:
            near |= set(BC.tokens(a["text"]))
    return [w for w in extra if w in near]


def majority_text(outs):
    """The text 2 of 3 runs agree on (normalised), else run 1's - used for the all-lines numbers and scoreboard B."""
    keys = [" ".join(BC.tokens((o or {}).get("text") or "")) for o in outs]
    k, n = collections.Counter(keys).most_common(1)[0]
    if n * 2 > len(outs):
        return outs[keys.index(k)], True
    return outs[0], len(outs) == 1


def score(truth, runs, whole_file=False, conv=BC.latin_to_arabic, who="Medi"):
    """truth = truth.json; runs = [{line_i(str): {"text", "alt"?, "error"?}}] (1-3 runs of one engine in one mode).
    A line missing from a run was not sent to the engine: the raw engine text stands there (listeners skip long English)."""
    lines = {ln["i"]: ln for ln in truth["lines"]}
    order = sorted(lines)
    pos = {i: k for k, i in enumerate(order)}
    slip_of = {}
    for s in truth.get("slips") or []:
        slip_of.setdefault(s["i"], s)

    def out_of(run, i):
        o = run.get(str(i))
        return o if o is not None else None

    def text_of(run, i):
        o = out_of(run, i)
        return lines[i]["engine"] if o is None else (o.get("text") or "")

    # ---- A: the moments
    per, final = [], collections.Counter()
    by_class = collections.defaultdict(lambda: [0, 0])
    for m in truth["moments"]:
        ln = lines[m["i"]]
        vs = []
        for run in runs:
            nb = ()
            if whole_file:
                k = pos[m["i"]]
                # the line before / after counts only when its own truth lacks the word (the word slid across the
                # line break); a neighbour that says the word anyway is no evidence for this line
                nb = [text_of(run, order[j]) for j in (k - 1, k + 1) if 0 <= j < len(order) and not has_want(m, lines[order[j]]["truth"], "", conv)]
            vs.append(score_moment(m, out_of(run, m["i"]), nb, ln["engine"], slip_of.get(m["i"]) if m["class"] == "kept-slip" else None, ln["truth"], conv))
        c = consensus(vs)
        final[c] += 1
        by_class[m["class"]][1] += 1
        by_class[m["class"]][0] += c == "hit"
        per.append({"id": m["id"], "t": m["t"], "class": m["class"], "runs": vs, "final": c,
                    "heard": [text_of(run, m["i"]) for run in runs]})
    n = len(truth["moments"])

    # ---- hidden slips over every published slip of the lesson
    hid, judged, hid_rows = 0, 0, []
    for s in truth.get("slips") or []:
        ln = lines[s["i"]]
        vs = [slip_hidden(s, ln["truth"], text_of(run, s["i"]), conv) for run in runs]
        if vs[0] is None:
            continue
        judged += 1
        if sum(bool(v) for v in vs) * 2 > len(vs):
            hid += 1
            hid_rows.append({"t": s["t"], "wrong": s["wrong"], "right": s["right"], "heard": text_of(runs[0], s["i"])})

    # ---- all lines: word recall, false changes on the should-stay set, language switch, bleed, run agreement
    tot = found = stay = changed = content = switch = agree = sent = extra_n = bleed_n = errors = 0
    changed_rows = []
    for i in order:
        ln = lines[i]
        outs = [out_of(run, i) for run in runs]
        if all(x is None for x in outs):
            o, ok = {"text": ln["engine"]}, True
        else:
            sent += 1
            o, ok = majority_text([x if x is not None else {"text": ln["engine"]} for x in outs])   # a run that lacks the line = the raw text there
            agree += ok
            errors += sum(1 for x in outs if x and x.get("error"))
        text = o.get("text") or ""
        w, f, extra = line_words(ln["truth"], text, conv)
        tot += w
        found += f
        extra_n += len(extra)
        switch += BC.has_foreign(text)
        bleed_n += len(bleed(extra, ln, truth.get("amal_all") or []))
        if ln["should_stay"]:
            stay += 1
            content += content_change(ln["truth"], text, conv)
            if f < w or extra:
                changed += 1
                if len(changed_rows) < 400:
                    changed_rows.append({"t": ln["t"], "truth": ln["truth"], "heard": text, "missing": w - f, "extra": extra})
    return {"moments": n, "hit": final["hit"], "hit_pct": round(100.0 * final["hit"] / n, 1) if n else None,
            "verdicts": dict(final), "by_class": {k: v for k, v in sorted(by_class.items())},
            "stable_pct": round(100.0 * sum(1 for p in per if len(set(p["runs"])) == 1) / n, 1) if n else None,
            "hidden_slips": hid, "slips_judged": judged, "hidden_rows": hid_rows,
            "should_stay": stay, "false_changes": changed, "false_change_pct": round(100.0 * changed / stay, 1) if stay else None,
            "content_changes": content, "content_change_pct": round(100.0 * content / stay, 1) if stay else None,
            "arabic_words": tot, "arabic_words_heard": found, "all_lines_pct": round(100.0 * found / tot, 1) if tot else None,
            "extra_arabic_words": extra_n, "language_switch_lines": switch, "bleed_words": bleed_n,
            "lines_sent": sent, "lines_2of3_agree_pct": round(100.0 * agree / sent, 1) if sent else None, "call_errors": errors,
            "runs": len(runs), "per_moment": per, "false_change_rows": changed_rows}


def score_amal(truth, runs, conv=BC.latin_to_arabic):
    """The Amal-line fixes (6 on 10-02): hit / miss only."""
    lines = {ln["i"]: ln for ln in truth.get("amal_lines") or []}
    per, hits = [], 0
    for m in truth.get("amal_moments") or []:
        vs = [score_moment(m, run.get("A%d" % m["i"]), (), lines[m["i"]]["engine"], None, lines[m["i"]]["truth"], conv) if run.get("A%d" % m["i"]) is not None else "error" for run in runs]
        c = consensus(vs)
        hits += c == "hit"
        per.append({"id": m["id"], "runs": vs, "final": c})
    return {"moments": len(per), "hit": hits, "per_moment": per}


# ------------------------------------------------------------------ CLI (reads the frozen files)

def load_runs(d, engine, mode):
    runs = []
    for n in (1, 2, 3):
        r = BC.J(os.path.join(d, engine, "%s-run%d.json" % (mode, n)))
        if r and (r.get("complete") is True or ("complete" not in r and "seconds" in r and engine in DONE_AT_ONCE)):   # a run in progress is never scored
            runs.append(r)
    return runs


def main(argv):
    date = argv[0]
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    man = BC.J(os.path.join(d, "manifest.json"))
    if BC.sha_file(os.path.join(d, "truth.json")) != man["truth_sha256"]:
        raise SystemExit("truth.json does not match the manifest: the key was edited after the freeze")
    code = (BC.sha_file(os.path.abspath(__file__)), BC.sha_file(os.path.join(HERE, "bench_common.py")))
    if code != (man.get("scorer_sha256"), man.get("normaliser_sha256")):
        print("NOTE: the scorer / normaliser changed since the freeze - every engine is re-scored with this one version: %s / %s" % (code[0][:12], code[1][:12]))
    engines = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and x not in ("clips", "scratch", "runs", "vowel", "b"))
    scores = {}                                    # always every engine, one scorer version (never a mix)
    for e in engines:
        for mode in ("line", "whole"):
            runs = load_runs(d, e, mode)
            if not runs:
                continue
            s = score(truth, [r["lines"] for r in runs], whole_file=(mode == "whole"))
            s["scorer_sha256"], s["normaliser_sha256"] = code
            s["amal"] = score_amal(truth, [r["lines"] for r in runs])
            s.update(model=runs[0].get("model"), cost_usd=round(sum(r.get("cost_usd") or 0 for r in runs), 4),
                     seconds=[round(r.get("seconds") or 0, 1) for r in runs], truth_sha256=man["truth_sha256"])
            scores["%s|%s" % (e, mode)] = s
            print("%-22s %-5s A %2d/%d (%s%%) hidden %d/%d  changed %d/%d (%s%%) words-changed %d  all-lines %s%%  switch %d  stable %s%%  runs %d  $%.2f" % (
                e, mode, s["hit"], s["moments"], s["hit_pct"], s["hidden_slips"], s["slips_judged"], s["false_changes"], s["should_stay"],
                s["false_change_pct"], s["content_changes"], s["all_lines_pct"], s["language_switch_lines"], s["stable_pct"], s["runs"], s["cost_usd"]))
    BC.W(os.path.join(d, "scores.json"), scores)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
