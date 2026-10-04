# -*- coding: utf-8 -*-
"""The generic Gemini Batch transport (scripts/batch_jobs.py): no network, no paid call. Every job lives in a temp
folder and the five network functions are a fake `net` object that remembers the jobs it created."""
import json, os, sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import batch_jobs as BJ  # noqa: E402


class Net:
    def __init__(self):
        self.jobs, self.uploads, self.creates, self.crash, self.state, self.out = [], [], [], False, "JOB_STATE_SUCCEEDED", []

    def upload_file(self, path, display_name):
        self.uploads.append((os.path.basename(path), display_name))
        return "files/in%d" % len(self.uploads)

    def create_batch(self, model, file_name, display_name):
        self.creates.append((model, file_name, display_name))
        job = {"name": "batches/b%d" % len(self.creates), "metadata": {"state": "BATCH_STATE_PENDING", "displayName": display_name, "createTime": "2099-01-01T00:00:%02dZ" % len(self.creates)}}
        self.jobs.append(job)
        if self.crash:
            raise RuntimeError("dropped after the job was created")
        return job

    def list_batches(self):
        return list(self.jobs)

    def get_batch(self, name):
        return {"name": name, "metadata": {"state": self.state, "batchStats": {"requestCount": "2"}}, "response": {"responsesFile": "files/out1"}}

    def download_file(self, name, out):
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            for r in self.out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    for name in ("upload_file", "create_batch", "get_batch", "download_file", "list_batches"):         # a test that reaches the network fails loudly
        monkeypatch.setattr(BJ, name, lambda *a, _n=name, **k: (_ for _ in ()).throw(AssertionError("network call: " + _n)))


REQS = [("a", {"contents": [{"parts": [{"text": "مرحبا"}]}]}), ("b", {"contents": [{"parts": [{"text": "two"}]}]}), ("c", {"contents": [{"parts": [{"text": "three"}]}]})]


def _built(tmp_path, name="job"):
    d = str(tmp_path / "jobs")
    return d, BJ.build(d, name, "gemini-3.8-flash", iter(REQS), meta={"lesson": "2099-01-01"})


def test_build_writes_the_jsonl_and_what_was_built(tmp_path):
    d, info = _built(tmp_path)
    P = BJ.paths(d, "job")
    assert [os.path.basename(P[k]) for k in ("jsonl", "build", "job", "results")] == ["job.jsonl", "job.build.json", "job.job.json", "job.results.jsonl"]
    raw = open(P["jsonl"], "rb").read()
    lines = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
    assert lines == [{"key": k, "request": b} for k, b in REQS] and b"\r" not in raw and "مرحبا".encode("utf-8") in raw
    assert (info["name"], info["model"], info["requests"], info["bytes"], info["lesson"]) == ("job", "gemini-3.8-flash", 3, len(raw), "2099-01-01")
    assert len(info["jsonl_sha256"]) == 64 and len(info["keys_sha256"]) == 64 and info["built"] and json.load(open(P["build"], encoding="utf-8")) == info
    with pytest.raises(SystemExit, match="same key"):
        BJ.build(d, "dup", "m", [("a", {}), ("a", {})])


def test_submit_refuses_unbuilt_changed_capped_and_never_creates_twice(tmp_path):
    d, info = _built(tmp_path)
    net, P = Net(), BJ.paths(d, "job")
    with pytest.raises(SystemExit, match="not built"):
        BJ.submit(d, "other", 1.0, net=net)
    with pytest.raises(SystemExit, match="over the cap"):
        BJ.submit(d, "job", 1.0, cap_check=lambda e: "over the cap by $%.2f" % e, net=net)
    assert not os.path.exists(P["job"]) and not net.uploads                 # refused before anything was written or sent
    seen = []
    rec = BJ.submit(d, "job", 1.25, cap_check=lambda e: seen.append(e), net=net)
    assert seen == [1.25] and net.uploads == [("job.jsonl", rec["display_name"])] and net.creates == [("gemini-3.8-flash", "files/in1", rec["display_name"])]
    assert rec["display_name"].startswith("anees-job-%s" % info["jsonl_sha256"][:8])
    assert (rec["job"], rec["file"], rec["state"], rec["est_usd"], rec["requests"], rec["lesson"]) == ("batches/b1", "files/in1", "JOB_STATE_PENDING", 1.25, 3, "2099-01-01")
    assert json.load(open(P["job"], encoding="utf-8")) == rec
    with pytest.raises(SystemExit, match="already submitted"):
        BJ.submit(d, "job", 1.25, net=net)
    with pytest.raises(SystemExit, match="already submitted"):              # nor is the JSONL Google was sent built over
        BJ.build(d, "job", "m", REQS)
    assert len(net.creates) == 1
    d2, _ = _built(tmp_path, "edited")
    with open(BJ.paths(d2, "edited")["jsonl"], "a", encoding="utf-8") as f:
        f.write("\n")
    with pytest.raises(SystemExit, match="changed since it was built"):
        BJ.submit(d2, "edited", 1.0, net=net)


