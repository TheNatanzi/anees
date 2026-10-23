# -*- coding: utf-8 -*-
"""De-word overnight: three blind judges grade one page in one look, on Medi's plans only ($0).

    python scripts/deword_judge.py <shots_dir> <page> <look> [--before <before_dir>] [--judges claude,codex,gemini]

Reads <shots_dir>/<page>-{light,dark}-{desktop,phone}.png and <page>.text.txt (from scripts/deword_capture.py).
Judges (each blind to the others, each on its plan route, API keys removed from its environment):
  claude  `claude -p`                         (Claude plan; reads the PNGs with its Read tool)
  codex   `codex.cmd exec -m gpt-6-astra -i`  (ChatGPT plan)
  gemini  `agy -p --model gemini-3.8-flash-medium` (AI Pro; told the PNG paths)
Writes <shots_dir>/<page>.<look>.grades.json and logs every call as step deword.judge (scripts/track.py).
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    import track
except Exception:  # logging must never stop a judge
    track = None

AGY = os.path.expandvars(r'%LOCALAPPDATA%\agy\bin\agy.exe')
KEYS = ('OPENAI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'ANTHROPIC_API_KEY')
LINES = ['add', 'crucial', 'pictures', 'modes', 'look']
BRIEF = {
    'flat': 'Look A "Flat": the app\'s own calm green/cream (dark: deep green) colours, flat icons, bold colour blocks, '
            'big numbers, short captions. Same app feel, far less text.',
    'kurz': 'Look B "Kurzgesagt-style": a deep navy ground with bright accent colours (yellow, orange, teal, blue, pink), '
            'rounded shapes, simple illustrated shapes drawn as SVG, big friendly numbers. In Light mode a light '
            'variant of the same palette (pale blue ground, navy ink, the same bright accents).',
}
RUBRIC = """You are grading one page of "Anees", a personal Arabic-learning app, for a reader with severe ADD.
The page was just cut down to only crucial content (a number the learner or tutor tracks, an action they take,
or a warning) and turned into pictures where a picture says it better.
{brief}

Grade each line A-F (A = excellent, no real fix left):
- add: can someone with ADD get the point in 5 seconds?
- crucial: every tracked number, row and list the learner or tutor uses is visible on screen (not hidden behind a fold or (i)); only explanation prose is cut. The owner said the first pass "cut out too much data": hiding data is a worse fault than a long page
- pictures: pictures say it better than words would
- modes: reads well in Light and Dark, desktop (1280 px) and phone (390 px): no overflow, no clipped or overlapping text
- look: the look matches its brief and feels like one app

Screenshots (top of the page; open and look at every one): {shots}
In the phone shots the app's fixed bottom menu bar is hidden on purpose (a full-page still would paint it over the middle of the page); in real use it sits at the screen bottom and the page scrolls above it. Do not grade it.
The visible page text (all tabs) follows after the line ---.

Reply with ONLY this JSON, nothing else:
{{"grades":{{"add":"A","crucial":"A","pictures":"A","modes":"A","look":"A"}},"fix":"ONE concrete fix, or empty if all A"}}
---
{text}
"""


def env():
    e = dict(os.environ)
    for k in KEYS:
        e.pop(k, None)
    return e


def parse(out):
    for m in reversed(list(re.finditer(r'\{[^{}]*"grades"\s*:\s*\{[^{}]*\}[^{}]*\}', out or '', re.S))):
        try:
            j = json.loads(m.group(0))
            g = {k: str(j['grades'].get(k, '?')).strip().upper()[:2] for k in LINES}
            return {'grades': g, 'fix': j.get('fix', '')}
        except Exception:
            continue
    m = re.search(r'"grades"\s*:\s*(\{[^{}]*\})', out or '')  # the fix text broke the outer JSON: keep the grades
    if m:
        try:
            g = json.loads(m.group(1))
            f = re.search(r'"fix"\s*:\s*"(.*)', out[m.end():], re.S)
            return {'grades': {k: str(g.get(k, '?')).strip().upper()[:2] for k in LINES},
                    'fix': (f.group(1)[:400] if f else '')}
        except Exception:
            pass
    return None


def run(cmd, prompt, timeout=600, stdin=True):
    t = time.time()
    try:
        p = subprocess.run(cmd, input=prompt if stdin else None, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', env=env(), timeout=timeout, cwd=str(ROOT))
        return p.returncode, (p.stdout or '') + '\n' + (p.stderr or '')[-2000:], int((time.time() - t) * 1000)
    except subprocess.TimeoutExpired:
        return -9, 'timeout', int((time.time() - t) * 1000)


def judge(name, shots, prompt):
    if name == 'claude':
        rc, out, ms = run(['claude', '-p', '--allowedTools', 'Read', '--output-format', 'text'], prompt)
        model = 'claude (plan default)'
    elif name == 'codex':
        cmd = ['codex.cmd', 'exec', '-m', 'gpt-6-astra', '--skip-git-repo-check', '-s', 'read-only']
        for s in shots:
            cmd += ['-i', s]
        rc, out, ms = run(cmd + ['-'], prompt)
        model = 'gpt-6-astra'
    else:
        d = str(Path(shots[0]).parent)
        p = 'Use your file viewing tool (never a shell command) to open each screenshot. ' + prompt
        model = 'gemini-3.8-flash-medium'
        for _ in range(3):  # agy sometimes reaches for a shell tool, gets denied headless and answers empty: retry
            rc, raw, ms = run([AGY, '-p', p, '--add-dir', d, '--mode', 'plan', '--model', model,
                               '--output-format', 'json'], None, stdin=False)
            try:
                out = json.loads(raw[raw.index('{'):].split(chr(10))[0]).get('response', '') or raw
            except Exception:
                out = raw
            if parse(out):
                break
    res = parse(out)
    if track:
        try:
            track.log_run('deword.judge', None, provider={'claude': 'anthropic-plan', 'codex': 'openai-plan',
                                                          'gemini': 'google-plan'}[name], request_model=model,
                          status='ok' if res else 'error', duration_ms=ms, params={'rc': rc})
        except Exception:
            pass
    return name, res, (None if res else out[-600:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shots'); ap.add_argument('page'); ap.add_argument('look')
    ap.add_argument('--judges', default='claude,codex,gemini')
    a = ap.parse_args()
    d = Path(a.shots).resolve()
    shots = [str(d / f'{a.page}-{t}-{v}.png') for t in ('light', 'dark') for v in ('desktop', 'phone')]
    text = (d / f'{a.page}.text.txt').read_text(encoding='utf-8')[:14000]
    prompt = RUBRIC.format(brief=BRIEF[a.look], shots=', '.join(shots), text=text)
    names = a.judges.split(',')
    with ThreadPoolExecutor(len(names)) as ex:
        got = list(ex.map(lambda n: judge(n, shots, prompt), names))
    result = {n: (r if r else {'error': err}) for n, r, err in got}
    (d / f'{a.page}.{a.look}.grades.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    for n, r in result.items():
        if 'grades' in r:
            print(f"{n:7s} {' '.join(r['grades'][k] for k in LINES)}  fix: {r['fix']}")
        else:
            print(f"{n:7s} FAILED: {r['error'][:300]!r}")
    allA = all('grades' in r and all(v == 'A' for v in r['grades'].values()) for r in result.values())
    print('ALL A' if allA else 'not yet')


if __name__ == '__main__':
    main()
