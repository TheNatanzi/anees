"""Is every answer Amal has given in the app? One row per input: given -> stored -> shown -> gap.

    python scripts/amal_inputs_check.py          # table (needs Supabase read access; read-only, never writes)
    python scripts/amal_inputs_check.py --json   # same rows as JSON

given  = what she submitted where she submitted it (Supabase link rows, her Doc notes as applied, Quizlet links she sent)
stored = what the repo keeps as her input (data/vocab/*.json, data/amal-grammar-notes-*.json, docs/data/quizlet/*)
shown  = what a page reads (Word Bank catalog / verb drills, verb-addons.json, grammar console + lesson files,
         Word Bank evidence, Flashcards set tiles)
Engineering audit 2026-09-29 (area 8). Nothing here contacts Amal or changes any row."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent


def load(p, default=None):
    p = ROOT / p
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default


def catalog_checked():
    cat = load('docs/data/word-bank-catalog.json')
    return {p['id'] for g in cat['groups'] for f in g['entries'] for p in f.get('persons', [])
            if p.get('provenance') == 'inferred' and p.get('checked') is True and 'id' in p}


def rows():
    import db
    out = []
    links = db.select('verb_check_links', {'select': 'token,payload,answers'})
    stored1 = load('data/vocab/amal_verb_checks.json', {'answers': {}})['answers']
    shown1 = catalog_checked()
    for r in links:
        ans = (r['answers'] or {}).get('answers', {})
        if r['payload'].get('kind') == 'verb-addons':
            addon = load('data/vocab/amal_addon_checks.json', {})
            stored = sum(('object' in v) + len(v.get('preps_ok', [])) + len(v.get('preps_off', [])) for v in addon.values())
            tags = load('docs/data/verb-addons.json', {'verbs': {}})['verbs']
            shown = sum(1 for v in tags.values() if v.get('source') == 'amal')
            out.append(dict(input='Verb check list 2 (endings/prepositions)', token=r['token'][:6], given=len(ans), stored=stored,
                            shown=shown, unit='answers (shown = verbs tagged from her answers)'))
        else:
            ids = set(r['payload']['items'])
            st = {k for k in stored1 if k in ids}
            out.append(dict(input='Verb check list 1 (verb forms)', token=r['token'][:6], given=len(ans), stored=len(st),
                            shown=len(st & shown1), unit='forms'))
    review = db.select('amal_rules', {'select': 'word_key,kind', 'source': 'eq.review'})
    out.append(dict(input="Slips-by-pattern review (tutor.html)", token='WcvsRL', given=len({r['word_key'] for r in review}),
                    stored=len({r['word_key'] for r in review}), shown=len({r['word_key'] for r in review}),
                    unit='patterns answered (Supabase is the store; the page reads it live)'))
    tr = db.select('transcript_review_links', {'select': 'token,answers'})
    given = sum(len((r['answers'] or {}).get('answers', {})) for r in tr)
    ev = load('docs/data/word-bank-evidence.json', {'events': []})['events']
    shown = len({i for e in ev for i in (e.get('review_ids') or [])})
    out.append(dict(input='Word review (09-05 transcript)', token=','.join(r['token'][:6] for r in tr), given=given, stored=given,
                    shown=shown, unit='answers (shown = Word Bank rows marked human-reviewed)'))
    notes = load('data/amal-grammar-notes-2026-09-29.json', {'not_counted': [], 'read_and_kept': []})
    uids = [r['uid'] for r in notes['not_counted']]
    console = (ROOT / 'docs/data/grammar-console.json').read_text(encoding='utf-8')
    lesson_files = {r['uid']: (ROOT / f"docs/data/lessons/{r['date']}.json") for r in notes['not_counted']}
    in_both = sum(1 for u in uids if u in console and lesson_files[u].exists() and u in lesson_files[u].read_text(encoding='utf-8'))
    out.append(dict(input='Grammar-rule notes (her Doc, applied 09-29)', token='-', given=len(uids), stored=len(uids), shown=in_both,
                    unit=f"rulings that take a row out of the count (+{len(notes['read_and_kept'])} rows read and kept)"))
    # tests/test_m4_after.py stands in for Amal on a fresh 2026-09-04 after-link (its fixture lesson) and deletes it
    # afterwards; while it runs those rows look like hers. The real 09-04 links expired 2026-09-12, so a 09-04 link
    # made later is the test, never Amal.
    links = {r['token'] for r in db.select('amal_links', {'select': 'token,lesson_date,created_at'})
             if not (r['lesson_date'] == '2026-09-04' and r['created_at'] > '2026-09-12')}
    after = [r for r in db.select('amal_rules', {'select': 'token,kind,payload', 'source': 'eq.after'}) if r['token'] in links]
    verdicts = [r for r in after if r['kind'] in ('right', 'wrong', 'not_medi', 'alias', 'no', 'skip')]
    out.append(dict(input='After-lesson links (was he right here?)', token='-', given=len(verdicts), stored=len(verdicts),
                    shown=sum(1 for r in verdicts if (r['payload'] or {}).get('applied')), unit='verdicts (shown = applied to the lesson events)'))
    hw = db.select('homework_answers', {'select': 'amal_verdict,applied'})
    g = [r for r in hw if r['amal_verdict']]
    out.append(dict(input='Homework verdicts', token='-', given=len(g), stored=len(g), shown=sum(1 for r in g if r['applied']), unit='verdicts'))
    sent = load('docs/data/quizlet/sets-sent-to-medi.json', {'sets': []})['sets']
    got = load('docs/data/quizlet/amal-quizlet-sets.json', {'sets': []})['sets']
    sent_ids = {s['id'] for s in sent}
    out.append(dict(input='Quizlet sets she sent (WhatsApp)', token='-', given=len(sent_ids), stored=len(sent_ids & {s['id'] for s in got}),
                    shown=len(sent_ids & {s['id'] for s in got}), unit='sets (shown = on Flashcards; dated ones sit in Sets > by date)'))
    for r in out:
        r['gap'] = r['given'] - min(r['stored'], r['shown']) if r['given'] >= r['shown'] else 0
    return out


def main():
    rs = rows()
    if '--json' in sys.argv:
        print(json.dumps(rs, ensure_ascii=False, indent=1)); return
    print(f"{'input':45} {'given':>6} {'stored':>6} {'shown':>6} {'gap':>5}  unit")
    for r in rs:
        print(f"{r['input']:45} {r['given']:>6} {r['stored']:>6} {r['shown']:>6} {r['gap']:>5}  {r['unit']}")


if __name__ == '__main__':
    main()
