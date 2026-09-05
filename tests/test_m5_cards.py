"""M5 gate: flip / toggle / shuffle / wrong-pile replay on phone and desktop; a round of 20 with 6 misses -> replay shows exactly
those 6, second replay only the still-missed; end summary counts reconcile with stored rows; scheduler: Missed >= 3x Cold over 300
draws; ice-cold promotion (5 right on 3 days -> ice_cold, one miss -> cold); offline: 20 answers with network off then on -> 20 rows,
0 duplicates. Python buckets.py and docs/js/buckets.js agree (parity)."""
import io, json, subprocess, time
from pathlib import Path
import pytest

import buckets
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
NET = bool(E.ACCESS_TOKEN and E.SERVICE_KEY and E.ANON_KEY)
JS = ROOT / 'docs' / 'js'


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, cwd=str(JS), encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


PRELUDE = "require('./buckets.js'); require('./cards-core.js');"


def test_scheduler_missed_3x_cold_over_300_draws():
    out = node(PRELUDE + """
const C=globalThis.AneesCards; const words=[]; const stats={};
for(let i=0;i<10;i++){ words.push({key:'m'+i}); stats['m'+i]={bucket:'missed',weight:3}; words.push({key:'c'+i}); stats['c'+i]={bucket:'cold',weight:1}; }
function run(seed,n){ const rnd=C.mulberry32(seed); let m=0,c=0; for(let i=0;i<n;i++){ const w=C.drawOne(words,stats,rnd); if(w.key[0]==='m') m++; else c++; } return m/c; }
const seeds=Array.from({length:200},(_,i)=>run(i+1,300));
console.log(JSON.stringify({r300:run(20260905,300), r3000:run(7,3000), mean200:seeds.reduce((a,b)=>a+b,0)/seeds.length}));
""")
    assert out['r300'] >= 3.0, out              # the plan's check: one 300-draw simulation (seed 20260905)
    assert out['r3000'] >= 2.8, out
    assert 2.9 <= out['mean200'] <= 3.2, out     # weight is exactly 3: the long-run ratio must sit at 3


def test_round_of_20_with_6_misses_replays_exactly_those():
    out = node(PRELUDE + """
const C=globalThis.AneesCards; const words=Array.from({length:20},(_,i)=>({key:'w'+i}));
let r=C.newRound(words,{mode:'ar_first',subject:'test',id:'R'}); const missIdx=new Set([1,4,7,10,13,19]); const rows=[];
for(let i=0;i<20;i++){ rows.push(C.answer(r, missIdx.has(i)?'missed':'got', '2026-09-05T10:00:00Z', 'id'+i)); }
const s1=C.summary(r); let r2=C.replayWrong(r); const keys2=r2.cards.map(w=>w.key);
for(let i=0;i<6;i++){ rows.push(C.answer(r2, i<2?'missed':'got', '2026-09-05T10:05:00Z', 'rid'+i)); }
const s2=C.summary(r2); const r3=C.replayWrong(r2);
console.log(JSON.stringify({s1, keys2, s2, keys3:r3.cards.map(w=>w.key), rows:rows.length, got:rows.filter(x=>x.result==='got').length, attempts:[...new Set(rows.map(x=>x.attempt))]}));
""")
    assert out['s1']['n'] == 20 and out['s1']['got'] == 14 and out['s1']['missed'] == 6
    assert out['keys2'] == ['w1', 'w4', 'w7', 'w10', 'w13', 'w19']
    assert out['s2']['n'] == 6 and out['s2']['missed'] == 2 and out['keys3'] == ['w1', 'w4']
    assert out['rows'] == 26 and out['got'] == 14 + 4 and out['attempts'] == [1, 2]


