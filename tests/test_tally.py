"""Slips page: the tally is verified against the transcripts, every clip exists, the nav reaches it."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_tally  # noqa: E402


def test_tally_builds_verified_and_counts_add_up():
    doc = build_tally.build(cut_clips=False)
    assert doc['problems'] == [], doc['problems']                      # every moment has its transcript line and quoted words
    t = doc['totals']
    grammar = [r for r in doc['rules'] if not r.get('candidate')]
    assert t['slips'] == sum(r['count'] for r in grammar) == sum(t['by_kind'].values()) == sum(t['per_lesson'].values())
    assert t['rules_with_slips'] == sum(1 for r in grammar if r['count'])
    assert 'preposition' in t['by_kind'], 'Medi 2026-09-05: preposition errors are their own kind'
    for r in doc['rules']:
        for m in r['slips'] + r['asks']:
            assert m['date'] in doc['lessons'] and re.fullmatch(r'\d\d:\d\d', m['mmss']), m


def test_published_tally_matches_source_and_clips_exist():
    pub = json.loads((ROOT / 'docs' / 'data' / 'tally.json').read_text(encoding='utf-8'))
    fresh = build_tally.build(cut_clips=False)
    assert pub['totals'] == fresh['totals'], 'run python scripts/build_tally.py'
    for r in pub['rules']:
        for m in r['slips'] + r['asks']:
            if m['clip']:
                assert (ROOT / 'docs' / 'lessons' / m['clip']).exists(), m['clip']
                assert 0 <= m['offset'] < 60
            else:
                assert 'no lesson audio' in m['audio'] or 'ffmpeg' in m['audio'], m   # honest reason, never a silent blank


def test_preposition_is_a_grammar_kind():
    import miss_kind
    assert 'preposition' in miss_kind.KINDS and 'preposition' in miss_kind.GRAMMAR_KINDS


def test_slips_page_reachable_from_every_menu():
    html = (ROOT / 'docs' / 'slips.html').read_text(encoding='utf-8')
    assert 'data/tally.json' in html and 'js/stale.js' in html
    for page in ('index.html', 'cards.html'):
        assert 'slips.html' in (ROOT / 'docs' / page).read_text(encoding='utf-8'), page
    rules = json.loads((ROOT / 'docs' / 'data' / 'ai_rules.json').read_text(encoding='utf-8'))
    ids = {r['id'] for g in rules['groups'] for r in g['rules']}
    assert {'M8', 'M9'} <= ids
