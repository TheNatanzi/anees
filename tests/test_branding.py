import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'


def test_brand_assets_and_manifest_are_complete():
    manifest = json.loads((DOCS / 'manifest.webmanifest').read_text(encoding='utf-8'))
    assert manifest['name'].startswith('Anees')
    assert manifest['display'] == 'standalone'
    assert {icon['sizes'] for icon in manifest['icons']} == {'192x192', '512x512'}
    for relative in [
        'assets/anees-logo.png',
        'assets/favicon-32.png',
        'assets/apple-touch-icon.png',
        'assets/icon-192.png',
        'assets/icon-512.png',
    ]:
        assert (DOCS / relative).stat().st_size > 0


def test_primary_page_and_shared_loader_apply_branding():
    index = (DOCS / 'index.html').read_text(encoding='utf-8')
    stale = (DOCS / 'js' / 'stale.js').read_text(encoding='utf-8')
    brand = (DOCS / 'js' / 'brand.js').read_text(encoding='utf-8')
    assert 'manifest.webmanifest' in index
    assert 'js/brand.js' in stale
    assert 'brand-logo' in brand
    assert 'apple-touch-icon' in brand
