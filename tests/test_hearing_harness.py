# -*- coding: utf-8 -*-
"""The hearing harness skeleton (overnight brief 2026-10-10 section 5; protocol section 5): cell presets, dry-run on a
fixture lesson, hit rate + FCR on a hand-made key, the blind judge prompt (no engine name, coin swap), the cache key,
and `run` refusing (no paid path)."""
import io, os, re, sys, contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import hearing_harness as HH  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "hearing_harness")
DATA, RAW = os.path.join(FX, "data"), os.path.join(FX, "raw")
D = "2026-01-01"


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = HH.main(argv)
    return code, buf.getvalue()


# ------------------------------------------------------------------ cells and switches

def test_named_cells_are_the_protocol_setups():
    assert sorted(HH.CELLS) == list("ABCDEF")
    a = HH.cell("A")
    assert a["proposer"] == ("eleven",) and a["cutter"] == "eleven" and a["listens"] == 3
    assert a["settle"] == "majority" and a["context"] == "full"
    assert HH.cell("b")["proposer"] == ("gemini",) and HH.cell("B")["listens"] == 0
    assert set(HH.cell("C")["proposer"]) == {"eleven", "deepgram"} and HH.cell("C")["judge"] == "gemini"
    assert HH.cell("E")["listens"] == 2
    assert HH.cell("F")["settle"] == "second-listen" and HH.cell("F")["judge"] == "gemini"
    for k in HH.CELLS:
        HH.validate(HH.cell(k))                                   # every preset uses only protocol values


def test_switch_flags_override_a_cell():
    ap = HH.build_parser()
    a = ap.parse_args(["dry-run", D, "--cell", "A", "--listens", "1", "--context", "masked"])
    name, cfg = HH.config_from_args(a)
    assert name == "custom" and cfg["listens"] == 1 and cfg["context"] == "masked" and cfg["proposer"] == ("eleven",)
    a = ap.parse_args(["dry-run", D, "--cell", "C"])
    assert HH.config_from_args(a)[0] == "C"
    a = ap.parse_args(["dry-run", D, "--proposer", "gemini,deepgram", "--settle", "majority"])
    name, cfg = HH.config_from_args(a)
    assert name == "custom" and cfg["proposer"] == ("gemini", "deepgram")


def test_bad_switch_values_are_refused():
    bad = HH.cell("A")
    bad["proposer"] = ("whisper",)
    try:
        HH.validate(bad)
        assert False
    except ValueError:
        pass
    bad = HH.cell("A")
    bad["settle"], bad["judge"] = "judge", "none"
    try:
        HH.validate(bad)
        assert False
    except ValueError:
        pass


# ------------------------------------------------------------------ cache key

def test_cache_key_has_four_parts():
    k = HH.cache_key("a" * 64, "gemini", "gemini-3.8-flash", "p" * 64)
    assert k == HH.cache_key("a" * 64, "gemini", "gemini-3.8-flash", "p" * 64) and len(k) == 64
    assert k != HH.cache_key("b" * 64, "gemini", "gemini-3.8-flash", "p" * 64)
    assert k != HH.cache_key("a" * 64, "deepgram", "gemini-3.8-flash", "p" * 64)
    assert k != HH.cache_key("a" * 64, "gemini", "gemini-3.1-pro-preview", "p" * 64)
    assert k != HH.cache_key("a" * 64, "gemini", "gemini-3.8-flash", "q" * 64)
    assert HH.cache_key("a" * 64, "deepgram", "nova-3") == HH.cache_key("a" * 64, "deepgram", "nova-3", "")
    try:
        HH.cache_key("", "gemini", "m")
        assert False
    except ValueError:
        pass


# ------------------------------------------------------------------ dry-run

def test_inventory_lists_cached_outputs_per_engine():
    inv = HH.inventory(D, DATA, RAW)
    assert len([r for r in inv["elevenlabs"] if r["what"].startswith("whole track")]) == 2
    g = [r for r in inv["gemini"] if r["what"].startswith("line listen base-run")]
    assert len(g) == 2 and all(r["complete"] for r in g)
    assert "deepgram" not in inv and any("review-grades" in r["what"] for r in inv["key"])


