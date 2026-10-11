# -*- coding: utf-8 -*-
"""PG-50 fast review mode: scripts/review_picker.py (Medi 2026-10-10 "Is there anyway we can simplify this so that it
doesnt take as much time for amal and i"). Fixture files only: the unsure set, the order (unsure first), the blind
block, the 5 random confident lines stable per date, and missing inputs never failing."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import review_picker as RP  # noqa: E402

DATE = "2026-10-08"
WORDS = ["بيت", "كبير", "شمس", "قمر", "نار", "ماء", "تراب", "حجار", "ورد", "شجرة", "جبل", "بحر", "نهر", "سماء", "ريح"]


def _w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _lesson(n=20):
    """n Student lines with Arabic, each answered by the Tutor (so none join), plus one English line and a chat line."""
    turns, t = [], 10.0
    for k in range(n):
        turns.append({"t": t, "end": t + 3, "who": "Medi", "text": "أنا شفت %s اليوم." % WORDS[k % len(WORDS)], "en": "I saw it today."})
        turns.append({"t": t + 4, "end": t + 6, "who": "Amal", "text": "ممتاز"})
        t += 10
    turns.append({"t": t, "end": t + 2, "who": "Medi", "text": "Can you hear me?"})
    turns.append({"t": t + 3, "end": t + 4, "who": "chat", "text": "hi", "typed_by": "Amal"})
    tm = {"4": {"c": [{"id": "c1", "k": "vocab", "s": "wrong", "said": "شمس", "ar": "شمس", "src": "FA-1"}], "u": []},
          "8": {"c": [{"id": "c2", "k": "grammar", "s": "correct", "said": "نار"}], "u": []}}
    return {"date": DATE, "turns": turns, "tmarks": tm}


def _repo(tmp_path, plan=True, compare=True):
    r = str(tmp_path)
    _w(os.path.join(r, "docs", "data", "lessons", DATE + ".json"), _lesson())
    if plan:   # second listen: 10 changed 3/3, 30 changed 3/3 (+ its ✗ chip), 40 changed 2/3, 70 changed with no 2 agreeing,
        #          80 held, 20 no agreement
        _w(os.path.join(r, "data", "lesson-work", "rehear", DATE, "apply-plan.json"),
           {"lines_changed": [{"t": 10.0, "runs": ["بيت", "بيت", "بيت"], "heard": "بيت"},
                              {"t": 30.0, "runs": ["شمس", "شمس", "شمس"], "heard": "شمس"},
                              {"t": 40.0, "runs": ["قمر.", "قمر", "قمرة"], "heard": "قمر"},
                              {"t": 70.0, "runs": ["ترب", "تراب", "تربة"], "heard": "تراب"}],
            "held": [{"t": 80.0, "runs": ["حجار", "حجار", "حجر"]}],
            "no_agreement": [{"t": 20.0, "runs": ["a", "كبير", "b"]}]})
    if compare:   # the readers disagreed at 01:00 (line 5, t 60)
        _w(os.path.join(r, "data", "lesson-work", "full-audit", DATE + ".compare.json"),
           {"agreed": [], "disputes": [{"id": "D1", "why": "only r1 found it",
                                         "r1": {"t": "01:00", "wrong": "ماء", "right": "مية", "kind": "grammar"}, "r2": None}]})
    return r


def test_pg_50_three_tiers_from_the_second_listen_the_readers_and_the_x_chips(tmp_path):
    out = RP.pick(DATE, repo=_repo(tmp_path))
    assert out["all"] == 20                      # the English line and the chat line hold no Arabic
    by_t = {x["t"]: x for x in out["lines"]}
    # tier 2: changed with 2 of 3 runs agreeing (why keeps the 2-of-3 note)
    assert by_t[10.0]["tier"] == 2 and by_t[10.0]["why"] == ["second listen changed it"] and not by_t[10.0]["unsure"]
    assert by_t[40.0]["tier"] == 2 and by_t[40.0]["why"] == ["second listen changed it", "second listen: 2 of 3 runs agree"]
    # tier 1: no 2 of 3 agree, held, readers disagree, a ✗ chip (a changed line with a ✗ is tier 1, both reasons listed)
    assert by_t[20.0]["tier"] == 1 and by_t[20.0]["why"] == ["second listen: no 2 of 3 runs agree"]
    assert by_t[70.0]["tier"] == 1 and "no 2 of 3 runs agree" in by_t[70.0]["why"][0]
    assert by_t[80.0]["tier"] == 1 and by_t[80.0]["why"] == ["second listen held a change"]
    assert by_t[30.0]["tier"] == 1 and by_t[30.0]["why"][0] == "second listen changed it" and by_t[30.0]["why"][1].startswith("✗ chip")
    assert any("two readers disagreed (D1" in w for w in by_t[60.0]["why"]) and by_t[60.0]["tier"] == 1
    assert by_t[60.0]["propose"] == {"k": "grammar", "said": "ماء", "right": "مية", "from": "readers"}
    assert by_t[50.0]["propose"]["k"] == "grammar" and by_t[50.0]["propose"]["from"] == "chip"   # turn 8, a ✓ grammar chip
    real = {x["t"] for x in out["lines"] if x["unsure"] and not x.get("random")}
    assert real == {20.0, 30.0, 60.0, 70.0, 80.0}
    assert all(x["unsure"] == (x["tier"] == 1) for x in out["lines"])
    assert out["tier_n"] == {"1": 5 + 5, "2": 2, "3": 8}
    assert out["unsure_n"] == 10 and out["changed_n"] == 2 and out["confident_n"] == 8 and out["unsure"] == out["unsure_n"]


def test_pg_50_five_random_confident_lines_are_stable_per_date(tmp_path):
    a = RP.pick(DATE, repo=_repo(tmp_path))
    b = RP.pick(DATE, repo=_repo(tmp_path))
    ra = sorted(x["t"] for x in a["lines"] if x.get("random"))
    assert len(ra) == 5 and ra == sorted(x["t"] for x in b["lines"] if x.get("random"))
    # a confident line changing elsewhere does not reshuffle the others (a hash per line, not a shuffle of the set)
    d = _lesson()
    d["turns"][-4]["text"] = "Okay."                              # line 19 (t 190) loses its Arabic
    c = RP.pick(DATE, d=d, repo=_repo(tmp_path))
    rc = sorted(x["t"] for x in c["lines"] if x.get("random"))
    assert len(set(rc) & set(ra)) >= 4
    assert all(x["why"][0].startswith("random check") for x in a["lines"] if x.get("random"))


def test_pg_50_order_is_tier_1_then_2_then_3_and_blind_is_the_first_50_shown(tmp_path):
    out = RP.pick(DATE, repo=_repo(tmp_path))
    order = sorted(out["lines"], key=lambda x: x["order"])
    tiers = [x["tier"] for x in order]
    assert tiers == sorted(tiers) and tiers[0] == 1 and tiers[-1] == 3
    for k in (1, 2, 3):
        ts = [x["t"] for x in order if x["tier"] == k]
        assert ts == sorted(ts)                                  # each tier in time order
    assert [x["order"] for x in order] == list(range(1, 21))
    assert all(x["blind"] == (x["order"] <= RP.BLIND_N) for x in out["lines"])


def test_pg_50_missing_inputs_are_absent_signals_never_a_crash(tmp_path):
    out = RP.pick(DATE, repo=_repo(tmp_path, plan=False, compare=False))
    assert out["all"] == 20
    assert {x["t"] for x in out["lines"] if x["unsure"] and not x.get("random")} == {30.0}   # only the ✗ chip
    assert RP.pick("2026-01-01", repo=str(tmp_path))["all"] == 0


def test_pg_50_his_split_sentence_is_one_line_like_the_page(tmp_path):
    d = {"date": DATE, "turns": [{"t": 1.0, "end": 2.0, "who": "Medi", "text": "أنا"}, {"t": 4.0, "end": 5.0, "who": "Medi", "text": "شفت بيت"},
                                 {"t": 6.0, "end": 7.0, "who": "Amal", "text": "طيب"}, {"t": 30.0, "end": 31.0, "who": "Medi", "text": "شمس."}], "tmarks": {}}
    out = RP.pick(DATE, d=d, repo=str(tmp_path))
    assert [x["parts"] for x in out["lines"]] == [[0, 1], [3]]


def test_pg_50_run_writes_docs_data_review_pick(tmp_path):
    r = _repo(tmp_path)
    RP.run(DATE, repo=r, log=lambda *a: None)
    got = json.load(open(os.path.join(r, "docs", "data", "review-pick", DATE + ".json"), encoding="utf-8"))
    assert got["date"] == DATE and got["unsure_n"] + got["changed_n"] + got["confident_n"] == got["all"] == sum(got["tier_n"].values())
    assert RP.dates(r) == [DATE]
