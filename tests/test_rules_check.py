# -*- coding: utf-8 -*-
"""Standing rules vs data (scripts/check_rules.py, eng audit 2026-09-29 area 5).

Each BLOCK check gets a tiny fixture repo with one planted violation (the check must fail) and the clean twin (it must
pass). The last tests run the checker on the real repo: no BLOCK rule may be broken, and RULES.md must match the
System Settings copy (this one failed before 2026-09-29: standing-rules.json still had the 09-23 text of S1)."""
import hashlib, json
from pathlib import Path

import pytest

import check_rules as cr

ROOT = Path(__file__).resolve().parent.parent


def w(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return p


def audit(root, rows):
    w(root / "data" / "full-audit-2026-09-26.json", {"rows": rows})


def wordbank(root, events, evidence):
    w(root / "docs" / "data" / "word-bank-audit.json", {"events": events})
    w(root / "docs" / "data" / "word-bank-evidence.json", {"events": evidence})


def row(kind="grammar", signal="recast", **k):
    return dict({"uid": "FA-1", "date": "2026-09-28", "t": "01:00", "kind": kind, "signal": signal, "why": "", "mode": "speaking"}, **k)


def ev(i, word, t, status, reason="x", date="2026-09-28"):
    return {"id": i, "date": date, "time": t, "word": word, "status": status, "reason": reason}


# ---------------------------------------------------------------- S1
def test_s1_extra_rows_need_method_source_and_her_letters(tmp_path):
    good = {"words": {"بيزعجني": {"latin": "byez3ejni", "method": "pieces", "from": "baz3ej + bye-"},
                      "روسيا": {"latin": "Roosya", "method": "guess", "from": ""}}}
    w(tmp_path / "docs" / "data" / "arabizi-extra.json", good)
    assert cr.check_s1_extra(tmp_path, None)["status"] == "pass"
    for bad in ({"latin": "ka3ke", "method": "invented"}, {"latin": "", "method": "sound", "from": "x"},
                {"latin": "dallat", "method": "sound", "from": ""}, {"latin": "4arab", "method": "pieces", "from": "x"},
                {"latin": "دلت", "method": "as-said", "from": "x"}):
        w(tmp_path / "docs" / "data" / "arabizi-extra.json", {"words": {"كلمة": bad}})
        assert cr.check_s1_extra(tmp_path, None)["status"] == "fail", bad


# ---------------------------------------------------------------- S2
def test_s2_raw_transcript_edit_is_caught(tmp_path):
    raw = tmp_path / "raw" / "2026-09-28"
    f = w(raw / "scribe_Medi.json", {"words": [{"text": "مرحبا"}]})
    w(raw / "scribe_Medi.provenance.json", {"response_sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
    (tmp_path / "data" / "runs").mkdir(parents=True)
    r = cr.check_s2_raw(tmp_path, str(tmp_path / "raw"))
    assert r["status"] == "pass" and r["total"] == 1
    f.write_text(json.dumps({"words": [{"text": "مرحبا!"}]}), encoding="utf-8")        # someone "fixed" the raw text
    assert cr.check_s2_raw(tmp_path, str(tmp_path / "raw"))["status"] == "fail"


def test_s2_missing_raw_dir_is_skip_not_pass(tmp_path):
    assert cr.check_s2_raw(tmp_path, str(tmp_path / "nope"))["status"] == "skip"


# ---------------------------------------------------------------- S3
def test_s3_scored_slip_without_signal_fails(tmp_path):
    audit(tmp_path, [row(), row(kind="grammar-B", signal="none")])       # a B row may have no signal: it is unscored
    assert cr.check_s3_signal(tmp_path, None)["status"] == "pass"
    audit(tmp_path, [row(signal="none")])
    assert cr.check_s3_signal(tmp_path, None)["status"] == "fail"
    audit(tmp_path, [row(kind="vocab-A", signal="amal-ruling")])       # her ruling must be stored
    assert cr.check_s3_signal(tmp_path, None)["status"] == "fail"
    audit(tmp_path, [row(kind="vocab-A", signal="amal-ruling", amal_ruling={"kind": "confirm"})])
    assert cr.check_s3_signal(tmp_path, None)["status"] == "pass"


# ---------------------------------------------------------------- S5
def test_s5_pause_scored_as_error_fails(tmp_path):
    audit(tmp_path, [row()])
    wordbank(tmp_path, [ev("a", "bokra", 10, "Partial", "long pause before the right answer")], [])
    assert cr.check_s5_pause(tmp_path, None)["status"] == "fail"
    wordbank(tmp_path, [ev("a", "bokra", 10, "Correct", "long pause before the right answer")], [])
    assert cr.check_s5_pause(tmp_path, None)["status"] == "pass"


# ---------------------------------------------------------------- M11
def test_only_medi_speech_is_scored(tmp_path):
    wordbank(tmp_path, [ev("a", "bokra", 10, "Correct"), ev("b", "bokra", 20, "Not scored")],
             [{"id": "a", "speaker": "Medi"}, {"id": "b", "speaker": "Amal"}])
    assert cr.check_medi_only(tmp_path, None)["status"] == "pass"
    wordbank(tmp_path, [ev("b", "bokra", 20, "Correct")], [{"id": "b", "speaker": "Amal"}])
    assert cr.check_medi_only(tmp_path, None)["status"] == "fail"


# ---------------------------------------------------------------- report-level checks never block, but count
def test_report_checks_count_without_failing(tmp_path):
    audit(tmp_path, [row(why="may be only pronunciation (dropped hamza)")])
    wordbank(tmp_path, [ev("a", "wa7ad", 100, "Correct"), ev("b", "wa7ad", 105, "Correct", "same episode, count once"),
                        ev("c", "shu", 200, "Correct"), ev("d", "akId", 300, "Partial", "Same vocabulary supplied by Amal within 15 seconds; x")],
             [{"id": x, "speaker": "Medi", "grammar_only": x == "a"} for x in "abcd"])
    for fn, n in ((cr.check_s4_pronunciation, 1), (cr.check_one_episode, 1), (cr.check_glue, 1), (cr.check_15s_clue, 1),
                  (cr.check_grammar_only, 1)):
        r = fn(tmp_path, None)
        assert (r["status"], r["level"], r["count"]) == ("open", "report", n), (fn.__name__, r)


# ---------------------------------------------------------------- new bucket
def test_new_word_needs_an_amal_or_medi_mark(tmp_path):
    w(tmp_path / "docs" / "data" / "lessons.json", {"lessons": [{"date": "2026-09-04", "new_words": [{"key": "banbese6"}]}]})
    w(tmp_path / "data" / "decisions" / "2026-09.jsonl",
      json.dumps({"who": "Medi", "answer": "new", "about_id": "banbese6", "source_row": {"lesson_date": "2026-09-04"}}) + "\n")
    assert cr.check_new_signal(tmp_path, None)["status"] == "pass"
    w(tmp_path / "docs" / "data" / "lessons.json", {"lessons": [{"date": "2026-09-04", "new_words": [{"key": "sawwi"}]}]})
    assert cr.check_new_signal(tmp_path, None)["status"] == "fail"       # inferred 'new' (first heard) is not allowed


# ---------------------------------------------------------------- Amal's hub stays removed
def test_hub_page_or_button_coming_back_fails(tmp_path):
    w(tmp_path / "docs" / "tutor.html", "<a href='amal/review.html'>review</a>")
    w(tmp_path / "docs" / "go.html", "// Amal's hub was removed 2026-09-28; old ?to=hub links open the review page")
    assert cr.check_hub_removed(tmp_path, None)["status"] == "pass"
    w(tmp_path / "docs" / "tutor.html", "<a class=btn href='amal/hub.html'>Amal's hub</a>")
    assert cr.check_hub_removed(tmp_path, None)["status"] == "fail"
    w(tmp_path / "docs" / "tutor.html", "ok")
    w(tmp_path / "docs" / "amal" / "hub.html", "<html></html>")
    assert cr.check_hub_removed(tmp_path, None)["status"] == "fail"


# ---------------------------------------------------------------- A1 never contacts Amal
def test_mail_only_to_medi(tmp_path):
    w(tmp_path / "scripts" / "send_lesson_email.mjs", "const TO = 'thenatanzi@gmail.com';   // only Medi\nnodemailer")
    w(tmp_path / "scripts" / "x.py", "print(1)")
    assert cr.check_medi_only_email(tmp_path, None)["status"] == "pass"
    w(tmp_path / "scripts" / "notify_amal.py", "import smtplib\n")
    assert cr.check_medi_only_email(tmp_path, None)["status"] == "fail"
    (tmp_path / "scripts" / "notify_amal.py").unlink()
    w(tmp_path / "scripts" / "send_lesson_email.mjs", "const TO = 'amal@example.com';")
    assert cr.check_medi_only_email(tmp_path, None)["status"] == "fail"


# ---------------------------------------------------------------- H4
def test_budget_at_90_percent_fails(tmp_path):
    w(tmp_path / "data" / "budget.json", {"elevenlabs": 3.39, "openai": 2.21})
    assert cr.check_budget(tmp_path, None)["status"] == "pass"
    w(tmp_path / "data" / "budget.json", {"elevenlabs": 9.0, "openai": 2.21})
    assert cr.check_budget(tmp_path, None)["status"] == "fail"


# ---------------------------------------------------------------- RULES.md -> System Settings copy
def test_rules_json_out_of_sync_fails(tmp_path):
    w(tmp_path / "RULES.md", "# Anees\n\nintro\n\n---\n\n## S1 — One\n\nbody one\n\n---\n\n## S2 — Two\n\nbody two\n")
    w(tmp_path / "docs" / "data" / "standing-rules.json", {"rules": [{"id": "S1", "body_md": "body one"}, {"id": "S2", "body_md": "body two"}]})
    assert cr.check_rules_json(tmp_path, None)["status"] == "pass"
    w(tmp_path / "docs" / "data" / "standing-rules.json", {"rules": [{"id": "S1", "body_md": "old body"}]})
    assert cr.check_rules_json(tmp_path, None)["count"] == 2


# ---------------------------------------------------------------- AI steps (area 6)
def test_new_untracked_ai_call_fails(tmp_path):
    w(tmp_path / "scripts" / "reader.py", "import track\nsubprocess.run([CLAUDE, '-p', prompt])\n")
    assert cr.check_ai_logged(tmp_path, None)["status"] == "pass"
    w(tmp_path / "scripts" / "new_judge.py", "requests.post('https://api.openai.com/v1/chat/completions')\n")
    r = cr.check_ai_logged(tmp_path, None)
    assert r["status"] == "fail" and "new_judge.py" in r["examples"][0]


def test_claude_run_must_log_its_model_and_match_the_pin(tmp_path):
    base = {"kind": "inference", "gen_ai.provider.name": "anthropic", "status": "ok", "step": "full_audit.reader", "run_id": "r"}
    w(tmp_path / "data" / "runs" / "2026-09.jsonl", json.dumps(dict(base, **{"gen_ai.request.model": "claude-opus-5-5",
                                                                           "gen_ai.response.model": "claude-opus-5-5"})) + "\n")
    assert cr.check_ai_model(tmp_path, None)["status"] == "pass"
    w(tmp_path / "data" / "runs" / "2026-09.jsonl", json.dumps(dict(base, **{"gen_ai.request.model": "claude-opus-5-5",
                                                                           "gen_ai.response.model": "claude-other"})) + "\n")
    assert cr.check_ai_model(tmp_path, None)["status"] == "fail"
    w(tmp_path / "data" / "runs" / "2026-09.jsonl", json.dumps(dict(base, **{"gen_ai.request.model": None,
                                                                           "gen_ai.response.model": None})) + "\n")
    assert cr.check_ai_model(tmp_path, None)["status"] == "fail"


# ---------------------------------------------------------------- the real repo
def test_live_rules_json_matches_rules_md():
    """Failed before 2026-09-29: docs/data/standing-rules.json was built 09-23 and missed the 09-26 S1 extension."""
    r = cr.check_rules_json(ROOT, None)
    assert r["status"] == "pass", r["examples"]


def test_live_repo_breaks_no_block_rule():
    """The guard itself: every BLOCK rule holds on the committed data. REPORT rules are listed, not failed."""
    results = cr.run_all(ROOT, cr.DEFAULT_RAW)
    fails = [(r["id"], r["examples"][:2]) for r in results if r["status"] == "fail"]
    assert not fails, fails
    assert {r["id"] for r in results} >= {"S1-extra", "S3-signal", "S5-pause", "M11-medi-only", "NEW-amal-signal",
                                          "HUB-removed", "A1-medi-only", "H4-budget", "RULES-json-sync", "AI-logged", "AI-model"}


def test_cli_first_line_is_the_reason(tmp_path, capsys):
    w(tmp_path / "RULES.md", "# A\n\n---\n\n## S1 — One\n\nnew text\n")
    w(tmp_path / "docs" / "data" / "standing-rules.json", {"rules": [{"id": "S1", "body_md": "old text"}]})
    rc = cr.main(["--root", str(tmp_path), "--raw", str(tmp_path / "raw"), "--only", "RULES-json-sync"])
    first = capsys.readouterr().out.splitlines()[0]
    assert rc == 1 and first.startswith("check_rules: FAIL RULES-json-sync: 1 violation(s) - S1")
