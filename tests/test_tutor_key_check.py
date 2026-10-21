# -*- coding: utf-8 -*-
"""AM-29 - the tutor's half of the exam's answer key (Medi 2026-10-11: "mix 30-20", after "Put it in the tutor panel I will
have amal work on it as well"): 50 blind moments of the 10-09 lesson on her Tutor page (30 tier-1 + 20 tier-2/3 lines of
docs/data/review-pick/2026-10-09.json, chosen by a hash of the date, in time order), her answers mirrored into data/ and
compared with the student's fast-review keys in the grade book (amal_check). scripts/build_tutor_key_check.py."""
import json, os, random, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "scripts"))
import build_tutor_key_check as TK  # noqa: E402

DATE = "2026-10-09"
DATA = json.loads((DOCS / "data" / ("amal-check-key-check-%s.json" % DATE)).read_text(encoding="utf-8"))
KEY = json.loads(Path(TK.key_path(DATE, str(ROOT))).read_text(encoding="utf-8"))
PICK = json.loads((DOCS / "data" / "review-pick" / (DATE + ".json")).read_text(encoding="utf-8"))


def fake_pick(n1=83, n2=92, n3=47, seed=1):
    r = random.Random(seed)
    lines, t = [], 10.0
    for tier in [1] * n1 + [2] * n2 + [3] * n3:
        lines.append({"t": round(t, 2), "end": round(t + 2, 2), "tier": tier})
        t += r.uniform(3, 9)
    r.shuffle(lines)
    return {"lines": lines}


def test_am_29_selection_is_30_unsure_plus_20_others_stable_per_date_in_time_order():
    pick = fake_pick()
    a = TK.select(pick, DATE)
    assert len(a) == 50
    assert sum(1 for x in a if x["tier"] == 1) == 30 and sum(1 for x in a if x["tier"] in (2, 3)) == 20
    assert [x["t"] for x in a] == sorted(x["t"] for x in a)                          # shown in time order
    shuffled = {"lines": list(reversed(pick["lines"]))}
    assert TK.select(shuffled, DATE) == a                                             # stable: input order does not matter
    assert TK.select(pick, "2026-10-12") != a                                         # the date seeds the choice
    few = TK.select(fake_pick(n1=10, n2=5, n3=0), DATE)                               # fewer lines than asked: all of them
    assert len(few) == 15


def test_am_29_the_10_09_list_is_the_selection_of_its_review_pick():
    assert DATA["date"] == DATE and DATA["kind"] == "key_check" and DATA["prefix"] == "keycheck" and DATA["list"] == "key-check-" + DATE
    assert DATA["n"] == len(DATA["items"]) == 50
    assert sum(1 for k in KEY["items"] if k["tier"] == 1) == 30 and sum(1 for k in KEY["items"] if k["tier"] in (2, 3)) == 20
    assert [x["id"] for x in DATA["items"]] == [k["id"] for k in KEY["items"]]
    assert [k["word_key"] for k in KEY["items"]] == ["keycheck:" + x["id"] for x in DATA["items"]]
    assert [x["t"] for x in DATA["items"]] == sorted(x["t"] for x in DATA["items"])
    # the frozen key is the seeded choice of the review pick (when the pick has not moved since); every line still exists
    at = {round(x["t"], 2): x for x in PICK["lines"]}
    assert all(round(k["t"], 2) in at for k in KEY["items"])
    assert KEY["quote"] == "mix 30-20" and KEY["rule"] == "AM-29"


def _keys(o, out=None):
    out = set() if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            out.add(k)
            _keys(v, out)
    elif isinstance(o, list):
        for v in o:
            _keys(v, out)
    return out


def test_am_29_cards_are_blind_no_chip_no_mark_no_tier_no_student_answer():
    keys = _keys(DATA["items"])
    for bad in ("tier", "why", "unsure", "random", "order", "blind", "propose", "chips", "c", "tmarks", "marks", "heard",
                "engine", "engine_wrote", "rule", "answer", "key", "verdict", "versions", "said", "right", "wrong", "s", "k"):
        assert bad not in keys, bad
    text = json.dumps(DATA, ensure_ascii=False)
    for bad in ("unsure", "tier", "robot", "chip", "✗", "second listen", "readers"):
        assert bad not in text.lower(), bad
    for x in DATA["items"]:
        assert set(x) <= {"id", "date", "mmss", "t", "end", "clips", "line", "rows"}
        assert x["line"]["label"] == "The student" and x["line"]["ar"]
        for r in x["rows"]:
            assert re.match(r"You, just (before|after) · (\d:)?\d\d:\d\d$", r["label"])
        c = x["clips"][0]
        assert c["fallback"].startswith(DATE + "/audio/lesson.mp3#t=")
        assert c["src"].startswith(DATE + "/clips/") or c["src"] == c["fallback"]
        st = float(c["fallback"].split("#t=")[1].split(",")[0])
        assert abs(st - max(0.0, x["t"] - 1)) < 0.02                                  # the lesson audio from 1 s before the line


