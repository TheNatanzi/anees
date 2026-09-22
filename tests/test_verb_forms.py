"""Golden tests for the verb engine: Amal's documented forms must come back
from the others (hold-one-out), and from the present "I" form alone (cold).
Floors sit just under the 2026-09-22 rates so a rule change that loses forms fails."""
import sys
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
