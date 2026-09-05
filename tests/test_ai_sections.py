"""AI reports + AI rules tabs (2026-09-05): the JSON behind both tabs is valid and complete, every report card links to a file that
exists, every rule says where it is enforced, and index.html + the shared menus carry the two tabs."""
import json, io, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'


def test_ai_rules_json_is_complete():
    j = json.load(io.open(DOCS / 'data' / 'ai_rules.json', encoding='utf-8'))
    ids = []
    for g in j['groups']:
        assert g['title'] and g['rules']
        for r in g['rules']:
            assert r['id'] and r['rule'] and r['why'] and r['where'], r
            assert r['status'] in ('enforced', 'partly', 'planned'), r
            ids.append(r['id'])
    assert len(ids) == len(set(ids)), 'rule ids must be unique'
    assert all(g.get('tab') in ('system', 'words') for g in j['groups']), 'every group is a System or a Word rule'
    assert any(r['id'] == 'N1' and 'Amal' in r['rule'] for g in j['groups'] for r in g['rules']), "the 'new' rule must name Amal as the source"


def test_ai_reports_json_and_pages():
    j = json.load(io.open(DOCS / 'data' / 'ai_reports.json', encoding='utf-8'))
    slugs = []
    for r in j['reports']:
        assert r['slug'] and r['date'] and r['author'] in ('Claude', 'Codex') and r['title'] and r['question'] and r['verdict']
        assert 1 <= len(r['numbers']) <= 4
        for b in r.get('bars', []):
            assert b['max'] > 0 and 0 <= b['value'] <= b['max'], b
        for l in r['links']:
            target = (DOCS / l['url']).resolve()
            assert target.exists(), f"dead link {l['url']} on {r['slug']}: run python scripts/build_ai_reports.py"
        slugs.append(r['slug'])
    assert len(slugs) == len(set(slugs))


def test_tabs_present_everywhere():
    idx = (DOCS / 'index.html').read_text(encoding='utf-8')
    for tab in ('ai-reports', 'sys-rules', 'word-rules'):
        assert f'data-tab="{tab}"' in idx and f'id="tab-{tab}"' in idx
    for f in (ROOT / 'scripts' / 'lesson_pipeline.py', ROOT / 'scripts' / 'build_report.py', DOCS / 'cards.html', ROOT / 'scripts' / 'build_ai_reports.py'):
        t = f.read_text(encoding='utf-8')
        assert 'index.html#ai-reports' in t and 'index.html#sys-rules' in t and 'index.html#word-rules' in t, f.name