def test_am_29_lines_arabizi_first_arabic_small_english_under():
    # S1 / PG-44: Arabizi first, the Arabic small after; PG-48: the English under it
    with_az = [x for x in DATA["items"] if x["line"].get("az")]
    assert len(with_az) >= 45
    assert sum(1 for x in DATA["items"] if x["line"].get("en")) >= 45
    js = (DOCS / "js" / "hub" / "check-task.js").read_text(encoding="utf-8")
    assert '<span class="ck-az" dir="auto">${esc(l.az)}</span><span class="ck-ar" lang="ar" dir="auto">' in js
    assert '<span class="ck-en" lang="en">' in js


def test_am_29_her_four_plain_sentences_about_the_student():
    (q,) = DATA["questions"]
    assert [(o["v"], o["label"]) for o in q["options"]] == [
        ("right", "The words are right and the student said it right"),
        ("words", "The words are not what the student said"),
        ("mistake", "The student made a mistake here"),
        ("cant_tell", "Can't tell from the recording")]
    box = {o["v"]: o.get("box") for o in q["options"]}
    assert box["words"] and "really say" in box["words"] and box["mistake"] and "optional" in box["mistake"]
    assert not box["right"] and not box["cant_tell"]
    words = " ".join([DATA["title"], DATA["intro"], DATA["what"]] + [o["label"] for o in q["options"]])
    assert not re.search(r"\bMedi\b|\bAmal\b|\bslips?\b", words)                     # PG-33, AM-24
    assert DATA["title"] == "Check 50 moments of the Oct 9 lesson (about 12 minutes)" and DATA["mins"] == 12


def test_am_29_one_row_on_her_to_do_counted_with_the_other_checks():
    T = json.loads((DOCS / "data" / "tutor.json").read_text(encoding="utf-8"))
    row = next(x for x in T["open"] if x["id"] == "check-key-check-" + DATE)
    assert row["kind"] == "check" and row["list"] == "key-check-" + DATE and row["total"] == 50 and row["unit"] == "moments"
    assert row["title"] == "Check 50 moments of the Oct 9 lesson (about 12 minutes)" and abs(row["min_each"] * 50 - 12) < 0.01
    rv = next(x for x in T["open"] if x["kind"] == "review")
    assert row["token"] == rv["token"]                                                # her review link's token, like her other checks
    src = (ROOT / "scripts" / "build_tutor_data.py").read_text(encoding="utf-8")
    assert 'KEY_CHECKS = os.path.join(DOCS, "data", "amal-check-key-check-*.json")' in src
    assert "build_tutor_key_check.build_all()" in src


def test_am_29_refresh_order_pulls_her_answers_then_the_grade_book():
    import amal_trigger as T
    names = [n for n, _ in T.STEPS]
    assert names.index("build_tutor_data") < names.index("tutor_key_check_pull") < names.index("review_grades")
    src = (ROOT / "scripts" / "amal_trigger.py").read_text(encoding="utf-8")       # the sandbox fixture empties SOURCES
    assert '"steps": ["tutor_more_check", "build_tutor_data", "tutor_key_check_pull", "tutor_note_check_pull", "review_grades"]' in src
    assert src.index('{"id": "listen_check"') < src.index('"steps": ["tutor_more_check", "build_tutor_data", "tutor_key_check_pull", "tutor_note_check_pull", "review_grades"]') < src.index('{"id": "tutor_notes"')
    hourly = (ROOT / "scripts" / "hourly_lessons.py").read_text(encoding="utf-8")
    assert hourly.index("'build_tutor_key_check.py pull'") < hourly.index("run_step('review_grades.py'")


def _her(word_key, answer, i, kind="key_check"):
    return {"id": i, "kind": kind, "word_key": word_key, "payload": {"answer": answer} if answer else {}, "created_at": "2026-10-12T00:00:%02d" % i}


def _his(t, key, ts, kind="rule-answer", relisten=False):
    p = {"review_mode": "fast", "key": key}
    if relisten:
        p["relisten"] = True
    return {"lesson_date": DATE, "turn_t": t, "kind": kind, "payload": p, "ts": ts}


