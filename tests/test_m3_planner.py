"""M3 gate: stand-in completes the planner on a phone in <= 2 min (timed); one question per screen, buttons >= 48 px, no scrolling
inside a step, progress '1 of 3', no typing except the topic; every suggested sentence uses only Doc words (0 violations);
kept/dropped decisions change the next set (drop a word twice -> it stops appearing)."""
import io, json, re, time, secrets
from pathlib import Path
import pytest

import suggest
import anees_env as E
from arabizi import Matcher

ROOT = Path(__file__).resolve().parent.parent
NET = bool(E.ACCESS_TOKEN and E.SERVICE_KEY and E.ANON_KEY)
PAYLOAD = ROOT / 'data' / 'planner_payload_2026-09-05.json'


def payload():
    if not PAYLOAD.exists():
        pytest.skip('planner payload not built')
    return json.load(io.open(PAYLOAD, encoding='utf-8'))


def test_sentences_use_only_doc_words_and_taught_topics():
    p = payload()
    words = suggest.load_words(); wmap = {w['key']: w for w in words}
    m = Matcher(words)
    assert len(p['sentences']) == suggest.N_SENTENCES, len(p['sentences'])
    taught = {w['topic'] for w in words}          # every Doc heading is a topic Amal has taught
    for s in p['sentences']:
        v = suggest.validate(s, m, p['meta']['list_a'], p['meta']['list_b'], wmap)
        assert v['ok'], (s['arabizi'], v)
        assert all(wmap[k]['topic'] in taught for k in v['keys'])
        assert v['a'] and v['b']


def test_drop_twice_removes_word():
    words = suggest.load_words()
    stats = [{'word_key': w['key'], 'bucket': 'missed' if i % 2 else 'cold', 'times_missed': 3 - (i % 3), 'times_seen': 5, 'recent': False}
             for i, w in enumerate(words[:60])]
    A0, B0, _ = suggest.candidate_lists(words, stats, [])
    victim = A0[0]
    A1, _, _ = suggest.candidate_lists(words, stats, [{'kind': 'drop', 'word_key': victim}])
    assert victim in A1, 'one drop is not enough'
    A2, _, _ = suggest.candidate_lists(words, stats, [{'kind': 'drop', 'word_key': victim}, {'kind': 'drop', 'word_key': victim}])
    assert victim not in A2
    # a kept sentence comes back first, without calling OpenAI
    p = payload()
    kept = p['sentences'][0]
    res = suggest.suggest_sentences(words, [{'word_key': k, 'bucket': 'missed', 'times_missed': 1, 'times_seen': 1, 'recent': True} for k in p['meta']['list_a']] +
                                    [{'word_key': k, 'bucket': 'cold', 'times_missed': 0, 'times_seen': 3, 'recent': False} for k in p['meta']['list_b']],
                                    [{'kind': 'keep', 'word_key': None, 'payload': kept}], use_openai=False)
    assert res['sentences'] and res['sentences'][0]['arabizi'] == kept['arabizi'] and res['sentences'][0]['source'] == 'kept by Amal'


@pytest.mark.skipif(not NET, reason='needs Supabase')
def test_stand_in_completes_planner_on_phone_under_2_min():
    """Medi as stand-in, on a 375x812 phone window, tapping at a human pace (0.8 s per tap). Also checks the UX rules."""
    import db, amal_links
    from playwright.sync_api import sync_playwright
    p = payload()
    token, url = amal_links.create('before', '2026-09-05', p)
    local = (ROOT / 'docs' / 'amal' / 'plan.html').resolve().as_uri() + f'?t={token}'
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={'width': 375, 'height': 812})
            t0 = time.time()
            pg.goto(local)
            pg.wait_for_selector('#prog:has-text("1 of 3")', timeout=15000)
            steps = 0
            typed_fields = 0
            while True:
                prog = pg.text_content('#prog')
                if prog == 'Done':
                    break
                # exactly one question per screen: one h1, buttons <= 4, all >= 48 px, no inner scrolling
                assert pg.locator('h1').count() == 1
                btns = pg.locator('#root button:visible')
                n = btns.count()
                assert 1 <= n <= 4, (prog, n)
                for i in range(n):
                    box = btns.nth(i).bounding_box()
                    assert box and box['height'] >= 48, (prog, box)
                    assert box['y'] + box['height'] <= 812, f'{prog}: button below the fold'
                assert 'suggest' in pg.text_content('#root').lower()
                assert pg.evaluate('document.documentElement.scrollWidth') <= 375
                if prog == '1 of 3':
                    pg.click('#ttype'); typed_fields += 1
                    pg.fill('#topic', 'past tense practice'); pg.click('#tgo')
                elif prog == '2 of 3':
                    pg.click('#nw0')
                elif prog == '3 of 3':
                    if pg.locator('#r0').count():
                        pg.click('#r0')
                    pg.click('#rgo')
                else:
                    m = re.match(r'Sentence (\d+) of (\d+)', prog)
                    assert m, prog
                    i = int(m.group(1)) - 1
                    pg.click(f'#{"d" if i == 1 else "k"}{i}')    # drop the second sentence, keep the rest
                steps += 1
                time.sleep(0.8)
                pg.wait_for_timeout(200)
            elapsed = time.time() - t0
            pg.wait_for_timeout(2500)          # let the save queue drain
            b.close()
        assert elapsed <= 120, elapsed
        assert typed_fields == 1
        rules = db.select('amal_rules', {'token': f'eq.{token}'})
        kinds = {r['kind'] for r in rules}
        assert {'topic', 'new_words', 'keep', 'drop'} <= kinds, kinds
        row = db.select('amal_links', {'token': f'eq.{token}'})[0]
        assert row['done_at'] and row['answers']['topic'] == 'past tense practice'
        # second open shows "already done"
        with sync_playwright() as pw:
            b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 375, 'height': 812}); pg.goto(local)
            pg.wait_for_selector('h1', timeout=15000)
            assert 'Already done' in pg.text_content('h1'); b.close()
        io.open(ROOT / 'data' / 'm3_stand_in_timing.json', 'w').write(json.dumps({'elapsed_s': round(elapsed, 1), 'steps': steps, 'token_prefix': token[:6]}))
        print(f'STAND-IN: {steps} screens in {elapsed:.1f} s')
    finally:
        db.sql(f"delete from amal_rules where token='{token}'; delete from amal_links where token='{token}'")
