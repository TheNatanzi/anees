# -*- coding: utf-8 -*-
"""One grammar formula for every page (eng audit 2026-09-29, Medi's decision 6: when two pages disagree, recompute from
raw and make every page read that one number).

Before this file the Lessons page / Overview and the Grammar Console counted "uses" two different ways:
  - Lessons (build_lessons_page_data.py): uses = rule uses the usage detector found in the lesson; when a lesson had
    more corrections than detected uses the % became an "estimate" uses / (uses + slips) and the Overview then LEFT
    THOSE LESSONS OUT of its pooled average (they are the two weakest lessons, so the average was pushed up).
  - Grammar Console (build_grammar_console.py): per rule, a correction with no detected use within 2 s is itself a use
    (he tried the rule), so a rule never has more mistakes than uses; rules with no detector at all are "Unscored".
Σ uses over lessons (1,712) and Σ uses over rules (2,237) did not match.

The one rule now, for a rule r and a lesson d:
    uses(r, d)     = detected uses of r in d  +  corrections of r in d that no detected use (same lesson, ±2 s) pairs with
    mistakes(r, d) = corrections of r in d (Amal voiced or typed; rows her notes take out are not corrections)
    scored rule    = r has a usage detector that fired at least once in any lesson, r is taught, r is not a sound (F).
Rule score   = 1 - Σ_d mistakes / Σ_d uses                 (scored rules only)
Lesson score = 1 - Σ_r mistakes / Σ_r uses                 (scored rules only)
Corrections of an unscored rule (e.g. B18, no detector) are still shown and counted as slips, but not in any %: with no
counter of his right uses, the rule would read 0 % for lack of a counter, not for lack of skill (same reason the
console shows them "Unscored"). So Σ over lessons == Σ over rules, and mistakes <= uses everywhere, by construction.
"""
import collections

NO_USAGE_SCORE = {"F1", "F2", "F3"}   # sounds, not grammar (wiki/18 rule M4): never a grammar use
PAIR_WINDOW = (0, -1, 1, -2, 2)       # seconds: a correction pairs with a detected use this close to his line


def pair(uses, slips):
    """uses / slips: lists of {"date", "t"} for ONE rule. Returns {date: extra} = corrections no detected use pairs with.
    Greedy, one use per correction, corrections newest first (the console's historical order, so counts do not move)."""
    free = collections.Counter((u["date"], int(u["t"])) for u in uses if u.get("t") is not None)
    extra = collections.Counter()
    for c in sorted(slips, key=lambda c: (c["date"], c["t"] if c.get("t") is not None else 0), reverse=True):
        hit = None
        if c.get("t") is not None:
            hit = next(((c["date"], int(c["t"]) + k) for k in PAIR_WINDOW if free.get((c["date"], int(c["t"]) + k))), None)
        if hit:
            free[hit] -= 1
        else:
            extra[c["date"]] += 1
    return dict(extra)


def table(usage_uses, slips, bucket_ids, not_taught=lambda b: False):
    """usage_uses = grammar-usage.json["uses"] ({bucket: [{date, t, ...}]}); slips = [{"bucket", "date", "t"}] counted
    corrections (Amal-ruled rows already removed). Returns {bucket: {...}} with per-lesson and total uses / mistakes."""
    by_b = collections.defaultdict(list)
    for s in slips:
        by_b[s["bucket"]].append(s)
    out = {}
    for b in bucket_ids:
        nt = bool(not_taught(b))
        u = [] if b in NO_USAGE_SCORE else list(usage_uses.get(b, []))
        mine = by_b.get(b, [])
        extra = pair(u, mine)
        det = collections.Counter(x["date"] for x in u)
        mis = collections.Counter(s["date"] for s in mine)
        dates = sorted(set(det) | set(mis))
        per = {d: {"detected": det[d], "extra": extra.get(d, 0), "uses": det[d] + extra.get(d, 0), "mistakes": mis[d]} for d in dates}
        scored = bool(u) and not nt
        why = ("not taught yet (Amal's notes)" if nt else "a sound, not grammar" if b in NO_USAGE_SCORE
               else "no usage detector: only corrections are on record" if mine and not u else None if u else "never used")
        out[b] = {"scored": scored, "why_unscored": None if scored else why, "not_taught": nt,
                  "detected": len(u), "extra": sum(extra.values()),
                  "uses": 0 if nt else len(u) + sum(extra.values()) if b not in NO_USAGE_SCORE else 0,
                  "mistakes": 0 if nt else len(mine), "by_date": per}
    return out


def pct(uses, mistakes, ndigits=1):
    if not uses:
        return None
    v = 100 * (uses - mistakes) / uses
    return round(v, ndigits) if ndigits is not None else round(v)


def lesson(tbl, date):
    """The lesson's grammar numbers from the rule table (scored rules only in the %)."""
    uses = mis = unscored = 0
    for b, r in tbl.items():
        x = r["by_date"].get(date)
        if not x or r["not_taught"]:
            continue
        if r["scored"]:
            uses += x["uses"]
            mis += x["mistakes"]
        else:
            unscored += x["mistakes"]
    return {"uses": uses, "scored_mistakes": mis, "unscored_mistakes": unscored, "pct": pct(uses, mis)}


def totals(tbl):
    s = [r for r in tbl.values() if r["scored"]]
    return {"uses": sum(r["uses"] for r in s), "mistakes": sum(r["mistakes"] for r in s),
            "unscored_mistakes": sum(r["mistakes"] for r in tbl.values() if not r["scored"] and not r["not_taught"])}
