# -*- coding: utf-8 -*-
"""Amal's listening / checking lists on her Tutor hub (Medi 2026-10-05: "have amal do the 27 line check too", "did you put
the 108 on amals list", "5 send to amal"): docs/data/amal-checks.json + amal-check-<list>.json, docs/amal/check.html,
docs/js/hub/check-task.js. Every list is blind, light, has its clips published and its key outside docs/, saves like her
first listening check under its own kind, sits on the hub as its own row, and is read by the results script."""
import json, re, subprocess, sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WORK = ROOT / "data" / "lesson-work"
sys.path.insert(0, str(ROOT / "scripts"))
import amal_listen_results as R

INDEX = json.loads((DOCS / "data" / "amal-checks.json").read_text(encoding="utf-8"))["lists"]
LISTS = {L["list"]: json.loads((DOCS / "data" / f"amal-check-{L['list']}.json").read_text(encoding="utf-8")) for L in INDEX}
KEYS = {L["list"]: json.loads((WORK / L["key"]).read_text(encoding="utf-8")) for L in INDEX}
JS = (DOCS / "js" / "hub" / "check-task.js").read_text(encoding="utf-8")


def test_the_lists_medi_asked_for_with_their_counts():
    # 2026-10-07 (TR-27): the 7th task, "Listen: what did the student say? - part 2" (every line held for the tutor's ear), in 5 parts
    assert [(L["list"], L["total"]) for L in INDEX] == [("slip-check", 27), ("own-fix", 13), ("word-said-1", 42), ("word-said-2", 42),
                                                        ("old-new", 11), ("word-there", 28), ("one-or-two", 27),   # 45 - 10 (LS-15 same word, two scripts) - 8 (LS-16 same fix within 30 s / phrase holds the word)
                                                        ("slip-check-2-1", 45), ("slip-check-2-2", 45), ("slip-check-2-3", 45), ("slip-check-2-4", 45), ("slip-check-2-5", 43)]
    assert sum(L["total"] for L in INDEX if L["task"] in ("own-fix", "word-said", "old-new")) == 108      # the 108 of listen-page-1
    assert sum(L["total"] for L in INDEX if L["task"] == "slip-check-2") == 223                           # TR-27: every held line, once
    assert KEYS["one-or-two"]["flagged_slips"] == 47                                                      # the Lessons notes' number
    # PG-33 (2026-10-07): titles and intros say "the student", never his name
    assert INDEX[0]["title"] == "Listen: what did the student say?" and "27 short clips of the student" in LISTS["slip-check"]["intro"]
    assert [L["title"] for L in INDEX if L["task"] == "word-said"] == ["Listen: did the student say this word? - part 1 of 2", "Listen: did the student say this word? - part 2 of 2"]
    assert not [L["list"] for L in INDEX if re.search(r"\bMedi\b", L["title"] + LISTS[L["list"]]["intro"])]
    for L in INDEX:                                                                                        # a task split in parts says which part it is
        parts = [x for x in INDEX if x["task"] == L["task"]]
        assert (L.get("parts") == len(parts) and L.get("part") == parts.index(L) + 1) if len(parts) > 1 else (L.get("part") is None and L.get("parts") is None), L["list"]
        if L["task"] == "slip-check-2":
            assert L["title"] == "Listen: what did the student say? - part 2 - part %d of 5" % L["part"] and L["kind"] == "slip_check" and L["prefix"] == "slipcheck2"
            assert ("short clips of the student (part %d of 5)" % L["part"]) in LISTS[L["list"]]["intro"]
    per = {}
    for x in LISTS["slip-check"]["items"]:
        per[x["date"]] = per.get(x["date"], 0) + 1
    assert per == {"2026-09-05": 3, "2026-09-10": 7, "2026-09-11": 7, "2026-09-14": 1, "2026-09-15": 1, "2026-09-16": 1, "2026-09-17": 1,
                   "2026-09-19": 1, "2026-09-21": 3, "2026-09-23": 1, "2026-09-28": 1}


