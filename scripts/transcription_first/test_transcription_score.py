"""Synthetic offline scoring tests: no real human assertions or provider calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess

from transcription_score import load, score, compare_window, summarize_comparison, comparison_tokens, word_levenshtein
from transcription_review import window_runs


def fixture():
    windows = []
    for i in (1, 2):
        candidates = []
        for cid, source in [('A', 'separate_tracks'), ('B', 'mixed_recording')] if i == 1 else [('A', 'mixed_recording'), ('B', 'separate_tracks')]:
            candidates.append({'id':cid,'source_kind':source,'runs':[
                {'id':f'w{i}-{cid}-r1','speaker':'Medi','start':(i-1)*25+1,'end':(i-1)*25+3,'text':'ana uh ma-','events':[], 'evidence_ids':[f'{source}:{i}']},
                {'id':f'w{i}-{cid}-r2','speaker':'Amal','start':(i-1)*25+4,'end':(i-1)*25+6,'text':'أنا مبسوطة','events':[], 'evidence_ids':[f'{source}:{i}b']},
                {'id':f'w{i}-{cid}-r3','speaker':'Amal','start':(i-1)*25+7,'end':(i-1)*25+8,'text':'[laughs]','events':[{'text':'[laughs]'}], 'evidence_ids':[f'{source}:{i}c']},
            ]})
        windows.append({'id':f'w{i}','category':'explicit_recall_or_word_question' if i == 1 else 'candidate_self_repair',
                        'start':(i-1)*25,'end':i*25,'candidates':candidates})
    return {'schema_version':'1.0','lesson':'synthetic','review_set_id':'synthetic-test-only','manifest_sha256':'a'*64,'windows':windows}


def export(data, role='Medi'):
    p={'schema_version':'1.0','kind':'anees-human-review','lesson':data['lesson'],'review_set_id':data['review_set_id'],
       'manifest_sha256':data['manifest_sha256'],'reviewers':{role:{'reviewer':role,'active_seconds':0,'windows':{}}}}
    for w in data['windows']:
        p['reviewers'][role]['windows'][w['id']]={'id':w['id'],'status':'pending','active_seconds':0,'playback_count':0,
            'candidate_preference':None,'candidates':{c['id']:{'metrics':{},'runs':{},'missing_speech':[]} for c in w['candidates']}}
    return p


def answer(data, payload, wid='w1', cid='A', rid=None, role='Medi', verdict='exact', text=None, certainty='confirmed', deliberate='no'):
    w=next(w for w in data['windows'] if w['id']==wid)
    c=next(c for c in w['candidates'] if c['id']==cid)
    r=next(r for r in c['runs'] if r['id']==rid) if rid else c['runs'][0]
    rr={'id':r['id'],'speaker':r['speaker'],'start':r['start'],'end':r['end'],'original_text':r['text'],
        'verdict':verdict,'fixed_text':r['text'] if text is None else text,'text_certainty':certainty,
        'deliberate_error':deliberate,'active_seconds':0}
    payload['reviewers'][role]['windows'][wid]['candidates'][cid]['runs'][r['id']]=rr
    return rr


def comparison_fixture():
    # Independently corrected references agree despite different candidate
    # segment boundaries. Original B has an inserted word and a substitution.
    def run(cid, idx, start, end, text):
        return {'id':f'{cid}-{idx}','speaker':'Medi','start':start,'end':end,'text':text,'events':[]}
    w={'id':'paired','start':0,'end':25,'candidates':[
        {'id':'A','source_kind':'separate_tracks','runs':[run('A',1,1,3,'ana uh ma-'),run('A',2,4,6,'ana أَنا')]},
        {'id':'B','source_kind':'mixed_recording','runs':[run('B',1,1,6,'ana uh ma- filler ana أنا')]}]}
    wr={'id':'paired','status':'pending','candidate_preference':'B','candidates':{}}
    for c in w['candidates']:
        cr={'runs':{},'missing_speech':[]};wr['candidates'][c['id']]=cr
        for r in c['runs']:
            cr['runs'][r['id']]={'id':r['id'],'speaker':r['speaker'],'start':r['start'],'end':r['end'],
                'original_text':r['text'],'fixed_text':r['text'] if c['id']=='A' else 'ana uh ma- ana أَنا',
                'verdict':'exact' if c['id']=='A' else 'wrong','text_certainty':'confirmed'}
    return w,wr


class ScoreTests(unittest.TestCase):
    def test_automatic_comparison_same_reference_segmentation_invariant(self):
        w,wr=comparison_fixture();before=copy.deepcopy(wr)
        result=compare_window(w,wr)
        self.assertEqual(result['state'],'ready')
        self.assertEqual(result['winner'],'A')
        self.assertEqual(result['by_candidate']['A']['errors'],0)
        self.assertEqual(result['by_candidate']['B']['S'],1)
        self.assertEqual(result['by_candidate']['B']['I'],1)
        self.assertEqual(result['by_candidate']['B']['N'],5)
        self.assertEqual(wr,before)
        self.assertEqual(wr['candidate_preference'],'B', 'Historical manual vote is never overwritten')

    def test_automatic_comparison_ref_disagreement_never_guesses(self):
        w,wr=comparison_fixture();wr['candidates']['B']['runs']['B-1']['fixed_text']='ana uh ma- ana إنا'
        result=compare_window(w,wr)
        self.assertEqual(result['reason'],'human_reference_disagreement')
        self.assertIsNone(result['winner'])
        self.assertNotIn('word_error_rate',result['by_candidate']['A'])

    def test_automatic_comparison_rejects_ambiguous_and_partial_records(self):
        for case in ('abstention','unconfirmed','empty','boundary','overlap','unrated','bad_original','missing_unclear'):
            w,wr=comparison_fixture()
            if case=='abstention':wr['candidates']['B']['runs']['B-1'].update(verdict='cant_tell',text_certainty='unclear')
            if case=='unconfirmed':wr['candidates']['B']['runs']['B-1']['text_certainty']=None
            if case=='empty':wr['candidates']['B']['runs']['B-1']['fixed_text']=''
            if case=='boundary':w['candidates'][0]['runs'][0]['crosses_window_boundary']=True
            if case=='overlap':
                w['candidates'][0]['runs'][1]['start']=2
                wr['candidates']['A']['runs']['A-2']['start']=2
            if case=='unrated':wr['candidates']['B']['runs']={}
            if case=='bad_original':wr['candidates']['B']['runs']['B-1']['original_text']='tampered'
            if case=='missing_unclear':wr['candidates']['B']['missing_speech']=[{'id':'missing','start':8,'end':9,'text':'word','text_certainty':'unclear'}]
            result=compare_window(w,wr)
            self.assertEqual(result['state'],'pending',case)
            self.assertIsNone(result['winner'],case)

    def test_confirmed_missing_speech_contributes_deletion_against_same_reference(self):
        w,wr=comparison_fixture()
        b_run=w['candidates'][1]['runs'][0]
        b_review=wr['candidates']['B']['runs']['B-1']
        b_run['text']=b_review['fixed_text']
        b_review['original_text']=b_run['text'];b_review['verdict']='exact'
        for cid in ('A','B'):
            wr['candidates'][cid]['missing_speech']=[{'id':'missing-'+cid,'start':8,'end':9,'text':'forgot','text_certainty':'confirmed'}]
        result=compare_window(w,wr)
        self.assertEqual(result['state'],'ready')
        self.assertEqual(result['by_candidate']['A']['D'],1)
        self.assertEqual(result['by_candidate']['A']['N'],6)
        self.assertEqual(result['by_candidate']['B']['D'],1)

    def test_error_rate_can_exceed_one_no_clamp(self):
        result=word_levenshtein(['a'],['a','b','c','d'])
        self.assertEqual(result,{'S':0,'D':0,'I':3,'errors':3,'N':1,'word_error_rate':3})
        self.assertIsNone(word_levenshtein([],[])['word_error_rate'])

    def test_normalization_preserves_arabic_and_malformed_evidence(self):
        self.assertEqual(comparison_tokens('ANA, ma- ma... ma… أَنا أنا إنا 3adi uh uh'),
                         ['ana','ma-','ma...','ma…','أَنا','أنا','إنا','3adi','uh','uh'])

    def test_subset_exposes_exclusions_and_has_no_full_accuracy(self):
        w,wr=comparison_fixture();other=copy.deepcopy(w);other['id']='unreviewed'
        result=summarize_comparison([w,other],{'windows':{'paired':wr}})
        self.assertEqual(result['included_window_ids'],['paired'])
        self.assertEqual(result['excluded_windows'][0]['window_id'],'unreviewed')
        self.assertEqual(result['by_source_kind']['separate_tracks']['N'],5)
        self.assertEqual(result['lower_error_source_on_reviewed_subset'],'separate_tracks')
        self.assertFalse(result['complete_review_set'])
        blocked=summarize_comparison([w],{'windows':{'paired':wr}},reviewer_conflict=True)
        self.assertEqual(blocked['included_window_ids'],[])
        self.assertIsNone(blocked['lower_error_source_on_reviewed_subset'])
        self.assertIsNone(blocked['by_source_kind']['separate_tracks']['word_error_rate'])

    def test_javascript_python_comparison_parity_and_readonly(self):
        w,wr=comparison_fixture()
        variants=[]
        for case in ('ready','disagreement','abstention','boundary','overlap','missing','partial','no_review'):
            a,b=copy.deepcopy(w),copy.deepcopy(wr)
            if case=='disagreement':b['candidates']['B']['runs']['B-1']['fixed_text']='totally different'
            if case=='abstention':b['candidates']['B']['runs']['B-1'].update(verdict='cant_tell',text_certainty='unclear')
            if case=='boundary':a['candidates'][0]['runs'][0]['crosses_window_boundary']=True
            if case=='overlap':a['candidates'][0]['runs'][1]['start']=2;b['candidates']['A']['runs']['A-2']['start']=2
            if case=='missing':
                for cid in ('A','B'):b['candidates'][cid]['missing_speech']=[{'id':'missing-'+cid,'start':8,'end':9,'text':'lost','text_certainty':'confirmed'}]
            if case=='partial':b['candidates']['B']['runs']={}
            if case=='no_review':b=None
            variants.append({'window':a,'record':b})
        node_code="const fs=require('fs'),api=require('./review_comparison.js');const data=JSON.parse(fs.readFileSync(0,'utf8'));const before=JSON.stringify(data);const comparisons=data.map(x=>api.compareWindow(x.window,x.record));const summaries=data.map(x=>api.summarize([x.window],{windows:x.record?{[x.window.id]:x.record}:{}}));const conflict=api.summarize([data[0].window],{windows:{paired:data[0].record}},{reviewerConflict:true});if(JSON.stringify(data)!==before)throw Error('input mutated');process.stdout.write(JSON.stringify({comparisons,summaries,conflict,tokens:api.tokenize('ANA, ma- ma... ma… أَنا أنا إنا 3adi uh uh'),edit:api.levenshtein(['a'],['a','b','c','d'])}));"
        completed=subprocess.run(['node','-e',node_code],input=json.dumps(variants,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,check=True,cwd=Path(__file__).parent)
        actual=json.loads(completed.stdout)
        self.assertEqual(actual['comparisons'],[compare_window(x['window'],x['record']) for x in variants])
        self.assertEqual(actual['summaries'],[summarize_comparison([x['window']],{'windows':{x['window']['id']:x['record']} if x['record'] else {}}) for x in variants])
        self.assertEqual(actual['conflict'],summarize_comparison([w],{'windows':{'paired':wr}},reviewer_conflict=True))
        self.assertEqual(actual['tokens'],comparison_tokens('ANA, ma- ma... ma… أَنا أنا إنا 3adi uh uh'))
        self.assertEqual(actual['edit'],word_levenshtein(['a'],['a','b','c','d']))

    def test_no_human_data_is_pending_not_zero_accuracy(self):
        s,g=score(fixture(),[])
        self.assertIsNone(s['accuracy'])
        self.assertEqual(s['human_reference_status'],'pending_human_review')
        self.assertEqual(g['eligible_assertion_count'],0)
        m=s['reviewers']['Medi']['metrics']['by_source_kind']['separate_tracks']
        self.assertIsNone(m['exact_rate_among_judged_speech_runs'])
        self.assertEqual(m['speech_runs_unjudged'],4)
        self.assertEqual(m['event_runs_total'],2)
        self.assertIsNone(m['unsupported_insertions_sum'])
        self.assertIsNone(m['metrics']['recall_utterance_preserved']['yes_rate_among_decidable'])

    def test_randomized_letters_map_to_source_not_letter(self):
        d=fixture(); p=export(d)
        answer(d,p,cid='A')
        answer(d,p,wid='w2',cid='B',verdict='wrong',text='ana uh mu-')
        s,g=score(d,[p]); m=s['reviewers']['Medi']['metrics']['by_source_kind']
        self.assertEqual(m['separate_tracks']['speech_verdicts'],{'exact':1,'wrong':1})
        self.assertEqual(m['mixed_recording']['speech_runs_judged'],0)
        self.assertEqual(m['separate_tracks']['wrong_rate_among_judged_speech_runs'],.5)
        self.assertEqual(m['separate_tracks']['speech_run_coverage'],.5)
        self.assertEqual(m['separate_tracks']['acceptance_status'],'pending_partial_or_no_human_review')
        self.assertEqual(g['eligible_assertion_count'],2)
        self.assertFalse(g['adjudicated'])

    def test_only_medi_attempt_metric_counts_and_blank_not_zero(self):
        d=fixture(); p=export(d,'Amal')
        p['reviewers']['Amal']['windows']['w1']['candidates']['A']['metrics']={'learner_attempt_preserved':'yes','speaker_correct':'uncertain','unsupported_insertions':0}
        s,_=score(d,[p]); m=s['reviewers']['Amal']['metrics']['by_source_kind']['separate_tracks']
        self.assertEqual(m['metrics']['learner_attempt_preserved']['answered_windows'],0)
        self.assertIsNone(m['metrics']['speaker_correct']['yes_rate_among_decidable'])
        self.assertEqual(m['unsupported_insertions_sum'],0)
        self.assertEqual(m['unsupported_windows_counted'],1)
        self.assertEqual(m['unsupported_audio_seconds_counted'],25)

    def test_reference_requires_confirmation_and_own_attempt_flag(self):
        d=fixture(); p=export(d)
        rr=answer(d,p,certainty='unclear')
        s,g=score(d,[p]); self.assertEqual(g['eligible_assertion_count'],0)
        rr['text_certainty']='confirmed'; rr['deliberate_error']=None
        _,g=score(d,[p]); self.assertEqual(g['eligible_assertion_count'],0)
        rr['deliberate_error']='no'; rr['fixed_text']='[unclear]'; rr['verdict']='wrong'
        _,g=score(d,[p]); self.assertEqual(g['eligible_assertion_count'],0)
        rr['fixed_text']=''
        _,g=score(d,[p]); self.assertEqual(g['eligible_assertion_count'],0)
        rr['fixed_text']=rr['original_text']
        _,g=score(d,[p]); self.assertEqual(g['eligible_assertion_count'],0)

    def test_medi_cannot_supply_arabic_authority(self):
        d=fixture(); p=export(d)
        answer(d,p,verdict='minor',text='أنا')
        _,g=score(d,[p]); self.assertEqual(g['eligible_assertion_count'],0)
        self.assertIn('Arabic_wording_requires_Amal',g['assertions'][0]['ineligibility_reasons'])
        amal=export(d,'Amal');answer(d,amal,role='Amal',rid='w1-A-r2',deliberate=None)
        _,g=score(d,[amal]); self.assertEqual(g['eligible_assertion_count'],1)

    def test_two_candidates_never_become_consensus(self):
        d=fixture();p=export(d)
        answer(d,p,cid='A');answer(d,p,cid='B')
        _,g=score(d,[p])
        self.assertEqual(len(g['assertions']),2)
        self.assertEqual(g['adjudicated_gold_count'],0)

    def test_missing_speech_is_separate_not_added_to_run_denominator(self):
        d=fixture();p=export(d)
        p['reviewers']['Medi']['windows']['w1']['candidates']['A']['missing_speech']=[{'id':'missing-x','speaker':'Medi','start':10,'end':12,'text':'forgot','text_certainty':'confirmed'}]
        s,g=score(d,[p]);m=s['reviewers']['Medi']['metrics']['by_source_kind']['separate_tracks']
        self.assertEqual(m['missing_entries_confirmed_nonblank'],1)
        self.assertIsNone(m['wrong_or_missing_rate'])
        self.assertEqual(m['speech_runs_judged'],0)
        self.assertEqual(g['eligible_assertion_count'],0)
        self.assertFalse(g['missing_speech_annotations'][0]['eligible_candidate_reference'])

    def test_recall_metric_only_explicit_annotation_in_recall_windows(self):
        d=fixture();p=export(d)
        p['reviewers']['Medi']['windows']['w1']['candidates']['A']['metrics']['recall_utterance_preserved']='yes'
        p['reviewers']['Medi']['windows']['w2']['candidates']['B']['metrics']['recall_utterance_preserved']='no'
        s,_=score(d,[p]);m=s['reviewers']['Medi']['metrics']['by_source_kind']['separate_tracks']['metrics']['recall_utterance_preserved']
        self.assertEqual(m['counts'],{'yes':1})
        self.assertEqual(m['expected_windows'],1)

    def test_duplicate_snapshot_deduplicated_different_snapshot_retained(self):
        d=fixture();p=export(d);answer(d,p)
        s,g=score(d,[p,p]);self.assertEqual(s['reviewers']['Medi']['snapshot_count'],1)
        self.assertEqual(len(g['assertions']),1)
        q=copy.deepcopy(p);answer(d,q,verdict='minor',text='ana um ma-')
        s,g=score(d,[p,q]);self.assertEqual(s['reviewers']['Medi']['snapshot_count'],2)
        self.assertIsNone(s['reviewers']['Medi']['metrics'])
        self.assertEqual(len(g['assertions']),2)
        self.assertEqual(len(s['conflicts']),2)
        self.assertEqual(g['eligible_assertion_count'],0)

    def test_arabic_reviewers_disagree_retained(self):
        d=fixture();p=export(d);q=export(d,'Amal')
        answer(d,p);answer(d,q,role='Amal',verdict='minor',text='انا ام ما')
        s,g=score(d,[p,q]);self.assertTrue(s['conflicts'])
        self.assertEqual(len(g['assertions']),2)
        self.assertFalse(g['adjudicated'])
        self.assertEqual(g['eligible_assertion_count'],0)

    def test_reject_manifest_ids_and_original_text(self):
        d=fixture();p=export(d);answer(d,p)
        for mutate in [lambda q:q.update(manifest_sha256='b'*64),
                       lambda q:q['reviewers'].update(Bot=q['reviewers']['Medi']),
                       lambda q:q['reviewers']['Medi']['windows'].update(unknown=q['reviewers']['Medi']['windows']['w1']),
                       lambda q:q['reviewers']['Medi']['windows']['w1']['candidates'].update(C={}),
                       lambda q:q['reviewers']['Medi']['windows']['w1']['candidates']['A']['runs']['w1-A-r1'].update(original_text='edited'),
                       lambda q:q['reviewers']['Medi']['windows']['w1']['candidates']['A']['runs']['w1-A-r1'].update(start=2),
                       lambda q:q['reviewers']['Medi']['windows']['w1']['candidates']['A']['runs']['w1-A-r1'].update(fixed_text='changed')]:
            q=copy.deepcopy(p);mutate(q)
            with self.assertRaises(ValueError):score(d,[q])

    def test_reject_negative_bool_nan_and_fractional_counts(self):
        d=fixture();p=export(d)
        for value in (-1, True, float('nan'), .5):
            q=copy.deepcopy(p);q['reviewers']['Medi']['windows']['w1']['candidates']['A']['metrics']['unsupported_insertions']=value
            with self.assertRaises(ValueError):score(d,[q])
        p['reviewers']['Medi']['active_seconds']=-1
        with self.assertRaises(ValueError):score(d,[p])

    def test_unknown_metric_rejected_not_silently_ignored(self):
        d=fixture();p=export(d);p['reviewers']['Medi']['windows']['w1']['candidates']['A']['metrics']['made_up_accuracy']=100
        with self.assertRaises(ValueError):score(d,[p])

    def test_event_and_boundary_runs_not_reference_gold(self):
        d=fixture();p=export(d,'Amal')
        answer(d,p,role='Amal',rid='w1-A-r3')
        d['windows'][0]['candidates'][0]['runs'][1]['crosses_window_boundary']=True
        answer(d,p,role='Amal',rid='w1-A-r2')
        _,g=score(d,[p]);self.assertEqual(g['eligible_assertion_count'],0)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.json';p.write_text('{"x":1,"x":2}',encoding='utf-8')
            with self.assertRaises(ValueError):load(p)

    def test_builder_preserves_overlapping_prior_event_and_warns(self):
        items=[{'id':'s:0','start':5,'end':18,'type':'audio_event','text':'[laughs]','speaker':'Amal','speaker_basis':'track'},
               {'id':'s:1','start':6,'end':9,'type':'word','text':'before','speaker':'Amal','speaker_basis':'track'},
               {'id':'s:2','start':7,'end':14,'type':'word','text':'long','speaker':'Amal','speaker_basis':'track'},
               {'id':'s:3','start':10,'end':10,'type':'spacing','text':' ','speaker':'Amal','speaker_basis':'track'},
               {'id':'s:4','start':12,'end':13,'type':'word','text':'inside','speaker':'Medi','speaker_basis':'track'}]
        runs=window_runs(items,10,20,'test')
        self.assertEqual([r['text'] for r in runs],['[laughs]','long','inside'])
        self.assertTrue(runs[0]['carry_in'])
        self.assertTrue(runs[1]['crosses_window_boundary'])
        self.assertIn('cannot confirm',runs[0]['timing_warning_text'])
        self.assertFalse(runs[2]['carry_in'])

    def test_cant_tell_keeps_unverified_draft_and_cannot_be_gold(self):
        for certainty in (None, 'unclear'):
            d=fixture();p=export(d)
            answer(d,p,verdict='cant_tell',text='possible ma- sound',certainty=certainty)
            before=copy.deepcopy(p)
            s,g=score(d,[p])
            self.assertEqual(p,before, 'Scoring must not rewrite the review export')
            self.assertEqual(g['eligible_assertion_count'],0)
            self.assertEqual(g['assertions'][0]['fixed_text'],'possible ma- sound')
            self.assertEqual(g['assertions'][0]['text_certainty'],certainty)
            self.assertIn('reviewer_cannot_determine_wording',g['assertions'][0]['ineligibility_reasons'])
            m=s['reviewers']['Medi']['metrics']['by_source_kind']['separate_tracks']
            self.assertEqual(m['speech_runs_abstained'],1)
            self.assertEqual(m['speech_runs_judged'],0)
            self.assertEqual(m['speech_runs_responded'],1)
            self.assertEqual(m['speech_runs_unanswered'],3)
            self.assertIsNone(m['exact_rate_among_judged_speech_runs'])
            self.assertIsNone(m['wrong_rate_among_judged_speech_runs'])

    def test_cant_tell_confirmed_contradiction_rejected(self):
        d=fixture();p=export(d)
        answer(d,p,verdict='cant_tell',certainty='confirmed')
        with self.assertRaisesRegex(ValueError, "Can't tell cannot confirm"):
            score(d,[p])

    def test_cant_tell_not_in_mixed_verdict_denominator(self):
        d=fixture();p=export(d,'Amal')
        answer(d,p,role='Amal',cid='A',rid='w1-A-r1',verdict='exact')
        answer(d,p,role='Amal',cid='A',rid='w1-A-r2',verdict='wrong',text='أنا مش مبسوطة')
        answer(d,p,role='Amal',wid='w2',cid='B',rid='w2-B-r1',verdict='cant_tell',certainty='unclear')
        answer(d,p,role='Amal',wid='w2',cid='B',rid='w2-B-r3',verdict='cant_tell',certainty='unclear')
        s,g=score(d,[p]);m=s['reviewers']['Amal']['metrics']['by_source_kind']['separate_tracks']
        self.assertEqual(m['speech_verdicts'],{'exact':1,'wrong':1})
        self.assertEqual(m['event_verdicts'],{})
        self.assertEqual(m['speech_runs_abstained'],1)
        self.assertEqual(m['event_runs_abstained'],1)
        self.assertEqual(m['speech_runs_judged'],2)
        self.assertEqual(m['speech_runs_responded'],3)
        self.assertEqual(m['exact_rate_among_judged_speech_runs'],.5)
        self.assertEqual(m['wrong_rate_among_judged_speech_runs'],.5)
        self.assertEqual(m['speech_run_coverage'],.5)
        self.assertEqual(m['speech_response_coverage'],.75)
        self.assertEqual(g['eligible_assertion_count'],2)

    def test_full_cant_tell_response_is_not_a_full_judgment(self):
        d=fixture();p=export(d)
        for w in d['windows']:
            p['reviewers']['Medi']['windows'][w['id']]['status']='reviewed'
            for c in w['candidates']:
                answer(d,p,wid=w['id'],cid=c['id'],verdict='cant_tell',certainty='unclear')
        s,g=score(d,[p]);m=s['reviewers']['Medi']['metrics']['by_source_kind']['separate_tracks']
        self.assertTrue(m['full_focus_response'])
        self.assertFalse(m['full_focus_review'])
        self.assertEqual(m['focus_runs_abstained'],2)
        self.assertEqual(m['focus_response_coverage'],1)
        self.assertEqual(m['focus_run_coverage'],0)
        self.assertEqual(m['acceptance_status'],'pending_partial_or_no_human_review')
        self.assertEqual(g['eligible_assertion_count'],0)

    def test_legacy_exact_does_not_infer_confirmation(self):
        for certainty in (None, 'unclear'):
            d=fixture();p=export(d)
            answer(d,p,verdict='exact',certainty=certainty)
            before=copy.deepcopy(p)
            s,g=score(d,[p])
            self.assertEqual(p,before)
            self.assertEqual(g['assertions'][0]['text_certainty'],certainty)
            self.assertFalse(g['assertions'][0]['eligible_candidate_reference'])
            self.assertEqual(g['eligible_assertion_count'],0)
            m=s['reviewers']['Medi']['metrics']['by_source_kind']['separate_tracks']
            self.assertEqual(m['speech_runs_judged'],1)
            self.assertEqual(m['speech_runs_abstained'],0)


if __name__ == '__main__':
    unittest.main()