def test_am_29_agreement_math():
    items = [{"id": "a", "word_key": "keycheck:a", "t": 10.0, "end": 12.0}, {"id": "b", "word_key": "keycheck:b", "t": 20.0, "end": 22.0},
             {"id": "c", "word_key": "keycheck:c", "t": 30.0, "end": 31.0}, {"id": "d", "word_key": "keycheck:d", "t": 40.0, "end": 41.0},
             {"id": "e", "word_key": "keycheck:e", "t": 50.0, "end": 51.0}, {"id": "f", "word_key": "keycheck:f", "t": 60.0, "end": 61.0}]
    her = [_her("keycheck:a", "right", 1),
           _her("keycheck:b", "right", 2), _her("keycheck:b", "words", 3),             # the latest tap wins
           _her("keycheck:c", "mistake", 4),
           _her("keycheck:d", "cant_tell", 5),                                         # answered, never compared
           _her("keycheck:e", "right", 6), _her("keycheck:e", None, 7, kind="undo"),  # undone: no answer
           _her("keycheck:f", "words", 8)]
    his = [_his(10.5, 1, "1"),                                                         # a: right / right -> agree
           _his(20.4, 3, "2", kind="add"), _his(20.5, 2, "3", kind="text"),           # b: his latest = 2 words -> agree
           _his(30.2, 1, "4"), _his(30.3, 1, "5", relisten=True),                     # c: mistake vs right -> disagree (re-listen ignored)
           _his(40.1, 1, "6"),                                                         # d: she can't tell -> not compared
           _his(50.1, 1, "7"),                                                         # e: undone -> not compared
           _his(60.2, 4, "8", kind="not-slip")]                                        # f: his key 4 -> not compared
    got = TK.agreement(items, her, his)
    assert got == {"total": 6, "answered": 5, "compared_n": 3, "agree_with_student_n": 2, "agreement_pct": 66.7}
    assert TK.agreement(items, [], his)["agreement_pct"] is None
    # a row without payload.key: the kind says which key (rule-answer 1, text 2, add 3)
    assert TK.his_key({"kind": "text", "payload": {}}) == 2 and TK.his_key({"kind": "add"}) == 3


def test_am_29_grade_book_row_and_never_a_page_change(tmp_path):
    import review_grades as RG
    repo = tmp_path / "repo"
    (repo / "data" / "lesson-work" / "review-grades").mkdir(parents=True)
    shutil.copy(TK.key_path(DATE, str(ROOT)), TK.key_path(DATE, str(repo)))
    k = KEY["items"]
    her = [_her(k[0]["word_key"], "right", 1), _her(k[1]["word_key"], "mistake", 2), _her(k[2]["word_key"], "cant_tell", 3)]
    his = [_his(k[0]["t"], 1, "1"), _his(k[1]["t"], 2, "2", kind="text"), _his(k[2]["t"], 1, "3")]
    got = RG.tutor_check(DATE, his, str(repo), her)
    assert got == {"total": 50, "answered": 3, "compared_n": 2, "agree_with_student_n": 1, "agreement_pct": 50.0}
    assert RG.tutor_check("2026-10-08", his, str(repo), her) is None                   # no key check for that lesson
    G = json.loads((DOCS / "data" / "review-grades.json").read_text(encoding="utf-8"))
    row = next(r for r in G["lessons"] if r["date"] == DATE)
    assert set(row["amal_check"]) == {"total", "answered", "compared_n", "agree_with_student_n", "agreement_pct"}
    js = (DOCS / "js" / "review-grades.js").read_text(encoding="utf-8")
    assert "Tutor and student agree on ${esc(ac.agree_with_student_n)} of ${esc(ac.compared_n)} lines" in js
    # her answers are a measurement: the builder and the pull write only their own files, never a lesson page
    src = (ROOT / "scripts" / "build_tutor_key_check.py").read_text(encoding="utf-8")
    assert "lessons\", date + \".json\")" in src and not re.search(r"W\([^)]*lessons", src)


def test_am_29_build_writes_only_its_own_files(tmp_path):
    repo = tmp_path / "repo"
    for rel in ("docs/data/review-pick/%s.json" % DATE, "docs/data/lessons/%s.json" % DATE):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, repo / rel)
    before = {p: p.stat().st_mtime_ns for p in repo.rglob("*") if p.is_file()}
    D = TK.build(DATE, str(repo), render=lambda texts: [None] * len(texts), log=lambda *a: None)
    after = {p for p in repo.rglob("*") if p.is_file()}
    new = sorted(str(p.relative_to(repo)).replace("\\", "/") for p in after - set(before))
    assert new == ["data/lesson-work/review-grades/tutor-check-%s-key.json" % DATE, "docs/data/amal-check-key-check-%s.json" % DATE]
    assert all(p.stat().st_mtime_ns == m for p, m in before.items())                  # the lesson page is never touched
    assert [x["id"] for x in D["items"]] == [TK.item_id(DATE, c["t"]) for c in TK.select(PICK, DATE)]
    # a second build reads the selection back from its key (frozen), whatever the pick says later
    (repo / ("docs/data/review-pick/%s.json" % DATE)).write_text(json.dumps({"lines": []}), encoding="utf-8")
    D2 = TK.build(DATE, str(repo), render=lambda texts: [None] * len(texts), log=lambda *a: None)
    assert [x["id"] for x in D2["items"]] == [x["id"] for x in D["items"]]
    # no Arabizi renderer: the Arabic alone (S1: never a guessed spelling)
    assert all(x["line"]["az"] is None for x in D["items"])
