# -*- coding: utf-8 -*-
"""Gemini's re-heard words into the lesson transcript, as OVERLAY rows (RULES.md S2: the engine's text is never edited;
TR-18 overlay, TR-22 re-hear; overnight backfill spec 2026-10-04, Phase 3 - Medi: "Dont throw away the eleven data but
lets replace it").

    python scripts/rehear_apply.py plan [dates]      # rehear/<date>/apply-plan.json: the rows, his corrections checked, the lists (no change to the lesson)
    python scripts/rehear_apply.py apply [dates]     # the plan's rows into data/lesson-work/transcript-fixes.json (by: gemini-rehear), status -> applied
    python scripts/rehear_apply.py unapply [dates]   # takes this job's rows out again (a row of anyone else is never touched), status back to proposed
    python scripts/rehear_apply.py check [dates]     # every gemini-rehear row lands on exactly its line and nothing else moves

What goes in: only the PROPOSED pile of scripts/rehear_lesson.py (2 of 3 runs agree on the line or the span; held lines
released by the two-clip check). What never goes in: a held line, a line with no agreement, a word change on a line cut
from a mixed recording - those are listed for Medi.
One row per changed LINE. The row names its line exactly (speaker, time, the engine's whole line letter for letter) and
carries the whole re-heard line plus its changed stretches ("spans": the engine's other words are not named, so a stored
word score on an unchanged word is not thrown out by the TR-18 override in lesson_ledger). transcript_fixes.apply puts
such a row only on a line that no correction of anyone lands on: his own corrections stay (decision 2), also one he
makes later.
Each of his corrections is compared with the 3 runs by the benchmark's own scorer (bench_score.score_moment); where none
of the 3 runs heard his word the moment goes on the listen page - nothing of his is overwritten.
Nothing is written unless the WHOLE overlay, run on the engine's lines with the new rows in it, changes exactly the
planned lines to exactly the planned text and no other line (Codex audit 2026-10-04).
"""
import copy, difflib, json, os, re, sys, time

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


def spans(engine, heard):
    """(the re-heard line built on the engine's own line, [{"engine_wrote", "heard"}]). Only the changed stretches are
    replaced, at their exact place; punctuation and letter case of unchanged words stay the engine's. A stretch is the
    engine's words that changed ("" when words were only added) and what was heard there ("" when words were dropped).
    (None, []) when no word differs after the normaliser."""
    E = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", engine)]
    H = heard.split()
    ops = [op for op in difflib.SequenceMatcher(None, [key(w[0]) for w in E], [key(w) for w in H], autojunk=False).get_opcodes() if op[0] != "equal"]
    if not ops:
        return None, []
    out, pos, sp = [], 0, []
    for tag, i1, i2, j1, j2 in ops:
        new = " ".join(H[j1:j2])
        a = E[i1][1] if i1 < len(E) else len(engine)
        b = E[i2 - 1][2] if i2 > i1 else a
        out.append(engine[pos:a])
        out.append((" " + new + " ") if i2 == i1 else new)       # words only added: before engine word i1 (or after the last word)
        pos = b
        sp.append({"engine_wrote": engine[a:b], "heard": new})
    out.append(engine[pos:])
    return re.sub(r"\s+", " ", "".join(out)).strip(), sp


def _views(out):
    t, z = (out or {}).get("text") or "", (out or {}).get("alt") or ""
    return [BC.tokens(v) for v in (t, BC.latin_to_arabic(t), z, BC.latin_to_arabic(z)) if v]


def _count(toks, seq):
    return sum(1 for k in range(len(toks) - len(seq) + 1) if all(BC.tok_eq(toks[k + n], seq[n]) for n in range(len(seq)))) if seq else 0


def heard_his(fix, raw_line, out):
    """Did one run hear Medi's correction? Counted AT the correction, not anywhere in the line (Codex audit 2026-10-04):
    his line = the engine's line with his fix applied. In each alphabet view of his correction (as he typed it, and
    turned into Arabic script), the run heard it when one of the run's views (as written, the other alphabet, its
    Arabizi echo) holds his word(s) at least as often as his line does, and NO view of the run holds the engine's
    replaced word(s) more often than his line does. So "blue red" -> "blue blue" is not heard by a run that wrote
    "blue" once; "red" -> "red blue" is not heard by "red blue red"; a removed word must be gone in every alphabet."""
    ew, hw = fix.get("engine_wrote") or "", fix.get("heard") or ""
    his_line = raw_line.replace(ew, hw, 1) if ew else (raw_line + " " + hw)
    views = _views(out)
    if not views:
        return False
    has, clean = not BC.tokens(hw), True
    for cv in (lambda x: x, BC.latin_to_arabic):
        want, gone, his = BC.tokens(cv(hw)), BC.tokens(cv(ew)), BC.tokens(cv(his_line))
        if want and any(_count(v, want) >= max(1, _count(his, want)) for v in views):
            has = True
        if gone and any(_count(v, gone) > _count(his, gone) for v in views):
            clean = False
    return has and clean


