# -*- coding: utf-8 -*-
"""PG-47 (Medi 2026-10-10: "also why did you remove the written chat from google meet? lets put that back in with a
different color? into the transcript"): the Meet chat is in every lesson transcript, in its own colour, never scored as
speech; the hourly job re-merges a chat a rebase dropped; frozen second-listen rows survive the index shift."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_lesson_page as BLP        # noqa: E402
import hourly_lessons as H             # noqa: E402
import rehear_apply as RA              # noqa: E402
import word_coverage as WC             # noqa: E402

FIRST_CHAT = "2026-09-14"              # the first lesson whose page carries the Meet chat (earlier pages had none)


def lesson(date):
    return json.load(open(os.path.join(ROOT, "docs", "data", "lessons", date + ".json"), encoding="utf-8"))


def read(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def test_pg_47_meet_chat_is_in_the_transcript_in_its_own_colour(tmp_path):
    # 1. 10-08 has its chat back: 64 lines the tutor typed, on the lesson clock, typed_by set
    d = lesson("2026-10-08")
    chat = [u for u in d["turns"] if u["who"] == "chat"]
    assert len(chat) >= 60, len(chat)
    assert all(u.get("typed_by") in ("Amal", "Medi") for u in chat)
    assert any("el-yoam yoam el-5amees" in u["text"] for u in chat)
    # every published lesson page from the first chat lesson on carries chat lines (10-08 had none until 2026-10-10)
    dates = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "docs", "lessons")) if re.fullmatch(r"20\d\d-\d\d-\d\d\.html", f))
    empty = [x for x in dates if x >= FIRST_CHAT and not any(u["who"] == "chat" for u in lesson(x)["turns"])]
    assert not empty, "lessons with no Meet chat line: %s" % empty

    # 2. chat rows are never his speech: word_coverage.report reads his spoken lines only
    rows = WC.report("2026-10-08")
    his = sum(len(WC.arabic_tokens(u.get("text"))) for u in d["turns"] if u["who"] == "Medi")
    assert len(rows) == his
    fake = {"date": "2099-01-01", "turns": [{"t": 1.0, "end": 2.0, "who": "Medi", "text": "بدي قهوة"},
                                            {"t": 3.0, "end": None, "who": "chat", "typed_by": "Medi", "text": "بدي شاي كتير"},
                                            {"t": 4.0, "end": None, "who": "chat", "typed_by": "Amal", "text": "بدك شاي"}], "tmarks": {}}
    (tmp_path / "docs" / "data" / "lessons").mkdir(parents=True)
    (tmp_path / "docs" / "data" / "lessons" / "2099-01-01.json").write_text(json.dumps(fake, ensure_ascii=False), encoding="utf-8")
    assert [r["word"] for r in WC.report("2099-01-01", repo=str(tmp_path))] == ["بدي", "قهوة"]

    # 3. its own colour + label on the Lessons page (a Sabz token, not a speaker or chip colour) and on the lesson pages
    css = read("docs", "css", "lessons.css")
    assert "--ls-chat:var(--sabz-state-rinad-drifting-text)" in css
    assert ".ls-turn-chat{--who:var(--ls-chat)" in css
    assert "--sabz-state-rinad-drifting-text" in read("docs", "css", "sabz-tokens.css")
    js = read("docs", "js", "lessons-page.js")
    assert "function chatWho(t)" in js and "'Chat · typed by '" in js and "Tutor · chat" not in js
    page = read("docs", "lessons", "2026-10-08.html")
    assert BLP.CHAT_LIGHT in page and BLP.CHAT_DARK in page and page.count('class="chat"') >= 60
    assert all(old not in page for old, _ in BLP.OLD_CHAT)

    # 4. the hourly job re-merges a chat whose page lost it (marker in the raw folder, no chat line on the page)
    day = "2026-10-08"
    (tmp_path / "raw" / day / "tracks").mkdir(parents=True)
    (tmp_path / "raw" / day / "tracks" / "tracks.json").write_text("{}", encoding="utf-8")
    (tmp_path / "raw" / day / "meet-chat-transcript.txt").write_text("x", encoding="utf-8")
    rec = [(tmp_path / ("jyx-mqtj-yuj (%s 13 33 GMT-7)" % day), "jyx-mqtj-yuj", day, "1333")]
    ledger = [{"bot_id": "b", "date": day, "t": "x"}]
    bots = [{"id": "b", "status_changes": [{"code": "done"}]}]
    _, todo = H.plan(ledger, bots, rec, {day}, tmp_path / "raw", has_chat=lambda p: True, page_chat=lambda d_: 0)
    assert {"kind": "chat", "date": day} in todo
    _, todo = H.plan(ledger, bots, rec, {day}, tmp_path / "raw", has_chat=lambda p: True, page_chat=lambda d_: 64)
    assert {"kind": "chat", "date": day} not in todo
    assert H.page_chat_lines(day) >= 60

    # 5. a frozen second-listen row finds its line by time after a chat line shifted the indexes
    turns = [{"t": 1.0, "who": "Medi", "text": "a"}, {"t": 2.0, "who": "chat", "text": "typed"}, {"t": 3.0, "who": "Medi", "text": "b"}]
    assert RA.at(turns, {"i": 1, "t": 3.0, "engine": "b"}) == 2
    assert RA.at(turns, {"i": 0, "t": 1.0, "engine": "a"}) == 0
