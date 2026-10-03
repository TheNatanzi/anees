# -*- coding: utf-8 -*-
"""LS-11 one lesson ledger (scripts/lesson_ledger.py). Medi 2026-10-02: "what is the main source of all of errors on the
lessons? I think the transcription page of the lessons should be no?" - then "yes": the marked transcript is the one
source of every judgment. Each conflict kind is tested on its real moment; the guard check is tested on planted drift.
Offline: nothing here touches the database or writes outside tmp_path."""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import lesson_ledger as LL  # noqa: E402

BUCKETS = {"B6": {"name": "kan"}, "A9": {"name": "plural"}, "D2": {"name": "prep"}}
SCORED = {"B6", "A9", "D2"}
NOT_TAUGHT = lambda b: False  # noqa: E731


def turns():
    return [
        {"t": 92.92, "end": 95.7, "who": "Medi", "text": "لسه الـ divine يروحوا."},            # 10-01 01:33
        {"t": 99.9, "end": 101.6, "who": "Amal", "text": "شو يعني لسه الزباين يروحوا؟"},
        {"t": 1285.0, "end": 1288.0, "who": "Medi", "text": "اليوم بلبس بلوزة so شو؟"},       # 09-26 21:25
        {"t": 2000.0, "end": 2003.0, "who": "Medi", "text": "اسمي كتير"},                       # 09-14 08:16 shape
        {"t": 3000.0, "end": 3006.0, "who": "Medi", "text": "كانت عمرها عشرين، كان حلو"},     # C3: use + slip, one turn
        {"t": 3111.0, "end": 3112.0, "who": "Medi", "text": "tazkara?"},                         # 09-23 51:51
    ]


def wb(eid, t, key, tok, kind="correct"):
    return {"event_id": eid, "t": t, "kind": kind, "word_key": key, "arabic": tok, "tok": tok}


def audit(uid, t, wrong, fix, tier=1, conf="high", signal="explicit-no", on_sheet=True, kind="wrong", key=None):
    return {"source": "audit-2026-09-26", "audit_uid": uid, "t": t, "kind": kind, "wrong": wrong, "fix": fix, "tier": tier,
            "confidence": conf, "signal": signal, "on_sheet": on_sheet, "sheet_key": key, "arabic": fix}


def detail(**kw):
    d = {"turns": turns(), "vocab_correct": [], "vocab_errors": [], "not_errors": [], "grammar_errors": [], "grammar_not_counted": []}
    d.update(kw)
    return d


def build(d, uses=None, patches=None, rulings=None, resolve=True):
    return LL.build("2026-10-01", d, uses or {}, BUCKETS, SCORED, NOT_TAUGHT, (), (), patches or {}, rulings or {}, resolve=resolve)


def test_LS_11_c1_word_bank_correct_gives_way_to_amals_no_on_that_word():
    # 10-01 01:33: the Word Bank scored لسه Correct; Amal said no to it (he meant 'until' = la-, not on her list)
    led, act = build(detail(vocab_correct=[wb("e-lisa", 92.92, "lisa", "لسه")],
                            vocab_errors=[audit("FA-lisa", 93, "لسه", "لـ (la) الزباين يروحوا", on_sheet=False)]))
    c = led["conflicts"][0]
    assert c["kind"] == "C1" and c["resolved"] and not led["needs_medi"]
    m = {x["id"]: x for x in led["marks"]}
    assert m["wb:e-lisa"]["verdict"] == "folded" and m["wb:e-lisa"]["folded_into"] == "ra:FA-lisa"
    assert m["ra:FA-lisa"]["verdict"] == "not-scored"                      # la- is not on her list
    assert act["overrides"][0]["event_id"] == "e-lisa" and act["overrides"][0]["changes"]["observation_only"] is True
    assert "reason" not in act["overrides"][0]["changes"]                  # never a key a review patch guards
    assert led["counts"]["words"]["right"] == 0 and led["counts"]["words"]["scored"] == 0


