"""Golden tests for the verb engine: Amal's documented forms must come back
from the others (hold-one-out), and from the present "I" form alone (cold).
Floors sit just under the 2026-09-22 rates so a rule change that loses forms fails."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verb_forms as vf
import verb_forms_holdout as holdout
from arabizi import fold

FLOORS = {  # tense: (hold, cold, arabic hold, arabic cold) as % of golden forms
    'Present': (93, 93, 98, 98),
    'Past': (97, 91, 99, 95),
    'Command': (94, 84, 96, 89),
}


def test_hit_rates_hold_their_floor():
    s = holdout.summary(holdout.score(holdout.load()))
    for tense, (hold, cold, hold_ar, cold_ar) in FLOORS.items():
        x = s[tense]
        assert 100 * x['hold'] / x['forms'] >= hold, (tense, x)
        assert 100 * x['cold'] / x['forms'] >= cold, (tense, x)
        assert 100 * x['hold_ar'] / x['arabic_forms'] >= hold_ar, (tense, x)
        assert 100 * x['cold_ar'] / x['arabic_forms'] >= cold_ar, (tense, x)


def test_you_feminine_takes_i_ending():
    out = vf.conjugate({'Present': {'I': ('ba3raf', 'بعرف')}})['Present']
    assert fold(out['You (f)']['word']) == fold('bte3rafi')
    assert out['You (f)']['arabic'] == 'بتعرفي'
    assert out['They']['arabic'] == 'بيعرفوا'


def test_documented_form_is_never_replaced():
    forms = {'Present': {'I': ('ba3raf', 'بعرف')}, 'Past': {'He': ('3iref', 'عرف')}}
    out = vf.conjugate(forms)
    assert out['Past']['He'] == {'word': '3iref', 'arabic': 'عرف', 'provenance': 'document'}
    assert out['Past']['She']['provenance'] == 'inferred'


def test_no_arabic_when_amal_gave_none():
    out = vf.conjugate({'Present': {'I': ('ba3raf', '')}})
    assert all(not r['arabic'] for t in out.values() for r in t.values())


def test_every_person_filled_for_regular_verbs():
    out = vf.conjugate({'Present': {'I': ('baktub', 'بكتب')}})
    for tense, persons in vf.PERSONS_BY_TENSE.items():
        assert set(out[tense]) == set(persons), tense
    assert fold(out['Past']['She']['word']) == fold('katbat')
    assert fold(out['Command']['You (pl)']['word']) == fold('ektubu')


# Amal's verb check list 1 (pulled 2026-09-22): every guess she marked right. Fixes go here too,
# with her text; the engine must produce each one with no answers fed in.
AMAL_CHECKED = {
    'ana ba7faz:command:You (f)': ('e7fazi', 'احفظي'),
    'ana ba7faz:command:You (m)': ('e7faz', 'احفظ'),
    'ana ba7faz:command:You (pl)': ('e7fazu', 'احفظوا'),
    'ana ba7faz:past:He': ('huwwe 7efez', 'هو حفظ'),
    'ana ba7faz:past:I': ('Ana 7fezet', 'أنا حفظت'),
    'ana ba7faz:past:She': ('heyye 7efzat', 'هي حفظت'),
    'ana ba7faz:past:They': ('humme 7efzu', 'هم حفظوا'),
    'ana ba7faz:past:We': ('i7na 7fezna', 'إحنا حفظنا'),
    'ana ba7faz:past:You (f)': ('inti 7fezti', 'إنتي حفظتي'),
    'ana ba7faz:past:You (m)': ('inta 7fezet', 'إنت حفظت'),
    'ana ba7faz:past:You (pl)': ('intu 7feztu', 'إنتو حفظتو'),
    'ana ba7faz:present:He': ('huwwe bye7faz', 'هو بيحفظ'),
    'ana ba7faz:present:She': ('heyye bte7faz', 'هي بتحفظ'),
    'ana ba7faz:present:They': ('humme bye7fazu', 'هم بيحفظوا'),
    'ana ba7faz:present:We': ('i7na bne7faz', 'إحنا بنحفظ'),
    'ana ba7faz:present:You (f)': ('inti bte7fazi', 'إنتي بتحفظي'),
    'ana ba7faz:present:You (m)': ('inta bte7faz', 'إنت بتحفظ'),
    'ana ba7faz:present:You (pl)': ('intu bte7fazu', 'إنتو بتحفظوا'),
    'ana basawi:past:He': ('huwwe sawwa', 'هو سوى'),
    'ana basawi:past:I': ('Ana sawwait', 'أنا سويت'),
    'ana basawi:past:She': ('heyye sawwat', 'هي سوت'),
    'ana basawi:past:They': ('humme sawwu', 'هم سووا'),
    'ana basawi:past:We': ('i7na sawwaina', 'إحنا سوينا'),
    'ana basawi:past:You (f)': ('inti sawwaiti', 'إنتي سويتي'),
    'ana basawi:past:You (m)': ('inta sawwait', 'إنت سويت'),
    'ana basawi:past:You (pl)': ('intu sawwaitu', 'إنتو سويتو'),
    'ana basawi:present:He': ('huwwe beysawwi', 'هو بيسوي'),
    'ana basawi:present:She': ('heyye betsawwi', 'هي بتسوي'),
    'ana basawi:present:They': ('humme beysawwu', 'هم بيسووا'),
    'ana basawi:present:We': ('i7na bensawwi', 'إحنا بنسوي'),
    'ana basawi:present:You (f)': ('inti betsawwi', 'إنتي بتسوي'),
    'ana basawi:present:You (m)': ('inta betsawwi', 'إنت بتسوي'),
    'ana basawi:present:You (pl)': ('intu betsawwu', 'إنتو بتسووا'),
    'ana batbu5:past:I': ('Ana taba5et', 'أنا طبخت'),
    'ana batbu5:present:He': ('huwwe byetbu5', 'هو بيطبخ'),
    'ana batbu5:present:She': ('heyye btetbu5', 'هي بتطبخ'),
    'ana batbu5:present:They': ('humme byetbu5u', 'هم بيطبخوا'),
    'ana batbu5:present:We': ('i7na bnetbu5', 'إحنا بنطبخ'),
    'ana batbu5:present:You (f)': ('inti btetbu5i', 'إنتي بتطبخي'),
    'ana batbu5:present:You (m)': ('inta btetbu5', 'إنت بتطبخ'),
    'ana batbu5:present:You (pl)': ('intu btetbu5u', 'إنتو بتطبخوا'),
}


def test_amal_checked_forms_are_golden():
    """Engine output (no answers applied) equals Amal's checked text, word and Arabic."""
    import copy
    import build_word_bank_catalog as cat
    groups = copy.deepcopy(json.loads((ROOT / 'docs/data/word-bank-catalog.json').read_text(encoding='utf-8'))['groups'])
    cat.fill_verb_forms(groups, {})
    made = {p['id']: (p['word'], p['arabic']) for g in groups if g['type'] == 'Verb' for e in g['entries'] for p in e['persons'] if 'id' in p}
    wrong = {k: (made.get(k), v) for k, v in AMAL_CHECKED.items() if made.get(k) != v}
    assert not wrong, wrong
