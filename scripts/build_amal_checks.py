# -*- coding: utf-8 -*-
"""Amal's listening / checking tasks on her Tutor hub (Medi 2026-10-05: "have amal do the 27 line check too",
"did you put the 108 on amals list", "5 send to amal"). One list per task, each its own hub row, so she can stop and
come back. Same saving as her first listening check: amal_rules source 'listen-check' with her review link's token;
each list has its own kind and word_key prefix, so the tasks never mix.

    python scripts/build_amal_checks.py --src C:/dev/anees-wt-bench

<src> is the work copy that holds the second-listen files (data/lesson-work/rehear/...) and the scripts that read them
(scripts/rehear_listen_page.py, rehear_audio.py, rehear_rejudge.py). They are imported and only READ: nothing under
<src> is written (clips cut from a track go to the temp folder).

  list          what                                                              source
  slip-check    27 slips she confirmed whose line the second listen changed       rehear_listen_page.council_cards(), the cards
                                                                                  of Medi's council-check-1.html
  own-fix       13 corrections Medi typed that no AI run heard                    apply-plan.json 'listen'
  word-said-N   84 words the AI wanted to add that Amal says right after          apply-plan.json 'held' (in parts)
  old-new       11 lines the blind spot check preferred the old text for          spot.json verdict 'old text'
  word-there    28 credited words the second listen no longer hears               rejudge/word-credit-conflicts.json
  one-or-two    47 slips that may be counted twice                                rehear_rejudge.maybe_same_slip_loose over
                                                                                  <src>/docs/data/lessons/<date>.json

Writes docs/data/amal-check-<list>.json (blind: Version A / B / C, shuffled per item with a fixed seed),
docs/data/amal-checks.json (the index the hub builder reads), docs/lessons/<date>/clips/<xx>-<sha1>[-both].mp3
(force-add: *.mp3 is git-ignored) and the unblinding keys data/lesson-work/amal-check-<list>-key.json
(amal-slip-check-key.json for the 27) - never under docs. No AI call, no database."""
import argparse, glob, hashlib, json, math, os, random, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SET = "amal-checks-2026-10-05"
COUNCIL_PAGE = r"C:\Claude\reports\anees-listen-2026-10-05\council-check-1.html"
LISTEN_PAGE = r"C:\Claude\reports\anees-listen-2026-10-05\listen-page-1.html"
BEFORE, AFTER, BOTH_CAP = 6.0, 8.0, 30.0
PART_BYTES = 4 * 1000 * 1000
LETTERS = "abcdefgh"

