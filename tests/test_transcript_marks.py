# -*- coding: utf-8 -*-
"""PG-20 transcript marks (scripts/transcript_marks.py -> docs/data/lessons/<date>.json tmarks / marks_report).
Medi 2026-10-02: "for the transcript lets put check marks and xs for incorrect correct and mark vocab or grammar with
grammar rule", "mark amals signal for correction too", "underline the word thats wrong"."""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import transcript_marks as TM  # noqa: E402

BUCKETS = {"B6": {"name": "kan"}, "A2": {"name": "idafa"}}


def _turns():
    return [
        {"t": 10.0, "end": 12.5, "who": "Medi", "text": "أنا كانت هون امبارح"},
        {"t": 13.0, "end": 14.0, "who": "Amal", "text": "لا، كنت هون."},
        {"t": 20.0, "end": 22.0, "who": "Medi", "text": "بس الكتاب"},
        {"t": 30.0, "end": 31.0, "who": "Medi", "text": "allo, yes, customer"},
    ]


def _detail():
    return {"turns": _turns(),
            "vocab_correct": [{"t": 20.4, "kind": "correct", "arabizi": "Bass", "arabic": "بس", "word_key": "bas"}],
            "vocab_errors": [], "not_errors": [], "grammar_not_counted": [],
            "grammar_errors": [{"t": 10, "t_fix": 13, "bucket": "B6", "bucket_name": "kan", "wrong": "كانت", "right": "كنت",
                                "signal": "explicit-no", "id": "FA-1"}]}


def test_PG_20_find_span_normalises_and_flags_closest():
    assert TM.find_span("Uh, واحدة وواحد و...", "واحدة")[2] == "exact"
    assert TM.find_span("شنطة الـ شغل", "الشغل")[:2] == [5, 12]
    assert TM.find_span("إنتِ رحتي", "انت")[2] == "exact"              # hamza + diacritic
    assert TM.find_span("مدرسة", "مدرسه")[2] == "exact"                 # taa marbuta
    assert TM.find_span("بتصور كتير", "بصور")[2] == "closest"
    assert TM.find_span("hello there", "مش هون") is None


def test_PG_20_slip_lands_on_his_line_and_her_fix_is_linked_both_ways():
    tm, rep = TM.build("2026-10-01", _detail(), {"B6": [{"date": "2026-10-01", "t": 10.0, "hit": "كانت"},
                                                       {"date": "2026-10-01", "t": 20.0, "hit": "كان"}]},
                       BUCKETS, lambda b: False, off_lesson=[{"from": "00:29", "to": "00:40", "what": "customer call"}])
    medi = tm["0"]["c"]
    x = [c for c in medi if c["s"] == "wrong"][0]
    assert x["k"] == "grammar" and x["rule"] == "B6" and x["sig"] == "says no"
    fix = tm["1"]["c"][0]
    assert fix["k"] == "fix" and fix["link"] == x["id"] and x["link"] == fix["id"]
    # the use paired with the slip is not also a ✓; the other use is
    assert not any(c["s"] == "correct" for c in medi)
    assert any(c["s"] == "correct" and c.get("rule") == "B6" for c in tm["2"]["c"])
    assert any(c["k"] == "vocab" and c["s"] == "correct" for c in tm["2"]["c"])
    # underlines: his wrong word red on his line, her fix green on hers, tied to the chips
    u = tm["0"]["u"][0]
    assert u[2:4] == ["wrong", x["id"]] and _turns()[0]["text"][u[0]:u[1]] == "كانت"
    assert tm["1"]["u"][0][2:4] == ["fix", fix["id"]]
    # off-lesson turn: grey with the reason, not scored
    assert tm["3"]["c"][0]["s"] == "na" and "customer call" in tm["3"]["c"][0]["why"]
    assert rep["scored"] == rep["placed"] == 3 and rep["fix_wanted"] == rep["fix_placed"] == 1


