# -*- coding: utf-8 -*-
"""Eng audit 2026-09-29 (area 2, decision 6): one grammar formula on every page.

The Lessons page counted a lesson's grammar uses as detected uses only; the Grammar Console also counts a fixed slip that
no detected use pairs with as a use. Σ over lessons (1,712) != Σ over the console's rules (2,178 scored), two lessons
showed more slips than uses (09-16 57/52, 09-18 45/23) and the Overview then left them out of its average."""
import json
from pathlib import Path

import grammar_math as GM

ROOT = Path(__file__).resolve().parent.parent


def test_a_fix_with_no_counted_use_is_a_use():
    uses = [{"date": "d1", "t": 10.0}, {"date": "d1", "t": 50.0}]
    slips = [{"date": "d1", "t": 11.0}, {"date": "d1", "t": 90.0}]       # 11 s pairs with the use at 10 s; 90 s pairs with none
    assert GM.pair(uses, slips) == {"d1": 1}
    T = GM.table({"A1": uses}, [dict(s, bucket="A1") for s in slips], ["A1", "B18"])
    assert T["A1"]["uses"] == 3 and T["A1"]["mistakes"] == 2 and T["A1"]["scored"]
    assert GM.lesson(T, "d1") == {"uses": 3, "scored_mistakes": 2, "unscored_mistakes": 0, "pct": 33.3}


def test_rule_with_no_counter_is_listed_not_scored():
    T = GM.table({}, [{"bucket": "B18", "date": "d1", "t": 5.0}], ["B18"])
    assert not T["B18"]["scored"] and T["B18"]["mistakes"] == 1
    assert GM.lesson(T, "d1") == {"uses": 0, "scored_mistakes": 0, "unscored_mistakes": 1, "pct": None}


def test_not_taught_rule_is_out_of_every_total():
    T = GM.table({"B14": [{"date": "d1", "t": 1.0}]}, [], ["B14"], not_taught=lambda b: b == "B14")
    assert T["B14"]["uses"] == 0 and not T["B14"]["scored"]


def test_published_lessons_and_console_agree():
    """The built files: Σ lesson uses == Σ scored-rule uses, no lesson has more scored slips than uses, no estimates."""
    L = json.load(open(ROOT / "docs" / "data" / "lessons.json", encoding="utf-8"))["lessons"]
    C = json.load(open(ROOT / "docs" / "data" / "grammar-console.json", encoding="utf-8"))
    scored = [r for r in C["rules"] if r["status"] in ("Mastered", "Good", "Shaky", "Wrong")]
    assert sum(x["grammar"]["uses"] or 0 for x in L) == sum(r["uses"] for r in scored)
    for x in L:
        g = x["grammar"]
        assert not g.get("estimate"), x["date"]
        assert g.get("scored_mistakes", g["mistakes"]) <= (g["uses"] or 0), x["date"]