def mmss(t):
    return "%02d:%02d" % (int(t) // 60, int(t) % 60)


def other_rows(date):
    """Every overlay row of the lesson that is not this job's: the hand file + Medi's page corrections + his standing rules."""
    return [r for r in TF.load() if (str(r.get("date")) == date or r.get("pattern")) and r.get("by") != BY]


_BLD = {}


def builder_turns(date):
    """The lesson's lines exactly as scripts/build_lessons_page_data.py hands them to the overlay (the page's own lines
    + the Meet gap fills, unrounded times, typed chat lines marked chat) - the same call, so the check below sees what
    the page build will see. Each line carries its place as "_id"."""
    if "m" not in _BLD:
        import build_lessons_page_data as B
        _BLD["m"] = B
    B = _BLD["m"]
    if date not in _BLD:
        P = B.page_turns(date)
        _BLD[date] = B.with_gapfill(P, B.trim_layers(B.gapfill_layers(date), P))
    return [dict(u, _id=k) for k, u in enumerate(copy.deepcopy(_BLD[date]))]


def overlay(date, rows):
    """{_id: line after the whole overlay} + the lines in page order (the builder's call: sorted, GR-11 pass included)."""
    out = TF.apply(date, builder_turns(date), rows=rows)
    return {u["_id"]: u for u in out}, out


def verify(date, rows, others=None):
    """The whole overlay with `rows` in it, on the builder's own lines: every row must change exactly ONE line - its
    own (speaker, time, the engine's text) - to exactly its heard_line, and every other line must come out as it does
    without these rows. Returns the problems (empty = OK)."""
    others = other_rows(date) if others is None else others
    base, _ = overlay(date, others)
    new, _ = overlay(date, others + rows)
    bad, hit = [], {}
    for k, a in base.items():
        b = new[k]
        if a["text"] == b["text"] and a.get("heard") == b.get("heard"):
            continue
        mine = [n for n, r in enumerate(rows) if r["who"] == a["who"] and not a.get("chat") and abs(float(r["t"]) - float(a["t"])) <= 1.0 and r["line"] == a["text"]]
        if len(mine) != 1 or b["text"] != rows[mine[0]]["heard_line"] or a.get("engine"):
            bad.append({"t": a["t"], "why": "a line changed that is not exactly one row's own uncorrected line", "before": a["text"], "after": b["text"]})
        else:
            hit[mine[0]] = hit.get(mine[0], 0) + 1
    for n, r in enumerate(rows):
        if hit.get(n, 0) != 1:
            bad.append({"t": r["t"], "why": "the row lands on %d lines" % hit.get(n, 0), "line": r["line"]})
        if spans(r["line"], r["heard_line"]) != (r["heard_line"], r["spans"]) or (r.get("engine_wrote"), r.get("heard")) != (r["line"], r["heard_line"]):
            bad.append({"t": r["t"], "why": "the row's spans / aliases are not the ones its two lines give", "line": r["line"]})
    return bad


def plan(date):
    d, man, lines, amal, prompts = RL.load(date)
    P = BC.J(os.path.join(d, "proposals.json"))
    if not P:
        raise SystemExit("%s: no proposals.json" % date)
    turns = RL.page_turns(date)                                   # the published page data (what the freeze read)
    others = other_rows(date)
    base, order = overlay(date, others)                           # the builder's lines after everyone else's rows, page order
    eturns = builder_turns(date)
    if len(order) != len(turns):
        raise SystemExit("%s: the page data has %d lines, the builder now makes %d - rebuild the lesson data first" % (date, len(turns), len(order)))
    by_i = {ln["i"]: ln for ln in lines}
    runs = [BC.J(RL.run_path(d, "base", n))["lines"] for n in (1, 2, 3)]

    out = {"date": date, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": [], "lines_changed": [], "kept_overlay": [], "his_corrections": [],
           "reader_rows_gemini_disagrees": [], "listen": [], "held": [], "held_mix": [], "no_agreement": [], "skipped": []}
    for r in P["rows"]:
        base_ = {"i": r["i"], "t": r["t"], "mmss": mmss(r["t"]), "engine": r["engine"], "runs": r["runs"]}
        if r["status"] == "held":
            out["held"].append(dict(base_, heard=r["heard"], her_words=r.get("amal_next"), two_clip=r.get("two_clip")))
            continue
        if r["status"] == "held-mix":
            out["held_mix"].append(dict(base_, heard=r["heard"]))
            continue
        if r["status"] != "proposed":
            out["no_agreement"].append(base_)
            continue
        u = turns[r["i"]] if r["i"] < len(turns) else None
        e = eturns[order[r["i"]]["_id"]] if u else None            # the same line as the builder holds it, before any row
        if not (u and u["who"] == "Medi" and not e.get("chat") and abs(u["t"] - r["t"]) < 0.01 and RL.raw(u) == r["engine"] and e["text"] == r["engine"]):
            out["skipped"].append(dict(base_, why="the page line changed since the freeze"))
            continue
        if any(TF._lands(x, e) for x in others):                  # the line carries a correction: it stays as it is
            out["kept_overlay"].append(dict(base_, now=u["text"], gemini=r["heard"]))
            continue
        line, sp = spans(r["engine"], r["heard"] or "")
        if line is None or not BC.tokens(line, fillers=True):
            out["skipped"].append(dict(base_, why="Gemini wrote no word there, or no word differs; the engine's text stays"))
            continue
        how = "released by the two-clip check" if r.get("released") else ("2 of 3 runs agree on these words" if r["how"] == "spans" else "%d of 3 runs agree on the line" % r["agree"])
        row = {"date": date, "t": u["t"], "who": "Medi", "i": r["i"], "line": r["engine"], "heard_line": line, "spans": sp,
               "engine_wrote": r["engine"], "heard": line,          # plain aliases: older readers of the overlay file expect these two keys
               "rule": RULE, "by": BY,
               "on": RS.today(), "kind": r.get("kind"), "how": how,
               "why": "Gemini 3.8 Flash re-heard his own microphone for this line with the lesson around it (3 runs; %s)" % how}
        if verify(date, [row], others):                           # e.g. two identical lines within a second, or a neighbour's correction that would land on the new text
            out["skipped"].append(dict(base_, why="the row cannot name this line alone, or a neighbouring correction would land on the new text"))
            continue
        out["rows"].append(row)
        out["lines_changed"].append(dict(base_, heard=line, kind=r.get("kind"), how=how, src=by_i[r["i"]].get("src"), spans=len(sp)))
    # ---- every correction already on the lesson, against the 3 runs (also where Gemini agreed with the engine)
    idx = {u["_id"]: k for k, u in enumerate(order)}              # builder line -> page index (= the runs' line number)
    for f in others:
        if f.get("pattern") or f.get("who", "Medi") != "Medi" or f.get("set_who") or f.get("set_t") is not None or f.get("heard_line") is not None:
            continue
        cands = sorted((abs(float(f["t"]) - float(e["t"])), e["_id"]) for e in eturns if e["who"] == "Medi" and not e.get("chat") and TF._lands(f, e))
        if not cands:
            continue
        e = eturns[cands[0][1]]
        i = idx[e["_id"]]
        outs = [run.get(str(i)) for run in runs]
        usable = [o for o in outs if o is not None and not o.get("error")]
        agree = sum(1 for o in usable if heard_his(f, e["text"], o))
        row = {"i": i, "t": turns[i]["t"], "mmss": mmss(turns[i]["t"]), "by": f.get("by"), "engine_wrote": f.get("engine_wrote"), "his": f.get("heard"),
               "engine_line": e["text"], "line_now": turns[i]["text"], "runs": [(o or {}).get("text") if o is not None else None for o in outs],
               "listened": len(usable), "runs_with_his_word": agree}
        if f.get("by") == "medi":
            out["his_corrections"].append(row)
            if len(usable) == 3 and agree == 0:
                out["listen"].append(dict(row, type="his-correction"))
        elif len(usable) == 3 and agree == 0:
            out["reader_rows_gemini_disagrees"].append(row)
    bad = verify(date, out["rows"], others)
    if bad:
        raise SystemExit("%s: the planned rows do not verify together: %s" % (date, json.dumps(bad[:3], ensure_ascii=False)))
    hc = out["his_corrections"]
    out["summary"] = {"lines_changed": len(out["lines_changed"]), "word_changes": sum(1 for x in out["lines_changed"] if x["kind"] == "words"),
                      "alphabet_only": sum(1 for x in out["lines_changed"] if x["kind"] == "alphabet"),
                      "lines_kept_because_already_corrected": len(out["kept_overlay"]),
                      "his_corrections": len(hc), "his_corrections_listened": sum(1 for x in hc if x["listened"] == 3),
                      "his_corrections_heard_by_2_of_3": sum(1 for x in hc if x["runs_with_his_word"] >= 2),
                      "his_corrections_heard_by_1_of_3": sum(1 for x in hc if x["runs_with_his_word"] == 1),
                      "his_corrections_all_3_runs_disagree": len(out["listen"]), "reader_rows_gemini_disagrees": len(out["reader_rows_gemini_disagrees"]),
                      "held": len(out["held"]), "held_mix": len(out["held_mix"]), "no_agreement": len(out["no_agreement"]), "skipped": len(out["skipped"])}
    out["page_data_sha256"] = BC.sha_file(os.path.join(BC.REPO, "docs", "data", "lessons", date + ".json"))
    BC.W(os.path.join(d, "apply-plan.json"), out)
    print(date, json.dumps(out["summary"]), flush=True)
    return out


def _doc():
    with open(TF.FIXES_P, encoding="utf-8-sig") as f:
        return json.load(f)


def _save(doc):
    tmp = TF.FIXES_P + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, TF.FIXES_P)


