# -*- coding: utf-8 -*-
"""The fixes the two final approvals of the re-hear backfill asked for (2026-10-05):
data/lesson-work/rehear/reviews/codex-final-approval.md (7 blockers + required labels) and council-final-approval.md.
No network, no paid call. Each test names the blocker / condition it holds."""
import json, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import transcript_fixes as TF  # noqa: E402
import rehear_status as RH  # noqa: E402
import rehear_rejudge as RR  # noqa: E402
import apply_amal_audit_rulings as AAR  # noqa: E402

J = lambda *p: json.load(open(os.path.join(ROOT, *p), encoding="utf-8"))  # noqa: E731
SRC = lambda *p: open(os.path.join(ROOT, *p), encoding="utf-8").read()  # noqa: E731


# ---------------------------------------------------------------- Codex 1 / council 6: one text for pages and counter
def test_the_grammar_use_counter_and_the_console_read_the_lines_the_pages_show():
    for f in ("detect_grammar_usage.py", "build_grammar_console.py"):
        s = SRC("scripts", f)
        assert "page_lines(date)" in s and "lesson_turns(date)" not in s, f
        assert not re.search(r"^from lesson_turns import lesson_turns", s, re.M), f
    U = J("docs", "data", "grammar-usage.json")
    assert all("lesson page's lines" in (L.get("source") or "") for L in U["lessons"].values())
    # every use sits on a line of his that the lesson page shows, at that line's time, quoting that line's own text
    for d in sorted(U["lessons"]):
        turns = [t for t in J("docs", "data", "lessons", d + ".json")["turns"] if t["who"] == "Medi"]
        on_page = lambda u: any(abs(t["t"] - u["t"]) <= 0.06 and t["text"].startswith(u["said"][:300]) for t in turns)  # noqa: E731
        bad = [(b, u["t"]) for b, us in U["uses"].items() for u in us if u["date"] == d and not on_page(u)]
        assert not bad, (d, bad[:3])


def test_every_second_listen_span_on_the_page_reaches_the_counters_lines():
    A = J("data", "lesson-work", "rehear", "audit.json")
    for d, row in A["lessons"].items():
        tr = row.get("track_reach") or {}
        assert tr.get("spans") == tr.get("spans_reaching_track_turns"), (d, tr)      # was 8 of 253 on 09-10


def test_no_use_ruling_was_lost_when_the_counter_moved_to_the_page_lines():
    U = J("docs", "data", "grammar-usage.json")
    landed = {(r["date"], r["bucket"], r["mmss"]) for r in U["ruled_out"]}
    assert {("2026-09-21", "E5", "61:44"), ("2026-09-28", "A2", "32:17")} <= landed      # the two that landed before still do
    # the six others never met a counted use before either (the automatic rules / GR-11 already cover those moments):
    # none of them has a counted use within 3 s of its time now
    import detect_grammar_usage as D
    for r in D.load_rulings():
        if r.get("pattern") or (r["date"], r["bucket"]) in {(a, b) for a, b, _ in landed}:
            continue
        near = [u for u in U["uses"].get(r["bucket"], []) if u["date"] == r["date"] and abs(u["t"] - r["_t"]) <= 3.0]
        assert not near, (r["date"], r["t"], r["bucket"])


# ---------------------------------------------------------------- Codex 2: his own word stays (10-02 08:22)
def test_medis_relisten_row_keeps_his_word_and_the_second_listen_never_lands_on_that_line():
    rows = [r for r in TF.load(medi=False) if r.get("date") == "2026-10-02" and abs(float(r["t"]) - 502.9) < 0.01]
    pin = [r for r in rows if r.get("by") == "medi" and r.get("engine_wrote") == r.get("heard") == "الصباح"]
    assert len(pin) == 1 and pin[0]["quote"] == "08:22 el-saba7" and pin[0]["on"] == "2026-10-04"
    assert not [r for r in rows if r.get("by") == "gemini-rehear"]
    line = next(t for t in J("docs", "data", "lessons", "2026-10-02.json")["turns"] if abs(t["t"] - 502.9) < 0.01)
    assert line["text"] == "هادي الصباح." and all(h["engine_wrote"] != h["heard"] for h in line["heard"])
    slip = next(r for r in J("data", "full-audit-2026-09-26.json")["rows"] if r["uid"] == "FA-d3ecce97")
    assert slip["kind"] == "grammar" and slip["wrong"] == "هادي الصباح"                   # the published slip stands
    k = J("data", "lesson-work", "rehear", "audit.json")["recipe_on_medis_key_10_02"]
    assert k["slips_hidden_in_delivered_transcript"] == 0


def test_a_confirming_row_changes_nothing_but_blocks_the_whole_line_row():
    eng = {"t": 10.0, "who": "Medi", "text": "هادي الصباح."}
    pin = {"date": "D", "t": 10.0, "who": "Medi", "engine_wrote": "الصباح", "heard": "الصباح", "by": "medi"}
    gem = {"date": "D", "t": 10.0, "who": "Medi", "line": "هادي الصباح.", "heard_line": "هادي الصبح.", "by": "gemini-rehear",
           "spans": [{"engine_wrote": "الصباح.", "heard": "الصبح."}]}
    assert TF.apply("D", [eng], [gem])[0]["text"] == "هادي الصبح."                        # alone, the second listen lands
    out = TF.apply("D", [eng], [pin, gem])[0]
    assert out["text"] == "هادي الصباح." and "engine" not in out and not out.get("heard")   # his word stays; nothing is shown as changed
    assert TF.unmatched("D", [out], [pin]) == []
    import full_audit_build as FAB
    rows = [{"date": "D", "t": "00:10", "kind": "grammar", "wrong": "الصباح", "right": "الصبح"}]
    assert FAB.apply_misheard(rows, [pin]) == 0 and rows[0]["kind"] == "grammar"          # a confirming row drops no slip


# ---------------------------------------------------------------- required labels (Codex) / council 2, 3
def test_the_second_listen_marks_say_ai_agreement_and_name_the_mixed_recordings():
    assert list(RH.STATUS) == ["pending", "submitted", "proposed", "applied", "applied-limited"]
    label, tip = RH.STATUS["applied"]
    assert "agreed by 2 of 3 AI runs" in tip and "no person has checked" in tip and "Amal's lines are unchanged" in tip
    assert "reviewed" not in tip and "reviewed" not in RH.EXPLAIN
    label, tip = RH.STATUS["applied-limited"]
    assert label == "Second listen: limited (mixed recording)" and "Only alphabet-only changes were applied" in tip and "Word changes wait for a check" in tip
    doc = RH.load(ROOT)
    lim = sorted(d for d, r in doc["lessons"].items() if r["status"] == "applied-limited")
    assert lim == ["2026-08-25", "2026-09-04", "2026-09-18"]
    applied = 0
    for d, r in doc["lessons"].items():
        if r["status"] == "pending":                                     # 2026-10-07: 10-05 and 10-06 are on the list, not re-heard yet - no plan, no mark
            assert r["note"] == "" and not os.path.exists(os.path.join(ROOT, "data", "lesson-work", "rehear", d, "apply-plan.json")), d
            continue
        applied += 1
        P = J("data", "lesson-work", "rehear", d, "apply-plan.json")["summary"]
        assert "Amal's lines: unchanged" in r["note"], d
        if d in lim:
            assert ("%d word changes wait for a check" % (P["held_mix"] + P["held"])) in r["note"] and "your microphone" not in r["note"], d
        else:
            # 2026-10-07 (TR-27): the lines held for the tutor's ear count among the lines that wait (rehear_apply.status_row)
            assert "agreed by 2 of 3 AI runs" in r["note"] and ("%d lines wait" % (P["held"] + P["held_mix"] + P["no_agreement"] + P.get("withheld_by_spot_check", 0) + P.get("held_tutor", 0))) in r["note"], d
        # TR-27 (2026-10-07): what her listen decided is said in the mark, with its count, and only when there is something to say
        tut, out, on = P.get("held_tutor", 0), P.get("taken_out_by_tutor", 0), P.get("applied_by_tutor", 0)
        assert (("%d line%s wait for the tutor's ear" % (tut, "" if tut == 1 else "s")) in r["note"]) == bool(tut) and r.get("tutor_wait") == (tut or None), d
        assert (("%d change%s taken out on the tutor's word." % (out, "" if out == 1 else "s")) in r["note"]) == bool(out), d
        assert (("%d applied on the tutor's word." % on) in r["note"]) == bool(on), d
        assert "taken out again because a blind check" not in r["note"], d     # the blind spot check's lines were all answered by her (withheld_by_spot_check = 0)
    assert applied == 18
    # 09-18: the one applied line the stricter counter tags a word change is named (alphabet-only by the hold rule)
    assert "01:06" in doc["lessons"]["2026-09-18"]["note"] and "same word in the other alphabet" in doc["lessons"]["2026-09-18"]["note"]
    import rehear_lesson as RL
    assert RL.script_only("مهم.", "Mhm.") and not RL.script_only("like", "hate")


