# -*- coding: utf-8 -*-
"""scripts/arabizi_reader.py + the automatic not-a-use rules in detect_grammar_usage.py (Medi 2026-10-01/02)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from arabizi_reader import to_arabic  # noqa: E402


def test_latin_idafa_read_as_arabic():
    assert "باب الغرفة" in to_arabic("The room's door, bab al-ghurfa.")
    assert "هدول السوت" in to_arabic("So hadol el swat,")
    assert "بنت جاري" in to_arabic("So benet jari.")


def test_article_glued_across_pause_and_cutoff_dropped():
    assert "هادي الشنتة" in to_arabic("Hadi el, uh, shanta Zahadi.")
    assert to_arabic("uh, bab al-ghurfa al-mufta-- Al-maftuh.").strip(" ,.") == "باب الغرفة المفتوح"


def test_english_look_alikes_are_breaks():
    assert to_arabic("Gosh, I hate Arabic, man.").strip(" ,.") == ""
    assert to_arabic("the verb list is based on the document").strip(" ,.") == ""
    assert to_arabic("there's no L immediately following Hadi.").strip(" ,.") == "هادي"


def test_arabic_script_untouched():
    assert to_arabic("بيت صديقة خطيبتي") == "بيت صديقة خطيبتي"


def test_question_about_rule_is_not_a_use():
    import detect_grammar_usage as D
    assert D.asks_about_rule("but when is it طاولة الكبير? Like")
    assert not D.asks_about_rule("طاولة كبيرة")


def test_kaman_marra_when_amal_repeats():
    import detect_grammar_usage as D
    T = [{"speaker": "Amal", "text": "شو بتحب تلبس لون كلسات أكتر إشي؟"}, {"speaker": "Medi", "text": "آآآ، كم مرة؟"},
         {"speaker": "Amal", "text": "شو بتحب تلبس لون كلسات أكتر إشي؟"}]
    assert D.asks_again(T, 1, "آآآ، كم مرة؟")
    T[2]["text"] = "تلات مرات"
    assert not D.asks_again(T, 1, "آآآ، كم مرة؟")
