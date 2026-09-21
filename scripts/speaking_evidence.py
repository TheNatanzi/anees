"""Source-bound Speaking evidence. Pure functions: no providers, mail or DB writes.

Raw ASR stays immutable. The returned overlay and occurrence ledger are derived.
Matching deliberately does not call arabizi.Matcher: fuzzy=False there still
folds phonemes, strips articles, and resolves some ambiguous words.
"""
import copy
import hashlib
import json
import math
import re
import unicodedata
from collections import defaultdict, Counter
from english_stop import ENGLISH_STOP

VERSION = 'speaking-evidence-1'
STATUSES = {'independent', 'helped', 'recall_failure', 'incorrect', 'unresolved'}
# Audited finite paradigm for the active break lexeme. Deliberately excludes
# بنكسر (ambiguous we break / I get broken), انكسر (intransitive), and بخسر
# (lose or mispronunciation). Inflections retain their original spoken wording.
CONJUGATIONS = {'ana bakser': ('كسر','كسرت','كسرتي','كسروا','كسرتوا','كسرتو','كسرنا',
                              'بتكسر','بتكسري','بتكسروا','بتكسرو','بيكسر','بيكسروا','بيكسرو')}
# Reviewed source identities: kaan alone means was, while kaan biddi means
# wanted. Ra7/raa7 can be a future marker or went; spelling cannot choose the
# sense. Including the future candidate makes ambiguous matches stay pending.
CONTEXT_ALIASES = {'huwe kAn': ('كان','kaan'), 'ra7': ('راح','raa7')}

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def normalize(text):
    text = unicodedata.normalize('NFKC', text).replace('ـ', '')
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.translate(str.maketrans('أإآٱ', 'اااا')).casefold()

def tokens(text):
    if text.rstrip().endswith(('-', '–', '—', '…', '...')):
        return None
    # Keep internal punctuation and language boundaries; never delete English.
    parts = text.split()
    out=[]
    for part in parts:
        part=part.strip('.,!?،؟؛:;"“”()[]')
        if not part or not re.fullmatch(r'[\w\u064b-\u065f’\x27]+', part): return None
        if re.search('[A-Za-z]', part) and re.search('[\u0621-\u064a]', part): return None
        out.append(normalize(part))
    return tuple(out) if out else None

class StrictMatcher:
    def __init__(self, words):
        self.words={w['key']:w for w in words if w.get('active', True)}
        self.index=defaultdict(dict)
        for key,w in self.words.items():
            forms=[(p,'arabic_exact') for p in re.split('[/|]',w.get('arabic') or '')]
            forms += [(w.get('arabizi') or '', 'arabizi_exact')]
            forms += [(a,'approved_alias') for a in w.get('aliases') or []]
            forms += [(a,'explicit_break_conjugation') for a in CONJUGATIONS.get(key,())]
            forms += [(a,'reviewed_context_alias') for a in CONTEXT_ALIASES.get(key,())]
            # Explicit first-person Arabic present form: subject omission changes
            # neither person nor lexeme. No root/skeleton or pronoun stripping in Latin.
            for f,method in list(forms):
                t=tokens(f)
                if method=='arabic_exact' and t and len(t)==2 and t[0]=='انا' and t[1].startswith('ب'):
                    forms.append((t[1],'first_person_subject_omission'))
            for f,method in forms:
                t=tokens(f)
                if t: self.index[t][key]=method
        self.lengths=sorted({len(t) for t in self.index},reverse=True)

    def match(self,text):
        t=tokens(text)
        if t and any(re.search('[a-z]',x) and x in ENGLISH_STOP for x in t): return {}
        return self.index.get(t,{}) if t else {}

