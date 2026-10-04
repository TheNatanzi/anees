# -*- coding: utf-8 -*-
"""True scoreboard B (PR-18): the 3 AI readers re-read a listener's version of the lesson in a scratch folder.
Nothing is published, no database, no ledger: every file stays under bench/<date>/readers/<tag>/.

    python scripts/bench_readers.py 2026-10-02 prep gemini-flash-best-t1 best     # readers/best/<date>.txt from rehear/<engine>.transcript.json
    (readers r1, r2 write readers/<tag>/<date>.r1.json / .r2.json - READER-BRIEF.md, the scratch transcript only)
    python scripts/bench_readers.py 2026-10-02 compare best                       # compare.json + disputes.md for the third reader
    python scripts/bench_readers.py 2026-10-02 settle best                        # settled.json + compare-with-published.json

The scratch transcript = the engine's raw text of every turn, with Medi's lines replaced by the re-hear's PROPOSED
changes (2 of 3 runs agree, not held) - scripts/bench_rehear.py.
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402


def sdir(date, tag):
    return os.path.join(BC.bench_dir(date), "readers", tag)


def mmss(t):
    t = int(round(t))
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)


def prep(date, engine, tag):
    T = BC.J(os.path.join(BC.bench_dir(date), "rehear", engine + ".transcript.json"))
    if not T:
        raise SystemExit("run scripts/bench_rehear.py %s %s first" % (date, engine))
    page = BC.J(os.path.join(BC.REPO, "docs", "data", "lessons", date + ".json"))
    L = ["# Lesson %s - %d turns on the lesson clock (mm:ss = seconds on the page audio)" % (date, len(page["turns"])), ""]
    for i, t in enumerate(page["turns"]):
        who = t["who"]
        tag_ = ("CHAT %s" % t.get("typed_by", "")).strip() if who == "chat" else who
        text = T[str(i)] if (who == "Medi" and str(i) in T) else (t.get("engine") or t["text"])
        L.append("[%s] %s: %s" % (mmss(t["t"]), tag_, text))
    p = os.path.join(sdir(date, tag), date + ".txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("wrote", p, len(L) - 2, "turns")


def _fac(date, tag):
    import full_audit_compare as FAC
    FAC.WORK = sdir(date, tag)                        # the scratch folder, never data/lesson-work/full-audit
    return FAC


def compare(date, tag):
    FAC = _fac(date, tag)
    out = FAC.compare(date)
    print(json.dumps((out or BC.J(os.path.join(sdir(date, tag), date + ".compare.json")))["counts"]))


def settle(date, tag):
    FAC = _fac(date, tag)
    FAC.settle(date)
    S = BC.J(os.path.join(sdir(date, tag), date + ".settled.json"))
    P = BC.J(os.path.join(BC.REPO, "data", "lesson-work", "full-audit", date + ".settled.json"))
    mine, pub = S["rows"], P["rows"]
    used, both, only_mine = set(), 0, []
    for a in mine:
        j = next((k for k, b in enumerate(pub) if k not in used and FAC.kind_class(a.get("kind")) == FAC.kind_class(b.get("kind")) and FAC.same_moment(a, b)), None)
        if j is None:
            j = next((k for k, b in enumerate(pub) if k not in used and FAC.same_moment(a, b)), None)
        if j is None:
            only_mine.append(a)
        else:
            used.add(j)
            both += 1
    brief = lambda r: {"t": r.get("t"), "kind": r.get("kind"), "wrong": r.get("medi_said") or r.get("wrong"), "right": r.get("should_be") or r.get("right"), "bucket": r.get("bucket")}  # noqa: E731
    out = {"tag": tag, "settled": len(mine), "kinds": dict(collections.Counter(str(r.get("kind")) for r in mine)),
           "published_settled": len(pub), "published_kinds": dict(collections.Counter(str(r.get("kind")) for r in pub)), "in_both": both,
           "only_here": [brief(r) for r in only_mine], "only_published": [brief(b) for k, b in enumerate(pub) if k not in used], "counts": S.get("counts")}
    BC.W(os.path.join(sdir(date, tag), "compare-with-published.json"), out)
    print(json.dumps({k: out[k] for k in ("settled", "kinds", "published_settled", "in_both")}, ensure_ascii=False))
    print("only here:", json.dumps(out["only_here"], ensure_ascii=False))
    print("only published:", json.dumps(out["only_published"], ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    {"prep": lambda: prep(a[0], a[2], a[3]), "compare": lambda: compare(a[0], a[2]), "settle": lambda: settle(a[0], a[2])}[a[1]]()
