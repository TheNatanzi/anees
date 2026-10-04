# -*- coding: utf-8 -*-
"""The 2026-10-04 re-read on the re-heard transcript must not cut anything off an audit row (scripts/rehear_rejudge.py,
the carry in scripts/full_audit_build.py assign_uids, the moment match in scripts/full_audit_compare.py hand_self_fix).
Pure: no network, no AI, nothing written outside tmp_path."""
import copy, hashlib, json, os, sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import full_audit_build as FAB  # noqa: E402
import full_audit_compare as C  # noqa: E402
import rehear_rejudge as RR  # noqa: E402

D = "2026-10-02"


def row(t, wrong, kind="grammar", right="x", **k):
    return {"date": D, "t": t, "t_amal": None, "wrong": wrong, "right": right, "kind": kind, "mode": "speaking", **k}


def as_old(rows):
    rows = copy.deepcopy(rows)
    FAB.assign_uids(rows)
    return rows


def as_new(rows):
    """What rehear_rejudge.new_rows gives: read_key + the uid the row would get by itself."""
    rows = copy.deepcopy(rows)
    FAB.stamp_read_keys(rows)
    keys = [r["read_key"] for r in rows]
    FAB.assign_uids(rows)
    for r, k in zip(rows, keys):
        r["read_key"] = k
    return rows


def carried(old, new_raw):
    """Run the carry and the build's assign_uids on fresh rows -> (final rows, entries)."""
    ent, _ = RR.carry_entries(old, as_new(new_raw))
    rows = FAB.stamp_read_keys(copy.deepcopy(new_raw))
    FAB.assign_uids(rows, {e["read_key"]: e["old_uid"] for e in ent})
    return rows, ent


# ------------------------------------------------------------------------------------------------ assign_uids
def test_uid_is_unchanged_without_a_carry():
    r = as_old([row("07:02", "سمعت")])[0]
    base = f"{D}|422|{C.norm('سمعت')}|grammar"
    assert r["uid"] == "FA-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    assert "read_key" not in r and "uid_carried_from" not in r


def test_a_row_moved_one_second_keeps_the_old_uid():
    old = as_old([row("07:02", "سمعت", right="صحيت")])
    rows, ent = carried(old, [row("07:03", "سمعت", right="صحيت")])
    assert [e["how"] for e in ent] == ["piece"]
    assert rows[0]["uid"] == old[0]["uid"] and rows[0]["uid_carried_from"] != old[0]["uid"]
    assert "read_key" not in rows[0]
    assert ent[0]["new_key"] == {"date": D, "t": "07:03", "sec": 423, "wrong": "سمعت", "wrong_norm": C.norm("سمعت"), "kind_class": "grammar"}


def test_exact_rows_need_no_carry_entry():
    old = as_old([row("07:02", "سمعت"), row("09:00", "على عشرة")])
    rows, ent = carried(old, [row("07:02", "سمعت"), row("09:00", "على عشرة")])
    assert ent == [] and [r["uid"] for r in rows] == [o["uid"] for o in old]


def test_reworded_row_is_carried_only_when_one_candidate_on_each_side():
    old = as_old([row("10:00", "المال مسافة", right="مصاري")])
    rows, ent = carried(old, [row("10:01", "مسافه كتير", right="فلوس")])
    assert [e["how"] for e in ent] == ["piece"]                      # half the tokens shared = the same piece
    old = as_old([row("10:00", "aaa", right="r1")])
    rows, ent = carried(old, [row("10:02", "bbb", right="r2")])
    assert [e["how"] for e in ent] == ["moment"] and rows[0]["uid"] == old[0]["uid"]
    rows, ent = carried(old, [row("10:02", "bbb", right="r2"), row("10:03", "ccc", right="r3")])
    assert ent == [] and old[0]["uid"] not in {r["uid"] for r in rows}       # two candidates: not guessed


def test_kind_class_must_match():
    old = as_old([row("10:00", "عموي", kind="grammar")])
    rows, ent = carried(old, [row("10:00", "عموي", kind="vocab-A")])
    assert ent == [] and rows[0]["uid"] != old[0]["uid"]


def test_a_dropped_or_rejected_old_row_matches_by_its_first_class():
    o = row("10:00", "aaa", kind="dropped-by-amal", amal_ruling={"kind": "skip", "before": {"kind": "vocab-B"}})
    o["uid"] = "FA-old00001"
    rows, ent = carried([o], [row("10:02", "aaa b", kind="vocab-B")])
    assert rows[0]["uid"] == "FA-old00001"
    o = row("10:00", "aaa", kind="rejected", kind_before_rejection="grammar"); o["uid"] = "FA-old00002"
    assert carried([o], [row("10:04", "aaa", kind="grammar-B")])[0][0]["uid"] == "FA-old00002"


