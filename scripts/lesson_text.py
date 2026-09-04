"""Shared text rules for Anees transcripts (fillers = pauses, tutor confirmations = said it right)."""
import re

FILLER = re.compile(r"^[\W_]*(u+m+|u+h+|u+h+m+|h+m+|m+m+|e+r+|a+h+|أ*م+|ا+م+|آ+|ا{2,}|ه+م+|إ+م+|ء*م+)[\W_]*$", re.I)
CONFIRM = re.compile(r"^[\W_]*(m+h+m+|mm-?hmm|uh-?huh|a+h+a+|yes|yeah|yep|yup|exactly|correct|perfect|bravo|ممتاز|أيوه|ايوه|ايوا|أيوا|صح|بالظبط|مظبوط|برافو|عظيم)[\W_]*$", re.I)
ARABIC = re.compile(r'[؀-ۿ]')


def is_filler(w):
    return bool(FILLER.match(w))


def is_confirm(w):
    return bool(CONFIRM.match(w))


def runs_from_words(words, tutor, st=None, en=None, gap=1.0):
    """Group words into speaker runs. Fillers become {'pause': seconds}. Tutor confirmations that open a reply
    right after a learner run containing Arabic are flagged 'ok'.
    words: [{'s','e','spk','w'}] with spk already 'Medi'/'Amal'. Returns [{'spk','s','e','items':[...]}],
    items are {'w': text} | {'pause': sec} | {'w': text, 'ok': True}."""
    runs = []
    pause = None
    for w in words:
        if st is not None:
            dur = max(0.05, w['e'] - w['s'])
            inside = min(w['e'], en) - max(w['s'], st)
            if inside / dur < 0.6:
                continue
        if is_filler(w['w']):
            if pause and pause['spk'] == w['spk'] and w['s'] - pause['e'] < gap:
                pause['e'] = w['e']
            else:
                if pause:
                    _push(runs, pause['spk'], pause['s'], pause['e'], {'pause': round(max(0.3, pause['e'] - pause['s']), 1)})
                pause = {'spk': w['spk'], 's': w['s'], 'e': w['e']}
            continue
        if pause:
            _push(runs, pause['spk'], pause['s'], pause['e'], {'pause': round(max(0.3, pause['e'] - pause['s']), 1)})
            pause = None
        _push(runs, w['spk'], w['s'], w['e'], {'w': w['w']})
    if pause:
        _push(runs, pause['spk'], pause['s'], pause['e'], {'pause': round(max(0.3, pause['e'] - pause['s']), 1)})
    # confirmations
    for k, r in enumerate(runs):
        if r['spk'] != tutor or k == 0:
            continue
        prev = runs[k - 1]
        if prev['spk'] == tutor or not any('w' in it and ARABIC.search(it['w']) for it in prev['items']):
            continue
        for it in r['items']:
            if 'w' not in it or not is_confirm(it['w']):
                break
            it['ok'] = True
    return runs


def _push(runs, spk, s, e, item):
    if runs and runs[-1]['spk'] == spk:
        runs[-1]['items'].append(item)
        runs[-1]['e'] = e
    else:
        runs.append({'spk': spk, 's': s, 'e': e, 'items': [item]})


def run_text(r):
    out = []
    for it in r['items']:
        if 'pause' in it:
            out.append(f"(pause {it['pause']}s)")
        elif it.get('ok'):
            out.append('✓' + it['w'])
        else:
            out.append(it['w'])
    return ' '.join(out)
