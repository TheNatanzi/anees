# -*- coding: utf-8 -*-
"""Re-hear proposals from the benchmark's listener runs (PR-18 / TR-22; Medi 2026-10-04 "A - lets get a good baseline
scoring done before we make a decision").

No new paid call: the 3 frozen runs of one listener on the lesson are read, and for every line of Medi's
  - a change is PROPOSED only when 2 of 3 runs agree on the same words;
  - a proposed change is HELD (never automatic) when a word it adds is a word Amal says in the next 15 s - the listener
    may be writing her correction into his line (slip-hiding);
  - a change of alphabet only (his Arabic in English letters -> Arabic script) is kept apart from a change of words.
Nothing is applied to the lesson: the output is a proposals file for Medi's review and the transcript the proposals
would make (scratch), which scoreboard B and the AI readers can then score.

    python scripts/bench_rehear.py 2026-10-02 gemini-flash-t1
"""
import collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402

AMAL_NEXT_S = 15.0


def mmss(t):
    return "%02d:%02d" % (int(t) // 60, int(t) % 60)


def proposals(truth, runs):
    amal = truth.get("amal_all") or []
    mom = collections.defaultdict(list)
    for m in truth["moments"]:
        mom[m["i"]].append(m)
    rows = []
    for ln in truth["lines"]:
        outs = [r.get(str(ln["i"])) for r in runs]
        if all(o is None for o in outs):
            continue
        outs = [o if o is not None else {"text": ln["engine"]} for o in outs]
        keys = [" ".join(BC.tokens(o.get("text") or "")) for o in outs]
        k, n = collections.Counter(keys).most_common(1)[0]
        if k == " ".join(BC.tokens(ln["engine"])):
            continue                                              # the listener agrees with the engine
        row = {"i": ln["i"], "t": ln["t"], "mmss": mmss(ln["t"]), "engine": ln["engine"], "agree": n, "runs": [o.get("text") or "" for o in outs]}
        if n * 2 <= len(outs):
            row.update(status="no-agreement", heard=None)         # 3 different answers: nothing proposed
        else:
            o = outs[keys.index(k)]
            heard = o.get("text") or ""
            new = [w for w in BC.tokens(heard) if BC.is_ar(w) and w not in set(BC.tokens(ln["engine"])) | set(BC.tokens(BC.latin_to_arabic(ln["engine"])))]
            hers = set()
            for a in amal:
                if ln["t"] < a["t"] <= ln["end"] + AMAL_NEXT_S:
                    hers |= set(BC.tokens(a["text"]))
            danger = [w for w in new if w in hers]
            words = BS.content_change(ln["engine"], heard)
            row.update(heard=heard, arabizi=o.get("alt") or "", kind="words" if words else "alphabet",
                       amal_next=danger, status="held" if danger else "proposed",
                       confidence=(o.get("raw") or {}).get("confidence"), why=(o.get("raw") or {}).get("why"))
        # the answer key, for the baseline only (never used to decide)
        ms = mom.get(ln["i"]) or []
        if ms and row.get("heard") is not None:
            row["key"] = [{"id": m["id"], "ok": BS.has_want(m, row["heard"], row.get("arabizi") or "", truth_line=ln["truth"])} for m in ms]
        elif ms:
            row["key"] = [{"id": m["id"], "ok": False} for m in ms]
        row["medi_corrected"] = ln["corrected"]
        rows.append(row)
    return rows


def transcript(truth, rows, held=False):
    """{line_i: text} the proposals would make: proposed changes in, held ones only when held=True, the rest raw."""
    out = {ln["i"]: ln["engine"] for ln in truth["lines"]}
    for r in rows:
        if r["status"] == "proposed" or (held and r["status"] == "held"):
            out[r["i"]] = r["heard"]
    return out


def main(argv):
    date, engine = argv[0], argv[1]
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    runs = [r["lines"] for r in BS.load_runs(d, engine, "line")]
    rows = proposals(truth, runs)
    c = collections.Counter((r["status"], r.get("kind")) for r in rows)
    moments = {m["id"]: m for m in truth["moments"]}
    fixed = {k["id"] for r in rows if r["status"] == "proposed" for k in r.get("key", []) if k["ok"]}
    held_ok = {k["id"] for r in rows if r["status"] == "held" for k in r.get("key", []) if k["ok"]}
    T = transcript(truth, rows)
    lines = {ln["i"]: ln for ln in truth["lines"]}
    hidden = [s for s in truth["slips"] if BS.slip_hidden(s, lines[s["i"]]["truth"], T[s["i"]])]
    hidden_if_held = [s for s in truth["slips"] if BS.slip_hidden(s, lines[s["i"]]["truth"], transcript(truth, rows, held=True)[s["i"]])]
    untouched = [r for r in rows if not r["medi_corrected"] and not lines[r["i"]]["overlay"]]
    summary = {"engine": engine, "runs": len(runs), "lines_listened": len(runs[0]), "lines_changed": len(rows),
               "proposed_words": c[("proposed", "words")], "proposed_alphabet": c[("proposed", "alphabet")],
               "held_amal_next": sum(v for (s, _), v in c.items() if s == "held"), "no_agreement": c[("no-agreement", None)],
               "moments": len(moments), "moments_fixed_by_proposed": len(fixed), "moments_fixed_only_if_held_are_taken": len(held_ok - fixed),
               "slips_hidden_by_proposed": len(hidden), "slips_hidden_if_held_are_taken": len(hidden_if_held),
               "untouched_lines_proposed_words": sum(1 for r in untouched if r["status"] == "proposed" and r["kind"] == "words"),
               "untouched_lines_proposed_alphabet": sum(1 for r in untouched if r["status"] == "proposed" and r["kind"] == "alphabet"),
               "untouched_lines_held": sum(1 for r in untouched if r["status"] == "held")}
    BC.W(os.path.join(d, "rehear", engine + ".json"), {"date": date, "summary": summary, "rows": rows})
    BC.W(os.path.join(d, "rehear", engine + ".transcript.json"), {str(k): v for k, v in T.items()})
    for k, v in summary.items():
        print("%-40s %s" % (k, v))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
