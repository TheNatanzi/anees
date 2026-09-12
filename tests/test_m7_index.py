"""M7 gate: every tab reachable in <= 2 taps; dark/light; no dead links (crawler); loads with Supabase down (cached data + banner);
Words search: 20 queries (10 Medi misspellings, 5 English, 5 Arabic) -> top 3, each < 100 ms; every row shows a bucket and a
last-reviewed value or 'never'; JS Arabizi normalisation == Python. Lighthouse mobile >= 80 is run by scripts/lighthouse.ps1 and
pasted in the log (skipped here when the CLI is missing)."""
import io, json, re, subprocess
from pathlib import Path
import pytest

import arabizi
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
NET = bool(E.ANON_KEY)
QUERIES = [('mabsoot', 'mabsU6'), ('khalas', '5alas'), ('ba3dain', 'ba3dain'), ('kteer', 'ktIr'), ('yaani', 'ya3ni'), ('shukran', 'shukran'),
           ('ankabut', '3ankabUt'), ('sabah el kheir', 'sabah al5eir'), ('mnih', 'mnIh'), ('tariqa', 'tari2a'),
           ('happy', 'mabsU6'), ('spider', '3ankabUt'), ('thank you', 'shukran'), ('later', 'ba3dain'), ('weather', 'jaw'),
           ('مبسوط', 'mabsU6'), ('شكرا', 'shukran'), ('كتير', 'ktIr'), ('بعدين', 'ba3dain'), ('عنكبوت', '3ankabUt')]


def test_js_normalisation_matches_python():
    forms = ['Mabsoo6', "tesbah 'ala kheir", 'El-jaw', 'Ana ba5aaf', 'ghayr', 'Sabah Alkheir', 'kateer', 'Qaleel', '3ankaboot', 'Ma6aar', 'Halla', 'Kelme', 'ya3ni',
             'Btenbese6i', 'Enbasa6u', 'huwwe saa2', 'Basee6a', 'Shu8ul', 'mneeh', 'akhui']
    js = "require('./arabizi.js'); const A=globalThis.AneesArabizi; const f=%s; console.log(JSON.stringify(f.map(x=>[A.loose(x),A.fold(x),A.short(x),A.skeleton(x)])));" % json.dumps(forms)
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, cwd=str(DOCS / 'js'), encoding='utf-8')
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    for f, got in zip(forms, out):
        assert got == [arabizi.loose(f), arabizi.fold(f), arabizi.short(f), arabizi.skeleton(f)], (f, got)


def test_no_dead_links():
    import requests
    seen_http = {}
    for p in DOCS.rglob('*.html'):
        html = re.sub(r'<script.*?</script>', '', p.read_text(encoding='utf-8'), flags=re.S)     # markup only, not JS templates
        for m in re.finditer(r'(?:href|src)="([^"#][^"]*)"', html):
            u = m.group(1)
            if u.startswith('javascript:') or u.startswith('data:'):
                continue
            if u.startswith('http'):
                if 'supabase.co' in u or u in seen_http or 'reports' in p.parts:      # third-party research reports cite hundreds of outside pages: not ours to keep alive
                    continue
                try:
                    seen_http[u] = requests.head(u, timeout=15, allow_redirects=True).status_code
                except (requests.RequestException, OSError) as e:
                    pytest.skip(f'no network for external link check: {e}')
                assert seen_http[u] in (200, 301, 302), (p.name, u, seen_http[u])
            else:
                target = (p.parent / u.split('?')[0].split('#')[0]).resolve()
                assert target.exists(), (p.name, u)


