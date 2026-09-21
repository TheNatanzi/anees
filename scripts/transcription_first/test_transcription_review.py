"""Synthetic regression cases; never human judgments or provider calls."""
import copy
import tempfile
import unittest
from pathlib import Path
from transcription_review import evidence_stream, window_runs, write_once, who, selection

class ReviewEvidenceTest(unittest.TestCase):
    def test_preserves_every_raw_item_and_provider_identity(self):
        original = {'words':[{'type':'word','text':'Uh-','start':1,'end':2,'speaker_id':'speaker_1'},
                              {'type':'spacing','text':' ','start':2,'end':2},
                              {'type':'audio_event','text':'[laughs]','start':2,'end':3}]}
        frozen = copy.deepcopy(original)
        items = evidence_stream(original,'Medi','Medi',.429)
        self.assertEqual(original,frozen)
        self.assertEqual(len(items),3)
        self.assertEqual(items[0]['provider_item']['speaker_id'],'speaker_1')
        self.assertEqual(items[0]['start'],1.429)
        self.assertEqual(items[0]['speaker_basis'],'participant_track_not_voice_verified')

    def test_fillers_are_not_silence_and_events_not_hidden(self):
        raw = {'words':[{'type':'word','text':'uh','start':1,'end':1.5},
                        {'type':'audio_event','text':'[laughs]','start':2,'end':9}]}
        runs = window_runs(evidence_stream(raw,'Medi','Medi'),0,10,'w')
        self.assertEqual(runs[0]['text'],'uh')
        self.assertTrue(runs[1]['events'])
        self.assertTrue(runs[1]['timing_warning'])
        self.assertNotIn('pause',runs[0]['text'])

    def test_gap_splits_normal_words(self):
        raw={'words':[{'type':'word','text':'one','start':1,'end':2},
                      {'type':'word','text':'two','start':5,'end':6}]}
        self.assertEqual(len(window_runs(evidence_stream(raw,'Medi','Medi'),0,10,'w')),2)

    def test_crossing_word_and_event_are_carried_with_warning(self):
        raw={'words':[{'type':'word','text':'hmm','start':1,'end':62},
                      {'type':'audio_event','text':'[laughs]','start':4,'end':12}]}
        runs=window_runs(evidence_stream(raw,'Amal','Amal'),10,20,'w')
        self.assertEqual(len(runs),2)
        self.assertTrue(all(r['carry_in'] and r['crosses_window_boundary'] for r in runs))

    def test_mixed_clusters_are_not_guessed_people(self):
        item=evidence_stream({'words':[{'type':'word','text':'hi','start':0,'end':1,'speaker_id':'speaker_0'}]},'mixed')[0]
        self.assertEqual(item['speaker'],'Unknown (speaker_0)')
        self.assertEqual(item['speaker_basis'],'model_cluster_unverified')
        with self.assertRaises(ValueError):
            who({'participant':'Unregistered guest'})

    def test_no_overwrite_frozen_data(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.json'
            write_once(p,{'a':1}); write_once(p,{'a':1})
            with self.assertRaises(ValueError):write_once(p,{'a':2})

    def test_twenty_deterministic_nonoverlapping_windows(self):
        items=[{'type':'word','text':'كلمة','start':float(i)} for i in range(0,3750)]
        windows,pool=selection(items)
        self.assertEqual(windows,selection(items)[0])
        self.assertEqual(len(windows),20)
        self.assertEqual(len({w['id'] for w in windows}),20)
        for i,a in enumerate(windows):
            self.assertEqual(a['end']-a['start'],25)
            for b in windows[i+1:]:self.assertFalse(a['start']<b['end'] and b['start']<a['end'])

if __name__=='__main__':unittest.main()
