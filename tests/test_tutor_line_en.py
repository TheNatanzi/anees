# -*- coding: utf-8 -*-
"""PG-48 (Medi 2026-10-10 "lets add the english translations for the transcript for Amal as well"): every transcript line
on her Tutor page shows its English (docs/js/hub/line-en.js, data docs/data/tutor-line-en.json)."""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import translate_lines as TL  # noqa: E402


def test_pg_48_tutor_card_lines_have_english():
    m = json.load(io.open(os.path.join(ROOT, "docs", "data", "tutor-line-en.json"), encoding="utf-8"))["lines"]
    lines = TL.tutor_lines(ROOT)
    assert lines and len([n for n in lines if n in m]) >= 0.95 * len(lines)
    assert all(not TL.AR.search(v) for v in m.values())          # the English holds no Arabic letter (PG-40)
    assert TL.tnorm("«بسطني»، صح؟ ok...") == "بسطني صح ok"


def test_pg_48_line_en_script_on_every_tutor_page():
    js = io.open(os.path.join(ROOT, "docs", "js", "hub", "line-en.js"), encoding="utf-8").read()
    assert "data/tutor-line-en.json" in js and "hb-line-en" in js
    pages = ["tutor.html"] + ["amal/" + f for f in ("after.html", "check.html", "listen-check.html", "review.html", "word-review.html")]
    for p in pages:
        assert "hub/line-en.js" in io.open(os.path.join(ROOT, "docs", p), encoding="utf-8").read(), p


def test_pg_49_transcript_time_has_a_play_icon():
    css = io.open(os.path.join(ROOT, "docs", "css", "lessons.css"), encoding="utf-8").read()
    """PG-49: the time that plays the lesson has a play triangle in front of it."""
    assert r'button.ls-time::before{content:"\25B6"' in css
