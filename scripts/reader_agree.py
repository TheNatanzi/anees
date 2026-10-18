# -*- coding: utf-8 -*-
"""PR-25: the two slip readers are Opus + Sonnet, and a slip stands only when BOTH flagged it (Medi 2026-10-15: "Yes:
build the Opus + Sonnet both-agree reader into the app, confirm it on the next fully reviewed lesson, and push it through
the publish guard.").

Evidence (data/lesson-work/reader-tiers/runs/debate-results-2026-10-15.json): one read each on 10-08/09/10, pooled over 102
key slips, F0.5 both-agree 69.6 (precision 68.5, recall 74.5) vs Opus alone 65.0, Sonnet alone 61.9, either 58.4, a
cross-judging debate 65.0; both-agree won on every lesson (70.7 / 68.5 / 69.8). Adopted on dev; it must win again on the
next exam lesson (protocol section 6) - `confirm` scores it there automatically once that key freezes.

The rule (the scorer's own match, scripts/reader_tiers.py): a settled row that is a slip (vocab or grammar, any A/B kind,
never a tier-3 vocab row) is KEPT when reader r1 (Opus) flagged a slip of the same family within 15 s of it AND reader r2
(Sonnet) did too. Otherwise it is HELD, "one reader only": listed on AI Reports > Grades, never a ✗ chip, never sent to
the tutor. Rows that are not slips pass through.

Which lessons: only a lesson whose two reader files were written by this pair (their .inputs.json manifests carry the
model, scripts/review_lesson.py), so every lesson read before 2026-10-15 keeps its chips exactly as they are.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

R1_MODEL = "claude-opus-5-5"
R2_MODEL = "claude-sonnet-5-5"
EFFORT = "high"
MODELS = {"r1": R1_MODEL, "r2": R2_MODEL}
WINDOW_S = 15.0
HELD = "held: one reader only"


def _J(p, d=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def sec(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    try:
        p = [float(x) for x in str(t).strip().split(":")]
    except ValueError:
        return None
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def family(kind, tier=None):
    """vocab / grammar for a row that can become a ✗ (scripts/reader_tiers.family, the scorer's own rule)."""
    k = str(kind or "")
    if k.startswith("vocab") and tier != 3:
        return "vocab"
    return "grammar" if k.startswith("grammar") else None


def flags(rows):
    """[(family, seconds)] of a reader's slip rows."""
    out = []
    for r in rows or []:
        f, t = family(r.get("kind"), r.get("tier")), sec(r.get("t"))
        if f and t is not None:
            out.append((f, t))
    return out


def flagged(fl, f, t, window=WINDOW_S):
    return any(g == f and abs(u - t) <= window for g, u in fl)


def gate(rows, r1_rows, r2_rows, window=WINDOW_S):
    """(kept, held): a slip row is kept only when both readers flagged a slip of its family within `window` s."""
    a, b = flags(r1_rows), flags(r2_rows)
    kept, held = [], []
    for r in rows:
        f, t = family(r.get("kind"), r.get("tier")), sec(r.get("t"))
        if not f or t is None:
            kept.append(r)
            continue
        ia, ib = flagged(a, f, t, window), flagged(b, f, t, window)
        if ia and ib:
            kept.append(r)
        else:
            held.append(dict(r, held=HELD, flagged_by=("r1 (Opus)" if ia else "r2 (Sonnet)" if ib else "neither reader (third reader only)")))
    return kept, held


# PR-27 (Medi 2026-10-17 "Ship the rule and fix"; overnight test: flags on these signals were real slips only 18% / 26% of
# the time, and dropping them added 5-10 F0.5 to every reader): the grade book never scores a moment where he only ASKED
# for a word (asked = half credit) and never a voiced (A-kind) slip with NO reaction from the tutor. Such a row is held,
# listed, never a chip. Let-pass (B-kind) rows keep going to the tutor's review as before: only her yes makes them a slip.
HELD_SIGNAL = "held: asked for a word or no reaction from the tutor (PR-27)"


def signal_of(r):
    return (str(r.get("signal") or "none").split() or ["none"])[0].strip(",;").lower()


def signal_gate(rows):
    """(kept, held): an 'asked' row, or an A-kind slip row with no tutor reaction, is held - never a chip."""
    kept, held = [], []
    for r in rows:
        f, k, s = family(r.get("kind"), r.get("tier")), str(r.get("kind") or ""), signal_of(r)
        if f and (s == "asked" or (s == "none" and not k.endswith("-B"))):
            held.append(dict(r, held=HELD_SIGNAL))
        else:
            kept.append(r)
    return kept, held


def pair_of(date, work):
    """{'r1': model, 'r2': model} from the reader files' manifests (None for a file written before PR-25)."""
    out = {}
    for r in ("r1", "r2"):
        m = _J(os.path.join(work, "%s.%s.json.inputs.json" % (date, r))) or {}
        out[r] = m.get("model")
    return out


def active(date, work):
    """True when this lesson's two readers were the PR-25 pair."""
    return pair_of(date, work) == MODELS


# ------------------------------------------------------------------ confirmation on the next exam (protocol section 6)

def score(pred, key_slips):
    """precision / recall / F0.5 of [(family, t)] against [(family, t)], one-to-one nearest within 15 s (reader_tiers)."""
    import reader_tiers as RT
    return RT.prf(RT.match(pred, key_slips), len(pred), len(key_slips))


def confirm(date, work, key, settled=None, r1=None):
    """Both-agree (the settled ✗ rows) vs Opus alone (reader r1's rows) on one frozen key -> dict, or None when the lesson
    was not read by the PR-25 pair or has no settled file."""
    if not active(date, work):
        return None
    settled = settled if settled is not None else _J(os.path.join(work, date + ".settled.json"))
    r1 = r1 if r1 is not None else _J(os.path.join(work, date + ".r1.json"))
    if not settled or not r1:
        return None
    ks = [(s["k"], float(s["i"])) for s in key.get("slips") or [] if s.get("k") in ("vocab", "grammar")]
    both = score(flags(settled.get("rows")), ks)
    opus = score(flags(r1.get("rows")), ks)
    won = both["f05"] > opus["f05"]
    return {"kind": "reader both-agree (PR-25)", "date": date, "lessons": [date], "base": "Opus alone",
            "both_agree": both, "opus_alone": opus, "won": won, "adopted": True,
            "flag": None if won else "Both-agree did NOT beat Opus alone on %s (F0.5 %.1f vs %.1f): tell the student; "
                                     "no silent roll-back" % (date, both["f05"], opus["f05"])}


def held_rows(work, dates=None):
    """Every held 'one reader only' row of the settled lessons, newest first, for AI Reports > Grades."""
    out = []
    names = sorted(os.listdir(work)) if os.path.isdir(work) else []
    for n in names:
        if not n.endswith(".settled.json") or n.count(".") != 2:
            continue
        d = n[:-len(".settled.json")]
        if dates and d not in dates:
            continue
        for r in (_J(os.path.join(work, n)) or {}).get("held_one_reader") or []:
            out.append({"date": d, "t": r.get("t"), "kind": r.get("kind"), "wrong": r.get("wrong"), "right": r.get("right"),
                        "flagged_by": r.get("flagged_by"), "why": str(r.get("why") or "")[:160]})
    out.sort(key=lambda x: (x["date"], sec(x["t"]) or 0), reverse=True)
    return out