def test_LS_11_c1q_a_phrase_with_two_candidate_words_is_one_medi_question_counted_as_before():
    # 09-26 21:25: he answered about clothes (بلبس بلوزة), Amal said الجو: which word was wrong is not decidable
    led, act = build(detail(vocab_correct=[wb("e-b1", 1285.7, "ana balbes", "بلبس"), wb("e-b2", 1286.5, "blUze", "بلوزة")],
                            vocab_errors=[audit("FA-j", 1285, "بلبس بلوزة", "الجو", conf="medium", signal="prompt-then-fix")]))
    assert [c["kind"] for c in led["conflicts"]] == ["C1q", "C1q"]
    assert len(led["needs_medi"]) == 1                                      # one question for the moment
    lead = next(c for c in led["conflicts"] if c["id"] in led["needs_medi"])
    assert set(lead["options"]) == {"بلبس", "بلوزه", "keep"} or "keep" in lead["options"]
    assert not act["overrides"] and led["counts"]["words"]["right"] == 2 and led["counts"]["words"]["wrong"] == 1


def test_LS_11_c1_same_word_is_one_attempt_counted_as_the_slip():
    # 09-10 27:50 shape: the Word Bank took his بخسر as bakser right; Amal recast it to بكسر (same list word)
    led, act = build(detail(vocab_correct=[wb("e-k", 2000.5, "ana bakser", "بخسر")],
                            vocab_errors=[audit("FA-k", 2000, "بخسر", "بكسر", key="ana bakser", signal="recast")]))
    assert led["conflicts"][0]["kind"] == "C1" and act["overrides"][0]["changes"]["scored_in_event"] is True
    assert "Same attempt" in act["overrides"][0]["changes"]["ledger_reason"]


def test_LS_11_c2q_medi_says_word_slip_takes_the_grammar_copy_out():
    g = {"id": "FA-g", "t": 2000, "bucket": "A9", "wrong": "اسمي", "right": "أسماء", "signal": "recast", "confidence": "high"}
    d = detail(grammar_errors=[g], vocab_errors=[audit("FA-v", 2000, "اسمي", "أسماء", tier=1)])
    led, _ = build(d)
    cid = led["needs_medi"][0]
    led2, act = build(d, rulings={cid: {"conflict": cid, "answer": "word"}})
    assert ("grammar_errors", "rg:FA-g") == act["move"][0][:2]
    assert led2["counts"]["grammar"]["mistakes"] == 0 and led2["counts"]["words"]["wrong"] == 1


def test_LS_11_an_answer_to_a_grouped_question_settles_every_word_without_crashing():
    d = detail(vocab_correct=[wb("e-b1", 1285.7, "ana balbes", "بلبس"), wb("e-b2", 1286.5, "blUze", "بلوزة")],
               vocab_errors=[audit("FA-j", 1285, "بلبس بلوزة", "الجو", conf="medium", signal="prompt-then-fix")])
    led, _ = build(d)
    cid = led["needs_medi"][0]
    led2, act = build(d, rulings={cid: {"conflict": cid, "answer": "بلوزة", "date": "2026-10-03"}})
    assert not led2["needs_medi"] and all(c.get("resolved") for c in led2["conflicts"])
    assert [o["event_id"] for o in act["overrides"]] == ["e-b2"]


def test_LS_11_shadow_mode_settles_nothing():
    led, act = build(detail(vocab_correct=[wb("e-lisa", 92.92, "lisa", "لسه")],
                            vocab_errors=[audit("FA-lisa", 93, "لسه", "لـ الزباين", on_sheet=False)]), resolve=False)
    assert not led["conflicts"][0].get("resolved") and led["conflicts"][0]["would_settle"]


def test_LS_11_medi_answer_settles_the_question():
    d = detail(vocab_correct=[wb("e-b1", 1285.7, "ana balbes", "بلبس")],
               vocab_errors=[audit("FA-j", 1285, "بلبس بلوزة", "الجو", conf="medium", signal="prompt-then-fix")])
    led, _ = build(d)
    cid = led["needs_medi"][0]
    led2, act = build(d, rulings={cid: {"conflict": cid, "answer": "بلبس", "date": "2026-10-03"}})
    assert not led2["needs_medi"] and led2["conflicts"][0]["resolved"] and act["overrides"]


