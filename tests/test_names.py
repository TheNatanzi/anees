# -*- coding: utf-8 -*-
"""Names & places layer (scripts/names.py, docs/data/names.json; Medi 2026-09-28: "yes").
His example (Sep 21 65:27): Amal's "Bass ma, ma bazonn fih Irani. yemken fih رام Allah, Bass Bait La7em, la." - Ramallah and
Bethlehem must be ONE place each (not house + meat, not "Allah"), Irani stays her word, people are fingerprints only."""
import io, json, re, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import names  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = json.load(io.open(ROOT / "docs" / "data" / "names.json", encoding="utf-8"))
NM = names.Names(DATA)
FIXTURE = ROOT / "tests" / "fixtures" / "names_parity.json"


def spans(text):
    return [(s["text"], s["kind"], s.get("id")) for s in NM.find(text)]


def test_medi_example_places_are_one_token_each():
    arabizi = "Bass ma, ma bazonn fih Irani. yemken fih رام Allah, Bass Bait La7em, la."
    assert spans(arabizi) == [("رام Allah", "place", "ramallah"), ("Bait La7em", "place", "bethlehem")]
    assert NM.find(arabizi)[0]["mixed"] is True                     # the engine's cross-script split, repaired
    recorded = "آه، بس ما، ما بظن فيه إيراني. يمكن فيه رام الله، بس بيت لحم، لا."
    assert spans(recorded) == [("رام الله", "place", "ramallah"), ("بيت لحم", "place", "bethlehem")]
    for v, want in (("Ramallah", "ramallah"), ("Ram Allah", "ramallah"), ("رامالله", "ramallah"), ("Bait Lahem", "bethlehem"),
                    ("بيتلحم", "bethlehem"), ("Beit La7em", "bethlehem")):
        assert [x[2] for x in spans("fi " + v + " kaman")] == [want], v


def test_seed_levant_places_and_prefixes():
    for text, want in [("il-Quds", "jerusalem"), ("بالقدس", "jerusalem"), ("للقدس", "jerusalem"), ("عالقدس", "jerusalem"),
                       ("برام الله", "ramallah"), ("Nablus", "nablus"), ("حيفا", "haifa"), ("Yafa", "jaffa"), ("غزة", "gaza"),
                       ("جنين", "jenin"), ("il-Khalil", "hebron"), ("عكا", "akka"), ("الناصرة", "nazareth"), ("Tulkarem", "tulkarem"),
                       ("قلقيلية", "qalqilya"), ("أريحا", "jericho"), ("Amman", "amman"), ("بيروت", "beirut"), ("ish-Sham", "damascus"),
                       ("القاهرة", "cairo")]:
        got = spans(text)
        assert got and got[0][2] == want, (text, got)
    assert spans("il-Quds")[0][0] == "il-Quds"                      # the joined article belongs to the name
    assert spans("bil-Quds")[0][0] == "Quds"                        # a preposition does not


def test_countries_nationalities_and_decision_3_vocab():
    vocab = {v["word_key"] for v in DATA["vocab"]}
    assert {"irani", "amriki"} <= vocab                             # on Amal's list: stays vocab, scored normally
    assert spans("fih Irani") == [] and spans("إيراني") == []
    assert spans("إيران") == [("إيران", "country", "c-ir")] and spans("Iran")[0][2] == "c-ir"
    assert spans("فلسطيني")[0][1] == "country"                      # a nationality not on her list is a name
    assert spans("UAE")[0][2] == "c-ae" and spans("uae") == []      # abbreviations only in capitals
    assert spans("Turkey")[0][2] == "c-tr" and spans("roast turkey") == []
    assert spans("صورة") == [] and spans("صور") == []               # pictures, never Tyre
    assert spans("المغرب") == []                                    # her word (sunset) wins; "Morocco" stays a name
    assert spans("Morocco")[0][2] == "c-ma"


def test_everyday_words_are_not_names():
    for text in ("كامل", "بابا", "مالي", "per", "hang", "Would you say أنا كامل نسيت", "ana bafadal amal, amalu illayli"):
        assert spans(text) == [], text


def test_people_are_fingerprints_only():
    raw = json.dumps(DATA, ensure_ascii=False)
    assert all(set(p) <= {"fp", "src"} and re.fullmatch(r"[0-9a-f]{32}", p["fp"]) for p in DATA["people"])
    people_text = json.dumps(DATA["people"], ensure_ascii=False)
    for name in ("Amal", "Medi", "Mahdi", "Mehdi", "أمل", "مهدي", "ميدي"):
        assert name not in people_text
    assert '"Mahdi"' not in raw and '"ميدي"' not in raw and '"مهدي"' not in raw
    assert DATA["salt"] == names.SALT
    assert spans("The apology came from Amal") == [("Amal", "person", None)]
    assert spans("يا مهدي") == [("مهدي", "person", None)]
    assert spans("لأمل") == [("أمل", "person", None)]
    assert spans("amal") == []                                      # lower-case Arabizi "amal" is a word (3amal), not her name
    assert names.fp("Amal") == names.fp(("amal",))


