"""Reconcile each legacy count against cached labeled source words, without ASR.

Unbound/ambiguous historical matches remain visible but earn no count or score.
Legacy cue-only correctness is not carried forward as verified assessment.
"""
import hashlib
import json
from pathlib import Path
from speaking_evidence import sha, tokens, VERSION

def audit_legacy(raw, words, audio, label_path, matcher, date):
    source_hash=hashlib.sha256(Path(audio).read_bytes()).hexdigest()
    label_hash=hashlib.sha256(Path(label_path).read_bytes()).hexdigest()
    out=[]; occupied=[]
    for old in sorted(raw,key=lambda e:(e.get('t_start') or 0,-((e.get('t_end') or 0)-(e.get('t_start') or 0)),e['id'])):
        if old['lesson_date']!=date: continue
        reason=None; bound=[]
        if old.get('speaker')!='Medi': reason='Tutor/unknown speaker excluded'
        elif old.get('typed_line_id') or str(old.get('text') or '').lower().startswith('homework:'): reason='Typed homework excluded'
        elif not isinstance(old.get('t_start'),(int,float)) or old['t_start']<0: reason='Missing recorded speech timing'
        elif date=='2026-08-25' and any(a<=old['t_start']<=b for a,b in [(218,259),(2440,2452)]): reason='Known background/Farsi interval excluded'
        if reason is None:
            inside=[(i,w) for i,w in enumerate(words) if w['s']>=old['t_start']-.03 and w['e']<=old['t_end']+.03]
            matches=[]
            for start in range(len(inside)):
                for length in matcher.lengths:
                    part=inside[start:start+length]
                    if len(part)!=length or any(w['spk']!='Medi' for _,w in part): continue
                    if any(j!=i+1 or b['s']-a['e']>1.2 for (i,a),(j,b) in zip(part,part[1:])): continue
                    hit=matcher.match(' '.join(w['w'] for _,w in part))
                    if list(hit)==[old['word_key']]: matches.append(part)
            if matches:
                bound=sorted(matches,key=lambda part:(-len(part),part[0][0]))[0]
                interval=(bound[0][1]['s'],bound[-1][1]['e'])
                if any(max(interval[0],a)<min(interval[1],b) for a,b in occupied): reason='Overlapping historical duplicate excluded'
                else: occupied.append(interval)
            else: reason='Legacy match not uniquely recoverable from source words with strict vocabulary identity'
        start=bound[0][1]['s'] if bound else old.get('t_start')
        end=bound[-1][1]['e'] if bound else old.get('t_end')
        ctx=[{'row_id':f'{date}:labeled:{i}','speaker':w['spk'],'text':w['w'],'timeline_start':w['s'],'timeline_end':w['e']}
             for i,w in enumerate(words) if isinstance(start,(int,float)) and w['s']>=start-15 and w['e']<=(end or start)+10]
        out.append({'id':sha(['legacy',date,old['id'],source_hash]),'legacy_event_id':old['id'],
            'lesson_date':date,'word_key':old['word_key'],'candidate_keys':[old['word_key']],
            'speaker':old.get('speaker'),'source_id':f'{date}:meeting-recording','source_sha256':source_hash,
            'source_item_basis':'immutable words_labeled.json array index; original system assigned no word IDs',
            'labels_sha256':label_hash,'row_id':f'legacy-word-event:{old["id"]}',
            'item_ids':[f'{date}:labeled:{i}' for i,_ in bound],
            'local_start':start,'local_end':end,'t_start':start,'t_end':end,
            'text':' '.join(w['w'] for _,w in bound) if bound else old.get('text') or '',
            'original_text':old.get('text') or '', 'clip':old.get('clip'),
            'match_method':'historical_source_exact' if not reason else 'historical_unresolved',
            'assessment':'unresolved','assessment_status':'provisional','spoken':reason is None,
            'wording_status':'asr' if not reason else 'unresolved','review_ids':[],
            'reason':reason or 'Source-bound historical occurrence; old no/recast-based grading withheld pending contextual reassessment',
            'context':ctx,'version':VERSION,'legacy_assessment':{k:old.get(k) for k in ('prompted','correction','asked','miss_kind')}})
    return out
