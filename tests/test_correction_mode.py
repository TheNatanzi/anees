# -*- coding: utf-8 -*-
"""PR-16 (every correction proposes a rule; his yes -> registry + guard test; probation) and PR-17 (pull fail-open,
producer targets, orphans, precedence, 15-minute recount) - Medi 2026-10-03: "do a hand off chip where I can make all the
corrections. Have it make rules for every correction if possible". Fixtures only, no live writes (tests/conftest.py)."""
import json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import medi_corrections as MC  # noqa: E402

Q = lambda *a: None  # noqa: E731  (silent log)


def _c(**k):
    base = {"id": "c-" + k.pop("cid", "x1"), "lesson_date": "2026-10-02", "turn_t": 422.0, "turn_who": "Medi", "kind": "not-slip",
            "target": {"k": "vocab", "wrong": "سمعت", "src": "FA-aaaa1111"}, "payload": {"reason": "not-correcting"},
            "ts": "2026-10-03T10:00:00-07:00"}
    base.update(k)
    return base


# ------------------------------------------------------------------ PR-17
def test_pr_17_pull_never_fails_missing_table_unreachable_bad_rows_and_big_batch(tmp_path):
    out, q = str(tmp_path / "m.json"), str(tmp_path / "q.json")
    MC.W(out, {"rows": [_c(cid="old")]})
    assert MC.pull(out, fetch=lambda: None, dates={"2026-10-02"}, quar=q, log=Q)["status"] == "missing"

    def boom():
        raise OSError("down")
    assert MC.pull(out, fetch=boom, dates={"2026-10-02"}, quar=q, log=Q)["status"] == "unreachable"
    assert [r["id"] for r in MC.J(out)["rows"]] == ["c-old"]          # the last mirror is kept
    rows = [_c(cid="ok"), _c(cid="bad", lesson_date="2031-01-01"), {"id": "c-k", "kind": "nonsense"}]
    assert MC.pull(out, fetch=lambda: rows, dates={"2026-10-02"}, quar=q, log=Q) == {"status": "ok", "new": 1, "quarantined": 2}
    assert {x["row"]["id"] for x in MC.J(q)["rows"]} == {"c-bad", "c-k"}
    many = [_c(cid="n%d" % i) for i in range(MC.HOLD_OVER + 1)]
    assert MC.pull(out, fetch=lambda: many, dates={"2026-10-02"}, quar=q, log=Q)["status"] == "held"
    assert not any(r["id"] == "c-n0" for r in MC.J(out)["rows"])


def test_pr_17_target_by_producer_id_then_fingerprint_and_orphan_is_reported_not_raised():
    a = {"date": "2026-10-02", "t": "07:02", "kind": "vocab-A", "wrong": "سمعت", "uid": "FA-aaaa1111", "signal": "recast"}
    b = {"date": "2026-10-02", "t": "07:02", "kind": "vocab-A", "wrong": "سمعت", "uid": "FA-bbbb2222", "signal": "recast"}
    MC.apply_rows([a, b], [_c()], answers={}, rules=[])
    assert a["kind"] == "rejected" and b["kind"] == "vocab-A"      # the producer id picks the one row
    no_src = _c(cid="f", target={"k": "vocab", "wrong": "سمعت"})
    c = dict(b)
    MC.apply_rows([c], [no_src], answers={}, rules=[])
    assert c["kind"] == "rejected"                                   # fingerprint fallback
    lost = _c(cid="lost", turn_t=3000.0, target={"k": "vocab", "wrong": "زز", "src": "FA-nothere"})
    rep = MC.apply_rows([dict(b)], [lost], answers={}, rules=[])
    assert rep["orphaned"] == ["c-lost"] and rep["applied"] == []


def test_pr_17_my_arabic_was_right_is_amals_card_and_counts_until_she_taps():
    row = {"date": "2026-10-02", "t": "07:02", "kind": "vocab-A", "wrong": "سمعت", "right": "صحيت", "uid": "FA-aaaa1111", "signal": "recast"}
    c = _c(payload={"reason": "right"})
    rows = [dict(row)]
    rep = MC.apply_rows(rows, [c], answers={}, rules=[])
    assert rows[0]["kind"] == "vocab-A" and rep["waiting_for_amal"][0]["voiced"] is True
    card = MC.amal_cards(rep, repo=ROOT)[0]
    assert card["id"] == "ledger:MC-c-x1" and "He was right" in [o["label"] for o in card["options"]]
    rows = [dict(row)]
    rep = MC.apply_rows(rows, [c], answers={"MC-c-x1": {"conflict": "MC-c-x1", "answer": "right", "at": "2026-10-04"}}, rules=[])
    assert rows[0]["kind"] == "rejected" and "Amal" in rows[0]["rejected_why"]
    assert MC.amal_cards(rep, repo=ROOT)[0]["answered"]["answer"] == "right"


