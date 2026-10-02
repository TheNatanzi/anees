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
for(let i=0;i<10;i++){ words.push({key:'m'+i}); stats['m'+i]={bucket:'cold',progress_scores:{version:1,flashcards:{bucket:'missed'}}}; words.push({key:'c'+i}); stats['c'+i]={bucket:'missed',recent:true,progress_scores:{version:1,flashcards:{bucket:'cold'}}}; }
function run(seed,n){ const rnd=C.mulberry32(seed); let m=0,c=0; for(let i=0;i<n;i++){ const w=C.drawOne(words,stats,rnd); if(w.key[0]==='m') m++; else c++; } return m/c; }
const seeds=Array.from({length:200},(_,i)=>run(i+1,300));
console.log(JSON.stringify({r300:run(20260905,300), r3000:run(7,3000), mean200:seeds.reduce((a,b)=>a+b,0)/seeds.length}));
""")
    assert out['r300'] >= 3.0, out              # the plan's check: one 300-draw simulation (seed 20260905)
    assert out['r3000'] >= 2.8, out
    assert 2.9 <= out['mean200'] <= 3.2, out     # weight is exactly 3: the long-run ratio must sit at 3


def test_round_of_20_with_6_misses_replays_exactly_those():
    """Since Medi 2026-09-30 (086d3b2) a missed card comes back REDO_GAP cards later in the same round until it is known;
    Know / Still learning count each card once (its latest answer). The wrong pile still holds every card missed once."""
    out = node(PRELUDE + """
const C=globalThis.AneesCards; const words=Array.from({length:20},(_,i)=>({key:'w'+i}));
function play(r, miss, tag){ const seen=new Set(), rows=[]; let k=0;
  while(!C.done(r)){ const w=r.cards[r.i]; const m=miss.has(w.key)&&!seen.has(w.key); if(m) seen.add(w.key); rows.push(C.answer(r, m?'missed':'got', '2026-09-05T10:00:00Z', tag+(k++))); }
  return rows; }