CASES = {
    'ice': [{'ts': f'2026-09-0{d}T10:00:00Z', 'result': 'got', 'attempt': 1} for d in (1, 1, 2, 3, 3)],
    'ice_then_miss': [{'ts': f'2026-09-0{d}T10:00:00Z', 'result': 'got', 'attempt': 1} for d in (1, 1, 2, 3, 3)] + [{'ts': '2026-09-04T10:00:00Z', 'result': 'missed', 'attempt': 1}],
    'two_misses': [{'ts': '2026-09-01T10:00:00Z', 'result': 'missed', 'attempt': 1}, {'ts': '2026-09-01T10:01:00Z', 'result': 'missed', 'attempt': 2}],
    'second_try': [{'ts': '2026-09-01T10:00:00Z', 'result': 'missed', 'attempt': 1}, {'ts': '2026-09-01T10:01:00Z', 'result': 'got', 'attempt': 2}],
    'first_try': [{'ts': '2026-09-01T10:00:00Z', 'result': 'got', 'attempt': 1}],
    'five_same_day': [{'ts': '2026-09-01T10:0%d:00Z' % i, 'result': 'got', 'attempt': 1} for i in range(5)],
    'miss_got_miss': [{'ts': '2026-09-01T10:00:00Z', 'result': 'missed', 'attempt': 1}, {'ts': '2026-09-01T10:01:00Z', 'result': 'got', 'attempt': 1}, {'ts': '2026-09-01T10:02:00Z', 'result': 'missed', 'attempt': 1}],
}
EXPECT = {'ice': 'ice_cold', 'ice_then_miss': 'cold', 'two_misses': 'missed', 'second_try': 'shaky', 'first_try': 'cold', 'five_same_day': 'cold', 'miss_got_miss': 'missed'}


def test_ice_cold_promotion_and_demotion_python():
    for name, cards in CASES.items():
        rows = [{'word_key': name, **c} for c in cards]
        st = buckets.compute([], rows, ['2026-08-25', '2026-09-04'])
        assert st[name]['bucket'] == EXPECT[name], (name, st[name]['bucket'])
    # lesson signals
    D = ['2026-06-01', '2026-07-01', '2026-08-01', '2026-09-04']
    ev = [{'lesson_date': '2026-06-01', 'word_key': 'x', 'speaker': 'Medi', 'prompted': False, 'correction': True, 't_start': 1}]
    assert buckets.compute(ev, [], D)['x']['bucket'] == 'missed'
    ev[0]['correction'] = False; ev[0]['prompted'] = True
    assert buckets.compute(ev, [], D)['x']['bucket'] == 'shaky'
    ev[0]['prompted'] = False
    assert buckets.compute(ev, [], D)['x']['bucket'] == 'cold'
    # later cards win over an earlier lesson signal; a later lesson wins over earlier cards
    st = buckets.compute(ev, [{'word_key': 'x', 'ts': '2026-09-05T10:00:00Z', 'result': 'missed', 'attempt': 1}, {'word_key': 'x', 'ts': '2026-09-05T10:01:00Z', 'result': 'missed', 'attempt': 1}], D)
    assert st['x']['bucket'] == 'missed'
    # 'new' (Medi 2026-09-05): ONLY a word marked new (Amal/Medi rule, or Doc diff). Heard, typed or asked is never enough.
    nw = [{'lesson_date': '2026-09-04', 'word_key': 'n', 'speaker': 'Medi', 'prompted': False, 'correction': False, 'asked': True, 't_start': 1}]
    st = buckets.compute(nw, [], D, introduced={('2026-09-04', 'n')})['n']
    assert st['bucket'] == 'missed' and st['new_candidate'] is True, 'asked + typed = only a candidate for Amal, not new'
    st = buckets.compute(nw, [], D, confirmed_new={('2026-09-04', 'n')})['n']
    assert st['bucket'] == 'new' and st['lesson_signal'] == 'missed'
    assert buckets.compute(nw, [], D, doc_before={'2026-09-04': set()})['n']['bucket'] == 'new', 'heard but absent from the pre-lesson Doc = new by the Doc rule'
    assert buckets.compute(nw, [], D, doc_before={'2026-09-04': {'n'}})['n']['bucket'] == 'missed', 'in the Doc before the lesson = not new'
    C = {('2026-09-04', 'n')}
    cards = [{'word_key': 'n', 'ts': f'2026-09-0{d}T10:00:00Z', 'result': 'got', 'attempt': 1} for d in (5, 5, 6, 6, 7)]
    assert buckets.compute(nw, cards[:4], D, confirmed_new=C)['n']['bucket'] == 'new', '4 rights: still new'
    assert buckets.compute(nw, cards, D, confirmed_new=C)['n']['bucket'] != 'new', '5 first-try rights on 2 days: no longer new'
    again = nw + [{'lesson_date': '2026-09-11', 'word_key': 'n', 'speaker': 'Medi', 'prompted': False, 'correction': False, 'asked': False, 't_start': 1}]
    assert buckets.compute(again, [], D + ['2026-09-11'], confirmed_new=C)['n']['bucket'] == 'new', 'heard again but not yet practised 5x: still new'
    # chat forms map to Doc keys by exact match or consonant family (a typed conjugation counts for its lemma) -> candidates only
    W = [{'key': 'ana babse6', 'arabizi': 'Ana babse6', 'arabic': 'أنا ببسط', 'english': 'I cause happiness', 'aliases': []},
         {'key': 'na7el', 'arabizi': 'Na7el', 'arabic': 'نحل', 'english': 'Bees', 'aliases': []},
         {'key': 'kalb', 'arabizi': 'Kalb', 'arabic': 'كلب', 'english': 'Dog', 'aliases': []}]
    got = buckets.introduced_from_chat([{'lesson_date': '2026-09-04', 'text': 'Na7el'}, {'lesson_date': '2026-09-04', 'text': 'Basa6tek?'}], words=W)
    assert ('2026-09-04', 'na7el') in got and ('2026-09-04', 'ana babse6') in got and not any(k == 'kalb' for _, k in got)


