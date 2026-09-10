"""Label-only rename: legacy IDs, progress, thresholds and saved links still work."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def node(script):
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_display_labels_and_legacy_card_links():
    result = node("""
require('./docs/js/buckets.js'); require('./docs/js/cards-core.js');
const B=globalThis.AneesBuckets, C=globalThis.AneesCards;
const words=[{key:'g',topic:'Test'},{key:'m',topic:'Test'},{key:'s',topic:'Test'}];
const stats={g:{bucket:'cold'},m:{bucket:'ice_cold'},s:{bucket:'shaky'}};
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
    assert result['labels'] == ['Good', 'Mastered', 'new', 'missed', 'shaky', 'never', '–', '  proto  ']
    assert result['subject']['name'] == 'Good + Mastered (keep them)'
    assert result['subject']['id'] == 'b-cold'
    assert result['pool'] == ['g', 'm']
    assert result['event'] == result['good'] == 'cold'
    assert result['mastered'] == 'ice_cold'
    assert result['stored'] == {'g': {'bucket': 'cold'}, 'm': {'bucket': 'ice_cold'}, 's': {'bucket': 'shaky'}}


def test_all_badges_filters_and_summary_use_display_names():
    hub = (ROOT / 'docs/index.html').read_text(encoding='utf-8')
    cards = (ROOT / 'docs/cards.html').read_text(encoding='utf-8')
    assert 'value="cold">Good</option>' in hub
    assert 'value="ice_cold">Mastered</option>' in hub
    assert 'esc(window.AneesBuckets.label(b))' in hub
    assert 'class="badge b-cold">Good</span>' in hub
    assert "['Good words',n(cold)" in hub
    assert "['Mastered',n(ice)" in hub
    assert cards.count('esc(window.AneesBuckets.label(s.bucket))') == 2
    assert 'esc(round.subject)' not in cards
    assert 'buckets.find(b=>b.id===round.subject)' in cards
    assert "String(s.bucket).replace('_',' ')" not in cards
    for page in (hub, cards):
        assert 'js/buckets.js?v=20260910-medi-v2' in page


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
    for filename in ('docs/index.html', 'docs/cards.html'):
        page = (ROOT / filename).read_text(encoding='utf-8')
        scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', page, flags=re.S | re.I)
        assert node('const vm=require("vm"); const scripts=' + json.dumps(scripts) +
                    '; for(const source of scripts) new vm.Script(source); console.log(JSON.stringify(true));')
