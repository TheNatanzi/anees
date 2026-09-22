import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import review_new_lessons as R

ROOT = Path(__file__).resolve().parents[1]


def test_scored_mirrors_word_bank_points():
    assert R.scored({'assessment': 'helped'}) and R.scored({'vocab_points': 0})
    assert not R.scored({'assessment': 'helped', 'needs_review': True})
    assert not R.scored({'assessment': 'independent', 'scored_in_event': True})
    assert not R.scored({'assessment': 'unresolved'})
    assert not R.scored({'assessment': 'independent', 'correction': True})


def test_published_lessons_obey_rules_4_and_5():
    ev = json.loads((ROOT / 'docs/data/word-bank-evidence.json').read_text(encoding='utf-8'))['events']
    patches = json.loads((ROOT / 'docs/data/word-bank-review.json').read_text(encoding='utf-8'))['patches']
    shown = [{**e, **patches.get(e['id'], {}).get('changes', {})} for e in ev if e['speaker'] == 'Medi']
    assert not [e for e in shown if R.estimated(e) and R.scored(e)], 'an estimated-speaker event is scored'
    seen, dup = set(), 0
    for e in shown:
        if R.scored(e):
            k = (e['lesson_date'], e.get('row_id'), e.get('word_key'))
            dup += k in seen
            seen.add(k)
    assert dup == 0, f'{dup} words scored twice in one sentence'