def test_prices_come_from_the_repo():
    P = HH.prices(DATA, RAW, D)
    assert abs(P["gemini_line_call"][0] - 0.0015) < 1e-9          # (0.002 + 0.004) / (2 + 2) lines, this lesson's runs
    assert abs(P["gemini_whole_per_min"][0] - 0.015) < 1e-9       # 0.30 / 20 min (2026-01-02)
    assert abs(P["deepgram_per_min"][0] - 0.0043) < 1e-9          # scripts/bench_run.py PRICE
    assert abs(P["eleven_whole_per_min"][0] - 0.27 / 60) < 1e-9   # pipeline_ext: 0.22 + 0.05 keyterms per hour
    assert abs(P["eleven_whole_per_min_observed"][0] - 0.0045) < 1e-9
    for k, (v, src) in P.items():
        assert src and v is not None, k


def test_disputed_lines_from_the_cache():
    disp, listen = HH.disputed_lines(D, DATA)
    assert [ln["i"] for ln in disp] == [2, 5] and len(listen) == 4


def test_dry_run_cells_cached_vs_paid():
    res = HH.dry_run(D, DATA, RAW, out=lambda *a: None)
    c = res["cells"]
    assert c["E"]["cached_all"] and c["E"]["paid_usd"] == 0           # 2 listens, both cached
    assert abs(c["A"]["paid_usd"] - 0.006) < 1e-6                     # listen 3 missing: 4 lines x 0.0015
    assert abs(c["B"]["paid_usd"] - 0.15) < 1e-6                      # whole track: 10 min x 0.015
    assert abs(c["C"]["paid_usd"] - (10 * 0.0043 + 2 * 0.0015)) < 1e-6   # Deepgram + judge on the 2 disputed clips
    f = 0.15 + 2 * 0.0015 + 4.5 * 0.22 / 3600 + 2 * 0.0015            # whole + Gemini 2nd listen + ElevenLabs 2nd listen + judge
    assert abs(c["F"]["paid_usd"] - round(f, 4)) < 1e-6
    d_rows = c["D"]["rows"]
    assert any("NOT BUILT" in r["how"] for r in d_rows if not r["cached"])
    assert not any(r["cached"] for r in c["A"]["rows"] if "listen 3" in r["need"])


def test_dry_run_cli_prints_every_cell_and_spends_nothing():
    code, out = run_cli(["--data", DATA, "--raw", RAW, "dry-run", D])
    assert code == 0
    for k in "ABCDEF":
        assert re.search(r"^%s\s" % k, out, re.M), k
    assert "spends nothing" in out and "Unit prices" in out
    code, out = run_cli(["--data", DATA, "--raw", RAW, "dry-run", D, "--cell", "B"])
    assert code == 0 and re.search(r"^B\s", out, re.M) and not re.search(r"^A\s", out, re.M)


# ------------------------------------------------------------------ scorer

def test_score_hit_rate_and_fcr_on_a_hand_made_key():
    key = HH.load_key(D, DATA)
    assert key["kind"] == "grades" and len(key["words"]) == 8
    texts, info = HH.load_version(os.path.join(FX, "versions", "x.json"), key)
    s = HH.score_version(key, texts)
    # 10: 2/2; 20: سمعت missed (wrote the tutor's صحيت), متأخر; 30: بدي + البيت, أروح missed; 50: عصافير
    assert (s["hit"], s["words"], s["hit_rate"]) == (6, 8, 75.0)
    # slips: 20 erased (صحيت written), 50 kept; the grammar slip has no right form: not judged
    assert (s["hidden"], s["slips_judged"], s["slips"], s["fcr"]) == (1, 2, 3, 50.0)
    assert s["hidden_rows"][0]["id"] == "20.00"


def test_score_engine_raw_and_a_rehear_run_with_fallback():
    key = HH.load_key(D, DATA)
    e = HH.score_version(key, HH.load_version("@engine", key)[0])
    # the engine wrote صرت (not his سمعت) and سما (the tutor's form: an erased slip)
    assert (e["hit"], e["words"], e["hidden"], e["slips_judged"]) == (6, 8, 1, 2)
    texts, info = HH.load_version(os.path.join(DATA, "lesson-work", "rehear", D, "base-run1.json"), key)
    assert info["from_version"] == 2 and info["from_fallback"] == 3      # rehear line numbers mapped to key line ids
    g = HH.score_version(key, texts)
    assert (g["hit"], g["hit_rate"], g["hidden"], g["fcr"]) == (8, 100.0, 0, 0.0)
    texts, info = HH.load_version(os.path.join(DATA, "lesson-work", "rehear", D, "base-run2.json"), key)
    assert info["errors"] == 1
    g2 = HH.score_version(key, texts)
    assert g2["hit"] == 5 and g2["hidden"] == 1             # a failed call = nothing written: both words of line 20 missed