YES_NO = [{"v": "yes", "label": "Yes"}, {"v": "no", "label": "No"}, {"v": "not_sure", "label": "Not sure"}]
TASKS = {   # list -> what the hub and the page say; kind / prefix keep the tasks apart in amal_rules
    "slip-check": {"kind": "slip_check", "prefix": "slipcheck", "clip": "sc", "title": "Listen: what did the student say?", "unit": "clips", "mins": 10,
                   "intro": "27 short clips of the student. A second AI listen changed how these lines are written - tell us what he really said.",
                   "questions": [{"field": "choice", "ask": "Listen to the student. What did he say?", "type": "versions", "other": "Something else"},
                                 {"field": "mistake", "ask": "Was it a mistake?", "type": "options",
                                  "options": [{"v": "yes", "label": "Yes, he said it wrong"}, {"v": "no", "label": "No, he said it right"}, {"v": "not_sure", "label": "Not sure"}]}]},
    "slip-check-2": {"kind": "slip_check", "prefix": "slipcheck2", "clip": "s2", "title": "Listen: what did the student say? - part 2", "unit": "clips", "mins": None,
                     "intro": "Short clips of the student. A second AI listen wants to change how these lines are written, but the new words are "
                              "your own words from the same minute, or sit on a mistake you marked - so the change waits for your ear (TR-27). Tell us what he really said.",
                     "questions": [{"field": "choice", "ask": "Listen to the student. What did he say?", "type": "versions", "other": "Something else"},
                                   {"field": "mistake", "ask": "Was it a mistake?", "type": "options",
                                    "options": [{"v": "yes", "label": "Yes, he said it wrong"}, {"v": "no", "label": "No, he said it right"}, {"v": "not_sure", "label": "Not sure"}]}]},
    "own-fix": {"kind": "own_fix", "prefix": "ownfix", "clip": "oc", "title": "Listen: the student's own corrections", "unit": "clips", "mins": 5,
                "intro": "13 short clips of the student. His line is written in two or three ways - which one did he say?",
                "questions": [{"field": "choice", "ask": "Listen to the student. What did he say?", "type": "versions", "other": "Something else"}]},
    "word-said": {"kind": "word_said", "prefix": "wordsaid", "clip": "ws", "title": "Listen: did the student say this word?", "unit": "clips", "mins": None,
                  "intro": "Short clips of the student. You say a word a few seconds later - did the student say it himself, in his own line?",
                  "questions": [{"field": "said", "ask": "Did the student say this word himself in his line?", "type": "options", "options": YES_NO}]},
    "old-new": {"kind": "old_new", "prefix": "oldnew", "clip": "on", "title": "Listen: old or new line?", "unit": "clips", "mins": 4,
                "intro": "11 short clips of the student. His line is written two ways - which one did he say?",
                "questions": [{"field": "choice", "ask": "Listen to the student. What did he say?", "type": "versions", "other": "Something else"}]},
    "word-there": {"kind": "word_there", "prefix": "wordthere", "clip": "wt", "title": "Check: is this word really there?", "unit": "clips", "mins": 8,
                   "intro": "28 short clips of the student. He was given credit for a word here - listen and tell us if he really said it.",
                   "questions": [{"field": "said", "ask": "Did he say this word?", "type": "options", "options": YES_NO}]},
    "one-or-two": {"kind": "one_or_two", "prefix": "oneortwo", "clip": "ot", "title": "Check: one mistake or two?", "unit": "pairs", "mins": 12,
                   "intro": "Two mistakes written down from the same moment of a lesson. Is it the same mistake written twice, or two different mistakes?",
                   "questions": [{"field": "same", "ask": "Is this one mistake or two?", "type": "options",
                                  "options": [{"v": "same", "label": "The same mistake, written twice"}, {"v": "different", "label": "Two different mistakes"}, {"v": "not_sure", "label": "Not sure"}]}]},
}
_AR = re.compile(r"[\u0600-\u06FF]")


def _norm_ar(w):
    from arabizi_reader import to_arabic
    w = str(w or "").strip()
    if not _AR.search(w):
        w = to_arabic(w)
    w = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", w).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"[^\u0600-\u06FF]+", "", w)


def same_word_two_scripts(a, b):
    """LS-15: the same word once in Arabic letters and once in Arabizi (Medi 2026-10-06)."""
    a, b = str(a or ""), str(b or "")
    if not a or not b or bool(_AR.search(a)) == bool(_AR.search(b)):
        return False
    na, nb = _norm_ar(a), _norm_ar(b)
    return bool(na) and (na == nb or na in nb or nb in na)


def _norm_any(s):
    """A 'should be' or a wrong phrase as one comparable Arabic string: a ( ) gloss dropped, Arabizi read into Arabic letters,
    vowels / hamza forms / ta marbuta folded, spaces and punctuation gone."""
    s = re.sub(r"\([^)]*\)", "", str(s or ""))
    s = re.sub(r"\((.)\)", r"\1", str(s or ""))
    parts = [p.strip() for p in re.split(r"\s*/\s*", s) if p.strip()]
    return "|".join(sorted(_norm_ar(p) for p in parts if _norm_ar(p)))


def one_mistake_by_rule(first, second, dt):
    """LS-16 (Medi 2026-10-06 'find any other logical rules to cut down the questions'): two rows are ONE mistake when
    (a) within 30 s Amal's fix is the same word (GR-12: the same wrong phrase fixed once), or
    (b) within 3 s one wrong phrase contains the other (a phrase and the word inside it). Returns the reason or None."""
    ra, rb = _norm_any(first.get("right")), _norm_any(second.get("right"))
    wa, wb = _norm_ar(first.get("wrong")), _norm_ar(second.get("wrong"))
    same_fix = ra and rb and any(x and x == y for x in ra.split("|") for y in rb.split("|"))
    if dt <= 30 and same_fix:
        return "same fix within 30 s (GR-12): one mistake"
    # a phrase and the word inside it: BOTH the wrong and the fix of one sit inside the other's (never the fix alone -
    # 'عمي' inside 'أروح عند عمي' was a different, grammar, mistake)
    holds = wa and wb and len(min(wa, wb, key=len)) >= 3 and ((wa in wb and any(x and x in y for x in ra.split("|") for y in rb.split("|"))) or (wb in wa and any(y and y in x for x in ra.split("|") for y in rb.split("|"))))
    if dt <= 3 and holds:
        return "one phrase holds the other, fix included: one mistake"
    return None


