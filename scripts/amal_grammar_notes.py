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


# Her second set of notes (same Doc, edited 2026-09-30): C4b, C5, C6, C7, C8, D1, D3, E1, E2, E5, F3. They change
# rule WORDING only (build_grammar_buckets.py). Every recorded correction under those rules was read against her note;
# none is dropped and none is added. Listed here so a reader can see each was looked at.
OUT_0930 = os.path.join(REPO, "data", "amal-grammar-notes-2026-09-30.json")
SOURCE_0930 = "Amal's notes, Google Doc \"Mahdi's Grammar Rules notes\" (edited 2026-09-30), applied 2026-09-30"
NOTES_0930 = {
    "C4b": "after abel it is always abel ma + present, no b-, even for a past meaning (abel ma aaji = before I came)",
    "C5": "willa is another 'or'; the recorded slip is aw vs willa; wala ana = neither do I",
    "C6": "conditionals need bikoon before an adjective or biddi / 3indi; lamma drops the b-, iza keeps it",
    "C7": "no el, no illi: an indefinite word takes no illi (aktar ishi ba7ebbo, fi u8niyye ba3rafha)",
    "C8": "addaish and kam both = how much / many; kam always takes the singular; kam also = few",
    "D1": "see her Doc 'Arabic Materials' for more",
    "D3": "all prepositions take endings except bi; la-: ili, ilak...; fi: fiyy, fik...",
    "E1": "3-10: the number without its -e/-a ending + the plural noun (5ames da2aaye2)",
    "E2": "tult = 20 past (talaat u tult = 3:20); illa also = except",
    "E5": "kam also means few",
    "F3": "the card explains causative verbs (doubled middle, n-, t-) instead of shadda",
}
KEPT_0930 = {
    "FA-a72c3b35": ("C4b", "abadan + past: the slip is present for a past meaning after abadan, not abel ma - kept."),
    "FA-5fb68cc1": ("C4b", "ma added after daayman (only abadan drags ma) - not about abel ma, kept."),
    "FA-1f2f0f3f": ("C4b", "same moment as 44:08, filed C4 - kept."),
    "FA-dfad5b40": ("C4b", "abadan without ma - kept."),
    "FA-fe29a96e": ("C4b", "abadan ma + present keeps the b- - not abel ma, kept."),
    "FA-95587f34": ("C5", "he reached for willa (ولا) where aw fit; her note names this as THE recorded slip (aw vs "
                          "willa) - kept, wording fixed from 'wala' to 'willa'."),
    "FA-efa0a7b7": ("C5", "extra u between marraat and usboo3 - not about or-words, kept."),
    "FA-8587adb4": ("C6", "lamma used where iza (if) was meant - agrees with her note, kept."),
    "FA-d7a48f3c": ("C6", "lamma + past needs kaan (lamma kunti) - kept."),
    "FA-bb1ccb9b": ("C7", "he wanted illi after aktar ishi; she said no illi - exactly her 'no el, no illi' example, kept."),
    "FA-2e9daa0d": ("C7", "fee hada ili: indefinite hada, she said no illi - agrees with 'no el, no illi', kept."),
    "FA-abcba6ae": ("C7", "question word meen where illi was needed - kept."),
    "FA-93db2190": ("C7", "illi where enno was needed - kept."),
    "FA-1e934159": ("C7", "illi where enno was needed - kept."),
    "FA-aaec4e5a": ("C8", "ayy + plural: singular after ayy, same logic as kam + singular - kept."),
    "FA-9641739c": ("D3", "kaanu ili: la- ending ili as its own word - matches her la- list, kept."),
    "FA-5060cbb4": ("D3", "la- ending: she gave lek - matches her la- list, kept."),
    "FA-63834679": ("D3", "fi + ending (fiyo / fiyyo) - matches her fi list, kept."),
    "FA-5b9ef3b3": ("D3", "he tried bi + el- where fiha was needed; bi takes no ending, fi does - kept."),
    "FA-595c3f41": ("E1", "3-10 + singular saa3a: plural needed - kept."),
    "FA-9c92be40": ("E1", "9 + singular ibn: plural needed - kept."),
    "FA-2c926c84": ("E2", "2:20 said with 'three' instead of tult - she supplied tentain u tult, matches her note, kept."),
    "FA-43fd066c": ("E2", "wrong hour before illa tult - kept."),
    "FA-50c3b4ac": ("E5", "kam + plural - kept (kam = few changes nothing here)."),
    "FA-e8a77db7": ("E5", "kam + plural - kept."),
    "FA-83496534": ("E5", "kam + plural - kept."),
    "FA-9c59e378": ("F3", "zakkerni: extra vowel in a doubled-middle command; filed B10, F3 second - unchanged (F is never "
                          "scored as grammar)."),
}


