# -*- coding: utf-8 -*-
"""English and names on the tutor's page (Medi 2026-10-12, with AM-30):
(1) the student's lines on her cards written in Latin letters ('akli khatibti / il mufaddal') get English too (PG-48);
(2) no visible string of her page's data names Amal or Medi - the AI readers' explanations ("Reader AI says",
    "Listening AI says") and every builder's text are screened at build time (PG-33, scripts/screen_names.py);
(3) the English never carries the prompt's speaker label ("Tutor:", "Student:") or a "(filler)" tag (PG-40 / PG-48,
    scripts/translate_lines.py), in the caches and on the lesson pages."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "scripts"))
import screen_names as SN  # noqa: E402
import translate_lines as T  # noqa: E402


# ------------------------------------------------------------------ (1) her cards' Latin lines
def test_student_latin_lines_on_her_cards_are_collected(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "data").mkdir(parents=True)
    (repo / "docs" / "data" / "amal-x.json").write_text(json.dumps({
        "items": [{"medi_said": "akli khatibti / il mufaddal", "amal_said": "Okay, good."},
                  {"line": {"label": "The student · 01:00", "ar": "Ana hakeet ma khatibti", "az": None, "en": None}},
                  {"line": {"label": "The student · 02:00", "ar": "already has English", "az": None, "en": "Done."}},
                  {"medi_said": "Okay."}],
        "paused": {"items": [{"medi_said": "paused line here"}]}}), encoding="utf-8")
    got = {lab_txt[1]: lab_txt[0] for lab_txt in T.tutor_lines(str(repo)).values()}
    assert got == {"akli khatibti / il mufaddal": "Student", "Ana hakeet ma khatibti": "Student"}
    assert T.student_latin("akli khatibti / il mufaddal") and not T.student_latin("Okay.") and not T.student_latin("أنا شربت")


def test_the_khatibti_line_has_english_and_line_en_decorates_latin():
    M = json.loads((DOCS / "data" / "tutor-line-en.json").read_text(encoding="utf-8"))["lines"]
    assert M.get(T.tnorm("akli khatibti / il mufaddal"))
    js = (DOCS / "js" / "hub" / "line-en.js").read_text(encoding="utf-8")
    assert "if (!en || (!AR.test(t) && (k.length < 4 || !/[A-Za-z]/.test(k)))) continue;" in js
    assert "if (!t || t.length > 420 || !AR.test(t)) continue;" not in js


# ------------------------------------------------------------------ (2) no names on her page's data
def test_screen_text_names_as_pg33():
    assert SN.screen_text("He addresses Amal (f) with the masculine you-form") == "He addresses the tutor (f) with the masculine you-form"
    assert SN.screen_text("Medi appears to be building it, and Amal's 'on dinner' is a hint") == \
        "The student appears to be building it, and the tutor's 'on dinner' is a hint"
    assert SN.screen_text("Did Medi say ") == "Did the student say "
    assert SN.screen_text("Medi's microphone") == "The student's microphone"
    assert SN.screen_text("[Medi track missing] - his dual") == "[The student's track missing] - his dual"
    assert SN.screen_text("Medi 2026-10-10 marked it a mistake") == "Medi 2026-10-10 marked it a mistake"   # a dated attribution
    assert SN.screen_text("Medi") == "Medi"                                                                 # a data value
    d = SN.screen_data({"about": "Amal's list", "items": [{"who": "Medi", "readers_say": "Amal let it pass", "medi_said": "ya Amal"}]})
    assert d == {"about": "Amal's list", "items": [{"who": "Medi", "readers_say": "The tutor let it pass", "medi_said": "ya Amal"}]}


def test_no_name_in_her_page_data():
    hits = SN.data_hits()
    assert hits == [], hits[:10]
    files = [Path(p).name for p in SN.tutor_data_files()]
    assert "tutor.json" in files and "amal-verify.json" in files and "amal-trigger.json" not in files


def test_screened_at_build_time():
    btd = (ROOT / "scripts" / "build_tutor_data.py").read_text(encoding="utf-8")
    assert "screen_names.screen_tutor_files()" in btd and "screen_names.screen_data(open_, False)" in btd
    cr = (ROOT / "scripts" / "codex_rejudge.py").read_text(encoding="utf-8")
    assert '"readers_say": SN.screen_text(' in cr and '"codex_says": SN.screen_text(' in cr
    js = (DOCS / "js" / "tutor-verify.js").read_text(encoding="utf-8")
    assert "Reader AI says" in js and "esc(x.readers_say)" in js


# ------------------------------------------------------------------ (3) no speaker label or (filler) in the English
def test_clean_and_labelled():
    assert T.clean("Tutor: So neither 'tihmas' nor 'bihmis'.") == "So neither 'tihmas' nor 'bihmis'."
    assert T.clean("Student: coffee.") == "coffee."
    assert T.clean("Tutor: (filler)") == "" and T.clean("(filler)") == ""
    assert T.clean("Yes, (filler) good.") == "Yes, good."
    assert T.labelled("Student: and") and T.labelled("Tutor: (filler)") and not T.labelled("The student is right.")
    assert "never write that label in the English" in T.PROMPT and "(Medi)" not in T.PROMPT and "(Amal)" not in T.PROMPT


def test_no_labelled_english_in_any_cache():
    for p in sorted((ROOT / "data" / "lesson-work" / "translations").glob("*.json")):
        lines = json.loads(p.read_text(encoding="utf-8")).get("lines") or {}
        bad = [v for v in lines.values() if T.labelled(v)]
        assert not bad, (p.name, bad[:3])


def test_no_labelled_english_on_the_pages():
    for d in ("2026-10-08", "2026-10-09"):
        turns = json.loads((DOCS / "data" / "lessons" / (d + ".json")).read_text(encoding="utf-8")).get("turns") or []
        bad = [u["en"] for u in turns if u.get("en") and T.labelled(u["en"])]
        assert not bad, (d, bad[:3])
    M = json.loads((DOCS / "data" / "tutor-line-en.json").read_text(encoding="utf-8"))["lines"]
    assert not [v for v in M.values() if T.labelled(v)]


def test_a_cached_labelled_row_is_dropped_and_translated_again(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "OUT", str(tmp_path))
    (tmp_path / "2026-10-09.json").write_text(json.dumps({"lines": {"a": "Tutor: (filler)", "b": "Student: Very,", "c": "Fine.", "d": ""}}), encoding="utf-8")
    assert T.load("2026-10-09") == {"c": "Fine.", "d": ""}                    # "" = a filler line: no English, never asked again
