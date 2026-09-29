# -*- coding: utf-8 -*-
"""Accuracy gates (plan/PROMPT-SYSTEMIC-ACCURACY-AUDIT-2026-09-27.md items 1-8 + the 2026-09-29 engineering audit).
Offline: every test builds a tiny repo in tmp_path or uses a pure function. Real difficult cases are quoted from the
lessons they come from."""
import copy, io, json, os, contextlib

import pytest

import accuracy_gates as G

D = "2026-09-28"
POLICY = {"release_threshold_pct": 95.0, "consecutive_passes_required": 2, "agreement_readings": {"applied": "both"},
          "max_reader_passes": 2, "missing_interval_min_s": 120,
          "hole_markers": "\\[[^\\]]*(?:speaking|speaks|foreign language|inaudible|unintelligible|track missing|not transcribed)[^\\]]*\\]",
          "asr_review_required_for_verified": True}


def wj(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def turns(until=3600, step=10):
    out = []
    for i, t in enumerate(range(0, until, step)):
        out.append({"t": float(t), "end": float(t) + 4, "who": "Medi" if i % 2 else "Amal", "text": "أنا رحت" if i % 2 else "صح"})
    return out


def build_repo(root, *, not_counted=True, source_audit=True):
    """One lesson (2026-09-28): 1 word right, 1 word wrong, 1 counted grammar card, 1 card Amal's notes set apart."""
    r = str(root)
    wj(os.path.join(r, "docs", "data", "accuracy-policy.json"), POLICY)
    lesson = {"date": D, "duration_min": 60, "source": {"attribution": "per-speaker-tracks", "timing": "engine"},
              "words": {"right": 1, "wrong": 1, "partial": 0, "scored": 2, "pct": 50.0},
              "grammar": {"mistakes": 1, "uses": 10, "pct": 90.0}}
    wj(os.path.join(r, "docs", "data", "lessons.json"), {"lessons": [lesson]})
    g1 = {"id": "FA-1", "t": 300, "t_fix": 305, "said": "أنا بروح", "bucket": "A1"}
    g2 = {"id": "FA-2", "t": 360, "t_fix": 365, "said": "أنا بتحمس", "bucket": "A1", "counted": False, "not_counted_kind": "not-taught"}
    detail = {"date": D, "turns": turns(), "vocab_correct": [{"kind": "correct", "t": 100}],
              "vocab_errors": [{"kind": "wrong", "t": 200, "on_sheet": True, "event_id": "e1"}],
              "grammar_errors": [g1], "grammar_not_counted": [g2] if not_counted else []}
    wj(os.path.join(r, "docs", "data", "lessons", D + ".json"), detail)
    rows = [{"uid": "FA-1", "date": D, "kind": "grammar", "t": "05:00", "t_amal": "05:05", "bucket": "A1", "mode": "speaking",
             "medi_said": "أنا بروح", "confidence": "high", "agreed_by": "r1+r2", "passes": [1, 2]},
            {"uid": "FA-2", "date": D, "kind": "grammar", "t": "06:00", "t_amal": "06:05", "bucket": "A1", "mode": "speaking",
             "medi_said": "أنا بتحمس", "confidence": "high", "agreed_by": "r1+r2", "passes": [1, 2]}]
    wj(os.path.join(r, "data", "full-audit-2026-09-26.json"),
       {"rows": rows, "sweep_compat": {"rows": [{"uid": x["uid"], "date": D, "mode": "speaking", "bucket": "A1"} for x in rows]}})
    wj(os.path.join(r, "docs", "data", "grammar-buckets.json"), {"buckets": [{"id": "A1"}]})
    wj(os.path.join(r, "docs", "data", "word-bank-audit.json"), {"events": [{"date": D, "status": "Correct"}, {"date": D, "status": "Wrong"}]})
    os.makedirs(os.path.join(r, "data", "lesson-work", "full-audit"), exist_ok=True)
    if source_audit:
        wj(os.path.join(r, "data", "accuracy", "source-audit.json"), {"lessons": {D: {"flags": []}}})
    G.run_annotate(r, write=True)
    return r


# ---------------------------------------------------------------- item 1: the release threshold is enforced in code
def test_policy_threshold_is_95_and_cannot_drop():
    real = json.load(open(os.path.join(G.REPO, "docs", "data", "accuracy-policy.json"), encoding="utf-8"))
    assert real["release_threshold_pct"] >= 95.0


def test_lowered_threshold_blocks_publishing(tmp_path):
    r = build_repo(tmp_path)
    p = os.path.join(r, "docs", "data", "accuracy-policy.json")
    pol = json.load(open(p, encoding="utf-8"))
    pol["release_threshold_pct"] = 60.0
    wj(p, pol)
    assert any("threshold lowered" in x for x in G.validate(r))


@pytest.mark.parametrize("within,between,status", [
    ({1: 61.8, 2: 80.9}, {(1, 2): 78.9}, "withheld"),       # 08-25, the real numbers
    ({1: 95.0, 2: 96.0}, {(1, 2): 94.9}, "withheld"),       # passes agree inside, not with each other
    ({1: 95.0, 2: 96.0}, {(1, 2): 95.0}, "released"),
    ({1: 99.0}, {}, "withheld"),                            # one pass is never enough
])
def test_release_decision(within, between, status):
    assert G.release_decision(within, between, POLICY)["status"] == status


# ---------------------------------------------------------------- item 5: the check reconciles the pages with the audit
def test_grammar_cards_set_apart_by_amal_reconcile(tmp_path):
    """2026-09-29: Amal's rule notes set 1-5 grammar rows per lesson apart (grammar_not_counted, e.g. 09-04 بتحمس ->
    متحمس 'not taught yet'). The check compared counts and failed on 11 lessons, which would block every publish."""
    r = build_repo(tmp_path)
    assert not [p for p in G.validate(r) if "grammar" in p], G.validate(r)


def test_grammar_row_missing_from_the_page_is_caught(tmp_path):
    r = build_repo(tmp_path, not_counted=False)
    assert any("audit rows missing ['FA-2']" in p for p in G.validate(r))


def test_stale_release_layer_blocks_publishing(tmp_path):
    """A new ledger record / source audit changes the release layer; lessons.json must be re-annotated before publishing."""
    r = build_repo(tmp_path)
    assert G.validate(r) == []
    wj(os.path.join(r, "data", "accuracy", "source-audit.json"),
       {"lessons": {D: {"flags": [{"who": "Medi", "kind": "untranscribed", "from": 42.0, "to": 402.0, "speech_s": 174.0,
                                   "text": "Medi talks 00:42-06:42 (174 s of speech on their own track) with no transcript line"}]}}})
    assert any("stale" in p for p in G.validate(r))
    G.run_annotate(r, write=True)
    assert G.validate(r) == []


def test_check_fails_closed_on_an_exception(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("docs/data/lessons.json")
    monkeypatch.setattr(G, "validate", boom)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = G.main(["check"])
    assert code == 1
    last = out.getvalue().strip().splitlines()[-1]
    assert last.startswith("accuracy check: 1 problem(s) - do not publish. First:") and "FileNotFoundError" in last


def test_check_last_line_is_one_plain_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "validate", lambda: ["2026-09-28: words pct 50 != 51"])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert G.main(["check"]) == 1
    assert out.getvalue().strip().splitlines()[-1] == "accuracy check: 1 problem(s) - do not publish. First: 2026-09-28: words pct 50 != 51"


# ---------------------------------------------------------------- item 2: source coverage from the raw audio
def test_untranscribed_speech_makes_rows_unscoreable(tmp_path):
    """09-28: Medi's first recording (0:00-6:43) was never transcribed; the audio shows 174 s of his speech 00:42-06:42.
    A grammar row at 05:00 there has no transcript of what he said -> unscoreable, and the lesson says why."""
    r = build_repo(tmp_path)
    wj(os.path.join(r, "data", "accuracy", "source-audit.json"),
       {"lessons": {D: {"flags": [{"who": "Medi", "kind": "untranscribed", "from": 42.0, "to": 402.0, "speech_s": 174.0,
                                   "text": "Medi talks 00:42-06:42 (174 s of speech on their own track) with no transcript line"}]}}})
    doc, rel, q = G.run_annotate(r, write=False)
    L = doc["lessons"][0]
    assert any("Medi talks 00:42-06:42" in x for x in L["release"]["reasons"])
    assert L["grammar"]["excluded"] == 1 and L["grammar"]["eligible"] == 0        # FA-1 at 05:00 is inside the hole
    assert L["words"]["excluded"] == 2                                            # the words at 01:40 and 03:20 too


def test_missing_source_audit_is_a_reason_not_a_pass(tmp_path):
    r = build_repo(tmp_path, source_audit=False)
    doc, rel, q = G.run_annotate(r, write=False)
    assert any("no source audit" in x for x in doc["lessons"][0]["release"]["reasons"])


def test_nothing_is_verified_without_asr_review(tmp_path):
    r = build_repo(tmp_path)
    doc, rel, q = G.run_annotate(r, write=False)
    L = doc["lessons"][0]
    assert L["release"]["status"] == "not verified"
    assert L["words"]["verified_pct"] is None and L["grammar"]["verified_pct"] is None
    assert L["words"]["pct"] == 50.0                                               # the shown number stays (decision 4: shown with ≈)


def test_real_lessons_are_all_not_verified_and_say_why():
    doc = json.load(open(os.path.join(G.REPO, "docs", "data", "lessons.json"), encoding="utf-8"))
    for L in doc["lessons"]:
        assert L["release"]["status"] in ("verified", "not verified")
        if L["release"]["status"] != "verified":
            assert L["release"]["reasons"], L["date"]


# ---------------------------------------------------------------- items 3 + 6: checks, the ledger, and who may check
def rec(uid, verdict, role, reviewer, at="2026-09-29T03:00:00-07:00"):
    return {"uid": uid, "method": "human" if role == "human" else "audio", "role": role, "reviewer": reviewer, "verdict": verdict,
            "confidence": "high", "evidence": {"t_start": 290, "t_end": 325, "quote": "x"}, "at": at}


def low_conf_repo(tmp_path):
    r = build_repo(tmp_path)
    p = os.path.join(r, "data", "full-audit-2026-09-26.json")
    A = json.load(open(p, encoding="utf-8"))
    A["rows"][0]["confidence"] = "low"                                          # -> needs an audio or human check
    wj(p, A)
    return r


def annotate_with(r, records):
    wj(os.path.join(r, "data", "accuracy", "verifications.json"), {"records": records})
    doc, rel, q = G.run_annotate(r, write=False)
    return doc["lessons"][0]["grammar"], q


def test_uncertain_row_waits_for_a_check(tmp_path):
    g, q = annotate_with(low_conf_repo(tmp_path), [])
    assert g["pending"] == 1 and [x["uid"] for x in q] == ["FA-1"] and q[0]["stage"].startswith("needs the second judge")


def test_codex_confirms_row_becomes_eligible(tmp_path):
    g, q = annotate_with(low_conf_repo(tmp_path), [rec("FA-1", "confirmed", "second-judge", "codex gpt-5.5")])
    assert g["pending"] == 0 and g["excluded"] == 0 and q == []


def test_codex_rejects_row_waits_for_amal_never_dropped_on_one_ai(tmp_path):
    """The two AIs disagree -> the row is not counted as right and not dropped: it goes to Amal (decision 5)."""
    g, q = annotate_with(low_conf_repo(tmp_path), [rec("FA-1", "rejected", "second-judge", "codex gpt-5.5")])
    assert g["pending"] == 1 and g["excluded"] == 0
    assert q[0]["stage"].startswith("waiting for Amal") and q[0]["second_judge"]["verdict"] == "rejected"


def test_amal_settles_a_disagreement(tmp_path):
    base = [rec("FA-1", "rejected", "second-judge", "codex gpt-5.5")]
    g, q = annotate_with(low_conf_repo(tmp_path), base + [rec("FA-1", "confirmed", "human", "Amal", "2026-09-30T10:00:00-07:00")])
    assert g["pending"] == 0 and g["excluded"] == 0                              # her yes = scored
    g, q = annotate_with(low_conf_repo(tmp_path / "b"), base + [rec("FA-1", "rejected", "human", "Amal", "2026-09-30T10:00:00-07:00")])
    assert g["excluded"] == 1                                                    # her reason = dropped


def test_ledger_rejects_a_claude_second_judge_and_bad_records():
    probs = G.ledger_problems({"records": [rec("FA-1", "confirmed", "second-judge", "claude opus"),
                                           {"uid": "FA-2", "method": "audio", "verdict": "maybe"}]})
    assert any("Claude model cannot be the second judge" in p for p in probs)
    assert any("record 1 missing" in p for p in probs) and any("verdict must be" in p for p in probs)


def test_ledger_revision_history_latest_human_wins():
    s = G.ledger_state({"records": [rec("FA-1", "confirmed", "human", "Amal", "2026-09-30T10:00:00Z"),
                                    rec("FA-1", "rejected", "human", "Amal", "2026-09-30T11:00:00Z"),
                                    rec("FA-1", "confirmed", "second-judge", "codex gpt-5.5", "2026-09-30T12:00:00Z")]})["FA-1"]
    assert s["revisions"] == 3 and s["human"]["verdict"] == "rejected"
    assert G.check_outcome(s)[0] == "excluded"


# ---------------------------------------------------------------- item 7: grammar denominator
def test_grammar_denominator_latin_slips_invalid():
    """09-04 22:09: the engine wrote his try in Latin letters ('M-mitruj?'); the usage counter skips Latin turns."""
    den = G.grammar_denominator([{"said": "maruj baru... Is it m-maruj? M-mitruj?", "bucket": "B15"},
                                 {"said": "أنا بتحمس", "bucket": "B15"}], {"uses": 70, "by_bucket": {"B15": 3}})
    assert not den["valid"] and den["slips_latin"] == 1


def test_grammar_denominator_valid_when_counter_saw_every_slip():
    den = G.grammar_denominator([{"said": "أنا بروح", "bucket": "A1"}], {"uses": 10, "by_bucket": {"A1": 4}})
    assert den["valid"]


# ---------------------------------------------------------------- item 4: cached outputs invalidate on input change
def test_cache_state(tmp_path):
    out, inp = tmp_path / "r1.json", tmp_path / "t.txt"
    inp.write_text("transcript v1", encoding="utf-8")
    out.write_text("{}", encoding="utf-8")
    assert G.cache_state(str(out), [str(inp)], str(tmp_path)).startswith("stale: no input manifest")
    G.write_manifest(str(out), [str(inp)], str(tmp_path))
    assert G.cache_state(str(out), [str(inp)], str(tmp_path)) == "fresh"
    inp.write_text("transcript v2", encoding="utf-8")
    assert "inputs changed" in G.cache_state(str(out), [str(inp)], str(tmp_path))


# ---------------------------------------------------------------- item 8: eligible / excluded / pending beside the headline
def test_release_totals_carry_eligible_excluded_pending(tmp_path):
    r = build_repo(tmp_path)
    doc, rel, q = G.run_annotate(r, write=False)
    for k in ("eligible", "excluded", "pending"):
        assert k in rel["totals"]["words"] and k in rel["totals"]["grammar"]
    w = doc["lessons"][0]["words"]
    assert w["eligible"] + w["excluded"] == w["scored"]


# ---------------------------------------------------------------- item 3: the third reader sees the agreed rows too
def test_third_reader_sees_agreed_rows_and_can_challenge(tmp_path, monkeypatch):
    import full_audit_compare as F
    monkeypatch.setattr(F, "WORK", str(tmp_path))
    agreed = [{"t": "05:00", "t_amal": "05:05", "kind": "grammar", "bucket": "A1", "medi_said": "أنا بروح", "amal_said": "بروح",
               "wrong": "بروح", "right": "روح", "agreed_by": "r1+r2"}]
    out = {"date": D, "pass": 1, "counts": {"r1": 1, "r2": 1, "agreed": 1, "disputed": 0, "agreement_pct": 100.0},
           "coverage": {}, "agreed": agreed, "disputes": []}
    F.write_disputes_md(D, out)
    md = open(os.path.join(str(tmp_path), f"{D}.disputes.md"), encoding="utf-8").read()
    assert "A1 t=05:00" in md and "challenges" in md                               # before: agreed rows were never shown
    wj(os.path.join(str(tmp_path), f"{D}.compare.json"), out)
    wj(os.path.join(str(tmp_path), f"{D}.r3.json"), {"rulings": [], "added": [], "challenges": [{"id": "A1", "why": "Amal was not correcting"}]})
    st = F.settle(D)
    assert st["rows"][0]["r3_challenge"] == "Amal was not correcting" and st["counts"]["r3_challenged"] == 1
    row = dict(st["rows"][0], passes=[1, 2], confidence="high")
    assert "both readers found it but the third reader challenged it" in G.check_reasons(row, 2)
