"""M7 gate (trimmed 2026-09-26 when the hub was retired): no dead links (crawler); JS Arabizi normalisation == Python.
Original scope: every tab reachable in <= 2 taps; dark/light; no dead links (crawler); loads with Supabase down (cached data + banner);
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

# The old hub (index.html, then notes.html) was retired 2026-09-26: its Words / Today / draft-review browser checks went with it.
# Word search now lives on word-bank.html (tests/word_bank_browser.cjs).
