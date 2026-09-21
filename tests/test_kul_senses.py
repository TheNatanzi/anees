import import_vocab as iv
import speaking_evidence as se


def test_source_quantifier_and_eat_imperative_do_not_merge():
    def row(topic, text, meaning):
        return dict(topic=topic, subtopic=topic, tab=topic, doc_order=1,
                    arabizi=text, arabic='كل', english=meaning, plural='')
    words, _ = iv.to_words([row('Quantity / Degree', 'Kul', 'All / Every'),
                           row('Command Tense', 'Kul / kuli / kulu', 'Eat')])
    assert {w['key'] for w in words} == {'kul', 'kul~eat'}
    assert all(w['match_loose'] == 'kul' for w in words)
    matcher = se.StrictMatcher(words)
    match = matcher.match('كل')
    assert set(match) == {'kul', 'kul~eat'}
    assert se.contextual_match(match, 'إشي') == {'kul': 'context_quantifier'}
    assert se.contextual_match(match, 'يوم') == {'kul': 'context_quantifier'}
    assert se.contextual_match(match, '') == match
    assert se.contextual_match(match, 'رز') == match  # Food alone is not decisive.
    assert matcher.match('kuli') == {'kul~eat': 'approved_alias'}
