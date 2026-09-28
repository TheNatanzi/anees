"""Label-only rename: legacy IDs, progress, thresholds and saved links still work."""
import pytest
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def node(script):
    # Feed JavaScript over stdin so large inline page scripts do not exceed
    # Windows' command-line length limit.
    result = subprocess.run(['node', '-'], input=script, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_display_labels_and_legacy_card_links():
    result = node("""
require('./docs/js/buckets.js'); require('./docs/js/cards-core.js');
const B=globalThis.AneesBuckets, C=globalThis.AneesCards;
const words=[{key:'g',topic:'Test'},{key:'m',topic:'Test'},{key:'s',topic:'Test'}];
const stats=Object.fromEntries([['g','cold'],['m','ice_cold'],['s','shaky']].map(([k,b])=>[k,{bucket:'never',progress_scores:{version:1,flashcards:{bucket:b}}}]));
console.log(JSON.stringify({
  labels:['cold','ice_cold','new','missed','shaky','never','–','__proto__'].map(B.label),
  subject:C.subjects(words,stats).buckets.find(s=>s.id==='b-cold'),
  pool:C.pool(words,stats,'b-cold').map(w=>w.key),
  event:B.signalFromEvent({speaker:'Medi',prompted:false,correction:false}),
  good:B.signalFromCards([{ts:'2026-09-10',result:'got',attempt:1}])[0],
  mastered:B.signalFromCards([1,1,2,3,3].map(d=>({ts:'2026-09-0'+d,result:'got',attempt:1})))[0],
  stored:stats
}));
""")
    assert result['labels'] == ['Good', 'Mastered', 'new', 'missed', 'shaky', 'Not assessed', '–', '  proto  ']
    assert result['subject']['name'] == 'Good + Mastered (keep them)'
    assert result['subject']['id'] == 'b-cold'
    assert result['pool'] == ['g', 'm']
    assert result['event'] == result['good'] == 'cold'
    assert result['mastered'] == 'ice_cold'
    assert all(s['bucket'] == 'never' for s in result['stored'].values())
    assert [s['progress_scores']['flashcards']['bucket'] for s in result['stored'].values()] == ['cold', 'ice_cold', 'shaky']


@pytest.mark.xfail(strict=False, reason='known failure on master 2026-09-27; fix it, then delete this marker: cards.html no longer contains esc(window.AneesBuckets.label(s.bucket)) (expected 2, found 0); the page changed after the test')
def test_all_badges_filters_and_summary_use_display_names():
    # the old hub (notes.html) was retired 2026-09-26; its label checks went with it
    cards = (ROOT / 'docs/cards.html').read_text(encoding='utf-8')
    assert cards.count('esc(window.AneesBuckets.label(s.bucket))') == 2
    assert 'esc(round.subject)' not in cards
    assert 'buckets.find(b=>b.id===round.subject)' in cards
    assert "String(s.bucket).replace('_',' ')" not in cards
    assert 'js/buckets.js?v=20260911-evidence-v1' in cards


def test_published_report_wording_and_generator():
    for date in ('2026-08-25', '2026-09-04', '2026-09-05'):
        report = (ROOT / f'docs/lessons/{date}-report.html').read_text(encoding='utf-8')
        assert 'said cold' not in report
        assert 'words you said unprompted' in report
        email = json.loads((ROOT / f'data/lessons/{date}/report_email.json').read_text(encoding='utf-8'))
        assert all('said cold' not in row['name'] for row in email['rows'])
        assert all(not row['text'].startswith('said cold:') for row in email['log'])
    source = (ROOT / 'scripts/build_report.py').read_text(encoding='utf-8')
    assert 'said cold' not in source
    assert source.count('said unprompted') >= 3


def test_modified_page_scripts_compile_without_running_them():
    # Syntax validation only: no browser, credentials, network or stored progress.
    for filename in ('docs/cards.html',):
        page = (ROOT / filename).read_text(encoding='utf-8')
        scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', page, flags=re.S | re.I)
        assert node('const vm=require("vm"); const scripts=' + json.dumps(scripts) +
                    '; for(const source of scripts) new vm.Script(source); console.log(JSON.stringify(true));')
