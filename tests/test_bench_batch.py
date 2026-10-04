# -*- coding: utf-8 -*-
"""The Batch transport of the baseline listener (scripts/bench_batch.py, PR-18): no network, no paid call.
Everything runs in a temp bench folder; the five network functions are replaced."""
import json, os, struct, sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402
import bench_batch as BB  # noqa: E402

DATE = "2099-01-01"


def _wav(path, seconds=1.0):
    n = int(16000 * seconds)
    data = struct.pack("<%dh" % n, *([1000, -1000] * (n // 2)))
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16) + b"data" + struct.pack("<I", len(data)) + data)


def _answer(arabic, arabizi, tin=700, aud=40, cand=100, thoughts=60):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps({"arabic": arabic, "arabizi": arabizi, "changes": []}, ensure_ascii=False)}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": tin, "candidatesTokenCount": cand, "thoughtsTokenCount": thoughts,
                              "promptTokensDetails": [{"modality": "TEXT", "tokenCount": tin - aud}, {"modality": "AUDIO", "tokenCount": aud}]}}


@pytest.fixture
def bench(tmp_path, monkeypatch):
    d = str(tmp_path / "bench")
    os.makedirs(os.path.join(d, "clips"))
    monkeypatch.setattr(BC, "bench_dir", lambda date: d)
    lines = []
    for i, listen in ((0, True), (2, True), (3, False), (5, True)):
        clip = "clips/medi-%04d.wav" % i
        _wav(os.path.join(d, clip), 1.0 + i / 10.0)
        lines.append({"i": i, "listen": listen, "clip": clip, "engine": "line %d" % i})
    BC.W(os.path.join(d, "truth.json"), {"lines": lines})
    BC.W(os.path.join(d, "prompts.json"), {"arms": {"ctx": {str(l["i"]): "PROMPT for line %d: مرحبا" % l["i"] for l in lines}, "before": {}}})
    BC.W(os.path.join(d, "manifest.json"), {"prompts_sha256": BC.sha_file(os.path.join(d, "prompts.json")), "truth_sha256": BC.sha_file(os.path.join(d, "truth.json")),
                                            "clips": {l["clip"]: BC.sha_file(os.path.join(d, l["clip"])) for l in lines}})
    paid = []
    monkeypatch.setattr(BR, "paid", lambda *a, **k: paid.append((a, k)))
    monkeypatch.setattr(BV, "money_base", lambda date, path, svc="gemini": (10.0, 61.0))
    for name in ("upload_file", "create_batch", "get_batch", "download_file", "list_batches"):         # a test that reaches the network fails loudly
        monkeypatch.setattr(BB, name, lambda *a, _n=name, **k: (_ for _ in ()).throw(AssertionError("network call: " + _n)))
    return {"d": d, "paid": paid}


def test_the_request_is_the_instant_calls_body_plus_its_key(bench, monkeypatch):
    sent = {}

    class R:
        status_code = 200

        def json(self):
            return _answer("x", "y")

    import requests
    monkeypatch.setattr(requests, "post", lambda url, **k: sent.update(url=url, body=k["json"]) or R())
    monkeypatch.setattr(BR, "key", lambda name: "k")
    its = BB.items(DATE)
    assert [i for i, _, _ in its] == ["0", "2", "5"]                 # only the lines the listener is sent
    i, clip, prompt = its[1]
    BR.gemini(BB.MODEL, clip, prompt, temp=1)                        # the instant baseline's call (bench_run.run_engine, engine gemini-flash-t1)
    assert sent["url"].endswith("/models/gemini-3.8-flash:generateContent")
    line = BB.request_line(i, clip, prompt)
    assert line == {"key": "2", "request": sent["body"]}
    req = line["request"]
    assert list(req) == ["contents", "generationConfig"]
    assert req["generationConfig"] == {"temperature": 1, "responseMimeType": "application/json"}
    parts = req["contents"][0]["parts"]
    assert [list(p)[0] for p in parts] == ["inline_data", "text"]    # his wav first, then the frozen prompt
    assert parts[0]["inline_data"]["mime_type"] == "audio/wav" and parts[1]["text"] == prompt == "PROMPT for line 2: مرحبا"


