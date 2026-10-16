# -*- coding: utf-8 -*-
"""The hearing harness's paid run step (scripts/hearing_run.py; Medi's yes 2026-10-14), with every engine faked: cells
C and F on the fixture lesson, the blind judge (no engine names, the picked letter mapped back), the cache (a rerun pays
nothing), the $ allowance (a step that would pass it sends nothing), cell D refused, the report."""
import json, os, re, sys, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import hearing_harness as HH  # noqa: E402
import hearing_run as HR  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "hearing_harness")
DATA = os.path.join(FX, "data")
D = "2026-01-01"


def _wav(path, secs=1.0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * secs))
    return path


def _root(tmp_path, limit=9.0):
    root = str(tmp_path / "harness")
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "spend.json"), "w", encoding="utf-8") as f:
        json.dump({"limit_usd": limit, "items": {}}, f)
    return root


def _lesson(tmp_path, monkeypatch, limit=9.0):
    root = _root(tmp_path, limit)
    L = HR.Lesson(D, DATA, root)

    def clip(self, i):
        p = _wav(os.path.join(self.dir, "clips", i.replace(".", "_") + ".wav"), 1.0 + float(i) / 1000.0)  # distinct bytes per line
        return p, HH.BC.sha_file(p)
    monkeypatch.setattr(HR.Lesson, "clip", clip)
    return L


def _versions(prompt):
    return dict(re.findall(r"Version ([XYZ]):\n(.*)\n", prompt))


class FakeGemini:
    """Batch stand-in: relisten answers echo the target; the judge picks the version holding a wanted word."""

    def __init__(self, want=("سمعت", "عصافير")):
        self.calls, self.prompts, self.want = 0, [], want

    def __call__(self, stage, todo):
        self.calls += 1
        out = {}
        for k, clip, prompt, cfg in todo:
            self.prompts.append((stage, prompt))
            if stage.startswith("judge"):
                vs = _versions(prompt)
                pick = next((L for L, t in sorted(vs.items()) if any(w in t for w in self.want)), "X")
                out[k] = {"text": "", "raw": {"pick": pick, "heard": vs.get(pick, ""), "why": "heard it"}, "usd": 0.001}
            else:
                tgt = re.search("«(.*)»", prompt).group(1)
                out[k] = {"text": tgt, "raw": {"arabic": tgt, "why": "his own word", "changes": []}, "usd": 0.002}
        return out


def _deepgram(monkeypatch, tmp_path):
    import rehear_audio as RA
    track = _wav(str(tmp_path / "medi-0.wav"), 2.0)
    monkeypatch.setattr(RA, "sources", lambda date: {"Medi": [{"file": track, "start": 0.0, "dur": 60.0}]})
    monkeypatch.setattr(RA, "whole_wav", lambda date, who, k, s: track)
    words = [("مرحبا", 10.1), ("كيفك", 10.5), ("أنا", 20.1), ("صحيت", 20.5), ("متأخر", 21.0), ("سما", 50.2)]
    calls = []

    def dg(path):
        calls.append(path)
        return {"text": " ".join(w for w, _ in words), "words": [{"text": w, "start": t, "end": t + 0.3} for w, t in words]}
    return {"deepgram": dg}, calls


def test_cell_C_votes_and_judges_blind(tmp_path, monkeypatch):
    L = _lesson(tmp_path, monkeypatch)
    G = FakeGemini(want=("سمعت",))
    net, dg_calls = _deepgram(monkeypatch, tmp_path)
    lines, info = HR.cell_C(L, HR.Gemini(L, net={"batch": G}, log=lambda *a: None), log=lambda *a: None, net=net)
    # 10: all three agree; 20: all differ -> judged, picked the version with سمعت (Gemini's);
    # 50: ElevenLabs + Deepgram (سما) outvote Gemini (عصافير); 40: not a listen line -> ElevenLabs
    assert lines["10.00"] == "مرحبا كيفك" and lines["20.00"] == "أنا سمعت متأخر" and lines["50.00"] == "سما"
    assert lines["40.00"] == "Okay so" and info["judged"] == 1
    judge_prompts = [p for s, p in G.prompts if s == "judge-C"]
    assert len(judge_prompts) == 1 and set(_versions(judge_prompts[0])) == {"X", "Y", "Z"}
    assert HH.leaks(judge_prompts[0]) == []
    for name in ("ElevenLabs", "Deepgram", "Gemini", "engine wrote"):
        assert name.lower() not in judge_prompts[0].lower()
    # the cache: a second run pays nothing and calls nothing
    n = G.calls
    HR.cell_C(L, HR.Gemini(L, net={"batch": G}, log=lambda *a: None), log=lambda *a: None, net=net)
    assert G.calls == n and len(dg_calls) == 1
    doc = HR.spend_doc(L.root)
    assert all(it["state"] == "paid" for it in doc["items"].values()) and HR.spent(L.root) > 0