def review_overlay(data, reviews, transcript_sha, interpretations=()):
    """Validate all bindings before interpreting a partial review. No mutation.

    Direct Arabic replacements may span multiple original IDs without fabricated
    word timing. Longer mixed-language answers stay notes; targeted substitutions
    must be explicitly adjudicated with the answer hash by a later overlay.
    """
    rows={r['id']:r for r in data['rows']}
    result=[]
    for review in reviews:
        if review['lesson_date'] != data['lesson']: continue
        p=review['payload']; a=review['answers']; binding=json.loads(a.get('binding') or '{}')
        expected={k:p[k] for k in ('batch_id','source_sha256','selection_sha256')}
        expected['items']=[[i['id'],i['source_word_ids'],i['proposal']] for i in p['items']]
        if binding != expected or p['source_sha256'] != transcript_sha or p['lesson'] != data['lesson']:
            raise ValueError('Review source/batch binding mismatch')
        for i in p['items']:
            row=rows.get(i['row_id']); source=data['sources'].get(i['source_id'])
            group=next((g for g in p['groups'] if g['row_id']==i['row_id']),None)
            if not row or not source or not group or row['source_id']!=i['source_id'] or source['source_sha256']!=group['source_sha256']:
                raise ValueError('Review row/recording binding mismatch')
            items={x['id']:x for x in row['items']}
            if not all(x in items and items[x]['type']=='word' for x in i['source_word_ids']):
                raise ValueError('Review word binding mismatch')
            part=[items[x] for x in i['source_word_ids']]
            if ' '.join(x['text'] for x in part)!=i['proposal'] or part[0]['local_start']!=i['local_start'] or part[-1]['local_end']!=i['local_end']:
                raise ValueError('Review original wording/time mismatch')
            ans=(a.get('answers') or {}).get(i['id'])
            entry={'id':sha([p['batch_id'],i['id']]),'lesson_date':data['lesson'],
                'batch_id':p['batch_id'],'item_id':i['id'],'row_id':i['row_id'],
                'source_id':i['source_id'],'source_sha256':source['source_sha256'],
                'item_ids':i['source_word_ids'],'original_text':i['proposal'],
                'status':'pending','replacement':None,'answer':ans,'answer_sha256':sha(ans),
                'reviewer':'Amal','revision':a['revision']}
            if ans:
                choice=ans.get('choice'); text=ans.get('text')
                if choice=='yes' and text==i['proposal']: entry['status']='confirmed_wording'
                elif choice=='inaudible' and text is None: entry['status']='inaudible'
                elif choice=='different' and text and text==ans.get('draft','').strip():
                    if re.search('[\u0621-\u064a]',text) and not re.search('[A-Za-z]',text) and len(text.split())<=max(3,len(part)+1):
                        entry.update(status='replacement',replacement=text)
                    else: entry['status']='note'
                else: raise ValueError('Invalid answer')
            result.append(entry)
        if set(a.get('answers',{})) - {i['id'] for i in p['items']}:
            raise ValueError('Unknown review item')
    for decision in interpretations:
        entry=next((o for o in result if o['item_id']==decision['item_id']),None)
        if not entry or entry['answer_sha256']!=decision['answer_sha256']:
            raise ValueError('Stale review interpretation')
        if entry['status']!='note' or not decision.get('reason'):
            raise ValueError('Interpretation is only for explanatory notes')
        entry.update(status='replacement',replacement=decision['replacement'],interpretation=decision)
    return result

def corrected_rows(data, overlay):
    rows=copy.deepcopy(data['rows'])
    by=defaultdict(list)
    for o in overlay: by[o['row_id']].append(o)
    for row in rows:
        for o in by[row['id']]:
            items=[x for x in row['items'] if x['id'] in o['item_ids']]
            for i in items:
                i['review_binding']=o['id']
                if o['status'] in ('confirmed_wording','replacement'): i['human_overlay']=o['id']
            if o['status'] in ('inaudible','note'): # target uncertain, notes are context, not replacement wording
                for i in items: i['unresolved_wording']=True
            if o['status']=='replacement':
                first=items[0]; first['original_text']=' '.join(x['text'] for x in items)
                first['text']=o['replacement']; first['bound_item_ids']=o['item_ids']
                first['local_end']=items[-1]['local_end']; first['timeline_end']=items[-1]['timeline_end']
                for i in items[1:]: i['type']='overlay_consumed'
        row['effective_text']=' '.join('[unresolved wording]' if x.get('unresolved_wording') else x['text'] for x in row['items'] if x['type']=='word')
    return rows

