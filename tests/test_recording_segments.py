from recall_bot import segment_filename
import pytest
from ingest_tracks import merge, validate_single_segment_tracks

def test_reconnect_recordings_have_unique_stable_safe_names():
    a={'participant':{'name':'Medi Natanzi','id':1},'start_timestamp':{'relative':1.2},'duration':60}
    b={**a,'start_timestamp':{'relative':120.5},'duration':3600}
    assert segment_filename(a,'recording')!=segment_filename(b,'recording')
    assert segment_filename(a,'recording')==segment_filename({**a,'download_url':'new-expiring-url'},'recording')
    bad={**a,'participant':{'name':'../../Amal','id':1}}
    assert '/' not in segment_filename(bad,'recording')
    assert '\\' not in segment_filename(bad,'recording')


def test_reconnects_cannot_duplicate_a_speaker_transcript_at_new_offsets():
    tracks=[{'participant':'Medi','file':'medi-first.mp3','start':{'relative':0},'duration_s':50},
            {'participant':'Medi','file':'medi-reconnect.mp3','start':{'relative':80},'duration_s':50}]
    with pytest.raises(ValueError,match='per-segment'):
        merge(tracks,{'Medi':{'words':[{'type':'word','text':'hello','start':1,'end':2}]}})
    with pytest.raises(ValueError,match='per-segment'):
        validate_single_segment_tracks([{**tracks[0],'participant':'Amal'},tracks[0]])


def test_distinct_single_tracks_preserve_person_and_offset():
    tracks=[{'participant':'Medi','file':'medi.mp3','start':{'relative':10},'duration_s':50},
            {'participant':'Amal','file':'amal.mp3','start':{'relative':20},'duration_s':50}]
    result=merge(tracks,{'Medi':{'words':[{'type':'word','text':'one','start':2,'end':3}]},
                         'Amal':{'words':[{'type':'word','text':'two','start':4,'end':5}]}})
    assert [(w['speaker_id'],w['start']) for w in result['words']]==[('Medi',12),('Amal',24)]