def test_cell_F_both_relisten_then_blind_judge(tmp_path, monkeypatch):
    L = _lesson(tmp_path, monkeypatch)
    G = FakeGemini()
    his = {"10.00": "مرحبا كيفك", "20.00": "أنا سمعت متأخر", "30.00": "بدي أروح على البيت", "40.00": "", "50.00": "عصافير"}
    el_calls = []

    def eleven(path):
        el_calls.append(path)
        return {"text": "أنا صرت متأخر" if "20_00" in path else "سما"}
    lines, info = HR.cell_F(L, HR.Gemini(L, net={"batch": G}, log=lambda *a: None), log=lambda *a: None,
                            net={"eleven": eleven}, whole=(his, {}))
    assert info["disputed"] == 2 and len(el_calls) == 2                       # 20 and 50 differ from ElevenLabs raw
    assert lines["20.00"] == "أنا سمعت متأخر" and lines["50.00"] == "عصافير" and lines["40.00"] == "Okay so"
    jp = [p for s, p in G.prompts if s == "judge-F"]
    assert len(jp) == 2 and all(HH.leaks(p) == [] for p in jp)
    assert all(p.count("Reasons given with it") == 1 for p in jp)           # Gemini's reasons; ElevenLabs writes none
    # the relisten prompt holds Gemini's own text around, never ElevenLabs' line
    rl = [p for s, p in G.prompts if s == "relisten-F"]
    assert rl and not any("صرت" in p for p in rl)


def test_budget_stop_sends_nothing(tmp_path, monkeypatch):
    L = _lesson(tmp_path, monkeypatch, limit=0.0)
    G = FakeGemini()
    try:
        HR.judge(L, HR.Gemini(L, net={"batch": G}, log=lambda *a: None), "judge-C", [("20.00", [("a", ""), ("b", "")])])
        raise AssertionError("no stop")
    except HR.BudgetStop as e:
        assert "stopped, nothing sent" in str(e)
    assert G.calls == 0 and HR.spend_doc(L.root).get("items") == {}


def test_no_limit_means_no_run(tmp_path):
    root = str(tmp_path / "h")
    os.makedirs(root)
    try:
        HR.check_budget(0.01, "x", root)
        raise AssertionError("no stop")
    except HR.BudgetStop as e:
        assert "no harness limit" in str(e)


def test_cell_D_and_unknown_cells_refused(tmp_path):
    for c in ("D", "A"):
        try:
            HR.run(D, [c], data_root=DATA, root=_root(tmp_path))
            raise AssertionError("ran")
        except SystemExit as e:
            assert ("forced alignment" in str(e)) if c == "D" else ("cached" in str(e))


def test_cache_key_has_all_four_parts():
    a = HR.Cache.key("aa", "gemini-judge", "m", "p1")
    assert a != HR.Cache.key("ab", "gemini-judge", "m", "p1") != HR.Cache.key("aa", "gemini-judge", "m", "p2")
    assert a != HR.Cache.key("aa", "gemini-p1", "m", "p1") and a != HR.Cache.key("aa", "gemini-judge", "m2", "p1")


