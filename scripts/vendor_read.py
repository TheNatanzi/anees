"""Vendor slip-reader test (Medi 2026-10-16: 'also test Gemini (all models) and openai (all models)').
Same frozen inputs the Claude reader tiers got (READER-BRIEF + the files it names + the key transcript), inlined because
an API model cannot open files. One read per model per lesson. Writes data/lesson-work/reader-tiers/runs/<date>.<tag>-run1.json
in the repo given by --repo, plus a usage line per call to vendor-usage.jsonl next to this script.

    python -I vendor_read.py --repo <worktree> --models gemini:gemini-3.8-flash,openai:gpt-5.4-mini --dates 2026-10-10
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error, concurrent.futures as cf

sys.path.insert(0, r'C:\dev\anees-hourly\scripts')
import anees_env as E

HERE = os.path.dirname(os.path.abspath(__file__))
USAGE = os.path.join(HERE, 'vendor-usage.jsonl')


def read(repo, p):
    with open(os.path.join(repo, p), encoding='utf-8') as f:
        return f.read()


def prompt(repo, date):
    brief = read(repo, 'data/lesson-work/full-audit/READER-BRIEF.md')
    system = (
        "You are a reader in a test. The brief below tells you to read files; they are all given to you inline instead, "
        "in <file> blocks, so you cannot and need not open anything. Follow the brief exactly. Where it says to write a "
        "file, return that ONE JSON object as your whole reply (no prose, no code fence). Use reader \"r1\".\n\n"
        "<file path=\"data/lesson-work/full-audit/READER-BRIEF.md\">\n" + brief + "\n</file>\n\n"
        "<file path=\"data/lesson-work/full-audit/buckets.md\">\n" + read(repo, 'data/lesson-work/full-audit/buckets.md') + "\n</file>\n\n"
        "<file path=\"RULES.md\">\n" + read(repo, 'RULES.md') + "\n</file>\n\n"
        "<file path=\"data/lesson-work/full-audit/amal-sheet.txt\">\n" + read(repo, 'data/lesson-work/full-audit/amal-sheet.txt') + "\n</file>\n")
    user = (f"You are reader r1 for lesson {date}. The transcript is below. Read the WHOLE transcript in order, then return "
            f"the JSON object (date, reader, read, coverage_note, counts, rows).\n\n"
            f"<file path=\"data/lesson-work/full-audit/{date}.txt\">\n" + read(repo, f'data/lesson-work/reader-tiers/{date}.txt') + "\n</file>")
    return system, user


def post(url, body, headers, timeout=3600):
    r = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers={**headers, 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read())


def call_openai(model, system, user):
    key = E.env('OPENAI_API_KEY')
    body = {'model': model, 'input': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            'reasoning': {'effort': 'high'}, 'text': {'format': {'type': 'json_object'}}, 'max_output_tokens': 64000}
    body['background'] = True
    H = {'Authorization': 'Bearer ' + key}
    try:
        d = post('https://api.openai.com/v1/responses', body, H, timeout=120)
    except urllib.error.HTTPError as e:
        msg = e.read().decode('utf-8', 'replace')
        if e.code == 400 and 'reasoning' in msg:
            body.pop('reasoning')
            d = post('https://api.openai.com/v1/responses', body, H, timeout=120)
        else:
            raise RuntimeError(f'HTTP {e.code}: {msg[:300]}')
    t_end = time.time() + 3 * 3600
    while d.get('status') in ('queued', 'in_progress') and time.time() < t_end:
        time.sleep(20)
        r = urllib.request.Request('https://api.openai.com/v1/responses/' + d['id'], headers=H)
        d = json.loads(urllib.request.urlopen(r, timeout=120).read())
    if d.get('status') != 'completed':
        raise RuntimeError('openai status ' + str(d.get('status')) + ' ' + str(d.get('error') or d.get('incomplete_details'))[:200])
    text = ''.join(c.get('text', '') for o in d.get('output', []) if o.get('type') == 'message' for c in o.get('content', []))
    u = d.get('usage') or {}
    return text, {'in': u.get('input_tokens'), 'cached': (u.get('input_tokens_details') or {}).get('cached_tokens'),
                  'out': u.get('output_tokens'), 'reasoning': (u.get('output_tokens_details') or {}).get('reasoning_tokens')}


def call_gemini(model, system, user):
    key = E.env('GEMINI_API_KEY') or E.env('GOOGLE_API_KEY')
    body = {'systemInstruction': {'parts': [{'text': system}]}, 'contents': [{'role': 'user', 'parts': [{'text': user}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 60000}}
    try:
        d = post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', body, {'x-goog-api-key': key})
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}')
    cand = (d.get('candidates') or [{}])[0]
    text = ''.join(p.get('text', '') for p in (cand.get('content') or {}).get('parts', []) if not p.get('thought'))
    u = d.get('usageMetadata') or {}
    return text, {'in': u.get('promptTokenCount'), 'cached': u.get('cachedContentTokenCount'), 'out': u.get('candidatesTokenCount'),
                  'reasoning': u.get('thoughtsTokenCount'), 'finish': cand.get('finishReason')}


def call_claude(model, system, user):
    """Claude via the logged-in `claude -p` CLI (Medi's plan): the SAME inline text as the other vendors, no tools."""
    import subprocess
    import tempfile
    sf = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8'); sf.write(system); sf.close()
    r = subprocess.run(['claude', '-p', '--model', model, '--output-format', 'json', '--system-prompt-file', sf.name,
                        '--disallowedTools', 'Bash,Read,Write,Edit,MultiEdit,Glob,Grep,WebFetch,WebSearch,Task,NotebookEdit,TodoWrite'],
                       input=user, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
    try:
        d = json.loads(r.stdout[r.stdout.index('{'):])
    except Exception:
        raise RuntimeError('claude -p: ' + (r.stdout or r.stderr)[:300])
    if d.get('is_error'):
        raise RuntimeError('claude -p error: ' + str(d.get('result'))[:300])
    u = d.get('usage') or {}
    return d.get('result') or '', {'in': (u.get('input_tokens') or 0) + (u.get('cache_read_input_tokens') or 0) + (u.get('cache_creation_input_tokens') or 0),
                                   'out': u.get('output_tokens'), 'cost_usd_plan': d.get('total_cost_usd')}


def parse(text):
    t = text.strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t)
    try:
        return json.loads(t)
    except ValueError:
        a, b = t.find('{'), t.rfind('}')
        return json.loads(t[a:b + 1])


def one(repo, vendor, model, date):
    tag = (f'{vendor}-{model}' + os.environ.get('VR_SUFFIX', '')).replace('/', '_')
    out = os.path.join(repo, 'data', 'lesson-work', 'reader-tiers', 'runs', f'{date}.{tag}-run1.json')
    if os.path.exists(out):
        return tag, date, 'cached', None
    system, user = prompt(repo, date)
    if os.environ.get('VR_EFFORT') and vendor == 'openai':
        pass
    t0 = time.time()
    rec = {'vendor': vendor, 'model': model, 'date': date, 'at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    try:
        text, usage = {'openai': call_openai, 'gemini': call_gemini, 'claude': call_claude}[vendor](model, system, user)
        rec.update(usage=usage, secs=round(time.time() - t0, 1))
        d = parse(text)
        if not isinstance(d.get('rows'), list):
            raise ValueError('no rows list')
        d['model'] = model; d['vendor'] = vendor
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        rec['rows'] = len(d['rows']); status = 'ok'
    except Exception as e:
        rec['error'] = f'{type(e).__name__}: {str(e)[:300]}'; status = 'error'
    with open(USAGE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return tag, date, status, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True); ap.add_argument('--models', required=True); ap.add_argument('--dates', required=True)
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    jobs = [(m.split(':', 1)[0], m.split(':', 1)[1], d) for m in a.models.split(',') for d in a.dates.split(',')]
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for tag, date, status, rec in ex.map(lambda j: one(a.repo, *j), jobs):
            print(date, tag, status, json.dumps((rec or {}).get('usage'))[:160], (rec or {}).get('rows'), (rec or {}).get('error', ''), flush=True)


if __name__ == '__main__':
    main()
