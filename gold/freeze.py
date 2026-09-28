# -*- coding: utf-8 -*-
"""Freeze Anees's eval (gold) sets: gold/<name>@<version>/ + gold/manifest.json.

    python gold/freeze.py            # freeze every set in SPECS that is not in the manifest yet; verify the rest
    python gold/freeze.py --verify   # only check every frozen file against its sha256 (exit 1 on any change)

Rules (plan/AI-ENGINEERING-REVIEW-2026-09-27.md, Tracking design section 4):
  - A frozen set is never edited. A changed set is a NEW version (add a spec with a new version string).
  - Existing manifest entries are never rewritten by this script; it only adds missing ones.
    The one exception: a placeholder (status to-label / not-saved / to-collect) is replaced once
    by the real frozen entry of the same id when its labels exist.
  - sha256 is over the frozen file's bytes with CRLF folded to LF (Windows checkouts use autocrlf;
    gold/.gitattributes also switches EOL conversion off for this folder).
  - Nothing here costs money: it copies files already in the repo (or in git history).
"""
import datetime as dt, hashlib, json, os, subprocess, sys

GOLD = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(GOLD)
MANIFEST = os.path.join(GOLD, "manifest.json")


def sha256_bytes(b):
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def sha256_file(p):
    with open(p, "rb") as f:
        return sha256_bytes(f.read())


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, check=True).stdout


def last_commit(path):
    return git("log", "-1", "--format=%H", "--", path).decode().strip()


def read_source(path, commit=None):
    """Bytes of a repo file, from the working tree or from a git commit (LF-normalised)."""
    if commit:
        return git("show", f"{commit}:{path}").replace(b"\r\n", b"\n")
    with open(os.path.join(REPO, path), "rb") as f:
        return f.read().replace(b"\r\n", b"\n")


def dumps(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def jsonl(rows):
    return "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")


# ------------------------------------------------------------------ builders (return: bytes, n, extra manifest fields)
def grammar_v1(split):
    src = "docs/data/grammar-goldset.json"

    def build():
        g = json.loads(read_source(src))
        ev = [e for e in g["events"] if e.get("split", "tuned") == split]
        doc = {"id": f"grammar@v1-{split}", "split": split, "source": src, "source_updated": g.get("updated"),
               "method": g.get("method"), "events": ev}
        return dumps(doc), len(ev), {"n_scored": sum(1 for e in ev if e["kind"] == "grammar"),
                                     "lessons": sorted({e["date"] for e in ev})}
    return src, None, build


def grammar_v2_audit():
    src = "data/full-audit-2026-09-26.json"

    def build():
        a = json.loads(read_source(src))
        rows = a["rows"]
        return jsonl(rows), len(rows), {"n_scored": sum(1 for r in rows if r.get("kind") == "grammar"),
                                        "source_built": a.get("built"), "totals": a.get("totals"),
                                        "lessons": sorted({r["date"] for r in rows}), "format": "jsonl, one audit row per line"}
    return src, None, build


def arabizi_v1():
    src, graded = "data/lesson-work/full-audit/arabizi-check-100.json", "data/lesson-work/full-audit/arabizi-check-100.graded.json"

    def build():
        s, g = json.loads(read_source(src)), json.loads(read_source(graded))
        by = {x["n"]: x for x in g["lines"]}
        lines = [dict(l, ok=by[l["n"]]["ok"], why=by[l["n"]].get("why")) for l in s["lines"]]
        assert len(lines) == 100 and all(l["n"] in by for l in s["lines"])
        doc = {"id": "arabizi@v1", "seed": s.get("seed"), "score": g.get("score"), "faults": g.get("faults"), "lines": lines}
        return dumps(doc), len(lines), {"accuracy": round(sum(l["ok"] for l in lines) / len(lines), 3),
                                        "also_from": [{"path": graded, "sha256": sha256_bytes(read_source(graded)),
                                                       "git_commit": last_commit(graded)}]}
    return src, None, build