def test_same_sweep_row_and_repeat_within_30_s():
    o = row("10:00", None, kind="vocab-A", right="كلمة", sweep_id="V1002-001"); o["uid"] = "FA-sw000001"
    rows, ent = carried([o], [row("10:20", "شي", kind="vocab-A", right="غير", sweep_id="V1002-001")])
    assert ent[0]["how"] == "sweep" and rows[0]["uid"] == "FA-sw000001"
    old = as_old([row("30:47", "الأول اليوم")])
    rows, ent = carried(old, [row("30:57", "الأول اليوم")])
    assert ent[0]["how"] == "repeat" and rows[0]["uid"] == old[0]["uid"]


def test_an_old_uid_goes_to_one_row_only_and_uids_stay_unique():
    rows = FAB.stamp_read_keys([row("10:00", "a"), row("10:10", "b")])
    FAB.assign_uids(rows, {rows[0]["read_key"]: "FA-old", rows[1]["read_key"]: "FA-old"})
    assert rows[0]["uid"] == "FA-old" and rows[1]["uid"] != "FA-old"
    rows = [row("10:00", "a", uid_keep="FA-kept0001", kept="x"), row("10:00", "a")]
    FAB.assign_uids(rows)
    assert rows[0]["uid"] == "FA-kept0001" and "uid_keep" not in rows[0] and len({r["uid"] for r in rows}) == 2


def test_load_carry_reads_the_file(tmp_path):
    p = tmp_path / "uid-carry.json"
    p.write_text(json.dumps({"lessons": {D: [{"old_uid": "FA-1", "read_key": "FA-9"}]}}), encoding="utf-8")
    assert FAB.load_carry(str(p)) == {"FA-9": "FA-1"}
    assert FAB.load_carry(str(tmp_path / "none.json")) == {} and FAB.load_preserved(str(tmp_path / "none.json")) == []


# ------------------------------------------------------------------------------------------------ the real 10-02 re-read
def test_real_reread_of_10_02_keeps_every_matched_uid():
    pub = os.path.join(REPO, "data", "lesson-work", "full-audit", D + ".settled.json")
    new = os.path.join(REPO, "data", "lesson-work", "bench", D, "readers", "flash", D + ".settled.json")
    if not (os.path.exists(pub) and os.path.exists(new)):
        pytest.skip("the 10-02 scratch re-read is not in this checkout")
    old = [dict(r, date=D) for r in json.load(open(pub, encoding="utf-8"))["rows"]]
    old = as_old(old)
    new_raw = [dict(r, date=D) for r in json.load(open(new, encoding="utf-8"))["rows"]]
    naive = {r["uid"] for r in as_new(new_raw)} & {o["uid"] for o in old}
    rows, ent = carried(old, new_raw)
    olds = {o["uid"] for o in old}
    kept = {r["uid"] for r in rows} & olds
    assert len({r["uid"] for r in rows}) == len(rows)                       # no uid twice
    assert len(kept) == len(naive) + len(ent) and len(ent) >= 8             # the carry is what saves them
    assert len(kept) >= 0.75 * len(old)                                     # most slips are the same slips
    assert len({e["old_uid"] for e in ent}) == len(ent) == len({e["read_key"] for e in ent})
    by = {r["uid"]: r for r in rows}
    for e in ent:                                                           # every carried pair is one moment or one sweep / repeat
        o = next(x for x in old if x["uid"] == e["old_uid"])
        assert e["how"] in ("piece", "moment", "repeat", "sweep")
        assert C.same_moment(o, by[e["old_uid"]]) or e["how"] in ("repeat", "sweep")