def test_pr_17_a_row_amal_ruled_is_never_changed_whatever_his_reason():
    rows = [{"date": "2026-10-02", "t": "07:02", "kind": "vocab-A", "wrong": "سمعت", "uid": "FA-aaaa1111", "signal": "amal-ruling"}]
    rep = MC.apply_rows(rows, [_c()], answers={}, rules=[])
    assert rows[0]["kind"] == "vocab-A" and rep["waiting_for_amal"]


def test_pr_17_was_wrong_or_add_without_her_voiced_fix_is_tier_b_with_it_tier_a():
    turns = [{"t": 422.0, "who": "Medi", "text": "أنا سمعت"}, {"t": 425.0, "who": "Amal", "text": "صحيت"}]
    add = _c(kind="add", target={"k": "vocab", "said": "سمعت"}, payload={"k": "vocab", "wrong": "سمعت", "right": "صحيت"})
    rows = []
    MC.apply_rows(rows, [add], answers={}, turns=turns, rules=[])
    assert rows[0]["kind"] == "vocab-A" and rows[0]["signal"] == "recast"
    rows = []
    rep = MC.apply_rows(rows, [dict(add, payload={"k": "vocab", "wrong": "سمعت", "right": "نمت"})], answers={}, turns=turns, rules=[])
    assert rows[0]["kind"] == "vocab-B" and rep["tier_b"] == ["c-x1"]


def test_pr_17_wrong_speaker_time_and_missing_word_reach_the_overlay():
    import transcript_fixes as TF
    rows = MC.text_rows([_c(cid="s", kind="speaker", payload={"who": "Amal"}), _c(cid="t", kind="time", turn_t=10.0, payload={"t": 12.5}),
                         _c(cid="m", kind="missing", turn_t=20.0, payload={"heard": "el"})])
    T = [{"t": 422.0, "who": "Medi", "text": "a"}, {"t": 10.0, "who": "Medi", "text": "b"}, {"t": 20.0, "who": "Medi", "text": "3ala 3ashra"}]
    out = {u.get("engine_t", u["t"]): u for u in TF.apply("2026-10-02", T, rows)}
    assert out[422.0]["who"] == "Amal" and out[10.0]["t"] == 12.5 and out[20.0]["text"].endswith("el")


