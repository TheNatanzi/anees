# -*- coding: utf-8 -*-
"""Gemini's re-heard words into the lesson transcript, as OVERLAY rows (RULES.md S2: the engine's text is never edited;
TR-18 overlay, TR-22 re-hear; overnight backfill spec 2026-10-04, Phase 3 - Medi: "Dont throw away the eleven data but
lets replace it").

    python scripts/rehear_apply.py plan [dates]      # rehear/<date>/apply-plan.json: the rows, his corrections checked, the lists (no change to the lesson)
    python scripts/rehear_apply.py apply [dates]     # the plan's rows into data/lesson-work/transcript-fixes.json (by: gemini-rehear), status -> applied
    python scripts/rehear_apply.py unapply [dates]   # takes this job's rows out again (a row of anyone else is never touched)
    python scripts/rehear_apply.py check             # every gemini-rehear row lands on its page line and gives the planned text

What goes in: only the PROPOSED pile of scripts/rehear_lesson.py (2 of 3 runs agree on the line or the span; held lines
released by the two-clip check). What never goes in: a held line, a line with no agreement, a word change on a line cut
from a mixed recording - those are listed for Medi.
His own corrections stay (decision 2): a line that already carries an overlay row (his, or an earlier reader's) gets NO
Gemini row. Each of his corrections is compared with the 3 runs; where none of the 3 wrote his word the moment goes on
the listen page for him - nothing of his is overwritten.
A row is as SMALL as the change: one row per changed stretch of words (the engine's other words on the line are not
named, so a stored word score on an unchanged word is not thrown out by the TR-18 override in lesson_ledger).
"""
import difflib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402
import rehear_lesson as RL  # noqa: E402
import rehear_status as RS  # noqa: E402
import transcript_fixes as TF  # noqa: E402

BY = "gemini-rehear"
RULE = "TR-22"


def key(w):
    return " ".join(BC.tokens(w, fillers=True))


def span_rows(engine, heard):
    """The smallest overlay rows that turn the engine's line into the heard line: [{"engine_wrote", "heard"} or
    {"engine_wrote": "", "heard", "insert_after"}]. Punctuation and letter case of unchanged words stay the engine's.
    None when the rows, applied the way transcript_fixes.apply applies them, do not give the heard words (then one
    whole-line row is used)."""
    E = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", engine)]
    H = heard.split()
    ek, hk = [key(w[0]) for w in E], [key(w) for w in H]
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ek, hk, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        new = " ".join(H[j1:j2])
        if i2 > i1:
            rows.append({"engine_wrote": engine[E[i1][1]:E[i2 - 1][2]], "heard": new})
        elif i1 > 0:                                              # words the engine dropped: after the word before them
            rows.append({"engine_wrote": "", "heard": new, "insert_after": E[i1 - 1][0]})
        elif E:                                                   # ... at the very start: with the first word
            rows.append({"engine_wrote": E[0][0], "heard": new + " " + E[0][0]})
        else:
            return None
    return rows if simulate(engine, rows) is not None and BC.tokens(simulate(engine, rows), fillers=True) == BC.tokens(heard, fillers=True) else None


def simulate(text, rows):
    """The text after the rows, by the rules of transcript_fixes.apply (first occurrence; insert after the first `after`).
    None when a row does not land."""
    for r in rows:
        if not r["engine_wrote"]:
            a = r.get("insert_after") or ""
            i = text.find(a) if a else -1
            if i < 0:
                return None
            text = text[:i + len(a)] + " " + r["heard"] + text[i + len(a):]
        elif r["engine_wrote"] in text:
            text = text.replace(r["engine_wrote"], r["heard"], 1)
        else:
            return None
    return text


def says(text, alt, phrase):
    """Is `phrase` (a correction's heard words) in a run's line - as written, or through the Arabizi echo / the other alphabet?"""
    want = BC.tokens(phrase)
    if not want:
        return True
    for view in (text or "", BC.latin_to_arabic(text or ""), alt or "", BC.latin_to_arabic(alt or "")):
        toks = BC.tokens(view)
        if any(all(BC.tok_eq(toks[k + n], want[n]) for n in range(len(want))) for k in range(len(toks) - len(want) + 1)):
            return True
    return False