def test_js_buckets_parity_with_python():
    payload = json.dumps({k: [{'word_key': k, **c} for c in v] for k, v in CASES.items()})
    out = node(PRELUDE + f"const cases={payload}; const res={{}}; for(const k in cases) res[k]=globalThis.AneesBuckets.compute([],cases[k],['2026-08-25','2026-09-04'])[k].bucket; console.log(JSON.stringify(res));")
    for k in CASES:
        assert out[k] == EXPECT[k] == buckets.compute([], [{'word_key': k, **c} for c in CASES[k]], ['2026-08-25', '2026-09-04'])[k]['bucket'], k


def test_merge_local_never_overrides_newer_server_and_weight_follows_bucket():
    out = node(PRELUDE + """
const C=globalThis.AneesCards;
const server={ a:{word_key:'a',bucket:'missed',recent:false,weight:3,last_reviewed:'2026-09-05T10:00:00Z'},
               b:{word_key:'b',bucket:'ice_cold',recent:false,weight:1,last_reviewed:'2026-09-01T10:00:00Z'},
               c:{word_key:'c',bucket:'cold',recent:false,weight:1,last_reviewed:'2026-09-01T10:00:00Z'} };
const log=[ {word_key:'a',ts:'2026-09-01T12:00:00Z',result:'got',attempt:1},          // OLD: must not override the newer server bucket
            {word_key:'b',ts:'2026-09-06T09:00:00Z',result:'missed',attempt:1},       // one miss after ice cold -> cold
            {word_key:'c',ts:'2026-09-06T09:00:00Z',result:'missed',attempt:1},{word_key:'c',ts:'2026-09-06T09:01:00Z',result:'missed',attempt:1} ];  // two misses -> missed, weight 3
const m=C.mergeLocal(server,log);
console.log(JSON.stringify({a:[m.a.bucket,m.a.weight,m.a.last_reviewed], b:[m.b.bucket,m.b.weight], c:[m.c.bucket,m.c.weight], w:C.weightOf({key:'x'},{bucket:'missed',weight:1}), w2:C.weightOf({key:'x'},{bucket:'cold',weight:3})}));
""")
    assert out['a'] == ['missed', 3, '2026-09-05T10:00:00Z'] and out['b'] == ['cold', 1] and out['c'] == ['missed', 3]
    assert out['w'] == 3 and out['w2'] == 1


def _run_round(pg, n_miss_idx):
    """Answer the current round: miss the cards at the given indexes. Returns the summary text."""
    i = 0
    while pg.locator('#got').count():
        if i == 0:
            pg.click('#card'); pg.wait_for_timeout(400)
            assert 'flip' in pg.get_attribute('#card', 'class')
        pg.click('#miss' if i in n_miss_idx else '#got')
        i += 1
        pg.wait_for_timeout(60)
    return pg.text_content('#root')