def test_tabs_dark_light_and_search_speed():
    from playwright.sync_api import sync_playwright
    url = (DOCS / 'index.html').resolve().as_uri()
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--allow-file-access-from-files']); pg = b.new_page(viewport={'width': 375, 'height': 812}); pg.goto(url)
        pg.wait_for_function('AneesIndex.words.length > 2000', timeout=30000)
        for tab in ['today', 'lessons', 'words', 'cards', 'amal', 'grammar', 'ai-reports', 'sys-rules', 'word-rules', 'future']:
            pg.click(f'.tab[data-tab="{tab}"]')                       # 1 tap from anywhere
            assert pg.evaluate(f"document.getElementById('tab-{tab}').classList.contains('on')")
            assert pg.evaluate('document.documentElement.scrollWidth') <= 375
        light = pg.evaluate('getComputedStyle(document.body).backgroundColor'); pg.emulate_media(color_scheme='dark')
        assert pg.evaluate('getComputedStyle(document.body).backgroundColor') != light
        pg.click('.tab[data-tab="words"]')
        # every row shows a bucket badge and a last-reviewed value or 'never'
        pg.fill('#q', ''); pg.wait_for_timeout(200)
        rows = pg.evaluate("[...document.querySelectorAll('.wrow')].map(r=>[!!r.querySelector('.badge'), r.querySelector('.last').textContent])")
        assert rows and all(bad and (last == 'never' or re.match(r'\d{4}-\d{2}-\d{2}', last)) for bad, last in rows), rows[:5]
        # Codex M7: ranking rules — literal beats pronoun-stripped, exact Arabic with al- beats stripped, an English word beats loose Arabizi tiers
        r = pg.evaluate("[['kaan',AneesIndex.search('kaan')[0].arabizi],['paid',AneesIndex.search('paid')[0].english],['الضهر',AneesIndex.search('الضهر')[0].arabic]]")
        assert r[0][1].lower() == 'kaan' and 'paid' in r[1][1].lower() and r[2][1].startswith('الضهر'), r
        # Codex M7: no attribute injection through Doc strings
        xss = pg.evaluate("""()=>{ const w={key:'x',arabizi:'x" onmouseover="window.__xss=1',arabic:'',english:'',topic:'t" onmouseover="window.__xss=1',subtopic:''}; AneesIndex.words.push(w); return document.querySelector('#results').innerHTML.includes('onmouseover=') }""")
        assert xss is False
        # 20 queries, top 3, each under 100 ms (measured in the page)
        res = pg.evaluate("""(qs)=>qs.map(([q,k])=>{ const t=performance.now(); const r=AneesIndex.search(q).slice(0,3).map(w=>w.key); return [q,k,r,performance.now()-t]; })""", QUERIES)
        bad = [x for x in res if x[1] not in x[2] or x[3] >= 100]
        assert not bad, bad
        print('search:', [(q, round(ms, 1)) for q, k, r, ms in res])
        b.close()


def test_word_history_audio_uses_the_event_offset_and_reliable_player():
    from playwright.sync_api import sync_playwright
    url = (DOCS / 'index.html').resolve().as_uri()
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--allow-file-access-from-files'])
        pg = b.new_page()
        pg.goto(url)
        assert pg.evaluate("Math.abs(AneesIndex.clipOffset({clip:'2026-09-11_002334_002517.mp3',t_start:238.03})-4.63)<0.001")
        b.close()
    html = (DOCS / 'index.html').read_text(encoding='utf-8')
    assert 'js/transcript-player.js?v=20260912-history-audio-v1' in html
    assert 'historyPlayer.playFrom(b,Number(b.dataset.off))' in html
    assert 'class="word-history" hidden' in html
    assert "if(item.classList.contains('open'))" in html
    assert "openHistoryItem)closeHistory(openHistoryItem)" in html
    assert 'class="mute history-audio-status"' in html


def test_listening_counts_only_timed_amal_words():
    from playwright.sync_api import sync_playwright
    url = (DOCS / 'index.html').resolve().as_uri()
    events = [
        {'word_key': 'x', 'lesson_date': '2026-09-04', 't_start': 2, 'speaker': 'Amal'},
        {'word_key': 'x', 'lesson_date': '2026-09-11', 't_start': 3, 'speaker': 'Amal'},
        {'word_key': 'x', 'lesson_date': '2026-09-11', 't_start': 4, 'speaker': 'Medi'},
        {'word_key': 'x', 'lesson_date': '2026-09-11', 't_start': -1, 'speaker': 'Amal'},
    ]
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--allow-file-access-from-files'])
        pg = b.new_page()
        pg.goto(url)
        assert pg.evaluate('(events)=>AneesIndex.buildListening(events)', events) == {
            'x': {'times_heard': 2, 'lesson_count': 2, 'last_heard': '2026-09-11'}
        }
        b.close()