let r=C.newRound(words,{mode:'ar_first',subject:'test',id:'R'});
const rows=play(r, new Set(['w1','w4','w7','w10','w13','w19']), 'id');
const s1=C.summary(r); let r2=C.replayWrong(r); const keys2=r2.cards.map(w=>w.key);
rows.push(...play(r2, new Set(['w1','w4']), 'rid'));
const s2=C.summary(r2); const r3=C.replayWrong(r2);
console.log(JSON.stringify({s1, keys2, s2, keys3:r3.cards.map(w=>w.key), rows:rows.length, missed:rows.filter(x=>x.result==='missed').length, attempts:[...new Set(rows.map(x=>x.attempt))]}));
""")
    assert out['s1']['n'] == 20 and out['s1']['shown'] == 26 and out['s1']['firstTry'] == 14
    assert out['s1']['got'] == 20 and out['s1']['missed'] == 0            # every missed card was known when it came back
    assert out['keys2'] == ['w1', 'w4', 'w7', 'w10', 'w13', 'w19']
    assert out['s2']['n'] == 6 and out['s2']['shown'] == 8 and out['s2']['firstTry'] == 4 and out['keys3'] == ['w1', 'w4']
    assert out['rows'] == 34 and out['missed'] == 8 and out['attempts'] == [1, 2]


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
        assert st[name]['progress_scores']['flashcards']['bucket'] == EXPECT[name], name
        assert st[name]['bucket'] == 'never'
    # lesson signals
    D = ['2026-06-01', '2026-07-01', '2026-08-01', '2026-09-04']
    ev = [{'lesson_date': '2026-06-01', 'word_key': 'x', 'speaker': 'Medi', 'prompted': False, 'correction': True, 'asked': False, 't_start': 1}]
    assert buckets.compute(ev, [], D)['x']['bucket'] == 'missed'
    ev[0]['correction'] = False; ev[0]['prompted'] = True
    assert buckets.compute(ev, [], D)['x']['bucket'] == 'shaky'
    ev[0]['prompted'] = False
    assert buckets.compute(ev, [], D)['x']['bucket'] == 'cold'
    # Cards never override a lesson score, regardless of date.
    st = buckets.compute(ev, [{'word_key': 'x', 'ts': '2026-09-05T10:00:00Z', 'result': 'missed', 'attempt': 1}, {'word_key': 'x', 'ts': '2026-09-05T10:01:00Z', 'result': 'missed', 'attempt': 1}], D)
    assert st['x']['bucket'] == 'cold'
    assert st['x']['progress_scores']['flashcards']['bucket'] == 'missed'
    # one signal per lesson (the lAzem case): three unprompted uses + one echo after Amal in the same lesson = cold, not shaky
    lz = [{'lesson_date': '2026-08-25', 'word_key': 'lz', 'speaker': 'Medi', 'prompted': False, 'correction': False, 'asked': False, 't_start': t} for t in (302, 1235, 1385)]
    lz.append({'lesson_date': '2026-08-25', 'word_key': 'lz', 'speaker': 'Medi', 'prompted': True, 'correction': False, 'asked': False, 't_start': 2908})
    assert buckets.compute(lz, [], D)['lz']['bucket'] == 'cold'
    lz.append({'lesson_date': '2026-08-25', 'word_key': 'lz', 'speaker': 'Medi', 'prompted': False, 'correction': True, 'asked': False, 't_start': 3000})
    assert buckets.compute(lz, [], D)['lz']['bucket'] == 'missed', 'a correction in the lesson still wins'
    # weight 3 only for missed / new; being heard recently is not weakness
    assert buckets.compute(ev, [], D)['x']['weight'] == 1.0
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
    assert buckets.compute(nw, cards[:4], D, confirmed_new=C)['n']['progress_scores']['flashcards']['bucket'] == 'new', '4 rights: still new'
    assert buckets.compute(nw, cards, D, confirmed_new=C)['n']['progress_scores']['flashcards']['bucket'] != 'new', '5 first-try rights on 2 days: no longer new'
    assert buckets.compute(nw, cards, D, confirmed_new=C)['n']['bucket'] == 'new', 'cards do not finish the Speaking introduction'
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
    out = node(PRELUDE + f"const cases={payload}; const res={{}}; for(const k in cases) res[k]=globalThis.AneesBuckets.compute([],cases[k],['2026-08-25','2026-09-04'])[k].progress_scores.flashcards.bucket; console.log(JSON.stringify(res));")
    for k in CASES:
        assert out[k] == EXPECT[k] == buckets.compute([], [{'word_key': k, **c} for c in CASES[k]], ['2026-08-25', '2026-09-04'])[k]['progress_scores']['flashcards']['bucket'], k


def test_merge_local_replays_cards_separately_and_weight_follows_card_bucket():
    out = node(PRELUDE + """
const C=globalThis.AneesCards;
const server=AneesBuckets.compute(['a','b','c'].map(k=>({word_key:k,lesson_date:'2026-09-05',speaker:'Medi',t_start:1,prompted:false,correction:k==='a',asked:false})),
 [1,1,2,3,3].map((d,i)=>({id:'b'+i,word_key:'b',ts:'2026-09-0'+d+'T10:00:00Z',result:'got',attempt:1})),['2026-09-05']);
const log=[ {id:'a1',word_key:'a',ts:'2026-09-01T12:00:00Z',result:'got',attempt:1},
            {id:'bm',word_key:'b',ts:'2026-09-06T09:00:00Z',result:'missed',attempt:1},
            {id:'c1',word_key:'c',ts:'2026-09-06T09:00:00Z',result:'missed',attempt:1},{id:'c2',word_key:'c',ts:'2026-09-06T09:01:00Z',result:'missed',attempt:1} ];