def test_the_display_name_is_saved_before_create_so_a_crash_is_recovered_not_paid_twice(tmp_path):
    d, _ = _built(tmp_path)
    net, P = Net(), BJ.paths(d, "job")
    net.crash = True
    with pytest.raises(RuntimeError):
        BJ.submit(d, "job", 2.0, net=net)                        # Google has the job; this PC never got its id
    job = json.load(open(P["job"], encoding="utf-8"))
    assert job["job"] is None and job["est_usd"] == 2.0 and job["display_name"] == net.jobs[0]["metadata"]["displayName"]
    net.crash = False
    rec = BJ.submit(d, "job", 2.0, cap_check=lambda e: "the cap is not asked for a job that already exists", net=net)
    assert rec["job"] == "batches/b1" and rec["recovered"] and rec["state"] == "JOB_STATE_PENDING" and len(net.creates) == 1 and len(net.uploads) == 1


def test_a_crash_before_google_created_anything_is_created_again_under_the_same_name(tmp_path):
    d, _ = _built(tmp_path)
    net, P = Net(), BJ.paths(d, "job")

    def boom(path, display_name):
        raise RuntimeError("upload dropped")
    net.upload_file, real = boom, net.upload_file
    with pytest.raises(RuntimeError):
        BJ.submit(d, "job", 2.0, net=net)
    first = json.load(open(P["job"], encoding="utf-8"))
    assert first["display_name"] and first["job"] is None and first["file"] is None
    net.upload_file = real
    rec = BJ.submit(d, "job", 2.0, net=net)                      # no remote job carries the name: upload + create, once
    assert rec["job"] == "batches/b1" and "recovered" not in rec and rec["display_name"] == first["display_name"] and len(net.creates) == 1


def test_recover_picks_the_job_by_display_name_newest_first_in_every_shape(tmp_path):
    d, _ = _built(tmp_path)
    net, P = Net(), BJ.paths(d, "job")
    assert BJ.recover(d, "job", net=net) is None                 # no job file
    BJ._W(P["job"], {"name": "job", "display_name": "anees-job-1", "est_usd": 1.0, "job": None})
    net.jobs = [{"name": "batches/other", "metadata": {"displayName": "anees-job-2", "createTime": "2099-01-09T00:00:00Z"}},
                {"name": "batches/old", "displayName": "anees-job-1", "createTime": "2099-01-01T00:00:00Z", "state": "JOB_STATE_FAILED"},
                {"name": "batches/new", "display_name": "anees-job-1", "create_time": "2099-01-02T00:00:00Z", "state": "BATCH_STATE_RUNNING"},
                {"name": "batches/mid", "metadata": {"displayName": "anees-job-1", "createTime": "2099-01-01T12:00:00Z", "state": "JOB_STATE_PENDING"}}]
    rec = BJ.recover(d, "job", net=net)
    assert (rec["job"], rec["state"]) == ("batches/new", "JOB_STATE_RUNNING") and rec["recovered"] and json.load(open(P["job"], encoding="utf-8")) == rec
    net.jobs = []
    assert BJ.recover(d, "job", net=net)["job"] == "batches/new"            # already attached: returned as it is, no lookup needed
    BJ._W(P["job"], {"name": "job", "display_name": "anees-job-9", "job": None})
    assert BJ.recover(d, "job", net=net) is None
    assert BJ.display_name({"metadata": {"displayName": "x"}}) == BJ.display_name({"displayName": "x"}) == BJ.display_name({"display_name": "x"}) == "x"


def test_status_and_fetch(tmp_path):
    d, _ = _built(tmp_path)
    net = Net()
    with pytest.raises(SystemExit, match="not submitted"):
        BJ.status(d, "job", net=net)
    BJ.submit(d, "job", 1.0, net=net)
    net.state = "BATCH_STATE_RUNNING"
    st = BJ.status(d, "job", net=net)
    assert st["state"] == "JOB_STATE_RUNNING" and st["stats"] == {"requestCount": "2"} and st["checked"]
    with pytest.raises(SystemExit, match="lesson 9: batches/b1 is JOB_STATE_RUNNING - nothing to collect yet"):
        BJ.fetch(d, "job", net=net, label="lesson 9")
    net.state, net.out = "JOB_STATE_SUCCEEDED", [{"key": "a", "response": {"candidates": []}}]
    path = BJ.fetch(d, "job", net=net)
    assert path == BJ.paths(d, "job")["results"] and [k for k, _, _ in BJ.rows(path)] == ["a"]
    net.out.append({"key": "b", "response": {"candidates": []}})
    assert [k for k, _, _ in BJ.rows(BJ.fetch(d, "job", net=net))] == ["a", "b"]         # fetching again is fine