def sheet(version, commit):
    src = "data/lesson-work/sheet-verdicts.json"

    def build():
        rows = json.loads(read_source(src, commit))
        from collections import Counter
        return dumps({"id": f"sheet@{version}", "verdicts": rows}), len(rows), {
            "verdict_counts": dict(Counter(r["verdict"] for r in rows))}
    return src, commit, build


# ------------------------------------------------------------------ the sets
SPECS = [
    dict(id="grammar@v1-tuned", name="grammar", version="v1-tuned", split="tuned", file="events.json",
         build=grammar_v1("tuned"),
         labelled_how="Every Medi turn in three lessons read by hand with the 25 s after it (Amal's voice + her Meet chat). "
                      "The auditor (scripts/audit_grammar_lessons.py) was TUNED on these rows: an optimistic number.",
         labelled_by="hand read of the transcripts in a Claude session (scripts/build_grammar_goldset.py); not Amal-verified", metrics=["recall", "precision", "f1", "bucket_accuracy"],
         gate="history only (tuned rows overfit)", scorer="scripts/score_grammar_detector.py --gold=grammar@v1-tuned"),
    dict(id="grammar@v1-heldout", name="grammar", version="v1-heldout", split="heldout", file="events.json",
         build=grammar_v1("heldout"),
         labelled_how="Lesson 2026-09-11 labelled by hand AFTER tuning and never tuned on: the honest recall estimate.",
         labelled_by="hand read of the transcripts in a Claude session (scripts/build_grammar_goldset.py); not Amal-verified", metrics=["recall", "precision", "f1", "bucket_accuracy"],
         gate="pytest floor: recall >= last accepted in gold/history.jsonl - 0.02 (tests/test_eval_floors.py)",
         scorer="scripts/score_grammar_detector.py --gold=grammar@v1-heldout"),
    dict(id="grammar@v2-audit", name="grammar", version="v2-audit", split="all", file="rows.jsonl",
         build=grammar_v2_audit(),
         labelled_how="Full audit of 14 lessons: two independent AI reader passes (r1, r2) per lesson, a third reader "
                      "settles disputes, reconciled with the 2026-09-24 hand sweep. AI-labelled (silver, not human gold); "
                      "B rows (Amal gave no signal) wait for Amal's ruling.",
         labelled_by="Claude readers r1/r2/r3; Medi yes/no on the build; Amal: pending (B rows)",
         metrics=["recall on kind=grammar rows", "precision", "f1"], gate="history only (trend)",
         scorer="scripts/score_grammar_detector.py --gold=grammar@v2-audit"),
    dict(id="arabizi@v1", name="arabizi", version="v1", split=None, file="lines.json", build=arabizi_v1(),
         labelled_how="100 random transcript lines (seed 20260926, scripts/arabizi_check.cjs) rendered by the shared Arabizi "
                      "renderer, each graded 1/0 against Amal's spelling (rule S1). 96/100.",
         labelled_by="Claude (hand grade against Amal's Doc + chat); not Amal-verified",
         metrics=["accuracy (target 0.95)"], gate="on renderer / prompt change", scorer=None),
    dict(id="sheet@v1", name="sheet", version="v1", split=None, file="verdicts.json", build=sheet("v1", "aa1e7f8e596812d22967c36200e0fffe21e99008"),
         labelled_how="The 98 'not on sheet' words on the Lessons page judged by meaning against Medi's list: 56 were on the "
                      "list (the string match was wrong), 42 really new. Frozen from git commit aa1e7f8.",
         labelled_by="Claude (hand check by meaning), confirmed by Medi 2026-09-27",
         metrics=["'new word' precision", "on_list never flagged new"], gate="tests/test_invariants.py (on code change)", scorer=None),
    dict(id="sheet@v2", name="sheet", version="v2", split=None, file="verdicts.json", build=sheet("v2", "92f901736d57092385eb39f4858761b1c3d8379c"),
         labelled_how="All 273 word cards on the Lessons page judged by meaning both ways (Arabic and English): on_list / new / "
                      "not_an_error / duplicate. Supersedes v1's 98 rows (same verdicts on the overlap).",
         labelled_by="Claude (overnight audit 2026-09-27), duplicates confirmed by Medi 2026-09-27",
         metrics=["'new word' precision", "verdicts applied on the page"], gate="tests/test_invariants.py", scorer=None),
]

