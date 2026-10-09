# -*- coding: utf-8 -*-
"""GR-31 (Medi 2026-10-09 "remvoe the [lauging] grammar errors"): the engine's sound tags in square brackets are no words
of his and never a grammar use. 28 uses in 6 lessons had been his laughs or a noise ([ضحك] / [ضحكة] as B5 and B10,
[صوت من behind الكاميرا] as A1 and A8)."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import detect_grammar_usage as D  # noqa: E402


def test_gr_31_a_laugh_tag_is_no_grammar_use_and_the_words_around_it_still_count():
    txt, back, read_as = D.read_turn({"text": "[ضحكة]"})
    assert txt is None                                            # only a tag: nothing to read
    txt, back, read_as = D.read_turn({"text": "خلص. [ضحك] ما كان في أكل."})
    assert "ضحك" not in txt and "كان" in txt
    hits = D.detect(txt)
    assert not any("ضحك" in str(h) for h in hits)


def test_gr_31_the_published_counts_hold_no_use_built_on_a_tag():
    U = json.load(open(os.path.join(ROOT, "docs", "data", "grammar-usage.json"), encoding="utf-8"))["uses"]
    bad = [(b, x["date"], x["mmss"]) for b, lst in U.items() for x in lst
           if x.get("hit") and any(x["hit"] in t for t in re.findall(r"\[([^\]]*)\]", x.get("said") or ""))
           and x["hit"] not in re.sub(r"\[[^\]]*\]", " ", x.get("said") or "")]
    assert bad == []
