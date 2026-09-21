"""Score offline review exports against their frozen evidence, without machine gold.

python transcription_score.py --data ../review/review-data.json --output ../review/scored --reviews medi.json amal.json
Omit --reviews to emit explicitly pending scores. Outputs are score.json and
candidate-gold.json. Candidate references remain reviewer assertions, not an
adjudicated reference transcript or a WER measurement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROLES = ('Medi', 'Amal')
VERDICTS = ('exact', 'minor', 'wrong', 'cant_tell')
CHOICES = ('yes', 'no', 'uncertain', 'not_applicable')
METRICS = ('learner_attempt_preserved', 'speaker_correct', 'timestamp_within_1s', 'recall_utterance_preserved')
ARABIC = re.compile(r'[\u0600-\u06ff]')
UNCLEAR = re.compile(r'\[\s*(unclear|inaudible|unintelligible|غير واضح|غير مسموع)\s*\]', re.I)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def object_(value, label):
    require(isinstance(value, dict), f'{label} must be an object')
    return value


def number(value, label, integer=False):
    require(not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value >= 0 and (not integer or int(value) == value),
            f'{label} must be a nonnegative finite {"integer" if integer else "number"}')
    return value


def enum(value, choices, label):
    require(value is None or value in choices, f'Invalid {label}: {value!r}')
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def load(path):
    def unique_pairs(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, f'Duplicate JSON key: {k}')
            result[k] = v
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique_pairs)


def index_data(data):
    object_(data, 'review data')
    require(data.get('schema_version') == '1.0', 'Unsupported review-data schema')
    require(isinstance(data.get('manifest_sha256'), str) and re.fullmatch(r'[0-9a-f]{64}', data['manifest_sha256']),
            'Invalid frozen-manifest SHA-256')
    require(isinstance(data.get('windows'), list) and data['windows'], 'Frozen windows missing')
    windows = {}
    for w in data['windows']:
        object_(w, 'window')
        require(isinstance(w.get('id'), str) and w['id'] not in windows, 'Duplicate/invalid frozen window')
        number(w.get('start'), 'window start'); number(w.get('end'), 'window end')
        require(w['end'] > w['start'], 'Window ends before it starts')
        require(isinstance(w.get('candidates'), list) and w['candidates'], 'Candidates missing')
        candidates = {}
        sources = set()
        for c in w['candidates']:
            require(c.get('id') in ('A', 'B') and c['id'] not in candidates, 'Duplicate/invalid frozen candidate')
            require(isinstance(c.get('source_kind'), str) and c['source_kind'] and c['source_kind'] not in sources,
                    'Candidate source_kind missing or duplicated in window')
            sources.add(c['source_kind'])
            require(isinstance(c.get('runs'), list), 'Frozen runs missing')
            runs = {}
            for r in c['runs']:
                require(isinstance(r.get('id'), str) and r['id'] not in runs and isinstance(r.get('text'), str),
                        'Duplicate/invalid frozen run')
                number(r.get('start'), 'run start'); number(r.get('end'), 'run end')
                require(r['end'] >= r['start'], 'Run ends before it starts')
                runs[r['id']] = r
            candidates[c['id']] = (c, runs)
        require(set(candidates) == {'A', 'B'}, 'Frozen window requires exactly A and B')
        windows[w['id']] = (w, candidates)
    return windows


def validate_export(data, windows, payload):
    object_(payload, 'export')
    require(payload.get('schema_version') == '1.0' and payload.get('kind') == 'anees-human-review', 'Unsupported human-review export')
    for key in ('lesson', 'review_set_id', 'manifest_sha256'):
        require(payload.get(key) == data.get(key), f'{key} does not match frozen evidence')
    people = object_(payload.get('reviewers'), 'reviewers')
    require(bool(people), 'Export has no reviewer records')
    for role, person in people.items():
        require(role in ROLES and person.get('reviewer') == role, 'Unknown/mismatched reviewer')
        number(person.get('active_seconds', 0), 'review time')
        for wid, wr in object_(person.get('windows'), 'reviewer windows').items():
            require(wid in windows and wr.get('id') == wid, f'Unknown/mismatched window: {wid}')
            enum(wr.get('status'), ('pending', 'reviewed'), 'window status')
            require(wr.get('status') is not None, 'Window status missing')
            number(wr.get('active_seconds', 0), 'window time')
            number(wr.get('playback_count', 0), 'playback count', integer=True)
            enum(wr.get('candidate_preference'), ('A', 'B', 'tie', 'neither', 'uncertain'), 'preference')
            w, candidates = windows[wid]
            submitted = object_(wr.get('candidates'), 'submitted candidates')
            require(set(submitted) == set(candidates), 'Unknown/missing candidate ID')
            for cid, cr in submitted.items():
                c, runs = candidates[cid]
                metrics = object_(cr.get('metrics', {}), 'metrics')
                require(set(metrics) <= set(METRICS) | {'unsupported_insertions'}, 'Unknown metric field')
                for k in METRICS:
                    enum(metrics.get(k), CHOICES, k)
                if metrics.get('unsupported_insertions') is not None:
                    number(metrics['unsupported_insertions'], 'unsupported insertions', integer=True)
                for rid, rr in object_(cr.get('runs'), 'submitted runs').items():
                    require(rid in runs and rr.get('id') == rid, f'Unknown/mismatched run ID: {rid}')
                    r = runs[rid]
                    for key, frozen in [('original_text', r['text']), ('start', r['start']), ('end', r['end']), ('speaker', r.get('speaker', 'Unknown'))]:
                        require(rr.get(key) == frozen, f'Run evidence mismatch: {rid} {key}')
                    enum(rr.get('verdict'), VERDICTS, 'run verdict')
                    enum(rr.get('text_certainty'), ('confirmed', 'unclear'), 'text certainty')
                    require(not (rr.get('verdict') == 'cant_tell' and rr.get('text_certainty') == 'confirmed'),
                            f"Can't tell cannot confirm wording: {rid}")
                    enum(rr.get('deliberate_error'), CHOICES, 'deliberate error')
                    require(rr.get('fixed_text') is None or isinstance(rr['fixed_text'], str), 'Invalid fixed text')
                    number(rr.get('active_seconds', 0), 'run time')
                    if rr.get('verdict') == 'exact' and rr.get('fixed_text') is not None:
                        require(rr['fixed_text'] == r['text'], f'Edited text marked exact: {rid}')
                missing_ids = set()
                require(isinstance(cr.get('missing_speech', []), list), 'Missing speech must be an array')
                for m in cr.get('missing_speech', []):
                    require(isinstance(m.get('id'), str) and m['id'] and m['id'] not in missing_ids,
                            'Missing-speech ID missing or duplicated')
                    missing_ids.add(m['id'])
                    require(m.get('speaker') in (*ROLES, 'Unknown') and isinstance(m.get('text'), str), 'Invalid missing-speech content')
                    number(m.get('start'), 'missing start'); number(m.get('end'), 'missing end')
                    require(w['start'] <= m['start'] <= m['end'] <= w['end'], 'Missing-speech times outside window')
                    enum(m.get('text_certainty'), ('confirmed', 'unclear'), 'missing certainty')
    return people


def fraction(n, d):
    return n / d if d else None


COMPARISON_NORMALIZATION = 'NFC and lowercase; remove limited edge punctuation; preserve Arabic letters/diacritics, digits, apostrophes, hyphens, ellipses and repeated words. Whitespace tokenization.'
COMPARISON_EDGE = set('.,!?;:"“”«»()[]{}،؛؟')
COMPARISON_KEYS = ('speech_runs_total', 'exact', 'minor', 'wrong', 'cant_tell', 'unrated', 'confirmed_wording')


def comparison_tokens(text):
    tokens = []
    for token in unicodedata.normalize('NFC', str(text)).lower().split():
        while token and token[0] in COMPARISON_EDGE and not token.startswith('..'):
            token = token[1:]
        while token and token[-1] in COMPARISON_EDGE and not token.endswith('..'):
            token = token[:-1]
        if token: tokens.append(token)
    return tokens


def word_levenshtein(reference, hypothesis):
    prior = [[j, 0, 0, j] for j in range(len(hypothesis) + 1)]
    for i, expected in enumerate(reference, 1):
        row = [[i, 0, i, 0]]
        for j, observed in enumerate(hypothesis, 1):
            if expected == observed:
                row.append(prior[j-1][:])
            else:
                choices = []
                for cell, kind in ((prior[j-1], 1), (prior[j], 2), (row[j-1], 3)):
                    value = cell[:]; value[0] += 1; value[kind] += 1
                    choices.append(value)
                row.append(min(choices, key=lambda value:value[0]))
        prior = row
    errors, substitutions, deletions, insertions = prior[len(hypothesis)]
    return {'S':substitutions,'D':deletions,'I':insertions,'errors':errors,'N':len(reference),
            'word_error_rate':fraction(errors,len(reference))}


def comparison_diagnostic(runs, record):
    d = dict.fromkeys(COMPARISON_KEYS, 0)
    for r in runs:
        if r.get('events'): continue
        d['speech_runs_total'] += 1
        rr = (record or {}).get('runs', {}).get(r['id'], {})
        verdict = rr.get('verdict')
        d[verdict if verdict in VERDICTS else 'unrated'] += 1
        text = rr.get('fixed_text')
        if verdict in ('exact','minor','wrong') and rr.get('text_certainty') == 'confirmed' and isinstance(text,str) and text.strip() and not UNCLEAR.search(text):
            d['confirmed_wording'] += 1
    d['judgment_coverage'] = fraction(d['exact']+d['minor']+d['wrong'],d['speech_runs_total'])
    d['response_coverage'] = fraction(d['exact']+d['minor']+d['wrong']+d['cant_tell'],d['speech_runs_total'])
    return d


def comparison_finite(n):
    return not isinstance(n,bool) and isinstance(n,(float,int)) and math.isfinite(n) and n >= 0


def prepare_comparison(w, c, record):
    result = {'source_kind':c['source_kind'],'diagnostics':comparison_diagnostic(c.get('runs',[]),record),'state':'pending','reason':None}
    def fail(reason): return {**result,'reason':reason}
    speech = [r for r in c.get('runs',[]) if not r.get('events')]
    if not speech: return fail('empty_speech_candidate')
    if not record or 'runs' not in record: return fail('missing_candidate_review')
    all_ids = {r['id'] for r in c.get('runs',[])}
    if any(rid not in all_ids for rid in record['runs']): return fail('unknown_run_id')
    pieces, hypotheses = [], []
    for r in speech:
        rr = record['runs'].get(r['id'])
        if not rr or rr.get('verdict') is None: return fail('speech_runs_unrated')
        if any(rr.get(k) != expected for k,expected in [('id',r['id']),('original_text',r['text']),('start',r['start']),('end',r['end']),('speaker',r.get('speaker') or 'Unknown')]):
            return fail('run_evidence_mismatch')
        if rr['verdict'] == 'cant_tell': return fail('speech_contains_abstention')
        if rr['verdict'] not in ('exact','minor','wrong'): return fail('invalid_verdict')
        text = rr.get('fixed_text')
        if rr.get('text_certainty') != 'confirmed' or not isinstance(text,str) or not text.strip() or UNCLEAR.search(text):
            return fail('speech_wording_unconfirmed')
        if (rr['verdict']=='exact') != (text==r['text']): return fail('verdict_correction_contradiction')
        if not comparison_finite(r['start']) or not comparison_finite(r['end']) or r['end'] <= r['start']:
            return fail('invalid_speech_timing')
        if r.get('crosses_window_boundary') or r['start'] < w['start'] or r['end'] > w['end']:
            return fail('speech_crosses_window_boundary')
        tokens = comparison_tokens(text)
        if not tokens: return fail('empty_reference_tokens')
        pieces.append({'id':r['id'],'start':r['start'],'end':r['end'],'tokens':tokens})
        hypotheses.append({'id':r['id'],'start':r['start'],'end':r['end'],'tokens':comparison_tokens(r['text'])})
    missing = record.get('missing_speech') or []
    if not isinstance(missing,list): return fail('invalid_missing_speech')
    ids = set()
    for m in missing:
        if not m.get('id') or m['id'] in ids: return fail('invalid_missing_speech_id')
        ids.add(m['id'])
        text = m.get('text')
        if m.get('text_certainty') != 'confirmed' or not isinstance(text,str) or not text.strip() or UNCLEAR.search(text):
            return fail('missing_speech_unconfirmed')
        if not comparison_finite(m.get('start')) or not comparison_finite(m.get('end')) or m['end'] <= m['start'] or m['start'] < w['start'] or m['end'] > w['end']:
            return fail('invalid_missing_speech_timing')
        tokens = comparison_tokens(text)
        if not tokens: return fail('empty_missing_speech_tokens')
        pieces.append({'id':m['id'],'start':m['start'],'end':m['end'],'tokens':tokens})
    order = lambda p:(p['start'],p['end'],p['id'])
    pieces.sort(key=order); hypotheses.sort(key=order)
    for prior, current in zip(pieces,pieces[1:]):
        if current['start'] < prior['end'] - .000001: return fail('overlapping_reference_spans')
    reference = [t for p in pieces for t in p['tokens']]
    hypothesis = [t for p in hypotheses for t in p['tokens']]
    if not reference or not hypothesis: return fail('empty_transcript_tokens')
    return {**result,'state':'ready','reason':None,'reference_tokens':reference,'hypothesis_tokens':hypothesis,'confirmed_missing_spans':len(missing)}


def compare_window(w, record):
    out = {'window_id':w.get('id') if w else None,'state':'pending','reason':None,'winner':None,
           'normalization':COMPARISON_NORMALIZATION,'by_candidate':{}}
    if not w or not comparison_finite(w.get('start')) or not comparison_finite(w.get('end')) or w['end'] <= w['start'] or not isinstance(w.get('candidates'),list) or len(w['candidates']) != 2 or {c.get('id') for c in w['candidates']} != {'A','B'} or not all(isinstance(c.get('runs'),list) and c.get('source_kind') for c in w['candidates']) or len({c['source_kind'] for c in w['candidates']}) != 2:
        return {**out,'reason':'invalid_window'}
    if record and record.get('id') != w['id']: return {**out,'reason':'window_evidence_mismatch'}
    for c in w['candidates']:
        out['by_candidate'][c['id']] = prepare_comparison(w,c,(record or {}).get('candidates',{}).get(c['id']))
    if any(c['state'] != 'ready' for c in out['by_candidate'].values()):
        return {**out,'reason':'candidate_review_incomplete_or_ambiguous'}
    a,b = out['by_candidate']['A'],out['by_candidate']['B']
    if a['reference_tokens'] != b['reference_tokens']: return {**out,'reason':'human_reference_disagreement'}
    common = a['reference_tokens']
    a.update(word_levenshtein(common,a['hypothesis_tokens'])); b.update(word_levenshtein(common,b['hypothesis_tokens']))
    return {**out,'state':'ready','reason':None,'winner':'A' if a['errors']<b['errors'] else 'B' if a['errors']>b['errors'] else 'tie',
        'common_reference_tokens':common,'scope':'One complete window, one reviewer, identical independently supplied normalized references. Not adjudicated gold.'}


def summarize_comparison(windows, person, reviewer_conflict=False):
    reports = []
    for w in windows:
        wr = (person or {}).get('windows',{}).get(w['id'])
        if reviewer_conflict:
            reports.append({'window_id':w['id'],'state':'pending','reason':'reviewer_conflict','winner':None,
                'normalization':COMPARISON_NORMALIZATION,'by_candidate':{c['id']:{'source_kind':c['source_kind'],
                    'diagnostics':comparison_diagnostic(c['runs'],(wr or {}).get('candidates',{}).get(c['id'])),
                    'state':'pending','reason':'reviewer_conflict'} for c in w['candidates']}})
        else: reports.append(compare_window(w,wr))
    sources, included, excluded = {}, [], []
    for report in reports:
        if report['state']=='ready': included.append(report['window_id'])
        else: excluded.append({'window_id':report['window_id'],'reason':report['reason'],
            'candidate_reasons':{cid:c['reason'] for cid,c in report['by_candidate'].items()}})
        for c in report['by_candidate'].values():
            s=sources.setdefault(c['source_kind'],{'diagnostics':dict.fromkeys(COMPARISON_KEYS,0),'paired_windows':0,
                'S':0,'D':0,'I':0,'errors':0,'N':0,'word_error_rate':None})
            for k in COMPARISON_KEYS: s['diagnostics'][k]+=c['diagnostics'][k]
            if report['state']=='ready':
                s['paired_windows']+=1
                for k in ('S','D','I','errors','N'): s[k]+=c[k]
    for s in sources.values():
        d=s['diagnostics'];d['judgment_coverage']=fraction(d['exact']+d['minor']+d['wrong'],d['speech_runs_total'])
        d['response_coverage']=fraction(d['exact']+d['minor']+d['wrong']+d['cant_tell'],d['speech_runs_total'])
        s['word_error_rate']=fraction(s['errors'],s['N'])
        if not s['paired_windows']:
            for k in ('S','D','I','errors'): s[k]=None
    keys=sorted(sources)
    lower=None
    if included and len(keys)==2:
        a,b=sources[keys[0]],sources[keys[1]]
        lower=keys[0] if a['errors']<b['errors'] else keys[1] if a['errors']>b['errors'] else 'tie'
    return {'state':'reviewed_subset_available' if included else 'pending',
        'scope':'Lower edit count on the listed jointly reviewed full windows only. Includes English context; not Arabic-specific accuracy or a statistical model winner.',
        'normalization':COMPARISON_NORMALIZATION,'included_window_ids':included,'excluded_windows':excluded,
        'reviewed_paired_windows':len(included),'total_windows':len(windows),'complete_review_set':bool(windows) and len(included)==len(windows),
        'lower_error_source_on_reviewed_subset':lower,'by_source_kind':sources,'windows':reports}


def relevant(role, r):
    speaker = r.get('speaker', 'Unknown')
    return (speaker == 'Medi' or speaker not in ROLES) if role == 'Medi' else (speaker == 'Amal' or speaker not in ROLES or bool(ARABIC.search(r['text'])))


def eligibility(role, r, rr):
    text = rr.get('fixed_text')
    reasons = []
    if not rr.get('verdict'): reasons.append('no_explicit_verdict')
    if rr.get('verdict') == 'cant_tell': reasons.append('reviewer_cannot_determine_wording')
    if rr.get('text_certainty') != 'confirmed': reasons.append('wording_not_confirmed')
    if not isinstance(text, str) or not text.strip(): reasons.append('no_nonblank_confirmed_text')
    if isinstance(text, str) and UNCLEAR.search(text): reasons.append('unclear_marker_present')
    if rr.get('verdict') in ('minor', 'wrong') and text == r['text']: reasons.append('changed_verdict_without_corrected_wording')
    if r.get('events'): reasons.append('audio_event_requires_separate_adjudication')
    if r.get('crosses_window_boundary'): reasons.append('run_extends_beyond_review_audio')
    if role == 'Medi':
        if r.get('speaker') != 'Medi': reasons.append('not_identified_as_Medi_own_attempt')
        if rr.get('deliberate_error') not in ('yes', 'no', 'not_applicable'): reasons.append('Medi_attempt_status_not_explicit')
        if isinstance(text, str) and ARABIC.search(text): reasons.append('Arabic_wording_requires_Amal')
    return not reasons, reasons


def summarize_person(role, person, windows, snapshot_id):
    per_source = {}
    assertions, missing_assertions = [], []
    for wid, (w, candidates) in windows.items():
        wr = person.get('windows', {}).get(wid)
        for cid, (c, runs) in candidates.items():
            source = c['source_kind']
            s = per_source.setdefault(source, {'window_total': 0, 'windows_opened': 0, 'windows_marked_reviewed': 0,
                'speech_runs_total': 0, 'event_runs_total': 0, 'focus_runs_total': 0, 'focus_runs_judged': 0,
                'speech_runs_abstained': 0, 'event_runs_abstained': 0, 'focus_runs_abstained': 0,
                'speech_verdicts': Counter(), 'event_verdicts': Counter(), 'certainty_counts': Counter(),
                'metrics': {k:Counter() for k in METRICS}, 'unsupported_insertions_sum': 0,
                'unsupported_windows_counted': 0, 'unsupported_audio_seconds_counted': 0,
                'missing_entries_total': 0, 'missing_entries_confirmed_nonblank': 0,
                'eligible_reference_assertions': 0, 'preference_counts': Counter(), 'recall_windows_total': 0})
            s['window_total'] += 1
            s['recall_windows_total'] += w.get('category') == 'explicit_recall_or_word_question'
            cr = wr.get('candidates', {}).get(cid) if wr else None
            if wr:
                s['windows_opened'] += 1
                s['windows_marked_reviewed'] += wr['status'] == 'reviewed'
                pref = wr.get('candidate_preference')
                if pref is not None:
                    s['preference_counts']['preferred' if pref == cid else 'other_preferred' if pref in ('A', 'B') else pref] += 1
            for rid, r in runs.items():
                event = bool(r.get('events'))
                s['event_runs_total' if event else 'speech_runs_total'] += 1
                focus = relevant(role, r)
                s['focus_runs_total'] += focus
                rr = cr.get('runs', {}).get(rid) if cr else None
                if not rr: continue
                verdict = rr.get('verdict')
                if verdict == 'cant_tell':
                    s['event_runs_abstained' if event else 'speech_runs_abstained'] += 1
                    s['focus_runs_abstained'] += focus
                elif verdict:
                    s['event_verdicts' if event else 'speech_verdicts'][verdict] += 1
                    s['focus_runs_judged'] += focus
                if rr.get('text_certainty'): s['certainty_counts'][rr['text_certainty']] += 1
                eligible, reasons = eligibility(role, r, rr)
                if verdict or rr.get('fixed_text') is not None or rr.get('text_certainty'):
                    assertions.append({'reviewer':role, 'snapshot_id':snapshot_id, 'window_id':wid,
                        'candidate_id':cid, 'source_kind':source, 'run_id':rid,
                        'start':r['start'], 'end':r['end'], 'speaker':r.get('speaker', 'Unknown'),
                        'original_text':r['text'], 'fixed_text':rr.get('fixed_text'), 'verdict':verdict,
                        'text_certainty':rr.get('text_certainty'), 'deliberate_error':rr.get('deliberate_error'),
                        'evidence_ids':r.get('evidence_ids', []), 'eligible_candidate_reference':eligible,
                        'ineligibility_reasons':reasons,
                        'authority_scope':'Palestinian_Arabic_wording_not_Medi_intention' if role=='Amal' else 'Medi_own_attempt_not_Arabic_authority'})
                    s['eligible_reference_assertions'] += eligible
            if cr:
                for k in METRICS:
                    value = cr.get('metrics', {}).get(k)
                    if value is not None and (k != 'learner_attempt_preserved' or role == 'Medi'):
                        if k != 'recall_utterance_preserved' or w.get('category') == 'explicit_recall_or_word_question':
                            s['metrics'][k][value] += 1
                count = cr.get('metrics', {}).get('unsupported_insertions')
                if count is not None:
                    s['unsupported_insertions_sum'] += count
                    s['unsupported_windows_counted'] += 1
                    s['unsupported_audio_seconds_counted'] += w['end'] - w['start']
                for m in cr.get('missing_speech', []):
                    s['missing_entries_total'] += 1
                    confirmed = m.get('text_certainty') == 'confirmed' and bool(m['text'].strip()) and not UNCLEAR.search(m['text']) and m['end'] > m['start']
                    s['missing_entries_confirmed_nonblank'] += bool(confirmed)
                    missing_assertions.append({'reviewer':role,'snapshot_id':snapshot_id,'window_id':wid,
                        'candidate_id':cid,'source_kind':source, **m,
                        'eligible_candidate_reference':False,
                        'ineligibility_reasons':['missing_speech_schema_has_no_run_verdict_or_adjudication'],
                        'confirmed_omission_annotation':bool(confirmed)})
    for source, s in per_source.items():
        judged = sum(s['speech_verdicts'].values())
        s['speech_runs_judged'] = judged
        s['speech_runs_unjudged'] = s['speech_runs_total'] - judged
        s['speech_runs_responded'] = judged + s['speech_runs_abstained']
        s['speech_runs_unanswered'] = s['speech_runs_total'] - s['speech_runs_responded']
        s['focus_runs_responded'] = s['focus_runs_judged'] + s['focus_runs_abstained']
        s['speech_run_coverage'] = fraction(judged, s['speech_runs_total'])
        s['focus_run_coverage'] = fraction(s['focus_runs_judged'], s['focus_runs_total'])
        s['speech_response_coverage'] = fraction(s['speech_runs_responded'], s['speech_runs_total'])
        s['focus_response_coverage'] = fraction(s['focus_runs_responded'], s['focus_runs_total'])
        s['verdict_denominator_note'] = 'Exact/minor/wrong rates exclude cant_tell abstentions. Response coverage includes abstentions; judged coverage does not.'
        s['exact_rate_among_judged_speech_runs'] = fraction(s['speech_verdicts']['exact'], judged)
        s['wrong_rate_among_judged_speech_runs'] = fraction(s['speech_verdicts']['wrong'], judged)
        s['wrong_or_missing_rate'] = None
        s['wrong_or_missing_rate_reason'] = 'Missing-speech entries are separately reported spans, not standardized runs; no valid combined denominator.'
        s['accuracy'] = None
        s['accuracy_reason'] = 'No overall adjudicated human accuracy. Run verdicts are diagnostic; separate matched-reference comparison is limited to its listed jointly reviewed windows.'
        s['full_focus_review'] = s['windows_marked_reviewed'] == s['window_total'] and s['focus_runs_judged'] == s['focus_runs_total']
        s['full_focus_response'] = s['windows_marked_reviewed'] == s['window_total'] and s['focus_runs_responded'] == s['focus_runs_total']
        s['acceptance_status'] = 'pending_adjudication' if s['full_focus_review'] else 'pending_partial_or_no_human_review'
        for k, counter in list(s['metrics'].items()):
            expected = s['recall_windows_total'] if k == 'recall_utterance_preserved' else s['window_total']
            s['metrics'][k] = {'counts':dict(counter), 'expected_windows':expected,
                'answered_windows':sum(counter.values()), 'decidable_windows':counter['yes']+counter['no'],
                'yes_rate_among_decidable':fraction(counter['yes'],counter['yes']+counter['no']),
                'authority':'Medi only' if k=='learner_attempt_preserved' else 'reviewer-specific assertion'}
        s['unsupported_insertions_per_10_reviewed_audio_minutes'] = fraction(s['unsupported_insertions_sum']*600, s['unsupported_audio_seconds_counted'])
        if not s['unsupported_windows_counted']: s['unsupported_insertions_sum'] = None
    return {'active_seconds':person.get('active_seconds',0), 'by_source_kind':per_source}, assertions, missing_assertions


def score(data, exports):
    windows = index_data(data)
    snapshots = {role:{} for role in ROLES}
    for payload in exports:
        for role, person in validate_export(data, windows, payload).items():
            sid = hashlib.sha256(canonical(person).encode()).hexdigest()
            snapshots[role][sid] = person
    out = {'schema_version':'1.0','kind':'anees-review-score','lesson':data['lesson'],
        'review_set_id':data['review_set_id'],'manifest_sha256':data['manifest_sha256'],
        'human_reference_status':'pending_human_review' if not any(snapshots.values()) else 'candidate_assertions_pending_adjudication',
        'accuracy':None,'acceptance_status':'not_established','reviewers':{},'conflicts':[],
        'limitations':['No machine-generated gold or overall adjudicated accuracy. Conditional edit rates are separate and limited to matched reviewer references.',
            'Randomized A/B mapped to source_kind separately in each window.',
            'Window reviewed flags do not establish full audio coverage or accepted quality.',
            'Arabic-script selection/focus can miss Latin-script Arabic; inspect all runs.',
            'Missing-speech annotations have no standardized run denominator.',
            'Two candidate texts are never merged or treated as consensus.',
            'cant_tell remains unverified; abstentions are excluded from exact/minor/wrong rate denominators.',
            'Legacy verdicts never imply wording confirmation; stored text_certainty is preserved.',
            'Only Medi judgments contribute learner-attempt preservation; recall preservation is never inferred.']}
    assertions, missing = [], []
    for role in ROLES:
        if not snapshots[role]:
            empty = {'reviewer':role,'windows':{},'active_seconds':0}
            metrics, _, _ = summarize_person(role,empty,windows,'no-human-review')
            out['reviewers'][role] = {'status':'no_human_review','metrics':metrics,'snapshot_count':0}
        else:
            summaries = []
            for sid, person in snapshots[role].items():
                metrics, refs, absent = summarize_person(role,person,windows,sid)
                summaries.append({'snapshot_id':sid,'metrics':metrics})
                assertions.extend(refs); missing.extend(absent)
            conflicted = len(summaries)>1
            out['reviewers'][role] = {'status':'conflicting_snapshots' if conflicted else 'human_review_received',
                'snapshot_count':len(summaries),'metrics':None if conflicted else summaries[0]['metrics'],
                'snapshots':summaries if conflicted else []}
            if conflicted: out['conflicts'].append({'type':'different_snapshots_same_reviewer','reviewer':role,'snapshot_ids':list(snapshots[role]),'resolution':'pending; no double-counting or silent replacement'})
    grouped = defaultdict(list)
    for a in assertions:
        if a['text_certainty']=='confirmed' and a.get('fixed_text'):
            grouped[(a['window_id'],a['candidate_id'],a['run_id'])].append(a)
    for key, group in grouped.items():
        if len({a['fixed_text'] for a in group})>1:
            out['conflicts'].append({'type':'confirmed_wording_difference','window_id':key[0],'candidate_id':key[1],'run_id':key[2],
                'assertions':[{'reviewer':a['reviewer'],'snapshot_id':a['snapshot_id'],'fixed_text':a['fixed_text']} for a in group],
                'resolution':'pending_human_adjudication'})
            for a in group:
                a['eligible_candidate_reference'] = False
                a['ineligibility_reasons'].append('unresolved_confirmed_wording_conflict')
    for a in assertions:
        if len(snapshots[a['reviewer']]) > 1:
            a['eligible_candidate_reference'] = False
            a['ineligibility_reasons'].append('unresolved_same_reviewer_snapshots')
    # Source summaries were computed before conflict detection; report eligible
    # counts only after every reviewer-version/wording conflict is preserved.
    for role, person_summary in out['reviewers'].items():
        summaries = person_summary.get('snapshots') or ([{'metrics':person_summary['metrics']}]
            if person_summary.get('metrics') is not None else [])
        for summary in summaries:
            for source, metrics in summary['metrics']['by_source_kind'].items():
                metrics['eligible_reference_assertions'] = sum(
                    a['eligible_candidate_reference'] for a in assertions
                    if a['reviewer'] == role and a['source_kind'] == source
                    and (not summary.get('snapshot_id') or a['snapshot_id'] == summary['snapshot_id']))
    conflicting_roles = {c['reviewer'] for c in out['conflicts'] if c['type']=='different_snapshots_same_reviewer'}
    for c in out['conflicts']:
        if c['type']=='confirmed_wording_difference': conflicting_roles.update(a['reviewer'] for a in c['assertions'])
    for role in ROLES:
        person = next(iter(snapshots[role].values())) if len(snapshots[role])==1 else None
        out['reviewers'][role]['automatic_comparison'] = summarize_comparison(data['windows'],person,role in conflicting_roles)
    gold = {'schema_version':'1.0','kind':'anees-candidate-reference-assertions',
        'lesson':data['lesson'],'review_set_id':data['review_set_id'],'manifest_sha256':data['manifest_sha256'],
        'status':out['human_reference_status'],'adjudicated':False,
        'reference_policy':'Reviewer-anchored candidate assertions only. Never synthesize text or resolve disagreements automatically.',
        'assertions':assertions,'missing_speech_annotations':missing,'conflicts':out['conflicts'],
        'eligible_assertion_count':sum(a['eligible_candidate_reference'] for a in assertions),
        'adjudicated_gold_count':0}
    return out, gold


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, nargs='*', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results, gold = score(load(args.data), [load(p) for p in args.reviews])
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, obj in [('score.json',results),('candidate-gold.json',gold)]:
        (args.output/filename).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':results['human_reference_status'],'eligible_assertions':gold['eligible_assertion_count'],
        'adjudicated_gold_count':0,'conflicts':len(results['conflicts']),'output':str(args.output)},indent=2))


if __name__ == '__main__':
    main()