def test_build_writes_one_line_per_request_and_refuses_a_changed_prompt(bench):
    info = BB.build(DATE, 1)
    P = BB.paths(DATE, 1)
    rows = [json.loads(x) for x in open(P["jsonl"], encoding="utf-8")]
    assert info["requests"] == len(rows) == 3 and [r["key"] for r in rows] == ["0", "2", "5"]
    assert info["bytes"] == os.path.getsize(P["jsonl"]) and b"\r" not in open(P["jsonl"], "rb").read()
    p = os.path.join(bench["d"], "prompts.json")
    j = BC.J(p)
    j["arms"]["ctx"]["0"] += " (edited)"
    BC.W(p, j)
    with pytest.raises(SystemExit):
        BB.build(DATE, 1)


def _results(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_collect_maps_keys_back_to_lines_and_prices_at_half(bench):
    res = os.path.join(bench["d"], "res.jsonl")
    _results(res, [{"key": "5", "response": _answer("خمسة", "5amse")}, {"key": "0", "response": _answer("مرحبا", "mar7aba", tin=1000, aud=100, cand=50, thoughts=150)},
                   {"key": "2", "response": {"candidates": [{"content": {"parts": [{"text": "not json"}]}}], "usageMetadata": {"promptTokenCount": 10}}},
                   {"key": "99", "response": _answer("x", "y")}])
    rec = BB.collect_file(DATE, 1, res, {"job": "batches/abc", "submitted": "t"})
    assert rec["engine"] == "gemini-flash-batch-t1" and rec["mode"] == "line" and rec["run"] == 1 and rec["model"] == "gemini-3.8-flash" and rec["complete"] is True
    assert sorted(rec["lines"]) == ["0", "2", "5"]
    a = rec["lines"]["0"]
    assert (a["text"], a["alt"], a["tokens"]) == ("مرحبا", "mar7aba", [1000, 100, 200]) and a["raw"]["arabic"] == "مرحبا"
    p = BR.PRICE["gemini-3.8-flash"]
    full = (900 * p[0] + 100 * p[1] + 200 * p[2]) / 1e6
    assert a["usd"] == round(full / 2, 6) and full == pytest.approx(BR.gemini_parse("gemini-3.8-flash", _answer("م", "m", 1000, 100, 50, 150))["usd"])
    assert rec["lines"]["5"]["text"] == "خمسة" and rec["lines"]["2"]["error"] == "bad json"
    assert rec["cost_usd"] == pytest.approx(sum(v["usd"] for v in rec["lines"].values()), abs=1e-6)
    steps = [(a[1], a[5]) for a, k in bench["paid"]]                  # one run line per answer that cost money, at the half price
    assert len(steps) == 3 and all(e == "gemini-flash-batch-t1" for e, _ in steps)
    assert sum(u for _, u in steps) == pytest.approx(rec["cost_usd"], abs=1e-5)
    # the saved file is what the scorer reads; a second collect of the same file pays and logs nothing again
    on_disk = BC.J(BB.paths(DATE, 1)["run"])
    assert on_disk["complete"] is True and on_disk["lines"]["5"]["alt"] == "5amse"
    again = BB.collect_file(DATE, 1, res)
    assert len(bench["paid"]) == 3 and again["cost_usd"] == rec["cost_usd"]


def test_an_unreached_request_is_not_stored_and_a_real_failure_is(bench):
    res = os.path.join(bench["d"], "res.jsonl")
    _results(res, [{"key": "0", "response": _answer("مرحبا", "mar7aba")},
                   {"key": "2", "error": {"code": 8, "message": "You exceeded your current quota", "status": "RESOURCE_EXHAUSTED"}},
                   {"key": "5", "error": {"code": 3, "message": "Request contains an invalid argument.", "status": "INVALID_ARGUMENT"}}])
    rec = BB.collect_file(DATE, 2, res)
    assert sorted(rec["lines"]) == ["0", "5"] and rec["complete"] is False        # line 2 has no answer: the run is not scored
    assert rec["lines"]["5"] == {"text": "", "error": "400 Request contains an invalid argument.", "usd": 0.0}
    assert BV.unreached(BB.err_text({"code": 8, "message": "quota"})) and BV.unreached(BB.err_text({"code": 429, "message": "x"}))
    assert BV.unreached(BB.err_text({"message": "Your prepayment credits are depleted", "status": "RESOURCE_EXHAUSTED"}))
    assert not BV.unreached(BB.err_text({"code": 13, "message": "internal"}))
    # the missing line arrives in a later results file: only it is added
    _results(res, [{"key": "2", "response": _answer("تنين", "tnen")}, {"key": "0", "response": _answer("CHANGED", "c")}])
    rec = BB.collect_file(DATE, 2, res)
    assert rec["complete"] is True and rec["lines"]["2"]["text"] == "تنين" and rec["lines"]["0"]["text"] == "مرحبا"


def _baseline(d, n=1):
    BC.W(os.path.join(d, "gemini-flash-t1", "line-run%d.json" % n), {"complete": True, "lines": {i: {"text": "x", "tokens": [1000, 100, 200], "usd": 0.001} for i in ("0", "2", "5")}})


def test_submit_checks_the_cap_first_and_never_creates_a_job_twice(bench, monkeypatch):
    BB.build(DATE, 1)
    with pytest.raises(SystemExit, match="no baseline token counts"):
        BB.submit(DATE, 1)
    _baseline(bench["d"])
    p = BR.PRICE["gemini-3.8-flash"]
    est = BB.estimate(DATE, 1)
    assert est == round(3 * (900 * p[0] + 100 * p[1] + 200 * p[2]) / 1e6 / 2, 4)
    monkeypatch.setattr(BV, "money_base", lambda date, path, svc="gemini": (61.0, 61.0))       # the cap is reached: no upload
    with pytest.raises(SystemExit, match="budget cap"):
        BB.submit(DATE, 1)
    assert not os.path.exists(BB.paths(DATE, 1)["job"])
    monkeypatch.setattr(BV, "money_base", lambda date, path, svc="gemini": (10.0, 61.0))
    calls = []
    monkeypatch.setattr(BB, "upload_file", lambda path, name: calls.append(("upload", os.path.basename(path))) or "files/f1")
    monkeypatch.setattr(BB, "create_batch", lambda model, file_name, name: calls.append(("create", model, file_name)) or {"name": "batches/b1", "metadata": {"state": "JOB_STATE_PENDING"}})
    job = BB.submit(DATE, 1)
    assert calls == [("upload", "run1.jsonl"), ("create", "gemini-3.8-flash", "files/f1")]
    assert (job["job"], job["file"], job["state"], job["est_usd"]) == ("batches/b1", "files/f1", "JOB_STATE_PENDING", est) and job["submitted"]
    with pytest.raises(SystemExit, match="already submitted"):
        BB.submit(DATE, 1)
    assert len(calls) == 2
    assert BB.outstanding(DATE) == est and BB.outstanding(DATE, but=1) == 0.0      # owed until it is collected


def test_collect_downloads_only_a_succeeded_job(bench, monkeypatch):
    BC.W(BB.paths(DATE, 1)["job"], {"job": "batches/b1", "file": "files/f1", "est_usd": 0.5, "submitted": "t"})
    monkeypatch.setattr(BB, "get_batch", lambda name: {"name": name, "metadata": {"state": "JOB_STATE_RUNNING"}})
    with pytest.raises(SystemExit, match="JOB_STATE_RUNNING"):
        BB.collect(DATE, 1)
    monkeypatch.setattr(BB, "get_batch", lambda name: {"name": name, "done": True, "metadata": {"state": "JOB_STATE_SUCCEEDED"}, "response": {"responsesFile": "files/out1"}})

    def dl(name, out):
        assert name == "files/out1"
        _results(out, [{"key": k, "response": _answer("ا", "a")} for k in ("0", "2", "5")])
    monkeypatch.setattr(BB, "download_file", dl)
    rec = BB.collect(DATE, 1)
    assert rec["complete"] is True and rec["job"] == "batches/b1" and BB.outstanding(DATE) == 0.0
    # both status shapes of Google's docs are read
    assert BB.job_state({"state": "JOB_STATE_SUCCEEDED"}) == "JOB_STATE_SUCCEEDED" and BB.responses_file({"dest": {"fileName": "files/x"}}) == "files/x"


def test_compare_says_plainly_when_the_batch_runs_are_missing(bench, capsys):
    assert BB.compare(DATE) == 1
    assert "Nothing to compare yet" in capsys.readouterr().out
    s = {"moments": 63, "hit": 53, "hidden_slips": 1, "slips_judged": 24, "should_stay": 519, "content_changes": 59, "stable_pct": 90.5, "runs": 3, "cost_usd": 2.02}
    BC.W(os.path.join(bench["d"], "scores.json"), {"gemini-flash-t1|line": s, "gemini-flash-batch-t1|line": dict(s, hit=52, runs=1, cost_usd=0.56)})
    assert BB.compare(DATE) == 0
    out = capsys.readouterr().out
    assert "heard right (of 63)" in out and "53" in out and "52" in out and "not like for like" in out


def test_the_batch_engine_is_billed_to_gemini_and_named():
    import bench_report
    assert BR.root(BB.ENGINE) == "gemini-flash" and BR.SERVICE[BR.root(BB.ENGINE)] == "gemini"
    assert BB.ENGINE in bench_report.NAMES and BB.PRICE_FACTOR == 0.5


# ------------------------------------------------------------------ 2026-10-04: complete baseline, crash recovery, the missing lines as a later part

def test_estimate_refuses_an_incomplete_baseline_and_prices_the_lines_of_this_job(bench):
    d, p = bench["d"], BR.PRICE["gemini-3.8-flash"]
    line = (900 * p[0] + 100 * p[1] + 200 * p[2]) / 1e6 / 2
    tok = {"text": "x", "tokens": [1000, 100, 200], "usd": 0.001}
    base = os.path.join(d, "gemini-flash-t1", "line-run1.json")
    BC.W(base, {"complete": False, "lines": {i: tok for i in ("0", "2", "5")}})            # not marked complete
    assert BB.estimate(DATE, 1) is None
    BC.W(base, {"complete": True, "lines": {i: tok for i in ("0", "2")}})                  # a listen line is absent
    assert BB.estimate(DATE, 1) is None
    BC.W(base, {"complete": True, "lines": {"0": tok, "2": tok, "5": {"text": "x"}}})      # an answered line with no token counts
    assert BB.estimate(DATE, 1) is None
    BB.build(DATE, 1)
    with pytest.raises(SystemExit, match="no baseline token counts"):
        BB.submit(DATE, 1)
    BC.W(os.path.join(d, "gemini-flash-t1", "line-run3.json"), {"complete": True, "lines": {"0": tok, "2": tok, "5": {"text": "", "error": "400 bad"}}})
    assert BB.estimate(DATE, 1) == round(3 * line, 4)             # run 1 is not usable: any COMPLETE run is (a stored error needs no tokens)
    # the number of lines is the build's, not the baseline's: a part with one line costs one line
    BC.W(BB.paths(DATE, 1, 2)["build"], {"requests": 1})
    assert BB.estimate(DATE, 1, 2) == round(line, 4)


class Google:
    """A fake of the five network functions with a memory of the jobs that were created."""

    def __init__(self, monkeypatch):
        self.jobs, self.uploads, self.creates, self.fail_after_create = [], [], 0, False
        self.results = {}                                      # job name -> rows of its results file
        for name in ("upload_file", "create_batch", "get_batch", "download_file", "list_batches"):
            monkeypatch.setattr(BB, name, getattr(self, name))

    def upload_file(self, path, name):
        self.uploads.append(os.path.basename(path))
        return "files/f%d" % len(self.uploads)

    def create_batch(self, model, file_name, name):
        self.creates += 1
        job = {"name": "batches/b%d" % self.creates, "metadata": {"state": "JOB_STATE_PENDING", "displayName": name, "createTime": "2099-01-01T00:00:%02dZ" % self.creates}}
        self.jobs.append(job)
        if self.fail_after_create:
            raise RuntimeError("the connection dropped after Google created the job")
        return job

    def list_batches(self):
        return list(self.jobs)

    def get_batch(self, name):
        return {"name": name, "metadata": {"state": "JOB_STATE_SUCCEEDED"}, "response": {"responsesFile": "files/out-" + name.split("/")[1]}}

    def download_file(self, name, out):
        _results(out, self.results["batches/" + name.split("-")[1]])


def test_a_submit_that_crashed_after_create_is_recovered_and_never_created_twice(bench, monkeypatch, capsys):
    _baseline(bench["d"])
    BB.build(DATE, 1)
    g = Google(monkeypatch)
    g.fail_after_create = True
    with pytest.raises(RuntimeError):
        BB.submit(DATE, 1)
    job = BC.J(BB.paths(DATE, 1)["job"])                         # on disk before the create: the name that finds the job again
    assert job["job"] is None and job["display_name"].startswith("anees-run1-") and job["est_usd"] == BB.estimate(DATE, 1) and job["file"] == "files/f1"
    assert BB.outstanding(DATE) == job["est_usd"]                # owed although this PC has no job id
    g.fail_after_create = False
    rec = BB.submit(DATE, 1)                                     # the second submit attaches the job Google already has
    assert rec["job"] == "batches/b1" and rec["recovered"] and g.creates == 1 and g.uploads == ["run1.jsonl"]
    assert "recovered run 1: batches/b1" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="already submitted"):
        BB.submit(DATE, 1)
    assert g.creates == 1