auto_same = []
ORDER = ("slip-check", "own-fix", "word-said", "old-new", "word-there", "one-or-two", "slip-check-2")


def J(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:10]


def ff(args, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y"] + args + ["-ac", "1", "-map_metadata", "-1", "-fflags", "+bitexact",
                                                                          "-flags:a", "+bitexact", str(out)], check=True)


def both_sources(date, src):
    for base in (ROOT, src):
        a = base / "docs" / "lessons" / date / "audio"
        if (a / "lesson.mp3").exists():
            return [a / "lesson.mp3"]
        if (a / "Amal.mp3").exists() and (a / "Medi.mp3").exists():
            return [a / "Amal.mp3", a / "Medi.mp3"]
    return []


class Build:
    def __init__(self, src, audio=True):
        self.src, self.audio = Path(src), audio
        sys.dont_write_bytecode = True                   # nothing is written under <src>
        sys.path.insert(0, str(self.src / "scripts"))
        import rehear_listen_page as P
        import rehear_audio as RA
        import rehear_rejudge as RR
        self.P, self.RA, self.RR = P, RA, RR
        self.rehear = self.src / "data" / "lesson-work" / "rehear"
        self._lines = {}

    # ---- his line + clips -----------------------------------------------------------------------------------------
    def lines(self, date):
        if date not in self._lines:
            p = self.rehear / date / "lines.json"
            self._lines[date] = J(p)["lines"] if p.exists() else []
        return self._lines[date]

    def line_at(self, date, t):
        """His line that holds lesson time t (the latest line starting at or before t + 1 s), like council_cards."""
        L = self.lines(date)
        cand = [ln for ln in L if ln["t"] <= t + 1.0] or L[:1]
        ln = max(cand, key=lambda l: l["t"]) if cand else None
        if not ln or t > ln.get("end", ln["t"] + 3.0) + 6.0:        # no line there: a plain window around the time
            return {"i": -1, "t": max(0.0, t - 1.0), "end": t + 6.0}
        return ln

    def own_wav(self, date, ln):
        """(wav of his microphone for this line, 'own' | 'mix')."""
        if ln.get("clip") and (self.rehear / date / ln["clip"]).exists():
            return self.rehear / date / ln["clip"], ln.get("src", "own")
        out = Path(tempfile.gettempdir()) / f"anees-amal-check-{date}-{ln['t']:.2f}.wav"
        how = self.RA.clip(date, "Medi", max(0.0, float(ln["t"]) - 0.6), float(ln.get("end", ln["t"] + 3.0)) + 0.6, str(out))
        return out, how

    def clips(self, task, date, key, ln, both=False):
        """Writes his clip (and the both-speakers clip) -> (own rel, both rel | None, bytes)."""
        name = f"{TASKS[task]['clip']}-{sha(date, key)}"
        own = f"{date}/clips/{name}.mp3"
        brel = f"{date}/clips/{name}-both.mp3"
        srcs = both_sources(date, self.src) if both else []
        if self.audio:
            wav, _ = self.own_wav(date, ln)
            ff(["-i", str(wav), "-b:a", "32k"], ROOT / "docs" / "lessons" / own)
            if srcs:
                start = max(0.0, float(ln["t"]) - BEFORE)
                dur = min(BOTH_CAP, float(ln.get("end", ln["t"] + 3.0)) + AFTER - start)
                args = []
                for s in srcs:
                    args += ["-ss", "%.2f" % start, "-t", "%.2f" % dur, "-i", str(s)]
                if len(srcs) > 1:
                    args += ["-filter_complex", "amix=inputs=%d:duration=longest:normalize=0" % len(srcs)]
                ff(args + ["-ar", "16000", "-b:a", "24k"], ROOT / "docs" / "lessons" / brel)
        size = sum((ROOT / "docs" / "lessons" / r).stat().st_size for r in (own, brel) if (ROOT / "docs" / "lessons" / r).exists() and (r == own or srcs))
        return own, (brel if srcs else None), size

    def amal_rows(self, date, times, within=20.0):
        """Amal's lines (spoken or typed) in the `within` seconds after each time - what she said about the moment, or that she let it pass."""
        p = os.path.join(ROOT, "docs", "data", "lessons", f"{date}.json")
        turns = (json.load(open(p, encoding="utf-8")).get("turns") or []) if os.path.exists(p) else []
        out, seen = [], set()
        for t in times:
            for x in turns:
                if x.get("who") in ("Amal", "chat") and t - 1 <= float(x.get("t", 0)) <= t + within and str(x.get("text") or "").strip() and (x.get("t"), x.get("text")) not in seen:
                    seen.add((x.get("t"), x.get("text")))
                    tt = int(float(x["t"])); out.append({"label": f"You · {tt // 60}:{tt % 60:02d}" + (" (typed)" if x.get("who") == "chat" else ""), "text": ["", str(x["text"]).strip(), "", ""]})
        return out[:4] or [{"label": "You", "text": ["", "no line from you in the next 20 seconds - you let it pass", "", ""]}]

    def players(self, own, both):
        out = [{"label": "The student's microphone", "src": own}]
        if both:
            out.append({"label": "Both of you, a little before and after", "src": both})
        return out

    @staticmethod
    def blind(rng, texts_by_role):
        """[(role, text)] -> (versions [{k, text}], roles {k: role}) in a shuffled order."""
        order = list(texts_by_role)
        rng.shuffle(order)
        return ([{"k": LETTERS[n], "text": t} for n, (_, t) in enumerate(order)], {LETTERS[n]: r for n, (r, _) in enumerate(order)})

    # ---- the six lists ----------------------------------------------------------------------------------------------
    def page_ids(self, page, kind):
        h = Path(page).read_text(encoding="utf-8")
        return set(re.findall(r'data-id="([^"]+-%s)"' % re.escape(kind), h))

    def slip_check(self):
        P, rng = self.P, random.Random(SET + "|slip-check")
        want = self.page_ids(COUNCIL_PAGE, "council")
        cards = [c for c in P.council_cards() if "%s-%s-council" % (c["date"], c["uid"]) in want]
        if len(cards) != len(want):
            raise SystemExit(f"slip-check: the council page has {len(want)} cards, the data gives {len(cards)} of them")
        items, key = [], []
        for c in sorted(cards, key=lambda c: (c["date"], c["t"])):
            iid = f"{c['date']}:{c['uid']}"
            own, both, size = self.clips("slip-check", c["date"], c["uid"], {"t": c["t"], "end": c["end"], "clip": os.path.relpath(c["clip_path"], self.rehear / c["date"]) if c.get("clip_path") else None}, both=True)
            versions, roles = self.blind(rng, [("old", c["line_before"]), ("new", c["line_after"])])
            items.append({"id": iid, "date": c["date"], "mmss": c["mmss"], "clips": self.players(own, both), "versions": versions,
                          "note": ["You marked: he said ", c.get("wrong") or "(no word)", ", should be ", c.get("right") or ""], "bytes": size})
            key.append({"id": iid, "uid": c["uid"], "i": c["i"], "t": c["t"], "roles": roles, "old": c["line_before"], "new": c["line_after"],
                        "wrong": c.get("wrong"), "right": c.get("right")})
        return items, key

    def slip_check_2(self):
        """TR-27 (2026-10-07): every second-listen change the widened hold keeps back for the tutor's ear - each lesson's
        rehear/<date>/apply-plan.json held_tutor (a change toward her own words within 30 s, or on a mistake she
        confirmed) that she has not answered yet. One list, in parts when the clips are big."""
        rng = random.Random(SET + "|slip-check-2")
        items, key = [], []
        for p in sorted(glob.glob(str(self.rehear / "*" / "apply-plan.json"))):
            P = J(p)
            date = P.get("date")
            if not date or not self.P.DATE_RE.match(date):
                continue
            by_i = {ln["i"]: ln for ln in self.lines(date)}
            for h in sorted(P.get("held_tutor") or [], key=lambda h: h["t"]):
                if h.get("tutor"):
                    continue                                    # she answered this line on an earlier list
                iid = f"{date}:{h['i']}"
                ln = by_i.get(h["i"]) or {"i": h["i"], "t": h["t"], "end": h["t"] + 3.0}
                c = {"date": date, "t": ln["t"], "end": ln.get("end", ln["t"] + 3.0), "clip_path": str(self.rehear / date / ln["clip"]) if ln.get("clip") else None}
                own, both, size = self.clips("slip-check-2", date, h["i"], self._ln(c), both=True)
                versions, roles = self.blind(rng, [("old", h["engine"]), ("new", h["heard"])])
                note = None
                if h.get("toward"):
                    note = ["The new line has your own word: ", " / ".join(h["toward"]), "."]
                elif h.get("confirmed"):
                    note = ["You marked a mistake on this line earlier."]
                items.append({"id": iid, "date": date, "mmss": h["mmss"], "clips": self.players(own, both), "versions": versions, "note": note, "bytes": size})
                key.append({"id": iid, "i": h["i"], "t": h["t"], "roles": roles, "old": h["engine"], "new": h["heard"], "toward": h.get("toward"),
                            "confirmed": h.get("confirmed"), "why": h.get("why")})
        return items, key

    def plan_cards(self):
        P = self.P
        dates = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(str(self.rehear / "*" / "apply-plan.json")))
        cards = []
        for d in dates:
            if not P.DATE_RE.match(d):
                continue
            cards += (P.collect(d, str(self.rehear), None) or []) + P.spot_cards(d)
        want = {t: self.page_ids(LISTEN_PAGE, t) for t in ("his-correction", "held", "spot")}
        out = {t: [c for c in cards if c["type"] == t and "%s-%s-%s" % (c["date"], c["i"], t) in want[t]] for t in want}
        for t in want:                                   # two corrections on one line share a card id on the page
            if {"%s-%s-%s" % (c["date"], c["i"], t) for c in out[t]} != want[t]:
                raise SystemExit(f"{t}: the listen page's cards and the data do not match")
        return out

    def _ln(self, c):
        return {"t": c["t"], "end": c["end"], "clip": os.path.relpath(c["clip_path"], self.rehear / c["date"]) if c.get("clip_path") else None}

    def own_fix(self, cards):
        P, rng = self.P, random.Random(SET + "|own-fix")
        items, key = [], []
        n_on_line = {}
        for c in sorted(cards, key=lambda c: (c["date"], c["t"])):
            n = n_on_line[(c["date"], c["i"])] = n_on_line.get((c["date"], c["i"]), 0) + 1
            iid = f"{c['date']}:{c['i']}" + (f".{n}" if n > 1 else "")
            his = c.get("line_now") or c.get("his") or ""
            texts, seen = [("medi", his)], [P.norm(his)]
            for text, ns in P.group_runs(c.get("runs")):
                if text and P.norm(text) not in seen:
                    seen.append(P.norm(text)); texts.append(("ai run " + ",".join(str(n) for n in ns), text))
            own, both, size = self.clips("own-fix", c["date"], iid, self._ln(c))
            versions, roles = self.blind(rng, texts)
            items.append({"id": iid, "date": c["date"], "mmss": c["mmss"], "clips": self.players(own, both), "versions": versions, "bytes": size})
            key.append({"id": iid, "i": c["i"], "t": c["t"], "roles": roles, "engine_line": c.get("engine_line"), "engine_wrote": c.get("engine_wrote"),
                        "his": c.get("his"), "runs": c.get("runs")})
        return items, key

    def word_said(self, cards):
        P, rng = self.P, random.Random(SET + "|word-said")
        items, key = [], []
        for c in sorted(cards, key=lambda c: (c["date"], c["t"])):
            iid = f"{c['date']}:{c['i']}"
            w = " ".join(P.words(c.get("her_words")) or [])
            own, both, size = self.clips("word-said", c["date"], c["i"], self._ln(c), both=True)
            versions, roles = self.blind(rng, [("old", c.get("engine") or ""), ("ai", c.get("heard") or "")])
            items.append({"id": iid, "date": c["date"], "mmss": c["mmss"], "clips": self.players(own, both), "versions": versions,
                          "ask": ["Did the student say ", f"«{w}»", " himself in his line?"] if w else "Did the student say the extra word himself in his line?",
                          "note": ["You say ", w, " right after."] if w else None, "bytes": size})
            key.append({"id": iid, "i": c["i"], "t": c["t"], "roles": roles, "word": w, "old": c.get("engine"), "ai": c.get("heard"), "two_clip": c.get("two_clip")})
        return items, key

    def old_new(self, cards):
        rng = random.Random(SET + "|old-new")
        items, key = [], []
        for c in sorted(cards, key=lambda c: (c["date"], c["t"])):
            iid = f"{c['date']}:{c['i']}"
            own, both, size = self.clips("old-new", c["date"], c["i"], self._ln(c))
            versions, roles = self.blind(rng, [("old", c.get("engine") or ""), ("new", c.get("heard") or "")])
            items.append({"id": iid, "date": c["date"], "mmss": c["mmss"], "clips": self.players(own, both), "versions": versions, "bytes": size})
            key.append({"id": iid, "i": c["i"], "t": c["t"], "roles": roles, "old": c.get("engine"), "new": c.get("heard"), "votes": c.get("votes")})
        return items, key

    def word_there(self):
        rng = random.Random(SET + "|word-there")
        rows = J(self.rehear / "rejudge" / "word-credit-conflicts.json")["rows"]
        items, key = [], []
        for r in sorted(rows, key=lambda r: (r["date"], r["t"])):
            iid = f"{r['date']}:{str(r.get('event_id') or sha(r['date'], r['t'], r.get('word')))[:10]}"
            ln = self.line_at(r["date"], float(r["t"]))
            own, both, size = self.clips("word-there", r["date"], iid, ln)
            versions, roles = self.blind(rng, [("old", r.get("old_line") or ""), ("new", r.get("new_line") or "")])
            word = r.get("list_word") or r.get("word") or ""
            items.append({"id": iid, "date": r["date"], "mmss": r.get("mmss") or self.P.mmss(r["t"]), "clips": self.players(own, both), "versions": versions,
                          "ask": ["Did he say ", f"«{word}»", "?"], "bytes": size})
            key.append({"id": iid, "i": ln.get("i"), "t": r["t"], "roles": roles, "word": word, "word_key": r.get("word_key"), "was": r.get("was"),
                        "old": r.get("old_line"), "new": r.get("new_line"), "event_id": r.get("event_id"), "mark": r.get("mark")})
        return items, key

    def one_or_two(self):
        """The loose detector behind the Lessons note "N slips may be counted twice" (build_lessons_page_data.first_read_summary):
        a first-read slip and another slip of the same lesson that rehear_rejudge.maybe_same_slip_loose pairs with it."""
        RR = self.RR
        T = lambda x: RR.sec(x.get("t")) or 0.0            # the slips carry mm:ss; the matchers read it with RR.sec
        ident = lambda x: str(x.get("id") or "%s@%s" % (x["kind"], x.get("mmss")))   # a word slip may carry no audit id
        items, key, flagged = [], [], 0
        for p in sorted(glob.glob(str(self.src / "docs" / "data" / "lessons" / "2*.json"))):
            v, date = J(p), os.path.basename(p)[:10]
            g = [dict(e, kind="grammar", t=RR.sec_mmss(e.get("mmss"))) for e in v.get("grammar_errors") or []]
            w = [dict(e, kind="vocab-A", right=e.get("fix") or e.get("arabic"), t=RR.sec_mmss(e.get("mmss"))) for e in v.get("vocab_errors") or []]
            seen = set()
            for pool in (g, w):
                for e in pool:
                    if not e.get("first_read"):
                        continue
                    ms = [o for o in pool if o is not e and RR.maybe_same_slip_loose(e, o)]
                    if not ms:
                        continue
                    flagged += 1
                    o = min(ms, key=lambda o: abs(T(o) - T(e)))
                    pair = tuple(sorted([ident(e), ident(o)]))
                    if pair in seen:                       # both slips are first-read and point at each other: one question
                        continue
                    seen.add(pair)
                    first, second = sorted([e, o], key=lambda x: (T(x), ident(x)))
                    iid = f"{date}:{pair[0]}+{pair[1]}"
                    # LS-15 (Medi 2026-10-06 "these are the same, one is arabizi and one is arabic?"): the same word at the same
                    # second, once in Arabic letters and once in Arabizi, is ONE mistake - settled here, never asked
                    if abs(T(first) - T(second)) <= 2.0 and same_word_two_scripts(first.get("wrong"), second.get("wrong")):
                        auto_same.append({"id": iid, "date": date, "mmss": first.get("mmss"), "said": [first.get("wrong"), second.get("wrong")], "rule": "LS-15"})
                        continue
                    why = one_mistake_by_rule(first, second, abs(T(first) - T(second)))
                    if why:
                        auto_same.append({"id": iid, "date": date, "mmss": first.get("mmss"), "said": [first.get("wrong"), second.get("wrong")], "right": [first.get("right"), second.get("right")], "rule": "LS-16", "why": why})
                        continue
                    ln = self.line_at(date, T(first))
                    own, both, size = self.clips("one-or-two", date, iid, ln)
                    row = lambda n, x: {"label": f"Mistake {n} · {x.get('mmss') or ''}",
                                        "text": ["he said ", x.get("wrong") or "(did not know the word)", " → should be ", x.get("right") or ""]}
                    # Medi 2026-10-06 "amal doesnt correct me here? why are we not including this context in all of them": her next
                    # line after each mistake, and a both-voices window of the lesson audio (the card plays it from lesson.mp3)
                    amal_rows = self.amal_rows(date, [T(first), T(second)])
                    clips = self.players(own, both)
                    if not both and os.path.exists(os.path.join(ROOT, "docs", "lessons", date, "audio", "lesson.mp3")):
                        clips.append({"label": "Both of you · the lesson a little before and after", "src": f"{date}/audio/lesson.mp3#t={max(0, int(T(first)) - 3)},{int(T(second)) + 15}"})
                    items.append({"id": iid, "date": date, "mmss": first.get("mmss") or "", "clips": clips,
                                  "rows": [row(1, first), row(2, second)] + amal_rows, "bytes": size})
                    key.append({"id": iid, "kind": e["kind"], "t": T(first), "ids": [ident(first), ident(second)],
                                "first_read": [bool(first.get("first_read")), bool(second.get("first_read"))],
                                "slips": [{k: x.get(k) for k in ("id", "mmss", "wrong", "right", "bucket", "said")} for x in (first, second)]})
        return items, key, flagged