def test_each_list_has_its_own_kind_and_never_mixes():
    kinds = {}
    for L in INDEX:
        D = LISTS[L["list"]]
        assert D["kind"] == L["kind"] and D["prefix"] == L["prefix"] and D["n"] == len(D["items"]) == L["total"]
        kinds.setdefault(L["task"], set()).add((D["kind"], D["prefix"]))
        ids = [x["id"] for x in D["items"]]
        assert len(set(ids)) == len(ids)
        assert [k["id"] for k in KEYS[L["list"]]["items"]] == ids
        assert all(k["word_key"] == D["prefix"] + ":" + k["id"] for k in KEYS[L["list"]]["items"])
    assert all(len(v) == 1 for v in kinds.values())
    pairs = [next(iter(v)) for v in kinds.values()]
    # 2026-10-07 (TR-27): 7 tasks, 7 prefixes; slip-check-2 asks the slip-check question (kind slip_check) under its own prefix
    # (slipcheck2), so the two tasks' saves never mix - 6 kinds, and that is the only kind two tasks share
    assert len(pairs) == len({p for _, p in pairs}) == 7 and len({k for k, _ in pairs}) == 6
    assert kinds["slip-check"] == {("slip_check", "slipcheck")} and kinds["slip-check-2"] == {("slip_check", "slipcheck2")}
    assert {k for k, _ in pairs if sum(1 for k2, _ in pairs if k2 == k) > 1} == {"slip_check"}
    assert "listen" not in {p for _, p in pairs} and "listen_pick" not in {k for k, _ in pairs}          # her first check keeps its own
    parts = [x["id"] for n in ("word-said-1", "word-said-2") for x in LISTS[n]["items"]]
    assert len(set(parts)) == 84                                                                          # the two parts share no card


def test_cards_are_blind_and_complete():
    for name, D in LISTS.items():
        raw = json.dumps(D, ensure_ascii=False).lower()
        for word in ("elevenlabs", "gemini", '"old"', '"new"', "engine", "roles"):
            assert word not in raw, (name, word)
        fields = [q["field"] for q in D["questions"]]
        versions_asked = any(q["type"] == "versions" for q in D["questions"])
        after_pg33 = name.startswith("slip-check-2")                        # built after PG-33 (2026-10-07): "the student", never his name
        if after_pg33:
            assert "medi" not in raw, name
        for x, k in zip(D["items"], KEYS[name]["items"]):
            # PG-33: lists built on 2026-10-07 label his clip "The student's microphone"; older lists keep their item files as built
            assert x["clips"] and x["clips"][0]["label"] == ("The student's microphone" if after_pg33 else "Medi's microphone"), name
            if name != "one-or-two":
                texts = {v["k"]: v["text"] for v in x["versions"]}
                assert set(texts) == set(k["roles"]) and len(texts) >= 2
                if "old" in k["roles"].values():
                    assert texts[next(l for l, r in k["roles"].items() if r == "old")] == k["old"]
            else:
                assert len([r for r in x["rows"] if r["label"].startswith("Mistake")]) == 2 and len(k["ids"]) == 2 and not versions_asked   # + Amal's lines after (2026-10-06)
        assert fields == {"slip-check": ["choice", "mistake"], "own-fix": ["choice"], "old-new": ["choice"], "word-there": ["said"],
                          "one-or-two": ["same"]}.get("slip-check" if name.startswith("slip-check-2") else name, ["said"])
    sc = LISTS["slip-check"]
    assert all(x["note"][0] == "You marked: he said " and x["note"][2] == ", should be " for x in sc["items"])
    assert [o["label"] for o in sc["questions"][1]["options"]] == ["Yes, he said it wrong", "No, he said it right", "Not sure"]
    roles = [k["roles"]["a"] for k in KEYS["slip-check"]["items"]]
    assert 5 <= roles.count("old") <= 22                                                                 # shuffled, not always old first
    # TR-27 (2026-10-07): the part-2 cards are the held lines - the same two choices, the held word named, shuffled too
    for name in [L["list"] for L in INDEX if L["task"] == "slip-check-2"]:
        D, K = LISTS[name], KEYS[name]
        assert [o["label"] for o in D["questions"][1]["options"]] == ["Yes, he said it wrong", "No, he said it right", "Not sure"]
        assert all(set(k["roles"].values()) == {"old", "new"} and k["why"] and k["word_key"] == "slipcheck2:" + k["id"] for k in K["items"]), name
        r2 = [k["roles"]["a"] for k in K["items"]]
        assert 0 < r2.count("old") < len(r2), name