def write_0930(rows):
    by_uid = {(r.get("uid") or r.get("id")): r for r in rows}
    missing = sorted(set(KEPT_0930) - set(by_uid))
    left = rows_left_after_reread(missing, out_path=OUT_0930, since="2026-09-30", rulings=KEPT_0930)
    missing = [u for u in missing if u not in left]
    assert not missing, "09-30 rows not in the full audit: %s" % missing
    touched = {b: [u for u, r in by_uid.items() if b in (r.get("bucket"), r.get("bucket2"))] for b in NOTES_0930}
    out = {
        "built": "2026-09-30",
        "source": SOURCE_0930,
        "what": "Amal's 11 new notes change rule wording only. Every recorded correction under those rules was read "
                "against her note: 0 dropped, 0 added. Rows not listed in read_and_kept were read too and are untouched "
                "by the notes (e.g. D1 preposition choices, E1 duals).",
        "dropped": [], "added": [],
        "notes": NOTES_0930,
        "corrections_per_rule": {b: len(u) for b, u in touched.items()},
        "read_and_kept": [_line(by_uid[u], {"kind": "kept", "why": why}) for u, (_b, why) in KEPT_0930.items() if u in by_uid],
        "left_after_reread": [left[u] for u in sorted(left)],
        "open_for_medi": "C6 says conditionals REQUIRE bikoon; her B8 note says it is NOT strict after lamma / iza. The 4 "
                         "lamma rows dropped on 09-29 (FA-08b564c1, FA-d2009048, FA-5d2bf797, FA-7d9cfb2c) stay dropped "
                         "until Medi decides.",
    }
    json.dump(out, open(OUT_0930, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", OUT_0930, "- 0 dropped, 0 added;", len(KEPT_0930), "rows read and kept")


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


def rows_left_after_reread(uids, out_path=None, work=None, since="2026-09-29", rulings=None):
    """{uid: line} for ruled rows that left the full audit for a recorded reason since this list was built:
    - the row was rejected under a rule (data/lesson-work/full-audit/rejected.json, uid_at_time; e.g. GR-19 took out the
      fixes Amal only typed in the chat on 2026-10-02: 09-21 11:39 FA-efa0a7b7), or
    - its lesson's readers re-read it after `since` (new tracks / longer transcript) and no longer flag it (date from the
      last written list; 2026-10-02: 09-23 48:45 FA-7d9cfb2c).
    A uid with neither reason is not here: the caller's assert still catches a typo or a lost row."""
    out_path = out_path or OUT
    work = work or os.path.join(REPO, "data", "lesson-work", "full-audit")
    rulings = rulings if rulings is not None else {**KEPT, **DROPPED}
    try:
        prev = json.load(open(out_path, encoding="utf-8"))
    except Exception:
        prev = {}
    known = {x["uid"]: x for k in ("not_counted", "read_and_kept", "left_after_reread") for x in prev.get(k) or [] if x.get("uid")}
    try:
        rejected = {r.get("uid_at_time"): r for r in json.load(open(os.path.join(work, "rejected.json"), encoding="utf-8"))["rows"]}
    except Exception:
        rejected = {}
    left = {}
    for u in uids:
        ruling = rulings.get(u) or ("", "")
        line = {"uid": u, "bucket": ruling[0], "ruling": ruling[1], "kind": "dropped" if u in DROPPED else "kept"}
        if u in rejected:
            r = rejected[u]
            left[u] = {**line, "date": r.get("date"), "t": r.get("t"), "left": "rejected under %s: %s" % (r.get("rule"), r.get("why"))}
            continue
        x = known.get(u)
        if not x or not x.get("date"):
            continue
        man = os.path.join(work, "%s.r1.json.inputs.json" % x["date"])
        try:
            written = str(json.load(open(man, encoding="utf-8")).get("written") or "")[:10]
        except Exception:
            continue
        if written > since:
            left[u] = {**line, "date": x["date"], "t": x.get("t"), "left": "row left the audit when %s was re-read on %s" % (x["date"], written)}
    return left


def main():
    A = json.load(open(AUDIT, encoding="utf-8"))
    rows = [r for r in A["sweep_compat"]["rows"] + A["sweep_compat"].get("unfiled", []) if r.get("mode") == "speaking"]
    uids = {r.get("uid") or r.get("id") for r in rows}
    missing = sorted((set(DROPPED) | set(KEPT)) - uids)
    left = rows_left_after_reread(missing)
    missing = [u for u in missing if u not in left]
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
        "read_and_kept": [_line(by_uid[u], {"kind": "kept", "why": why}) for u, (_b, why) in KEPT.items() if u in by_uid],
        # a ruled row the same-day readers no longer flag after its lesson was re-read (new tracks / longer transcript):
        # nothing left to rule on; kept here with its date so the next run still knows it (2026-10-02: 09-23 48:45)
        "left_after_reread": [left[u] for u in sorted(left)],
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
    write_0930(rows)


if __name__ == "__main__":
    main()
