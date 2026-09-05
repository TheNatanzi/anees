"""M4 + M6 - Amal's after-lesson link: 3-5 questions chosen by value (disputed corrections, low-confidence clips, unknown words)
plus the homework suggestion sheet (<= 10 items, Doc words only). Each question = audio <= 15 s + big buttons.

  python scripts/after_questions.py 2026-09-04 [--audio path] [--no-openai]   -> data/lessons/<date>/after_payload.json (+ docs/lessons/<date>/q/*.mp3)
Answers land in amal_rules (right / wrong / not_medi / skip / alias / keep / drop / edit) and scripts/apply_rules.py re-scores the words."""
import argparse, collections, io, json, re, subprocess, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import ARABIC, arabic_norm, loose
import suggest

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / 'data' / 'lessons'
DOCS = ROOT / 'docs' / 'lessons'
MAX_Q = 5
MIN_Q = 3
Q_CLIP = 15.0
HOMEWORK_ITEMS = 10
AUDIO = {'2026-08-25': ROOT / 'data' / 'aug25' / 'audio' / 'aug25.mp3'}


def cut(audio, start, end, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.2f}', '-t', f'{end - start:.2f}', '-i', str(audio), '-ac', '1', '-ar', '16000', '-b:a', '32k', str(path)], check=True)
    return path.name


def unknown_words(u, words_labeled, wmap, matcher):
    """Arabic tokens Medi said >= 3 times that are not Doc words: candidates for 'is this a word, and how do you spell it?'."""
    from lesson_text import is_filler
    c = collections.Counter(); first = {}
    for w in words_labeled:
        if w['spk'] != 'Medi' or not ARABIC.search(w['w']) or is_filler(w['w']):
            continue
        n = arabic_norm(w['w'])
        if len(n) < 3 or matcher.match(w['w']):
            continue
        c[n] += 1; first.setdefault(n, w)
    return [(n, k, first[n]) for n, k in c.most_common(12) if k >= 3]


