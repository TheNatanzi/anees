"""M0 gate: Doc import >= 2,100 words with all fields, 0 duplicate keys, idempotent second run, 20/20 spot check,
loose matcher >= 90% right and 0 wrong on Medi spellings, RLS token isolation."""
import io, json, random, re, secrets
from pathlib import Path
import pytest

import import_vocab as iv
from arabizi import Matcher, loose, arabic_core
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
SNAP = sorted((ROOT / 'data' / 'vocab').glob('doc_markdown_*.md'))[-1]
FIX = json.load(io.open(ROOT / 'tests' / 'fixtures' / 'medi_spellings.json', encoding='utf-8'))
NET = bool(E.ACCESS_TOKEN and E.SERVICE_KEY and E.ANON_KEY)


@pytest.fixture(scope='module')
def parsed():
    text = io.open(SNAP, encoding='utf-8').read()
    rows = iv.parse_markdown(text)
    words, merged = iv.to_words(rows)
    return text, rows, words, merged


def test_import_counts(parsed):
    text, rows, words, merged = parsed
    assert len(words) >= 2100, len(words)
    for w in words:
        for f in ('arabizi', 'arabic', 'english', 'topic', 'subtopic'):
            assert w[f], (w['key'], f)
    keys = [w['key'] for w in words]
    assert len(keys) == len(set(keys)), 'duplicate keys'
    assert len({(w['match_loose'], arabic_core(w['arabic'])) for w in words}) == len(words), 'two rows share a normalised key and the same Arabic word'


def test_spot_check_20_against_doc(parsed):
    text, rows, words, merged = parsed
    cells = set()
    for line in text.split('\n'):
        if line.startswith('|'):
            for c in line.strip().strip('|').split('|'):
                cells.add(iv.clean(c))
    rng = random.Random(20260905)
    sample = rng.sample(words, 20)
    ok = 0
    for w in sample:
        in_doc = any(w['arabizi'] == c or w['arabizi'] in c.split(' / ') for c in cells) and any(w['arabic'] == c or w['arabic'] in re.split(r'\s*/\s*', c) for c in cells)
        ok += in_doc
        assert in_doc, (w['arabizi'], w['arabic'])
    assert ok == 20


def test_loose_matcher_fixture(parsed):
    text, rows, words, merged = parsed
    m = Matcher(words)
    right = wrong = missed = 0
    report = []
    for it in FIX['items']:
        got = m.match(it['s'])
        exp = it['expect']
        exp_key = None
        if exp:
            exp_key = m.match(exp, fuzzy=False)
            assert exp_key, f'fixture expectation {exp!r} is not a Doc word'
        if got == exp_key or (got and exp_key and arabic_core(m.words[got]['arabic']) == arabic_core(m.words[exp_key]['arabic'])):
            right += 1; verdict = 'ok'      # same Arabic word (a row and its pronoun-less twin) counts as right
        elif got is None:
            missed += 1; verdict = 'MISSED'
        else:
            wrong += 1; verdict = 'WRONG'
        report.append(f"{verdict:7} {it['s']:18} -> {str(got):18} expected {str(exp_key)}")
    print('\n'.join(report))
    n = len(FIX['items'])
    print(f'right {right}/{n}  missed {missed}  wrong {wrong}')
    assert wrong == 0, [r for r in report if r.startswith('WRONG')]
    assert right >= 0.9 * n, f'{right}/{n}'


@pytest.mark.skipif(not NET, reason='needs Supabase keys')
def test_sync_is_idempotent(parsed):
    text, rows, words, merged = parsed
    first = iv.sync(words)
    second = iv.sync(words)
    assert second['inserted'] == 0 and second['updated'] == 0 and second['deactivated'] == 0, second
    import db
    n = db.sql('select count(*) as n from words where active')[0]['n']
    assert n == len(words), (n, len(words))


@pytest.mark.skipif(not NET, reason='needs Supabase keys')
def test_rls_token_isolation():
    import db
    a, b = 'test_' + secrets.token_hex(8), 'test_' + secrets.token_hex(8)
    db.upsert('amal_links', [{'token': a, 'kind': 'before', 'payload': {'who': 'A'}}, {'token': b, 'kind': 'before', 'payload': {'who': 'B'}}], on='token')
    try:
        anon = E.ANON_KEY
        seen_a = db.rest('GET', 'amal_links', params={'select': 'token'}, key=anon, token=a)
        seen_b = db.rest('GET', 'amal_links', params={'select': 'token'}, key=anon, token=b)
        seen_none = db.rest('GET', 'amal_links', params={'select': 'token'}, key=anon)
        assert [r['token'] for r in seen_a] == [a]
        assert [r['token'] for r in seen_b] == [b]
        assert seen_none == []
        # A may write its own rule, not B's
        db.rest('POST', 'amal_rules', body={'token': a, 'source': 'test', 'kind': 'keep', 'payload': {}}, key=anon, token=a, prefer='return=minimal')
        with pytest.raises(db.DbError):
            db.rest('POST', 'amal_rules', body={'token': b, 'source': 'test', 'kind': 'keep', 'payload': {}}, key=anon, token=a, prefer='return=minimal')
        rules_b = db.rest('GET', 'amal_rules', params={'select': 'token'}, key=anon, token=b)
        assert rules_b == []
        # SQL-level check (same policy, run as anon with the header GUC)
        r = db.sql(f"""set role anon; select set_config('request.headers', '{{"x-anees-token":"{a}"}}', true);
                       select count(*) as n from amal_links; reset role;""")
        assert r == [] or r[0].get('n', 1) == 1
    finally:
        db.sql(f"delete from amal_rules where token in ('{a}','{b}'); delete from amal_links where token in ('{a}','{b}')")