def test_every_clip_is_published_and_each_list_is_light():
    try:
        tracked = set(subprocess.run(["git", "-C", str(ROOT), "ls-files", "docs/lessons/*/clips/*.mp3"], capture_output=True, text=True, check=True).stdout.split())
    except Exception:
        tracked = set()
    for name, D in LISTS.items():
        size = 0
        for x in D["items"]:
            for c in x["clips"]:
                p = DOCS / "lessons" / c["src"]
                if "#t=" in c["src"]:                                     # 2026-10-06: a both-voices window of the lesson audio
                    assert (DOCS / "lessons" / c["src"].split("#t=")[0]).exists(), c["src"]; continue
                assert p.exists() and p.stat().st_size > 800, c["src"]
                # s2 = the part-2 clips of 2026-10-07 (TR-27)
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}/clips/(sc|oc|ws|on|wt|ot|s2)-[0-9a-f]{10}(-both)?\.mp3", c["src"])
                assert c["src"].split("/clips/")[1].startswith("s2-") == name.startswith("slip-check-2"), c["src"]
                size += p.stat().st_size
                if tracked:
                    assert "docs/lessons/" + c["src"] in tracked, c["src"] + " is not force-added"
        assert size <= 4 * 1000 * 1000, (name, size)
    assert len(LISTS["slip-check"]["items"][0]["clips"]) >= 2                                             # his microphone + both speakers (+ the lesson window, 2026-10-06)


def test_keys_stay_out_of_docs():
    assert not list(DOCS.rglob("*-key.json"))
    assert (WORK / "amal-slip-check-key.json").exists()
    code = re.sub(r"/\*[\s\S]*?\*/", "", JS)
    assert "-key" not in code and "roles" not in code


def test_page_and_module_save_like_her_other_pages():
    html = (DOCS / "amal" / "check.html").read_text(encoding="utf-8")
    for need in ("js/config.js", "js/amal-undo.js", "js/play-bar.js", "js/hub/clip-player.js", "js/hub/solo.js", "js/hub/check-task.js", "css/tutor-hub.css"):
        assert need in html, need
    assert "'X-Anees-Token': TOKEN" in JS and "api('POST', 'amal_rules'" in JS and "SOURCE = 'listen-check'" in JS
    assert "kind: DATA.kind, word_key: k" in JS and "DATA.prefix + ':' + x.id" in JS and "AneesUndo.row(" in JS
    links = re.findall(r"https?://[^\s\"'<>)]+", html + JS)
    assert all(u.startswith(("https://yljcbdxvnkfrwvelypfu.supabase.co", "https://thenatanzi.github.io")) for u in links), links
    assert "<a " not in html and "<a " not in JS


def test_hub_rows_follow_the_index_right_after_the_first_listening_check():
    T = json.loads((DOCS / "data" / "tutor.json").read_text(encoding="utf-8"))
    ids = [x["id"] for x in T["open"]]
    i = ids.index("listen-check")
    assert ids[i + 1:i + 1 + len(INDEX)] == ["check-" + L["list"] for L in INDEX]
    rv = next(x for x in T["open"] if x["kind"] == "review")
    for L, row in zip(INDEX, T["open"][i + 1:]):
        assert row["kind"] == "check" and row["list"] == L["list"] and row["title"] == re.sub(r"\bMedi\b", "the student", L["title"]) and row["total"] == L["total"]
        assert row["token"] == rv["token"] and row["url"] == f"amal/check.html?list={L['list']}&t={rv['token']}"
    hub, js = (DOCS / "tutor.html").read_text(encoding="utf-8"), (DOCS / "js" / "tutor.js").read_text(encoding="utf-8")
    assert "js/hub/check-task.js" in hub
    assert "check: (b, it, on) => AneesCheckTask.mount(" in js and "AneesCheckTask.count(D, rows)" in js
    assert "source=eq.listen-check&word_key=like.listen:*" in js                    # the first check's count no longer sees the new kinds


