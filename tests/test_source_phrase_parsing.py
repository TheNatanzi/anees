from pathlib import Path
import import_vocab as iv
from speaking_evidence import StrictMatcher


def test_internal_alternative_consonants_keep_whole_words():
    assert iv.arabizi_forms('Ana baq/2aatel') == ['Ana baqaatel', 'Ana ba2aatel']
    assert iv.arabizi_forms('Ana ba2/qul') == ['Ana ba2ul', 'Ana baqul']
    assert iv.arabizi_forms('Ana balte2/qi') == ['Ana balte2i', 'Ana balteqi']
    assert set(iv.arabizi_forms('Azraq/2 / Zarq/2a')) == {'Azraq','Azra2','Zarqa','Zar2a'}
    assert set(iv.arabizi_forms('mishtaaq/2/a la')) == {'mishtaaq la','mishtaa2 la','mishtaaqa la','mishtaa2a la'}


def test_document_pronoun_shorthand_replaces_suffix_without_orphan_fragments():
    assert iv.arabizi_forms('Allah ysallmek / ak') == ['Allah ysallmek','Allah ysallmak']
    assert iv.arabizi_forms('Shu ra2yak/ek?') == ['Shu ra2yak','Shu ra2yek']
    assert iv.arabizi_forms('Shu ra2yak/ek + verb (no b-)') == ['Shu ra2yak','Shu ra2yek']
    assert iv.arabizi_forms('Shu ra2yak/ek bi-/fi…?') == ['Shu ra2yak','Shu ra2yek']
    source=Path(__file__).resolve().parents[1]/'data/vocab/word_bank_source.md'
    words,_=iv.to_words(iv.parse_markdown(source.read_text(encoding='utf-8')))
    by={w['key']:w for w in words}
    assert 'Allah ysallmak' in by['alah isalmek']['aliases']
    assert 'Allah ysallmekak' not in by['alah isalmek']['aliases']
    assert 'Shu ra2yek' in by['shu ra2yak']['aliases']
    assert 'How about' in by['shu ra2yak']['english']
    assert not any(a.strip() in {'ek?', 'ek + verb (no b-)', 'ek bi-', 'fi…?'} for a in by['shu ra2yak']['aliases'])


def test_hot_weather_shared_tail_is_not_bare_weather_or_a_plural():
    row={'arabizi':'El-jaw / el-denia shoab','arabic':'الجو / الدنيا شوب','english':"It's hot",'plural':'','topic':'Travel and Weather','subtopic':'Travel and Weather','tab':'Travel and Weather','doc_order':1}
    words,_=iv.to_words([row]);w=words[0]
    assert w['key']=='aljaw'  # Keep stable source identity.
    assert w['arabizi']=='El-jaw shoab' and w['arabic']=='الجو شوب'
    assert w['arabic_plural']==''
    assert set(w['aliases'])=={'el-denia shoab','الدنيا شوب'}
    assert not StrictMatcher(words).match('الجو')


def test_wanted_keeps_shared_phrase_and_person_identities():
    source=Path(__file__).resolve().parents[1]/'data/vocab/word_bank_source.md'
    rows=iv.parse_markdown(source.read_text(encoding='utf-8'))
    words,_=iv.to_words(rows)
    wanted=[w for w in words if w['topic']=='Past Tense' and 'wanted' in w['english']]
    assert len(wanted)==8
    assert len({w['key'] for w in wanted})==8
    assert all('بد' in w['arabic'] for w in wanted)
    assert all(not w['arabic_plural'] for w in wanted)
    first=next(w for w in wanted if w['english']=='I wanted')
    assert first['key']=='kAn'  # Existing identity/history stays stable.
    assert first['arabizi']=='kaan biddi'
    assert first['arabic']=='كان بدي'
    assert 'kunet biddi' in first['aliases'] and 'كنت بدي' in first['aliases']
    assert not any(a.strip() in {'kaan','كان','kunet','كنت'} for w in wanted for a in w['aliases'])
    by={w['key']:w for w in words}
    assert by['ana ba2']['english']=='I fight'
    assert by['ana ba2~2']['english']=='I say / tell'
    assert by['ana balte2']['arabizi']=='Ana balte2i'
    assert 'ana balte2i' not in by
    assert by['huwe kAn']['english']=='He was'
    assert by['ra7']['english']=='Will'
    assert by['rA7']['english']=='He went'
    matcher=StrictMatcher(words)
    assert set(matcher.match('كان'))=={'huwe kAn'}
    assert set(matcher.match('كان بدي'))=={'kAn'}
    assert set(matcher.match('راح'))=={'ra7','rA7'}
    assert set(matcher.match('raa7'))=={'ra7','rA7'}
    assert by['mara']['english']=='Woman / Wife / Woman'
    assert by['mara~time']['english']=='One time'
    assert by['2arIb']['english']=='Close'
    assert by['2arIb~relative']['english']=='Relative'
    assert by['sA7eb']['english']=='Friend/boyfriend'
    assert by['sA7eb~owner']['english']=='Owner'
    assert by['salon']['english']=='Guest room'
    assert by['salon~hair-salon']['english']=='Hair Salon'
    assert 'Ana bazahheq' in by['ana bazahe2']['aliases']
    assert set(matcher.match('قريب'))=={'2arIb','2arIb~relative'}