def mmss(t):
    return "%02d:%02d" % (int(t) // 60, int(t) % 60)


def plan(date):
    d, man, lines, amal, prompts = RL.load(date)
    P = BC.J(os.path.join(d, "proposals.json"))
    if not P:
        raise SystemExit("%s: no proposals.json" % date)
    turns = RL.page_turns(date)
    by_i = {ln["i"]: ln for ln in lines}
    runs = [BC.J(RL.run_path(d, "base", n))["lines"] for n in (1, 2, 3)]
    fixes = [r for r in (BC.J(TF.FIXES_P) or {}).get("rows", []) if str(r.get("date")) == date and r.get("by") != BY]
    try:
        import medi_corrections as MC
        fixes += [dict(r, by="medi") for r in MC.text_rows() if str(r.get("date")) == date]
    except Exception as e:  # noqa: BLE001
        print("page corrections not read:", type(e).__name__)

    def turn_of(row):
        u = turns[row["i"]] if row["i"] < len(turns) else None
        if u and u["who"] == "Medi" and abs(u["t"] - row["t"]) < 0.01 and RL.raw(u) == row["engine"]:
            return u
        return None

    out = {"date": date, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": [], "lines_changed": [], "whole_line_rows": 0, "kept_overlay": [], "his_corrections": [],
           "listen": [], "held": [], "held_mix": [], "no_agreement": [], "skipped": []}
    for r in P["rows"]:
        base = {"i": r["i"], "t": r["t"], "mmss": mmss(r["t"]), "engine": r["engine"], "runs": r["runs"]}
        if r["status"] == "held":
            out["held"].append(dict(base, heard=r["heard"], her_words=r.get("amal_next"), two_clip=r.get("two_clip")))
            continue
        if r["status"] == "held-mix":
            out["held_mix"].append(dict(base, heard=r["heard"]))
            continue
        if r["status"] != "proposed":
            out["no_agreement"].append(base)
            continue
        u = turn_of(r)
        if u is None:
            out["skipped"].append(dict(base, why="the page line changed since the freeze"))
            continue
        if not (r["heard"] or "").strip() or not BC.tokens(r["heard"], fillers=True):
            out["skipped"].append(dict(base, why="Gemini wrote an empty line; the engine's text stays"))
            continue
        if u.get("engine"):                                      # the line already carries a correction: it stays as it is
            out["kept_overlay"].append(dict(base, now=u["text"], gemini=r["heard"]))
            continue
        rows = span_rows(r["engine"], r["heard"])
        # transcript_fixes.apply gives a row to EVERY line of the speaker within a second of its time: when another of
        # his lines is that close, a small row could land on it too - then one whole-line row is used, and when even the
        # whole line is inside the neighbour's text the change is not applied (listed).
        near = [RL.raw(v) for v in turns if v is not u and v["who"] == "Medi" and abs(v["t"] - u["t"]) <= 1.0]
        if rows is not None and near and any((x["engine_wrote"] in n) if x["engine_wrote"] else True for x in rows for n in near):
            rows = None
        if rows is None:
            if any(r["engine"] in n for n in near):
                out["skipped"].append(dict(base, why="another of his lines starts within a second and holds the same words: a row could not name this line alone"))
                continue
            rows = [{"engine_wrote": r["engine"], "heard": r["heard"]}]
            out["whole_line_rows"] += 1
        how = "released by the two-clip check" if r.get("released") else ("2 of 3 runs agree on these words" if r["how"] == "spans" else "%d of 3 runs agree on the line" % r["agree"])
        for x in rows:
            out["rows"].append(dict({"date": date, "t": u["t"], "who": "Medi"}, **x, rule=RULE, by=BY, on=RS.today(), kind=r.get("kind"), how=how,
                                    why="Gemini 3.8 Flash re-heard his own microphone for this line with the lesson around it (3 runs; %s)" % how))
        out["lines_changed"].append(dict(base, heard=r["heard"], kind=r.get("kind"), how=how, src=by_i[r["i"]].get("src"), rows=len(rows)))
    # ---- his corrections against the 3 runs (every correction, also where Gemini agreed with the engine)
    for f in fixes:
        if f.get("who", "Medi") != "Medi" or not f.get("heard") or f.get("set_who") or f.get("set_t") is not None:
            continue
        cands = [k for k, u in enumerate(turns) if u["who"] == "Medi" and abs(float(f["t"]) - u["t"]) <= 1.0 and (f.get("engine_wrote") or "") in RL.raw(u)]
        if not cands:
            continue
        i = cands[0]
        outs = [run.get(str(i)) for run in runs]
        heard = [(o or {}).get("text") if o is not None else None for o in outs]
        agree = sum(1 for o in outs if o is not None and says(o.get("text"), o.get("alt"), f["heard"]))
        row = {"i": i, "t": turns[i]["t"], "mmss": mmss(turns[i]["t"]), "by": f.get("by"), "engine_wrote": f.get("engine_wrote"), "his": f["heard"], "engine_line": RL.raw(turns[i]),
               "line_now": turns[i]["text"], "runs": heard, "listened": sum(1 for o in outs if o is not None), "runs_with_his_word": agree}
        if f.get("by") == "medi":
            out["his_corrections"].append(row)
            if row["listened"] == 3 and agree == 0:
                out["listen"].append(dict(row, type="his-correction"))
        elif row["listened"] == 3 and agree == 0:
            out.setdefault("reader_rows_gemini_disagrees", []).append(row)
    out["summary"] = {"lines_changed": len(out["lines_changed"]), "rows": len(out["rows"]), "word_changes": sum(1 for x in out["lines_changed"] if x["kind"] == "words"),
                      "alphabet_only": sum(1 for x in out["lines_changed"] if x["kind"] == "alphabet"), "whole_line_rows": out["whole_line_rows"],
                      "lines_kept_because_already_corrected": len(out["kept_overlay"]),
                      "his_corrections": len(out["his_corrections"]), "his_corrections_gemini_heard_in_2_of_3": sum(1 for x in out["his_corrections"] if x["runs_with_his_word"] >= 2),
                      "his_corrections_all_3_runs_disagree": len(out["listen"]), "held": len(out["held"]), "held_mix": len(out["held_mix"]),
                      "no_agreement": len(out["no_agreement"]), "skipped": len(out["skipped"])}
    BC.W(os.path.join(d, "apply-plan.json"), out)
    print(date, json.dumps(out["summary"]), flush=True)
    return out


def _doc():
    with open(TF.FIXES_P, encoding="utf-8-sig") as f:
        return json.load(f)


def _save(doc):
    with open(TF.FIXES_P, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


def apply(ds):
    doc = _doc()
    for date in ds:
        P = BC.J(os.path.join(RL.ldir(date), "apply-plan.json"))
        if not P:
            raise SystemExit("%s: no apply-plan.json (run plan)" % date)
        doc["rows"] = [r for r in doc["rows"] if not (r.get("by") == BY and str(r.get("date")) == date)] + P["rows"]
    _save(doc)
    bad = check(ds)
    if bad:
        raise SystemExit("apply: %d rows do not land - nothing is marked applied" % len(bad))
    doc2 = RS.load()
    for date in ds:
        P = BC.J(os.path.join(RL.ldir(date), "apply-plan.json"))
        s = P["summary"]
        doc2["lessons"][date] = {"status": "applied", "since": RS.today(),
                                 "note": "Gemini's second listen changed %d of your lines (%d with a different word, %d only the alphabet); your own corrections stayed; %d lines are waiting for your ear." % (
                                     s["lines_changed"], s["word_changes"], s["alphabet_only"], s["held"] + s["held_mix"] + s["his_corrections_all_3_runs_disagree"])}
    RS.stamp_pages(RS.save(doc2))
    print("applied:", ", ".join(ds))


def unapply(ds):
    doc = _doc()
    n = len(doc["rows"])
    doc["rows"] = [r for r in doc["rows"] if not (r.get("by") == BY and str(r.get("date")) in ds)]
    _save(doc)
    print("removed %d rows of %s" % (n - len(doc["rows"]), BY))


def check(ds=None):
    """Every gemini-rehear row lands on its page line (same speaker, +-1 s, engine_wrote in the engine's line) and the
    line after all its rows holds the planned words. Returns the problems."""
    rows = [r for r in _doc()["rows"] if r.get("by") == BY and (not ds or str(r.get("date")) in ds)]
    bad, by_line = [], {}
    for r in rows:
        by_line.setdefault((r["date"], r["t"]), []).append(r)
    cache = {}
    for (date, t), rs in sorted(by_line.items()):
        if date not in cache:
            cache[date] = RL.page_turns(date)
        us = [u for u in cache[date] if u["who"] == "Medi" and abs(u["t"] - t) <= 1.0]
        if len(us) != 1:
            # two of his lines within a second: the row must name the right one by its engine text
            us = [u for u in us if all((r["engine_wrote"] or r.get("insert_after") or "") in RL.raw(u) for r in rs)]
        if len(us) != 1 or simulate(RL.raw(us[0]), rs) is None:
            bad.append({"date": date, "t": t, "rows": len(rs), "lines_in_reach": len(us)})
    return bad


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""
    ds = argv[1:] or RS.published()
    if cmd == "plan":
        for d in ds:
            plan(d)
    elif cmd == "apply":
        apply(ds)
    elif cmd == "unapply":
        unapply(ds)
    elif cmd == "check":
        bad = check(argv[1:] or None)
        for b in bad:
            print(b)
        print("rehear rows: %s" % ("OK" if not bad else "%d line(s) where the rows do not land" % len(bad)))
        sys.exit(1 if bad else 0)
    else:
        raise SystemExit(__doc__)