def test_names_json_licence_and_counts():
    st = DATA["stats"]
    assert "CC0" in DATA["licence"] and "Wikidata" in DATA["licence"]
    assert st["countries"] >= 190 and st["capitals"] >= 180 and st["cities"] >= 400 and st["places"] >= 50
    assert st["people_fingerprints"] >= 7


def test_keyterms_are_names_only_within_limits():
    amal, medi = NM.keyterms("amal"), NM.keyterms("medi")
    assert 0 < len(amal) <= 1000 and 0 < len(medi) <= 1000
    assert all(len(k) <= 50 for k in amal + medi)
    assert "رام الله" in amal and "Ramallah" in amal and "Bethlehem" in medi
    assert not any(re.search(r"[A-Za-z]\d|\d[A-Za-z]", k) for k in amal)    # no invented Arabizi (RULES S1)
    place_terms = {v for e in DATA["entries"] if e["kind"] == "place" for v in [e.get("ar"), e.get("en")] + e["v"] if v}
    place_terms |= {re.sub(r"^the ", "", re.sub(r"\s*\([^)]*\)", "", e.get("en") or "")) for e in DATA["entries"] if e["kind"] == "place"}
    assert not [k for k in medi if k not in place_terms]              # Medi's track: place names only
    words = json.load(io.open(ROOT / "docs" / "data" / "words.json", encoding="utf-8"))["items"]
    vocab_ar = {names.variant_key(p) for w in words for p in re.split(r"\s*/\s*", w.get("arabic") or "") if p.strip()}
    assert not [k for k in amal if names.is_ar(k) and names.variant_key(k) in vocab_ar]   # never a vocabulary word


def test_scribe_request_carries_name_keyterms(tmp_path, monkeypatch):
    import pipeline_ext as px
    monkeypatch.setattr(px, "LEDGER", tmp_path / "budget.json")
    sent = []

    class R:
        status_code, text = 200, ""
        def json(self): return {"words": [{"type": "word", "text": "x"}]}

    def post(url, headers, data, files, timeout):
        sent.append(data)
        return R()
    for who, mode in (("Amal", "all"), ("Medi", "places")):
        mp3 = tmp_path / f"{who}.mp3"; mp3.write_bytes(b"x")
        px.transcribe_with_retry(post, mp3, "k", minutes=1, who=who)
    a, m = sent
    assert a["model_id"] == "scribe_v2" and len(a["keyterms"]) == len(NM.keyterms("amal"))
    assert m["keyterms"] == NM.keyterms("medi")
    monkeypatch.setenv("ANEES_KEYTERMS_AMAL", "off")
    px.transcribe_with_retry(post, tmp_path / "Amal.mp3", "k", minutes=1, who="Amal")
    assert "keyterms" not in sent[-1]


def test_lesson_layer_and_glossary_sep_21():
    lay = names.layer("2026-09-21", NM, write=False)
    ids = {s.get("id") for s in lay["spans"]}
    assert {"ramallah", "bethlehem"} <= ids
    doc = json.load(io.open(ROOT / "docs" / "data" / "lessons" / "2026-09-21.json", encoding="utf-8"))
    for s in lay["spans"]:                                          # offsets point into the untouched transcript (S2)
        assert doc["turns"][s["i"]]["text"][s["s"]:s["e"]] == s["text"]
    g = names.glossary("2026-09-21", NM)
    assert "Ramallah (place)" in g and "Bethlehem (place)" in g and "never gloss them word by word" in g
    assert (ROOT / "docs" / "data" / "lesson-names" / "2026-09-21.json").exists()
    assert not list((ROOT / "docs" / "data" / "lessons").glob("*.names.json"))   # never inside the lessons glob


def test_review_prompts_carry_the_names_glossary():
    import review_lesson as rl
    for p in (rl.reader_prompt("2026-09-21", "r1"), rl.third_prompt("2026-09-21"), rl.pattern_prompt("2026-09-21"), rl.gaps_prompt("2026-09-21")):
        assert "Bethlehem (place)" in p
    assert "Names in this lesson" not in rl.gaps_prompt()


