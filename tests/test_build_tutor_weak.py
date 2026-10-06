# -*- coding: utf-8 -*-
"""PG-30 (Medi 2026-10-05): Amal's Tutor page has To do / Grammar / Vocab / Completed; Grammar = his 10 weakest rules, Vocab =
his 20 weakest Doc words, lowest % first, each with its numbers and last moments. Offline."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import build_tutor_weak as W


def test_PG_30_weakest_words_lowest_pct_first_with_two_uses_and_their_moments():
    words = {"maw3ed": {"arabizi": "maw3ed", "arabic": "موعد", "english": "appointment"}, "one": {"arabizi": "x"}, "good": {"arabizi": "g"}}
    L1 = {"date": "2026-10-01", "vocab_errors": [{"sheet_key": "maw3ed", "kind": "wrong", "mmss": "05:00", "said_arabizi": "maw3id", "fix": "موعد", "rating": {"status": "Wrong", "n": 2, "right": 0, "wrong": 2, "pct": 0}},
                                                 {"sheet_key": "one", "kind": "wrong", "mmss": "06:00", "rating": {"status": "Shaky", "n": 1, "right": 0, "wrong": 1, "pct": 0}}],
          "vocab_correct": [{"sheet_key": "good", "kind": "correct", "rating": {"status": "Good", "n": 4, "right": 4, "wrong": 0, "pct": 100}}]}
    L2 = {"date": "2026-10-02", "vocab_errors": [], "vocab_correct": [{"sheet_key": "maw3ed", "kind": "correct", "rating": {"status": "Shaky", "n": 3, "right": 1, "wrong": 2, "pct": 33}}]}
    out = W.weak_words([L1, L2], words, n=20)
    assert [w["key"] for w in out] == ["maw3ed", "good"]          # 'one' has a single use: not yet a weakness
    assert out[0]["pct"] == 33 and out[0]["n"] == 3 and out[0]["last_date"] == "2026-10-02"   # the latest rating wins
    assert out[0]["moments"][0]["said"] == "maw3id" and out[0]["arabic"] == "موعد"
    assert len(W.weak_words([L1, L2], words, n=1)) == 1


def test_PG_30_weakest_rules_need_three_uses_and_skip_not_taught():
    console = {"rules": [{"id": "D2", "name": "prep", "pct": 17, "uses": 53, "mistakes": 44, "events": [{"kind": "right", "date": "2026-09-05", "mmss": "43:17", "said": "x"}]},
                         {"id": "B16", "name": "b16", "pct": 20, "uses": 2, "mistakes": 1, "events": []},
                         {"id": "B14", "name": "nt", "pct": 10, "uses": 9, "mistakes": 8, "not_taught": True, "events": []},
                         {"id": "A1", "name": "el", "pct": 96, "uses": 500, "mistakes": 20, "events": []}]}
    out = W.weak_rules(console, n=10)
    assert [r["id"] for r in out] == ["D2", "A1"]
    assert out[0]["moments"][0]["mmss"] == "43:17"


def test_PG_30_tutor_page_has_todo_grammar_vocab_completed_and_no_materials_tab():
    html = open(os.path.join(REPO, "docs", "tutor.html"), encoding="utf-8").read()
    tabs = re.findall(r'class="hb-tab" role="tab" href="#(\w+)"', html)
    assert tabs == ["upload", "homework", "todo", "grammar", "vocab", "decay", "done"], tabs
    assert ">Completed <" in html and 'href="#materials"' not in html
    js = open(os.path.join(REPO, "docs", "js", "tutor.js"), encoding="utf-8").read()
    assert "data/tutor-weak.json" in js and "function vocab(id)" in js
    assert os.path.exists(os.path.join(REPO, "docs", "data", "tutor-weak.json"))


def test_PG_30_decay_is_words_not_said_for_three_weeks_longest_first_plus_never_said():
    words = {"old": {"arabizi": "old", "english": "o"}, "fresh": {"arabizi": "fresh", "english": "f"}, "never": {"arabizi": "never", "english": "n", "first_seen": "2026-09-01"}, "gone": {"arabizi": "g", "active": False}}
    L = [{"date": "2026-09-01", "vocab_correct": [{"sheet_key": "old", "kind": "correct", "rating": {"status": "Good", "n": 3, "pct": 100}}]},
         {"date": "2026-10-02", "vocab_correct": [{"sheet_key": "fresh", "kind": "correct", "rating": {"status": "Good", "n": 1, "pct": 100}}]}]
    D = W.decay(L, words)
    assert D["as_of"] == "2026-10-02" and D["days"] == 21
    assert [w["key"] for w in D["decaying"]] == ["old"] and D["decaying"][0]["days_ago"] == 31
    assert [w["key"] for w in D["untested"]] == ["never"]        # an archived Doc word is not untested


def test_PG_31_every_page_with_the_shared_menu_loads_the_phone_tab_bar():
    """PG-31 (Medi 2026-10-06 'This top bar is really bothering me' -> Option 1): bottom tabs on phones, built from the sidebar."""
    import glob
    pages = [p for p in glob.glob(os.path.join(REPO, "docs", "*.html")) if 'class="ab-nav"' in open(p, encoding="utf-8").read()]
    assert len(pages) >= 10
    for p in pages:
        assert "js/phone-nav.js" in open(p, encoding="utf-8").read(), os.path.basename(p)
    js = open(os.path.join(REPO, "docs", "js", "phone-nav.js"), encoding="utf-8").read()
    assert "max-width: 680px" in js and "'student.html', 'Student'" in js and "More" in js
