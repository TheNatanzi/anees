# -*- coding: utf-8 -*-
"""Page health (engineering audit 2026-09-29, area 9). Offline: no network, no browser.

- js/clip-fallback.js must reach a PUBLISHED recording for every missing clip, including the two-channel lesson
  (2026-09-10 has audio/Medi.mp3 + audio/Amal.mp3 and no audio/lesson.mp3, so the old single fallback 404'd).
- scripts/check_pages.py (the publish guard's page check) passes on the repo and catches each kind of problem.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
sys.path.insert(0, str(ROOT / 'scripts'))
import check_pages as CP  # noqa: E402

NODE = next((p for p in ('C:/dev/tools/node-v24.18.0-win-x64/node.exe', shutil.which('node') or '') if p and Path(p).exists()), None)

HARNESS = r"""
const fs = require('fs');
const handlers = [];
global.window = global;
global.document = { addEventListener: (t, fn) => { if (t === 'error') handlers.push(fn); },
                    createElement: () => ({ style: {}, className: '', textContent: '', classList: { contains: () => true } }) };
eval(fs.readFileSync(process.argv[2], 'utf8'));
const pub = new Set(JSON.parse(fs.readFileSync(process.argv[3], 'utf8')));
const cases = JSON.parse(process.argv[4]);
const out = {};
for (const [src, t] of cases) {
  const a = { tagName: 'AUDIO', dataset: { t: String(t) }, attrs: { src }, currentSrc: '', next: null,
              getAttribute(k) { return this.attrs[k]; }, set src(v) { this.attrs.src = v; }, get src() { return this.attrs.src; },
              load() {}, addEventListener() {}, insertAdjacentElement(_, el) { this.next = el; },
              get nextElementSibling() { return this.next; } };
  const tried = [];
  for (let i = 0; i < 6; i++) {
    const cur = a.getAttribute('src').split('#')[0];
    if (pub.has(cur)) break;
    const before = a.getAttribute('src');
    handlers.forEach(h => h({ target: a }));
    if (a.getAttribute('src') === before) break;
    tried.push(a.getAttribute('src'));
  }
  out[src] = { final: a.getAttribute('src'), tried, note: a.next && a.next.textContent,
               chained: typeof AneesClipFallback.url === 'function' ? AneesClipFallback.url(src, t, tried[0] || null) : null };
}
console.log(JSON.stringify(out));
"""


def _fallback_run(tmp_path, cases):
    pub = sorted(CP.published_files())
    (tmp_path / 'pub.json').write_text(json.dumps(pub), encoding='utf-8')
    (tmp_path / 'h.cjs').write_text(HARNESS, encoding='utf-8')
    r = subprocess.run([NODE, str(tmp_path / 'h.cjs'), str(DOCS / 'js' / 'clip-fallback.js'), str(tmp_path / 'pub.json'), json.dumps(cases)],
                       capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(r.stdout), set(pub)


@pytest.mark.skipif(NODE is None, reason='needs node')
def test_missing_clip_on_two_channel_lesson_falls_back_to_a_published_recording(tmp_path):
    """2026-09-10 has no audio/lesson.mp3: a missing 09-10 clip must still end on a recording that ships."""
    pub = CP.published_files()
    assert 'lessons/2026-09-10/audio/lesson.mp3' not in pub and 'lessons/2026-09-10/audio/Medi.mp3' in pub
    gc = json.loads((DOCS / 'data' / 'grammar-console.json').read_text(encoding='utf-8'))
    missing = sorted({s for s in CP.iter_strings(gc) if re.search(r'2026-09-10/clips/gc-[0-9a-f]+\.mp3$', s)
                      and not any(c in pub for c in CP.clip_candidates(s))})
    assert missing, 'expected at least one unpublished 09-10 grammar clip to exercise the fallback'
    cases = [['lessons/' + missing[0], 754.2], ['lessons/2026-08-25/clips/gc-does-not-exist.mp3', 12]]
    res, pubset = _fallback_run(tmp_path, cases)
    for src, _ in cases:
        final = res[src]['final'].split('#')[0]
        assert final in pubset, (src, res[src])
        assert re.search(r'#t=\d+,\d+$', res[src]['final']), res[src]
    assert res[cases[0][0]]['final'].startswith('lessons/2026-09-10/audio/Medi.mp3#t=751,767'), res[cases[0][0]]
    assert 'channel' in (res[cases[0][0]]['note'] or ''), res[cases[0][0]]
    assert res[cases[1][0]]['final'] == 'lessons/2026-08-25/audio/lesson.mp3#t=9,24'
    # the shared-player pages (amal/review.html) ask for the NEXT recording after the one that failed
    assert res[cases[0][0]]['chained'] == 'lessons/2026-09-10/audio/Medi.mp3#t=751,767'


@pytest.mark.skipif(NODE is None, reason='needs node')
def test_fallback_gives_up_with_a_plain_note_when_nothing_is_published(tmp_path):
    res, _ = _fallback_run(tmp_path, [['lessons/1999-01-01/clips/gc-nothing.mp3', 5]])
    r = res['lessons/1999-01-01/clips/gc-nothing.mp3']
    assert r['tried'] and r['note'] == 'No recording is available for this moment.', r


def test_review_page_chains_the_fallback():
    """amal/review.html drives one shared player: on a second error it must ask for the next recording, not give up."""
    s = (DOCS / 'amal' / 'review.html').read_text(encoding='utf-8')
    assert re.search(r'AneesClipFallback\.url\(src,\s*AneesClipFallback\.secs\(b\),\s*player\.dataset\.fb', s), 'review.html does not chain'


# ---- scripts/check_pages.py: the page check the publish guard runs ----

def test_check_pages_passes_on_the_repo_and_is_fast():
    res = CP.check()
    assert res['problems'] == [], CP.one_line(res)
    assert res['pages'] >= 40 and res['secs'] < 90, res
    assert CP.main([]) == 0


def _site(tmp_path, monkeypatch, files):
    docs = tmp_path / 'docs'
    for rel, body in files.items():
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body) if isinstance(body, bytes) else p.write_text(body, encoding='utf-8')
    monkeypatch.setattr(CP, 'DOCS', docs)
    monkeypatch.setattr(CP, 'ROOT', tmp_path)
    return docs


GOOD = {
    'index.html': '<a href="tutor.html">Tutor</a><script src="js/a.js"></script><link rel="stylesheet" href="css/s.css?v=2">',
    'tutor.html': '<a href="index.html#top">Home</a><a href="https://example.com/x">out</a><a href="lessons/2026-09-01.html">L</a>',
    'lessons/2026-09-01.html': '<a href="../index.html">Home</a><script src="../js/clip-fallback.js"></script><script>fetch("../data/d.json")</script><audio></audio>',
    'lessons/2026-09-01/audio/lesson.mp3': b'ID3',
    'js/a.js': 'fetch("data/d.json"); /* example: fetch("data/not-real.json") */',
    'js/clip-fallback.js': '',
    'css/s.css': '',
    'data/d.json': '{"clip": "2026-09-01/clips/gc-0000000000000000.mp3"}',
}


def test_check_pages_clean_fake_site_passes(tmp_path, monkeypatch):
    _site(tmp_path, monkeypatch, GOOD)
    res = CP.check()
    assert res['problems'] == [], res['problems']
    assert res['missing_clips_with_fallback'] == 1


@pytest.mark.parametrize('change,kind,words', [
    ({'tutor.html': '<a href="gone.html">x</a>'}, 'links', 'gone.html'),
    ({'index.html': '<img src="assets/missing.png">'}, 'links', 'missing.png'),
    ({'js/a.js': 'fetch("data/nope.json")'}, 'data', 'data/nope.json'),
    ({'data/d.json': '{"a": '}, 'data', 'does not parse'),
    ({'data/d.json': '{"clip": "1999-01-01/clips/gc-1.mp3"}'}, 'clips', 'no full-lesson recording'),
    ({'lessons/2026-09-01.html': '<script>fetch("../data/d.json")</script><audio></audio>'}, 'clips', 'clip-fallback.js'),
    ({'tutor.html': "<button>Amal's hub</button>"}, 'hub', 'hub'),
    ({'tutor.html': '<a href="go.html?to=hub">Open</a>'}, 'hub', 'hub'),
    ({'amal/hub.html': '<p>x</p>'}, 'hub', 'hub page file'),
])
def test_check_pages_catches_each_problem_with_one_plain_line(tmp_path, monkeypatch, capsys, change, kind, words):
    _site(tmp_path, monkeypatch, {**GOOD, **change})
    res = CP.check()
    assert any(p['kind'] == kind and words in p['what'] for p in res['problems']), res['problems']
    assert CP.main([]) == 1
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1 and out[0].startswith('pages NOT OK:'), out


def test_old_reports_may_mention_the_hub_in_text_but_pages_may_not(tmp_path, monkeypatch):
    _site(tmp_path, monkeypatch, {**GOOD, 'reports/old.html': "<p>If yes: the Tutor Hub page builds from patterns.</p>"})
    assert CP.check()['problems'] == []
    _site(tmp_path, monkeypatch, {**GOOD, 'tutor.html': "<p>Open Amal's Tutor Hub</p>"})
    assert [p['kind'] for p in CP.check()['problems']] == ['hub']