def test_paired_word_by_word():
    key = HH.load_key(D, DATA)
    x = HH.score_version(key, HH.load_version(os.path.join(FX, "versions", "x.json"), key)[0])
    e = HH.score_version(key, HH.load_version("@engine", key)[0])
    p = HH.paired(x, e)
    assert (p["both"], p["only_first"], p["only_second"], p["neither"]) == (5, 1, 1, 1)
    assert p["p_sign"] == 1.0
    assert HH.sign_test(0, 10) < 0.01


def test_score_against_a_bench_key_reuses_bench_score():
    key = HH.load_key("2026-01-03", DATA)
    assert key["kind"] == "bench"
    s = HH.score_version(key, HH.load_version(os.path.join(FX, "versions", "bench-v.json"), key)[0])
    assert (s["hit"], s["words"]) == (5, 6) and (s["hidden"], s["slips_judged"], s["fcr"]) == (1, 1, 100.0)


def test_score_cli():
    code, out = run_cli(["--data", DATA, "--raw", RAW, "score", D, "--version", os.path.join(FX, "versions", "x.json"), "--version", "@engine"])
    assert code == 0 and "6/8 (75.0%)" in out and "1/2 (50.0%)" in out and "paired" in out


# ------------------------------------------------------------------ blind judge prompt

def test_judge_prompt_has_no_engine_name():
    a = "Gemini heard: غير لو. ElevenLabs wrote it."
    b = "قير لاو (deepgram nova-3 / OpenAI gpt / Claude)"
    res = HH.judge_prompt(a, b, seed=1, item="x", context="Google Scribe Cohere Speechmatics Whisper",
                          reasons_a="gemini-3.8-flash thinks so", reasons_b="scribe_v2 second listen")
    low = res["prompt"].lower()
    for name in HH.ENGINE_NAMES:
        assert name not in low, name
    for name in ("gemini", "elevenlabs", "deepgram", "openai", "claude", "google", "cohere", "whisper", "speechmatics", "scribe", "gpt", "nova-3"):
        assert name not in low, name
    assert HH.leaks(res["prompt"]) == []
    assert "Version X" in res["prompt"] and "Version Y" in res["prompt"]
    assert "غير لو" in res["prompt"] and "قير لاو" in res["prompt"]       # the words themselves are kept
    assert HH.scrub("he said eleven") == "he said eleven"                   # a plain number word is his speech, not a name


def test_judge_prompt_coin_swaps_order_and_keeps_the_key():
    seen = {}
    for n in range(200):
        r = HH.judge_prompt("AAA", "BBB", seed=42, item=str(n))
        x_text = r["prompt"].split("Version X:\n", 1)[1].split("\n", 1)[0]
        assert x_text == ("BBB" if r["swapped"] else "AAA")
        assert r["key"]["X"] == ("b" if r["swapped"] else "a") and {r["key"]["X"], r["key"]["Y"]} == {"a", "b"}
        seen[r["swapped"]] = seen.get(r["swapped"], 0) + 1
    assert 60 < seen[True] < 140 and 60 < seen[False] < 140                 # a fair coin
    assert HH.judge_prompt("A", "B", seed=7, item="85.25") == HH.judge_prompt("A", "B", seed=7, item="85.25")   # seeded


# ------------------------------------------------------------------ no paid path

def test_run_refuses():
    for argv in (["run"], ["run", "--cell", "B"], ["run", "2026-10-08", "--proposer", "gemini"]):
        code, out = run_cli(argv)
        assert code == 2 and "not built: paid runs need Medi's yes" in out


def test_no_paid_module_or_network_is_imported():
    src = open(os.path.join(ROOT, "scripts", "hearing_harness.py"), encoding="utf-8").read()
    for bad in ("import bench_run", "import bench_batch", "import rehear_job", "import requests", "urllib", "http.client",
                "import pipeline_ext", "import context_transcribe", "subprocess"):
        assert bad not in src, bad
