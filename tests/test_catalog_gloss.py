from build_word_bank_catalog import gloss
from pathlib import Path
import json,subprocess,sys


def test_base_verbs_ending_ed_are_not_mistaken_for_past_suffixes():
    assert gloss('I need') == gloss('I needed') == {'need'}
    assert gloss('I feed') == gloss('I fed') == {'feed'}
    assert gloss('I proceed') == gloss('I proceeded') == {'proceed'}
    assert gloss('I help') == gloss('I helped') == {'help'}


def test_documented_alternatives_irregulars_and_prose_fill_only_supported_forms(tmp_path):
    root=Path(__file__).resolve().parents[1];out=tmp_path/'catalog.json'
    subprocess.run([sys.executable,str(root/'scripts/build_word_bank_catalog.py'),'--document',str(root/'data/vocab/word_bank_source.md'),'--output',str(out)],check=True,capture_output=True)
    groups={g['id']:g for g in json.loads(out.read_text(encoding='utf-8'))['groups']}
    entries={e['id']:e for g in groups.values() for e in g['entries']}
    expected={'ana ba23ud:command':'E3od','ana bAji:command':'Ta3aal','ana basta5dem:past':'sta3malet','ana basta5dem:command':'ista5dem','ana basA3ed:past':'saa3adet','ana bason:past':'zannait','ana bason:command':'Zonn','ana balte2:past':'lta2ayt'}
    for entry,word in expected.items():
        assert entries[entry]['word']==word
        assert entries[entry]['provenance']=='document'
    assert len(entries['ana basta5dem:command']['persons'])==1  # No invented gender variants.
    assert 'source_note' in entries['ana basA3ed:past']['persons'][0]
    assert 'akalet' in entries['ana bakul:past']['keys']
    assert 'shrebet' in entries['ana bashrab:past']['keys']
    assert 'basawer' in entries['ana basawer:present']['keys']
    assert entries['ana banbese6:command']['keys']==['enbese6']
    assert [p['word'] for p in entries['ana banbese6:command']['persons']]==['Enbese6','Enbes6i','Enbes6u']
    assert 'byebse6' in entries['ana babse6:present']['keys']
    assert 'kul' not in groups['ana bakul']['keys']  # All/every is not command eat.
    for entry in ['ana basawi:past','ana babda:past','ana balef:past','ana ba7dar:command','ana bat7arak:past']:
        assert not entries[entry]['word']  # An English synonym alone is insufficient.
    owners={}
    for g in groups.values():
        for key in g['keys']:
            assert key not in owners or owners[key]==g['id']
            owners[key]=g['id']
