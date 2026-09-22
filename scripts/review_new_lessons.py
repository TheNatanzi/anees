"""Additive contextual review for newly loaded lessons (generic rules only). Idempotent; writes the file once.

  python scripts/review_new_lessons.py 2026-09-14 2026-09-18 2026-09-21

Rules, in order, over the given lessons' events (docs/data/word-bank-evidence.json):
 1. the GENERIC rules of scripts/build_context_audit.py (everything before its hand-made section, plus its
    'repeated restarts within one row' rule);
 2. a resolved non-attempt is not pending;
 3. a scored verb occurrence no catalog form can place is held for review (same test as the audit's form_attributed);
 4. one scored attempt per word per transcript row: later repeats in the row are kept as context, not scored again
    (Codex review 2026-09-23: 09-21 bandora / 09-14 alkul were scored twice);
 5. speakers ESTIMATED from one mixed recording (source id '-meet-'): nothing is scored until a person checks it;
    rule 1 must not promote them (Codex review 2026-09-23: four 09-18 'el-yom' events had been promoted).
Patches it makes carry changes.auto_rule = 'review_new_lessons' and are replaced on a re-run; every other patch,
addition and transcript row is untouched (asserted). No per-lesson or per-event hand edits.
"""
import collections, copy, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = 'review_new_lessons'
KEYS = ['source_sha256', 'row_id', 'word_key', 'text', 't_start', 't_end']
HELD = ' [Speakers estimated from one mixed recording: held until a person checks it.]'


def generic_code():
    src = (ROOT / 'scripts/build_context_audit.py').read_text(encoding='utf8')
    head = src.split('# Source-bound decisions explicitly established')[0]
    tail = src.split('# Repeated restarts within one row should not multiply a scored attempt.')[1].split('out={')[0]
    lines = head.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith('def own('))
    return '\n'.join(lines[start:]) + '\n# duplicate-attempt rule\n' + tail


def patch(e):
    return {'expected': {k: e.get(k) for k in KEYS}, 'changes': {'auto_rule': TAG}}


def estimated(e):
    return '-meet-' in str(e.get('source_id', '')) or 'estimate' in str(e.get('speaker_basis', ''))


def scored(c):
    """Mirror of word-bank-core points(): does this occurrence carry a speaking score?"""
    if (c.get('ignored') or c.get('immediate_repeat') or c.get('grammar_only') or c.get('observation_only') or c.get('is_echo')
            or c.get('scored_in_event') or c.get('needs_review') or c.get('assessment') == 'unresolved'
            or c.get('classification') in ('grammar', 'ignored') or c.get('wording_status') == 'unresolved'):
        return False
    if c.get('vocab_points') in (0, .5, 1):
        return True
    if (c.get('correction') or c.get('human_correction')) and not c.get('classification'):
        return False
    return c.get('assessment') in ('independent', 'helped', 'recall_failure', 'incorrect')


def rules(events):
    """Rules 1, 2, 4, 5 for one lesson's events -> {event id: patch}."""
    ns = {'json': json, 're': re, 'copy': copy, 'hashlib': hashlib, 'collections': collections,
          'events': events, 'patches': {}, 'additions': [], 'row_edits': {}}
    exec(compile(generic_code(), 'generic-rules', 'exec'), ns)
    assert not ns['additions'] and not ns['row_edits'], 'generic rules must not add events or edit rows'
    patches = ns['patches']
    for p in patches.values():
        p['changes']['auto_rule'] = TAG
    shown = lambda e: {**e, **patches.get(e['id'], {}).get('changes', {})}
    for e in events:                                                     # rule 2
        c = shown(e)
        if e['speaker'] == 'Medi' and (c.get('ignored') or c.get('immediate_repeat') or c.get('grammar_only')
                                       or c.get('observation_only') or c.get('scored_in_event')):
            patches.setdefault(e['id'], patch(e))['changes'].update(needs_review=False)
    seen = set()                                                          # rule 4
    for e in sorted(events, key=lambda e: (e['t_start'] if e['t_start'] is not None else -1, e['id'])):
        c = shown(e)
        if e['speaker'] != 'Medi' or not scored(c):
            continue
        k = (e.get('row_id'), c.get('word_key'))
        if k in seen:
            patches.setdefault(e['id'], patch(e))['changes'].update(scored_in_event=True, needs_review=False,
                                                                  reason='Same word again in the same sentence: kept as context, scored once.')
        seen.add(k)
    for e in events:                                                      # rule 5
        c = shown(e)
        if e['speaker'] == 'Medi' and estimated(e) and scored(c):
            patches.setdefault(e['id'], patch(e))['changes'].update(needs_review=True, reason=(c.get('reason') or '') + HELD)
    return patches


def main(dates):
    snap = json.loads((ROOT / 'docs/data/word-bank-evidence.json').read_text(encoding='utf8'))
    path = ROOT / 'docs/data/word-bank-review.json'
    review = json.loads(path.read_text(encoding='utf8'))
    by_id = {e['id']: e for e in snap['events']}
    for k in [k for k, p in review['patches'].items() if p['changes'].get('auto_rule') == TAG and by_id.get(k, {}).get('lesson_date') in dates]:
        del review['patches'][k]                                          # a re-run replaces this script's own patches
    before = copy.deepcopy(review)
    tag = 'lessons-' + '-'.join(d[5:].replace('-', '') for d in dates)
    report = {}
    for day in dates:
        events = [e for e in snap['events'] if e['lesson_date'] == day]
        assert events, f'no published events for {day}'
        patches = rules(events)
        overlap = set(patches) & set(review['patches'])
        assert not overlap, f'{day}: {len(overlap)} events already carry a hand-made patch'
        for p in patches.values():
            if p['changes'].get('audit_version'):
                p['changes']['audit_version'] = f'2026-09-23-{tag}-v1'
        review['patches'].update(patches)
        report[day] = {'events': len(events), 'patches': len(patches),
                       'held_estimated_speakers': sum(HELD in p['changes'].get('reason', '') for p in patches.values()),
                       'scored_once_per_sentence': sum('scored once' in p['changes'].get('reason', '') for p in patches.values())}
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf8') as tmp:   # rule 3 sees rules 1-5
        json.dump(review, tmp, ensure_ascii=False)
    try:
        out = subprocess.run(['node', str(ROOT / 'scripts/unplaced_scored_events.cjs'), *dates], capture_output=True, text=True,
                             check=True, encoding='utf8', env={**os.environ, 'ANEES_REVIEW': tmp.name}).stdout
    finally:
        os.unlink(tmp.name)
    for ident in json.loads(out):                                         # rule 3
        e = by_id[ident]
        assert ident not in before['patches']
        review['patches'].setdefault(ident, patch(e))['changes'].update(
            needs_review=True, reason='Heard form does not match any form of this word in the catalog (for example I-form vs command); held for review, not scored.')
        report[e['lesson_date']]['unplaced_held'] = report[e['lesson_date']].get('unplaced_held', 0) + 1
    review['version'] = re.sub(r'\+lessons-[0-9-]+', '', before['version']) + '+' + tag
    assert all(review['patches'][k] == before['patches'][k] for k in before['patches'])
    assert review['additions'] == before['additions'] and review['transcript_rows'] == before['transcript_rows']
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf8')    # written once, at the end
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
