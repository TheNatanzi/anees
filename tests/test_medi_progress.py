"""Pure rules + cross-language parity. Never calls a provider or database."""
import json
import random
import subprocess
from pathlib import Path
import buckets

ROOT = Path(__file__).resolve().parent.parent


def event(day, speaker='Medi', **kw):
    return dict(lesson_date=f'2026-09-{day:02}', word_key='x', speaker=speaker,
                prompted=False, correction=False, asked=False, miss_kind=None, t_start=1, **kw)


def changed(day, **kw):
    e = event(day)
    e.update(kw)
    return e


def card(day, result='got', attempt=1, ident='c'):
    return dict(id=ident, word_key='x', ts=f'2026-09-{day:02}T12:00:00+00:00', result=result, attempt=attempt)


def calc(events, cards=None, marked=False):
    return buckets.compute(events, cards or [], [f'2026-09-{d:02}' for d in range(1, 11)],
                           confirmed_new={('2026-09-01', 'x')} if marked else None)['x']


def node(source):
    r = subprocess.run(['node', '-'], input=source, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_amals_counts_dates_and_mastery_are_excluded():
    s = calc([event(d, 'Amal') for d in range(1, 7)])
    assert (s['times_seen'], s['independent_uses'], s['seen_lessons']) == (0, 0, 0)
    assert s['last_reviewed'] is s['last_lesson'] is None
    assert s['bucket'] == 'never' and s['mastery_streak'] == 0 and not s['recent']
    s = calc([event(1)] + [event(d, 'Amal') for d in range(2, 7)])
    assert s['times_seen'] == s['independent_uses'] == s['seen_lessons'] == 1
    assert s['last_lesson'] == s['last_reviewed'] == '2026-09-01'


def test_independent_uses_require_explicit_no_help_no_correction():
    s = calc([event(1), changed(1, prompted=True), changed(1, correction=True),
              changed(1, asked=True), changed(1, prompted=None), changed(1, correction=None),
              changed(1, correction=True, miss_kind='gender'), changed(1, speaker='Unknown')])
    assert s['times_seen'] == 7 and s['independent_uses'] == 1
    assert s['bucket'] == 'missed' and s['mastery_streak'] == 0
    assert s['times_missed'] == 2 and s['grammar_misses'] == 1


def test_repetition_is_not_mastery_but_five_lessons_are():
    s = calc([event(1) for _ in range(10)])
    assert s['times_seen'] == s['independent_uses'] == 10
    assert s['mastery_streak'] == 1 and s['bucket'] == 'cold'
    s = calc([event(d) for d in range(1, 6)])
    assert s['bucket'] == 'ice_cold' and s['mastery_streak'] == 5
    assert s['card_right'] == s['streak'] == 0


def test_mixed_mastery_requires_three_dates_and_resets_on_help():
    s = calc([event(1), event(2), event(3)], [card(1, ident='a'), card(2, ident='b')])
    assert s['bucket'] == 'ice_cold' and s['mastery_streak'] == 5
    s = calc([event(1), event(2)], [card(1, ident='a'), card(1, ident='b'), card(2, ident='c')])
    assert s['mastery_streak'] == 5 and s['bucket'] == 'cold'
    for failure in ({'prompted': True}, {'asked': True}, {'correction': True}):
        s = calc([event(1), event(2), changed(3, **failure), event(4), event(5)])
        assert s['mastery_streak'] == 2 and s['bucket'] == 'cold'
    s = calc([event(d) for d in range(1, 6)], [card(6, 'missed')])
    assert s['bucket'] == 'cold' and s['mastery_streak'] == 0


def test_new_drill_remains_card_only_and_same_day_lesson_still_wins():
    s = calc([event(d) for d in range(1, 6)], marked=True)
    assert s['bucket'] == 'new' and s['mastery_streak'] == 5 and s['streak'] == 0
    s = calc([changed(5, asked=True)], [card(d, ident=str(i)) for i, d in enumerate([1, 1, 2, 3, 5])])
    assert s['bucket'] == 'missed' and s['mastery_streak'] == 0


def test_first_miss_after_lesson_mastery_ignores_old_card_failures():
    cards = [card(1, 'missed', ident='old1'), card(2, 'missed', ident='old2'), card(8, 'missed', ident='new')]
    s = calc([event(d) for d in range(3, 8)], cards)
    assert s['bucket'] == 'cold' and s['mastery_streak'] == 0
    s = calc([event(d) for d in range(3, 8)], cards + [card(9, 'missed', ident='new2')])
    assert s['bucket'] == 'missed'


def test_unknown_evidence_neither_promotes_nor_demotes_mastery():
    for field in ('prompted', 'correction', 'asked'):
        s = calc([event(d) for d in range(1, 6)] + [changed(6, **{field: None})])
        assert s['bucket'] == 'ice_cold' and s['mastery_streak'] == 5
        assert s['independent_uses'] == 5


def test_python_javascript_parity_for_mixed_histories():
    rnd = random.Random(17)
    cases = []
    for n in range(50):
        evs = [changed(rnd.randint(1, 8), speaker=rnd.choice(['Medi', 'Amal', 'Unknown']),
                       prompted=rnd.choice([True, False, None]), correction=rnd.choice([True, False]),
                       asked=rnd.choice([True, False]), miss_kind=rnd.choice([None, 'gender', 'choice'])) for _ in range(12)]
        cards = [card(rnd.randint(1, 9), rnd.choice(['got', 'missed']), rnd.choice([1, 1, 2]), f'{n}-{i}') for i in range(8)]
        cases.append({'evs': evs, 'cards': cards, 'marked': n % 3 == 0})
    result = node("require('./docs/js/buckets.js');const cases=" + json.dumps(cases) + ";console.log(JSON.stringify(cases.map(c=>AneesBuckets.compute(c.evs,c.cards,Array.from({length:10},(_,i)=>'2026-09-'+String(i+1).padStart(2,'0')),c.marked?new Set(['2026-09-01|x']):new Set()).x)));")
    for case, actual in zip(cases, result):
        expected = calc(case['evs'], case['cards'], case['marked'])
        for field, value in actual.items():
            assert value == expected[field], (field, value, expected[field])


def test_incremental_cards_match_full_replay_and_deduplicate_ids():
    events = [event(1), event(2), event(3)]
    initial = calc(events)
    cards = [card(4, ident='one'), card(5, ident='two')]
    source = "require('./docs/js/buckets.js');require('./docs/js/cards-core.js');const s=" + json.dumps(initial) + ", rows=" + json.dumps(cards) + ";let batch=AneesCards.mergeLocal({x:s},rows).x;let single={x:s};for(const r of rows)single=AneesCards.mergeLocal(single,[r]);const duplicate=AneesCards.mergeLocal(single,rows).x;console.log(JSON.stringify([batch,single.x,duplicate]));"
    result = node(source)
    assert result[0] == result[1] == result[2]
    expected = calc(events, cards)
    for k in ('bucket', 'mastery_streak', 'mastery_days', 'streak', 'streak_days', 'card_right', 'times_seen', 'independent_uses'):
        assert result[0][k] == expected[k]
    assert result[0]['bucket'] == 'ice_cold'


def test_local_new_streak_never_double_counts_days_or_bridges_a_miss():
    initial = calc([], [card(1, ident=str(i)) for i in range(4)], marked=True)
    for rows in ([card(1, ident='new')], [card(2, 'missed', ident='miss'), card(2, ident='new')]):
        actual = node("require('./docs/js/buckets.js');require('./docs/js/cards-core.js');console.log(JSON.stringify(AneesCards.mergeLocal({x:" + json.dumps(initial) + "}," + json.dumps(rows) + ").x));")
        assert actual['bucket'] == 'new'


def test_ui_uses_versioned_counts_and_durable_card_reads():
    for f in ('docs/index.html', 'docs/cards.html'):
        text = (ROOT / f).read_text(encoding='utf-8')
        assert "LS('anees-stats'" not in text
        assert 'window.AneesProgress.load(' in text
        assert 'word_stats?select=*&limit=5000' in text
    hub = (ROOT / 'docs/index.html').read_text(encoding='utf-8')
    assert 'You used it <span' in hub and 's.independent_uses' in hub
    assert 'Your last practice' in hub
    assert "window.AneesBuckets.mergeStats(window.AneesProgress.cached(" in hub
    cards = (ROOT / 'docs/cards.html').read_text(encoding='utf-8')
    assert 'window.AneesProgress.requireCurrent(stats)' in cards
    assert cards.index('stats=await window.AneesProgress.load(') < cards.index('LS(window.AneesProgress.CACHE_KEY,stats)')


def test_legacy_cache_rejected_and_saved_remote_cards_survive_reopen():
    initial = calc([event(1), event(2), event(3)])
    rows = [card(4, ident='remote1'), card(5, ident='remote2')]
    actual = node("require('./docs/js/buckets.js');require('./docs/js/progress.js');const stats={x:" + json.dumps(initial) + "};const rows=" + json.dumps(rows) + ";global.fetch=async()=>({ok:true,json:async()=>rows});(async()=>{const ready=await AneesProgress.load(stats,'https://example.invalid',{},rows);console.log(JSON.stringify({bucket:ready.x.bucket,count:ready.x.card_right,legacy:AneesProgress.cached({x:{times_seen:6}})}));})();")
    assert actual == {'bucket': 'ice_cold', 'count': 2, 'legacy': {}}


def test_missed_recovery_requires_two_independent_successes():
    events = [changed(1, asked=True), event(2), event(3)]
    assert [calc(events[:n])['bucket'] for n in (1, 2, 3)] == ['missed', 'shaky', 'cold']
    cards = [card(1, 'missed', ident='m1'), card(2, 'missed', ident='m2'),
             card(3, ident='r1'), card(4, ident='r2')]
    assert [calc([], cards[:n])['bucket'] for n in (2, 3, 4)] == ['missed', 'shaky', 'cold']
    mixed = calc([changed(1, correction=True), event(2)], [card(3, ident='r2')])
    assert mixed['bucket'] == 'cold' and mixed['mastery_streak'] == 2
    assert mixed['times_seen'] == 2 and mixed['independent_uses'] == mixed['times_missed'] == 1


def test_recovery_ignores_unknown_but_restarts_after_help():
    start = [changed(1, asked=True), event(2)]
    assert calc(start + [changed(3, prompted=None), event(4)])['bucket'] == 'cold'
    for failure in ({'prompted': True}, {'asked': True}, {'correction': True},
                    {'correction': True, 'miss_kind': 'gender'}):
        assert calc(start + [changed(3, **failure), event(4)])['bucket'] == 'shaky'
        assert calc(start + [changed(3, **failure), event(4), event(5)])['bucket'] == 'cold'
    assert calc(start, [card(3, attempt=2), card(4, ident='r1')])['bucket'] == 'shaky'
    # A grammar-only Good signal is not an independent success and cannot skip recovery.
    assert calc([changed(1, asked=True), changed(2, correction=True, miss_kind='gender')])['bucket'] == 'shaky'


def test_recovery_preserves_lesson_cap_new_gate_and_mastery_threshold():
    start = [changed(1, asked=True)]
    assert calc(start + [event(2) for _ in range(6)])['bucket'] == 'shaky'
    for n, expected in ((1, 'shaky'), (2, 'cold'), (4, 'cold'), (5, 'ice_cold')):
        s = calc(start + [event(d) for d in range(2, 2 + n)])
        assert s['bucket'] == expected and s['mastery_streak'] == n
    assert calc(start + [event(2), event(3)], marked=True)['bucket'] == 'new'
    assert calc([changed(1, prompted=True), event(2)])['bucket'] == 'cold'
    assert calc([event(1)])['bucket'] == 'cold'  # No invented recovery for an unassessed word.


def test_recovery_context_replay_survives_reload_and_duplicate_answers():
    initial = calc([changed(1, asked=True)])
    rows = [card(2, ident='one'), card(3, ident='two')]
    source = "require('./docs/js/buckets.js');require('./docs/js/cards-core.js');const stats={x:" + json.dumps(initial) + "}, rows=" + json.dumps(rows) + ";const one=AneesCards.mergeLocal(stats,[rows[0]]);const same=AneesCards.mergeLocal(JSON.parse(JSON.stringify(one)),[rows[0]]);const two=AneesCards.mergeLocal(same,[rows[1]]);const batch=AneesCards.mergeLocal(stats,rows);console.log(JSON.stringify({states:[one.x.bucket,same.x.bucket,two.x.bucket],parity:JSON.stringify(two)===JSON.stringify(batch),streak:two.x.mastery_streak}));"
    assert node(source) == {'states': ['shaky', 'shaky', 'cold'], 'parity': True, 'streak': 2}


def test_lesson_only_old_snapshot_is_rescored_even_with_no_new_cards():
    initial = calc([changed(1, asked=True), event(2)])
    initial['bucket'] = 'cold'  # Materialized value from the previous single-success rule.
    source = "require('./docs/js/buckets.js');require('./docs/js/progress.js');global.fetch=async()=>({ok:true,json:async()=>[]});(async()=>{const s={x:" + json.dumps(initial) + "};const loaded=await AneesProgress.load(s,'https://example.invalid',{},[]);const offline=AneesBuckets.mergeStats(AneesProgress.cached(s),[]);console.log(JSON.stringify([loaded.x.bucket,offline.x.bucket]));})();"
    assert node(source) == ['shaky', 'shaky']
