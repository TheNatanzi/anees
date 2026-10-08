# -*- coding: utf-8 -*-
"""GR-30 (2026-10-07): the Oct 2 tool words A13-A17 are scored - planted lines, no files."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import detect_grammar_usage as D  # noqa: E402


def hits(line):
    return D.detect(line, only={"A13", "A14", "A15", "A16", "A17"})


def test_GR_30_the_oct_2_tool_words_are_counted_as_uses_before_or_after_the_noun():
    """Medi 2026-10-07 'yes count them'; Amal 2026-10-06 'Yes - this is the rule as I teach it'."""
    assert "A13" in hits("هادي أول ساعة في شغلنا")            # awal + noun
    assert "A13" in hits("أول الساعة")                         # awal + el- + noun
    assert "A13" in hits("اليوم الأول")                        # after the noun
    assert "A13" in hits("الساعة الأولى")
    assert "A14" in hits("تاني يوم")                           # taani + noun
    assert "A14" in hits("يوم تاني")                           # noun + taani
    assert "A14" in hits("المرة التانية")
    assert "A15" in hits("آخر مرة")                            # aa5er + noun
    assert "A15" in hits("آخر الاجتماع")                       # the end of
    assert "A15" in hits("المرة الأخيرة") and "A15" in hits("العشر دقايق الأخيرات")
    assert "A16" in hits("بشوفك غير يوم")                      # 8eir + noun
    assert "A17" in hits("هاد نفس الإشي")                      # nafs + el- + noun
    # the wrong forms are attempts at the rule: still a use (the slip row carries the mistake)
    assert "A17" in hits("النفس الإشي") and "A16" in hits("الغير يوم") and "A14" in hits("التاني ساعة")


def test_GR_30_a_tool_word_with_no_noun_next_to_it_is_not_a_use():
    for line in ("أول، يعني", "غير هيك", "تاني", "آخر شو؟", "نفس يعني", "غير مش", "هو في البيت", "كمان مرة"):
        assert not hits(line), line


def test_GR_30_the_buckets_exist_with_their_proposals_approved():
    B = json.load(open(os.path.join(ROOT, "docs", "data", "grammar-buckets.json"), encoding="utf-8"))
    ids = {b["id"]: b for b in B["buckets"]}
    for b in ("A13", "A14", "A15", "A16", "A17"):
        assert b in ids and ids[b]["family"] == "A" and ids[b].get("taught") != "not-yet", b
    assert any("el-kull = everyone" in x for x in ids["A11"]["more"])
    P = json.load(open(os.path.join(ROOT, "data", "lesson-work", "full-audit", "proposed-buckets.json"), encoding="utf-8"))
    byid = {p["id"]: p for p in P["proposals"]}
    for pid, b in (("P-A13", "A13"), ("P-A14", "A14"), ("P-A15", "A15"), ("P-A16", "A16"), ("P-A17", "A17"), ("P-A11-add", "A11")):
        assert byid[pid]["medi"] == "yes" and byid[pid]["bucket"] == b and byid[pid]["medi_said"]["quote"].startswith("yes count them"), pid
