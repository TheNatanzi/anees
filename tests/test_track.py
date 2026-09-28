# -*- coding: utf-8 -*-
"""Run log (scripts/track.py) and its wiring: append-only, every schema field present, no transcript or prompt text in the
public log, claude JSON parsing with and without `result`, and the wrappers (review_lesson.claude, the Scribe call) with
stubs - no real claude -p, no real Scribe."""
import json, os, re, subprocess
from pathlib import Path

import pytest

import track

ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
FIELDS = ["schema", "run_id", "parent_id", "trace_id", "kind", "step", "lesson_date", "pass", "role", "trigger", "host",
          "gen_ai.provider.name", "gen_ai.request.model", "gen_ai.response.model", "tool_version", "params", "prompt_file",
          "prompt_sha", "code_sha", "code_dirty", "input_refs", "output_refs", "status", "error_type", "retries",
          "started_at", "duration_ms", "usage", "cost_usd", "cost_basis", "metrics", "agreement"]
CLAUDE_JSON = {"type": "result", "subtype": "success", "is_error": False, "duration_ms": 1234, "num_turns": 7,
               "result": "counts: A 12, B 3", "session_id": "abc", "total_cost_usd": 0.4213,
               "usage": {"input_tokens": 1200, "output_tokens": 800, "cache_read_input_tokens": 50000,
                         "cache_creation_input_tokens": 3000},
               "modelUsage": {"claude-small-x": {"inputTokens": 100, "outputTokens": 20, "costUSD": 0.001},
                              "claude-big-y": {"inputTokens": 1100, "outputTokens": 780, "cacheReadInputTokens": 50000,
                                               "cacheCreationInputTokens": 3000, "costUSD": 0.4203}}}


@pytest.fixture
def runs(tmp_path, monkeypatch):
    d = tmp_path / "runs"
    monkeypatch.setenv("ANEES_RUNS_DIR", str(d))
    return d