def test_LS_11_c1r_a_hand_context_review_of_the_moment_stands():
    # 09-23 51:51 tazkara: the Word Bank's context review already said "the miss was حجز (rule 5)"
    patches = {"e-t": {"expected": {}, "changes": {"contextual_audit": True, "vocab_points": 1, "observation_only": False}}}
    led, act = build(detail(vocab_correct=[wb("e-t", 3111.3, "tazkara", "tazkara?")],
                            vocab_errors=[audit("FA-t", 3111, "tazkara", "7ajez (حجز)")]), patches=patches)
    assert led["conflicts"][0]["kind"] == "C1r" and not act["overrides"] and not led["needs_medi"]


def test_LS_11_c2_a_wrong_form_filed_twice_counts_once_as_grammar_and_c2b_two_errors_both_count():
    g = {"id": "FA-g", "t": 2000, "bucket": "A9", "wrong": "اسمي", "right": "أسماء", "signal": "prompt-then-fix", "confidence": "medium"}
    led, act = build(detail(grammar_errors=[g], vocab_errors=[audit("FA-v", 2000, "اسمي", "أسماء", tier=2)]))
    assert led["conflicts"][0]["kind"] == "C2" and act["move"] == [("vocab_errors", "ra:FA-v", act["move"][0][2], "C2")]
    assert led["counts"]["words"]["wrong"] == 0 and led["counts"]["grammar"]["mistakes"] == 1
    # 09-23 25:24 shape: فول for فطور (a different word) AND the missing el- (A1-like): two errors
    g2 = dict(g, wrong="كتير", right="الكتير", id="FA-g2")
    led, act = build(detail(grammar_errors=[g2], vocab_errors=[audit("FA-v2", 2000, "كتير", "فطور", tier=1)]))
    assert led["conflicts"][0]["kind"] == "C2b" and not act["move"] and led["counts"]["words"]["wrong"] == 1


def test_LS_11_c3_a_use_and_a_slip_of_one_rule_on_one_turn_are_one_attempt():
    g = {"id": "FA-k", "t": 3000, "bucket": "B6", "wrong": "كانت", "right": "كان", "signal": "recast", "confidence": "high"}
    uses = {"B6": [{"date": "2026-10-01", "t": 3004.5, "hit": "كان"}]}           # 4.5 s away: grammar_math does not pair it
    led, act = build(detail(grammar_errors=[g]), uses=uses)
    assert led["conflicts"][0]["kind"] == "C3"
    assert led["counts"]["grammar"]["uses"] == 1 and led["counts"]["grammar"]["mistakes"] == 1
    assert act["fold_uses"] == [{"bucket": "B6", "date": "2026-10-01", "t": 3004.5, "hit": "كان", "mark": "rg:FA-k"}]
    assert LL.uses_minus(uses, act["fold_uses"]) == {"B6": []}


def test_LS_11_shadow_mode_records_conflicts_but_changes_nothing():
    d = detail(vocab_correct=[wb("e-lisa", 92.92, "lisa", "لسه")],
               vocab_errors=[audit("FA-lisa", 93, "لسه", "لـ الزباين", on_sheet=True, key="la")])
    led, act = build(d, resolve=False)
    assert led["conflicts"] and not act["overrides"] and not act["move"]
    assert led["counts"]["words"]["right"] == 1 and led["counts"]["words"]["wrong"] == 1


def test_LS_11_c4_same_word_folds_a_different_word_does_not():
    card = {"wrong": "لازم", "tok": "لازم", "arabic": "لازم"}
    assert not LL.same_word(card, {"wrong": "مساعد", "amal_gave": "مساعدة"})       # 09-26 10:13 (was swallowed)
    assert LL.same_word({"wrong": "الكلمة", "tok": "الكلمة", "arabic": "عاصفة"}, {"wrong": "storm (forgot the word)", "amal_gave": "عاصفة"})


def test_LS_11_every_producer_item_has_exactly_one_mark_on_the_committed_lessons():
    import glob
    for p in glob.glob(os.path.join(ROOT, "data", "lesson-work", "ledger", "20*.json")):
        led = json.load(open(p, encoding="utf-8"))
        own = [m["id"] for m in led["marks"]]
        assert len(own) == len(set(own)), p
        assert LL.counts(led) == led["counts"], p
        for c in led["conflicts"]:
            assert c.get("resolved") or c.get("medi") or c["kind"] in ("C1p", "C1a", "C2b", "C1r") or \
                (c.get("group") or c["id"]) in led["needs_medi"], (p, c["id"])


