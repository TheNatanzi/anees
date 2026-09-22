"""Additive contextual review for newly loaded lessons (generic rules only).

  python scripts/review_new_lessons.py 2026-09-14 2026-09-18 2026-09-21

Runs the GENERIC rules of scripts/build_context_audit.py (everything before its hand-made, source-bound section, plus its
'repeated restarts within one row' rule) over the given lessons' events from docs/data/word-bank-evidence.json, plus the
reliability-pass rule 'a resolved non-attempt is not pending', and merges the patches into docs/data/word-bank-review.json.
It never touches an existing patch, addition or transcript row (asserted). No per-lesson or per-event hand edits.
First used 2026-09-21 for the 09-14 lesson (scratch review_0914.py); this is that script for any list of dates.
"""
import collections, copy, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generic_code():
    src = (ROOT / 'scripts/build_context_audit.py').read_text(encoding='utf8')
    head = src.split('# Source-bound decisions explicitly established')[0]
    tail = src.split('# Repeated restarts within one row should not multiply a scored attempt.')[1].split('out={')[0]
    lines = head.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith('def own('))
    return '\n'.join(lines[start:]) + '\n# duplicate-attempt rule\n' + tail


def patches_for(events):
    ns = {'json': json, 're': re, 'copy': copy, 'hashlib': hashlib, 'collections': collections,
          'events': events, 'patches': {}, 'additions': [], 'row_edits': {}}
    exec(compile(generic_code(), 'generic-rules', 'exec'), ns)
    assert not ns['additions'] and not ns['row_edits'], 'generic rules must not add events or edit rows'
    patches = ns['patches']
    for e in events:
        if e['speaker'] != 'Medi':
            continue
        cur = {**e, **patches.get(e['id'], {}).get('changes', {})}
        if cur.get('ignored') or cur.get('immediate_repeat') or cur.get('grammar_only') or cur.get('observation_only') or cur.get('scored_in_event'):
            p = patches.setdefault(e['id'], {'expected': {k: e.get(k) for k in ['source_sha256', 'row_id', 'word_key', 'text', 't_start', 't_end']}, 'changes': {}})
            p['changes'].update(needs_review=False)
    return patches


def main(dates):
    snap = json.loads((ROOT / 'docs/data/word-bank-evidence.json').read_text(encoding='utf8'))
    path = ROOT / 'docs/data/word-bank-review.json'
    review = json.loads(path.read_text(encoding='utf8'))
    before = copy.deepcopy(review)
    tag = 'lessons-' + '-'.join(d[5:].replace('-', '') for d in dates)
    report = {}
    for day in dates:
        events = [e for e in snap['events'] if e['lesson_date'] == day]
        assert events, f'no published events for {day}'
        patches = patches_for(events)
        overlap = set(patches) & set(review['patches'])
        assert not overlap, f'{day}: {len(overlap)} patches already exist'
        for p in patches.values():
            if p['changes'].get('audit_version'):
                p['changes']['audit_version'] = f'2026-09-23-{tag}-v1'
        review['patches'].update(patches)
        report[day] = {'events': len(events), 'patches': len(patches),
                       'reasons': collections.Counter(v['changes'].get('reason', '(needs_review off)')[:60] for v in patches.values()).most_common(5)}
    # Rule 3 (2026-09-23): a scored verb occurrence that no catalog form can place (e.g. 'أشرب' = I drink, matched to the
    # command 'اشرب' because hamza is not written reliably) is held for review, never scored. Same test as the audit's form_attributed.
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    unplaced = json.loads(subprocess.run(['node', str(ROOT / 'scripts/unplaced_scored_events.cjs'), *dates], capture_output=True, text=True, check=True).stdout)
    by_id = {e['id']: e for e in snap['events']}
    for ident in unplaced:
        e = by_id[ident]
        p = review['patches'].setdefault(ident, {'expected': {k: e.get(k) for k in ['source_sha256', 'row_id', 'word_key', 'text', 't_start', 't_end']}, 'changes': {}})
        assert ident not in before['patches']
        p['changes'].update(needs_review=True, reason='Heard form does not match any form of this word in the catalog (for example I-form vs command); held for review, not scored.')
        report[e['lesson_date']]['unplaced_held'] = report[e['lesson_date']].get('unplaced_held', 0) + 1
    review['version'] = before['version'] + '+' + tag
    assert all(review['patches'][k] == before['patches'][k] for k in before['patches'])
    assert review['additions'] == before['additions'] and review['transcript_rows'] == before['transcript_rows']
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
