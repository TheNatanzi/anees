# -*- coding: utf-8 -*-
"""The hold: nothing the 2026-10-04 re-read created is put in front of Amal until Medi says so.

data/lesson-work/full-audit/hold-from-amal.json (written by `python scripts/rehear_rejudge.py hold`):
  uids    audit rows the re-read created (not in rehear/rejudge/before.json; carried and kept rows are not held)
  before  what was on her lists on origin/master when the hold was made: {"review": [row uids], "new_words": [card ids],
          "verify": [row uids], "ledger": [card ids]}. While the hold file exists a list shows only what it showed
          before, so a carried row that changed (A -> B, another wording) cannot become a new question either.
  dates   the lessons that were re-read. The 'only what it showed before' rule covers these lessons only, so a lesson
          taught after the re-read still reaches her lists normally.
The builders of her lists ask Hold().blocks(...). A held row still counts on Medi's pages exactly as the build decides;
only her lists skip it. No file = nothing is blocked and every builder writes exactly what it wrote before.
Release: Medi's OK = delete the file (or take a uid out of `uids` and add its id to `before`), then rebuild.
"""
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLD_P = os.path.join(REPO, "data", "lesson-work", "full-audit", "hold-from-amal.json")


class Hold:
    def __init__(self, path=None, doc=None):
        path = path or HOLD_P
        if doc is None and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        self.active = doc is not None
        self.uids = set((doc or {}).get("uids") or [])
        self.before = {k: set(v) for k, v in ((doc or {}).get("before") or {}).items() if v is not None}
        self.dates = set((doc or {}).get("dates") or [])

    def uid(self, uid):
        """True when this audit row was created by the re-read and waits for Medi's OK."""
        return self.active and uid in self.uids

    def blocks(self, kind, ident, uid=None, date=None):
        """True when item `ident` of her list `kind` must not be shown: its row is held, or it belongs to a re-read lesson
        (`date`; unknown date = treated as re-read) and was not on that list before."""
        if not self.active:
            return False
        if uid is not None and uid in self.uids:
            return True
        if date is not None and self.dates and date not in self.dates:
            return False
        return kind in self.before and ident not in self.before[kind]


# ---------------------------------------------------------------- the repeat-review hold (Codex final approval round 5)
ALREADY_P = os.path.join(REPO, "data", "lesson-work", "full-audit", "amal-already-ruled.json")


class AlreadyRuled:
    """data/lesson-work/full-audit/amal-already-ruled.json (written by `python scripts/rehear_rejudge.py already-ruled`):
    re-read B rows (a new uid) that sit within 5 s, in the same lesson, of a moment Amal ALREADY ruled on and whose old
    uid was not carried. Asking her again would repeat a question she answered, so the builders of her lists (review
    list, check list, ledger cards) skip these uids; they go to the owner instead (rehear/rejudge/owner-review.json).
    Proximity only routes the review: it transfers no ruling, merges no row and changes no score - the row stays a B row
    everywhere else. A different, narrower file than the hold above. No file = nothing is skipped."""
    def __init__(self, path=None, doc=None):
        path = path or ALREADY_P
        if doc is None and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        self.active = doc is not None
        self.uids = set((doc or {}).get("uids") or {})

    def uid(self, uid):
        return self.active and uid in self.uids