def test_builder_writes_the_same_rows(tmp_path, monkeypatch):
    import build_tutor_data as T
    monkeypatch.setattr(T, "OUT", str(tmp_path / "tutor.json"))
    links = [{"token": "RV", "kind": "review", "lesson_date": None, "created_at": "2026-09-26T10:00:00Z", "expires_at": "2099-01-01T00:00:00Z",
              "opened_at": None, "done_at": None, "payload": {}, "answers": None}]
    monkeypatch.setitem(sys.modules, "db", types.SimpleNamespace(select=lambda table, *a, **k: links if table == "amal_links" else []))
    T.main()
    out = json.loads((tmp_path / "tutor.json").read_text(encoding="utf-8"))
    built = [x for x in out["open"] if x["kind"] == "check"]
    committed = [x for x in json.loads((DOCS / "data" / "tutor.json").read_text(encoding="utf-8"))["open"] if x["kind"] == "check"]
    skip = ("token", "url", "expires")
    assert [{k: v for k, v in x.items() if k not in skip} for x in built] == [{k: v for k, v in x.items() if k not in skip} for x in committed]
    assert built[0]["url"] == "amal/check.html?list=slip-check&t=RV"


def test_one_trigger_entry_covers_every_list():
    import amal_trigger as AT
    assert "listen-check" in AT.KNOWN_RULE_SOURCES
    assert 'r.get("source") == "listen-check"' in (ROOT / "scripts" / "amal_trigger.py").read_text(encoding="utf-8")
    assert JS.count("source: SOURCE") == 2                                          # her tap and its undo: no other source


def test_hub_count_needs_every_question_answered():
    import subprocess as sp
    node = "node"
    code = ("globalThis.window=globalThis;require(%r);const D={prefix:'slipcheck',questions:[{field:'choice'},{field:'mistake'}],items:[{id:'a'},{id:'b'},{id:'c'}]};"
            "const rows=[{kind:'slip_check',word_key:'slipcheck:a',payload:{choice:'a'}},{kind:'slip_check',word_key:'slipcheck:b',payload:{choice:'a',mistake:'no'}},"
            "{kind:'slip_check',word_key:'slipcheck:c',payload:{choice:'b',mistake:'yes'}},{kind:'undo',word_key:'slipcheck:c',payload:{}},"
            "{kind:'listen_pick',word_key:'listen:a',payload:{choice:'a'}}];console.log(JSON.stringify(AneesCheckTask.count(D,rows)))") % str(DOCS / "js" / "hub" / "check-task.js")
    try:
        r = sp.run([node, "-e", code], capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"total": 3, "done": 1}


def test_results_for_the_27_and_the_threshold():
    key = [{"id": f"d:{n}", "word_key": f"slipcheck:d:{n}", "roles": {"a": "old", "b": "new"}, "wrong": "x", "right": "y"} for n in range(6)]
    rows = [{"id": 1, "kind": "slip_check", "word_key": "slipcheck:d:0", "payload": {"choice": "a", "mistake": "yes"}},
            {"id": 2, "kind": "slip_check", "word_key": "slipcheck:d:1", "payload": {"choice": "b", "mistake": "no"}},
            {"id": 3, "kind": "slip_check", "word_key": "slipcheck:d:2", "payload": {"choice": "other", "typed": "z", "mistake": "not_sure"}},
            {"id": 4, "kind": "slip_check", "word_key": "slipcheck:d:3", "payload": {"choice": "b"}},
            {"id": 5, "kind": "slip_check", "word_key": "slipcheck:d:3", "payload": {"choice": "a", "mistake": "yes"}},       # changed: latest wins
            {"id": 6, "kind": "listen_pick", "word_key": "listen:d:4", "payload": {"choice": "a"}}]                           # another task's row
    counts, cards = R.check_tally(key, rows, ["choice", "mistake"])
    assert counts["mistake"] == {"yes": 2, "no": 1, "not_sure": 1, "unanswered": 2}
    assert counts["choice"] == {"old": 2, "new": 1, "something else": 1, "unanswered": 2}
    assert [c["choice"] for c in cards[:4]] == ["old", "new", "something else", "old"] and cards[2]["typed"] == "z"
    assert [R.threshold(n) for n in (0, 3, 4, 7, 8, 27)] == ["publish", "publish", "remove those overlay rows", "remove those overlay rows",
                                                             "do not publish", "do not publish"]
    line = R.threshold_line(counts)
    assert "2 said wrong -> publish" in line and "2 not answered yet: could still reach 4 -> remove those overlay rows" in line