PLACEHOLDERS = [
    dict(id="asr@v1", name="asr", version="v1", status="to-label",
         seed=["data/aug25/gold_selection_v2.json (50 windows of the 2026-08-25 lesson; engine text, NOT a verbatim reference)",
               "data/aug25/check02_results_amal.json (Amal rated engine outputs on 20 clips; a preference, not a transcript)"],
         recipe=["Take the 50 windows in data/aug25/gold_selection_v2.json and the 20 check-02 clips.",
                 "Amal (or Medi, then Amal checks) types what was really said, verbatim, both channels, in Amal's own spelling "
                 "(Arabic script + her Arabizi), keeping Medi's mistakes as said.",
                 "Save gold/asr@v1/lines.jsonl: {lesson, t_start, t_end, speaker, verbatim_ar, verbatim_arabizi, labeller}.",
                 "Grow to 1-2 h across 3+ lessons (two-track lessons first). Freeze each growth step as a new version.",
                 "Score: CER/WER (normalised + raw on learner lines), learner-error retention, hallucinated words."],
         needs="Amal: about 2-6 h of typing", gate="on engine / param / keyterm change"),
    dict(id="speaker@v1", name="speaker", version="v1", status="to-label",
         recipe=["Sample 100 turns (seeded) from the one mixed-audio lesson 2026-09-18 (diarized scribe.json) and 100 from "
                 "2026-09-04 (pitch-labelled words_labeled.json).",
                 "Medi listens to each clip and marks Medi / Amal / both / unclear.",
                 "Save gold/speaker@v1/turns.jsonl: {lesson, t_start, t_end, machine_speaker, human_speaker}.",
                 "Metric: speaker accuracy (target >= 0.90); track unlabeled_share every lesson."],
         interim="tests/test_invariants.py::test_speakers_not_swapped uses grammar@v2-audit rows as a cheap proxy",
         needs="Medi: about 30 min of listening", gate="on diarization change"),
    dict(id="reader@v1", name="reader", version="v1", status="to-label",
         recipe=["Freeze 2-3 lessons' reader output (e.g. 2026-09-21 and 2026-09-14 settled rows, from grammar@v2-audit).",
                 "Sample 50 rows per lesson: 20 random, 20 low-confidence, 10 disputed; Amal (grammar) or Medi (vocab) answers "
                 "Yes / No / Unsure per row; answers go to data/decisions (decisions log).",
                 "Save gold/reader@v1/verdicts.jsonl: {uid, lesson, ai_kind, ai_bucket, human_answer, who}.",
                 "Metrics: human-sampled precision, pairwise F1, kappa on labels. Canary when model or brief sha changes."],
         needs="Amal: about 1 h per lesson", gate="canary on model / brief change"),
    dict(id="gloss@v1", name="gloss", version="v1", status="to-label",
         recipe=["Draw 200 Amal lines (seed 20260927) with >= 3 Arabic words from docs/data/lessons/<date>.json turns (who=Amal).",
                 "Amal writes the English she meant for each line.",
                 "Save gold/gloss@v1/lines.jsonl: {lesson, t, arabic, amal_english}.",
                 "Metrics: chrF++ of the machine gloss vs Amal, judge-vs-Amal agreement."],
         needs="Amal: about 2 h", gate="quarterly"),
    dict(id="ladder@v1", name="ladder", version="v1", status="not-saved",
         note="plan/SENTENCE-LADDER-SPEC-2026-09-27.md section 9: a blind check of 30 random listening units (19/30 -> 21/30 "
              "after two rule fixes) and 20 breakdowns (16/20). Only the totals were kept; the 30 per-unit labels were not saved, "
              "so there is nothing to freeze.",
         recipe=["Re-draw 30 listening units with a fixed seed from docs/data/sentence-ladder/<date>.json (all lessons).",
                 "Label each blind (understood / unclear / breakdown / unknown) and SAVE the labels: "
                 "gold/ladder@v1/units.jsonl {lesson, unit_id, machine_label, human_label, labeller_version}.",
                 "Then Medi's logged swipes (sentence_labels) become ladder@v2: confusion matrix, accuracy + 95% CI, weekly."],
         needs="Medi: swipes after each lesson", gate="weekly"),
    dict(id="fsrs@v1", name="fsrs", version="v1", status="to-collect",
         note="Needs card_results with grade 1-4, state_before, scheduler_version (roadmap item 9). "
              "tests/fixtures/fsrs-py-golden.json is an implementation-parity golden (JS vs py-fsrs), not a learner eval set.",
         recipe=["Log grade + state_before + scheduler_version on every card answer (roadmap 9).",
                 "Monthly: replay card_results, freeze the replay as fsrs@vN, score log loss + calibration (predicted R vs observed)."],
         needs="data only (Medi keeps reviewing cards)", gate="monthly refit"),
]

