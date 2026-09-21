import copy
import json
import subprocess
from pathlib import Path
import pytest
import buckets
import speaking_evidence as se

ROOT=Path(__file__).resolve().parents[1]
def fixture(texts,speaker='Medi',date='2026-09-10'):
    return {'lesson':date,'sources':{'track':{'speaker_label':speaker,'source_sha256':'a'*64,'track_offset_s':.5,'duration_s':100}},
      'rows':[{'id':'row','source_id':'track','speaker_label':speaker,'timeline_start':.5,'timeline_end':len(texts)+.5,'text':' '.join(texts),
      'items':[{'id':f'i{n}','type':'word','text':t,'local_start':n,'local_end':n+.4,'timeline_start':n+.5,'timeline_end':n+.9} for n,t in enumerate(texts)]}]}
def evidence(day=1,status='independent',spoken=True,**kw):
    return dict(id=str(day),lesson_date=f'2026-09-{day:02}',word_key='x',speaker='Medi',t_start=1,text='كلمة',
        assessment=status,assessment_status='provisional',spoken=spoken,eligible_evidence=True,**kw)
def score(es,new=False,cards=()):
    return buckets.compute(es,list(cards),[e['lesson_date'] for e in es],confirmed_new={('2026-09-01','x')} if new else set())['x']['progress_scores']['speaking']

def test_mneeh_two_practice_one_independent_one_helped():
    s=score([evidence(status='independent'),evidence(status='helped')],new=True)
    assert (s['times_seen'],s['independent_uses'],s['helped_uses'],s['bucket'],s['mastery_streak'])==(2,1,1,'new',1)

def test_five_repetitions_and_five_dates_have_different_arithmetic():
    s=score([evidence(status='helped') for _ in range(5)],new=True)
    assert (s['intro_uses'],s['mastery_streak'],s['bucket'])==(5,0,'shaky')
    assert score([evidence(i) for i in range(1,6)])['bucket']=='ice_cold'
    assert score([evidence(i) for i in [1,1,2,3,3]])['mastery_streak']==3

def test_recovery_and_new_exposure_cannot_erase_miss():
    miss=evidence(status='recall_failure',spoken=False)
    assert score([miss])['times_seen']==0
    assert score([miss,evidence(2)])['bucket']=='shaky'
    assert score([miss,evidence(2),evidence(3)])['bucket']=='cold'
    assert score([miss,evidence(2),evidence(3,'incorrect')])['bucket']=='missed'
    s=score([miss]+[evidence(status='helped') for _ in range(5)],new=True)
    assert s['bucket']=='missed' and s['times_seen']==5 and s['times_missed']==1

def test_grammar_and_unresolved_are_not_lexical_misses():
    assert score([evidence(status='unresolved')])['times_missed']==0
    e=evidence();e.update(assessment='independent',miss_kind='gender',correction=True)
    assert score([e])['times_missed']==0
    assert score([evidence(1,'incorrect'),evidence(2,'unresolved')])['bucket']=='missed'

def test_strict_hazards_and_phrase_overlap():
    words=[{'key':'laugh','arabic':'بضحك'},{'key':'cause','arabic':'بضحِّك'},
           {'key':'bored','arabic':'بزهق'},{'key':'boring','arabic':'بزهِّق'},
           {'key':'cucumber','arabic':'خيار'},{'key':'option','arabic':'خيار'},
           {'key':'today','arabic':'اليوم'},{'key':'day','arabic':'يوم'},
           {'key':'break','arabic':'أنا بكسر'},{'key':'thing','arabic':'اشي'},
           {'key':'phrase','arabic':'كل اشي'},{'key':'all','arabic':'كل'},
           {'key':'mneeh','arabic':'منيح','arabizi':'mneeh','aliases':['mnii7']}]
    m=se.StrictMatcher(words)
    assert set(m.match('بضحك'))=={'laugh','cause'}
    assert set(m.match('بزهق'))=={'bored','boring'}
    assert set(m.match('خيار'))=={'option','cucumber'}
    assert list(m.match('يوم'))==['day'] and list(m.match('اليوم'))==['today']
    assert m.match('بكسر')=={'break':'first_person_subject_omission'}
    assert not m.match('بخسر') and not m.match('minih') and m.match('mnii7')
    paradigm=se.StrictMatcher([{'key':'ana bakser','arabic':'أنا بكسر'}])
    assert paradigm.match('كسرتي')=={'ana bakser':'explicit_break_conjugation'}
    assert not paradigm.match('انكسرت') and not paradigm.match('بنكسر')
    d=fixture(['كل','اشي']);before=copy.deepcopy(d)
    es=se.candidates(d,m);assert len(es)==1 and es[0]['word_key']=='phrase' and d==before
    assert all(e['word_key']!='phrase' for e in se.candidates(fixture(['كل','English','اشي']),m))
    d['rows'][0]['items'][1].update(local_start=8,local_end=8.4,timeline_start=8.5,timeline_end=8.9)
    assert all(e['word_key']!='phrase' for e in se.candidates(d,m))

def test_duplicate_sources_and_overlaps_do_not_duplicate():
    d=fixture(['كلمة']);d['rows'].append(copy.deepcopy(d['rows'][0]));d['rows'][1]['id']='other';d['rows'][1]['items'][0]['id']='different-asr-id'
    es=se.candidates(d,se.StrictMatcher([{'key':'x','arabic':'كلمة'}]))
    assert len(es)==1
    assert se.candidates(d,se.StrictMatcher([{'key':'x','arabic':'كلمة'}]))==es

