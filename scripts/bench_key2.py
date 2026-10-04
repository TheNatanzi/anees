# -*- coding: utf-8 -*-
"""Benchmark answer key version 2 (PR-18: "a changed key is a new version, never a silent edit").

    python scripts/bench_key2.py 2026-10-02            # truth-v2.json + manifest-v2.json + scores-v2.json + the table
    python scripts/bench_key2.py 2026-10-02 --check    # re-derive v2 and compare with manifest-v2.json (exit 1 on a change)

Key v1 (truth.json, manifest.json, scores.json) is only READ. Key v2 = key v1 + the short explicit list in
key-v2-revisions.json (Medi re-listened on 2026-10-04 and reversed two of his own corrections: 49:44 he said tani, 39:45
akleh). Each revision names one moment, the heard word it replaces and the new one, with his words and the date; the
moment's `want`, its line's `truth` text and that line's `fixes[].heard` change together, nothing else does.
Refused: a truth.json that is not the manifest's, an unknown moment id, a `heard_was` that is not what key v1 holds, and a
second, different v2 over an existing manifest-v2.json. Every engine is then scored exactly like bench_score.main()
(same load_runs, line + whole) into scores-v2.json. No network, no paid call.
"""
import copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_score as BS  # noqa: E402

NOT_ENGINES = ("clips", "scratch", "runs", "vowel", "b")      # the same list as bench_score.main()


def apply_revisions(truth, rev):
    """Pure: (key v1, the revisions doc) -> key v2. The input is not touched. ValueError on anything that does not fit."""
    out = copy.deepcopy(truth)
    if out.get("version") != rev.get("derives_from_version"):
        raise ValueError("revisions derive from version %r, the key is version %r" % (rev.get("derives_from_version"), out.get("version")))
    moments = {m["id"]: m for m in out["moments"]}
    lines = {ln["i"]: ln for ln in out["lines"]}
    seen = set()
    for r in rev.get("revisions") or []:
        mid = r.get("moment")
        if mid not in moments:
            raise ValueError("unknown moment id %r" % mid)
        if mid in seen:
            raise ValueError("moment %s revised twice" % mid)
        seen.add(mid)
        if not (r.get("want") and r.get("heard") and r.get("heard_was") and r.get("quote") and r.get("on") and r.get("by")):
            raise ValueError("%s: a revision needs want, heard_was, heard, by, on and his words (quote)" % mid)
        m, ln = moments[mid], lines[moments[mid]["i"]]
        fixes = [f for f in ln.get("fixes") or [] if f.get("heard") == r["heard_was"]]
        if len(fixes) != 1 or ln["truth"].count(r["heard_was"]) != 1 or m["want"] != [r["heard_was"]]:
            raise ValueError("%s: key v%s does not hold %r on that line exactly once" % (mid, out.get("version"), r["heard_was"]))
        m["revised"] = {"want_was": m["want"], "by": r["by"], "on": r["on"], "quote": r["quote"]}
        m["want"] = list(r["want"])
        ln["truth"] = ln["truth"].replace(r["heard_was"], r["heard"], 1)
        fixes[0]["heard"] = r["heard"]
    out["version"] = rev["version"]
    out["derived"] = {"from_version": truth.get("version"), "on": rev.get("on"), "by": rev.get("by"), "why": rev.get("why"),
                      "revised_moments": sorted(seen)}
    return out


def build(date):
    """-> (truth v2, manifest v2 without the truth hash, v1 manifest). Reads only; refuses an edited key v1."""
    d = BC.bench_dir(date)
    man = BC.J(os.path.join(d, "manifest.json"))
    tp = os.path.join(d, "truth.json")
    if not man or BC.sha_file(tp) != man["truth_sha256"]:
        raise SystemExit("truth.json does not match manifest.json: key v1 was edited after the freeze - refusing to derive v2 from it")
    rp = os.path.join(d, "key-v2-revisions.json")
    rev = BC.J(rp)
    if not rev:
        raise SystemExit("no %s" % rp)
    try:
        truth2 = apply_revisions(BC.J(tp), rev)
    except ValueError as e:
        raise SystemExit("key-v2-revisions.json refused: %s" % e)
    truth2["derived"].update(from_truth_sha256=man["truth_sha256"], revisions_sha256=BC.sha_file(rp))
    man2 = {"date": date, "version": rev["version"], "derived_on": rev.get("on"),
            "derives_from": {"version": man["version"], "truth_sha256": man["truth_sha256"]},
            "revisions_file": "key-v2-revisions.json", "revisions_sha256": BC.sha_file(rp), "revisions": len(rev["revisions"]),
            "revised_moments": truth2["derived"]["revised_moments"], "counts": truth2["counts"],
            # the clips and the listeners' prompts are key v1's, untouched (the engines' saved runs are scored again)
            "prompts_sha256": man["prompts_sha256"], "clips_sha256": man["clips_sha256"],
            "normaliser_sha256": BC.sha_file(os.path.join(HERE, "bench_common.py")),
            "scorer_sha256": BC.sha_file(os.path.join(HERE, "bench_score.py"))}
    return truth2, man2, man