def write_list(name, task, items, key, part=None, parts=None, extra_key=None):
    T = TASKS[task]
    size = sum(x.pop("bytes", 0) for x in items)
    n = len(items)
    title = T["title"] + (f" - part {part} of {parts}" if parts and parts > 1 else "")
    intro = T["intro"] if not (parts and parts > 1) else f"{n} short clips of the student (part {part} of {parts}). " + T["intro"].split(". ", 1)[1]
    mins = T["mins"] or max(1, round(n * 0.3))
    doc = {"set": SET, "list": name, "kind": T["kind"], "prefix": T["prefix"], "title": title, "intro": intro, "unit": T["unit"],
           "questions": T["questions"], "n": n, "items": [{k: v for k, v in x.items() if v is not None} for x in items]}
    (ROOT / "docs" / "data" / f"amal-check-{name}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k in key:
        k["word_key"] = f"{T['prefix']}:{k['id']}"
    keyname = "amal-slip-check-key.json" if name == "slip-check" else f"amal-check-{name}-key.json"
    keydoc = {"set": SET, "list": name, "kind": T["kind"],
              "about": f"Unblinding key for docs/data/amal-check-{name}.json (never published). roles = what each version letter really is.",
              **(extra_key or {}), "items": key}
    (ROOT / "data" / "lesson-work" / keyname).write_text(json.dumps(keydoc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    per = {}
    for x in items:
        per[x["date"]] = per.get(x["date"], 0) + 1
    print(f"{name:14} {n:3} items  clips {size / 1e6:.2f} MB  {per}")
    return {"list": name, "task": task, "kind": T["kind"], "prefix": T["prefix"], "title": title, "total": n, "unit": T["unit"], "mins": mins,
            "what": f"{intro} About {mins} minutes.", "key": keyname, "clip_bytes": size, **({"part": part, "parts": parts} if parts and parts > 1 else {})}


def reword(index_path=ROOT / "docs" / "data" / "amal-checks.json"):
    """PG-33 / AM-24: the title, intro and question words of every EXISTING list file follow TASKS (the items, their
    ids and the clips are untouched, so her answers keep their keys). Returns the index entries, re-worded."""
    idx = J(index_path) if index_path.exists() else {"lists": []}
    out = []
    for e in idx.get("lists") or []:
        T = TASKS.get(e.get("task") or e["list"])
        p = ROOT / "docs" / "data" / f"amal-check-{e['list']}.json"
        if not T or not p.exists():
            out.append(e)
            continue
        doc = J(p)
        part, parts = e.get("part"), e.get("parts")
        m = re.search(r"part (\d+) of (\d+)", str(e.get("title") or ""))
        if m:
            part, parts = int(m.group(1)), int(m.group(2))
        n = doc.get("n") or len(doc.get("items") or [])
        title = T["title"] + (f" - part {part} of {parts}" if parts and parts > 1 else "")
        intro = T["intro"] if not (parts and parts > 1) else f"{n} short clips of the student (part {part} of {parts}). " + T["intro"].split(". ", 1)[1]
        doc.update(title=title, intro=intro, questions=T["questions"], kind=T["kind"], prefix=T["prefix"])
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        mins = T["mins"] or max(1, round(n * 0.3))
        out.append(dict(e, task=e.get("task") or e["list"], title=title, kind=T["kind"], prefix=T["prefix"], mins=mins, what=f"{intro} About {mins} minutes.",
                        **({"part": part, "parts": parts} if parts and parts > 1 else {})))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--only", nargs="*", help="build only these lists; the other index entries are kept (re-worded from TASKS)")
    a = ap.parse_args(argv)
    B = Build(a.src, audio=not a.no_audio)
    tasks = tuple(a.only) if a.only else ORDER
    plan = B.plan_cards() if any(t in ("own-fix", "word-said", "old-new") for t in tasks) else None
    index = [e for e in reword() if (e.get("task") or e["list"]) not in tasks] if a.only else []
    for task in tasks:
        extra = None
        if task == "slip-check":
            items, key = B.slip_check()
        elif task == "slip-check-2":
            items, key = B.slip_check_2()
            if not items:
                print("slip-check-2: nothing is held for the tutor")
                continue
        elif task == "own-fix":
            items, key = B.own_fix(plan["his-correction"])
        elif task == "word-said":
            items, key = B.word_said(plan["held"])
        elif task == "old-new":
            items, key = B.old_new(plan["spot"])
        elif task == "word-there":
            items, key = B.word_there()
        else:
            items, key, flagged = B.one_or_two()
            extra = {"flagged_slips": flagged, "note": "flagged_slips = the number the Lessons notes add up to; two first-read slips that point at each other are one pair"}
        total = sum(x.get("bytes", 0) for x in items)
        parts = max(1, math.ceil(total / PART_BYTES))      # --no-audio measures the clips already on disk
        if parts == 1:
            index.append(write_list(task, task, items, key, extra_key=extra))
        else:
            per = math.ceil(len(items) / parts)
            for n in range(parts):
                sl = slice(n * per, (n + 1) * per)
                index.append(write_list(f"{task}-{n + 1}", task, items[sl], key[sl], part=n + 1, parts=parts, extra_key=extra))
    index.sort(key=lambda e: (ORDER.index(e.get("task") or e["list"]) if (e.get("task") or e["list"]) in ORDER else 99, e.get("part") or 0))
    (ROOT / "docs" / "data" / "amal-checks.json").write_text(json.dumps({"set": SET, "note": "Amal's listening / checking lists (scripts/build_amal_checks.py). "
                                                                           "scripts/build_tutor_data.py puts one row per list on her Tutor hub.",
                                                                           "lists": index}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("total clips %.2f MB in %d lists" % (sum(x["clip_bytes"] for x in index) / 1e6, len(index)))


if __name__ == "__main__":
    main()
