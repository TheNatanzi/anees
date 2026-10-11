"""Out-of-date banner: a page stamped with build A shows a flashing Reload bar once data/build.json says build B."""
import pytest
import io, json, os, re, threading, http.server, functools
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'


def test_every_page_carries_the_stamp_and_checker():
    for p in ['tutor.html', 'cards.html', 'amal/plan.html', 'amal/after.html', 'lessons/2026-09-04-report.html', 'lessons/2026-09-04.html']:
        s = (DOCS / p).read_text(encoding='utf-8')
        assert 'js/build.js' in s and 'js/stale.js' in s, p
    b = (DOCS / 'js' / 'build.js').read_text(encoding='utf-8')
    j = json.load(io.open(DOCS / 'data' / 'build.json', encoding='utf-8'))
    assert j['build'] in b


@pytest.mark.skipif(__import__('importlib.util').util.find_spec('playwright') is None, reason='needs the Python playwright package and a browser (pip install playwright; playwright install chromium)')
def test_banner_appears_when_build_changes(tmp_path, rest_stub):
    from playwright.sync_api import sync_playwright
    import shutil
    site = tmp_path / 'docs'
    shutil.copytree(DOCS, site, ignore=shutil.ignore_patterns('lessons', '_backups'))
    (site / 'lessons').mkdir()
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 375, 'height': 812}); rest_stub.attach(pg.context)   # FC-08
        pg.goto(f'http://127.0.0.1:{port}/cards.html'); pg.wait_for_selector('[data-t="cat:topics"]', timeout=20000)   # home is the category menu since 4facdef (2026-09-22); #start only appears inside a set
        assert pg.evaluate('AneesStale.check()') is not None and pg.locator('#stale-bar').count() == 0
        (site / 'data' / 'build.json').write_text('{"build": "20991231-000000-newer"}', encoding='utf-8')
        pg.evaluate('AneesStale.check()'); pg.wait_for_selector('#stale-bar', timeout=5000)
        txt = pg.text_content('#stale-bar')
        assert 'out of date' in txt and pg.locator('#stale-reload').count() == 1
        assert pg.evaluate("document.querySelector('#stale-reload').getBoundingClientRect().height") >= 44
        b.close()
    assert not rest_stub.calls, rest_stub.calls      # opening the Flashcards page writes nothing


def _stall_text(health, now_iso):
    """docs/js/stale.js stallText(health, now) through node (no browser needed)."""
    import os, subprocess
    node = r"C:\dev\tools\node-v24.18.0-win-x64\node.exe"
    js = ("const s = require('./docs/js/stale.js'); process.stdout.write(JSON.stringify(s.stallText(%s, new Date(%s))))"
          % (json.dumps(health), json.dumps(now_iso)))
    out = subprocess.run([node if os.path.exists(node) else 'node', '-e', js], cwd=ROOT, capture_output=True, encoding='utf-8', check=True).stdout
    return json.loads(out)


def test_stall_banner_names_the_hours_and_the_reason():
    """PR-24. Overnight brief 2026-10-10 §3 (Medi: "MAKE A SYSTEM"): while the hourly robot cannot publish, every page (PG-01,
    docs/js/stale.js) says "The hourly robot has not published for N h: <reason>", counting on in the viewer's clock."""
    h = {'last_publish_utc': '2026-10-09T18:16:25Z', 'hours_since_publish': 3.0, 'stalled': True, 'pending': ['x'],
         'first_block_reason': 'pull --rebase failed (a conflict with master; a person merges): data/budget.json'}
    assert _stall_text(h, '2026-10-11T07:16:25Z') == ('The hourly robot has not published for 37 h: pull --rebase failed '
                                                      '(a conflict with master; a person merges): data/budget.json')
    # a file published while fine (stalled false) still turns on once 2 h pass with work waiting: the robot cannot republish it
    fine = {'last_publish_utc': '2026-10-11T00:00:00Z', 'hours_since_publish': 0.1, 'stalled': False, 'pending': ['lesson day (2026-10-11)'],
            'first_block_reason': None, 'last_block_reason': None, 'open_failures': []}
    assert _stall_text(fine, '2026-10-11T01:00:00Z') is None
    assert _stall_text(fine, '2026-10-11T05:00:00Z') == 'The hourly robot has not published for 5 h: waiting: lesson day (2026-10-11)'
    assert _stall_text({**fine, 'pending': []}, '2026-10-11T05:00:00Z') is None      # nothing waits: no banner
    assert _stall_text(None, '2026-10-11T05:00:00Z') is None                         # no file: fails quiet
    src = open(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'pipeline_health.py'), encoding='utf-8').read()
    assert "of the student's corrections since the last publish" in src and "of Medi's corrections since" not in src   # PG-33 on the banner


def test_stale_js_fetches_the_pipeline_health():
    s = (DOCS / 'js' / 'stale.js').read_text(encoding='utf-8')
    assert "data/pipeline-health.json" in s and "stall-bar" in s and 'The hourly robot has not published for ' in s


def test_pr_24_the_banner_says_what_blocks_it_in_plain_words():
    """PR-24. Medi 2026-10-11: "what is this The hourly robot has not published for 38 h: step_failures:
    build_lessons_page_data exit 1: "pass": "presentation", ..." - the banner shows one plain line, never raw error text."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    import pipeline_health as P
    raw = ('step_failures: build_lessons_page_data exit 1: "pass": "presentation", "check": "audio" }, { "id": "2c82"')
    assert P.plain_reason({'first_block_reason': raw}) == 'the step "build lessons page data" failed'
    assert P.plain_reason({'first_block_reason': raw, 'last_block_reason': 'pull --rebase failed: conflict in a hand-made '
                           'file (a person merges): data/budget.json'}) == 'its money file (data/budget.json) clashed with the live copy'
    h = {'last_publish_utc': '2026-10-09T18:16:25Z', 'hours_since_publish': 38.0, 'stalled': True, 'pending': ['x'],
         'first_block_reason': raw, 'plain_reason': P.plain_reason({'first_block_reason': raw})}
    t = _stall_text(h, '2026-10-11T08:16:25Z')
    assert '"pass"' not in t and t.endswith('the step "build lessons page data" failed')


def test_pr_24_every_page_with_the_shared_menu_gets_the_stall_banner():
    """PR-24. Medi 2026-10-11 full audit: the banner showed on 6 of 14 pages. Every docs page that loads the shared menu
    (js/phone-nav.js) either loads js/stale.js itself or gets it from phone-nav.js."""
    import glob
    root = os.path.join(os.path.dirname(__file__), '..', 'docs')
    nav = open(os.path.join(root, 'js', 'phone-nav.js'), encoding='utf-8').read()
    assert "document.querySelector('script[src*=\"js/stale.js\"]')" in nav and "js/stale.js?v=fresh1" in nav
    pages = [p for p in glob.glob(os.path.join(root, '*.html')) if 'js/phone-nav.js' in open(p, encoding='utf-8').read()]
    assert len(pages) >= 10
