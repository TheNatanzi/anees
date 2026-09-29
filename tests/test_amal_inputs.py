"""Amal's inputs reach the app (engineering audit 2026-09-29, area 8).

Offline: every verb-check answer stored in data/vocab/amal_verb_checks.json is applied in the Word Bank catalog;
the level-2 (endings / prepositions) answers survive a pull; a 'yes' is never silently dropped when the engine's
guess later changes. Online (Supabase reachable): nothing she answered is left un-pulled."""
import json, os, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verb_check_links as vcl
import build_word_bank_catalog as bwc

CHECKS = ROOT / 'data' / 'vocab' / 'amal_verb_checks.json'
CATALOG = ROOT / 'docs' / 'data' / 'word-bank-catalog.json'


def catalog_items():
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    return {p['id']: p for g in cat['groups'] for f in g['entries'] for p in f.get('persons', [])
            if p.get('provenance') == 'inferred' and 'id' in p}


def test_every_stored_verb_answer_is_shown_in_the_catalog():
    answers = json.loads(CHECKS.read_text(encoding='utf-8'))['answers']
    items = catalog_items()
    missing = [k for k in answers if k not in items]
    unchecked = [k for k in answers if k in items and items[k].get('checked') is not True]
    assert not missing and not unchecked, (len(answers), missing[:5], unchecked[:5])
    fixed = [k for k, a in answers.items() if a['choice'] == 'fix']
    wrong_word = [k for k in fixed if vcl_word(items[k]['word']) != vcl_word(answers[k]['word'])]
    assert not wrong_word, wrong_word[:5]


def vcl_word(w):
    import verb_forms as vf
    return vf.strip_pronoun(w.strip())


def test_pull_keeps_level_2_answers(tmp_path, monkeypatch):
    """verb_check_links.pull() read list 2 (endings / prepositions) but never wrote it: her answers vanished."""
    row = {'created_at': '2026-09-22T09:19:45Z',
           'payload': {'kind': 'verb-addons', 'items': {}},
           'answers': {'answers': {
               'ana ba7faz:addon:obj': {'choice': 'yes', 'word': 'ba7fazo', 'arabic': 'بحفظه', 'updated_at': '2026-09-29T00:00:00Z'},
               'ana ba7faz:addon:la': {'choice': 'fix', 'word': 'no', 'arabic': '', 'updated_at': '2026-09-29T00:00:01Z'},
               'ana ba7faz:addon:ma3': {'choice': 'fix', 'word': 'ba7faz ma3o', 'arabic': 'بحفظ معه', 'updated_at': '2026-09-29T00:00:02Z'}}}}
    monkeypatch.setattr(vcl.db, 'select', lambda *a, **k: [row])
    monkeypatch.setattr(vcl, 'CHECKS', tmp_path / 'amal_verb_checks.json')
    monkeypatch.setattr(vcl, 'ADDON_CHECKS', tmp_path / 'amal_addon_checks.json', raising=False)
    vcl.pull()
    out = tmp_path / 'amal_addon_checks.json'
    assert out.exists(), 'level-2 answers were read and thrown away'
    got = json.loads(out.read_text(encoding='utf-8'))
    assert got['ana ba7faz']['object'] is True
    assert got['ana ba7faz']['preps_off'] == ['la']
    assert got['ana ba7faz']['forms']['ma3'] == {'word': 'ba7faz ma3o', 'arabic': 'بحفظ معه'}


def test_a_yes_survives_an_engine_change(monkeypatch):
    """Her 'yes' approved one exact form. If the engine later guesses something else, her approved form must still
    show (checked); before the fix it silently fell back to an unchecked guess."""
    import verb_forms as vf
    real = vf.conjugate

    def changed(forms):
        out = real(forms)
        for tense in out.values():
            for person, g in tense.items():
                g['word'] = g['word'] + 'X'      # the engine now guesses something different
        return out
    monkeypatch.setattr(vf, 'conjugate', changed)
    group = {'type': 'Verb', 'key': 'ana ba7faz', 'entries': [
        {'id': 'ana ba7faz:present', 'label': 'Present', 'word': 'ba7faz', 'arabic': 'بحفظ',
         'persons': [{'person': 'I', 'word': 'Ana ba7faz', 'arabic': 'أنا بحفظ', 'provenance': 'document'}]}]}
    checks = {'ana ba7faz:present:He': {'choice': 'yes', 'word': 'huwwe bye7faz', 'arabic': 'هو بيحفظ', 'guess': 'huwwe bye7faz'}}
    bwc.fill_verb_forms([group], checks)
    he = next(p for p in group['entries'][0]['persons'] if p['person'] == 'He')
    assert he['checked'] is True and he['word'] == 'huwwe bye7faz', he


import anees_env as E  # noqa: E402
NET = bool(E.ACCESS_TOKEN and E.SERVICE_KEY)


@pytest.mark.skipif(not NET, reason='needs Supabase')
def test_nothing_she_answered_is_left_unpulled():
    import db
    stored = json.loads(CHECKS.read_text(encoding='utf-8'))['answers']
    given = {}
    for r in db.select('verb_check_links', {'select': 'payload,answers'}):
        if r['payload'].get('kind') == 'verb-addons':
            continue
        given.update((r['answers'] or {}).get('answers', {}))
    left = sorted(set(given) - set(stored))
    assert not left, f'{len(left)} of {len(given)} answers not pulled (e.g. {left[:3]})'