def score_all(d, truth, truth_sha):
    """Every engine dir with complete runs, exactly as bench_score.main() scores them."""
    code = (BC.sha_file(os.path.join(HERE, "bench_score.py")), BC.sha_file(os.path.join(HERE, "bench_common.py")))
    engines = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)) and x not in NOT_ENGINES)
    scores = {}
    for e in engines:
        for mode in ("line", "whole"):
            runs = BS.load_runs(d, e, mode)
            if not runs:
                continue
            s = BS.score(truth, [r["lines"] for r in runs], whole_file=(mode == "whole"))
            s["scorer_sha256"], s["normaliser_sha256"] = code
            s["amal"] = BS.score_amal(truth, [r["lines"] for r in runs])
            s.update(model=runs[0].get("model"), cost_usd=round(sum(r.get("cost_usd") or 0 for r in runs), 4),
                     seconds=[round(r.get("seconds") or 0, 1) for r in runs], truth_sha256=truth_sha, key_version=truth["version"])
            scores["%s|%s" % (e, mode)] = s
    return scores


def table(v1, v2):
    """[(engine|mode, heard right v1, v2, hidden slips v2, untouched lines changed v2)], best v2 first."""
    rows = [(k, (v1.get(k) or {}).get("hit"), s["hit"], s["hidden_slips"], s["content_changes"]) for k, s in v2.items()]
    return sorted(rows, key=lambda r: (-r[2], r[0]))


def main(argv):
    date = argv[0]
    d = BC.bench_dir(date)
    truth2, man2, man = build(date)
    tp2, mp2 = os.path.join(d, "truth-v2.json"), os.path.join(d, "manifest-v2.json")
    old = BC.J(mp2)
    if "--check" in argv:
        if not old:
            raise SystemExit("no manifest-v2.json: key v2 not written")
        now = BC.sha_text(json.dumps(truth2, ensure_ascii=False, indent=1))
        bad = [k for k, v in (("truth_v2_sha256", now), ("revisions_sha256", man2["revisions_sha256"])) if old.get(k) != v]
        bad += ["truth-v2.json (file)"] if BC.sha_file(tp2) != old.get("truth_v2_sha256") else []
        bad += ["derives_from"] if old.get("derives_from") != man2["derives_from"] else []
        print("bench key v2: %s" % ("CHANGED " + ", ".join(bad) if bad else "OK (truth v2 %s, from v1 %s)" % (old["truth_v2_sha256"][:16], man["truth_sha256"][:16])))
        return 1 if bad else 0
    new_sha = BC.sha_text(json.dumps(truth2, ensure_ascii=False, indent=1))      # BC.W writes exactly this text
    if old and old.get("truth_v2_sha256") != new_sha:
        raise SystemExit("manifest-v2.json already holds another key v2 (%s). A changed key is a new version, never a silent edit." % str(old.get("truth_v2_sha256"))[:16])
    BC.W(tp2, truth2)
    assert BC.sha_file(tp2) == new_sha
    BC.W(mp2, dict(man2, truth_v2_sha256=new_sha))
    v1 = BC.J(os.path.join(d, "scores.json")) or {}
    v2 = score_all(d, truth2, new_sha)
    BC.W(os.path.join(d, "scores-v2.json"), v2)
    stale = sorted(k for k, s in v1.items() if s.get("scorer_sha256") != man2["scorer_sha256"] or s.get("normaliser_sha256") != man2["normaliser_sha256"])
    if stale:
        print("NOTE: scores.json (key v1) was scored with another scorer version for %d rows, e.g. %s" % (len(stale), stale[0]))
    print("key v1 %s -> key v2 %s (%d revisions: %s)" % (man["truth_sha256"][:16], new_sha[:16], man2["revisions"], ", ".join(man2["revised_moments"])))
    print("%-30s %8s %8s %7s %9s" % ("engine|mode", "v1 right", "v2 right", "hidden", "untouched"))
    for k, a, b, h, c in table(v1, v2):
        print("%-30s %8s %8d %7d %9d%s" % (k, "-" if a is None else a, b, h, c, "" if a is None or a == b else "   (%+d)" % (b - a)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