def test_report_scores_written_versions(tmp_path, monkeypatch):
    L = _lesson(tmp_path, monkeypatch)
    HR.write_version(L, "A", {"10.00": "مرحبا كيفك", "20.00": "أنا صحيت متأخر", "30.00": "بدي أروح على البيت", "50.00": "عصافير"}, {})
    HR.write_version(L, "B", {"10.00": "مرحبا كيفك", "20.00": "أنا سمعت متأخر", "30.00": "بدي أروح على البيت", "50.00": "عصافير"}, {})
    res = HR.report([D], DATA, L.root)[D]["rows"]
    by = {r["version"]: r for r in res}
    assert by["A"]["hidden"] == 1 and by["B"]["hidden"] == 0                  # A wrote the tutor's صحيت: an erased slip
    assert by["B"]["hit"] == by["A"]["hit"] + 1 and by["B"]["vs_A"]["only_this"] == 1


def test_harness_cli_run_needs_a_date_and_cell():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert HH.main(["run"]) == 2
    assert "paid" in buf.getvalue() and "forced alignment" in buf.getvalue()


def test_decision_needs_a_win_on_both_lessons(tmp_path):
    def rows(b_only, a_only, p, fcr):
        return {"rows": [{"version": "A", "label": "", "hit_rate": 90.0, "hidden": 1, "slips_judged": 40, "fcr": 2.5, "vs_A": None, "cost_usd": None},
                         {"version": "B", "label": "", "hit_rate": 93.0, "hidden": 1, "slips_judged": 40, "fcr": fcr,
                          "vs_A": {"only_this": b_only, "only_A": a_only, "p_sign": p}, "cost_usd": 0.6}]}
    res = {"d1": rows(20, 3, 0.001, 2.5), "d2": rows(9, 7, 0.8, 2.5)}
    assert HR.decide(res, "d1", "d2") == [{"version": "B", "wins_first": True, "wins_second": False, "adopt_candidate": False}]
    res["d2"] = rows(20, 2, 0.001, 5.0)                                     # wins on words but FCR rose: not a win
    assert HR.decide(res, "d1", "d2")[0]["wins_second"] is False
    res["d2"] = rows(20, 2, 0.001, 2.5)
    run = HR.write_experiments(res, "d1", "d2", path=str(tmp_path / "e.json"))
    assert run["winner"] == ["B"] and run["adopted"] is False


def test_review_fixes_2026_10_14(tmp_path, monkeypatch):
    # a dropped word: the version must keep the anchor, losing the whole line is not "erased"
    E = HH.slip_erased
    assert E("في المطعم", "المطعم", "كنت في المطعم", "") is False
    assert E("في المطعم", "المطعم", "كنت في المطعم", "كنت") is False
    assert E("في المطعم", "المطعم", "كنت في المطعم", "كنت المطعم") is True
    # an engine error is never cached (sent again next run) and is counted missing
    L = _lesson(tmp_path, monkeypatch)
    his = {"10.00": "مرحبا كيفك", "20.00": "أنا سمعت متأخر", "30.00": "بدي أروح على البيت", "40.00": "", "50.00": "عصافير"}
    lines, info = HR.cell_F(L, HR.Gemini(L, net={"batch": FakeGemini()}, log=lambda *a: None), log=lambda *a: None,
                            net={"eleven": lambda p: {"text": "", "error": "401 quota_exceeded"}}, whole=(his, {}))
    assert info["eleven_second_listen_missing"] == 2
    assert not any(e["engine"] == "elevenlabs" for e in L.cache.d.values())
    item = next(v for k, v in HR.spend_doc(L.root)["items"].items() if "eleven" in k)
    assert item["missing"] == 2 and item["usd"] == 0
    # a second attempt of the same step never overwrites the first one's money
    a = HR.reserve("d/x", 0.01, L.root)
    b = HR.reserve("d/x", 0.01, L.root)
    assert (a, b) == ("d/x", "d/x#2")


def test_judge_pick_written_as_version_letter(tmp_path, monkeypatch):
    L = _lesson(tmp_path, monkeypatch)

    def batch(stage, todo):
        return {k: {"text": "", "raw": {"pick": "Version Y.", "heard": ""}, "usd": 0.0} for k, *_ in todo}
    r = HR.judge(L, HR.Gemini(L, net={"batch": batch}, log=lambda *a: None), "judge-C",
                 [("20.00", [("a", ""), ("b", ""), ("c", "")])])
    jp = HH.judge_prompt_n([("a", ""), ("b", ""), ("c", "")], seed=D, item="20.00")
    assert r["20.00"][0] == jp["key"]["Y"]