def valid_item(i,source):
    return i['type']=='word' and all(type(i.get(k)) in (int,float) and math.isfinite(i[k]) for k in ('local_start','local_end','timeline_start','timeline_end')) and 0<=i['local_start']<=i['local_end']<=source['duration_s'] and abs(i['timeline_start']-i['local_start']-source['track_offset_s'])<0.001 and abs(i['timeline_end']-i['local_end']-source['track_offset_s'])<0.001


def contextual_match(match, following):
    """Resolve only diagnostic phrases; bare homographs remain unresolved."""
    if set(match) == {'kul', 'kul~eat'}:
        tail = tokens(following) or ()
        # All people, every day, everything, everyone: these are not commands to eat.
        quantifier_followers = {'الناس', 'الكل', 'يوم', 'اليوم', 'مرة', 'إشي', 'اشي', 'شي', 'شيء', 'حدا', 'واحد', 'وحدة',
                                'nas', 'el-nas', 'yom', 'youm', 'yoam', 'shi', 'shee', 'shay', 'eshi', 'ishi', 'hada', '7ada'}
        if tail and tail[0] in {normalize(x) for x in quantifier_followers}:
            return {'kul': 'context_quantifier'}
    return match

def candidates(data, matcher, overlay=()):
    rows=corrected_rows(data,overlay); events=[]; seen=set(); intervals=defaultdict(list)
    for row in sorted(rows,key=lambda r:(r['timeline_start'],r['id'])):
        source=data['sources'][row['source_id']]
        if row['speaker_label'] not in ('Medi','Amal') or source['speaker_label']!=row['speaker_label']: continue
        if row.get('speaker_label') in ('Unknown','?') or row.get('background'): continue
        items=[i for i in row['items'] if i['type']!='spacing']; pos=0
        while pos<len(items):
            found=None
            for length in matcher.lengths:
                part=items[pos:pos+length]
                if len(part)!=length or not all(valid_item(i,source) for i in part): continue
                if any(b['local_start']-a['local_end']>1.2 or b['local_start']<a['local_end']-.02 for a,b in zip(part,part[1:])): continue
                start,end=part[0]['timeline_start'],part[-1]['timeline_end']
                if len(part)>1 and any(r['speaker_label']!=row['speaker_label'] and start<r['timeline_start']<end for r in rows): continue
                match=matcher.match(' '.join(i['text'] for i in part))
                if len(match)>1:
                    following=items[pos+length:pos+length+1]
                    match=contextual_match(match, ' '.join(i['text'] for i in following))
                if match: found=part,match; break
            if not found: pos+=1; continue
            part,match=found; pos+=len(part)
            ids=[x for i in part for x in i.get('bound_item_ids',[i['id']])]
            loc=(round(part[0]['local_start'],3),round(part[-1]['local_end'],3))
            ident=sha([data['lesson'],source['source_sha256'],loc])
            if ident in seen or any(max(loc[0],a)<min(loc[1],b) for a,b in intervals[source['source_sha256']]): continue
            seen.add(ident); intervals[source['source_sha256']].append(loc)
            key=next(iter(match)) if len(match)==1 else None
            context=[{'row_id':r['id'],'speaker':r['speaker_label'],'text':r['effective_text'],
                'timeline_start':r['timeline_start'],'timeline_end':r['timeline_end']}
                for r in rows if r['timeline_end']>=part[0]['timeline_start']-18 and r['timeline_start']<=part[-1]['timeline_end']+12]
            uncertain=any(i.get('unresolved_wording') for i in part)
            events.append({'id':ident,'lesson_date':data['lesson'],'word_key':key,'candidate_keys':sorted(match),
                'source_id':row['source_id'],'source_sha256':source['source_sha256'],'row_id':row['id'],
                'item_ids':ids,'local_start':loc[0],'local_end':loc[1],
                't_start':part[0]['timeline_start'],'t_end':part[-1]['timeline_end'],
                'speaker':row['speaker_label'],'speaker_basis':source.get('speaker_basis'),
                'text':' '.join(i['text'] for i in part),
                'original_text':' '.join(i.get('original_text',i['text']) for i in part),
                'match_method':match.get(key,'ambiguous'),'assessment':'unresolved',
                'assessment_status':'provisional','spoken':row['speaker_label']=='Medi' and bool(key) and not uncertain,
                'wording_status':'unresolved' if uncertain else ('human_reviewed' if any(i.get('human_overlay') for i in part) else 'asr'),
                'review_ids':sorted({i['review_binding'] for i in part if i.get('review_binding')}),
                'context':context,'reason':'Context not yet resolved','version':VERSION})
    return events

