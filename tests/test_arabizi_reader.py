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


def test_GR_28_repeat_of_the_line_amal_just_fixed_is_not_a_new_use():
    """GR-28, Medi 2026-10-05 (10-02 07:34 'على عشرة' -> Amal 'الـ.' -> 07:38 'على العشرة'): "this is a repeat of a mistake and
    should be marked as repeat and not counted"."""
    import detect_grammar_usage as G
    T = [{"speaker": "Medi", "start": 454.0, "text": "آآآ على عشرة."}, {"speaker": "Amal", "start": 456.0, "text": "الـ."},
         {"speaker": "Medi", "start": 457.8, "text": "على العشرة."}, {"speaker": "Medi", "start": 466.8, "text": "do you guys say lazy morning or no?"},
         {"speaker": "Medi", "start": 520.0, "text": "على العشرة بروح."}]
    assert G.repeat_of_fixed(T, 2)["start"] == 454.0          # the fixed repeat right after her prompt
    assert G.repeat_of_fixed(T, 0) is None                    # the first line is the slip itself
    assert G.repeat_of_fixed(T, 3) is None                    # English, nothing to repeat
    assert G.repeat_of_fixed(T, 4) is None                    # a new sentence a minute later is a real use
    T2 = [{"speaker": "Medi", "start": 10.0, "text": "على عشرة."}, {"speaker": "Medi", "start": 12.0, "text": "على العشرة."}]
    assert G.repeat_of_fixed(T2, 1) is None                   # his own self-fix with no Amal between is GR-22's case, not a repeat


def test_TR_26_sound_alike_cue_is_in_the_second_listen_prompt():
    """TR-26, Medi 2026-10-05: "Can we cue gemini for similar sounding words?" / "but maybe we get in front of it too"."""
    import confusables as CF, context_transcribe as CT
    c = CF.cue()
    assert "على" in c and "3ala" in c and "العشرة" in c
    assert c in CT.PROMPT and CT.PROMPT.index(c) < CT.PROMPT.index("How to use the context")
    assert CF.cue(path="C:/nowhere/none.json") == ""           # a missing list never breaks the prompt