def test_pr_17_trigger_recounts_medi_corrections_within_15_min():
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "scripts", "amal_trigger.py"), encoding="utf-8").read())
    assert "fetch_medi_corrections" in {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    import importlib
    import amal_trigger as AT
    AT = importlib.reload(AT)         # tests/conftest.py empties SOURCES for every other test file
    src = next(s for s in AT.SOURCES if s["id"] == "medi_corrections")
    names = [n for n, _ in AT.STEPS]
    assert src["steps"][0] == "pull_medi_corrections" and names.index("pull_medi_corrections") < names.index("full_audit_build")
    assert "build_lessons_page_data" in src["steps"] and "medi_corrections_propose" in src["steps"]


def test_pr_17_guard_check_is_a_warning_only_and_an_orphan_never_blocks(tmp_path):
    cfg = json.load(open(os.path.join(ROOT, "scripts", "publish_guard_config.json"), encoding="utf-8"))
    assert "medi_corrections" in cfg["advisory"] and "medi_corrections" not in cfg["required"]
    (tmp_path / "data" / "lesson-work").mkdir(parents=True)
    MC.W(str(tmp_path / "data" / "lesson-work" / "medi-corrections-report.json"), {"orphaned": ["c-lost"]})
    ok, detail = MC.check(repo=str(tmp_path))
    assert not ok and "c-lost" in detail


# ------------------------------------------------------------------ PR-16
def _turns(*lines):
    return [{"t": float(i * 10), "who": w, "text": x} for i, (w, x) in enumerate(lines)]


def test_pr_16_a_lone_word_stays_one_off_and_a_text_fix_spreads_only_in_the_same_3_word_context(monkeypatch):
    L = {"2026-10-02": _turns(("Medi", "على العشاء"), ("Medi", "العشاء")),
         "2026-09-30": _turns(("Medi", "على العشاء"), ("Amal", "على العشاء"), ("Medi", "بدي العشاء"), ("Medi", "على العشاء يلا"))}
    monkeypatch.setattr(MC, "_lessons", lambda repo=None: sorted(L.items()))
    monkeypatch.setattr(MC, "turns_of", lambda d, repo=None: L[str(d)])
    lone = _c(cid="l", kind="text", turn_t=10.0, target={"word": "العشاء"}, payload={"engine_wrote": "العشاء", "heard": "عشرة", "line": "العشاء"})
    p = MC.propose([lone], rows=[], uses_=[])[0]
    assert p["owner"] == "one-off" and not p["can_yes"]
    ctx = _c(cid="k", kind="text", turn_t=0.0, target={"word": "العشاء"}, payload={"engine_wrote": "العشاء", "heard": "عشرة", "line": "على العشاء"})
    p = MC.propose([ctx], rows=[], uses_=[])[0]
    assert p["owner"] == "medi" and p["can_yes"] and [(m["date"], m["t"]) for m in p["moments"]] == [("2026-09-30", 0.0)]
    assert p["first"][0]["after"] == "على عشرة"


def test_pr_16_yes_is_disabled_over_15_moments_and_arabic_questions_go_to_amal_shapes_to_claude():
    rows = [{"date": "2026-09-%02d" % (i + 1), "t": "01:00", "kind": "vocab-A", "wrong": "سمعت", "signal": "recast"} for i in range(16)]
    c = _c(target={"k": "vocab", "wrong": "سمعت", "signal": "recast"})
    p = MC.propose([c], rows=rows, uses_=[])[0]
    assert p["owner"] == "medi" and p["n"] == 16 and not p["can_yes"] and "more than 15" in p["why_not"]
    assert MC.propose([_c(payload={"reason": "right"})], rows=rows, uses_=[])[0]["owner"] == "amal"
    assert MC.propose([_c(payload={"reason": "fixed-first"})], rows=rows, uses_=[])[0]["owner"] == "code"
    add = _c(kind="add", target={"k": "vocab", "said": "سمعت"}, payload={"wrong": "سمعت", "right": "صحيت"})
    assert MC.propose([add], rows=rows, uses_=[])[0]["owner"] == "amal"


def test_pr_16_a_yes_counts_only_with_the_same_pattern_hash_and_rules_are_on_probation(tmp_path, monkeypatch):
    repo = tmp_path
    for d in ("docs/data/lessons", "data/lesson-work"):
        (repo / d).mkdir(parents=True)
    rows = [{"date": "2026-09-30", "t": "01:00", "kind": "vocab-A", "wrong": "سمعت", "signal": "recast"}]
    monkeypatch.setattr(MC, "audit_rows", lambda repo=None: rows)
    monkeypatch.setattr(MC, "uses", lambda repo=None: [])
    c = _c(target={"k": "vocab", "wrong": "سمعت", "signal": "recast"})
    P = MC.propose([c], repo=str(repo), rows=rows, uses_=[])
    stale = {"id": "a1", "kind": "rule-answer", "proposal": P[0]["id"], "answer": "yes", "payload": {"hash": "nope"},
             "lesson_date": "2026-10-02", "turn_t": 0, "turn_who": "Medi", "ts": "2026-10-03T11:00:00-07:00"}
    _, R = MC.write_proposals(repo=str(repo), corrections=[c, stale])
    assert R == []
    good = dict(stale, id="a2", payload={"hash": P[0]["hash"]})
    _, R = MC.write_proposals(repo=str(repo), corrections=[c, good])
    assert R[0]["id"] == "MC-001" and R[0]["n_at_yes"] == 1 and not R[0]["paused"]
    rows += [dict(rows[0], date="2026-09-0%d" % i) for i in range(1, 4)]      # now 4 > 2 x 1 at his yes: paused
    _, R = MC.write_proposals(repo=str(repo), corrections=[c, good])
    assert R[0]["id"] == "MC-001" and R[0]["paused"] and MC.live_rules(R) == []


def test_pr_16_his_yes_becomes_a_registry_entry_with_a_test_that_names_it(tmp_path):
    repo = tmp_path
    for d in ("rules", "scripts", "data/lesson-work/full-audit", "tests"):
        (repo / d).mkdir(parents=True)
    shutil.copy(os.path.join(ROOT, "scripts", "publish_guard_config.json"), repo / "scripts" / "publish_guard_config.json")
    (repo / "rules" / "registry.json").write_text(json.dumps({"rules": [{"id": "WS-28"}, {"id": "TR-22"}]}), encoding="utf-8")
    rule = {"id": "MC-001", "proposal": "P-c-x1", "from": "c-x1", "kind": "not-slip", "plain": "When Amal says mhm after «سمعت», she is not correcting you.",
            "pattern": {"wrong": "سمعت", "signal": "recast"}, "n_at_yes": 1, "on": "2026-10-03", "quote": "she wasn't correcting · Make it a rule: yes",
            "example": {"date": "2026-10-02", "t": "07:02"}}
    MC.W(str(repo / "data" / "lesson-work" / "correction-rules.json"), {"rules": [rule]})
    assert MC.register(repo=str(repo), run_book=False, log=Q) == ["WS-29"]
    reg = json.load(open(repo / "rules" / "registry.json", encoding="utf-8"))["rules"][-1]
    assert reg["id"] == "WS-29" and reg["status"] == "enforced" and reg["source"][0]["by"] == "medi" and reg["kind"] == "not-error"
    body = (repo / MC.GEN_TEST).read_text(encoding="utf-8")
    assert "def test_ws_29_mc_001_standing_rule_applies" in body and "WS-29" in body
    assert "- MC-001 (WS-29): " in (repo / "data" / "lesson-work" / "full-audit" / "READER-BRIEF.md").read_text(encoding="utf-8")
    assert MC.GEN_TEST in json.load(open(repo / "scripts" / "publish_guard_config.json", encoding="utf-8"))["commands"]["tests_py"]["cmd"]
    assert MC.register(repo=str(repo), run_book=False, log=Q) == []      # once only


def test_pr_16_standing_rules_apply_to_every_lesson_text_rows_and_not_use():
    import transcript_fixes as TF
    import detect_grammar_usage as DG
    tr = {"id": "MC-002", "kind": "text", "plain": "x", "pattern": {"who": "Medi", "engine_wrote": "العشاء", "heard": "عشرة", "ctx": ["على", "العشاء", ""]}}
    out = TF.apply("2026-11-01", [{"t": 1.0, "who": "Medi", "text": "على العشاء"}, {"t": 2.0, "who": "Medi", "text": "العشاء"}], MC.rule_text_rows([tr]))
    assert out[0]["text"] == "على عشرة" and out[1]["text"] == "العشاء"
    nu = {"id": "MC-003", "kind": "not-use", "plain": "y", "pattern": {"rule": "B1", "hit": "بدي"}}
    R = MC.use_rulings([], [nu])
    assert DG.ruled(R, "2026-11-01", "B1", 5.0, "بدي") and not DG.ruled(R, "2026-11-01", "B1", 5.0, "بحب")
    ns = {"id": "MC-004", "kind": "not-slip", "plain": "z", "pattern": {"wrong": "سمعت", "signal": "recast"}}
    rows = [{"date": "2026-11-01", "t": "00:01", "kind": "vocab-A", "wrong": "سمعت", "signal": "recast"},
            {"date": "2026-11-01", "t": "00:02", "kind": "vocab-A", "wrong": "سمعت", "signal": "amal-ruling"}]
    assert MC.apply_standing(rows, [ns]) == {"MC-004": 1} and rows[0]["kind"] == "rejected" and rows[1]["kind"] == "vocab-A"


# ------------------------------------------------------------------ Codex audit 2026-10-03 (PR-17)
def test_pr_17_a_duplicate_suffixed_uid_picks_its_own_row_and_an_ambiguous_fingerprint_changes_nothing():
    uid_of = lambda r: "FA-base0001"  # noqa: E731  (both rows share one base, as before assign_uids)
    a = {"date": "2026-10-02", "t": "07:02", "kind": "vocab-A", "wrong": "سمعت", "signal": "recast"}
    b = dict(a)
    MC.apply_rows([a, b], [_c(target={"k": "vocab", "wrong": "سمعت", "src": "FA-base0001x"})], answers={}, rules=[], uid_of=uid_of)
    assert a["kind"] == "vocab-A" and b["kind"] == "rejected"
    a2, b2 = dict(a), dict(a)
    rep = MC.apply_rows([a2, b2], [_c(cid="amb", target={"k": "vocab", "wrong": "سمعت"})], answers={}, rules=[])
    assert a2["kind"] == b2["kind"] == "vocab-A" and rep["orphaned"] == ["c-amb"]


def test_pr_17_a_held_bad_batch_never_blocks_later_real_corrections(tmp_path):
    out, q = str(tmp_path / "m.json"), str(tmp_path / "q.json")
    junk = [_c(cid="j%d" % i) for i in range(MC.HOLD_OVER + 1)]
    assert MC.pull(out, fetch=lambda: junk, dates={"2026-10-02"}, quar=q, log=Q)["status"] == "held"
    res = MC.pull(out, fetch=lambda: junk + [_c(cid="real")], dates={"2026-10-02"}, quar=q, log=Q)
    assert res["status"] == "ok" and [r["id"] for r in MC.J(out)["rows"]] == ["c-real"]


def test_pr_17_a_time_fix_reaches_the_track_turns_too():
    import transcript_fixes as TF
    rows = MC.text_rows([_c(cid="t", kind="time", turn_t=10.0, payload={"t": 12.5})])
    T = TF.apply_tracks("2026-10-02", [{"start": 10.0, "end": 11.0, "speaker": "Medi", "text": "b"}], rows)
    assert T[0]["start"] == 12.5 and T[0]["end"] == 13.5 and T[0]["engine_start"] == 10.0


def test_pr_16_the_corrected_moment_is_never_counted_as_another_moment():
    # his sentence starts 06:46 (406.48) and runs to 428.64; the reader row sits at 07:02 inside it
    rows = [{"date": "2026-10-02", "t": "07:02", "kind": "vocab-A", "wrong": "سمعت", "signal": "recast", "uid": "FA-172fc4ea"}]
    c = _c(turn_t=406.48, target={"k": "vocab", "wrong": "سمعت", "signal": "recast", "src": "FA-172fc4ea"},
           payload={"reason": "not-correcting", "turn_end": 428.64})
    assert MC.propose([c], rows=rows, uses_=[])[0]["n"] == 0


def test_gr_27_laazem_straight_onto_a_thing_is_a_b2_clue_and_her_english_take_counts_as_her_fix():
    """GR-27 (Medi 2026-10-03 "you 'take' a day off, it cant be 3utle by itself")."""
    import echo_candidates as E
    T = [{"t": 575.8, "end": 577.0, "who": "Medi", "text": "أنا لازم"}, {"t": 578.26, "end": 580.0, "who": "Medi", "text": "آآآ عطلة و"},
         {"t": 581.27, "who": "Amal", "text": "لازم you should take."},
         {"t": 600.0, "who": "Medi", "text": "وأنا لازم كل اليوم، أطلبهم"}]
    c = E.laazem_noun(T)
    assert [x["thing"] for x in c] == ["عطلة"] and c[0]["amal_after"][0]["text"].endswith("take.")
    hand = MC.J(MC.HAND_P)["rows"]
    row = next(r for r in hand if r["id"] == "chat-20261003-laazem-3utle")
    rows = []
    MC.apply_rows(rows, [row], answers={}, turns=T, rules=[])
    assert rows[0]["kind"] == "grammar" and rows[0]["bucket"] == "B2" and rows[0]["signal"] == "recast"


def test_pg_25_a_missing_preposition_or_verb_is_a_caret_where_it_belongs():
    """PG-25 (Medi 2026-10-03 "maybe put one of these ^ la (preposition missing)"; "same here with the missing verb Ra7 ^aroo7")."""
    import transcript_marks as T
    assert T.missing_piece("خططت سفر", "خططت لسفرة") == {"before": "سفر", "add": "ل", "az": "la", "what": "preposition"}
    assert T.missing_piece("راح على", "راح أروح على")["before"] == "على" and T.missing_piece("راح على", "راح أروح على")["add"] == "أروح"
    assert T.missing_piece("أنا لازم آآآ عطلة", "أنا لازم آخد عطلة")["add"] == "آخد"
    assert T.missing_piece("سمعت", "صحيت") is None
    d = json.load(open(os.path.join(ROOT, "docs", "data", "lessons", "2026-10-02.json"), encoding="utf-8"))
    carets = [u for m in d["tmarks"].values() for u in m["u"] if u[2] == "missing"]
    assert any(u[5] == "ل" and u[6] == "la" for u in carets) and any(u[5] == "أروح" for u in carets)


def test_tr_23_his_arabic_in_english_letters_is_read_and_checked_against_her_chat_and_gemini_tests_it():
    """TR-23 (Medi 2026-10-03 "why no credit here ... this should be nenbisit"; "she even wrote it for you")."""
    import arabizi_reader as R
    import echo_candidates as E
    import context_transcribe as CT
    assert "ننبسط" in R.to_arabic("Rah nimbisit.") and "رح" in R.to_arabic("Rah nimbisit.")
    assert R.to_arabic("basically nobody") .strip(" .") == ""          # English stays English
    T = [{"t": 827.2, "who": "Medi", "text": "nimbisit."}, {"t": 850.0, "who": "chat", "text": "bas 5atibti ra7 tiji ma3i u ra7 nenbese6"}]
    c = E.chat_latin(T)
    assert c and c[0]["engine_wrote"] == "nimbisit" and c[0]["her_chat"] == "nenbese6"
    key = CT.answer_key()
    assert any(d == "2026-10-02" and abs(t - 827.2) < .01 and "ننبسط" in w for d, t, w, g, n in key)