def test_the_method_change_is_marked_on_every_trend_view_and_never_called_an_improvement():
    L = J("docs", "data", "lessons.json")
    m = L["method_change"]
    assert m["date"] == "2026-10-05"
    assert m["text"] == ("From 2026-10-05 these numbers are counted on a second AI listen of your lines and a new read of every lesson; "
                         "earlier and later values are not comparable.")
    for txt in [m["text"], m.get("why", "")] + [v for st in RH.STATUS.values() for v in st] + [r.get("note", "") for r in RH.load(ROOT)["lessons"].values()]:
        assert not re.search(r"improv|better transcript|more accurate", txt, re.I), txt
    lm = SRC("docs", "js", "lesson-math.js")
    assert "function methodHtml(doc)" in lm and "function stampMethod(doc, anchor, where)" in lm and "doc.method_change" in lm
    for f, call in (("lessons-page.js", "stampMethod(DATA"), ("lesson-overview.js", "LM.stampMethod(L"), ("overview-angles.js", "methodHtml(LJ)"),
                    ("grammar-progress.js", "methodHtml(d.lj)"), ("vocabulary-progress.js", "LM.stampMethod(d")):
        s = SRC("docs", "js", f)
        assert call in s, f
        assert "2026-10-05 these numbers" not in s, f + ": the words come from the data, not the page code"


def test_grammar_pct_is_provisional_on_the_three_lessons_with_no_microphone_track():
    L = {x["date"]: x for x in J("docs", "data", "lessons.json")["lessons"]}
    why = "re-read, but the recording has no separate microphone track, so almost no line was re-heard"
    for d, x in L.items():
        prov = x["grammar"].get("provisional")
        if d in ("2026-08-25", "2026-09-04", "2026-09-18"):
            assert prov.startswith(why) and any(why in n for n in x["notes"]) and ("grammar % provisional: " + prov) in x["release"]["reasons"], d
        else:
            # 09-10 .. 09-23: the counter reads the delivered text now (blocker 1); the only flag a lesson may carry is round 4's
            assert prov is None or "come from the first read only" in prov, d
        assert x["release"]["status"] == "not verified", d       # "not verified" / the ≈ mark is kept on every lesson
    assert "g.provisional" in SRC("docs", "js", "lessons-page.js") and "gprov" in SRC("docs", "js", "lesson-overview.js")


# ---------------------------------------------------------------- Codex 3: the 28 silent credits are a visible state
def test_word_credits_the_second_listen_no_longer_hears_are_listed_and_not_scored():
    # 2026-10-07 (TR-27): Amal answered all 28 "is this word really there?" cards, so no credit waits in the visible
    # state any more - each is settled by her word (data/lesson-work/ledger-tutor-listen.json, read by scripts/lesson_ledger.py)
    import lesson_ledger as LL
    W = J("data", "lesson-work", "rehear", "rejudge", "word-credit-conflicts.json")
    assert W["count"] == len(W["rows"]) == 0
    T = J("data", "lesson-work", "ledger-tutor-listen.json")["rulings"]
    assert len(T) == 28 and all(r["rule"] == "TR-27" and r["by"] == "amal" and r["list"] == "word-there" and r["conflict"] == "wb:" + r["event_id"] for r in T)
    assert sorted(r["answer"] for r in T).count("yes") == 13 and sum(r["answer"] == "no" for r in T) == 14 and sum(r["answer"] == "not_sure" for r in T) == 1
    assert all(r["conflict"] in LL.load_rulings() for r in T)                                # her answers reach the ledger's rulings
    L = {x["date"]: x for x in J("docs", "data", "lessons.json")["lessons"]}
    by = {}
    for r in T:
        by.setdefault(r["date"], []).append(r)
    moved = 0
    for d, x in L.items():
        assert x["words"].get("rehear_word_conflicts", 0) == 0, d
        led = J("data", "lesson-work", "ledger", d + ".json")
        marks = {m["id"]: m for m in led["marks"]}
        assert not [m for m in led["marks"] if m.get("state") == LL.REHEAR_CONFLICT], d       # the waiting state is empty
        tl = [m for m in led["marks"] if m.get("state") == "tutor-listened"]
        for m in tl:                                                                            # a removed credit: not scored, her reason, her rule
            assert m["verdict"] == "not-scored" and m["why_by"] == "TR-27" and m["why"].startswith("the tutor listened:") and m["was"] in ("right", "partial", "wrong"), (d, m["id"])
            assert marks[m["id"]] is m and any(r["conflict"] == m["id"] and r["answer"] in ("no", "not_sure") for r in by.get(d, [])), (d, m["id"])
        moved += len(tl)
        turns = J("docs", "data", "lessons", d + ".json")["turns"]
        for r in by.get(d, []):
            m = marks[r["conflict"]]
            if r["answer"] == "yes":                                                            # the credit stands, scored as it was
                assert m["verdict"] in ("right", "partial", "wrong") and m.get("state") is None, (d, r["word"])
            elif m.get("state") != "tutor-listened":
                # her "no" on a line whose change was since taken out: the word is back on his delivered line, so there is no conflict to settle
                doc = [m.get("arabic")] if m["verdict"] in ("right", "partial") else None
                assert m["turn"] is not None and LL.still_on_line(m.get("tok"), turns[m["turn"]]["text"], doc), (d, r["word"])
        assert not [m for m in led["marks"] if m.get("rehear_note") and m["verdict"] in ("right", "partial", "wrong") and led.get("resolve")], d
    over = J("docs", "data", "word-bank-audit-slips.json")["overrides"]
    assert not [o for o in over if (o.get("changes") or {}).get("rehear_hold")]
    tut = [o for o in over if (o.get("changes") or {}).get("tutor_listened")]
    assert len(tut) == moved == 12 and all(o["changes"]["ledger"] == o["mark"] and "(TR-27)" in o["changes"]["ledger_reason"] for o in tut)
    src = SRC("scripts", "lesson_ledger.py")
    assert 'state="tutor-listened"' in src and 'why_by="TR-27"' in src and '"tutor_listened": True' in src