def test_sentence_ladder_counts_a_name_as_one_word_never_unknown():
    import build_sentence_ladder as L
    toks = L.tokenize("يمكن فيه رام الله، بس بيت لحم، لا.", L.bank())
    words = [t["w"] for t in toks if t["s"] == "ar"]
    assert "رام الله" in words and "بيت لحم" in words and "بيت" not in words and "لحم" not in words
    tags, out, rules = L.sentence_tags(toks, "يمكن فيه رام الله، بس بيت لحم، لا.", L.bank())
    nm = [t for t in out if t.get("nm")]
    assert [t["nm"] for t in nm] == ["place", "place"] and not any("k" in t or "ks" in t for t in nm)
    mixed = L.tokenize("yemken fih رام Allah, Bass Bait La7em, la.", L.bank())
    assert [t["w"] for t in mixed if t.get("nm")] == ["رام Allah", "Bait La7em"]
    assert L.count_words("صح، فيه صيني، صيني.", L.bank())[0] == 3   # a stutter of a name still counts once


def test_grammar_detector_ignores_names_and_nothing_else():
    import detect_grammar_usage as G
    assert G.mask_names("في رام الله")[0] == "في " + G.NAME_STANDIN
    assert G.word_rules([G.NAME_STANDIN]) == {}
    assert not any(re.search(p, G.NAME_STANDIN) for ps in G.P.values() for p in ps)
    plain = "بدي روح عالبيت بكرا"
    assert G.mask_names(plain) == (plain, [])
    assert G.unmask("في " + G.NAME_STANDIN, ["رام الله"]) == "في رام الله"


def test_possible_names_file_is_well_formed():
    d = json.load(io.open(ROOT / "docs" / "data" / "possible-names.json", encoding="utf-8"))
    assert d["items"] and all(re.fullmatch(r"[0-9a-f]{32}", x["cand"]) for x in d["items"])
    assert all(x["kind_guess"] in ("place", "person") and x["examples"] for x in d["items"])
    known = {k for e in DATA["entries"] for v in e["v"] + e.get("cap", []) for k in [names.variant_key(v)]}
    assert not [x for x in d["items"] if names.variant_key(x["text"]) in known]


def test_migration_021_is_anon_select_insert_and_person_private():
    sql = (ROOT / "supabase" / "migrations" / "021_name_labels.sql").read_text(encoding="utf-8")
    assert "for select to anon" in sql and "for insert to anon" in sql and "revoke update, delete" in sql
    assert "kind is distinct from 'person' or text is null" in sql


def test_parity_fixture_matches_python():
    """tests/test_names_parity.cjs runs docs/js/names.js on the same texts; both must equal this fixture."""
    fx = json.load(io.open(FIXTURE, encoding="utf-8"))
    for case in fx["cases"]:      # a names.json change that moves a span: re-check it, then python tests/test_names.py --fixture
        assert NM.find(case["text"]) == case["spans"], case["text"]
    for k, v in fx["fp"].items():
        assert names.fp(tuple(k.split(" "))) == v


def write_fixture():
    texts = ["Bass ma, ma bazonn fih Irani. yemken fih رام Allah, Bass Bait La7em, la.",
             "آه، بس ما، ما بظن فيه إيراني. يمكن فيه رام الله، بس بيت لحم، لا.",
             "bil-Quds w برام الله، il-Quds, b-il-Quds, Turkey turkey UAE uae", "لأمل وأمل كامل بابا مالي",
             "fi Ramallah w fi Bait-Lahem", "الضفة الغربية و قطاع غزة و Gaza Strip", "البحر الميت il-Ba7r الميت",
             "Amal said to Mahdi and مهدي", "بالقدس للقدس عالقدس وبالقدس", "we went to the US, us too", "Iran إيران إيراني Irani",
             "فلسطيني فلسطينية الفلسطينيين Falastiniyye", "بَيْتِ لَحْمٍ", "رامالله Ramalla", "Paris باريس London", "المغرب Morocco"]
    for p in sorted((ROOT / "docs" / "data" / "lessons").glob("20*.json")):
        for t in json.load(io.open(p, encoding="utf-8"))["turns"]:
            if NM.find(t.get("text") or ""):
                texts.append(t["text"])
    fx = {"names_sha": (names.names_sha() or "")[:16], "cases": [{"text": t, "spans": NM.find(t)} for t in texts],
          "fp": {k: names.fp(tuple(k.split(" "))) for k in ("amal", "امل", "mahdi", "رام الله", "x y z")}}
    io.open(FIXTURE, "w", encoding="utf-8").write(json.dumps(fx, ensure_ascii=False, indent=0))
    print("wrote", FIXTURE, len(fx["cases"]))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    if "--fixture" in sys.argv:
        write_fixture()
