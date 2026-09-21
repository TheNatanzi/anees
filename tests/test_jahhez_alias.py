import import_vocab as iv
from speaking_evidence import StrictMatcher


def test_attached_pronoun_cannot_match_get_ready():
    forms = iv.arabizi_forms('Jahhez / jahhzi / jahhzu 7aalak/ek/kom')
    matcher = StrictMatcher([{'key': 'jahez~2', 'arabizi': forms[0], 'aliases': forms[1:]}])
    assert forms[0] == 'Jahhez'  # Preserve existing vocabulary identity.
    assert not matcher.match('kom,')
    assert not matcher.match('ek')
    assert not matcher.match('Jahhezek')
    assert matcher.match('jahhzu 7aalkom')
    assert matcher.match('Jahhez 7aalak')
    assert iv.arabizi_forms('Mu7aadase/a') == ['Mu7aadase', 'Mu7aadasa']
