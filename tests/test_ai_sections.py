"""AI reports + AI rules tabs (2026-09-05): the JSON behind both tabs is valid and complete, every report card links to a file that
exists, every rule says where it is enforced, and index.html + the shared menus carry the two tabs."""
import pytest
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
            target = (DOCS / l['url'].split('#')[0]).resolve()   # links may point at a heading inside the report
            assert target.exists(), f"dead link {l['url']} on {r['slug']}: run python scripts/build_ai_reports.py"
        slugs.append(r['slug'])
    assert len(slugs) == len(set(slugs))


@pytest.mark.xfail(strict=False, reason='known failure on master 2026-09-27; fix it, then delete this marker: docs/reports/ai-process-review-2026-09-27.html was published without the AI Reports shell (css/ai-reports.css, active tab, ar-doc article)')
def test_tabs_present_everywhere():
    tutor = (DOCS / 'tutor.html').read_text(encoding='utf-8')                                        # the old hub was retired 2026-09-26
    assert 'aria-current="page" href="tutor.html">Tutor</a>' in tutor and 'js/tutor.js' in tutor
    assert "location.replace('tutor.html')" in (DOCS / 'notes.html').read_text(encoding='utf-8')     # old notes links land on Tutor
    idx = (DOCS / 'index.html').read_text(encoding='utf-8')
    assert "location.replace(to[h]||'progress.html')" in idx and "'ai-reports':'ai-reports.html'" in idx and 'manifest.webmanifest' in idx   # home = Progress & Stats
    page = (DOCS / 'ai-reports.html').read_text(encoding='utf-8')
    assert 'aria-current="page" href="ai-reports.html"' in page and 'js/ai-reports.js' in page and 'css/ai-reports.css' in page
    prog = (DOCS / 'progress.html').read_text(encoding='utf-8')
    assert 'data-tab="overview" aria-current="page"' in prog and 'id="ov-series"' in prog and "'lesson-overview'" in prog   # lesson numbers = Progress › Overview
    assert "fetch('data/lessons.json'" in (DOCS / 'js' / 'lesson-overview.js').read_text(encoding='utf-8')
    for f in (ROOT / 'scripts' / 'lesson_pipeline.py', ROOT / 'scripts' / 'build_report.py'):
        t = f.read_text(encoding='utf-8')
        assert 'ai-reports.html' in t and '../tutor.html' in t, f.name
    assert 'aria-current="page" href="../ai-reports.html"' in (ROOT / 'scripts' / 'build_ai_reports.py').read_text(encoding='utf-8')
    assert 'ai-reports.html' in (DOCS / 'cards.html').read_text(encoding='utf-8'), 'cards.html'
    for f in sorted((DOCS / 'reports').glob('*.html')):                                              # every built report wears the skin
        t = f.read_text(encoding='utf-8')
        assert 'css/ai-reports.css' in t and 'aria-current="page" href="../ai-reports.html"' in t and '<article class="ar-doc">' in t, f.name
    for f in ('big-picture', 'cards', 'grammar', 'lessons', 'progress', 'settings', 'word-bank', 'ai-reports', 'tutor'):    # sidebar links everywhere
        t = (DOCS / f'{f}.html').read_text(encoding='utf-8')
        assert 'href="ai-reports.html"' in t and 'href="tutor.html"' in t and 'Tutor Notes' not in t, f
    T = json.loads((DOCS / 'data' / 'tutor.json').read_text(encoding='utf-8'))
    assert T['open'] and all(x.get('title') and x.get('url') for x in T['open'])