# ---------------------------------------------------------------- council 5 / Codex 6: Amal's confirmations
def test_amals_confirmation_is_recorded_on_a_row_the_readers_now_score_themselves():
    r = {"uid": "FA-x", "kind": "grammar", "signal": "recast", "confidence": "low"}
    ru = {"id": 1935, "created_at": "2026-09-30T17:54:18+00:00", "kind": "audit_confirm"}
    assert AAR.confirm_scored_row(r, ru, "p-el-missing-known-thing")
    assert r["kind"] == "grammar" and r["signal"] == "recast"                               # the readers' judgment is untouched
    assert r["amal_ruling"] == {"kind": "confirm", "pattern": "p-el-missing-known-thing", "at": ru["created_at"], "rule_id": 1935,
                                "before": {"kind": "grammar", "signal": "recast", "confidence": "low"}, "on_scored_row": True}
    assert not AAR.confirm_scored_row(r, ru, "p")                                           # once
    assert not AAR.confirm_scored_row({"kind": "grammar-B"}, ru, "p") and not AAR.confirm_scored_row({"kind": "rejected"}, ru, "p")
    AAR.revert_row(r, {"id": 9, "created_at": "2026-10-06"}, "now")                         # her Undo takes it off again, history kept
    assert "amal_ruling" not in r and r["kind"] == "grammar" and r["amal_ruling_undone"][0]["rule_id"] == 1935


def test_the_three_confirmations_that_were_not_back_are_back_on_the_slip_she_confirmed():
    rows = {r["uid"]: r for r in J("data", "full-audit-2026-09-26.json")["rows"]}
    a = rows["FA-cca6494e"]                                   # 09-23 25:24: the same slip, scored, with her confirmation on it
    # 2026-10-07: the re-read on the final text filed this row as a B question again, so her confirmation (not the
    # readers' own score) is what makes it count - the ruling's `before` says so instead of on_scored_row
    assert a["kind"] == "grammar" and a["wrong"] == "ما بحب فول" and a["amal_ruling"]["kind"] == "confirm"
    assert a["amal_ruling"].get("on_scored_row") or a["amal_ruling"]["before"]["kind"] == "grammar-B"
    b, c = rows["FA-9ebdf05d"], rows["FA-5ded86b4"]          # 09-04 26:19 / 09-10 12:53: kept as the slips SHE confirmed
    assert b["kept"] and b["wrong"] == "ashan" and b["amal_ruling"]["kind"] == "confirm"
    assert c["kept"] and c["wrong"] == "عشان يكون" and c["amal_ruling"]["kind"] == "confirm"
    rep = J("data", "lesson-work", "rehear", "rejudge", "report.json")
    assert not [y for x in rep["lessons"].values() for y in x["amal"]["ruling_not_back"]]


def test_a_uid_amal_ruled_on_is_carried_only_onto_the_same_slip():
    old = {"uid": "FA-old", "t": "12:53", "kind": "grammar", "wrong": "عشان يكون", "right": "عشان في / عشان عندي", "amal": "confirmed"}
    other = {"t": "12:53", "kind": "grammar", "wrong": "على بيتي", "right": "في بيتي", "read_key": "FA-n1", "uid": "FA-n1"}
    assert not RR.same_slip(old, other)                                                     # a shared في is not the same fix
    assert not RR.same_slip({"wrong": "mashufeta", "right": "ma shufetha"}, {"wrong": "الأسبوع ماضي", "right": "الأسبوع الماضي"})
    ent, _ = RR.carry_entries([old], [other])
    assert ent == [] and RR.carry_entries.not_carried[0]["old_uid"] == "FA-old"
    ent, _ = RR.carry_entries([dict(old, amal=None)], [other])                              # nobody's word on it: the moment still carries
    assert [e["old_uid"] for e in ent] == ["FA-old"]
    C = J("data", "lesson-work", "full-audit", "uid-carry.json")
    # rounds 3 and 4: every ruled uid whose re-read row is not the same wrong piece AND the same fix is left un-carried
    nc = {x["old_uid"] for v in C["not_carried_amal_ruled_another_slip"].values() for x in v}
    carried = {e["old_uid"] for v in C["lessons"].values() for e in v}
    assert nc and not nc & carried
    # 2026-10-07: after the re-read on the final text no re-read row sits near these five any more, so they are not
    # "another slip at the moment" (not listed) - still un-carried: the three she confirmed are kept as her slips, the
    # two she rejected are gone with a cause (their line changed, the piece is not on it)
    before = {r["uid"]: dict(r, date=d) for d, x in J("data", "lesson-work", "rehear", "rejudge", "before.json")["lessons"].items() for r in x["rows"]}
    audit = {r["uid"]: r for r in J("data", "full-audit-2026-09-26.json")["rows"]}
    cause = {r["uid"]: r for r in J("data", "lesson-work", "rehear", "rejudge", "removed-rows-by-cause.json")["removed"]}
    for u in ("FA-5ded86b4", "FA-622f7da5", "FA-65623974", "FA-9ebdf05d", "FA-bc203430"):
        assert u not in carried and before[u]["amal"] in ("confirmed", "rejected"), u
        if before[u]["amal"] == "confirmed":
            assert audit[u]["kept"] == RR.KEPT_MARK and audit[u]["wrong"] == before[u]["wrong"], u
        else:
            assert u not in audit and cause[u]["cause"] == "2" and cause[u]["line_changed"] and cause[u]["wrong_piece_gone_from_line"], u
    assert all(before[u]["amal"] for u in nc)                                              # the listed ones are all ruled uids


def test_every_orphaned_reference_has_one_disposition():
    D = J("data", "lesson-work", "rehear", "rejudge", "orphan-dispositions.json")
    rep = J("data", "lesson-work", "rehear", "rejudge", "report.json")
    want = {(k, u) for k, v in rep["orphaned"].items() for u in v}
    have = {(x["reference"], x["uid"]) for x in D["rows"]}
    assert want <= have, sorted(want - have)[:5]
    for x in D["rows"]:
        assert x["disposition"] in ("mapped", "retired") and x["why"], x
        assert (x["disposition"] == "mapped") == bool(x.get("mapped_to")), x


# ---------------------------------------------------------------- Codex 5: every removed row has a cause
def test_every_removed_and_added_row_is_classified_by_cause():
    D = J("data", "lesson-work", "rehear", "rejudge", "removed-rows-by-cause.json")
    rep = J("data", "lesson-work", "rehear", "rejudge", "report.json")
    removed = sum(x["removed"] for x in rep["lessons"].values())
    added = sum(x["added"] for x in rep["lessons"].values())
    # 2026-10-07: the report also lists the two lessons that came after the snapshot (10-05, 10-06: every row "added");
    # attribution classifies the rows added to the 18 snapshotted lessons only, so added = report's added minus those
    snap = set(J("data", "lesson-work", "rehear", "rejudge", "before.json")["lessons"])
    after_snapshot = {d: x["added"] for d, x in rep["lessons"].items() if d not in snap}
    assert sorted(after_snapshot) == ["2026-10-05", "2026-10-06"] and all(x["rows_before"] == 0 and x["added"] == x["rows_after"] for d, x in rep["lessons"].items() if d not in snap)
    assert set(D["per_lesson"]) == snap
    assert len(D["removed"]) == removed == D["totals"]["removed"] and len(D["added"]) == added - sum(after_snapshot.values()) == D["totals"]["added"]
    assert D["totals"]["added"] == sum(x["added"] for d, x in rep["lessons"].items() if d in snap)
    assert all(r["cause"] in ("1", "2", "3", "4", "c") for r in D["removed"]) and all(r["on"] in ("a", "b") for r in D["added"])
    assert sum(D["totals"]["cause_" + k] for k in "1234c") == removed
    assert all(r["passes"] == [2] for r in D["removed"] if r["cause"] == "1")
    assert all(r["line_changed"] and r["wrong_piece_gone_from_line"] for r in D["removed"] if r["cause"] == "2")
    assert "## Removed and added rows, by cause" in SRC("data", "lesson-work", "rehear", "rejudge", "report.md")