def test_recover_cli_attaches_the_job_and_says_when_there_is_none(bench, monkeypatch, capsys):
    _baseline(bench["d"])
    BB.build(DATE, 2)
    g = Google(monkeypatch)
    P = BB.paths(DATE, 2)
    BC.W(P["job"], {"display_name": "anees-run2-x", "est_usd": 0.1, "file": "files/f1", "job": None})
    assert BB.recover(DATE, 2) == [] and "nothing was created" in capsys.readouterr().out
    g.jobs.append({"name": "batches/zz", "displayName": "anees-run2-x", "state": "BATCH_STATE_RUNNING"})
    rec = BB.recover(DATE, 2)
    assert [r["job"] for r in rec] == ["batches/zz"] and BC.J(P["job"])["state"] == "JOB_STATE_RUNNING"
    assert BB.recover(DATE, 2) == [] and "nothing to recover" in capsys.readouterr().out


def test_submit_missing_sends_only_the_unanswered_lines_and_collect_merges_the_parts(bench, monkeypatch, capsys):
    _baseline(bench["d"])
    BB.build(DATE, 1)
    g = Google(monkeypatch)
    BB.submit(DATE, 1)
    with pytest.raises(SystemExit, match="no collected answers yet"):
        BB.submit_missing(DATE, 1)
    g.results["batches/b1"] = [{"key": "0", "response": _answer("مرحبا", "mar7aba")},
                               {"key": "2", "error": {"code": 8, "message": "quota", "status": "RESOURCE_EXHAUSTED"}}]      # 5 is absent from the results
    rec = BB.collect(DATE, 1)
    assert sorted(rec["lines"]) == ["0"] and rec["complete"] is False and len(bench["paid"]) == 1
    assert BB.missing(DATE, 1) == ["2", "5"] and BB.outstanding(DATE) == 0.0       # part 1 was collected: nothing is owed for it
    monkeypatch.setattr(BV, "money_base", lambda date, path, svc="gemini": (61.0, 61.0))       # the cap also guards a part
    with pytest.raises(SystemExit, match="budget cap"):
        BB.submit_missing(DATE, 1)
    assert g.creates == 1
    monkeypatch.setattr(BV, "money_base", lambda date, path, svc="gemini": (10.0, 61.0))
    job2 = BB.submit_missing(DATE, 1)
    P1, P2 = BB.paths(DATE, 1), BB.paths(DATE, 1, 2)
    assert os.path.basename(P2["jsonl"]) == "run1.p2.jsonl" and g.uploads == ["run1.jsonl", "run1.p2.jsonl"] and job2["job"] == "batches/b2"
    orig = {json.loads(x)["key"]: x for x in open(P1["jsonl"], encoding="utf-8")}
    assert open(P2["jsonl"], encoding="utf-8").read() == orig["2"] + orig["5"]     # the same requests, line for line
    assert job2["requests"] == 2 and job2["est_usd"] == BB.estimate(DATE, 1, 2) == pytest.approx(BB.estimate(DATE, 1) * 2 / 3, abs=1e-4) and BB.outstanding(DATE) == job2["est_usd"]
    with pytest.raises(SystemExit, match="collect 1 first"):                       # its answers are still out: never a third job for the same lines
        BB.submit_missing(DATE, 1)
    assert g.creates == 2
    g.results["batches/b2"] = [{"key": "2", "response": _answer("تنين", "tnen")}, {"key": "5", "response": _answer("خمسة", "5amse")}]
    rec = BB.collect(DATE, 1)                                    # part 1 again (nothing new) + part 2
    assert rec["complete"] is True and sorted(rec["lines"]) == ["0", "2", "5"] and rec["job"] == "batches/b1" and rec["parts"] == {"2": "batches/b2"}
    assert len(bench["paid"]) == 3                               # one run line per answered line, none twice
    again = BB.collect(DATE, 1)
    assert len(bench["paid"]) == 3 and again["cost_usd"] == rec["cost_usd"] and BB.outstanding(DATE) == 0.0
    with pytest.raises(SystemExit, match="nothing to send again"):
        BB.submit_missing(DATE, 1)
    capsys.readouterr()
    BB.status(DATE)
    out = capsys.readouterr().out
    assert "run 1: batches/b1 JOB_STATE_SUCCEEDED" in out and "run 1 part 2: batches/b2 JOB_STATE_SUCCEEDED" in out
