# -*- coding: utf-8 -*-
"""Remove the 90 fake flashcard answers (test runs, 2026-09-29) still frozen in Medi's live word_stats (FC-08).

The raw rows left card_results on 2026-09-30 (scripts/delete_test_card_rows_2026_09_29.py), but a test's
buckets.recompute_and_store() had already copied 90 of them into word_stats.progress_context.cards at 09:57 UTC.
Every page merges that stored list with card_results, so the fake answers still score 9 Animals words.

    python scripts/delete_fake_card_answers_2026_10_02.py          # dry run: check + show before/after, write nothing
    python scripts/delete_fake_card_answers_2026_10_02.py --yes    # remove exactly those card ids, then verify

Safety: removes ONLY the card ids listed in the frozen file (C:/Claude/reports/anees-fake-card-answers-2026-10-02.json,
or --file). Refuses (nothing written) when the file does not hold exactly 90 ids, when any id is back in card_results,
when a word's stored list holds an id the file does not explain differently than at freeze time, or when a removal would
touch any id outside the file. Each word is written with an updated_at check, so a concurrent rebuild wins and is reported.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEFAULT_FILE = r"C:/Claude/reports/anees-fake-card-answers-2026-10-02.json"
EXPECTED = 90


def plan(spec, current_rows, live_card_ids):
    """-> (problems, updates). updates = [(word_key, updated_at, new_fields, removed_ids, before, after)]."""
    import buckets
    ids = list(spec["fake_card_ids"])
    idset = set(ids)
    probs = []
    if len(ids) != EXPECTED or len(idset) != EXPECTED:
        probs.append(f"file has {len(ids)} ids ({len(idset)} distinct), expected {EXPECTED}")
    back = idset & set(live_card_ids)
    if back:
        probs.append(f"{len(back)} of the ids are in card_results again; stop and look")
    want = {}
    for e in spec["fake_entries"]:
        want.setdefault(e["word_key"], set()).add(e["card"]["id"])
    if set().union(*want.values()) != idset:
        probs.append("fake_entries and fake_card_ids disagree")
    cur = {r["word_key"]: r for r in current_rows}
    updates, already = [], 0
    for key, wids in sorted(want.items()):
        row = cur.get(key)
        if not row:
            probs.append(f"word_stats row {key} is gone"); continue
        ctx = row.get("progress_context") or {}
        cards = ctx.get("cards") or []
        present = {c.get("id") for c in cards} & wids
        if not present:
            already += len(wids); continue
        if present != wids:
            probs.append(f"{key}: {len(present)} of {len(wids)} ids present (partly changed since the freeze)"); continue
        keep = [c for c in cards if c.get("id") not in wids]
        removed = [c.get("id") for c in cards if c.get("id") in wids]
        if not set(removed) <= idset or len(keep) + len(removed) != len(cards):
            probs.append(f"{key}: removal would touch an id outside the file"); continue
        new_ctx = {**ctx, "cards": keep}
        prog = buckets.progress_from_context(new_ctx)
        # Only the card side changes; the Speaking fields (bucket, streaks, weight, last_reviewed) stay exactly as stored.
        fields = {"card_right": prog["card_right"], "card_wrong": prog["card_wrong"],
                  "progress_scores": prog["progress_scores"], "progress_context": new_ctx}
        fb = lambda r: (r.get("progress_scores") or {}).get("flashcards") or {}
        before = {"flashcards": fb(row).get("bucket"), "right": row.get("card_right"), "wrong": row.get("card_wrong"), "attempts": len(cards)}
        after = {"flashcards": fb(fields).get("bucket"), "right": fields["card_right"], "wrong": fields["card_wrong"], "attempts": len(keep)}
        updates.append((key, row["updated_at"], fields, removed, before, after))
    return probs, updates, already


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--file", default=DEFAULT_FILE)
    a = ap.parse_args(argv)
    import db
    spec = json.load(open(a.file, encoding="utf-8"))
    keys = sorted({e["word_key"] for e in spec["fake_entries"]})
    rows = db.select("word_stats", {"word_key": "in.(" + ",".join('"%s"' % k for k in keys) + ")"})
    idlist = "(" + ",".join('"%s"' % i for i in spec["fake_card_ids"]) + ")"
    live = [r["id"] for r in db.select("card_results", {"select": "id", "id": f"in.{idlist}"})]
    probs, updates, already = plan(spec, rows, live)
    if probs:
        print("STOP, nothing written:", "; ".join(probs)); return 1
    n = sum(len(u[3]) for u in updates)
    for key, _, _, removed, before, after in updates:
        print(f"  {key:8} remove {len(removed):2}  flashcards {before['flashcards']} -> {after['flashcards']}  "
              f"right {before['right']} -> {after['right']}  wrong {before['wrong']} -> {after['wrong']}")
    if not updates:
        print(f"nothing to remove: all {already} fake answers are already gone"); return 0
    if not a.yes:
        print(f"dry run: would remove {n} fake answers from {len(updates)} words. Re-run with --yes."); return 0
    done = 0
    for key, stamp, fields, removed, _, _ in updates:
        got = db.rest("PATCH", "word_stats", params={"word_key": f"eq.{key}", "updated_at": f"eq.{stamp}"},
                      body=fields, prefer="return=representation")
        if not got:
            print(f"  {key}: row changed since the check (a rebuild ran?) - skipped; re-run the dry run"); continue
        done += len(removed)
    rows = db.select("word_stats", {"word_key": "in.(" + ",".join('"%s"' % k for k in keys) + ")"})
    left = sum(1 for r in rows for c in (r.get("progress_context") or {}).get("cards", []) if c.get("id") in set(spec["fake_card_ids"]))
    print(f"removed {done} fake answers; {left} left")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