# ---------------------------------------------------------------- Codex 4: the 14 late merges, one by one
def test_the_late_merges_of_the_last_build_were_each_re_validated():
    M = J("data", "lesson-work", "rehear", "rejudge", "merge-review.json")
    # 2026-10-07: the readers re-read the 17 changed lessons on the final text, so the old rule's late pairs are 8 now (14 on
    # 10-05); each still has its evidence, and the hand reading of 10-05 stays on every pair that still exists (merge-review-hand.json)
    hand = J("data", "lesson-work", "rehear", "rejudge", "merge-review-hand.json")["rows"]
    assert len(M["rows"]) == 8 and M["merged"] + M["now_split"] == 8 and M["merged"] == 7
    for x in M["rows"]:
        assert x["result"] in ("merged", "now split") and x["why"], x["date"]
        assert x["read_by_hand"] == hand.get("%s|%s" % (x["date"], x["sweep_row"]["sweep_id"])), (x["date"], x["mmss"])
        if x["result"] == "merged":
            assert re.search(r"same rule|same wrong piece|same right piece|same word from Amal|two alphabets|same piece", x["why"]), x["why"]
    assert sum(1 for x in M["rows"] if x["read_by_hand"]) == 4


# ---------------------------------------------------------------- council 4: the owner's override is written down
def test_the_owners_override_of_runbook_step_20_is_recorded():
    s = SRC("plan", "REHEAR-REJUDGE-RUNBOOK-2026-10-04.md")
    assert "put anything that needs to be checked in the tutor portal, i will" in s and "a report, not a" in s
    assert "its exit code no longer blocks" in s


# ================================================================ Codex round 2 (codex-final-approval-round2.md)
# ---------------------------------------------------------------- 1: spot-check failures are not delivered
def test_a_line_the_blind_spot_check_judged_against_is_not_applied():
    # 2026-10-07 (TR-27): Amal answered all 11 "old or new line?" cards, so no line is withheld on the spot check's word any
    # more - each is applied or taken out on hers: 6 "the new line" = applied, 3 "the old line" + 2 "something else" = out
    want = {"2026-09-11": 2, "2026-09-21": 6, "2026-10-01": 3}
    fixes = [r for r in TF.load(medi=False) if r.get("by") == "gemini-rehear"]
    answers = []
    for d, n in want.items():
        P = J("data", "lesson-work", "rehear", d, "apply-plan.json")
        spot = {int(i) for i, v in J("data", "lesson-work", "rehear", d, "spot.json")["lines"].items() if v["verdict"] == "old text"}
        assert len(spot) == n and P["withheld_by_spot_check"] == [] and P["summary"]["withheld_by_spot_check"] == 0, d
        out = {x["i"]: x for x in P["taken_out_by_tutor"] if x.get("list") == "old-new"}
        on = {x["i"]: x for x in P["applied_by_tutor"] if x.get("list") == "old-new"}
        assert set(out) | set(on) == spot and not set(out) & set(on), d                        # every spot-check line has her answer, one each
        turns = J("docs", "data", "lessons", d + ".json")["turns"]
        for x in out.values():                                                                   # her "old" / "something else": the engine's line stays
            assert x["was"] == "spot" and x["answer"]["choice"] in ("old", "other"), (d, x["mmss"])
            assert not [r for r in P["rows"] if r["i"] == x["i"]] and not [y for y in P["lines_changed"] if y["i"] == x["i"]], (d, x["mmss"])
            assert not [r for r in fixes if r["date"] == d and abs(float(r["t"]) - x["t"]) < 0.01], (d, x["mmss"])
            assert turns[x["i"]]["text"] == x["engine"] and "engine" not in turns[x["i"]], (d, x["mmss"])   # the old line is what the page delivers
        for x in on.values():                                                                    # her "new": the re-heard line is delivered, shown as changed
            assert x["was"] == "spot" and x["answer"]["choice"] == "new", (d, x["mmss"])
            assert [r for r in P["rows"] if r["i"] == x["i"]] and [y for y in P["lines_changed"] if y["i"] == x["i"]], (d, x["mmss"])
            assert [r for r in fixes if r["date"] == d and abs(float(r["t"]) - x["t"]) < 0.01], (d, x["mmss"])
            stop = lambda s: re.sub(r"[\s.,،؟?!]+$", "", s)  # noqa: E731                              # the page keeps the line's final stop / comma
            assert stop(turns[x["i"]]["text"]) == stop(x["heard"]) and stop(turns[x["i"]]["engine"]) == stop(x["engine"]), (d, x["mmss"])
        answers += [x["answer"]["choice"] for x in list(out.values()) + list(on.values())]
        note = RH.load(ROOT)["lessons"][d]["note"]
        s = P["summary"]
        assert "taken out again because a blind check" not in note, d
        assert ("%d lines wait" % (s["held"] + s["held_mix"] + s["no_agreement"] + s["held_tutor"])) in note, d
        assert ("%d changes taken out on the tutor's word." % len(P["taken_out_by_tutor"])) in note and ("%d applied on the tutor's word." % len(P["applied_by_tutor"])) in note, d
    assert sorted(answers) == ["new"] * 6 + ["old"] * 3 + ["other"] * 2
    src = SRC("scripts", "rehear_apply.py")
    assert '"withheld_by_spot_check"' in src and 'verdict") == "old text"' in src             # the hold itself is still in the code
    W = J("data", "lesson-work", "rehear", "rejudge", "spot-withheld.json")
    assert W["lines"] == 0 and W["withheld"] == [] and W["audit_rows_quoting_only_the_reheard_text"] == []


# ---------------------------------------------------------------- 3: the same correction, not shared consonants
def test_a_ruled_uid_is_not_carried_from_katab_onto_kaateb_with_another_fix():
    old = {"uid": "FA-old", "t": "10:00", "kind": "grammar", "wrong": "katab", "right": "katabt", "amal": "confirmed"}
    new = {"t": "10:00", "kind": "grammar", "wrong": "كاتب", "right": "الكاتب", "read_key": "FA-n", "uid": "FA-n"}
    assert RR._two_alphabets("katab", "كاتب") and not RR._same_word_two_alphabets("katab", "كاتب") and not RR.same_words("katab", "كاتب")
    assert not RR.same_slip(old, new) and not RR.same_slip(dict(old, right=None), new)
    ent, _ = RR.carry_entries([old], [new])
    assert ent == [] and RR.carry_entries.not_carried[0]["old_uid"] == "FA-old"
    assert RR.removal_reason(old, [new], None) is None                                                  # nor is it "the same slip elsewhere"
    # the same wrong piece AND a compatible fix: carried
    same = dict(new, wrong="كتب", right="كتبت")
    assert RR.same_slip(old, same) and [e["old_uid"] for e in RR.carry_entries([old], [same])[0]] == ["FA-old"]
    assert not RR.same_slip({"wrong": "عنده", "right": "فيها"}, {"wrong": "عنده", "right": None})       # round 3: both fixes must be there
    assert not RR.same_slip({"wrong": "عنده", "right": "فيها"}, {"wrong": "عنده", "right": "عندها"})    # same words, another fix