@pytest.mark.skipif(not NET, reason='needs Supabase')
@pytest.mark.parametrize('viewport', [{'width': 375, 'height': 812}, {'width': 1280, 'height': 800}])
def test_flip_toggle_shuffle_replay_end_to_end(viewport):
    import db
    from playwright.sync_api import sync_playwright
    url = (ROOT / 'docs' / 'cards.html').resolve().as_uri()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); ctx = b.new_context(viewport=viewport); pg = ctx.new_page(); pg.goto(url)
        pg.wait_for_selector('#start', timeout=20000)
        pg.click('[data-s="t:Animals"]'); pg.click('#m-en'); pg.wait_for_selector('#m-en.sel')
        pg.click('#sh'); pg.wait_for_timeout(100); sh1 = pg.text_content('#sh'); pg.click('#sh'); pg.wait_for_timeout(100); sh2 = pg.text_content('#sh')
        assert sh1 != sh2 and 'Shuffle' in sh1
        pg.click('#n20'); pg.click('#start'); pg.wait_for_selector('#card')
        assert pg.evaluate('document.documentElement.scrollWidth') <= viewport['width']
        assert pg.evaluate("document.querySelector('#got').getBoundingClientRect().height") >= 48
        rid = pg.evaluate('AneesTest.round.id')
        first_face = pg.text_content('#card .face:not(.back) .en')
        assert first_face, 'English-first mode should show English on the front'
        txt = _run_round(pg, {1, 4, 7, 10, 13, 19})
        assert 'Review the ones I got wrong (6)' in txt, txt
        assert '14' in txt and '6' in txt
        wrong1 = pg.evaluate('AneesTest.round.wrong.map(w=>w.key)')
        pg.click('#replay'); pg.wait_for_selector('#card')
        assert pg.evaluate('AneesTest.round.cards.length') == 6 and pg.evaluate('AneesTest.round.cards.map(w=>w.key)') == wrong1
        txt = _run_round(pg, {0, 2})
        assert 'Review the ones I got wrong (2)' in txt
        pg.click('#replay'); pg.wait_for_selector('#card')
        assert pg.evaluate('AneesTest.round.cards.map(w=>w.key)') == [wrong1[0], wrong1[2]]
        txt = _run_round(pg, set())
        assert 'Pile empty' in txt
        log = pg.evaluate("JSON.parse(localStorage.getItem('anees-card-log'))")
        mine = [r for r in log if r['round_id'].startswith(rid)]
        assert len(mine) == 28 and sum(1 for r in mine if r['result'] == 'missed') == 8 and sum(1 for r in mine if r['result'] == 'got') == 20
        pg.wait_for_timeout(3000)
        b.close()
    rows = db.select('card_results', {'round_id': f'like.{rid}%'})
    try:
        assert len(rows) == 28 and len({r['id'] for r in rows}) == 28
    finally:
        db.sql(f"delete from card_results where round_id like '{rid}%'"); import buckets; buckets.recompute_and_store()


@pytest.mark.skipif(not NET, reason='needs Supabase')
def test_offline_20_answers_then_sync_no_duplicates():
    import db
    from playwright.sync_api import sync_playwright
    url = (ROOT / 'docs' / 'cards.html').resolve().as_uri()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': 375, 'height': 812}); pg = ctx.new_page(); pg.goto(url)
        pg.wait_for_selector('#start', timeout=20000)
        pg.click('[data-s="t:Numbers"]'); pg.click('#n20'); pg.click('#start'); pg.wait_for_selector('#card')
        rid = pg.evaluate('AneesTest.round.id')
        ctx.set_offline(True)
        _run_round(pg, {2, 5})
        pg.wait_for_timeout(1500)
        q = pg.evaluate("JSON.parse(localStorage.getItem('anees-card-queue')).length")
        assert q == 20, q
        assert 'waiting' in pg.text_content('#sync')
        ctx.set_offline(False)
        pg.evaluate('AneesTest.sync()'); pg.wait_for_timeout(4000)
        assert pg.evaluate("JSON.parse(localStorage.getItem('anees-card-queue')).length") == 0
        # replay the same 20 ids once more: must be ignored server-side
        ids = [r['id'] for r in pg.evaluate("JSON.parse(localStorage.getItem('anees-card-log'))") if r['round_id'] == rid]
        pg.evaluate("localStorage.setItem('anees-card-queue', JSON.stringify(JSON.parse(localStorage.getItem('anees-card-log')).filter(r=>r.round_id===arguments[0])))" if False else
                    f"localStorage.setItem('anees-card-queue', JSON.stringify(JSON.parse(localStorage.getItem('anees-card-log')).filter(r=>r.round_id==='{rid}')))")
        pg.evaluate('AneesTest.sync()'); pg.wait_for_timeout(4000)
        b.close()
    rows = db.select('card_results', {'round_id': f'eq.{rid}'})
    try:
        assert len(rows) == 20 and len({r['id'] for r in rows}) == 20 and set(ids) == {r['id'] for r in rows}
    finally:
        db.sql(f"delete from card_results where round_id = '{rid}'"); import buckets; buckets.recompute_and_store()


def test_no_attribute_injection_in_cards():
    """Every page escapes quotes too (Codex M7: a Doc topic inside data-s could inject an event handler)."""
    for page in ('cards.html', 'index.html', 'amal/plan.html', 'amal/after.html'):
        src = (ROOT / 'docs' / page).read_text(encoding='utf-8')
        line = next(l for l in src.splitlines() if 'esc=s=>' in l)
        assert '&quot;' in line and '&#39;' in line, page
