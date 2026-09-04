"""Anees Check 02: same 50 gold clips, engines side by side (blind, shuffled per row). Medi picks the best."""
import json, io, base64, os, html, random, subprocess
random = random.SystemRandom()
R = 'data/aug25/'
sel = json.load(io.open(R + 'gold_selection_v2.json', encoding='utf-8'))


def load_words(name):
    """Word-level list {s,e,spk,w} per engine."""
    if name == 'dialect':
        d = json.load(io.open(R + 'turns.json', encoding='utf-8'))['words']
        return [{'s': w['s'], 'e': w['e'], 'spk': w['spk'], 'w': w['w']} for w in d]
    if name == 'speechmatics':
        d = json.load(io.open(R + 'speechmatics_ar_en.json', encoding='utf-8'))['results']
        out = []
        for w in d:
            a = w['alternatives'][0]
            if w['type'] == 'word':
                out.append({'s': w['start_time'], 'e': w['end_time'], 'spk': a.get('speaker', '?'), 'w': a['content']})
            elif w['type'] == 'punctuation' and out:
                out[-1]['w'] += a['content']
        return out
    f = {'eleven_auto': 'eleven_scribe_auto.json', 'eleven_ara': 'eleven_scribe_ara.json'}[name]
    d = json.load(io.open(R + f, encoding='utf-8'))['words']
    return [{'s': w['start'], 'e': w['end'], 'spk': w.get('speaker_id', '?'), 'w': w['text']} for w in d if w['type'] == 'word']


def speaker_map(words, ref):
    """Map an engine's raw labels to Medi/Amal by time overlap with the reference (dialect) labels."""
    from collections import Counter, defaultdict
    ref_sorted = sorted(ref, key=lambda w: w['s'])
    import bisect
    starts = [w['s'] for w in ref_sorted]
    votes = defaultdict(Counter)
    for w in words:
        mid = (w['s'] + w['e']) / 2
        i = bisect.bisect_right(starts, mid) - 1
        if 0 <= i < len(ref_sorted) and ref_sorted[i]['e'] + 0.3 >= mid:
            votes[w['spk']][ref_sorted[i]['spk']] += 1
    return {lab: (c.most_common(1)[0][0] if c else '?') for lab, c in votes.items()}


ref_words = load_words('dialect')
engines = {}
for nm in ['dialect', 'speechmatics', 'eleven_auto', 'eleven_ara']:
    ws = load_words(nm)
    mp = {'Medi': 'Medi', 'Amal': 'Amal'} if nm == 'dialect' else speaker_map(ws, ref_words)
    for w in ws:
        w['spk'] = mp.get(w['spk'], w['spk'])
    engines[nm] = ws
    print(nm, 'label map', mp)


import re
FILLER = re.compile(r"^[\W_]*(u+m+|u+h+|u+h+m+|h+m+|m+m+|e+r+|a+h+|أ*م+|ا+م+|آ+|ا{2,}|ه+م+|إ+م+|ء*م+)[\W_]*$", re.I)


def is_filler(w):
    return bool(FILLER.match(w))


def clip_lines(words, st, en):
    """Words inside the clip window, grouped into speaker runs; filler sounds become (pause Ns)."""
    runs = []
    pause = None  # [spk, start, end]

    def flush():
        nonlocal pause
        if pause:
            spk, a, b = pause
            dur = max(0.3, b - a)
            tok = f'<span class="pz">(pause {dur:.1f}s)</span>'
            if runs and runs[-1]['spk'] == spk:
                runs[-1]['text'] += ' ' + tok
            else:
                runs.append({'spk': spk, 'text': tok})
            pause = None

    for w in words:
        mid = (w['s'] + w['e']) / 2
        if mid < st or mid > en:
            continue
        if is_filler(w['w']):
            if pause and pause[0] == w['spk'] and w['s'] - pause[2] < 1.0:
                pause[2] = w['e']
            else:
                flush()
                pause = [w['spk'], w['s'], w['e']]
            continue
        flush()
        if runs and runs[-1]['spk'] == w['spk']:
            runs[-1]['text'] += ' ' + html.escape(w['w'])
        else:
            runs.append({'spk': w['spk'], 'text': html.escape(w['w'])})
    flush()
    return runs