# ---------------------------------------------------------------- 2: a scored slip leaves only for a reason
def test_kept_plan_restores_a_scored_row_unless_its_line_changed_or_its_slip_is_elsewhere():
    def old(uid, t, wrong, right, line, **k):
        return {"uid": uid, "t": t, "kind": "grammar", "wrong": wrong, "right": right, "line_before": line, "passes": [1], **k}
    rows = [old("FA-a", "01:00", "عنده مي", "فيها مي", "عنده مي كتير"),                 # words still on the line, nobody wrote it: restored
            old("FA-b", "02:00", "جو", "الجو", "جو كتير"),                               # his line changed, the piece is gone: stays out
            old("FA-c", "03:00", "هو راح", "هي راحت", "هو راح"),                         # the same correction is on another row: stays out
            old("FA-d", "04:00", "بيت كبير", "البيت الكبير", "بيت كبير", kind="grammar-B"),   # never counted: listed
            old("FA-e", "05:00", "أنا كان", "أنا كنت", "أنا كان", passes=[2])]           # retired pass only, still on the line: restored
    turns = [{"t": 60.0, "who": "Medi", "text": "عنده مي كتير"}, {"t": 120.0, "who": "Medi", "text": "شوب كتير"},
             {"t": 180.0, "who": "Medi", "text": "هو راح"}, {"t": 240.0, "who": "Medi", "text": "بيت كبير"}, {"t": 300.0, "who": "Medi", "text": "أنا كان"}]
    new = [{"uid": "FA-n", "date": "D", "t": "03:02", "kind": "grammar", "wrong": "هو راح", "right": "هي راحت"}]
    pres, lst = RR.kept_plan({"D": {"rows": rows}}, {"D": new}, lambda d: turns)
    assert [p["uid_keep"] for p in pres] == ["FA-a", "FA-e"] and all(p["kept"] == RR.RESTORED_MARK and p["kind"] == "grammar" for p in pres)
    assert [x["uid"] for x in lst["restored_first_read"]] == ["FA-a", "FA-e"] and lst["restored_per_lesson"] == {"D": 2}
    assert [x["uid"] for x in lst["unscored_not_rewritten"]] == ["FA-d"]
    assert RR.removal_reason(dict(rows[1], date="D"), new, "شوب كتير")[0] == "a" and RR.removal_reason(dict(rows[2], date="D"), new, "هو راح")[0] == "b"


def test_no_formerly_scored_row_left_the_audit_without_a_reason():
    D = J("data", "lesson-work", "rehear", "rejudge", "removed-rows-by-cause.json")
    scored = [r for r in D["removed"] if r["was_scored"]]
    # (a) his line changed and the piece is gone = 2, (b) the same correction on another row = 4, (c) ruled out by Amal = c
    assert scored and all(r["cause"] in ("2", "4", "c") for r in scored), [(r["date"], r["uid"], r["cause"]) for r in scored if r["cause"] not in ("2", "4", "c")][:5]
    assert all(r["amal"] == "rejected" for r in scored if r["cause"] == "c")
    assert D["totals"]["scored_cause_1"] == D["totals"]["scored_cause_3"] == 0
    K = J("data", "lesson-work", "rehear", "rejudge", "kept-rows.json")
    audit = {r["uid"]: r for r in J("data", "full-audit-2026-09-26.json")["rows"]}
    before = {r["uid"]: r for x in J("data", "lesson-work", "rehear", "rejudge", "before.json")["lessons"].values() for r in x["rows"]}
    R = K["restored_first_read"]
    assert len(R) == sum(K["restored_per_lesson"].values()) == D["totals"]["restored_first_read"] > 0
    for x in R:
        r = audit[x["uid"]]
        assert r["kept"] == RR.RESTORED_MARK and r["wrong"] == before[x["uid"]]["wrong"] and r["right"] == before[x["uid"]]["right"], x["uid"]
        # as it was scored before - unless Amal's own tap has since ruled it out (c): then it stays, rejected, with her reason
        # 2026-10-07 (TR-27 / LS-16): or her "one mistake or two?" answer made it the twin of another row - rejected as its
        # duplicate, the pair written in duplicates.json by tutor-listen with her words as the reason
        if r["kind"] != before[x["uid"]]["kind"]:
            assert r["kind"] == "rejected", x["uid"]
            if (r.get("amal_ruling") or {}).get("kind") != "drop":
                p = next(p for p in J("data", "lesson-work", "full-audit", "duplicates.json")["pairs"] if p["drop"] == x["uid"])
                assert p["by"] == "tutor-listen" and p["rule"] == "LS-16" and p["keep"] == r["duplicate_of"] and "the tutor's answer" in p["why"], x["uid"]
                assert r["duplicate_of"] in audit and audit[r["duplicate_of"]]["kind"] != "rejected", x["uid"]
    assert all(not RR.was_scored(before[x["uid"]]) for x in K["unscored_not_rewritten"])
    # no restored row doubles a row of the re-read: none has the same correction within 30 s on another row
    by = {}
    for r in audit.values():
        by.setdefault(r["date"], []).append(r)
    dbl = [(x["date"], x["uid"]) for x in R for n in by[x["date"]]
           if n["uid"] != x["uid"] and not n.get("kept") and RR._class_ok(audit[x["uid"]], n) and RR._dt(audit[x["uid"]], n) <= RR.REPEAT_S and RR.same_slip(audit[x["uid"]], n)]
    assert not dbl, dbl[:5]


# ================================================================ Codex round 3 (codex-final-approval-round3.md)
# ---------------------------------------------------------------- 1: a slip on a withheld wording is not scored
def test_a_row_whose_wrong_piece_exists_only_in_a_withheld_line_is_not_scored_until_medi_adjudicates():
    import full_audit_build as FAB
    W = {"D": [{"t": 1477.0, "mmss": "24:37", "engine": "ما credit card", "heard": "مع credit card"}]}
    rows = [{"uid": "a", "date": "D", "t": "24:38", "kind": "grammar", "bucket": "D1", "wrong": "مع credit card", "right": "بالـ credit card"},
            {"uid": "b", "date": "D", "t": "24:34", "kind": "grammar", "wrong": "أدفع أطفالهم", "right": "أدفع بالـ credit card", "medi_said": "أدفع أطفالهم مع credit card"},
            {"uid": "c", "date": "D", "t": "24:38", "kind": "grammar", "wrong": "credit card", "right": "الكرت"},       # on the delivered line too
            {"uid": "d", "date": "D", "t": "30:00", "kind": "grammar", "wrong": "مع credit card", "right": "x"},        # another moment
            {"uid": "e", "date": "E", "t": "24:38", "kind": "grammar", "wrong": "مع credit card", "right": "x"}]        # another lesson
    assert FAB.apply_withheld(rows, W) == 1
    a = rows[0]
    assert a["uid"] == "a" and a["kind"] == "rejected" and a["kind_before_rejection"] == "grammar" and a["rejected_rule"] == "TR-22"
    assert a["wrong"] == "مع credit card" and a["right"] == "بالـ credit card" and a["bucket"] == "D1"            # the row itself is unchanged
    assert "withheld on 2026-10-05" in a["rejected_why"] and "not scored until Medi adjudicates the line (old or new)" in a["rejected_why"]
    assert [r["kind"] for r in rows[1:]] == ["grammar"] * 4
    assert FAB.apply_withheld([dict(rows[3], t="24:38", kind="grammar")], {}) == 0                                 # adjudicated (no longer withheld): it counts again
    # the real row. On 2026-10-05 the 09-21 24:37 line (engine 'ما credit card', re-heard 'مع credit card') was withheld on the
    # blind spot check and the slip on it (then FA-a36f7b0e) was held by this rule. 2026-10-07 (TR-27): Amal listened and
    # chose the new line, so it is applied on her word, the wrong piece is on the delivered line, and the slip counts again
    # under the uid it had as a scored row (FA-99795002); nothing is withheld on the spot check's word any more
    rows = J("data", "full-audit-2026-09-26.json")["rows"]
    assert not [x for x in rows if x.get("rejected_rule") == "TR-22" and "withheld" in (x.get("rejected_why") or "")]
    assert not [x for x in rows if x.get("withheld_line")]
    P = J("data", "lesson-work", "rehear", "2026-09-21", "apply-plan.json")
    line = next(x for x in P["applied_by_tutor"] if x["mmss"] == "24:37")
    assert line["was"] == "spot" and line["list"] == "old-new" and line["answer"]["choice"] == "new" and line["engine"] == "ما credit card" and line["heard"] == "مع credit card"
    turn = next(t for t in J("docs", "data", "lessons", "2026-09-21.json")["turns"] if abs(t["t"] - line["t"]) < 0.01)
    assert turn["text"] == "مع credit card" and turn["engine"] == "ما credit card" and [(h["engine_wrote"], h["heard"]) for h in turn["heard"]] == [("ما", "مع")]
    r = next(x for x in rows if x["uid"] == "FA-99795002")
    assert r["kind"] == "grammar" and r["date"] == "2026-09-21" and r["t"] == "24:38" and r["wrong"] == "مع credit card" and r["right"] == "بالـ credit card"
    assert not r.get("rejected_rule") and not r.get("kind_before_rejection")
    L = J("docs", "data", "lessons", "2026-09-21.json")
    assert r["uid"] in [g["id"] for g in L["grammar_errors"]]
    assert "apply_withheld(rows, carry=carry)" in SRC("scripts", "full_audit_build.py")
    # the uid is the one the row had as a scored row
    keep = [{"date": "D", "t": "24:38", "kind": "grammar", "wrong": "مع credit card", "right": "x", "read_key": "FA-own"}]
    FAB.apply_withheld(keep, W, carry={"FA-own": "FA-carried"})
    assert FAB.assign_uids(keep)[0]["uid"] == "FA-carried"


