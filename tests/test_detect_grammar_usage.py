

def test_gr_40_d2_reads_the_tutors_uploaded_collocation_sets(tmp_path):
    """The tutor 2026-10-18: 'update the verb plus preposition collocation list to include all the verbs' (her upload
    'All verb Collocations'): a card of a set whose title names collocations adds its verb + preposition to D2."""
    import json as _j
    import detect_grammar_usage as D
    (tmp_path / "docs" / "data").mkdir(parents=True)
    (tmp_path / "data" / "vocab").mkdir(parents=True)
    (tmp_path / "docs" / "data" / "uploads.json").write_text(_j.dumps({"sets": [
        {"title": "All verb Collocations", "cards": [{"arabizi": "Ana bastanna 3ala", "arabic": "أنا بستنى على I wait on"},
                                                     {"arabizi": "أنا بحلم في I dream of", "arabic": "", "english": "Ana ba7lam fi"}]},
        {"title": "Body parts", "cards": [{"arabizi": "Ana ba7ki ma3", "arabic": "أنا بحكي مع"}]}]}, ensure_ascii=False), encoding="utf-8")
    v = D.verb_preps(repo=str(tmp_path))
    assert v.get(D._vstem("أنا بستنى")) == {"3ala"} and v.get(D._vstem("أنا بحلم")) == {"fi"}
    assert D._vstem("أنا بحكي") not in v                     # a set that is not a collocation list adds nothing