def test_PG_20_amal_ruling_is_not_a_voiced_signal():
    d = _detail()
    d["grammar_errors"][0]["signal"] = "amal-ruling"
    tm, rep = TM.build("2026-10-01", d, {}, BUCKETS, lambda b: False)
    assert rep["fix_wanted"] == 0 and "1" not in tm
    assert [c for c in tm["0"]["c"] if c["s"] == "wrong"][0]["sig"] == "confirmed on her review page"


def _lessons():
    return sorted(glob.glob(os.path.join(ROOT, "docs", "data", "lessons", "*.json")))


def test_PG_20_every_scored_item_lands_on_exactly_one_medi_turn():
    """Per lesson: chips placed == report placed, placed + missed == scored, each chip on one turn only, every vocab /
    grammar chip on a Medi turn, misses at most 2 % (listed in marks_report.missed)."""
    for f in _lessons():
        x = json.load(open(f, encoding="utf-8"))
        r, tm = x["marks_report"], x["tmarks"]
        ids, scored_chips = [], 0
        for k, v in tm.items():
            turn = x["turns"][int(k)]
            for c in v["c"]:
                ids.append(c["id"])
                if c["k"] in ("vocab", "grammar") and c["s"] != "na":
                    scored_chips += 1
                    assert turn["who"] == "Medi", (f, k, c)
                if c["k"] == "fix":
                    assert turn["who"] in ("Amal", "chat"), (f, k, c)
        assert len(ids) == len(set(ids)), f
        assert scored_chips == r["placed"], (f, scored_chips, r["placed"])
        assert r["placed"] + len(r["missed"]) == r["scored"], f
        on_sheet = sum(1 for e in x["vocab_errors"] if e.get("on_sheet") is not False)
        assert r["scored"] >= len(x["vocab_correct"]) + on_sheet + len(x["grammar_errors"]), f
        assert len(r["missed"]) <= max(2, 0.02 * r["scored"]), (f, r["missed"])


def test_PG_20_every_voiced_slip_fix_lands_on_one_amal_turn_linked_back():
    for f in _lessons():
        x = json.load(open(f, encoding="utf-8"))
        r, tm = x["marks_report"], x["tmarks"]
        chips = {c["id"]: c for v in tm.values() for c in v["c"]}
        fixes = [c for c in chips.values() if c["k"] == "fix"]
        assert len(fixes) == r["fix_placed"], f
        assert r["fix_placed"] + len(r["fix_missed"]) == r["fix_wanted"], f
        for c in fixes:
            assert chips[c["link"]]["link"] == c["id"] and chips[c["link"]]["s"] in ("wrong", "asked"), (f, c)
        voiced = sum(1 for g in x["grammar_errors"] if g.get("signal") in TM.VOICED and g.get("t_fix") is not None)
        assert r["fix_wanted"] >= voiced - len(r["missed"]), f
        assert len(r["fix_missed"]) <= max(2, 0.05 * r["fix_wanted"]), (f, r["fix_missed"])


def test_PG_20_underlines_point_at_real_chips_and_are_counted():
    for f in _lessons():
        x = json.load(open(f, encoding="utf-8"))
        r, tm = x["marks_report"], x["tmarks"]
        chips = {c["id"] for v in tm.values() for c in v["c"]}
        n = 0
        for k, v in tm.items():
            text = x["turns"][int(k)]["text"]
            for a, b, cls, cid, how in v["u"]:
                assert 0 <= a < b <= len(text) and cls in ("wrong", "fix") and cid in chips and how in ("exact", "closest")
                n += 1
            spans = sorted(v["u"])
            assert all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)), (f, k)   # never overlapping
        assert n == r["ul_exact"] + len(r["ul_closest"]), f
        assert r["ul_exact"] + len(r["ul_closest"]) + len(r["ul_none"]) + r["ul_shared"] == r["ul_wanted"], f
