"""M0 hardening: broken inputs never corrupt the words table."""
import pytest
import import_vocab as iv


def test_empty_doc_parses_to_nothing():
    assert iv.parse_markdown('') == []
    assert iv.parse_html('<html><body><p>oops</p></body></html>') == []
    words, merged = iv.to_words([])
    assert words == [] and merged == 0


def test_sync_refuses_a_broken_fetch(monkeypatch):
    """An empty or truncated Doc must raise, not deactivate 2,000 rows."""
    class FakeDb:
        def select(self, table, params=None):
            return [{'key': f'k{i}', 'row_hash': 'x', 'active': True} for i in range(2000)]
        def upsert(self, *a, **k): raise AssertionError('must not write')
        def rest(self, *a, **k): raise AssertionError('must not write')
    import sys
    monkeypatch.setitem(sys.modules, 'db', FakeDb())
    with pytest.raises(RuntimeError):
        iv.sync([])
    few = [{'key': f'k{i}', 'row_hash': 'x'} for i in range(1200)]
    with pytest.raises(RuntimeError):
        iv.sync(few)


def test_missing_source_is_loud(tmp_path, monkeypatch):
    monkeypatch.setattr(iv, 'VOCAB', tmp_path)
    monkeypatch.setattr(iv.E, 'env', lambda name, default=None: None)
    with pytest.raises(RuntimeError):
        iv.load_source(None)


def test_swapped_columns_are_repaired():
    rows = iv.parse_markdown('# T\n\n| **Transliteration** | **Arabic** | **English** |\n| أنا بسافر | Ana basaafer | I travel |\n')
    assert rows and rows[0]['arabizi'] == 'Ana basaafer' and rows[0]['arabic'] == 'أنا بسافر'


def test_headerless_table_by_content():
    rows = iv.parse_markdown('# T\n\n|  |  |  |\n| :-: | :-: | :-: |\n| Ana seret | أنا صرت | I became |\n')
    assert rows[0]['arabizi'] == 'Ana seret' and rows[0]['english'] == 'I became'