names = list(engines)
EXTRA = [
    {'kind': 'silence', 'start': 46.0, 'end': 51.5, 'why': 'pre-lesson silence'},
    {'kind': 'silence', 'start': 96.0, 'end': 101.5, 'why': 'pre-lesson silence'},
    {'kind': 'silence', 'start': 3628.0, 'end': 3633.5, 'why': 'after goodbye'},
    {'kind': 'silence', 'start': 3690.0, 'end': 3695.5, 'why': 'after goodbye'},
    {'kind': 'disagree', 'start': 223.0, 'end': 233.0, 'why': 'engines disagree'},
    {'kind': 'disagree', 'start': 2445.7, 'end': 2449.2, 'why': 'engines disagree'},
    {'kind': 'disagree', 'start': 2683.5, 'end': 2696.0, 'why': 'engines disagree'},
]
AUDIO = R + 'audio/aug25.mp3'
for j, x in enumerate(EXTRA):
    out = f'{R}clips/{50 + j:02d}.mp3'
    if not os.path.exists(out):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(max(0, x['start'] - 0.5)), '-to', str(x['end'] + 0.7),
                        '-i', AUDIO, '-ac', '1', '-b:a', '48k', out], check=True)
sel = sel + EXTRA
for _i, _r in enumerate(sel):
    _r['clip'] = f'{R}clips/{_i:02d}.mp3'  # bind audio BEFORE any reordering
LESSON_START, LESSON_END = 173.0, 3600.0   # first 'Hello' both sides; goodbye
EXCLUDE = [(218.0, 259.0), (2440.0, 2452.0)]   # Medi talking Farsi to his dad (Medi 2026-09-04)
def _keep(r):
    st, en = r['start'] or 0, r['end'] or 0
    if en < LESSON_START:
        return False
    return not any(st < b and en > a for a, b in EXCLUDE)