# ------------------------------------------------------------------------------------------------ kept rows
def test_amal_confirmed_row_without_a_new_row_is_kept_and_listed():
    conf = row("05:00", "على ثمانية", kind="grammar", signal="amal-ruling", confidence="high", uid="FA-conf0001", n=4,
               amal_ruling={"kind": "confirm", "pattern": "p-x", "rule_id": 7, "before": {"kind": "grammar-B", "signal": "none", "confidence": "low"}},
               amal="confirmed", line_before="أنا صحيت على ثمانية.", refs={"amal_ruling": "confirm"})
    rej = row("06:00", "الله يوفقك", kind="dropped-by-amal", uid="FA-rej00001", amal="rejected", line_before="الله يوفقك.",
              amal_ruling={"kind": "skip", "before": {"kind": "vocab-B"}}, refs={})
    car = row("07:00", "سمعت", kind="grammar", uid="FA-car00001", amal="confirmed", line_before="أنا سمعت", refs={},
              amal_ruling={"kind": "confirm", "before": {"kind": "grammar-B"}})
    plain = row("08:00", "zzz", uid="FA-plain001", amal=None, refs={"verifications": 1})
    new = [row("07:00", "سمعت", kind="grammar-B", uid="FA-car00001")]
    turns = [{"t": 300.2, "who": "Medi", "text": "أنا صحيت عالتمانية."}, {"t": 360.0, "who": "Medi", "text": "الله يوفقك."},
             {"t": 420.4, "who": "Medi", "text": "أنا صحيت"}]
    pres, L = RR.kept_plan({D: {"rows": [conf, rej, car, plain]}}, {D: new}, lambda d: turns)
    assert [x["uid"] for x in L["kept_confirmed"]] == ["FA-conf0001"] and [x["uid"] for x in L["listed_rejected"]] == ["FA-rej00001"]
    assert L["kept_confirmed"][0]["line_before"] == "أنا صحيت على ثمانية." and L["kept_confirmed"][0]["line_after"] == "أنا صحيت عالتمانية."
    assert [x["uid"] for x in L["line_changed"]] == ["FA-car00001"]          # carried, his line changed: listed, not dropped
    assert len(pres) == 1
    p = pres[0]
    assert p["uid_keep"] == "FA-conf0001" and p["kept"] == RR.KEPT_MARK and "amal_ruling" not in p and "uid" not in p
    assert (p["kind"], p["signal"], p["confidence"]) == ("grammar-B", "none", "low")     # her confirm can be re-applied
    rows = new + pres
    FAB.assign_uids(rows)
    assert rows[1]["uid"] == "FA-conf0001" and rows[1]["kept"] == RR.KEPT_MARK and "uid_keep" not in rows[1]


def test_report_counts_and_orphans():
    before = {"date": D, "headline": None, "rows": [
        dict(row("05:00", "a"), uid="FA-1", amal="confirmed", amal_ruling={"kind": "confirm"}),
        dict(row("06:00", "b"), uid="FA-2", amal=None), dict(row("07:00", "c"), uid="FA-3", amal="rejected", amal_ruling={"kind": "skip"})]}
    after = [dict(row("05:01", "a2"), uid="FA-1", uid_carried_from="FA-x", amal_ruling={"kind": "confirm"}), dict(row("09:00", "n"), uid="FA-9")]
    x = RR.report_lesson(before, after, [{"uid": "FA-2", "date": D}, {"uid": "FA-1", "date": D}], [{"id": "p", "rows": ["FA-3", "FA-1"]}])
    assert (x["rows_before"], x["rows_after"], x["same_uid"], x["moved"], x["added"], x["removed"]) == (3, 2, 1, 1, 1, 2)
    assert x["amal"]["no_row_after"] == ["FA-3"] and x["amal"]["ruling_not_back"] == []
    assert x["verification_records"]["orphaned"] == ["FA-2"] and x["patterns"]["orphaned"] == ["FA-3"]
    after[0].pop("amal_ruling")
    assert [y["uid"] for y in RR.report_lesson(before, after)["amal"]["ruling_not_back"]] == ["FA-1"]


# ------------------------------------------------------------------------------------------------ hand rulings
def test_self_fix_ruling_follows_its_moment_when_disputes_renumber():
    hand = [{"date": D, "pass": "p1", "ruling": "D9", "verdict": "her-fix", "his_t": "04:30", "her_t": "04:21"}]
    disputes = [{"id": "D1", "r1": {"t": "01:00"}}, {"id": "D2", "r1": {"t": "04:23", "t_amal": "04:27"}}, {"id": "D9", "r1": {"t": "30:00"}}]
    get = lambda did: C.hand_self_fix(hand, D, 1, did, next(d for d in disputes if d["id"] == did)["r1"], disputes)
    assert get("D2") is hand[0]                 # renumbered D9 -> D2: found by the moment
    assert get("D9") is None and get("D1") is None       # the number alone no longer applies it to another moment
    same = [{"id": f"D{i}", "r1": {"t": "01:00"}} for i in range(1, 9)] + [{"id": "D9", "r1": {"t": "04:23"}}, {"id": "D10", "r1": {"t": "04:26"}}]
    assert C.hand_self_fix(hand, D, 1, "D9", same[8]["r1"], same) is hand[0]          # number still right: that dispute only
    assert C.hand_self_fix(hand, D, 1, "D10", same[9]["r1"], same) is None
    p2 = [dict(hand[0], **{"pass": "p2"})]      # its pass was retired: the ruling applies to the pass-1 dispute of the moment
    assert C.hand_self_fix(p2, D, 1, "D2", disputes[1]["r1"], disputes) is p2[0]