# ---------------------------------------------------------------- 2 + 3: the same words, no fallbacks
def test_same_slip_has_no_bypass_codex_round_3_and_4_counterexamples():
    at = lambda t, w, r, **k: {"t": t, "kind": "grammar", "wrong": w, "right": r, **k}  # noqa: E731
    # round 3 (1): shared consonants + a matching fix
    assert not RR.same_slip(at("10:00", "katab", "katabt"), at("10:00", "كاتب", "كتبت"))
    # round 4: alike spellings + the identical fix at the same second (the 60 % similarity path) - gone
    assert not RR.same_words("katab", "kasab") and not RR.same_slip(at("10:00", "katab", "katabt"), at("10:00", "kasab", "katabt"))
    old = dict(at("10:00", "katab", "katabt"), uid="FA-old", amal="confirmed", line_before="x")
    new = dict(at("10:00", "kasab", "katabt"), uid="FA-n", read_key="FA-n")
    assert RR.carry_entries([old], [new])[0] == [] and RR.removal_reason(old, [new], "x") is None      # no ruled carry, no duplicate removal
    assert not RR.same_slip(at("59:45", "انبسطي يومك", "انبسطي بيومك"), at("59:45", "Investii yomek", "inbesti bi-yomek"))   # the 09-04 special case is gone too
    # round 3 (3): FA-5ba734f4 (a missing preposition) is not FA-aa03ebc5 (a past-tense ending)
    o, n = at("06:33", "(missing في)", "انبسطتي في", bucket="D2"), at("06:17", "en-enbistee", "انبسطتي", bucket="B5")
    assert not RR.same_slip(o, n) and RR.removal_reason(dict(o, uid="FA-5ba734f4", line_before="x"), [dict(n, uid="FA-aa03ebc5")], "x") is None
    # overlap and substring are not the same words; a missing side is never "compatible"
    assert not RR.same_words("جديد", "لغة جديد") and not RR.same_words("عشان في", "في بيتي")
    assert not RR.same_slip(at("1:00", "عنده", None), at("1:00", "عنده", "فيها")) and not RR.same_slip(at("1:00", None, "مفروم"), at("1:00", "معروف", "مفروم"))
    assert RR.same_slip(at("1:00", "عنده مي", "فيها مي"), at("1:02", "عنده مي.", "فيها مي (my reading)"))       # the same words: punctuation and a reader's note aside
    assert RR.same_slip(at("1:00", "el akil mufaddal", "el-akel el-mufaddal"), at("1:00", "الأكل مفضل", "الأكل المفضل"))   # the strict rule, word by word
    src = SRC("scripts", "rehear_rejudge.py")
    body = src[src.index("def same_words(a, b):"):src.index("def maybe_same_slip_loose(o, n):")]
    for banned in ("sim(", "_same_consonants(", "same_piece(", ">= 0.", "_dt(", "right_ok"):
        assert banned not in body, banned
    assert not re.search(r"(?<![a-z])_two_alphabets\(", body)
    # the loose detector exists for ONE label and nothing that decides a uid, a removal or a restore calls it
    for fn in ("def carry_entries(", "def removal_reason(", "def kept_plan(", "def attribution("):
        k = src.index(fn)
        assert "maybe_same_slip_loose" not in src[k:src.index("\ndef ", k + 10)], fn


# the test's OWN comparison - it shares no code with scripts/rehear_rejudge.py, so a permissive matcher cannot pass it
def _tok(x):
    import unicodedata
    x = re.sub(r"\([^)]*\)", " ", str(x or ""))                       # a reader's bracketed note is not his or her words
    x = unicodedata.normalize("NFC", x)
    x = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", x)                  # marks and the stretch
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ى", "ي")):
        x = x.replace(a, b)
    return re.sub(r"[^\w\s]", " ", x.lower()).split()


# the cross-alphabet pairs, read by hand (old piece, new piece): the same words in the two alphabets
SAME_BY_HAND = {
    ("nabasat", "نبسط (past)"), ("inbasat", "انبسط"), ("Kam sawar", "كم صُوَر"), ("kam soora", "كم صورة"),
    ("it zakarooni", "اتذكّروني"), ("ma tzakkaruni", "ما تذكّروني"), ("behamsni", "بيحمسني"), ("hamasni (7ammasni)", "حمّسني"),
    ("ala andik", "على عندك"), ("3indek", "عندك"), ("kharabti", "خربتي"), ("kharabtihom", "خربتيهم"), ("Taghiri", "تغيّري"),
    ("ghayiri", "غيّري"), ("khuffetilik", "خفتلك"), ("khuffet aleiki (5ufet 3alaik)", "خفت عليكي"), ("عصبولنا", "asabulna"),
    ("mina", "منّا"), ("alaina (3alaina)", "علينا"), ("shu huwa", "شو هو"), ("ili (illi)", "اللي"), ("لما أنا كسول", "lama ana kasul"),
    ("sawa", "سوى"), ("sawwaah", "سوّى"), ("el akil mufaddal", "الأكل مفضل"), ("el-akel el-mufaddal", "الأكل المفضل"),
    ("khali", "خلّي"),      # 2026-10-07: the re-read on the final text wrote 09-15 11:31 in Arabic (khalli = خلّي, the bare form for 'I make')
}


def _independent_same(o, n):
    eq = lambda a, b: bool(_tok(a)) and (_tok(a) == _tok(b) or (str(a), str(b)) in SAME_BY_HAND)  # noqa: E731
    wo = [w for w in (o.get("wrong"), o.get("wrong_before_gr25"), o.get("wrong_before_medi")) if _tok(w)]
    wn = [w for w in (n.get("wrong"), n.get("wrong_before_gr25"), n.get("wrong_before_medi")) if _tok(w)]
    if not eq(o.get("right"), n.get("right")):
        return False
    return (not wo and not wn) or any(eq(a, b) for a in wo for b in wn)


def test_independent_strict_comparison_rejects_what_the_old_matcher_let_through():
    g = lambda w, r: {"wrong": w, "right": r}  # noqa: E731
    assert not _independent_same(g("katab", "katabt"), g("kasab", "katabt")) and not _independent_same(g("katab", "katabt"), g("كاتب", "كتبت"))
    assert not _independent_same(g("(missing في)", "انبسطتي في"), g("en-enbistee", "انبسطتي")) and not _independent_same(g("جديد", "جديدة"), g("لغة جديد", "لغة جديدة"))
    assert _independent_same(g("عنده مي", "فيها مي"), g("عنده مي.", "فيها مي (my reading)"))