const m=C.mergeLocal(server,log);
console.log(JSON.stringify({speaking:['a','b','c'].map(k=>m[k].bucket),cards:['a','b','c'].map(k=>C.cardScore(m[k]).bucket),weights:['a','b','c'].map(k=>C.weightOf({key:k},m[k])),unchanged:JSON.stringify(m.a.progress_scores.speaking)===JSON.stringify(server.a.progress_scores.speaking)}));
""")
    assert out == {'speaking': ['missed', 'cold', 'cold'], 'cards': ['cold', 'cold', 'missed'], 'weights': [1, 1, 3], 'unchanged': True}


def _run_round(pg, miss_keys):
    """Answer the current round. A card in miss_keys is missed the first time it shows; since Medi 2026-09-30 (086d3b2) a
    missed card comes back later in the same round, and is then known. Returns (swipes, summary text)."""
    i, missed = 0, set()
    while pg.locator('#got').count():
        # grading unlocks only after the card is flipped (Quizlet-style tap to flip)
        assert pg.locator('#got:disabled').count() == 1
        k = pg.evaluate('AneesTest.round.cards[AneesTest.round.i].key')
        pg.click('#card'); pg.wait_for_timeout(500 if i == 0 else 80)
        if i == 0:
            assert 'flip' in pg.get_attribute('#card', 'class')
        m = k in miss_keys and k not in missed
        if m:
            missed.add(k)
        pg.click('#miss' if m else '#got')
        i += 1
        pg.wait_for_timeout(320)   # the card flies off before the next one renders
    return i, pg.text_content('#root')


def _answers(rows):
    """One row per swipe: a singular/plural card also writes a 'form:<key>:plural' row (Medi 2026-09-30, 9f157bb)."""
    return [r for r in rows if not str(r.get('word_key', '')).startswith('form:')]


@pytest.mark.skipif(not NET, reason='needs Supabase')
@pytest.mark.parametrize('viewport', [{'width': 375, 'height': 812}, {'width': 1280, 'height': 800}])
def test_flip_toggle_shuffle_replay_end_to_end(viewport, rest_stub):
    """FC-08: the page reads Medi's live words/history (GET) but every answer it sends lands in rest_stub, never in
    his card_results (2026-09-29 runs of this test left 108 fake answers there)."""
    from playwright.sync_api import sync_playwright
    url = (ROOT / 'docs' / 'cards.html').resolve().as_uri()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); ctx = b.new_context(viewport=viewport); rest_stub.attach(ctx); pg = ctx.new_page(); pg.goto(url)
        pg.wait_for_selector('[data-t="cat:topics"]', timeout=20000)   # home is the category menu (Medi 2026-09-22); card front choice lives there too
        pg.click('#m-en'); pg.wait_for_selector('#m-en.sel'); pg.click('[data-t="cat:topics"]'); pg.click('[data-t="topic:Animals"]')
        pg.click('[data-t="all:topic:Animals"]'); pg.wait_for_selector('#start')
        pg.click('#sh'); pg.wait_for_timeout(100); sh1 = pg.text_content('#sh'); pg.click('#sh'); pg.wait_for_timeout(100); sh2 = pg.text_content('#sh')
        assert sh1 != sh2 and 'Shuffle' in sh1
        pg.click('#n20'); pg.click('#start'); pg.wait_for_selector('#card')
        assert pg.evaluate('document.documentElement.scrollWidth') <= viewport['width']
        assert pg.evaluate("document.querySelector('#got').getBoundingClientRect().height") >= 48
        rid = pg.evaluate('AneesTest.round.id')
        first_face = pg.text_content('#card .face:not(.back) .en')
        assert first_face, 'English-first mode should show English on the front'
        # The round is sized from what the page actually dealt (the daily new-card room follows Amal's curriculum).
        keys = pg.evaluate('AneesTest.round.cards.map(w=>w.key)')
        n = len(keys)
        if n < 4:
            b.close(); pytest.skip(f'only {n} Animals cards have room today; need 4')
        miss1 = {keys[j] for j in range(1, n, 3)}
        swipes1, txt = _run_round(pg, miss1)
        assert swipes1 == n + len(miss1), (swipes1, n, miss1)          # each missed card came back once in the round
        assert f'Review the ones I got wrong ({len(miss1)})' in txt, txt
        wrong1 = pg.evaluate('AneesTest.round.wrong.map(w=>w.key)')
        assert set(wrong1) == miss1
        pg.click('#replay'); pg.wait_for_selector('#card')
        assert pg.evaluate('AneesTest.round.cards.map(w=>w.key)') == wrong1
        miss2 = {wrong1[0], wrong1[2]} if len(wrong1) >= 3 else {wrong1[0]}
        swipes2, txt = _run_round(pg, miss2)
        assert swipes2 == len(wrong1) + len(miss2)
        assert f'Review the ones I got wrong ({len(miss2)})' in txt
        pg.click('#replay'); pg.wait_for_selector('#card')
        assert pg.evaluate('AneesTest.round.cards.map(w=>w.key)') == [k for k in wrong1 if k in miss2]
        swipes3, txt = _run_round(pg, set())
        assert swipes3 == len(miss2) and pg.locator('#replay').count() == 0, txt   # the wrong pile is empty
        total = swipes1 + swipes2 + swipes3
        log = pg.evaluate("JSON.parse(localStorage.getItem('anees-card-log'))")
        mine = _answers([r for r in log if r['round_id'].startswith(rid)])
        assert len(mine) == total and sum(1 for r in mine if r['result'] == 'missed') == len(miss1) + len(miss2)
        pg.wait_for_timeout(3000)
        b.close()
    sent = [r for r in rest_stub.rows('card_results') if str(r.get('round_id', '')).startswith(rid)]
    assert len(_answers(sent)) == total and len({r['id'] for r in sent}) == len(sent)
    assert {r['id'] for r in sent} == {r['id'] for r in log if r['round_id'].startswith(rid)}


@pytest.mark.skipif(not NET, reason='needs Supabase')
def test_offline_20_answers_then_sync_no_duplicates(rest_stub):
    """FC-08: answers go to rest_stub (de-duplicated by id like on_conflict=id ignore-duplicates), never to Medi's table."""
    from playwright.sync_api import sync_playwright
    url = (ROOT / 'docs' / 'cards.html').resolve().as_uri()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': 375, 'height': 812}); rest_stub.attach(ctx); pg = ctx.new_page(); pg.goto(url)
        pg.wait_for_selector('[data-t="cat:topics"]', timeout=20000); pg.click('[data-t="cat:topics"]'); pg.click('[data-t="topic:Numbers"]')   # home is the category menu
        pg.click('[data-t="all:topic:Numbers"]'); pg.wait_for_selector('#start')
        pg.click('#n20'); pg.click('#start'); pg.wait_for_function("document.querySelector('#card') || /new cards are in play/.test(document.body.innerText)")
        if not pg.locator('#card').count():
            b.close(); pytest.skip('every Numbers card would be new and today has no new-card room left')
        rid = pg.evaluate('AneesTest.round.id')
        keys = pg.evaluate('AneesTest.round.cards.map(w=>w.key)')
        n = len(keys)
        if n < 3:
            b.close(); pytest.skip(f'only {n} Numbers cards have room today')
        ctx.set_offline(True); rest_stub.offline = True
        swipes, _ = _run_round(pg, {keys[j] for j in (2, 5) if j < n})
        pg.wait_for_timeout(1500)
        log = [r for r in pg.evaluate("JSON.parse(localStorage.getItem('anees-card-log'))") if r['round_id'] == rid]
        assert len(_answers(log)) == swipes
        q = pg.evaluate("JSON.parse(localStorage.getItem('anees-card-queue')).length")
        assert q == len(log), (q, len(log))                              # nothing left the page while offline
        assert 'waiting' in pg.text_content('#sync')
        assert not rest_stub.rows('card_results')
        ctx.set_offline(False); rest_stub.offline = False
        pg.evaluate('AneesTest.sync()'); pg.wait_for_timeout(4000)
        assert pg.evaluate("JSON.parse(localStorage.getItem('anees-card-queue')).length") == 0
        # replay the same ids once more: must be ignored server-side
        ids = [r['id'] for r in log]
        pg.evaluate(f"localStorage.setItem('anees-card-queue', JSON.stringify(JSON.parse(localStorage.getItem('anees-card-log')).filter(r=>r.round_id==='{rid}')))")
        pg.evaluate('AneesTest.sync()'); pg.wait_for_timeout(4000)
        b.close()
    posts = [c for c in rest_stub.calls if c['method'] == 'POST' and '/rest/v1/card_results' in c['url']]
    assert len(posts) >= 2 and all('on_conflict=id' in c['url'] and 'ignore-duplicates' in c['prefer'] for c in posts)   # the server-side de-dup contract
    rows = [r for r in rest_stub.rows('card_results') if r.get('round_id') == rid]
    assert len(rows) == len(ids) and set(ids) == {r['id'] for r in rows}


def test_no_attribute_injection_in_cards():
    """Every page escapes quotes too (Codex M7: a Doc topic inside data-s could inject an event handler)."""
    for page in ('cards.html', 'amal/plan.html', 'amal/after.html'):
        src = (ROOT / 'docs' / page).read_text(encoding='utf-8')
        line = next(l for l in src.splitlines() if 'esc=s=>' in l)
        assert '&quot;' in line and '&#39;' in line, page