def test_rows_reads_both_key_shapes_and_error_rows(tmp_path):
    p = str(tmp_path / "res.jsonl")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for r in ({"key": "a", "response": {"candidates": [1]}}, {"metadata": {"key": "b"}, "response": {"candidates": [2]}},
                  {"key": "c", "error": {"code": 8, "message": "You exceeded your current quota", "status": "RESOURCE_EXHAUSTED"}},
                  {"metadata": {"key": 7}, "status": {"code": 3, "message": "Request contains an invalid argument."}}, {"key": "e"}):
            f.write(json.dumps(r) + "\n")
        f.write("\n")
    assert list(BJ.rows(p)) == [("a", {"candidates": [1]}, None), ("b", {"candidates": [2]}, None), ("c", None, "429 You exceeded your current quota"),
                                ("7", None, "400 Request contains an invalid argument."), ("e", None, "no response")]
    assert BJ.err_text({"message": "x", "status": "RESOURCE_EXHAUSTED"}).startswith("429") and BJ.err_text("plain") == "plain" and BJ.err_text({"code": 13, "message": "internal"}) == "500 internal"
    assert BJ.job_state({"error": {"code": 3}}) == "JOB_STATE_FAILED" and BJ.job_state({}) == "JOB_STATE_UNKNOWN"
    assert BJ.responses_file({"metadata": {"output": {"responsesFile": "files/x"}}}) == "files/x" and "JOB_STATE_SUCCEEDED" in BJ.DONE and BJ.API.startswith("https://")


def test_missing_part_holds_exactly_the_missing_lines_copied_line_for_line(tmp_path):
    d, info = _built(tmp_path)
    net = Net()
    BJ.submit(d, "job", 3.0, net=net)
    part = BJ.missing_part(d, "job", ["c", "a"], 2)
    P1, P2 = BJ.paths(d, "job"), BJ.paths(d, "job.p2")
    orig = open(P1["jsonl"], "rb").read().split(b"\n")
    assert open(P2["jsonl"], "rb").read() == orig[0] + b"\n" + orig[2] + b"\n"            # the original order, the original bytes
    assert (part["name"], part["requests"], part["model"], part["part_of"], part["part"], part["lesson"]) == ("job.p2", 2, "gemini-3.8-flash", "job", 2, "2099-01-01")
    assert part["jsonl_sha256"] != info["jsonl_sha256"] and BJ.parts(d, "job") == [(1, "job"), (2, "job.p2")]
    rec = BJ.submit(d, "job.p2", 2.0, net=net)                   # then a job like any other
    assert rec["job"] == "batches/b2" and net.uploads[1][0] == "job.p2.jsonl" and rec["part_of"] == "job"
    with pytest.raises(SystemExit, match="already submitted"):
        BJ.missing_part(d, "job", ["b"], 2)
    with pytest.raises(SystemExit, match="not in the original"):
        BJ.missing_part(d, "job", ["b", "zz"], 3)
    assert not os.path.exists(BJ.paths(d, "job.p3")["jsonl"]) and BJ.parts(d, "job") == [(1, "job"), (2, "job.p2")]
    with pytest.raises(SystemExit, match="numbered 2"):
        BJ.missing_part(d, "job", ["b"], 1)
    assert BJ.missing_part(d, "job", ["b"], 3)["requests"] == 1


def test_list_batches_follows_the_page_token(monkeypatch):
    import requests
    monkeypatch.undo()                                           # the real list_batches, over a faked requests.get
    monkeypatch.setattr(BJ, "api_key", lambda: "k")
    pages = {None: {"operations": [{"name": "batches/1"}], "nextPageToken": "t2"}, "t2": {"batches": [{"name": "batches/2"}]}}
    asked = []

    class R:
        status_code = 200

        def __init__(self, j):
            self._j = j

        def json(self):
            return self._j

    def get(url, **k):
        asked.append((url, k["params"].get("pageToken"), k["headers"]["x-goog-api-key"]))
        return R(pages[k["params"].get("pageToken")])
    monkeypatch.setattr(requests, "get", get)
    assert [b["name"] for b in BJ.list_batches()] == ["batches/1", "batches/2"]
    assert asked == [(BJ.API + "/v1beta/batches", None, "k"), (BJ.API + "/v1beta/batches", "t2", "k")]