def choose(u, words_labeled, wmap, matcher):
    """Ranked question candidates: disputed corrections (possible misses) first, then low-confidence ('?') Arabic spans, then unknown words."""
    q = []
    ok = u['label_confidence']['per_speaker_ok']
    if ok:
        for e in sorted([e for e in u['events'] if e['speaker'] == 'Medi' and e['correction']], key=lambda e: (e.get('cue') != 'recast', e['t_start'])):
            w = wmap.get(e['word_key'], {})
            mkd = e.get('miss_kind')
            q.append({'kind': 'correction', 'value': 3 if mkd in (None, 'word', 'unclear') else 2.5, 't': e['t_start'], 'word_key': e['word_key'], 'arabizi': w.get('arabizi', e['word_key']), 'arabic': w.get('arabic', ''),
                      'english': w.get('english', ''), 'ask': f"Did Medi say {w.get('arabizi', e['word_key'])} right here?",
                      'why': ('the app thinks you corrected it' + (f' (it reads this as a {mkd} slip)' if mkd and mkd not in ('word', 'unclear') else '')),
                      'miss_kind': mkd, 'buttons': ['Right', 'Wrong word', 'Wrong grammar', 'Not Medi']})
    # words the app heard but could not attribute (speaker '?'): only real Doc events, never glue words
    from understand_lesson import GLUE_KEYS, STOP_KEYS
    for e in u['events']:
        if e['speaker'] in ('Medi', 'Amal') or e['word_key'] in GLUE_KEYS or e['word_key'] in STOP_KEYS:
            continue
        d = wmap.get(e['word_key'])
        if not d:
            continue
        q.append({'kind': 'who', 'value': 2, 't': e['t_start'], 'word_key': e['word_key'], 'arabizi': d['arabizi'], 'arabic': d['arabic'], 'english': d['english'],
                  'ask': f"Who said {d['arabizi']} here, and was it right?", 'why': 'the app could not tell the voices apart', 'buttons': ['Medi, right', 'Medi, wrong', 'Not Medi', 'Skip']})
    for n, cnt, w in unknown_words(u, words_labeled, wmap, matcher):
        q.append({'kind': 'unknown', 'value': 1 + min(cnt, 5) / 10, 't': w['s'], 'word_key': None, 'arabizi': '', 'arabic': n, 'english': '',
                  'ask': f"Medi said this {cnt} times. Is it a word you taught? You can type its spelling.", 'why': 'not in your Doc yet', 'buttons': ['Yes, a word', 'No', 'Skip'], 'typed': True})
    # dedupe by word and spread over the lesson; never more than MAX_Q
    out, used, windows = [], set(), set()
    for c in sorted(q, key=lambda c: (-c['value'], c['t'])):
        key = c['word_key'] or c['arabic']
        if key in used or int(c['t'] // 20) in windows:      # never two questions on the same 20-s stretch of audio
            continue
        used.add(key); windows.add(int(c['t'] // 20)); out.append(c)
        if len(out) >= MAX_Q:
            break
    return out


def homework(words, stats, rules, use_openai=True):
    """<= 10 items: sentences to say (from the suggestion engine), words to use, one mini-dialogue. All Doc words."""
    sug = suggest.suggest_sentences(words, stats, rules, n=6, use_openai=use_openai)
    wmap = {w['key']: w for w in words}
    items = [{'kind': 'say', **{k: s[k] for k in ('arabizi', 'arabic', 'english')}, 'keys': s['keys']} for s in sug['sentences']]
    for k in sug['list_a'][:3]:
        if len(items) >= HOMEWORK_ITEMS - 1:
            break
        w = wmap[k]
        items.append({'kind': 'use', 'arabizi': w['arabizi'], 'arabic': w['arabic'], 'english': w['english'][:60], 'keys': [k], 'note': 'use it once in your own sentence'})
    if len(sug['sentences']) >= 2:
        a, b = sug['sentences'][0], sug['sentences'][1]
        items.append({'kind': 'dialogue', 'arabizi': f"A: {a['arabizi']}  B: {b['arabizi']}", 'arabic': f"A: {a['arabic']}  B: {b['arabic']}", 'english': f"A: {a['english']}  B: {b['english']}", 'keys': a['keys'] + b['keys']})
    return items[:HOMEWORK_ITEMS], sug


def payload(date, audio=None, use_openai=True, with_db=True):
    d = LESSONS / date
    u = json.load(io.open(d / 'understanding.json', encoding='utf-8'))
    wl = json.load(io.open(d / 'words_labeled.json', encoding='utf-8'))
    words = suggest.load_words(); wmap = {w['key']: w for w in words}
    from arabizi import Matcher
    m = Matcher(words)
    qs = choose(u, wl, wmap, m)
    audio = Path(audio) if audio else AUDIO.get(date, d / 'audio.mp3')
    for i, q in enumerate(qs):
        cs, ce = max(0.0, q['t'] - 6.0), q['t'] + 9.0
        q['clip'] = f'{date}/q/{cut(audio, cs, ce, DOCS / date / "q" / f"q{i + 1}_{int(cs * 10):06d}_{int(ce * 10):06d}.mp3")}'
        q['clip_start'], q['clip_end'], q['offset'] = round(cs, 2), round(ce, 2), round(q['t'] - cs, 2)
        q['n'] = i + 1
    if with_db:
        import db
        stats = db.select('word_stats'); rules = db.select('amal_rules', {'select': 'kind,word_key,payload,source,lesson_date', 'order': 'created_at.asc'})
        for q in qs:                                   # bind each question to its stored event row (Codex P0: patch by id, never by a time range)
            if q.get('word_key'):
                rows = db.select('word_events', {'lesson_date': f'eq.{date}', 'word_key': f"eq.{q['word_key']}", 'select': 'id,t_start'})
                near = [x for x in rows if abs(float(x['t_start']) - float(q['t'])) < 0.05]
                q['event_id'] = near[0]['id'] if len(near) == 1 else None
                q['who'] = q['kind'] == 'who'
    else:
        stats, rules = [], []
    prev = json.load(io.open(d / 'after_payload.json', encoding='utf-8')) if (d / 'after_payload.json').exists() else {}
    if not use_openai and prev.get('homework'):
        hw, sug = prev['homework'], {'model': prev.get('meta', {}).get('model'), 'cost_usd': 0.0, 'usage': {}, 'rejected': [], 'note': 'homework reused from the previous build (no API call)'}
    else:
        hw, sug = homework(words, stats, rules, use_openai=use_openai)
    out = {'lesson_date': date, 'built': datetime.datetime.now().isoformat(timespec='seconds'), 'questions': qs, 'homework': hw,
           'meta': {'candidates': len(qs), 'model': sug['model'], 'cost_usd': sug['cost_usd'], 'usage': sug['usage'], 'rejected': sug['rejected']}}
    io.open(d / 'after_payload.json', 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('date'); ap.add_argument('--audio'); ap.add_argument('--no-openai', action='store_true')
    a = ap.parse_args()
    p = payload(a.date, a.audio, use_openai=not a.no_openai)
    print(json.dumps({'questions': [(q['n'], q['kind'], q['arabizi'] or q['arabic'], q['clip']) for q in p['questions']], 'homework': [(h['kind'], h['arabizi']) for h in p['homework']], 'meta': p['meta']}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
