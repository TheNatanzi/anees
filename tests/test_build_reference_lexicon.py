# -*- coding: utf-8 -*-
"""Rule AM-25 (Medi 2026-10-06: "Lets spin up a new agent to do deep research on different levantine arabic curriculum
that you can create an index for yourself to use as a secondary data source, it may be useful to amal to help her" +
"ingest"): scripts/build_reference_lexicon.py turns the open Levantine dumps (kaikki ajp/apc, Maknuune) into
docs/data/reference-lexicon.json - glosses, roots, plurals, examples, verb-preposition hints - keyed by normalised
Arabic. A secondary source only: never a spelling (RULES.md S1), never a score. Five-line fixture in tmp_path; the
real raw dumps are never read here and nothing under the repo is written."""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
import build_reference_lexicon as B

KAIKKI_AJP = [
    {"word": "كتب", "pos": "verb", "lang_code": "ajp",
     "head_templates": [{"name": "ajp-verb", "args": {"head": "كتب", "pres": "بكتب"}}],
     "etymology_templates": [{"name": "ajp-root", "args": {"1": "ك ت ب"}}],
     "forms": [{"form": "katab", "tags": ["romanization"]},
               {"form": "بكتب", "tags": ["present"]},
               {"form": "كتب", "tags": ["masculine", "past", "singular", "third-person"], "source": "conjugation"},
               {"form": "كتبت", "tags": ["first-person", "masculine", "past", "singular"], "source": "conjugation"},
               {"form": "كتبوا", "tags": ["masculine", "past", "plural", "third-person"], "source": "conjugation"}],
     "senses": [{"glosses": ["to write"], "examples": [{"text": "كتبت لأهلي.", "english": "I wrote to my parents."},
                                                       {"text": "Audio (Ramallah): (file)"}]},
                {"glosses": ["to destine"]}]},
    {"word": "بيت", "pos": "noun", "lang_code": "ajp",
     "categories": [{"name": "South Levantine Arabic terms belonging to the root ب ي ت"}],
     "forms": [{"form": "bēt", "tags": ["romanization"]}, {"form": "بيوت", "tags": ["plural"]}],
     "senses": [{"glosses": ["house, home"], "examples": [{"text": "صاحب البيت", "english": "the landlord"}]}]},
]
KAIKKI_APC = [
    {"word": "بيت", "pos": "noun", "lang_code": "apc", "forms": [{"form": "بيوت", "tags": ["plural"]}],
     "senses": [{"glosses": ["house"]}, {"glosses": ["verse (of poetry)"]}]},
]
MAK_HEADER = ["ID", "ROOT", "ROOT_NTWS", "ROOT_1", "LEMMA", "LEMMA_SEARCH", "FORM", "LEMMA_BW", "FORM_BW", "CAPHI++",
              "ANALYSIS", "GLOSS", "GLOSS_MSA", "EXAMPLE_USAGE", "NOTES", "SOURCE", "ANNOTATOR"]
MAK_ROWS = [
    ["1", "خ.و.ف", "", "خ", "خَاف", "خاف", "خَاف", "xaAf", "xaAf", "kh aa f", "VERB:P", "be_afraid;fear_[auto]", "", "خاف من الكلب#", "", "", "x"],
    ["2", "خ.و.ف", "", "خ", "خَاف", "خاف", "يِخَاف", "xaAf", "yixaAf", "y i kh aa f", "VERB:I", "be_afraid;fear", "", "", "", "", "x"],
    ["3", "خ.و.ف", "", "خ", "خَاف", "خاف", "خاف على", "xaAf", "xaAf EalaY", "kh aa f # 3 a l a", "VERB:PHRASE", "worry_about", "", "", "", "", "x"],
    ["4", "ء.ب.ر", "", "ء", "إِبْرِة", "إبرة", "إِبْرِة", "<iborip", "<iborip", "2 i b r e", "NOUN:FS", "needle;injection", "إِبْرَة", "في إِبْرِة وقعت تحت الكنب.#أخذت ابرة الأنسولين ولّا؟", "", "", "x"],
    ["5", "ء.ب.ر", "", "ء", "إِبْرِة", "إبرة", "إِبَر", "<iborip", "<ibar", "2 i b a r", "NOUN:P", "needle_[auto]", "", "", "", "", "x"],
]
WORDS = {"items": [
    {"key": "katab", "arabizi": "Katab", "arabic": "كتب", "english": "wrote", "topic": "Verbs List"},
    {"key": "ana_katabet", "arabizi": "Ana katabet", "arabic": "أنا كتبت", "english": "I wrote", "topic": "Past Tense"},
    {"key": "el_bet", "arabizi": "El-bet", "arabic": "البيت", "english": "the house", "topic": "Newest Nouns"},
    {"key": "ibra", "arabizi": "Ibra", "arabic": "إبرة", "english": "needle", "topic": "Newest Nouns"},
    {"key": "bakhaf", "arabizi": "Ba5af", "arabic": "أنا بخاف", "english": "I am afraid", "topic": "Verbs List"},
    {"key": "ghost", "arabizi": "Ghost", "arabic": "مش موجود", "english": "not there", "topic": "Sentence Toolbox"},
    {"key": "noar", "arabizi": "No Arabic", "arabic": "", "english": "skipped", "topic": "Sentence Toolbox"},
]}