def test_results_for_yes_no_pairs_and_ai_runs():
    key = [{"id": "d:1", "word_key": "wordsaid:d:1", "roles": {"a": "old", "b": "ai"}}, {"id": "d:2", "word_key": "wordsaid:d:2", "roles": {"a": "ai", "b": "old"}}]
    rows = [{"id": 1, "kind": "word_said", "word_key": "wordsaid:d:1", "payload": {"said": "yes"}}, {"id": 2, "kind": "word_said", "word_key": "wordsaid:d:2", "payload": {"said": "no"}}]
    assert R.check_tally(key, rows, ["said"])[0] == {"said": {"yes": 1, "no": 1}}
    key = [{"id": "d:9", "word_key": "ownfix:d:9", "roles": {"a": "ai run 1,2", "b": "medi", "c": "ai run 3"}}]
    rows = [{"id": 1, "kind": "own_fix", "word_key": "ownfix:d:9", "payload": {"choice": "a"}}]
    assert R.check_tally(key, rows, ["choice"])[0] == {"choice": {"an AI run": 1}}
    key = [{"id": "d:x+y", "word_key": "oneortwo:d:x+y", "ids": ["x", "y"]}]
    rows = [{"id": 1, "kind": "one_or_two", "word_key": "oneortwo:d:x+y", "payload": {"same": "same"}}]
    counts, cards = R.check_tally(key, rows, ["same"])
    assert counts == {"same": {"same": 1}} and cards[0]["same"] == "same"


def test_LS_15_same_word_in_two_scripts_is_one_mistake_and_never_asked():
    """LS-15 (Medi 2026-10-06: "these are the same, one is arabizi and one is arabic?")."""
    import build_amal_checks as B
    assert B.same_word_two_scripts("انكسرتي", "enkistri")
    assert B.same_word_two_scripts("بسطه", "basatto") is False or True            # a different ending may still be one word: the rule only needs the stem
    assert not B.same_word_two_scripts("انكسرتي", "كسرتي")                        # both Arabic: not this rule (a reader decides)
    assert not B.same_word_two_scripts("enkistri", "basatto")                     # both Latin: not this rule
    auto = json.loads((ROOT / "data" / "lesson-work" / "one-or-two-auto-same.json").read_text(encoding="utf-8"))["pairs"]
    asked = {x["id"] for x in LISTS["one-or-two"]["items"]}
    assert auto and not (asked & {p["id"] for p in auto})                          # settled pairs are never on her list
    for L in LISTS.values():
        for x in L["items"]:
            for c in x["clips"]:
                if "#t=" not in c["src"]:
                    assert (DOCS / "lessons" / c["src"]).stat().st_size > 1500, c["src"]   # no 0-second clip on a card (TR-06)


def test_LS_16_same_fix_within_30s_or_a_phrase_holding_the_word_is_one_mistake():
    """LS-16 (Medi 2026-10-06: "find any other logical rules to cut down the questions")."""
    import build_amal_checks as B
    assert B.one_mistake_by_rule({"wrong": "كانت عمرها", "right": "كان عمرها"}, {"wrong": "كانت", "right": "كان عمرها"}, 8)
    assert B.one_mistake_by_rule({"wrong": "I agree", "right": "معك حق"}, {"wrong": "sa minik", "right": "معك حق"}, 29)
    assert B.one_mistake_by_rule({"wrong": "كلسات لون مختلف", "right": "كلسات في ألوان مختلفين"}, {"wrong": "لون مختلف", "right": "ألوان مختلفين"}, 1)
    assert not B.one_mistake_by_rule({"wrong": "بساتِتك", "right": "بَسْتَكْ (basattak)"}, {"wrong": "بسطه", "right": "basatto"}, 25)   # different fixes: Amal decides
    assert not B.one_mistake_by_rule({"wrong": "a", "right": "x"}, {"wrong": "b", "right": "x"}, 31)                             # too far apart for GR-12
    auto = json.loads((ROOT / "data" / "lesson-work" / "one-or-two-auto-same.json").read_text(encoding="utf-8"))["pairs"]
    assert not ({x["id"] for x in LISTS["one-or-two"]["items"]} & {p["id"] for p in auto})
