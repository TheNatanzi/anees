# -*- coding: utf-8 -*-
"""PG-33 (Medi 2026-10-07 "remove and change to tutor student?" -> "a, you can always remember that student means me and
tutor means amal right"): on screen the tutor is "Tutor" and the student is "Student". Internal names (file names, ids,
data keys, Supabase columns, comments) keep Amal / Medi. Offline."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import screen_names as S


def test_PG_33_no_page_or_script_shows_amal_or_medi_on_screen():
    hits = S.hits()
    assert not hits, "%d on-screen name(s), e.g. %s" % (len(hits), "; ".join("%s:%d %r" % (f, l, t[:80]) for f, l, t in hits[:8]))


def test_PG_33_scanner_reads_visible_text_and_skips_code():
    js = ("// Medi asked for this (a comment)\n"
          "const K = { 'Not Medi': 'not_medi' };\n"                 # an object key = a stored data label
          "if (x.speaker === 'Amal') go();\n"                        # a compared value
          "el.title = 'Ask Amal';\n"                                  # visible
          "const t = `Words ${n} Medi said`;\n")                      # visible template text
    seen = [t for _l, t in S.js_strings(js) if S.NAME.search(t) and not S._is_internal(t)]
    assert seen == ["Ask Amal", " Medi said"], seen
    assert S._is_internal("word_events?select=word_key&speaker=eq.Amal") and S._is_internal("lessons/2026-09-10/audio/Amal.mp3")
    # the allow-list keeps only what was really written: a dated attribution; a speaker label is shown as Tutor / Student
    assert not S.NAME.search(S.strip_allowed("x.html", "typed only (Medi, 2026-09-05)."))
    assert S.NAME.search(S.strip_allowed("x.html", "Medi:")) and S.NAME.search(S.strip_allowed("x.html", "Ask Amal"))
    assert not S.NAME.search(S.strip_allowed("amal/grammar-rules.html", "bait Medi")) and S.NAME.search(S.strip_allowed("cards.html", "bait Medi"))


def test_PG_33_builders_write_tutor_and_student_into_page_data():
    src = lambda p: open(os.path.join(REPO, "scripts", p), encoding="utf-8").read()
    assert '"You answer · the student sends the link"' in src("build_tutor_data.py") and "Amal answers ·" not in src("build_tutor_data.py")
    assert '"title": "Listen: what did the student say?"' in src("build_amal_checks.py")
    assert '"Asked the tutor for the word"' in src("build_lessons_page_data.py")
    import json
    tutor = json.load(open(os.path.join(REPO, "docs", "data", "tutor.json"), encoding="utf-8"))
    shown = [x.get(k) or "" for x in tutor.get("open", []) for k in ("title", "who")]
    assert not [t for t in shown if S.NAME.search(t) and "amal-check" not in t], shown


def test_PG_33_every_docs_script_still_parses():
    """The rename edits string literals only; a broken quote would blank a whole page (as lesson-overview.js was on 10-06)."""
    import glob, shutil
    node = shutil.which("node")
    if not node:
        return
    bad = []
    for p in glob.glob(os.path.join(REPO, "docs", "js", "**", "*.js"), recursive=True):
        r = subprocess.run([node, "--check", p], capture_output=True, text=True)
        if r.returncode:
            bad.append(os.path.relpath(p, REPO) + ": " + (r.stderr.strip().splitlines() or ["?"])[-1])
    assert not bad, bad