def apply(ds):
    """Verified first, written second: a lesson whose rows do not verify stops the whole call before any write."""
    doc = _doc()
    plans = {}
    for date in ds:
        P = BC.J(os.path.join(RL.ldir(date), "apply-plan.json"))
        if not P:
            raise SystemExit("%s: no apply-plan.json (run plan)" % date)
        if any(str(r.get("date")) != date or r.get("by") != BY or r.get("who") != "Medi" for r in P["rows"]):
            raise SystemExit("%s: the plan holds a row that is not this lesson's own Gemini row" % date)
        bad = verify(date, P["rows"])
        if bad:
            raise SystemExit("%s: the plan no longer verifies (the lesson or its corrections changed since the plan - run plan again): %s" % (date, json.dumps(bad[:2], ensure_ascii=False)))
        plans[date] = P
    n_other = sum(1 for r in doc["rows"] if r.get("by") != BY)
    doc["rows"] = [r for r in doc["rows"] if not (r.get("by") == BY and str(r.get("date")) in plans)] + [r for d in ds for r in plans[d]["rows"]]
    assert sum(1 for r in doc["rows"] if r.get("by") != BY) == n_other                       # nobody else's row is added or lost
    _save(doc)
    doc2 = RS.load()
    for date, P in plans.items():
        s = P["summary"]
        doc2["lessons"][date] = {"status": "applied", "since": RS.today(),
                                 "note": "Gemini's second listen changed %d of your lines (%d with a different word, %d only the alphabet); your own corrections stayed; %d lines wait for your ear." % (
                                     s["lines_changed"], s["word_changes"], s["alphabet_only"], s["held"] + s["held_mix"] + s["his_corrections_all_3_runs_disagree"])}
    RS.stamp_pages(RS.save(doc2))
    print("applied:", ", ".join("%s (%d rows)" % (d, len(plans[d]["rows"])) for d in ds))


