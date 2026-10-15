# -*- coding: utf-8 -*-
"""PR-25 (Medi 2026-10-15): the slip readers are Opus (r1) + Sonnet (r2) and a slip stands only when both flagged it.
The gate rule, which lessons it applies to (the reader manifests), settle holding one-reader rows, the readers' pinned
model + effort, the automatic confirmation on the next exam, and the 2026-10-15 evidence replayed exactly."""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import reader_agree as RA  # noqa: E402


def row(t, kind="grammar", **k):
    return dict(t=t, kind=kind, **k)


def test_gate_keeps_a_slip_only_when_both_readers_flagged_its_family_within_15_s():
    r1 = [row("01:00"), row("02:00", "vocab-A", tier=1), row("05:00")]
    r2 = [row("01:10"), row("02:05", "grammar"), row("09:00", "vocab-B", tier=3)]
    rows = [row("01:02", wrong="a"), row("02:01", "vocab-A", tier=1, wrong="b"), row("05:00", wrong="c"),
            row("09:00", "vocab-B", tier=3, wrong="d"), row("07:00", "note", wrong="e")]
    kept, held = RA.gate(rows, r1, r2)
    assert [r["wrong"] for r in kept] == ["a", "d", "e"]          # tier-3 and non-slip rows pass through (never a chip)
    assert [(r["wrong"], r["flagged_by"]) for r in held] == [("b", "r1 (Opus)"), ("c", "r1 (Opus)")]
    assert all(r["held"] == RA.HELD for r in held)
    k2, h2 = RA.gate([row("01:00", wrong="x")], [row("01:16")], [row("01:00")])
    assert not k2 and h2[0]["flagged_by"] == "r2 (Sonnet)"           # 16 s is outside the window
    assert RA.gate([row("03:00", wrong="z")], [], [])[1][0]["flagged_by"].startswith("neither")


def _manifest(work, date, r, model):
    with open(os.path.join(work, "%s.%s.json.inputs.json" % (date, r)), "w", encoding="utf-8") as f:
        json.dump({"inputs": {}, **({"model": model} if model else {})}, f)


def test_only_lessons_read_by_the_pair_are_gated(tmp_path):
    w = str(tmp_path)
    assert not RA.active("2026-01-05", w)
    _manifest(w, "2026-01-05", "r1", "claude-opus-5-5")
    _manifest(w, "2026-01-05", "r2", None)                           # an old Opus-only r2: unchanged chips
    assert not RA.active("2026-01-05", w)
    _manifest(w, "2026-01-05", "r2", "claude-sonnet-5-5")
    assert RA.active("2026-01-05", w)


def _write(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def test_settle_holds_one_reader_rows_on_a_pair_lesson_and_leaves_other_lessons_alone(tmp_path, monkeypatch):
    import full_audit_compare as FAC
    w = str(tmp_path)
    monkeypatch.setattr(FAC, "WORK", w)
    a = row("01:00", "grammar", wrong="w1", right="r1", bucket="A1", id="r1-1", confidence="high")
    b = row("01:03", "grammar", wrong="w1", right="r1", bucket="A1", id="r2-1", confidence="high")
    only = row("04:00", "vocab-A", tier=1, wrong="w2", right="r2", id="r1-2", confidence="high")
    for d in ("2026-01-05", "2026-01-06"):
        _write(os.path.join(w, d + ".r1.json"), {"rows": [a, only]})
        _write(os.path.join(w, d + ".r2.json"), {"rows": [b]})
        FAC.compare(d)
        _write(os.path.join(w, d + ".r3.json"), {"rulings": [{"id": x["id"], "verdict": "keep"} for x in
                                                             json.load(open(os.path.join(w, d + ".compare.json"), encoding="utf-8"))["disputes"]]})
    _manifest(w, "2026-01-05", "r1", "claude-opus-5-5")
    _manifest(w, "2026-01-05", "r2", "claude-sonnet-5-5")
    s = FAC.settle("2026-01-05")
    assert [r["wrong"] for r in s["rows"]] == ["w1"] and s["held_one_reader"][0]["wrong"] == "w2"
    assert s["both_agree"] == "PR-25" and s["counts"]["held_one_reader"] == 1
    s2 = FAC.settle("2026-01-06")                                    # not read by the pair: the third reader's keep stands
    assert [r["wrong"] for r in s2["rows"]] == ["w1", "w2"] and "held_one_reader" not in s2
    assert [x["wrong"] for x in RA.held_rows(w)] == ["w2"]


def test_review_lesson_pins_each_reader_to_its_model_and_effort(monkeypatch):
    import review_lesson as RL
    assert RL.READER_MODELS == {"r1": "claude-opus-5-5", "r2": "claude-sonnet-5-5"} and RL.READER_EFFORT == "high"
    seen = []

    def fake_run(cmd, **k):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout='{"result": "ok"}', stderr="")
    monkeypatch.setattr(RL.subprocess, "run", fake_run)
    monkeypatch.setattr(RL, "log", lambda *a: None)
    RL.claude("p", "x", model="claude-sonnet-5-5", effort="high")
    cmd = seen[-1]
    assert cmd[cmd.index("--model") + 1] == "claude-sonnet-5-5" and cmd[cmd.index("--effort") + 1] == "high"
    assert cmd.count("--model") == 1                                 # the default pin is not added on top


def test_confirm_scores_both_agree_vs_opus_alone_and_flags_a_loss(tmp_path):
    w = str(tmp_path)
    d = "2026-01-07"
    _manifest(w, d, "r1", "claude-opus-5-5")
    _manifest(w, d, "r2", "claude-sonnet-5-5")
    key = {"slips": [{"k": "grammar", "i": "60.00"}, {"k": "vocab", "i": "200.00"}]}
    win = RA.confirm(d, w, key, settled={"rows": [row("01:00")]}, r1={"rows": [row("01:00"), row("08:00"), row("09:00")]})
    assert win["won"] and win["flag"] is None and win["both_agree"]["precision"] == 100.0
    loss = RA.confirm(d, w, key, settled={"rows": [row("08:00")]}, r1={"rows": [row("01:00"), row("03:20", "vocab-A")]})
    assert not loss["won"] and "did NOT beat Opus alone" in loss["flag"] and "no silent roll-back" in loss["flag"]
    assert RA.confirm("2026-01-08", w, key, settled={"rows": []}, r1={"rows": []}) is None   # not a pair lesson


def test_the_2026_10_15_evidence_replays_exactly():
    import reader_tiers as RT
    tot = [0, 0, 0]
    per = []
    for d in RT.LESSONS:
        o, s = RT.load_run(d, "opus", 1)["rows"], RT.load_run(d, "sonnet", 1)["rows"]
        kept, _ = RA.gate(o, o, s)
        p, k = RA.flags(kept), RT.key_slips(d)
        m = RT.match(p, k)
        per.append(RT.prf(m, len(p), len(k))["f05"])
        tot = [tot[0] + m, tot[1] + len(p), tot[2] + len(k)]
    assert per == [70.7, 68.5, 69.8]
    assert RT.prf(*tot)["f05"] == 69.6