def test_preflight_lists_what_would_stop_the_build(tmp_path):
    w = str(tmp_path)
    J = lambda name, obj: open(os.path.join(w, name), "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False))
    J("rejected.json", {"rows": [{"date": D, "t": "05:00", "wrong": "ابل امبارح", "kind": "vocab", "why": "S4"},
                                 {"date": D, "t": "20:00", "wrong": "شي", "why": "gone"}]})
    J("signal-rulings.json", {"rows": []})
    J("proposed-buckets.json", {"proposals": [{"id": "P-1", "rows": [{"date": D, "t": "09:00", "wrong": "إنتي"}]}]})
    J("duplicates.json", {"pairs": [{"date": D, "keep": "FA-gone", "drop": "FA-here", "why": "x"},
                                    {"date": D, "keep": "FA-g1", "drop": "FA-g2", "why": "y"}]})
    J("self-fix-rulings.json", {"rows": []})
    before = [dict(row("05:00", "ابل امبارح", kind="rejected", kind_before_rejection="vocab-A"), uid="FA-old1")]
    rows = [dict(row("05:01", "قبل البارحة", kind="vocab-A"), uid="FA-old1"), dict(row("12:00", "x"), uid="FA-here")]
    P = RR.check_hand_rulings(rows, before, work=w, disputes_of=lambda d: [])
    by = {(p["file"], p["severity"]) for p in P}
    assert ("proposed-buckets.json", "stop") in by and ("duplicates.json", "stop") in by
    rej = [p for p in P if p["file"] == "rejected.json"]
    assert rej[0]["severity"] == "decide" and rej[0]["detail"]["uid"] == "FA-old1"     # carried under another wording: a person decides
    assert rej[1]["severity"] == "info"
    assert [p["severity"] for p in P if p["file"] == "duplicates.json"] == ["stop", "info"]
    ok = RR.check_hand_rulings([dict(row("05:00", "ابل امبارح", kind="rejected", kind_before_rejection="vocab-A"), uid="FA-old1"),
                                dict(row("09:00", "إنتي"), uid="FA-p"), dict(row("1:00", "k"), uid="FA-gone"), dict(row("2:00", "d"), uid="FA-here")],
                               before, work=w, disputes_of=lambda d: [])
    assert not [p for p in ok if p["severity"] in ("stop", "decide")]


# ------------------------------------------------------------------------------------------------ pass 2
def test_retired_pass_2_leaves_one_honest_pass(tmp_path, monkeypatch):
    import accuracy_gates as G
    w = str(tmp_path)
    S = lambda name, rows: open(os.path.join(w, name), "w", encoding="utf-8").write(json.dumps({"date": D, "counts": {"final": len(rows), "agreement_pct": 60.0}, "rows": rows}))
    S(D + ".settled.json", [row("05:00", "a", confidence="high")])
    S(D + ".p2.settled.json", [row("09:00", "old text row", confidence="high")])
    for f in (D + ".compare.json", D + ".p2.compare.json", D + ".passes.json", D + ".p2.r1.json", D + ".p2.r1.json.inputs.json"):
        open(os.path.join(w, f), "w", encoding="utf-8").write(json.dumps({"counts": {"agreement_pct": 60.0}}))
    monkeypatch.setattr(C, "WORK", w)
    assert len(C.union_rows(D)["rows"]) == 2 and G.pass_numbers(D, w) == [1, 2]
    assert len(RR.retire_pass2(False, work=w)) == 5 and os.path.exists(os.path.join(w, D + ".p2.settled.json"))      # dry run moves nothing
    moved = RR.retire_pass2(True, work=w)
    dest = os.path.join(w, "superseded-2026-10-04")
    assert sorted(os.listdir(dest)) == sorted(moved + ["README.json"])                # kept, not deleted
    U = C.union_rows(D)
    assert [r["wrong"] for r in U["rows"]] == ["a"] and U["rows"][0]["passes"] == [1]
    assert G.pass_numbers(D, w) == [1]
    policy = G.load_policy()
    dec = G.agreement(D, policy, w)
    assert dec["status"] == "withheld" and "2 consecutive passes" in dec["reasons"][0]   # never 'verified' on one pass


# ------------------------------------------------------------------------------------------------ prompts + accept
def test_agent_prompt_is_the_review_prompt_with_absolute_paths():
    import review_lesson as R
    p = RR.agent_prompt(D, "r1")
    assert p.startswith(R.reader_prompt(D, "r1").split("Transcript:")[0])
    assert os.path.join(R.WORK, D + ".txt") in p and "data/lesson-work/full-audit/" not in p
    assert "Write ONLY the one JSON file" in p and os.path.join(R.WORK, D + ".r1.json") in p
    p3 = RR.agent_prompt(D, "r3")
    assert "THIRD-READER-BRIEF.md" in p3 and os.path.join(R.WORK, D + ".disputes.md") in p3 and os.path.join(R.WORK, D + ".r3.json") in p3


def test_reader_inputs_are_the_ones_review_lesson_pins():
    import inspect, review_lesson as R
    src = inspect.getsource(R.main)
    assert 'reader_in = [f(".txt"), os.path.join(WORK, "READER-BRIEF.md"), os.path.join(WORK, "amal-sheet.txt")] + common' in src
    assert 'third_in = [f(".txt"), f(".disputes.md"), f(".r1.json"), f(".r2.json"), os.path.join(WORK, "THIRD-READER-BRIEF.md")] + common' in src
    assert 'common = [os.path.join(WORK, "buckets.md"), os.path.join(REPO, "RULES.md"), os.path.join(REPO, "docs", "data", "names.json")]' in src
    names = lambda r: [os.path.basename(p) for p in RR.reader_inputs(D, r, REPO)]
    assert names("r1") == [D + ".txt", "READER-BRIEF.md", "amal-sheet.txt", "buckets.md", "RULES.md", "names.json"]
    assert names("r3") == [D + ".txt", D + ".disputes.md", D + ".r1.json", D + ".r2.json", "THIRD-READER-BRIEF.md", "buckets.md", "RULES.md", "names.json"]


def test_accept_pins_an_agent_file_as_fresh(tmp_path, monkeypatch):
    import review_lesson as R
    repo = str(tmp_path)
    work = os.path.join(repo, "data", "lesson-work", "full-audit")
    os.makedirs(work); os.makedirs(os.path.join(repo, "docs", "data", "lessons"))
    put = lambda p, s: open(os.path.join(repo, p), "w", encoding="utf-8", newline="\n").write(s)
    put("docs/data/lessons/%s.json" % D, json.dumps({"turns": [{"t": 1.0, "who": "Medi", "text": "مرحبا"}, {"t": 3.0, "who": "Amal", "text": "أهلا"}]}))
    put("docs/data/names.json", "{}"); put("RULES.md", "rules")
    for f in ("READER-BRIEF.md", "THIRD-READER-BRIEF.md", "amal-sheet.txt", "buckets.md"):
        put("data/lesson-work/full-audit/" + f, f)
    monkeypatch.setattr(R, "REPO", repo); monkeypatch.setattr(R, "WORK", work); monkeypatch.setattr(RR, "OUTD", os.path.join(repo, "out"))
    put("data/lesson-work/full-audit/%s.txt" % D, R.transcript_text(D, repo))
    out = os.path.join(work, D + ".r1.json")
    assert RR.accept(D, "r1", before=os.path.join(repo, "none.json")) == 1            # nothing written yet
    put("data/lesson-work/full-audit/%s.r1.json" % D, '{"date": "%s", "reader": "r1", "rows": [' % D)
    assert RR.accept(D, "r1", before=os.path.join(repo, "none.json")) == 1 and not os.path.exists(out + ".inputs.json")    # cut-off file
    put("data/lesson-work/full-audit/%s.r1.json" % D, json.dumps({"date": D, "reader": "r1", "rows": []}))
    snap = os.path.join(repo, "before.json")
    open(snap, "w", encoding="utf-8").write(json.dumps({"lessons": {D: {"files": {".r1.json": RR.sha_file(out)}}}}))
    assert RR.accept(D, "r1", before=snap) == 1                                         # the pre-re-read file is never pinned as new
    assert RR.accept(D, "r1", before=os.path.join(repo, "none.json")) == 0
    man = json.load(open(out + ".inputs.json", encoding="utf-8"))
    assert man["prompt_sha"] == R._prompt_sha(R.reader_prompt(D, "r1")) and "agent" in man["written_by"]
    assert R.cache_decision(out, RR.reader_inputs(D, "r1", repo), R.reader_prompt(D, "r1"), legacy_ok=False) == "fresh"
    assert R.readers_read_current(D, repo) is None
    put("docs/data/lessons/%s.json" % D, json.dumps({"turns": [{"t": 1.0, "who": "Medi", "text": "مرحبتين"}]}))
    assert R.readers_read_current(D, repo)                                              # the text moved on: stale again
