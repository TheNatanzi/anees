"""Independent source/count reconciliation. Does not import the implementation.

Reference arithmetic below operates directly on the published ledger, not on
buckets.compute or its progress_context. This catches mutually-consistent bugs
between Python and JavaScript in addition to checking language parity.
"""
import argparse
from collections import defaultdict, Counter
import hashlib
import json
from pathlib import Path
import subprocess

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def verify(folder,snapshot,transcripts,repo):
    folder=Path(folder); snapshot=Path(snapshot);repo=Path(repo)
    events=read(folder/'events.json');stats={s['word_key']:s for s in read(folder/'stats.json')}
    old={s['word_key']:s for s in read(snapshot/'word_stats.json')}
    assert len({e['id'] for e in events})==len(events)
    lookup={}
    for date,path in transcripts.items():
        t=read(path)
        lookup[date]=(t,{i['id']:(r,i) for r in t['rows'] for i in r['items']})
    spans=defaultdict(list);by=defaultdict(list);audio_hashes={};public_text={}
    for e in events:
        if e['lesson_date'] in lookup:
            t,items=lookup[e['lesson_date']];src=t['sources'][e['source_id']]
            assert e['source_sha256']==src['source_sha256']
            bound=[items[i] for i in e['item_ids']]
            assert all(r['id']==e['row_id'] and r['speaker_label']==e['speaker'] and r['source_id']==e['source_id'] for r,i in bound)
            assert ' '.join(i['text'] for r,i in bound)==e['original_text']
            assert abs(bound[0][1]['local_start']-e['local_start'])<.001
            assert abs(bound[-1][1]['local_end']-e['local_end'])<.001
            assert abs(e['local_start']+src['track_offset_s']-e['t_start'])<.001
            if e['transcript_url']:
                public=Path('C:/dev/anees/docs')/e['transcript_url']
                if str(public) not in public_text:public_text[str(public)]=public.read_text(encoding='utf-8')
                assert e['row_id'] in public_text[str(public)]
            if e.get('audio_url'):
                if e['audio_url'] not in audio_hashes:audio_hashes[e['audio_url']]=hashlib.sha256((Path('C:/dev/anees/docs')/e['audio_url']).read_bytes()).hexdigest()
                assert audio_hashes[e['audio_url']]==e['source_sha256']
        if e['spoken']:
            assert e['word_key'] is not None and e['speaker']=='Medi'
            assert e['item_ids'] and e['wording_status']!='unresolved'
            assert not e['text'].lower().startswith('homework:')
            assert 0<=e['local_start']<=e['local_end']
            spans[e['source_sha256']].append((e['local_start'],e['local_end'],e['id']))
        if e['speaker']=='Medi' and e['word_key']:by[e['word_key']].append(e)
    for source,rows in spans.items():
        rows.sort()
        for a,b in zip(rows,rows[1:]):assert a[1]<=b[0]+.001,(source,a,b)
    comparisons=0
    for key,s in stats.items():
        evs=by[key]; spoken=[e for e in evs if e['spoken']];ind=[e for e in spoken if e['assessment']=='independent']
        assert s['times_seen']==len(spoken),(key,'uses')
        assert s['independent_uses']==len(ind),(key,'independent')
        misses=sum(e['assessment'] in ('recall_failure','incorrect') for e in evs)
        assert s['times_missed']==misses,(key,'misses')
        assert s['seen_lessons']==len({e['lesson_date'] for e in spoken}),(key,'dates')
        bucket='never';streak=0;recovery=0;dates=[];credits=0
        for day in sorted({e['lesson_date'] for e in evs}):
            group=[e for e in evs if e['lesson_date']==day]
            fail=any(e['assessment'] in ('recall_failure','incorrect') for e in group)
            success=any(e['assessment']=='independent' and e['spoken'] for e in group)
            help_=any(e['assessment']=='helped' for e in group)
            if fail: bucket='missed';recovery=2;streak=0;dates=[]
            elif success:
                credits+=1;streak+=1;dates.append(day)
                if recovery:recovery-=1
                bucket='shaky' if recovery else ('ice_cold' if streak>=5 else 'cold')
            elif help_:
                bucket='shaky';streak=0;dates=[]
                if recovery:recovery=2
        ctx=s['progress_context']; since=ctx['speaking'].get('new_since')
        intro=sum(since is None or e['lesson_date']>=since for e in spoken)
        if ctx['new'] and intro<5:bucket='new'
        actual=s['progress_scores']['speaking']
        assert actual['bucket']==bucket,(key,'bucket',actual['bucket'],bucket)
        assert actual['mastery_streak']==streak and actual['mastery_days']==dates,(key,'streak/dates')
        assert actual['intro_uses']==intro,(key,'introduction')
        if 'mastery_credits' in actual:assert actual['mastery_credits']==credits
        if key in old:assert old[key]['progress_scores']['flashcards']==s['progress_scores']['flashcards'],(key,'flashcards changed')
        comparisons+=1
    # Browser replay of the actual contexts must reproduce the release's scores.
    node="require('./docs/js/buckets.js');const fs=require('fs');const rows=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));console.log(JSON.stringify(rows.map(s=>AneesBuckets.progressFromContext(s.progress_context))));"
    result=subprocess.run(['node','-e',node,str((folder/'stats.json').resolve())],cwd=repo,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    for s,p in zip(stats.values(),json.loads(result.stdout)):
        assert s['progress_scores']==p['progress_scores'],s['word_key']
    result={'events_checked':len(events),'counted_occurrences':sum(e['spoken'] for e in events),'words_reconciled':comparisons,
            'source_span_checks':'passed','overlap_checks':'passed','independent_arithmetic':'passed','python_browser_parity':'passed',
            'flashcard_score_rows_unchanged':len(old),'flashcard_answers':len(read(snapshot/'card_results.json'))}
    (folder/'verification.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--release',required=True);p.add_argument('--snapshot',required=True);p.add_argument('--repo',required=True);p.add_argument('--lesson',action='append',default=[])
    a=p.parse_args();print(json.dumps(verify(a.release,a.snapshot,dict(x.split('=',1) for x in a.lesson),a.repo)))
