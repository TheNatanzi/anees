# -*- coding: utf-8 -*-
"""Offline page-health guard for the published site (docs/). Fast (< 90 s), static, no network, no browser.

    python scripts/check_pages.py            # exit 0 = healthy; exit 1 + ONE plain-words line saying what is wrong
    python scripts/check_pages.py --verbose  # also list every problem found
    python scripts/check_pages.py --json     # machine-readable result

What it checks (engineering audit 2026-09-29, area 9 "page health"):
  1. links    every local href / src in every page (docs/*.html, docs/lessons/*.html, docs/reports/*.html,
              docs/amal/*.html) points at a file that will be published.
  2. data     every data file a page or its scripts fetch ('data/....json' etc.) exists, and every JSON file
              under docs/data parses.
  3. clips    every audio clip named in docs/data is published, or has the full-lesson fallback that
              js/clip-fallback.js plays instead (lessons/<date>/audio/lesson.mp3, or Medi.mp3 / Amal.mp3 for a
              two-channel lesson), and every page that plays short clips from lessons/<date>/clips loads clip-fallback.js.
  4. hub      no page, link or button for "Amal's hub" / "Amal's Tutor Hub" (Medi removed them 2026-09-28:
              "this shouldnt exist"). Old reports may still mention it in their text; a link or button may not.
  5. arabizi  (with --arabizi) node scripts/arabizi_gaps.cjs prints 0 (RULES.md S1).

"Published" = on disk under docs/ and not git-ignored (*.mp3 is git-ignored, so a clip only ships when it was
force-added). Outside a git checkout every file on disk counts as published.
"""
import json, os, re, subprocess, sys, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
PAGE_GLOBS = ('*.html', 'lessons/*.html', 'reports/*.html', 'amal/*.html')
SKIP_SCHEMES = ('http:', 'https:', 'mailto:', 'tel:', 'javascript:', 'data:', 'blob:', '//', 'sms:', 'whatsapp:')
AUDIO = re.compile(r'\.(mp3|m4a|ogg|opus|wav|webm)$', re.I)
DATE = re.compile(r'(\d{4}-\d{2}-\d{2})')
CLIP = re.compile(r'lessons/(\d{4}-\d{2}-\d{2})/clips/[^/]+\.mp3$')
FULL_LESSON = ('lesson.mp3', 'Medi.mp3', 'Amal.mp3')      # the order js/clip-fallback.js tries
# a string literal in a script that names a site file: data/x.json, ../data/x.json, js/x.js, lessons/<date>/...
LITERAL = re.compile(r"""['"`]((?:\.\./|\./)*(?:data|js|css|lessons|reports|amal|assets)/[A-Za-z0-9_\-./]+\.(?:json|js|css|html|csv|txt|png|svg|jpg|webmanifest))['"`]""")
DATA_NAME = re.compile(r'([A-Za-z0-9_\-]+\.json)')


def strip_comments(js):
    """Drop /* */ blocks and whole-line // comments (file names quoted in comments are examples, not fetches)."""
    js = re.sub(r'/\*[\s\S]*?\*/', '', js)
    return re.sub(r'(?m)^\s*//.*$', '', js)


HUB_TEXT = re.compile(r"amal\W{0,2}s\s+(tutor\s+)?hub|tutor\s+hub", re.I)


def published_files():
    """Set of docs-relative posix paths that ship with the site."""
    on_disk = set()
    for dp, dns, fns in os.walk(DOCS):
        dns[:] = [d for d in dns if d != '_backups' and not d.startswith('.')]
        rel = Path(dp).relative_to(DOCS).as_posix()
        for f in fns:
            on_disk.add(f if rel == '.' else f'{rel}/{f}')
    try:
        tracked = subprocess.run(['git', '-C', str(DOCS), 'ls-files', '-z', '.'], capture_output=True, check=True).stdout
        ignored = subprocess.run(['git', '-C', str(DOCS), 'ls-files', '-z', '-o', '-i', '--exclude-standard', '.'],
                                 capture_output=True, check=True).stdout
    except Exception:
        return on_disk
    tracked = {x for x in tracked.decode('utf-8').split('\0') if x}
    ignored = {x for x in ignored.decode('utf-8').split('\0') if x} - tracked
    return on_disk - ignored


class Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.scripts, self.inline, self.clickables, self._s, self._c = [], [], [], [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ('href', 'src', 'poster', 'data-src'):
            if a.get(k):
                self.refs.append((tag, a[k]))
        if tag == 'script':
            if a.get('src'):
                self.scripts.append(a['src'])
            else:
                self._s = []
        if tag in ('a', 'button'):
            self._c = [tag, a.get('href') or '', []]

    def handle_endtag(self, tag):
        if tag == 'script' and self._s is not None:
            self.inline.append(''.join(self._s)); self._s = None
        if tag in ('a', 'button') and self._c:
            self.clickables.append((self._c[0], self._c[1], ''.join(self._c[2]).strip())); self._c = None

    def handle_data(self, d):
        if self._s is not None:
            self._s.append(d)
        if self._c is not None:
            self._c[2].append(d)


def resolve(page_dir, ref):
    """docs-relative path a local reference points at, or None when it is not a local file reference."""
    ref = ref.strip()
    if not ref or ref.startswith('#') or ref.lower().startswith(SKIP_SCHEMES) or any(x in ref for x in ('${', '{{', "'+", '"+', '+\'', '+"')):
        return None
    ref = unquote(re.split(r'[?#]', ref)[0])
    if not ref:
        return None
    parts = [] if ref.startswith('/') else [p for p in page_dir.split('/') if p]
    for seg in ref.lstrip('/').split('/'):
        if seg in ('', '.'):
            continue
        if seg == '..':
            if not parts:
                return '../' + ref           # climbs out of docs/: always broken on the site
            parts.pop()
        else:
            parts.append(seg)
    path = '/'.join(parts)
    if ref.endswith('/') or path == '':
        path = (path + '/index.html').lstrip('/')
    return path


def iter_strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from iter_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from iter_strings(v)


def clip_candidates(s):
    """Where a clip string in the data can live (the pages prefix bare names with lessons/ or lessons/<date>/clips/)."""
    p = re.split(r'[?#]', s.strip())[0]
    while p.startswith(('../', './')):
        p = p[3:] if p.startswith('../') else p[2:]
    c = [p, 'lessons/' + p]
    m = DATE.match(os.path.basename(p))
    if m:
        c.append(f'lessons/{m.group(1)}/clips/{os.path.basename(p)}')
    return c


def check(arabizi=False):
    t0 = time.time()
    pub = published_files()
    problems = []                        # (kind, where, what)
    add = lambda k, w, x: problems.append((k, w, x))
    pages = sorted({p.relative_to(DOCS).as_posix() for g in PAGE_GLOBS for p in DOCS.glob(g)})
    js_cache, clip_pages = {}, []
    for page in pages:
        src = (DOCS / page).read_text(encoding='utf-8', errors='replace')
        t = Tags()
        try:
            t.feed(src)
        except Exception as ex:                                   # malformed markup: still report, keep going
            add('links', page, f'HTML did not parse ({ex})')
        pdir = os.path.dirname(page)
        for tag, ref in t.refs:
            path = resolve(pdir, ref)
            if path and path not in pub:
                add('links', page, f'<{tag}> points at {ref} - no such published file ({path})')
        # literals in inline scripts and in the local scripts this page loads
        bodies = [('inline', s) for s in t.inline]
        for s in t.scripts:
            jp = resolve(pdir, s)
            if jp and jp in pub and jp.endswith('.js'):
                if jp not in js_cache:
                    js_cache[jp] = (DOCS / jp).read_text(encoding='utf-8', errors='replace')
                bodies.append((jp, js_cache[jp]))
        page_reads = set()
        for where, body in bodies:
            body = strip_comments(body)
            page_reads.update(DATA_NAME.findall(body))
            for lit in LITERAL.findall(body):
                here = resolve(pdir, lit)
                root = resolve('', lit)
                if here in pub or root in pub:
                    continue
                if DATE.search(lit) or '/clips/' in lit:          # an example / per-lesson path built at run time
                    continue
                add('data', page, f'{"script " + where if where != "inline" else "inline script"} fetches {lit} - no such published file')
        plays = bool(re.search(r"<audio|new Audio\(|createElement\(.audio", src + ''.join(b for _, b in bodies)))
        clip_pages.append((page, plays, 'js/clip-fallback.js' in {resolve(pdir, s) for s in t.scripts}, page_reads))
        # hub remnant: a link or button, or any page file, for Amal's hub
        for tag, href, text in t.clickables:
            if HUB_TEXT.search(text) or re.search(r'(^|/)(amal[-_]?)?hub\.html', href, re.I) or re.search(r'[?&]to=hub\b', href):
                add('hub', page, f'<{tag}> "{text[:60]}" -> {href or "(button)"} is an Amal hub link (removed 2026-09-28)')
        if not page.startswith('reports/') and HUB_TEXT.search(re.sub(r'<script[\s\S]*?</script>|<!--[\s\S]*?-->', '', src)):
            add('hub', page, 'page text still names "Amal\'s hub" / "Tutor Hub" (removed 2026-09-28)')
    for f in pub:
        if re.search(r'(^|/)[^/]*hub[^/]*\.html$', f, re.I) and '_backups' not in f and f != 'notes.html':
            add('hub', f, 'a hub page file exists (Amal\'s hub was removed 2026-09-28)')
    # data files parse; clip strings resolve or fall back
    lesson_audio = {d: [n for n in FULL_LESSON if f'lessons/{d}/audio/{n}' in pub] for d in
                    {m.group(1) for f in pub for m in [re.match(r'lessons/(\d{4}-\d{2}-\d{2})/', f)] if m}}
    no_fallback, fallback_needed, missing_total = {}, {}, 0
    for f in sorted(x for x in pub if x.startswith('data/') and x.endswith('.json')):
        try:
            doc = json.loads((DOCS / f).read_text(encoding='utf-8'))
        except Exception as ex:
            add('data', f, f'does not parse as JSON ({str(ex)[:80]})')
            continue
        for s in iter_strings(doc):
            if len(s) > 300 or ' ' in s or not AUDIO.search(re.split(r'[?#]', s)[0]) or s.lower().startswith(SKIP_SCHEMES):
                continue
            cands = clip_candidates(s)
            if any(c in pub for c in cands):
                continue
            missing_total += 1
            clip = next((c for c in cands if CLIP.search(c)), None)
            if clip and lesson_audio.get(CLIP.search(clip).group(1)):
                fallback_needed.setdefault(f, []).append(s)       # js/clip-fallback.js plays the full lesson instead
                continue
            no_fallback.setdefault(f, []).append(s)
    for f, xs in no_fallback.items():
        add('clips', f, f'{len(xs)} audio clip(s) missing with no full-lesson recording to fall back to, e.g. {xs[0]}')
    for f, xs in fallback_needed.items():               # the fallback only helps on pages that load clip-fallback.js
        name = f.rsplit('/', 1)[-1]
        for page, plays, has, reads in clip_pages:
            one = re.match(r'lessons/(\d{4}-\d{2}-\d{2})\.html$', page)     # a lesson page only plays its own date's clips
            mine = [x for x in xs if one.group(1) in x] if one else xs
            if plays and not has and name in reads and mine:
                add('clips', page, f'plays clips from {f} ({len(mine)} missing, e.g. {mine[0]}) but does not load js/clip-fallback.js, so they are silent')
    if arabizi:
        node = os.environ.get('NODE') or ('C:/dev/tools/node-v24.18.0-win-x64/node.exe' if os.path.exists('C:/dev/tools/node-v24.18.0-win-x64/node.exe') else 'node')
        r = subprocess.run([node, str(ROOT / 'scripts' / 'arabizi_gaps.cjs')], capture_output=True, text=True, encoding='utf-8', cwd=str(ROOT))
        m = re.search(r'(\d+) words', r.stdout or '')
        if r.returncode != 0 or not m or m.group(1) != '0':
            add('arabizi', 'scripts/arabizi_gaps.cjs', (r.stdout or r.stderr or 'did not run').strip().splitlines()[0][:120])
    return {'pages': len(pages), 'published_files': len(pub), 'missing_clips_with_fallback': missing_total - sum(len(v) for v in no_fallback.values()),
            'problems': [{'kind': k, 'where': w, 'what': x} for k, w, x in problems], 'secs': round(time.time() - t0, 1)}


def one_line(res):
    ps = res['problems']
    if not ps:
        return f"pages OK: {res['pages']} pages, every link, data file and clip resolves ({res['missing_clips_with_fallback']} references to unpublished clips play from the full lesson recording)"
    kinds = {}
    for p in ps:
        kinds.setdefault(p['kind'], []).append(p)
    words = {'links': 'broken link', 'data': 'missing or unreadable data file', 'clips': 'dead audio clip problem',
             'hub': "Amal's hub remnant", 'arabizi': 'Arabizi gap'}
    first = ps[0]
    summary = ', '.join(f"{len(v)} {words[k]}{'s' if len(v) != 1 else ''}" for k, v in kinds.items())
    return f"pages NOT OK: {summary}. First: {first['where']}: {first['what']}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    res = check(arabizi='--arabizi' in argv)
    if '--json' in argv:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(one_line(res))
        if '--verbose' in argv:
            for p in res['problems']:
                print(f"  [{p['kind']}] {p['where']}: {p['what']}")
    return 1 if res['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