def test_inaudible_and_pending_overlay_never_confirm():
    d=fixture(['كلمة']);base={'id':'review','row_id':'row','item_ids':['i0'],'replacement':None}
    m=se.StrictMatcher([{'key':'x','arabic':'كلمة'}])
    pending=se.candidates(d,m,[dict(base,status='pending')])[0]
    assert pending['wording_status']=='asr'
    unclear=se.candidates(d,m,[dict(base,status='inaudible')])[0]
    assert not unclear['spoken'] and unclear['wording_status']=='unresolved'
    assert score([evidence(status='unresolved',spoken=False)])['times_missed']==0

def test_long_tutor_end_cannot_hide_immediate_repeat():
    tutor=dict(evidence(),speaker='Amal',t_start=0,t_end=20)
    learner=dict(evidence(),t_start=5,t_end=5.3,context=[{'row_id':'r','speaker':'Medi','text':'كلمة في جملة','timeline_start':5,'timeline_end':6}],row_id='r')
    assert se.assess([tutor,learner])[1]['assessment']=='helped'

def test_bare_no_never_automatically_creates_error():
    learner=dict(evidence(),t_start=5,t_end=5.3,context=[{'row_id':'r','speaker':'Medi','text':'كلمة في جملة','timeline_start':5,'timeline_end':6},{'row_id':'a','speaker':'Amal','text':'No.','timeline_start':6,'timeline_end':7}],row_id='r')
    assert se.assess([learner])[0]['assessment']=='unresolved'

def test_later_correction_replaces_credit_and_never_changes_cards():
    cards=[{'id':str(i),'word_key':'x','ts':f'2026-09-{d:02}T12:00:00Z','result':'got','attempt':1} for i,d in enumerate([1,1,2,2,3])]
    evs=[evidence(i) for i in range(1,6)]
    before=buckets.compute(evs,cards,[])
    evs[-1]['assessment']='incorrect'
    after=buckets.compute(evs,cards,[])
    assert before['x']['progress_scores']['flashcards']==after['x']['progress_scores']['flashcards']
    assert before['x']['bucket']=='ice_cold' and after['x']['bucket']=='missed'
    assert after['x']['times_seen']==5 and after['x']['independent_uses']==4

def test_python_browser_actual_assessment_parity():
    es=[evidence(1,'recall_failure',False),evidence(2),evidence(3),evidence(4,'unresolved',False),evidence(5,'helped')]
    expected=buckets.compute(es,[],[])
    r=subprocess.run(['node','-e',"require('./docs/js/buckets.js');console.log(JSON.stringify(AneesBuckets.compute("+json.dumps(es)+",[],[])));"],cwd=ROOT,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    actual=json.loads(r.stdout)
    for k,v in actual['x'].items(): assert expected['x'][k]==v,(k,expected['x'][k],v)

def test_saved_review_binding_partial_notes_and_idempotency():
    data=fixture(['كلمة','ثانية'])
    items=[{'id':'q'+str(i),'row_id':'row','source_id':'track','source_word_ids':['i'+str(i)],'proposal':t,'local_start':i,'local_end':i+.4} for i,t in enumerate(['كلمة','ثانية'])]
    payload={'batch_id':'batch','source_sha256':'b'*64,'selection_sha256':'c'*64,'lesson':data['lesson'],'items':items,'groups':[{'row_id':'row','source_sha256':'a'*64}]}
    binding={k:payload[k] for k in ('batch_id','source_sha256','selection_sha256')}
    binding['items']=[[i['id'],i['source_word_ids'],i['proposal']] for i in items]
    review={'lesson_date':data['lesson'],'payload':payload,'answers':{'revision':1,'binding':json.dumps(binding),'answers':{'q0':{'choice':'different','text':'She means another word here','draft':'She means another word here'}}}}
    before=copy.deepcopy(data)
    result=se.review_overlay(data,[review],'b'*64)
    assert [o['status'] for o in result]==['note','pending']
    assert se.review_overlay(data,[review],'b'*64)==result
    corrected=se.corrected_rows(data,result)
    assert corrected[0]['items'][0]['text']=='كلمة' and corrected[0]['items'][0]['unresolved_wording']
    assert data==before
    with pytest.raises(ValueError,match='binding'):se.review_overlay(data,[review],'wrong')
    bad=copy.deepcopy(review);bad['payload']['items'][0]['source_word_ids']=['missing']
    with pytest.raises(ValueError):se.review_overlay(data,[bad],'b'*64)
    with pytest.raises(ValueError,match='Stale'):se.review_overlay(data,[review],'b'*64,[{'item_id':'q0','answer_sha256':'wrong'}])
    other=copy.deepcopy(review);other['lesson_date']='2026-09-05'
    assert se.review_overlay(data,[other],'b'*64)==[]


def test_legacy_recompute_cannot_overwrite_active_ledger(monkeypatch):
    import db,recompute_medi_progress
    monkeypatch.setattr(db,'sql',lambda *a,**k:[{'installed':True}])
    monkeypatch.setattr(db,'select',lambda *a,**k:[{'id':True}])
    monkeypatch.setattr(db,'upsert',lambda *a,**k:pytest.fail('Unexpected write'))
    with pytest.raises(RuntimeError,match='ledger is active'):buckets.recompute_and_store()
    with pytest.raises(RuntimeError,match='ledger is active'):recompute_medi_progress.apply(Path('nonexistent'))