def unapply(ds):
    doc = _doc()
    n = len(doc["rows"])
    doc["rows"] = [r for r in doc["rows"] if not (r.get("by") == BY and str(r.get("date")) in ds)]
    _save(doc)
    doc2 = RS.load()
    for date in ds:
        if (doc2["lessons"].get(date) or {}).get("status") == "applied":
            doc2["lessons"][date] = {"status": "proposed", "since": RS.today(), "note": "Gemini's second listen ran; its changes were taken out again and none is in the transcript."}
    RS.stamp_pages(RS.save(doc2))
    print("removed %d rows of %s; status back to proposed" % (n - len(doc["rows"]), BY))


def check(ds=None):
    """The rows of this job that are in the overlay file now: per lesson, the whole overlay must change exactly their
    lines to their text (verify), and each lesson marked applied must have its plan's rows in the file. Returns problems."""
    rows = [r for r in _doc()["rows"] if r.get("by") == BY]
    bad = []
    status = RS.load()["lessons"]
    for date in (ds or sorted(set(RS.published()) | {str(r.get("date")) for r in rows})):
        mine = [r for r in rows if str(r.get("date")) == date]
        applied = (status.get(date) or {}).get("status") == "applied"
        P = BC.J(os.path.join(RL.ldir(date), "apply-plan.json")) or {}
        if applied and mine != (P.get("rows") or []):
            bad.append({"date": date, "why": "marked applied but the overlay file does not hold exactly the plan's rows"})
        if mine and not applied:
            bad.append({"date": date, "why": "%d Gemini rows are in the overlay but the lesson is not marked applied" % len(mine)})
        bad += [dict(b, date=date) for b in verify(date, mine)] if mine else []
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
            print(json.dumps(b, ensure_ascii=False)[:300])
        print("rehear rows: %s" % ("OK" if not bad else "%d problem(s)" % len(bad)))
        sys.exit(1 if bad else 0)
    else:
        raise SystemExit(__doc__)
