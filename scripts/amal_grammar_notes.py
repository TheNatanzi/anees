# -*- coding: utf-8 -*-
"""Amal's written notes on the grammar rules, as scoring rulings.

Source: Amal's Google Doc "Mahdi's Grammar Rules notes" (edited 2026-09-27). Medi said "apply" on 2026-09-29.
The rule TEXT lives in scripts/build_grammar_buckets.py (and docs/amal/grammar-rules.html, wiki/18). This file holds
what her notes change in the SCORING, so every builder that counts grammar corrections applies the same rulings:

    scripts/build_grammar_console.py     -> docs/data/grammar-console.json (console, Amal's page, Progress & Stats)
    scripts/build_lessons_page_data.py   -> docs/data/lessons.json + docs/data/lessons/<date>.json (Lessons page)

Two kinds of ruling (nothing is ever deleted - S2; a ruled row stays visible with its reason, it just does not count):

  not-taught  the row's rule is one Amal has not taught yet (B14 3am, B15 participles: "part of the present
              progressive lesson"). The rule shows "Not taught yet", has no score, and is left out of every total.
  dropped     Amal's note says what he did is not a mistake. Judged by hand, by meaning in context (the machine
              flags are only clues - memory rule 2026-09-25), one row at a time, listed in DROPPED below.

Run this file to write the audit list data/amal-grammar-notes-2026-09-29.json (every ruled row, with date, time,
what he said and the reason, plus the rows that were read and KEPT, and the -et count for Medi):

    python scripts/amal_grammar_notes.py
"""
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
OUT = os.path.join(REPO, "data", "amal-grammar-notes-2026-09-29.json")

SOURCE = "Amal's notes, Google Doc \"Mahdi's Grammar Rules notes\" (edited 2026-09-27), applied 2026-09-29"

# B13 in her headings = our B14. Both are "part of the (future) present progressive lesson".
NOT_TAUGHT = {
    "B14": "Not taught yet - part of the future present-progressive lesson (Amal, 2026-09-27).",
    "B15": "Not taught yet - part of the present-progressive lesson (Amal, 2026-09-27).",
}

# Rows her notes say are NOT mistakes. Keyed by the full audit's stable uid.
DROPPED = {
    # B7 "the b-drop note is not correct in all cases; do NOT mark b-drop after kan as a rule - some keep it, some drop it"
    "FA-50065cf6": ("B7", "b- kept or dropped right after kaan is not a rule; he said kaan 5awwaf (no b-), she recast "
                          "kaan bey5awwef. Amal: some verbs keep it, some drop it - not marked wrong."),
    # B8 "in past and future it's REQUIRED; the conditional case is NOT strict"
    "FA-08b564c1": ("B8", "missing ykoon after lamma (lamma ... ma 3indo -> lamma ma ykoon 3indo). Amal: after "
                          "lamma / iza bikoon is not strict."),
    "FA-d2009048": ("B8", "missing bakoon after lamma (lamma ana kasool -> lamma ana bakoon kasool). Amal: after "
                          "lamma / iza bikoon is not strict."),
    "FA-5d2bf797": ("B8", "same moment as 42:37 (lamma ana kasool); missing bakoon after lamma. Amal: after lamma / "
                          "iza bikoon is not strict."),
    "FA-7d9cfb2c": ("B8", "missing ykoon after lamma (lamma maw3ed el-dars badri -> lamma maw3ed el-dars ykoon "
                          "badri). Amal: after lamma / iza bikoon is not strict."),
}

# Rows read against her notes and KEPT, with why - so a reader can see they were looked at, not missed.
KEPT = {
    "FA-2585979c": ("B8", "habitual 'always' (daiman beykoon): Amal lists habits as a bikoon use and does not call "
                          "them optional - kept."),
    "FA-e6ef83c1": ("B8", "bakoon + bare verb in the plain present (bakun khaf for 'I am scared'): a misuse of bakoon, "
                          "not a missing one - kept."),
    "FA-e3de7919": ("B8", "'she would be' (bitkoon) in the result part of an iza sentence: he had no verb at all and "
                          "reached for 'name'; not the lamma / iza clause itself - kept (borderline, asked Medi)."),
    "FA-d4d22e4a": ("B8", "iza akoon -> iza bakoon: he DROPPED the b- after iza. Amal: iza keeps the b - still a "
                          "mistake, kept."),
    "FA-a378b8b3": ("B3", "iza ma ashoofak -> iza ma bashoofak: he dropped the b- after iza; iza keeps it - kept."),
    "FA-be2aa24b": ("C6", "iza ma + b-verb: she wanted the b- kept after iza - agrees with her note, kept."),
    "FA-d44e5f54": ("B7", "lebena -> kunna nel3ab: bare past where 'were playing' (kaan + verb, past continuous) was "
                          "needed - not about the b-, kept."),
    "FA-907e9e01": ("B12", "the slip is the get-form vs make-form; the kaan + b- remark is his own, not the error - kept."),
    "FA-d5b0426a": ("B2", "ma kaan 2asdhom + past verb: the verb follows 2asdhom (intention), not kaan; the error is "
                          "past vs bare present - kept."),
    "FA-dec56969": ("B16", "laazem + past verb (laazem eshta8alt): the trigger is laazem, not kaan - kept."),
    "FA-79cd4e3b": ("B5", "3am used where the past 3emel was needed: filed as a past-tense slip, 3am is only the "
                          "second rule - kept in B5."),
}


