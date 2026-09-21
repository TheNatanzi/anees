import speaking_evidence as se

def event(key,text,sentence):
    return {'id':key,'speaker':'Medi','word_key':key,'text':text,'spoken':True,'t_start':10,'t_end':11,'row_id':'r',
            'context':[{'row_id':'r','speaker':'Medi','text':sentence,'timeline_start':9,'timeline_end':11}]}

def test_arabizi_connected_sentence_is_not_isolated():
    e=event('safra','safra','intikharabti il safra.')
    assert se.assess([e])[0]['assessment']=='independent'

def test_meaning_request_targets_word_not_question_wrapper():
    smell=event('rI7a','ريحة؟','شو يعني ريحة؟')
    question=event('shu','شو','شو يعني ريحة؟')
    assert se.assess([smell,question])[0]['assessment']=='incorrect'
    assert question['ignored'] is True

def test_clarification_request_is_unscored():
    e=event('shu','شو؟','uh، شو؟')
    assert se.assess([e])[0]['ignored'] is True