def write_raw(tmp_path):
    raw = tmp_path / "raw"; raw.mkdir()
    io.open(raw / "kaikki-ajp.jsonl", "w", encoding="utf-8").write("\n".join(json.dumps(d, ensure_ascii=False) for d in KAIKKI_AJP) + "\n")
    io.open(raw / "kaikki-apc.jsonl", "w", encoding="utf-8").write(json.dumps(KAIKKI_APC[0], ensure_ascii=False) + "\n")
    io.open(raw / "maknuune-v1.0.1.tsv", "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in [MAK_HEADER] + MAK_ROWS) + "\n")
    io.open(tmp_path / "words.json", "w", encoding="utf-8").write(json.dumps(WORDS, ensure_ascii=False))
    return raw


def test_AM_25_norm_agrees_with_the_js_helper_on_the_shared_fixture():
    pairs = json.load(io.open(os.path.join(HERE, "fixtures", "reference-lexicon-norm.json"), encoding="utf-8"))["pairs"]
    for src, want in pairs:
        assert B.norm(src) == want, repr(src)
    assert B.norm(None) == ""


def test_AM_25_five_line_fixture_builds_one_record_per_lemma_with_sources_and_licenses(tmp_path):
    raw = write_raw(tmp_path)
    out = tmp_path / "reference-lexicon.json"
    log = []
    res = B.build(raw=raw, out=out, words_path=tmp_path / "words.json", log=log.append)
    d = json.load(io.open(out, encoding="utf-8"))
    assert res["sources"] == {"kaikki-ajp": 2, "kaikki-apc": 1, "maknuune": 5} == d["sources"]
    assert res["records"] == 4 == d["record_count"]                        # كتب, بيت, خاف, ابره
    R = d["records"]
    # kaikki verb: glosses, root from the ajp-root template, past + present, the example with its English, the ل hint
    k = R["كتب"]
    assert k["pos"] == "verb" and k["gloss"] == ["to write", "to destine"] and k["root"] == "ك.ت.ب"
    assert k["forms"] == {"present": "بكتب", "past": "كتب"}
    assert k["examples"] == [{"ar": "كتبت لأهلي.", "en": "I wrote to my parents."}]      # the Audio line is not an example
    assert k["preps"] == ["ل"]
    assert k["sources"] == [{"src": "kaikki-ajp", "license": "CC BY-SA 3.0"}]
    # the same lemma in two sources is ONE record: glosses merged, the root from the category line, the plural once
    b = R["بيت"]
    assert b["gloss"] == ["house, home", "house", "verse (of poetry)"] and b["root"] == "ب.ي.ت" and b["plural"] == "بيوت"
    assert [s["src"] for s in b["sources"]] == ["kaikki-ajp", "kaikki-apc"]
    # Maknuune verb: P/I rows -> past/present, _[auto] and underscores cleaned, the phrase head gives the على hint,
    # the example gives the من hint, PHRASE rows are not lemmas of their own
    x = R["خاف"]
    assert x["pos"] == "verb" and x["gloss"] == ["be afraid", "fear"] and x["root"] == "خ.و.ف"
    assert x["forms"] == {"past": "خَاف", "present": "يِخَاف"}
    assert x["examples"] == [{"ar": "خاف من الكلب", "en": ""}] and x["preps"] == ["من", "على"]
    assert x["sources"] == [{"src": "maknuune", "license": "CC BY-SA 4.0"}]
    assert "خاف على" not in R
    # Maknuune noun: the key is normalised (إبرة -> ابره), NOUN:P row -> plural, examples split on #
    n = R["ابره"]
    assert n["arabic"] == "إِبْرِة" and n["pos"] == "noun" and n["plural"] == "إِبَر"
    assert [e["ar"] for e in n["examples"]] == ["في إِبْرِة وقعت تحت الكنب.", "أخذت ابرة الأنسولين ولّا؟"]
    # the form index: plural, present, past and every conjugation row point at the lemma
    assert d["index"]["بيوت"] == "بيت" and d["index"]["بكتب"] == "كتب" and d["index"]["كتبت"] == "كتب"
    assert d["index"]["كتبوا"] == "كتب" and d["index"]["ابر"] == "ابره" and d["index"]["يخاف"] == "خاف"
    assert "كتب" not in d["index"]                                            # a lemma is never an index row
    # nothing in a record is a spelling or a score
    for rec in R.values():
        assert set(rec) == {"arabic", "pos", "gloss", "root", "plural", "forms", "examples", "preps", "sources"}
        assert len(rec["examples"]) <= 3
    assert "never a spelling" in d["about"].lower() or "Never a spelling" in d["about"]


def test_AM_25_coverage_counts_amal_doc_words_by_part_of_speech(tmp_path):
    raw = write_raw(tmp_path)
    res = B.build(raw=raw, out=tmp_path / "out.json", words_path=tmp_path / "words.json", log=lambda s: None)
    cov = res["coverage"]
    # كتب exact, أنا كتبت (pronoun + conjugation row), البيت (ال), إبرة (normalised), أنا بخاف (pronoun + present) = 5;
    # مش موجود missed; the row with no Arabic is not counted
    assert cov["total"] == 6 and cov["found"] == 5
    assert cov["by_pos"] == {"verb": 3, "noun": 2}
    assert cov["missed_by_topic"] == {"Sentence Toolbox": 1}
    d = json.load(io.open(tmp_path / "out.json", encoding="utf-8"))
    rec, key = B.lookup(d["records"], d["index"], "أنا بخاف")
    assert key == "خاف" and rec["gloss"][0] == "be afraid"
    assert B.lookup(d["records"], d["index"], "هم كتبوا")[1] == "كتب"
    assert B.lookup(d["records"], d["index"], "") == (None, None)


def test_AM_25_the_file_stays_under_the_size_cap_by_dropping_examples_first(tmp_path):
    raw = write_raw(tmp_path)
    out = tmp_path / "small.json"
    full = B.build(raw=raw, out=out, words_path=None, log=lambda s: None)["bytes"]
    res = B.build(raw=raw, out=out, words_path=None, max_bytes=full - 150, log=lambda s: None)
    d = json.load(io.open(out, encoding="utf-8"))
    assert res["bytes"] < full and "examples" in res["dropped"] and "index" not in res["dropped"]
    assert d["record_count"] == 4 and d["index"]                                 # records and the index survive
    assert sum(len(r["examples"]) for r in d["records"].values()) < 4           # some examples went
    assert res["coverage"] is None                                              # no words file = no coverage block


def test_AM_25_prepositions_after_a_verb_only():
    vf = {"فتح", "فتحت", "بفتح"}
    assert B.prep_after(B._tokens("فتحت عليه الباب"), vf) == ["على"]
    assert B.prep_after(B._tokens("فتح بالمفتاح"), vf) == ["ب"]
    assert B.prep_after(B._tokens("حكى لإلها"), {"حكي"}) == ["ل"]
    assert B.prep_after(B._tokens("الباب فتح"), vf) == []                      # nothing after the verb
    assert B.prep_after(B._tokens("على الباب فتح"), vf) == []                  # a preposition BEFORE the verb is not a hint
    assert B.prep_after(B._tokens("فتح بيته"), vf) == []                       # ب as the first letter of a noun is not ب