def ruling(row):
    """None if the row counts as before; else {"kind": "not-taught"|"dropped", "rule", "why", "source"}."""
    uid = row.get("uid") or row.get("id")
    if uid in DROPPED:
        rule, why = DROPPED[uid]
        return {"kind": "dropped", "rule": rule, "why": why, "source": SOURCE}
    b = row.get("bucket")
    if b in NOT_TAUGHT:
        return {"kind": "not-taught", "rule": b, "why": NOT_TAUGHT[b], "source": SOURCE}
    return None


def not_taught(bucket_id):
    return bucket_id in NOT_TAUGHT


def _line(r, ru=None):
    return {"uid": r.get("uid") or r.get("id"), "date": r["date"], "t": r.get("t") or r.get("t_amal"),
            "bucket": r.get("bucket"), "bucket2": r.get("bucket2"),
            "he_said": r.get("medi_said"), "amal_said": r.get("amal_said"),
            "wrong": r.get("wrong"), "right": r.get("right"),
            **({"kind": ru["kind"], "reason": ru["why"]} if ru else {})}


def main():
    A = json.load(open(AUDIT, encoding="utf-8"))
    rows = [r for r in A["sweep_compat"]["rows"] + A["sweep_compat"].get("unfiled", []) if r.get("mode") == "speaking"]
    uids = {r.get("uid") or r.get("id") for r in rows}
    missing = sorted((set(DROPPED) | set(KEPT)) - uids)
    assert not missing, "rulings name rows that are not in the full audit: %s" % missing

    ruled = [(_line(r, ruling(r))) for r in rows if ruling(r)]
    per_rule = {}
    for x in ruled:
        k = "%s %s" % (x["kind"], x["bucket"] if x["kind"] == "not-taught" else DROPPED[x["uid"]][0])
        per_rule[k] = per_rule.get(k, 0) + 1
    by_uid = {(r.get("uid") or r.get("id")): r for r in rows}

    # A1: how many A1 corrections were sun / moon letter slips (her note: never an error)
    a1 = [r for r in rows if r.get("bucket") == "A1"]
    sun = [r for r in a1 if re.search(r"sun[- ]letter|moon[- ]letter|assimil|shams", " ".join(
        str(r.get(k) or "") for k in ("mistake", "wrong", "right")), re.I)]

    # B5: corrections where the she-past ending -et is involved (Medi decides; not re-scored)
    et = ["FA-569ee5ef"]
    # B11: 'la' + you-form as a negative command (her note: 'la' is fus7a; an error, counted as B11)
    la = [r for r in rows if re.search(r"(^|\s)(لا\s+ت|la\s+t)", (r.get("medi_said") or "") + " " + (r.get("wrong") or ""), re.I)
          and r.get("bucket") == "B11"]

    out = {
        "built": "2026-09-29",
        "source": SOURCE,
        "what": "Every grammar correction Amal's notes take out of the count (kind 'dropped' = her note says it is not a "
                "mistake; kind 'not-taught' = its rule is not taught yet, shown but uncounted). Nothing is deleted: the "
                "rows stay in data/full-audit-2026-09-26.json and on the pages, marked 'not counted' with this reason.",
        "counts": dict(sorted(per_rule.items())),
        "total_not_counted": len(ruled),
        "not_counted": sorted(ruled, key=lambda x: (x["bucket"] or "", x["date"], x["t"] or "")),
        "read_and_kept": [_line(by_uid[u], {"kind": "kept", "why": why}) for u, (_b, why) in KEPT.items()],
        "checks": {
            "A1_corrections": len(a1),
            "A1_sun_moon": len(sun),
            "A1_note": "None of the A1 corrections is a sun/moon-letter slip; all are el- there / not there, which still "
                       "counts. The usage detector never marks a wrong use, so there was nothing to remove there.",
            "B3_iza_keeps_b": "No correction marks a b- kept after iza as wrong (3 rows read: FA-d4d22e4a, FA-a378b8b3, "
                              "FA-be2aa24b all go the same way as her note). The B3 detector never listed iza.",
            "B5_she_et": [_line(by_uid[u]) for u in et],
            "B5_note": "1 correction involves -et as the she-ending: 09-18 06:49, he said 'zehe-at', Amal recast the "
                       "she-form as zhe2et (her own -et). His slip was the extra vowel. Not re-scored - Medi decides.",
            "B11_la_corrections": [_line(r) for r in la],
            "B11_note": "'la' + verb as a negative command counts as a B11 mistake when Amal corrects it (every B11 "
                        "correction counts). None on record so far.",
        },
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", OUT)
    print("not counted:", len(ruled), per_rule)
    print("A1:", len(a1), "corrections,", len(sun), "sun/moon")


if __name__ == "__main__":
    main()
