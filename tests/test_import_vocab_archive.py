# -*- coding: utf-8 -*-
"""AM-12 (Medi 2026-09-30: "She took a few verbs off the list that was added by mistake"): every Doc sync archives the
words Amal removed - active:false, never a DELETE, history kept - and only a live Doc read may sync (the saved snapshot
never writes the table). Fake Doc snapshot + fake database: no network, no real Supabase writes."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import import_vocab as IV

DOC = """# Latest Topic

## Lesson words

|  |  |  |  |
| :-: | :-: | :-: | :-: |
| **Transliteration** | **Plural** | **Arabic** | **English** |
| Shanta | shanaat | شنطة | Bag |
| Ahel | — | أهل | Family |
| Mumtaaz | — | ممتاز | Excellent |
""" + "".join(f"| Raqam{i} | — | رقم{'ا' * i} | Number {i} |\n" for i in range(1, 9))   # 8 filler rows (the 80% floor)


class FakeDb:
    def __init__(self, rows):
        self.rows = {r["key"]: dict(r) for r in rows}
        self.calls = []

    def select(self, table, params=None, **kw):
        self.calls.append(("GET", table))
        return [{"key": k, "row_hash": r.get("row_hash"), "active": r["active"]} for k, r in self.rows.items()]

    def upsert(self, table, rows, on="", **kw):
        self.calls.append(("UPSERT", table, [r["key"] for r in rows]))
        for r in rows:
            self.rows.setdefault(r["key"], {"first_seen": "now", "history": []}).update(r)

    def rest(self, method, table, params=None, body=None, **kw):
        self.calls.append((method, table, params, body))
        assert method == "PATCH", "a sync never deletes a word row"
        self.rows[params["key"][3:]].update(body)


def _words(doc=DOC):
    words, _ = IV.to_words(IV.parse_markdown(doc))
    return words


def test_AM_12_a_word_amal_removed_is_archived_with_its_history_kept():
    first = _words()
    keys = {w["key"]: w for w in first}
    assert len(keys) == 11
    fake = FakeDb([{**w, "active": True, "first_seen": "2026-09-05", "history": ["said 09-11"]} for w in first])
    removed_key = next(k for k, w in keys.items() if w["arabic"] == "أهل")
    after = _words(DOC.replace("| Ahel | — | أهل | Family |\n", ""))          # Amal took Ahel off her Doc
    res = IV.sync(after, db=fake, min_words=1, ages=[])
    assert res["archived"] == [removed_key] and res["deactivated"] == 1 and res["inserted"] == 0
    row = fake.rows[removed_key]
    assert row["active"] is False and row["history"] == ["said 09-11"] and row["first_seen"] == "2026-09-05"
    assert not any(c[0] == "DELETE" for c in fake.calls)
    assert all(fake.rows[k]["active"] for k in keys if k != removed_key)
    # she puts it back: the same row comes back active (same key, same history)
    res2 = IV.sync(_words(), db=fake, min_words=1, ages=[])
    assert res2["reactivated"] == [removed_key] and res2["archived"] == []
    assert fake.rows[removed_key]["active"] is True and fake.rows[removed_key]["history"] == ["said 09-11"]


def test_AM_12_dry_run_and_broken_fetch_write_nothing():
    fake = FakeDb([{**w, "active": True} for w in _words()])
    res = IV.sync(_words(DOC.replace("| Ahel | — | أهل | Family |\n", "")), db=fake, dry=True, min_words=1, ages=[])
    assert res["archived"] and all(c[0] == "GET" for c in fake.calls)
    try:
        IV.sync([], db=fake, min_words=1, ages=[])
        assert False, "an empty fetch must refuse"
    except RuntimeError:
        pass
    assert all(r["active"] for r in fake.rows.values())


def test_AM_12_only_a_live_doc_read_syncs_never_the_old_snapshot():
    snap = r"C:\dev\anees\data\vocab\doc_markdown_2026-09-23.md (snapshot; no live source configured)"
    assert not IV.live_source(snap, None)
    assert IV.live_source(r"C:\x\doc_export_now.html", r"C:\x\doc_export_now.html")
    assert IV.live_source("https://docs.google.com/document/d/e/xyz/pub", None)
    src = open(os.path.join(REPO, "scripts", "import_vocab.py"), encoding="utf-8").read()
    assert "if not live_source(label, a.file):" in src


def test_snapshot_fallback_writes_nothing(monkeypatch, tmp_path):
    """2026-10-02: the hourly import with no live source rebuilt the word list from the 09-04 snapshot every hour and wiped
    the 09-23 'Added from lessons' words (accuracy_gates off-by-ones on 09-23 / 09-30). Without a live read nothing is written."""
    snap = tmp_path / "doc_markdown_2026-09-04.md"
    snap.write_text("# x\n", encoding="utf-8")
    monkeypatch.setattr(IV, "VOCAB", tmp_path)
    monkeypatch.setattr(IV, "DOCS_DATA", tmp_path / "docs")
    monkeypatch.setattr(IV.E, "env", lambda k, *a, **kw: None)
    monkeypatch.setattr(sys, "argv", ["import_vocab.py"])
    IV.main()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["doc_markdown_2026-09-04.md"]