POINTERS = [
    dict(id="quizlet@2026-09", name="quizlet", version="2026-09", status="pointer",
         path="docs/data/quizlet/amal-quizlet-sets.json",
         note="Amal's own Quizlet sets: the golden answers used by scripts/verb_addons_golden.cjs and scripts/verb_forms_holdout.py. "
              "A pointer (sha at freeze time), not a copy: those scorers are not wired to gold/history.jsonl yet.",
         labelled_by="Amal"),
]


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {"about": "Anees eval sets. name@version, never edited; a changed set is a new version. See gold/README.md.",
            "sha_rule": "sha256 of the frozen file with CRLF folded to LF", "sets": []}


def save_manifest(m):
    with open(MANIFEST, "wb") as f:
        f.write(dumps(m))


def verify(m):
    bad = []
    for e in m["sets"]:
        if e.get("status") != "frozen":
            continue
        p = os.path.join(GOLD, e["path"])
        if not os.path.exists(p):
            bad.append((e["id"], "missing"))
        elif sha256_file(p) != e["sha256"]:
            bad.append((e["id"], "changed"))
    return bad


def main():
    m = load_manifest()
    have = {e["id"]: e for e in m["sets"]}
    if "--verify" not in sys.argv:
        today = dt.date.today().isoformat()
        for s in SPECS:
            if have.get(s["id"], {}).get("status") == "frozen":
                continue
            src, commit, build = s["build"]
            data, n, extra = build()
            d = os.path.join(GOLD, s["id"])
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, s["file"])
            if os.path.exists(p) and sha256_file(p) != sha256_bytes(data):
                sys.exit(f"{s['id']}: {p} exists with other content and no manifest entry - refusing to overwrite")
            with open(p, "wb") as f:
                f.write(data)
            entry = {"id": s["id"], "name": s["name"], "version": s["version"], "status": "frozen",
                     "path": f"{s['id']}/{s['file']}", "sha256": sha256_bytes(data), "bytes": len(data), "n": n,
                     "split": s["split"], "created": today,
                     "source": {"path": src, "git_commit": commit or last_commit(src),
                                "sha256": sha256_bytes(read_source(src, commit))},
                     "labelled_how": s["labelled_how"], "labelled_by": s["labelled_by"], "metrics": s["metrics"],
                     "gate": s["gate"], "scorer": s["scorer"]}
            entry.update(extra)
            if s["id"] in have:
                m["sets"][m["sets"].index(have[s["id"]])] = entry
            else:
                m["sets"].append(entry)
            have[s["id"]] = entry
            print("froze", s["id"], "n=%d" % n, entry["sha256"][:12])
        for p in PLACEHOLDERS:
            if p["id"] not in have:
                m["sets"].append(dict(p, created=today))
                have[p["id"]] = p
                print("placeholder", p["id"], p["status"])
        for p in POINTERS:
            if p["id"] not in have:
                e = dict(p, sha256=sha256_bytes(read_source(p["path"])), git_commit=last_commit(p["path"]), created=today)
                m["sets"].append(e)
                have[p["id"]] = e
                print("pointer", p["id"])
        save_manifest(m)
    bad = verify(m)
    for i, why in bad:
        print("CHANGED FROZEN SET:", i, why)
    print("verified", sum(1 for e in m["sets"] if e.get("status") == "frozen"), "frozen sets;", len(bad), "problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