def assess(events):
    """Conservative contextual baseline. Explicit adjudications can supersede it.

    Positive connected production supports a *provisional* independent attempt;
    echo, no/recast, and isolated ambiguous language are separately represented.
    Never infer a lexical failure from a correction cue alone.
    """
    for e in events:
        if e['speaker']!='Medi': continue
        e['assessment']='unresolved'
        if not e['word_key'] or not e['spoken']:
            e['reason']='Ambiguous vocabulary or unresolved transcript wording'; continue
        before=[o for o in events if o['speaker']=='Amal' and o['word_key']==e['word_key'] and 0<=e['t_start']-o['t_start']<=15]
        after=[r for r in e['context'] if r['speaker']=='Amal' and 0<=r['timeline_start']-e['t_end']<=8]
        own=next(r['text'] for r in e['context'] if r['row_id']==e['row_id'])
        cue=any(re.search(r'\b(no|instead|wrong|pronounce|correction)\b|(?:^|\s)(لا|مش)(?:\s|[.،؟])',r['text'],re.I) for r in after)
        repeat=any(o['speaker']=='Amal' and o['word_key']==e['word_key'] and 0<=o['t_start']-e['t_end']<=5 for o in events)
        forgot=bool(re.search(r"\b(forgot|forget|don.t know|don.t remember)\b|نسيت|مش عارف",own,re.I))
        meaning=re.search(r'(?:شو\s+يعني|shu\s+ya3ni|what\s+does)\s+(.+)',own,re.I)
        if meaning and e['word_key'] in ('shu','ya3ni'):
            e.update(ignored=True,reason='Question wording, not the unknown vocabulary target'); continue
        if meaning and e['text'].strip(' .،؟?!') in meaning.group(1):
            e.update(assessment='incorrect',classification='lexical',vocab_points=0,reason='Explicit request for this vocabulary item’s meaning'); continue
        if e['word_key']=='shu' and re.fullmatch(r'(?:uh|um|شو|shu|what|huh|[\s،,.?!؟])+',own,re.I):
            e.update(ignored=True,reason='Clarification request, not failed recall of shu'); continue
        # Script is not proficiency: a connected Arabizi sentence is still a
        # connected sentence. Do not award this for an actual supplied echo.
        own_tokens=re.findall(r'[\w]+',own,flags=re.UNICODE)
        if before:
            questions=[r for r in e['context'] if r['speaker']=='Amal' and 0<=e['t_start']-r['timeline_end']<=15 and re.search(r'[?؟]',r['text'])]
            if questions and len(own_tokens)>=3 and not cue and not repeat:
                e.update(assessment='independent',reason='Word used in a new answer; tutor question wording alone is not evidence of help')
            else:
                e.update(assessment='helped',reason='Same vocabulary supplied by Amal within 15 seconds; repetition is practice, not independent credit')
        elif cue or repeat or forgot:
            e['reason']='Tutor cue/repetition or recall language needs contextual adjudication; not automatically an error'
        elif len(own_tokens)>=3:
            e.update(assessment='independent',reason='Word produced in a connected learner phrase, without a recent supplied target; provisional lexical use, pronunciation unverified')
        else:
            e['reason']='Isolated production; insufficient evidence of independent contextual success'
    return events

