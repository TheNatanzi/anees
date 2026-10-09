# -*- coding: utf-8 -*-
"""PG-37 one box per line (Medi 2026-10-08 "Can we turn this into just 1 box and we can write the correction, not try and
separate into so many boxes?"): the server half - medi_corrections.py accepts rows with payload.raw and kind 'note';
scripts/correction_parse.py reads notes with ONE logged Haiku call each and mirrors the edge function's spend. No live
writes: fixtures and injected runners only."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import tempfile
os.environ.setdefault("ANEES_RUNS_DIR", os.path.join(tempfile.gettempdir(), "anees-test-runs"))   # never inside the repo
import correction_parse as CP  # noqa: E402
import medi_corrections as MC  # noqa: E402

DATES = {"2026-10-08"}
NOTE = {"id": "n1-aaaaaaaa", "lesson_date": "2026-10-08", "turn_t": 454.0, "turn_who": "Medi", "kind": "note", "target": None,
        "payload": {"raw": "the engine heard العشاء, I said el 3ashara", "line": "على العشاء رح نروح", "turn_end": 456},
        "note": None, "ts": "2026-10-08T20:00:00.000Z", "tz_offset_min": 0}


def test_pg_37_rows_with_raw_and_kind_note_are_accepted_and_a_note_changes_nothing():
    assert MC.bad_row(NOTE, DATES) is None
    text = {"id": "t1-aaaaaaaa", "lesson_date": "2026-10-08", "turn_t": 454.0, "turn_who": "Medi", "kind": "text",
            "target": {"word": "العشاء"}, "payload": {"engine_wrote": "العشاء", "heard": "العشرة", "raw": "I said العشرة not العشاء"}, "ts": "2026-10-08T20:01:00Z"}
    assert MC.bad_row(text, DATES) is None
    out = MC.text_rows([NOTE, text])
    assert [r["heard"] for r in out] == ["العشرة"]            # the note is not an overlay row
    rows = [{"date": "2026-10-08", "t": "07:34", "kind": "vocab-A", "wrong": "العشاء", "right": "العشرة", "signal": "explicit-no"}]
    rep = MC.apply_rows(rows, [NOTE])
    assert rep["applied"] == [] and rows[0]["kind"] == "vocab-A"   # a note never touches a reader row
    assert MC.bad_row(dict(NOTE, kind="free-words"), DATES).startswith("unknown kind")


def test_pg_37_the_prompt_file_and_the_edge_copy_match():
    assert CP.prompt_ts_fresh(), "run python scripts/correction_parse.py build-prompt"
    p = CP.prompt_text()
    for k in ("speaker", "time", "missing", "text", "add", "note"):
        assert '"%s"' % k in p
    assert "{line}" in p and "{text}" in p and "{who}" in p


def test_pg_37_the_ai_answer_is_checked_against_the_line_like_the_page_does():
    ans = {"items": [{"kind": "text", "engine_wrote": "العشاء", "heard": "el 3ashara"}, {"kind": "add", "said": "نروح", "right": "منروح", "k": "grammar"},
                     {"kind": "speaker", "who": "Nobody"}, {"kind": "time", "t": "2:13"}, {"kind": "text", "engine_wrote": "nothing-like-it", "heard": "x"}]}
    items = CP.items_from_ai(ans, NOTE)
    assert [i[0] for i in items] == ["text", "add", "time"]
    assert items[0][2]["engine_wrote"] == "العشاء" and items[0][2]["heard"] == "el 3ashara"
    assert items[2][2]["t"] == 133.0
    assert CP.items_from_ai(ans, dict(NOTE, turn_who="Amal"))[0][0] == "text" and all(i[0] != "add" for i in CP.items_from_ai(ans, dict(NOTE, turn_who="Amal")))
    assert CP.in_line("عشرة", "على العشاء رح نروح", 0.5) == "العشاء"       # 'the' prefixes do not count


def test_pg_37_read_notes_makes_rows_with_raw_and_parsed_from_and_never_re_reads_a_note(tmp_path, monkeypatch):
    monkeypatch.setenv("ANEES_RUNS_DIR", str(tmp_path / "runs"))
    calls = []
    def runner(prompt):
        calls.append(prompt)
        assert "el 3ashara" in prompt and "على العشاء" in prompt
        return json.dumps({"result": json.dumps({"items": [{"kind": "text", "engine_wrote": "العشاء", "heard": "el 3ashara"}]}),
                           "total_cost_usd": 0.0004, "usage": {"input_tokens": 300, "output_tokens": 40}, "modelUsage": {"claude-haiku-5-5": {"costUSD": 0.0004}}})
    written, spent = [], []
    out = CP.read_notes([NOTE], insert=lambda rows: written.extend(rows), runner=runner, log=lambda *a: None, spend=lambda s, u, w: spent.append((s, u, w)))
    assert out["read"] == 1 and len(calls) == 1 and spent == [("anthropic", 0.0004, "parse-correction note n1-aaaaa (claude-haiku-5-5)")]
    kinds = [r["kind"] for r in written]
    assert kinds == ["text", "note"]                      # the fix + the done marker
    assert written[0]["payload"]["raw"] == NOTE["payload"]["raw"] and written[0]["payload"]["parsed_from"] == NOTE["id"]
    assert written[0]["payload"]["engine_wrote"] == "العشاء" and MC.bad_row(written[0], DATES) is None
    assert written[1]["payload"]["parsed_from"] == NOTE["id"] and MC.bad_row(written[1], DATES) is None
    # the run line is there with the cost (AI-paid-logged)
    lines = [json.loads(l) for p in (tmp_path / "runs").glob("*.jsonl") for l in open(p, encoding="utf-8")]
    assert lines and lines[-1]["step"] == "correction_parse.read_note" and lines[-1]["cost_usd"] == 0.0004 and lines[-1]["gen_ai.request.model"] == "claude-haiku-5-5"
    # second pass: the note has children -> nothing to read
    out2 = CP.read_notes([NOTE] + written, insert=lambda rows: written.extend(rows), runner=runner, log=lambda *a: None, spend=lambda *a: None)
    assert out2["read"] == 0 and len(calls) == 1
    # a note the model cannot shape stays a note (done marker only) and is not read again either
    w2 = []
    CP.read_notes([dict(NOTE, id="n2-bbbbbbbb")], insert=lambda rows: w2.extend(rows), runner=lambda p: json.dumps({"result": "no json here"}), log=lambda *a: None, spend=lambda *a: None)
    assert [r["kind"] for r in w2] == ["note"]
    assert CP.unread_notes([dict(NOTE, id="n2-bbbbbbbb")] + w2) == []


def test_pg_37_edge_spend_is_mirrored_once_into_the_ledger_and_the_run_log(tmp_path):
    rows = [{"ts": "2026-10-08T19:00:00+00:00", "service": "anthropic", "usd": 0.0003, "note": "parse-correction Medi 7:34 (340 tokens, claude-haiku-5-5)"},
            {"ts": "2026-10-08T19:05:00+00:00", "service": "anthropic", "usd": 0.0002, "note": "parse-correction Medi 7:40 (300 tokens, claude-haiku-5-5)"},
            {"ts": "2026-10-08T19:06:00+00:00", "service": "openai", "usd": 0.01, "note": "check-homework x"}]
    spent, runs = [], []
    st = tmp_path / "state.json"
    out = CP.mirror_spend(fetch=lambda: rows, log=lambda *a: None, state_p=str(st), spend=lambda s, u, w, t: spent.append((s, u, w)), log_run=lambda *a, **k: runs.append(k))
    assert out["mirrored"] == 2 and [s[1] for s in spent] == [0.0003, 0.0002] and all(s[0] == "anthropic" for s in spent)
    assert [r["cost_usd"] for r in runs] == [0.0003, 0.0002] and runs[0]["started_at"] == "2026-10-08T19:00:00Z"
    out2 = CP.mirror_spend(fetch=lambda: rows, log=lambda *a: None, state_p=str(st), spend=lambda *a: spent.append(a), log_run=lambda *a, **k: runs.append(k))
    assert out2["mirrored"] == 0 and len(spent) == 2             # never twice
