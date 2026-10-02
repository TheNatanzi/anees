"""RULES S6 (Medi 2026-10-02): a past form said without its pronoun counts for that verb's Past.
حكيت alone = "I spoke" or "you spoke": same verb and tense, one key kept. Guards: he-forms (درس, رسم), forms Amal
also has as a noun/adjective/phrase, a different sense (~scratch), and lists without topics are never matched bare."""
import speaking_evidence as se

W = [{'key': 'ana 7akait', 'arabic': 'أنا حكيت', 'topic': 'Past Tense'},
     {'key': 'inta 7akait', 'arabic': 'إنت حكيت', 'topic': 'Past Tense'},
     {'key': 'i7na 7akaina', 'arabic': 'إحنا حكينا', 'topic': 'Past Tense'},
     {'key': 'ana 2deret', 'arabic': 'أنا قدرت', 'topic': 'Past Tense'},
     {'key': 'huwe daras', 'arabic': 'هو درس', 'topic': 'Past Tense'},
     {'key': 'ana le3bet', 'arabic': 'أنا لعبت', 'topic': 'Past Tense'},
     {'key': 'le3bet', 'arabic': 'لعبت', 'topic': 'Random Nouns'},
     {'key': 'ana bashrab', 'arabic': 'أنا بشرب', 'topic': 'Verbs List'}]


def test_bare_past_matches_and_person_stays_open():
    m = se.StrictMatcher(W)
    assert m.match('قدرت') == {'ana 2deret': 'pronoun_omission'}
    assert m.match('حكيت') == {'ana 7akait': 'pronoun_omission_person_open'}
    assert m.match('حكينا') == {'i7na 7akaina': 'pronoun_omission'}
    assert m.match('أنا حكيت') == {'ana 7akait': 'arabic_exact'}          # the full form is unchanged


def test_guards():
    m = se.StrictMatcher(W)
    assert m.match('درس') == {}                                            # he-form: too often a noun
    assert m.match('لعبت') == {'le3bet': 'arabic_exact'}                   # her own non-verb row wins, no bare past
    scratch = se.StrictMatcher(W + [{'key': 'ana 7akait~scratch', 'arabic': 'أنا حكيت', 'topic': 'Past Tense'}])
    assert len(scratch.match('حكيت')) > 1                                  # a different sense stays ambiguous
    no_topic = se.StrictMatcher([{k: v for k, v in w.items() if k != 'topic'} for w in W])
    assert no_topic.match('قدرت') == {}