sel = [r for r in sel if _keep(r) and r['kind'] != 'silence']  # silence rows judged by data, not by Medi (2026-09-04)
PRI = {'disagree': 0, 'silence': 1, 'correction': 2, 'gap': 3, 'hesitation': 4}
sel = sorted(sel, key=lambda r: PRI.get(r['kind'], 9))  # hard rows first; Medi may stop early
rows = []
key = {}
block = []
for i, r in enumerate(sel):
    st = max(0, (r['start'] or 0) - 0.5)
    en = (r['end'] or st + 3) + 0.7
    if en < st + 2:
        en = st + 2
    if en - st > 14:
        en = st + 14
    b64 = base64.b64encode(open(r['clip'], 'rb').read()).decode()
    if not block:
        base = names[:]
        random.shuffle(base)
        block = [base[k:] + base[:k] for k in range(len(base))]
        random.shuffle(block)
    order = block.pop()
    key[i] = order
    cols = []
    for L, nm in zip('ABCD', order):
        ov = clip_lines(engines[nm], st, en)
        body = ''.join(
            f'<p class="ar" dir="auto"><b class="spk">{html.escape(str(t["spk"]))}:</b> {t["text"]}</p>'
            for t in ov) or '<p class="ar none">(nothing)</p>'
        cols.append(f'<div class="col"><div class="lbl">{L}</div>{body}</div>')
    m = int((r['start'] or 0) // 60)
    s = int((r['start'] or 0) % 60)
    btns = ''.join(f'<button data-v="{L}">{L}</button>' for L in 'ABCD'[:len(order)])
    rows.append(
        f'<div class="row" data-i="{i}"><div class="meta"><span class="k k-{r["kind"]}">{r["kind"]}</span>'
        f'<span class="t">{m:02d}:{s:02d}</span><span class="t">#{i + 1}</span></div>\n'
        f'<audio controls preload="none" src="data:audio/mpeg;base64,{b64}"></audio>\n'
        f'<div class="cols">{"".join(cols)}</div>\n'
        f'<div class="btns">{btns}<button data-v="tie">All same</button><button data-v="none">All wrong</button></div></div>')
n = len(sel)
letters = ', '.join('ABCD'[:len(names)])
CSS = """
:root{--bg:#F4F6F2;--bg2:#fff;--ink:#1B2620;--mute:#5B6A62;--line:#D6DDD8;--teal:#0F6E56;--amber:#B26F0E;--coral:#B54324}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--coral:#F08A6C}}
:root[data-theme="dark"]{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--coral:#F08A6C}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 "Atkinson Hyperlegible",system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:26px;margin:8px 0 4px} .lead{color:var(--mute);margin:0 0 14px}
.bar{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;font-weight:700;z-index:2}
.bar button{margin-left:auto;background:var(--teal);color:#fff;border:0;border-radius:999px;padding:8px 14px;font-weight:700;cursor:pointer}
.row{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:12px 0}
.row.done{opacity:.55}
.meta{display:flex;gap:10px;align-items:center;font-size:12px;color:var(--mute);margin-bottom:6px}
.k{padding:2px 8px;border-radius:999px;border:1px solid var(--line);text-transform:uppercase;letter-spacing:.06em;font-size:11px}
.k-silence{color:var(--mute)} .k-disagree{color:#6B4FBB;border-color:#6B4FBB}
.k-correction{color:var(--teal);border-color:var(--teal)} .k-gap{color:var(--amber);border-color:var(--amber)} .k-hesitation{color:var(--coral);border-color:var(--coral)}
audio{width:100%;margin:4px 0}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin:8px 0}
.col{border:1px solid var(--line);border-radius:10px;padding:8px 10px;min-width:0;overflow-wrap:anywhere}
.lbl{font-weight:700;color:var(--teal);font-size:14px;margin-bottom:4px}
.pz{color:var(--amber);font-size:14px;border:1px dashed var(--amber);border-radius:999px;padding:0 8px;white-space:nowrap}
.ar{font-size:19px;line-height:1.6;margin:6px 0} .none{color:var(--mute);font-size:14px} .spk{font-size:13px;color:var(--mute);margin-inline-end:6px}
.btns{display:flex;gap:8px;flex-wrap:wrap} .btns button{flex:1;min-width:70px;padding:10px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:15px;cursor:pointer}
.btns button.on{background:var(--teal);color:#fff;border-color:var(--teal)} .btns button.on[data-v=none]{background:var(--coral);border-color:var(--coral)} .btns button.on[data-v=tie]{background:var(--amber);border-color:var(--amber)}
.note{font-size:13px;color:var(--mute);margin:20px 0}
"""
JS = """
const K='anees-check-02-v1';let st={};try{st=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
function paint(){let c=0;document.querySelectorAll('.row').forEach(r=>{const v=st[r.dataset.i];r.classList.toggle('done',!!v);if(v)c++;r.querySelectorAll('.btns button').forEach(b=>b.classList.toggle('on',b.dataset.v===v))});document.getElementById('cnt').textContent=c+' / N'}
document.querySelectorAll('.btns button').forEach(b=>b.addEventListener('click',()=>{const r=b.closest('.row');st[r.dataset.i]=b.dataset.v;try{localStorage.setItem(K,JSON.stringify(st))}catch(e){}paint()}));
document.getElementById('copy').addEventListener('click',()=>{const out=Object.entries(st).map(([i,v])=>i+':'+v).join(',');navigator.clipboard.writeText('anees-check-02 '+out).then(()=>{document.getElementById('copy').textContent='Copied'})});
paint();
""".replace('N', str(n))
page = (
    '<meta charset="utf-8"><title>Anees Check 02</title>\n<style>' + CSS + '</style>\n<main>\n<h1>Anees check 02</h1>\n'
    f'<p class="lead">Clips from the Aug 25 lesson only (pre-class talk removed). Each clip was written down by {len(names)} different engines, '
    f'shown as {letters} in a random order on every row. Only the words inside the clip are shown. Hardest clips come first, so stopping early still counts. Filler sounds (um, uh, أمم) are shown as (pause). Play the clip, then tap the letter that matches what was '
    'said best. "All same" if they tie, "All wrong" if none is close.</p>\n'
    f'<div class="bar"><span id="cnt">0 / {n}</span><button id="copy">Copy results</button></div>\n'
    + ''.join(rows) +
    f'\n<p class="note">Answers save on this device. When you hit {n}, tap Copy results and paste them to Claude.</p>\n'
    '</main>\n<script>' + JS + '</script>')
out = os.environ.get('CHECK02_OUT',
                     r'C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\abd0ba78-530c-4869-b100-285fee95f910\scratchpad\anees-check-02.html')
io.open(out, 'w', encoding='utf-8').write(page)
json.dump(key, io.open(R + 'check02_key.json', 'w', encoding='utf-8'), indent=1)
print('page ok, rows', len(rows), 'engines', names, 'size KB', len(page) // 1024)
