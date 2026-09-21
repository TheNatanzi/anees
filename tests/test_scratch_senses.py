import import_vocab as V
import speaking_evidence as S

def test_doubling_lost_in_loose_key_does_not_merge_talk_and_scratch():
    def row(form,meaning):
        return dict(arabizi=form,arabic='أنا حكيت',english=meaning,plural='',topic='Past Tense',subtopic='Past Tense',tab='Past Tense',doc_order=1)
    words,_=V.to_words([row('Ana 7akait','I talked'),row('Ana 7akkait','I scratched')])
    assert {w['key'] for w in words}=={'ana 7akait','ana 7akait~scratch'}
    matcher=S.StrictMatcher(words)
    assert set(matcher.match('أنا حكيت'))=={'ana 7akait','ana 7akait~scratch'}
    assert set(matcher.match('Ana 7akkait'))=={'ana 7akait~scratch'}