def apply_adjudications(events, decisions):
    by={e['id']:e for e in events}
    for d in decisions:
        e=by.get(d['event_id'])
        if not e or d['source_sha256']!=e['source_sha256'] or d['original_text']!=e['original_text'] or d['context_sha256']!=sha(e['context']):
            raise ValueError('Stale contextual adjudication')
        if d['assessment'] not in STATUSES or not d.get('reason'): raise ValueError('Invalid adjudication')
        if d.get('word_key') is not None:
            if d['word_key'] not in e['candidate_keys']: raise ValueError('Target is not a matched candidate')
            e['word_key']=d['word_key']; e['match_method']='context_disambiguation'; e['spoken']=e['wording_status']!='unresolved'
        if 'spoken' in d: e['spoken']=d['spoken']
        e.update(assessment=d['assessment'],reason=d['reason'],adjudication=d,
                 assessment_status='human_reviewed' if d.get('reviewer')=='Amal' else 'provisional')
    return events

def bound_attempt(data, item_ids, word_key, assessment, reason):
    """Explicitly adjudicated omitted-target miss/incorrect attempt. No fuzzy match.

    Item IDs bind the actual recall statement or attempted wording, not an invented
    pronunciation of the target. Therefore it cannot increase spoken-use counts.
    """
    rows=[r for r in data['rows'] if any(i['id'] in item_ids for i in r['items'])]
    if len(rows)!=1 or rows[0]['speaker_label']!='Medi': raise ValueError('Attempt must bind one learner row')
    row=rows[0]; items=[i for i in row['items'] if i['id'] in item_ids]
    if len(items)!=len(item_ids) or not items or assessment not in ('recall_failure','incorrect'): raise ValueError('Invalid bound attempt')
    source=data['sources'][row['source_id']]
    if not all(valid_item(i,source) for i in items): raise ValueError('Invalid source time')
    text=' '.join(i['text'] for i in items)
    context=[{'row_id':r['id'],'speaker':r['speaker_label'],'text':r['text'],
        'timeline_start':r['timeline_start'],'timeline_end':r['timeline_end']}
        for r in data['rows'] if r['timeline_end']>=row['timeline_start']-18 and r['timeline_start']<=row['timeline_end']+20]
    return {'id':sha([data['lesson'],source['source_sha256'],[items[0]['local_start'],items[-1]['local_end']],'attempt']),
        'lesson_date':data['lesson'],'word_key':word_key,'candidate_keys':[word_key],
        'source_id':row['source_id'],'source_sha256':source['source_sha256'],'row_id':row['id'],
        'item_ids':item_ids,'local_start':items[0]['local_start'],'local_end':items[-1]['local_end'],
        't_start':items[0]['timeline_start'],'t_end':items[-1]['timeline_end'],'speaker':'Medi',
        'speaker_basis':source.get('speaker_basis'),'text':text,'original_text':text,
        'match_method':'explicit_context_target','assessment':assessment,'assessment_status':'provisional',
        'spoken':False,'wording_status':'asr','review_ids':[],'context':context,'reason':reason,'version':VERSION}

def to_scoring(events):
    out=[]
    for e in events:
        if e['speaker']!='Medi' or not e['word_key']: continue
        a=e['assessment']; miss=a in ('recall_failure','incorrect')
        out.append({**e,'prompted':True if a=='helped' else (None if a=='unresolved' else False),
            'correction':a=='incorrect','asked':a=='recall_failure','miss_kind':'unclear' if a=='unresolved' else None,
            'eligible_evidence':True,'spoken':e['spoken'],'assessment':a})
    return out

def review_queue(events, limit=20):
    priority={'incorrect':0,'recall_failure':1,'unresolved':2,'helped':3,'independent':4}
    candidates=[e for e in events if e['speaker']=='Medi' and e['assessment_status']!='human_reviewed']
    # Diversify across vocabulary; leave every unselected item provisional.
    chosen=[]; seen=set()
    for e in sorted(candidates,key=lambda e:(priority[e['assessment']],e['t_start'],e['id'])):
        key=e['word_key'] or tuple(e['candidate_keys'])
        if key in seen: continue
        seen.add(key); chosen.append(e['id'])
        if len(chosen)==limit: break
    return chosen