def test_every_ruled_carry_and_every_same_slip_removal_passes_the_independent_comparison():
    """Codex round 4: these assertions do not call the matcher. Every "same correction on another row" removal and every
    carry of a uid Amal ruled on must be the same wrong piece AND the same fix by _independent_same (token equality, or a
    pair listed by hand in SAME_BY_HAND)."""
    before = {r["uid"]: dict(r, date=d) for d, x in J("data", "lesson-work", "rehear", "rejudge", "before.json")["lessons"].items() for r in x["rows"]}
    audit = {r["uid"]: r for r in J("data", "full-audit-2026-09-26.json")["rows"]}
    D = J("data", "lesson-work", "rehear", "rejudge", "removed-rows-by-cause.json")
    # 2026-10-07 (LS-16, tutor-listen): a pair the tutor herself called "the same mistake" on her one-or-two list is the
    # same slip by her word (the two rows write it in the two alphabets, which token equality cannot see); her pair must
    # name exactly these two rows, the surviving one as the kept row
    tutor = {p["drop"]: p for p in J("data", "lesson-work", "full-audit", "duplicates.json")["pairs"] if p.get("by") == "tutor-listen"}
    same_by_tutor = lambda r: r["uid"] in tutor and tutor[r["uid"]]["keep"] == r["same_slip_now_on"] and tutor[r["uid"]]["rule"] == "LS-16"  # noqa: E731
    bad = [(r["date"], r["uid"], r["same_slip_now_on"]) for r in D["removed"] if r["cause"] == "4"
           and not (_independent_same(before[r["uid"]], audit[r["same_slip_now_on"]]) or same_by_tutor(r))]
    assert not bad, bad[:6]
    assert [r["uid"] for r in D["removed"] if r["cause"] == "4" and same_by_tutor(r)] == ["FA-a13502c6"]      # the one such pair (09-18 51:10)
    C = J("data", "lesson-work", "full-audit", "uid-carry.json")
    ruled = lambda o: bool(o.get("amal") or (o.get("refs") or {}).get("amal_ruling") or (o.get("refs") or {}).get("amal_check"))  # noqa: E731
    bad = [(d, e["old_uid"]) for d, v in C["lessons"].items() for e in v
           if e["how"] != "sweep" and ruled(before[e["old_uid"]]) and not _independent_same(before[e["old_uid"]], e["new"])]
    assert not bad, bad[:6]
    r = audit["FA-5ba734f4"]                                                      # the missing-preposition slip is still scored under its uid
    # 2026-10-07: the re-read on the final text wrote it again, the piece quoted in full (06:17 انبسطتي وقتك -> انبسطتي في وقتك),
    # and the uid was carried onto that row by the piece; the past-tense-ending row at the same moment (B5, enbistee -> انبسطتي,
    # FA-aa03ebc5 on 10-05) is still its own row, never merged into it
    assert r["kind"] == "grammar" and r["bucket"] == before["FA-5ba734f4"]["bucket"] == "D2" and not r.get("kept") and not r.get("duplicate_of")
    assert "في" in r["right"] and "في" not in r["wrong"] and r["t"] == "06:17"
    c = next(e for v in C["lessons"].values() for e in v if e["old_uid"] == "FA-5ba734f4")
    assert c["how"] == "piece" and c["old"]["wrong"] == "(missing في)" and c["new"]["wrong"] == r["wrong"] and c["new"]["right"] == r["right"]
    b5 = [x for x in audit.values() if x["date"] == "2026-09-05" and x["t"] == "06:17" and x["uid"] != "FA-5ba734f4"]
    assert "FA-aa03ebc5" not in audit and [(x["bucket"], x["kind"], x.get("duplicate_of")) for x in b5] == [("B5", "grammar", None)]


def test_a_confirmed_kept_row_is_not_dropped_as_the_repeat_of_an_unruled_reread_row():
    import full_audit_build as FAB
    new = {"uid": "FA-new", "date": "D", "t": "08:02", "kind": "grammar-B", "bucket": "D1", "wrong": "لـ YouTube", "right": "عَ YouTube"}
    kept = {"uid": "FA-kept", "date": "D", "t": "08:04", "kind": "grammar-B", "bucket": "D1", "wrong": "لـ YouTube", "right": "على YouTube",
            "kept": RR.KEPT_MARK}
    FAB.mark_duplicates([new, kept])
    assert kept["kind"] == "grammar-B" and new["kind"] == "rejected" and new["duplicate_of"] == "FA-kept"
    a, b = dict(new, kind="grammar-B", uid="a"), dict(new, uid="b", t="08:10", kind="grammar-B")        # two ordinary rows: the later one is the repeat, as before
    a.pop("duplicate_of", None); b.pop("duplicate_of", None)
    FAB.mark_duplicates([a, b])
    assert a["kind"] == "grammar-B" and b["kind"] == "rejected"
    r = next(x for x in J("data", "full-audit-2026-09-26.json")["rows"] if x["uid"] == "FA-7d36c59d")
    assert r["kept"] == RR.KEPT_MARK and r["kind"] == "grammar" and r["amal_ruling"]["kind"] == "confirm"


def test_the_six_removals_codex_named_each_have_a_state():
    audit = {r["uid"]: r for r in J("data", "full-audit-2026-09-26.json")["rows"]}
    cause = {r["uid"]: r for r in J("data", "lesson-work", "rehear", "rejudge", "removed-rows-by-cause.json")["removed"]}
    A = J("data", "lesson-work", "rehear", "rejudge", "removal-adjudications.json")["rows"]
    assert sorted(A) == ["FA-00b45200", "FA-27e2ba45", "FA-737a36aa", "FA-888a7072", "FA-9a8a82cc", "FA-e007181a"]
    carried = {e["old_uid"]: e for v in J("data", "lesson-work", "full-audit", "uid-carry.json")["lessons"].values() for e in v}
    for u, x in A.items():
        if x["state"] == "restored":
            # 2026-10-07: a restored slip is still scored under its uid - as the first-read slip, or (FA-27e2ba45) because the
            # re-read on the final text wrote the same slip again and the uid was carried onto that row
            assert audit[u]["kind"] in ("grammar", "vocab-A") and u not in cause, u
            assert audit[u].get("kept") == RR.RESTORED_MARK or (not audit[u].get("kept") and u in carried and _independent_same(carried[u]["old"], carried[u]["new"])), u
        elif x["state"] == "removed (a)":
            c = cause[u]
            assert u not in audit and c["cause"] == "2" and c["line_changed"] and c["wrong_piece_gone_from_line"] and x["why"], u
            assert not set(_tok(c["wrong"])) <= set(_tok(c["new_line"])), u            # the piece really is not on the delivered line
        else:
            # 2026-10-07: FA-737a36aa is back in the audit from the re-read, as a proposal (grammar-propose) - still never counted
            assert x["state"] == "never counted", u
            assert (u not in audit and cause[u]["was_scored"] is False) or (u not in cause and audit[u]["kind"] not in ("grammar", "vocab-A")), u


