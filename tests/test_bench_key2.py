# -*- coding: utf-8 -*-
"""PR-18: benchmark key version 2 is key v1 + an explicit revision list (scripts/bench_key2.py). Pure: no files, no network."""
import copy, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import bench_key2 as K2  # noqa: E402
import bench_score as BS  # noqa: E402

V1 = {"date": "2026-10-02", "version": 1, "counts": {"medi_moments": 2},
      "moments": [{"id": "M041", "i": 656, "t": 2385.63, "want": ["غير أكل"], "gone": ["tayir aklin"], "class": "latin-arabic"},
                  {"id": "M059", "i": 831, "t": 2984.21, "want": ["غير"], "gone": ["他 人"], "class": "foreign-script"}],
      "slips": [], "amal_all": [],
      "lines": [{"i": 656, "who": "Medi", "t": 2385.63, "engine": "tayir aklin.\"", "truth": "غير أكل.\"", "should_stay": False,
                 "fixes": [{"engine_wrote": "tayir aklin", "heard": "غير أكل", "by": "medi", "rule": "TR-23"}]},
                {"i": 831, "who": "Medi", "t": 2984.21, "engine": "Does it work? 'Cause 他 人 means like other...",
                 "truth": "Does it work? 'Cause غير means like other...", "should_stay": False,
                 "fixes": [{"engine_wrote": "他 人", "heard": "غير", "by": "medi", "rule": "TR-25"}]}]}


def rev(*rows):
    return {"version": 2, "derives_from_version": 1, "on": "2026-10-04", "by": "medi", "why": "Medi re-listened", "revisions": list(rows)}


TANI = {"moment": "M059", "heard_was": "غير", "heard": "تاني", "want": ["تاني"], "by": "medi", "on": "2026-10-04", "quote": "49:44 - تاني (tani)"}
AKLEH = {"moment": "M041", "heard_was": "غير أكل", "heard": "غير أكلة", "want": ["غير أكلة"], "by": "medi", "on": "2026-10-04", "quote": "39:45 - أكلة (akleh)"}


def test_revisions_change_the_moment_its_line_and_its_fix_and_nothing_else():
    before = copy.deepcopy(V1)
    v2 = K2.apply_revisions(V1, rev(TANI, AKLEH))
    assert V1 == before                                             # key v1 is not touched
    m = {x["id"]: x for x in v2["moments"]}
    ln = {x["i"]: x for x in v2["lines"]}
    assert v2["version"] == 2 and v2["derived"]["revised_moments"] == ["M041", "M059"]
    assert m["M059"]["want"] == ["تاني"] and m["M059"]["gone"] == ["他 人"] and m["M059"]["revised"]["want_was"] == ["غير"]
    assert m["M059"]["revised"]["quote"] == "49:44 - تاني (tani)" and m["M059"]["revised"]["on"] == "2026-10-04"
    assert ln[831]["truth"] == "Does it work? 'Cause تاني means like other..." and ln[831]["fixes"][0]["heard"] == "تاني"
    assert m["M041"]["want"] == ["غير أكلة"] and ln[656]["truth"] == "غير أكلة.\"" and ln[656]["fixes"][0]["heard"] == "غير أكلة"
    assert ln[831]["engine"] == V1["lines"][1]["engine"] and v2["counts"] == V1["counts"]


def test_the_same_answer_scores_differently_under_the_two_keys():
    v2 = K2.apply_revisions(V1, rev(TANI, AKLEH))
    run = {"656": {"text": "غير أكلة"}, "831": {"text": "Does it work? 'Cause تاني means like other"}}
    conv = lambda t: t  # noqa: E731
    assert BS.score(V1, [run], conv=conv)["hit"] == 0 and BS.score(v2, [run], conv=conv)["hit"] == 2
    old = {"656": {"text": "غير أكل"}, "831": {"text": "'Cause غير means like other"}}
    assert BS.score(V1, [old], conv=conv)["hit"] == 2 and BS.score(v2, [old], conv=conv)["hit"] == 0


def refused(r, truth=V1):
    try:
        K2.apply_revisions(truth, r)
    except ValueError:
        return True
    return False


def test_an_unknown_moment_or_a_revision_that_does_not_fit_is_refused():
    assert refused(rev(dict(TANI, moment="M999")))                   # unknown moment id
    assert refused(rev(dict(TANI, heard_was="آخر")))                 # not what key v1 holds
    assert refused(rev(TANI, TANI))                                  # the same moment twice
    assert refused(rev({k: v for k, v in TANI.items() if k != "quote"}))   # no words of his
    assert refused(rev(TANI), dict(V1, version=2))                   # not derived from the version it names
