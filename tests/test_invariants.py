# -*- coding: utf-8 -*-
"""One regression test per AI mistake that shipped and was caught afterwards
(docs/reports/ai-process-review-2026-09-27.html, section E), plus the gold-set freeze itself.

    python -m pytest tests/test_invariants.py -q

Each test names the bug it guards. They read committed files only: no network, no paid API.
"""
import glob, json, os, re, shutil, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
GOLD = ROOT / "gold"
sys.path.insert(0, str(GOLD))
import freeze  # noqa: E402  (gold/freeze.py)


def J(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def gold_file(gold_id):
    e = next(x for x in J(GOLD / "manifest.json")["sets"] if x["id"] == gold_id)
    return GOLD / e["path"]


def lessons():
    return J(DOCS / "data" / "lessons.json")["lessons"]


def lesson_detail(date):
    return J(DOCS / "data" / "lessons" / f"{date}.json")


def node():
    return os.environ.get("NODE") or shutil.which("node")


# ---------------------------------------------------------------- gold sets are frozen
def test_frozen_gold_sets_never_change():
    """Guards: tuning on test rows / silently editing a gold set. A changed set must be a new version."""
    m = J(GOLD / "manifest.json")
    ids = [e["id"] for e in m["sets"]]
    assert len(ids) == len(set(ids)), "duplicate gold id in manifest"
    assert freeze.verify(m) == [], "a frozen gold file changed - add a new version in gold/freeze.py instead"
    need = {"grammar@v1-tuned": 105, "grammar@v1-heldout": 29, "grammar@v2-audit": 1018, "arabizi@v1": 100,
            "sheet@v1": 98, "sheet@v2": 273}
    have = {e["id"]: e for e in m["sets"]}
    for i, n in need.items():
        assert have[i]["status"] == "frozen" and have[i]["n"] == n, i
    for e in m["sets"]:
        assert e.get("status") in {"frozen", "to-label", "not-saved", "to-collect", "pointer"}, e["id"]
        if e["status"] != "frozen":
            assert e.get("recipe") or e.get("note"), f"{e['id']}: a placeholder needs its labelling recipe"


# ---------------------------------------------------------------- 26 Sep: "Sep 23 shown as 100% with 35 errors"
@pytest.mark.parametrize("L", lessons(), ids=lambda L: L["date"])
def test_no_lesson_shows_a_score_that_ignores_its_listed_errors(L):
    """Guards f4251a9: the Lessons page showed Sep 23 at 100% while listing 35 word errors
    (the audit's slips were listed but not counted). Every on-sheet error card must be in the Words %."""
    P = lesson_detail(L["date"])
    w, g = L["words"], L["grammar"]
    on = [e for e in P["vocab_errors"] if e.get("on_sheet") is not False]
    on_wrong = sum(1 for e in on if e.get("kind") == "wrong")
    if w.get("scored"):
        assert w["pct"] == pytest.approx(100 * (w["right"] + .5 * w["partial"]) / w["scored"], abs=0.051), "words.pct formula"
    assert w["wrong"] == on_wrong, f"{on_wrong} on-sheet 'wrong' cards listed but words.wrong = {w['wrong']}"
    assert w["partial"] >= len(on) - on_wrong, "listed 'asked' cards missing from words.partial"
    if w.get("pct") == 100:
        assert not on, f"words 100% with {len(on)} on-sheet errors listed"
    assert L["counts"]["vocab_errors"] == len(P["vocab_errors"])
    assert L["counts"]["grammar_errors"] == len(P["grammar_errors"])
    if g.get("mistakes") is not None:
        assert g["mistakes"] == len(P["grammar_errors"]), "grammar mistakes counted != grammar cards listed"
    if g.get("pct") == 100:
        assert not P["grammar_errors"], f"grammar 100% with {len(P['grammar_errors'])} errors listed"


# ---------------------------------------------------------------- 27 Sep: "56 of 98 'new' words were already on your list"
def _cards():
    out = {}
    for f in glob.glob(str(DOCS / "data" / "lessons" / "20*.json")):
        d = os.path.basename(f)[:10]
        P = J(f)
        for e in P["vocab_errors"]:
            out.setdefault((d, e.get("mmss")), []).append(("shown", e))
        for e in P.get("not_errors", []):
            out.setdefault((d, e.get("mmss")), []).append(("dropped", e))
    return out


def test_sheet_v1_known_list_words_never_flagged_new():
    """Guards aa1e7f8: the string match called 56 of 98 words 'not on sheet' that were on Medi's list."""
    cards, bad, seen = _cards(), [], 0
    for v in J(gold_file("sheet@v1"))["verdicts"]:
        if v["verdict"] != "on_list":
            continue
        for where, e in cards.get((v["date"], v["mmss"]), []):
            seen += 1
            if where == "shown" and e.get("on_sheet") is False:
                bad.append(f"{v['date']} {v['mmss']} {v['arabic']}")
    assert seen >= 56, f"only {seen} of the 56 known on-list cards are still on the page (card keys moved?)"
    assert not bad, "known on-list words flagged 'Not on sheet': " + "; ".join(bad)


def test_sheet_v2_every_hand_verdict_is_applied():
    """Guards the 5-patches-in-one-night sheet check (one fix did nothing: a typo turned the rule off).
    Every card verdict in sheet@v2 must show on the page exactly as judged."""
    cards, bad = _cards(), []
    for v in J(gold_file("sheet@v2"))["verdicts"]:
        hits = [(w, e) for w, e in cards.get((v["date"], v["mmss"]), []) if e.get("arabic") == v["arabic"]]
        if not hits:
            continue          # the card left the page (a later audit may drop it); the v1 test checks coverage
        for where, e in hits:
            if v["verdict"] == "on_list" and not (where == "shown" and e.get("on_sheet") is True):
                bad.append(("on_list", v["date"], v["mmss"], where, e.get("on_sheet")))
            if v["verdict"] == "new" and not (where == "shown" and e.get("on_sheet") is False):
                bad.append(("new", v["date"], v["mmss"], where, e.get("on_sheet")))
            if v["verdict"] in ("not_an_error", "duplicate") and where != "dropped":
                bad.append((v["verdict"], v["date"], v["mmss"], where))
    assert not bad, bad[:10]


# ---------------------------------------------------------------- 26 Sep: card says 961 rows, audit file says 1,018
AUDIT_FILE = ROOT / "data" / "full-audit-2026-09-26.json"
# Cards already known to be stale when this test was written (2026-09-27). Fix the card (or give it "as_of"),
# then delete its slug here: a new stale card fails at once.
KNOWN_STALE = {"process-audit-2026-09-26": "says 961 rows (audit build 05:16); the audit now has 1,018",
               "ai-process-review-2026-09-27": "says '104 of 961 rows'; the audit now has 1,018"}


def _cards_citing_audit_size():
    rows = J(AUDIT_FILE)["totals"]["rows"]
    out = []
    for c in J(DOCS / "data" / "ai_reports.json")["reports"]:
        s = json.dumps({k: v for k, v in c.items() if k not in ("links", "source_md")}, ensure_ascii=False)
        nums = {int(x.replace(",", "")) for x in re.findall(r"(?<![\d.,])(\d,\d{3}|\d{3,4})(?![\d.%,])", s)}
        near = sorted(n for n in nums if abs(n - rows) <= 0.1 * rows)       # a number that claims to be the audit size
        if near:
            out.append(pytest.param(c, near, rows, id=c["slug"]))
    return out


@pytest.mark.parametrize("c,near,rows", _cards_citing_audit_size())
def test_ai_report_cards_match_the_audit_file(c, near, rows):
    """Guards the stale AI Reports card: a card quoting the full-audit size must equal the file, or say 'as of'."""
    if c["slug"] in KNOWN_STALE:
        pytest.xfail("known stale card: " + KNOWN_STALE[c["slug"]])
    pinned = c.get("as_of") or "as of" in json.dumps(c, ensure_ascii=False).lower()
    assert pinned or near == [rows], f"{c['slug']} quotes {near}, {AUDIT_FILE.name} has {rows} rows"


def test_audit_file_totals_match_its_rows():
    a = J(AUDIT_FILE)
    assert a["totals"]["rows"] == len(a["rows"])


# ---------------------------------------------------------------- 26 Sep: "why no arabizi again"
def test_every_error_card_word_has_arabizi():
    """Guards the missing-Arabizi cards (rule S1), second time round. Wraps scripts/arabizi_gaps.cjs."""
    n = node()
    if not n:
        pytest.skip("node not on PATH (set NODE=... or install Node 20); CI runs this")
    r = subprocess.run([n, str(ROOT / "scripts" / "arabizi_gaps.cjs")], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------------- 5 Sep: the hourly task overwrote the two-track lesson
def test_two_track_lessons_keep_their_per_speaker_source():
    """Guards d8037b9 (E1): a lesson recorded as one track per person must never be re-labelled from the mixed audio."""
    found = 0
    for tj in glob.glob(str(ROOT / "data" / "lessons" / "20*" / "tracks" / "tracks.json")):
        d = Path(tj).parent.parent
        tracks = J(tj)["tracks"]
        assert len({t["participant"] for t in tracks}) >= 2, d.name
        s = J(d / "summary.json")
        assert str(s.get("speaker_split", "")).startswith("ok: one audio track per person"), \
            f"{d.name}: two tracks on disk but the summary says {s.get('speaker_split')!r} (mixed audio overwrote it?)"
        found += 1
    assert found >= 1, "no two-track lesson source in data/lessons (2026-09-05 should be there)"


def test_pipeline_never_retranscribes_an_existing_scribe_json(tmp_path, monkeypatch):
    """Guards E1 in scripts/lesson_pipeline.process: an existing scribe.json is reused byte for byte."""
    pytest.importorskip("requests")
    import lesson_pipeline as lp
    date = "2099-01-01"
    d = tmp_path / date
    d.mkdir()
    raw = json.dumps({"words": [{"text": "two-track", "type": "word", "start": 0, "end": 1, "speaker_id": "Amal"}]})
    (d / "scribe.json").write_text(raw, encoding="utf-8")

    class Stop(Exception):
        pass

    def boom(*a, **k):
        raise AssertionError("transcribe() called although scribe.json exists")

    seen = {}

    def fake_build(res, *a, **k):
        seen["res"] = res
        raise Stop

    monkeypatch.setattr(lp, "LESSONS", tmp_path)
    monkeypatch.setattr(lp, "transcribe", boom)
    monkeypatch.setattr(lp, "extract_audio", lambda src, dst: dst)
    monkeypatch.setattr(lp, "chat_sidecar", lambda src: [(0, "Amal", "x")])
    monkeypatch.setattr(lp, "is_arabic_lesson", lambda *a: True)
    monkeypatch.setattr(lp, "build", fake_build)
    with pytest.raises(Stop):
        lp.process(tmp_path / "meet.mp4", date, "1200")
    assert seen["res"]["words"][0]["text"] == "two-track"
    assert (d / "scribe.json").read_text(encoding="utf-8") == raw


def test_hourly_transcribe_once_reuses_a_saved_transcript(tmp_path, monkeypatch):
    """Guards the same bug in scripts/hourly_lessons.transcribe_once (the hourly task's own path)."""
    pytest.importorskip("requests")
    import hourly_lessons as hl
    import lesson_pipeline as lp
    if not hasattr(hl, "transcribe_once"):
        pytest.skip("hourly_lessons.transcribe_once renamed; update this guard")
    out = tmp_path / "scribe_Amal.json"
    out.write_text('{"words": []}', encoding="utf-8")
    monkeypatch.setattr(lp, "transcribe", lambda *a, **k: (_ for _ in ()).throw(AssertionError("re-transcribed")))
    hl.transcribe_once(out, tmp_path / "Amal.mp3", "test")
    assert out.read_text(encoding="utf-8") == '{"words": []}'


# ---------------------------------------------------------------- 23 Sep: 09-18 speakers came out swapped
AR = re.compile(r"[ء-ي]+")


def _sec(s):
    v = 0.0
    for x in str(s).split(":"):
        v = v * 60 + float(x)
    return v


def _speaker_agreement():
    """Per lesson: of the audit rows whose Medi line / Amal line can be found on the lesson page
    (>= 60% of its Arabic words, within 15 s), how many sit on a turn labelled with the right speaker."""
    by = {}
    for line in open(gold_file("grammar@v2-audit"), encoding="utf-8"):
        r = json.loads(line)
        by.setdefault(r["date"], []).append(r)
    out = {}
    for L in lessons():
        T = [t for t in lesson_detail(L["date"])["turns"] if t.get("who") in ("Medi", "Amal")]
        ok = bad = 0
        for r in by.get(L["date"], []):
            for key, tk, who in (("amal_said", "t_amal", "Amal"), ("medi_said", "t", "Medi")):
                s, t = r.get(key), r.get(tk)
                toks = set(AR.findall(s or ""))
                if not t or len(toks) < 2:
                    continue
                t = _sec(t)
                best, bs = None, 0
                for x in T:
                    if abs(x["t"] - t) <= 15:
                        sc = len(toks & set(AR.findall(x.get("text") or ""))) / len(toks)
                        if sc > bs:
                            best, bs = x, sc
                if best and bs >= 0.6:
                    ok, bad = (ok + 1, bad) if best["who"] == who else (ok, bad + 1)
        out[L["date"]] = (ok, bad)
    return out


def test_speakers_not_swapped():
    """Guards 2026-09-18 ('more Arabic = Amal' flipped the labels). Cheap proxy until speaker@v1 is labelled:
    audit rows put Amal's fix on Amal's turns. Today every lesson agrees >= 92%; a swap gives ~5%."""
    low = {}
    for d, (ok, bad) in _speaker_agreement().items():
        if ok + bad >= 10 and ok / (ok + bad) < 0.8:
            low[d] = f"{ok}/{ok + bad}"
    assert not low, f"speaker labels look swapped on: {low}"
