# -*- coding: utf-8 -*-
"""Undo of Amal's taps (AM-17, Medi 2026-10-02: "can you add an undo button to all these tutor hub stuff").

Undo never deletes a row. The page writes a NEW amal_rules row: the same token / source / lesson_date / word_key as the
tap, kind 'undo', payload {undoes: <kind>, match: {...} | null, target_id: <id> | absent}. The latest action per item
wins: an undo cancels every earlier tap of the same item (source + lesson_date + word_key, and the payload fields in
`match` when given - e.g. the second of an after-lesson question, or the text of a grammar note); a tap after the undo
counts again (tap -> undo -> tap).

    resolve(rows)  -> Resolved(kept, undone, undos)   kept = the taps that still count (input order, undo rows removed)
    honour(rows)   -> kept

scripts/db.py runs this on every amal_rules / amal_rules_public select (pass undo=False for the raw history, e.g. the
trigger fingerprints in scripts/amal_trigger.py), so every consumer honours undo without its own code."""
from collections import namedtuple

UNDO = "undo"
Resolved = namedtuple("Resolved", "kept undone undos")   # undone: {tap id or index: the undo row}


def _order(r, i):
    rid = r.get("id")
    return (0, rid, i) if isinstance(rid, (int, float)) else (1, str(r.get("created_at") or ""), i)


def _same_item(tap, undo):
    if tap.get("kind") == UNDO:
        return False
    for k in ("source", "word_key", "lesson_date"):      # not the token: her link changes, the item does not
        if k in tap and k in undo and (tap.get(k) or None) != (undo.get(k) or None):
            return False
    up = undo.get("payload") if isinstance(undo.get("payload"), dict) else None
    if up and up.get("target_id") is not None:
        return tap.get("id") == up["target_id"]
    match = (up or {}).get("match") or {}
    if match:
        tp = tap.get("payload") if isinstance(tap.get("payload"), dict) else None
        if tp is None:              # a view without payload (amal_rules_public): cannot tell the items apart -> keep the tap
            return False
        return all(tp.get(k) == v for k, v in match.items())
    if undo.get("word_key") in (None, ""):
        return False                # no key, no match, no target: never guess which tap it meant
    return True


def resolve(rows):
    rows = list(rows or [])
    idx = sorted(range(len(rows)), key=lambda i: _order(rows[i], i))
    live, undone, undos = [], {}, []
    for i in idx:
        r = rows[i]
        if r.get("kind") == UNDO:
            undos.append(r)
            for j in list(live):
                if _same_item(rows[j], r):
                    live.remove(j)
                    undone[rows[j].get("id", j)] = r
            continue
        live.append(i)
    keep = set(live)
    return Resolved([rows[i] for i in range(len(rows)) if i in keep], undone, undos)


def honour(rows):
    return resolve(rows).kept