def test_loads_with_supabase_down():
    """Served over http like GitHub Pages (a file:// fetch of data/words.json is blocked by Chromium)."""
    import threading, http.server, functools, socket
    from playwright.sync_api import sync_playwright
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{port}/index.html'
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--allow-file-access-from-files']); ctx = b.new_context(viewport={'width': 375, 'height': 812})
        ctx.route(re.compile(r'.*supabase\.co.*'), lambda route: route.abort())
        pg = ctx.new_page(); pg.goto(url)
        pg.wait_for_function('AneesIndex.offline === true', timeout=30000)
        pg.wait_for_function("document.getElementById('banner').classList.contains('on')", timeout=30000)
        assert pg.evaluate("document.getElementById('banner').classList.contains('on')")
        assert pg.evaluate('AneesIndex.words.length') >= 2000
        pg.click('.tab[data-tab="words"]'); pg.fill('#q', 'mabsoot'); pg.wait_for_timeout(200)
        assert pg.evaluate("document.querySelectorAll('.wrow').length") >= 1
        # Codex M7: with no stats at all, rows say – (never a fabricated 0 / never)
        assert pg.evaluate("document.querySelector('.wrow .seen').textContent") == '–' and pg.evaluate("document.querySelector('.wrow .badge').textContent") == '–'
        # Word history opens beneath its own row as an accordion and toggles closed.
        pg.click('.word-item .wrow')
        assert pg.evaluate("document.querySelector('.word-item.open > .word-history').hidden === false")
        assert pg.evaluate("document.querySelector('.word-item.open .wrow').getAttribute('aria-expanded')") == 'true'
        pg.click('.word-item.open .wrow')
        assert pg.evaluate("document.querySelector('.word-item.open') === null")
        # The three source verb lists appear as one topic, narrowed by tense.
        pg.fill('#q', '')
        assert pg.locator('#f-topic option[value="__verbs__"]').count() == 1
        assert pg.locator('#f-topic option[value="__verbs__"]').text_content() == 'Verbs'
        assert pg.evaluate("[...document.querySelectorAll('#f-topic option')].every(o=>!['Verbs List','Past Tense','Command Tense'].includes(o.textContent))")
        pg.select_option('#f-topic', '__verbs__')
        assert pg.is_visible('#f-tense')
        pg.select_option('#f-tense', 'past')
        assert pg.evaluate("document.querySelectorAll('.word-item').length > 0")
        assert pg.evaluate("[...document.querySelectorAll('.word-item .en i')].every(x=>x.textContent==='Verbs · Past')")
        assert pg.evaluate("AneesIndex.verbTense({topic:'Verbs List'}) === 'present' && AneesIndex.verbTense({topic:'Past Tense'}) === 'past' && AneesIndex.verbTense({topic:'Command Tense'}) === 'command'")

        # Every playable draft match can be reviewed in place. The choice is
        # kept locally when Supabase is unavailable and will sync later.
        pg.select_option('#f-topic', '')
        pg.select_option('#f-draft', 'latest')
        draft_item = pg.locator('.word-item').filter(has=pg.locator('.draft-use')).first
        draft_item.locator('.wrow').click()
        row = draft_item.locator('.draft-review-row').filter(has=pg.locator('.draft-play')).first
        row.wait_for()
        assert row.locator('.draft-choice').count() == 3
        row.locator('[data-verdict="correct"]').click()
        assert row.locator('[data-verdict="correct"]').get_attribute('aria-pressed') == 'true'
        assert pg.evaluate("Object.values(JSON.parse(localStorage.getItem('anees-draft-reviews'))).some(r=>r.verdict==='correct')")
        row.locator('.draft-play').click()
        assert pg.evaluate("document.getElementById('player').getAttribute('src').includes('lessons/2026-09-11/clips/')")
        # Merely refocusing the browser must not rebuild the list and close
        # the accordion when no flashcard data changed.
        pg.evaluate("AneesIndex.stats.__focus_probe=AneesBuckets.emptyStats('__focus_probe')")
        pg.evaluate("window.dispatchEvent(new Event('focus'))")
        assert draft_item.locator('.word-history').is_visible()
        b.close()
