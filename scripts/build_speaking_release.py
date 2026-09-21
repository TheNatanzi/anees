"""Build the unified Speaking ledger and scores offline from a private snapshot.

No network/provider calls. This replaces each lesson's derived result, never raw
evidence. Publish with publish_speaking_release.py after independent verification.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import buckets
import speaking_evidence as se
from audit_legacy_speaking import audit_legacy

ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def filehash(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build(snapshot, transcripts, legacy_root, output, decisions_dir=None):
    snapshot=Path(snapshot); output=Path(output); output.mkdir(parents=True,exist_ok=True)
    decisions_dir=Path(decisions_dir or ROOT/'data/speaking')
    sources={name:read(snapshot/(name+'.json')) for name in ('word_events','word_stats','card_results','lessons','words','amal_rules','transcript_review_links')}
    matcher=se.StrictMatcher(sources['words']); ledger=[]; overlays=[]; inputs={}
    review_interpretations=read(decisions_dir/'review-interpretations.json')
    attempt_specs=read(decisions_dir/'context-attempts.json')
    for date,path in sorted(transcripts.items()):
        data=read(path); assert data['lesson']==date
        inputs[str(path)]=filehash(path)
        for s in data['sources'].values():
            if filehash(s['input_path'])!=s['source_sha256']: raise ValueError('Recording hash changed')
            inputs[s['input_path']]=s['source_sha256']
        overlay=se.review_overlay(data,sources['transcript_review_links'],filehash(path),review_interpretations if date=='2026-09-05' else [])
        events=se.assess(se.candidates(data,matcher,overlay))
        decisions_path=decisions_dir/f'adjudications-{date}.json'
        if decisions_path.exists():
            events=se.apply_adjudications(events,read(decisions_path))
        for spec in attempt_specs:
            if spec['lesson_date']!=date: continue
            e=se.bound_attempt(data,spec['item_ids'],spec['word_key'],spec['assessment'],spec['reason'])
            if e['source_sha256']!=spec['source_sha256'] or e['original_text']!=spec['original_text'] or se.sha(e['context'])!=spec['context_sha256']:
                raise ValueError('Stale explicit attempt')
            if e['word_key'] not in matcher.words: raise ValueError('Unknown attempt target')
            events.append(e)
        for e in events:
            e['transcript_url']=f'lessons/{date}.html' if date=='2026-09-10' else None
            e['audio_url']=f'lessons/{date}/audio/{"Medi" if e["speaker"]=="Medi" else "Amal"}.mp3' if date=='2026-09-10' else None
        ledger+=events; overlays+=overlay
    # Audit all old counts. Sep5 is replaced by its canonical participant transcript;
    # older lessons retain only individually source-bound, strict matches.
    for date in sorted({e['lesson_date'] for e in sources['word_events']}-set(transcripts)):
        labels=Path(legacy_root)/'data/lessons'/date/'words_labeled.json'
        audio=Path(legacy_root)/('data/aug25/audio/aug25.mp3' if date=='2026-08-25' else f'data/lessons/{date}/audio.mp3')
        events=audit_legacy(sources['word_events'],read(labels),audio,labels,matcher,date)
        for e in events:
            if e.get('clip'):
                clip=Path(legacy_root)/'docs/lessons'/date/'clips'/e['clip']
                if not clip.exists(): raise ValueError('Missing historical audio clip')
                e['clip_sha256']=filehash(clip)
                e['audio_url']=f'lessons/{date}/clips/{e["clip"]}'
            e['transcript_url']=f'lessons/{date}.html'
        ledger+=events; inputs[str(labels)]=filehash(labels); inputs[str(audio)]=filehash(audio)
    # A rerun must preserve later source-bound human decisions. A changed source
    # context needs deliberate reassessment, not silent replacement of Amal.
    if (snapshot/'speaking_events.json').exists():
        prior={r['id']:r['data'] for r in read(snapshot/'speaking_events.json') if r['data'].get('assessment_status')=='human_reviewed'}
        for e in ledger:
            if e['id'] not in prior: continue
            h=prior.pop(e['id'])
            if h['original_text']!=e['original_text'] or se.sha(h['context'])!=se.sha(e['context']):
                raise ValueError('Human-reviewed source context changed; explicit adjudication required')
            for field in ('word_key','spoken','assessment','assessment_status','reason','human_correction'):e[field]=h[field]
        if prior:raise ValueError('Human-reviewed events would be removed; explicit source correction required')
    ledger.sort(key=lambda e:(e['lesson_date'],e['t_start'] if e['t_start'] is not None else -1,e['id']))
    if len({e['id'] for e in ledger})!=len(ledger): raise ValueError('Duplicate event identity')
    scoring=se.to_scoring(ledger)
    confirmed={(r['lesson_date'],r['word_key']) for r in sources['amal_rules'] if r['kind']=='new' and r.get('word_key')}
    stats=buckets.compute(scoring,sources['card_results'],[r['date'] for r in sources['lessons']],confirmed_new=confirmed)
    old={s['word_key']:s for s in sources['word_stats']}
    for key,s in old.items():
        if key not in stats:
            context=s['progress_context']
            context={**context,'lessons':[],'speaking':{'times_seen':0,'independent_uses':0,'times_missed':0,'last_reviewed':None,'seen_lessons':0,'intro_uses':0,'new_since':context['speaking'].get('new_since')}}
            context['speaking'].update({k:0 for k in ('helped_uses','recall_failures','incorrect_attempts','unresolved','provisional','human_reviewed','mastery_credits')})
            stats[key]={**s,**buckets.progress_from_context(context),'progress_context':context,'times_seen':0,'independent_uses':0,'seen_lessons':0,'last_lesson':None,'grammar_misses':0,'grammar_kinds':[]}
        # Introduction metadata must never leak a Speaking import into Flashcards.
        stats[key]['progress_context']['new']=s['progress_context']['new']
        stats[key].update(buckets.progress_from_context(stats[key]['progress_context']))
        if stats[key]['progress_scores']['flashcards']!=s['progress_scores']['flashcards']:
            raise ValueError('Flashcard score changed: '+key)
    # Unknown candidates get no duplicate credits. They remain discoverable in history.
    by_word={}
    for key,s in sorted(stats.items()):
        if key not in matcher.words and key not in old: continue
        s.pop('new_candidate',None); s.pop('updated_at',None)
        if s.get('last_reviewed') and len(s['last_reviewed'])==10: s['last_reviewed']+='T00:00:00+00:00'
        by_word[key]=s
    summary=[]
    for date in sorted({e['lesson_date'] for e in ledger}):
        medi=[e for e in ledger if e['lesson_date']==date and e['speaker']=='Medi']
        counted=[e for e in medi if e['spoken']]
        summary.append({'date':date,'practice_occurrences':len(counted),'vocabulary_entries':len({e['word_key'] for e in counted}),
            'independent_successes':sum(e['assessment']=='independent' and e['spoken'] for e in medi),
            'helped_uses':sum(e['assessment']=='helped' and e['spoken'] for e in medi),
            'recall_failures':sum(e['assessment']=='recall_failure' for e in medi),
            'incorrect_attempts':sum(e['assessment']=='incorrect' for e in medi),
            'unresolved':sum(e['assessment']=='unresolved' for e in medi),
            'review_queue':se.review_queue(medi), 'coverage':'partial; unmatched words are not evidence of absence'})
    changes=[]
    for key in sorted(set(old)|set(by_word)):
        before=old.get(key,{}); after=by_word.get(key,{})
        if any(before.get(k)!=after.get(k) for k in ('times_seen','independent_uses','times_missed','bucket')):
            changes.append({'word_key':key,'before':{k:before.get(k) for k in ('times_seen','independent_uses','times_missed','bucket')},'after':{k:after.get(k) for k in ('times_seen','independent_uses','times_missed','bucket')}})
    revision=se.sha({'events':ledger,'stats':by_word,'overlays':overlays})
    artifact={'version':1,'revision':revision,'lessons':summary,
        'review_summary':{'answered':sum(o['answer'] is not None for o in overlays),'pending':sum(o['status']=='pending' for o in overlays),
                         'statuses':dict(Counter(o['status'] for o in overlays))},
        'vocabulary':{'active_entries':len(matcher.words),'database_snapshot_sha256':filehash(snapshot/'words.json'),
                      'doc_freshness':'September 4 saved Google Doc snapshot; no current live Doc import established'}}
    save(output/'release.json',artifact); save(output/'events.json',ledger); save(output/'stats.json',list(by_word.values()))
    save(output/'overlays.json',overlays); save(output/'changes.json',changes); save(output/'scoring-input.json',scoring)
    save(output/'inputs.json',inputs)
    save(output/'code-hashes.json',{str(p.relative_to(ROOT)):filehash(p) for p in [ROOT/'scripts/speaking_evidence.py',ROOT/'scripts/buckets.py',ROOT/'scripts/audit_legacy_speaking.py',ROOT/'scripts/build_speaking_release.py',ROOT/'docs/js/buckets.js']})
    return artifact

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--snapshot',required=True);p.add_argument('--lesson',action='append',default=[])
    p.add_argument('--legacy-root',required=True);p.add_argument('--output',required=True)
    a=p.parse_args(); result=build(a.snapshot,dict(x.split('=',1) for x in a.lesson),a.legacy_root,a.output)
    print(json.dumps(result,ensure_ascii=True))