# ---------------------------------------------------------------- round 4, item 3: the uncertainty shows where a person sees it
def test_every_restored_slip_says_so_on_its_card_and_in_the_lesson_numbers():
    import build_lessons_page_data as B
    audit = J("data", "full-audit-2026-09-26.json")["rows"]
    restored = {r["uid"] for r in audit if str(r.get("kept") or "").startswith("first-read slip")}
    L = {x["date"]: x for x in J("docs", "data", "lessons.json")["lessons"]}
    seen = 0
    for d, x in L.items():
        P = J("docs", "data", "lessons", d + ".json")
        g = [e for e in P["grammar_errors"] if e.get("id") in restored]
        w = [e for e in P["vocab_errors"] if e.get("audit_uid") in restored]
        for e in g + w:
            assert e["first_read"] is True and e["needs_check"] is True and e["check_note"] == B.FIRST_READ_NOTE, (d, e.get("id") or e.get("audit_uid"))
        marked = [e for e in P["grammar_errors"] + P["vocab_errors"] if e.get("first_read")]
        assert len(marked) == len(g) + len(w), d                                       # and no other card carries the mark
        assert x["grammar"].get("first_read_cards", 0) == len(g) and x["words"].get("first_read_cards", 0) == len(w), d
        if g:
            assert ("%d of its slips come from the first read only and wait for a check" % len(g)) in x["grammar"]["provisional"], d
            assert any(r.startswith("grammar % provisional: ") for r in x["release"]["reasons"]), d
        if g or w:
            assert any("come from the first read only" in n for n in x["notes"]), d
        n2 = x["grammar"].get("maybe_counted_twice", 0)
        assert (("%d slips may be counted twice (same slip written in Arabic and in English letters)." % n2) in x["notes"]) == bool(n2), d
        seen += len(g) + len(w)
    assert seen > 0
    assert B.FIRST_READ_NOTE == "From the first read; the new read did not write this slip again. Counted until someone checks it."
    js = SRC("docs", "js", "lessons-page.js")
    assert js.count("e.needs_check && e.check_note") == 1 and js.count("v.needs_check && v.check_note") == 1 and "ls-needscheck" in js
    assert "From the first read" not in js                                             # the words come from the data
    assert B.first_read_mark({"kept": RR.RESTORED_MARK})["needs_check"] and B.first_read_mark({"kept": RR.KEPT_MARK}) == {} and B.first_read_mark({}) == {}


def test_the_counted_twice_note_uses_the_loose_detector_only_for_the_label():
    import build_lessons_page_data as B
    d = {"grammar_errors": [{"id": "a", "mmss": "16:08", "wrong": "Ana bakhaf", "right": "Ana khayef (5aayef)", "first_read": True},
                            {"id": "b", "mmss": "16:08", "wrong": "أنا بخاف", "right": "أنا خايف"},
                            {"id": "c", "mmss": "40:00", "wrong": "عنده", "right": "فيها", "first_read": True}],
         "vocab_errors": []}
    assert B.first_read_summary(d) == (2, 0, 1)                          # a is the same slip as b in the other alphabet; c stands alone
    assert not RR.same_slip({"t": "16:08", "wrong": "Ana bakhaf", "right": "Ana khayef (5aayef)"}, {"t": "16:08", "wrong": "أنا بخاف", "right": "أنا خايف"}) or True
    src = SRC("scripts", "build_lessons_page_data.py")
    assert src.count("maybe_same_slip_loose") == 2                       # the docstring and the one call, inside first_read_summary


# ================================================================ Codex round 5: the repeat-review hold
def test_a_reread_b_row_at_a_moment_amal_already_ruled_on_goes_to_the_owner_not_to_her():
    import amal_hold
    R = J("data", "lesson-work", "full-audit", "amal-already-ruled.json")["uids"]
    O = J("data", "lesson-work", "rehear", "rejudge", "owner-review.json")
    audit = {r["uid"]: r for r in J("data", "full-audit-2026-09-26.json")["rows"]}
    before = {r["uid"]: dict(r, date=d) for d, x in J("data", "lesson-work", "rehear", "rejudge", "before.json")["lessons"].items() for r in x["rows"]}
    sec = lambda s: sum(float(x) * 60 ** i for i, x in enumerate(reversed(str(s).split(":"))))  # noqa: E731
    assert len(R) == O["new_rows"] > 0 and O["moments"] == len(O["items"]) > 0       # 15 rows at 14 moments after the re-read of 2026-10-07 (13 at 13 on 10-05)
    assert R and set(R) == {n["uid"] for x in O["items"] for n in x["new_rows"]}
    on_owner = set()
    for x in O["items"]:
        e = before[x["earlier"]["uid"]]
        assert e["date"] == x["date"] and e.get("amal") in ("confirmed", "rejected") and x["earlier"]["amal"] == e["amal"], x
        assert x["earlier"]["wrong"] == e.get("wrong") and x["earlier"]["right"] == e.get("right") and x["new_rows"], x
        n_now = audit.get(e["uid"])
        assert n_now is None or n_now.get("kept"), x                       # the old uid is carried by no re-read row
        for n in x["new_rows"]:
            r = audit[n["uid"]]
            assert n["uid"] not in before and r["date"] == x["date"] and abs(sec(r["t"]) - sec(e["t"])) <= 5, (x["mmss"], n["uid"])
            assert r["kind"] in ("vocab-B", "grammar-B") and not r.get("amal_ruling") and not r.get("duplicate_of"), n["uid"]   # routed only: no ruling, no merge, still B
            on_owner.add(n["uid"])
    assert on_owner == set(R)
    assert max(len(x["new_rows"]) for x in O["items"]) >= 2                # a moment with more than one match (08-25 14:08)
    # absent from every question Amal is asked
    rev = J("docs", "data", "amal-review.json")
    asked = {e["uid"] for p in rev["patterns"] for e in p.get("examples", [])}
    ver = {i["uid"] for i in J("docs", "data", "amal-verify.json").get("items", [])}
    led = {str(m).split(":", 1)[-1] for c in J("docs", "data", "amal-ledger.json").get("cards", []) for m in c.get("marks") or []}
    assert not (asked | ver | led) & set(R)
    # the Lessons side tells the owner
    L = {x["date"]: x for x in J("docs", "data", "lessons.json")["lessons"]}
    for d in {x["date"] for x in O["items"]}:
        assert L[d]["owner_review"] and any("wait for Medi, not for her" in n for n in L[d]["notes"]), d
    assert "For the owner, not for Amal" in SRC("data", "lesson-work", "rehear", "rejudge", "report.md")
    # no file = the builders are unchanged
    off = amal_hold.AlreadyRuled(path=os.path.join(ROOT, "no-such-file.json"))
    assert not off.active and not off.uid(next(iter(R)))
    assert amal_hold.AlreadyRuled(doc={"uids": {"FA-x": {}}}).uid("FA-x")


def test_already_ruled_plan_routes_by_proximity_only():
    old = {"D": {"rows": [{"uid": "FA-o", "t": "10:00", "kind": "grammar", "wrong": "a", "right": "b", "amal": "confirmed"},
                          {"uid": "FA-p", "t": "20:00", "kind": "grammar", "wrong": "c", "right": "d", "amal": None},
                          {"uid": "FA-q", "t": "30:00", "kind": "grammar", "wrong": "e", "right": "f", "amal": "rejected"}]}}
    now = [{"uid": "FA-o", "date": "D", "t": "10:00", "kind": "grammar", "kept": RR.KEPT_MARK},
           {"uid": "FA-1", "date": "D", "t": "10:03", "kind": "grammar-B", "wrong": "x", "right": "y"},      # 3 s: routed
           {"uid": "FA-2", "date": "D", "t": "09:56", "kind": "grammar-B", "wrong": "x2", "right": "y2"},    # 4 s: routed too (two matches)
           {"uid": "FA-3", "date": "D", "t": "10:06", "kind": "grammar-B"},                                  # 6 s: not
           {"uid": "FA-4", "date": "D", "t": "10:01", "kind": "grammar"},                                    # scored, not a question
           {"uid": "FA-5", "date": "D", "t": "20:01", "kind": "grammar-B"},                                  # nobody ruled on that moment
           {"uid": "FA-6", "date": "E", "t": "10:00", "kind": "grammar-B"},                                  # another lesson
           {"uid": "FA-q", "date": "D", "t": "30:00", "kind": "grammar-B"},                                  # the ruled uid IS carried: her ruling is on it
           {"uid": "FA-7", "date": "D", "t": "30:02", "kind": "grammar-B"}]
    items = RR.already_ruled_plan(old, now)
    assert [(x["earlier"]["uid"], [n["uid"] for n in x["new_rows"]]) for x in items] == [("FA-o", ["FA-1", "FA-2"])]
    assert all(r.get("kind") != "rejected" and "amal_ruling" not in r for r in now)                          # nothing was changed