def lines(d):
    return [json.loads(l) for p in sorted(Path(d).glob("*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield str(k); yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def assert_clean(rec):
    for s in strings(rec):
        assert not ARABIC.search(s), f"Arabic text in the public log: {s!r}"
        assert len(s) <= 200, f"free text longer than 200 chars in the public log: {s[:60]!r}..."


def test_one_line_per_run_with_every_field(runs, tmp_path):
    src = tmp_path / "in.txt"; src.write_text("x", encoding="utf-8")
    out = tmp_path / "out.json"
    with track.run("full_audit.reader", "2026-09-23", kind="inference", role="r1", pass_=1, provider="anthropic",
                   inputs=[src], outputs=[out]) as r:
        out.write_text(json.dumps({"rows": [1, 2, 3]}), encoding="utf-8")
        r.set(usage={"input_tokens": 5})
    (rec,) = lines(runs)
    assert [f for f in FIELDS if f not in rec] == []
    assert rec["status"] == "ok" and rec["kind"] == "inference" and rec["trace_id"] == "2026-09-23|manual"
    assert rec["input_refs"][0]["sha256"] and rec["output_refs"][0]["rows"] == 3
    assert rec["duration_ms"] >= 0 and rec["started_at"].endswith("Z")


def test_append_only_never_rewrites(runs):
    track.log_run("a.step", kind="build")
    (p,) = list(runs.glob("*.jsonl"))
    before = p.read_bytes()
    track.log_run("b.step", kind="eval", metrics={"n": 3})
    after = p.read_bytes()
    assert after.startswith(before) and len(lines(runs)) == 2
    assert len({x["run_id"] for x in lines(runs)}) == 2


def test_missing_output_is_empty_output_and_errors_are_reraised(runs, tmp_path):
    with track.run("x", outputs=[tmp_path / "never.json"]):
        pass
    with pytest.raises(ValueError):
        with track.run("y"):
            raise ValueError("boom")
    with pytest.raises(subprocess.TimeoutExpired):
        with track.run("z"):
            raise subprocess.TimeoutExpired("claude", 1)
    st = [(x["step"], x["status"], x["error_type"]) for x in lines(runs)]
    assert st == [("x", "empty_output", None), ("y", "error", "ValueError"), ("z", "timeout", "TimeoutExpired")]


def test_no_transcript_text_leaks(runs):
    arabic = "بدي روح عالبيت"
    long = "the whole reader brief " * 30
    track.log_run("leak.check", params={"said": arabic, "brief": long, "nested": [{"x": arabic}]}, role=arabic,
                  metrics={"note": long})
    (rec,) = lines(runs)
    assert_clean(rec)
    assert rec["role"].startswith("sha256:") and rec["params"]["brief"].startswith("sha256:")


def test_nothing_written_under_pytest_without_the_env(monkeypatch):
    monkeypatch.delenv("ANEES_RUNS_DIR", raising=False)
    assert track.runs_dir() is None
    assert track.log_run("silent")["step"] == "silent"          # built, but not written to data/runs


def test_parse_claude_json_with_result():
    p = track.parse_claude_output(json.dumps(CLAUDE_JSON))
    assert p["is_json"] and p["text"] == "counts: A 12, B 3"
    assert p["cost_usd"] == 0.4213 and p["usage"]["cache_read_input_tokens"] == 50000
    assert p["response_model"] == "claude-big-y" and set(p["models"]) == {"claude-small-x", "claude-big-y"}


def test_parse_claude_json_without_result_and_plain_text():
    no_result = {k: v for k, v in CLAUDE_JSON.items() if k != "result"}
    raw = json.dumps(no_result)
    p = track.parse_claude_output(raw)
    assert p["is_json"] and p["text"] == raw and p["cost_usd"] == 0.4213     # text falls back to stdout as before
    t = track.parse_claude_output("kept 3, dropped 1, added 0\n")
    assert not t["is_json"] and t["text"] == "kept 3, dropped 1, added 0\n" and t["cost_usd"] is None
    v = track.parse_claude_output(json.dumps([{"type": "system"}, CLAUDE_JSON]))   # --verbose array form
    assert v["text"] == "counts: A 12, B 3"
    assert track.parse_claude_output("")["text"] == ""


def test_model_flag_only_when_pinned(monkeypatch):
    monkeypatch.setattr(track, "CLAUDE_MODEL", None)
    assert track.claude_model_args() == []
    monkeypatch.setattr(track, "CLAUDE_MODEL", "claude-pinned-1")
    assert track.claude_model_args() == ["--model", "claude-pinned-1"]


def _stub_claude(monkeypatch, rl, stdout, returncode=0, writes=None):
    seen = {}
    real_run = subprocess.run

    def fake(cmd, *a, **k):
        if cmd and cmd[0] == rl.CLAUDE and "-p" in cmd:
            seen["cmd"] = cmd
            if writes:
                Path(writes).write_text(json.dumps({"rows": [1, 2]}), encoding="utf-8")
            return subprocess.CompletedProcess(cmd, returncode, stdout, "")
        return real_run(cmd, *a, **k)
    monkeypatch.setattr(rl.subprocess, "run", fake)
    return seen


def test_review_lesson_claude_wrapper_logs_tokens_cost_model(runs, tmp_path, monkeypatch):
    import review_lesson as rl
    monkeypatch.setattr(rl, "LOG", str(tmp_path / "review.log"))
    monkeypatch.setattr(rl, "CLAUDE", "claude-stub-not-on-path")
    monkeypatch.setattr(track, "CLAUDE_MODEL", None)
    out = tmp_path / "2026-09-23.r1.json"
    prompt = "Repo: X. SECRET PROMPT TEXT بدي. Reply with only your counts line."
    seen = _stub_claude(monkeypatch, rl, json.dumps(CLAUDE_JSON), writes=out)
    rl.claude(prompt, "2026-09-23 r1", step="full_audit.reader", lesson_date="2026-09-23", role="r1", pass_=1,
              outputs=[str(out)])
    cmd = seen["cmd"]
    assert cmd[cmd.index("--output-format") + 1] == "json" and "--model" not in cmd
    (rec,) = lines(runs)
    assert rec["status"] == "ok" and rec["gen_ai.response.model"] == "claude-big-y" and rec["gen_ai.request.model"] is None
    assert rec["cost_usd"] == 0.4213 and rec["cost_basis"] == "estimate" and rec["usage"]["output_tokens"] == 800
    assert rec["output_refs"][0]["rows"] == 2 and rec["params"]["prompt_arg_sha"] == track.sha256_text(prompt)
    assert "SECRET" not in json.dumps(rec) and "counts: A 12" not in json.dumps(rec)
    assert_clean(rec)
    assert "counts: A 12, B 3" in (tmp_path / "review.log").read_text(encoding="utf-8")    # same text as the old output


def test_review_lesson_claude_wrapper_pins_model_and_logs_failures(runs, tmp_path, monkeypatch):
    import review_lesson as rl
    monkeypatch.setattr(rl, "LOG", str(tmp_path / "review.log"))
    monkeypatch.setattr(rl, "CLAUDE", "claude-stub-not-on-path")
    monkeypatch.setattr(track, "CLAUDE_MODEL", "claude-pinned-1")
    seen = _stub_claude(monkeypatch, rl, "", returncode=1)
    rl.claude("p", "x r3", step="full_audit.third_reader", lesson_date="2026-09-23", outputs=[str(tmp_path / "none.json")])
    assert seen["cmd"][-2:] == ["--model", "claude-pinned-1"]

    def boom(cmd, *a, **k):
        raise subprocess.TimeoutExpired(cmd, 5)
    monkeypatch.setattr(rl.subprocess, "run", boom)
    rl.claude("p", "x r3", step="full_audit.third_reader", lesson_date="2026-09-23")       # swallowed, as before
    a, b = lines(runs)
    assert (a["status"], a["error_type"], a["gen_ai.request.model"]) == ("error", "exit_1", "claude-pinned-1")
    assert (b["status"], b["error_type"]) == ("timeout", "TimeoutExpired")


class R:
    def __init__(self, code, body=None, text=""): self.status_code, self._b, self.text = code, body or {}, text
    def json(self): return self._b


def test_scribe_call_logs_minutes_cost_retries(runs, tmp_path, monkeypatch):
    import pipeline_ext as px
    monkeypatch.setattr(px, "LEDGER", tmp_path / "budget.json")
    d = tmp_path / "2026-09-23" / "tracks"; d.mkdir(parents=True)
    mp3 = d / "amal.mp3"; mp3.write_bytes(b"x")
    seq = [R(503), R(200, {"words": [{"type": "word", "text": "مرحبا"}]})]
    out = px.transcribe_with_retry(lambda *a, **k: seq.pop(0), mp3, "k", minutes=30, sleep=lambda s: None)
    assert out["words"]                                           # the transcript itself is returned unchanged
    (rec,) = lines(runs)
    assert rec["step"] == "scribe.transcribe" and rec["kind"] == "ingest" and rec["lesson_date"] == "2026-09-23"
    assert rec["gen_ai.provider.name"] == "elevenlabs" and rec["gen_ai.request.model"] == "scribe_v2"
    # 0.22 $/h + 0.05 $/h keyterms (Amal's track gets the names list as Scribe keyterms, 2026-09-28)
    assert rec["usage"]["audio_min"] == 30 and abs(rec["cost_usd"] - 0.135) < 1e-6 and rec["cost_basis"] == "list_price"
    assert rec["params"]["track"] == "amal" and rec["params"]["keyterms"] > 0 and rec["params"]["names_sha"]
    assert rec["retries"] == 1 and rec["status"] == "ok" and rec["input_refs"][0]["sha256"]
    assert_clean(rec)


def test_scribe_budget_stop_and_failure_are_logged(runs, tmp_path, monkeypatch):
    import pipeline_ext as px
    monkeypatch.setattr(px, "LEDGER", tmp_path / "budget.json")
    mp3 = tmp_path / "a.mp3"; mp3.write_bytes(b"x")
    px.spend("elevenlabs", 8.9, "earlier")
    with pytest.raises(px.BudgetStop):
        px.transcribe_with_retry(lambda *a, **k: R(200), mp3, "k", minutes=60)
    monkeypatch.setattr(px, "LEDGER", tmp_path / "budget2.json")
    with pytest.raises(RuntimeError):
        px.transcribe_with_retry(lambda *a, **k: R(401, text="bad key"), mp3, "k", minutes=1, sleep=lambda s: None)
    a, b = lines(runs)
    assert a["status"] == "skipped_budget" and a["error_type"] == "BudgetStop"
    assert b["status"] == "error" and b["error_type"] == "http_401" and b["retries"] == 0


def test_logging_failure_never_breaks_the_call(tmp_path, monkeypatch):
    import pipeline_ext as px
    monkeypatch.setattr(px, "LEDGER", tmp_path / "budget.json")
    monkeypatch.setenv("ANEES_RUNS_DIR", str(tmp_path / "file-not-dir"))
    (tmp_path / "file-not-dir").write_text("x")                   # makedirs/open will fail inside track
    mp3 = tmp_path / "a.mp3"; mp3.write_bytes(b"x")
    out = px.transcribe_with_retry(lambda *a, **k: R(200, {"words": [{"type": "word", "text": "x"}]}), mp3, "k", minutes=1)
    assert out["words"]