def test_LS_11_committed_pages_equal_the_ledger():
    assert LL.check(ROOT) == []


# ---------------- planted failures: the guard check must catch each
def _mini_repo(tmp_path):
    led, act = build(detail(vocab_correct=[wb("e-lisa", 92.92, "lisa", "لسه"), wb("e-x", 1286.5, "blUze", "بلوزة")],
                            vocab_errors=[audit("FA-lisa", 93, "لسه", "لـ الزباين", on_sheet=False)]))
    led["overrides"] = [dict(o, expected={"word_key": "lisa", "t_start": 92.92}) for o in act["overrides"]]
    led["fold_uses"] = []
    d = "2026-10-01"
    root = tmp_path
    for sub in ("docs/data/lessons", "data/lesson-work/ledger"):
        os.makedirs(root / sub, exist_ok=True)
    w = lambda p, o: open(root / p, "w", encoding="utf-8").write(json.dumps(o, ensure_ascii=False))  # noqa: E731
    c = led["counts"]
    w("docs/data/lessons.json", {"lessons": [{"date": d, "words": dict(c["words"]), "grammar": {"uses": None, "mistakes": 0},
                                              "ledger": {"needs_medi": len(led["needs_medi"])}}]})
    w("docs/data/lessons/%s.json" % d, {"vocab_correct": [wb("e-x", 1286.5, "blUze", "بلوزة")], "grammar_errors": [],
                                        "vocab_errors": [], "not_errors": [dict(audit("FA-lisa", 93, "لسه", "لـ", on_sheet=False))]})
    w("docs/data/word-bank-audit-slips.json", {"events": [], "overrides": led["overrides"]})
    w("data/full-audit-2026-09-26.json", {"sweep_compat": {"vocab": []}})
    w("docs/data/word-bank-evidence.json", {"events": [{"id": "e-lisa", "word_key": "lisa", "t_start": 92.92}]})
    LL.write(led, repo=str(root))
    return root


def test_LS_11_check_is_clean_on_a_consistent_mini_repo_and_catches_planted_drift(tmp_path):
    root = _mini_repo(tmp_path)
    assert LL.check(str(root)) == []
    # 1 a page number that is not the ledger's count
    p = root / "docs/data/lessons.json"
    doc = json.load(open(p, encoding="utf-8"))
    good = copy.deepcopy(doc)
    doc["lessons"][0]["words"]["right"] += 1
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert any("words.right" in x for x in LL.check(str(root)))
    p.write_text(json.dumps(good), encoding="utf-8")
    # 2 an override whose Word Bank event changed since the ledger was built
    ev = root / "docs/data/word-bank-evidence.json"
    ev.write_text(json.dumps({"events": [{"id": "e-lisa", "word_key": "lisa", "t_start": 50.0}]}), encoding="utf-8")
    assert any("changed since the ledger" in x for x in LL.check(str(root)))
    # 3 a stale ledger: an input changed after it was built (the evidence file above is an input)
    assert any("older than its inputs" in x for x in LL.check(str(root)))
    # 4 a conflict nobody decided and nobody asked Medi about
    lp = root / "data/lesson-work/ledger/2026-10-01.json"
    led = json.load(open(lp, encoding="utf-8"))
    led["conflicts"][0].pop("resolved", None)
    lp.write_text(json.dumps(led, ensure_ascii=False), encoding="utf-8")
    assert any("neither resolved by a rule nor listed for Medi" in x for x in LL.check(str(root)))
    # 5 an answer of Medi's that matches no question any more is never dropped silently
    (root / "data/lesson-work/ledger-rulings.json").write_text(json.dumps({"rulings": [{"conflict": "C1q-gone", "answer": "keep"}]}), encoding="utf-8")
    assert any("matches no question" in x for x in LL.check(str(root)))
    # 6 a producer item with no mark (a card on the page the ledger never saw)
    led["marks"] = [m for m in led["marks"] if m["id"] != "wb:e-x"]
    lp.write_text(json.dumps(led, ensure_ascii=False), encoding="utf-8")
    assert any("have no mark" in x or "counts do not match" in x for x in LL.check(str(root)))
