# -*- coding: utf-8 -*-
"""Every Arabic word Medi says is judged, and a repeat of the tutor's correction is a repeat (WS-30, WS-31, GR-32).

Medi 2026-10-09, on the 10-08 lesson: "I want you to be sure that any time I speak ANY arabic word that you are giving me
credit or marking as incorrect. Mark as repeat if I am repeating one of amals corrections and dont give me credit for it.
You are also doing a poor job of realizing for grammar errors that I am being corrected and repeating the correctiong.
THese should also be marked as repeat and uncounted."

Why words went unjudged (10-08 audit): the Word Bank matcher (scripts/speaking_evidence.py) reads the recording engine's
words. The engine wrote most of his Arabic in English-ear Latin ('Ayan', 'Shui', 'rasa biwaja'); the second listen
(TR-22 / TR-29) fixed the LINES, but no Word Bank event was ever made from the fixed text. And a single word said alone
was left 'unresolved' (the matcher's "Isolated production" rule), so مرحبا showed nothing.

From FROM on (every new lesson; the earlier lessons wait for Medi's yes, PR-05):
  WS-30  every Arabic word on his lines AFTER the overlay (Arabic script, or Latin read by scripts/arabizi_reader.py) gets
         a visible state: right / partial / wrong / repeat (Word Bank), or a grey reason (not on her list, a grammar word,
         unclear which word, a name). A word on her list with no Word Bank event becomes one (review-overlay addition,
         by 'word-coverage'), judged by the context rules below; a lone word is judged like any other (no 'isolated' limbo).
  WS-31  a word he says within 15 s after the tutor GAVE it (her correction or recast of his line, a fix a counted slip
         names, her answer to his 'how do I say', her typed chat line) - or a pure echo of her line - is a REPEAT: shown
         as repeat, no credit, not a mistake. Her ordinary question wording ('شو اليوم؟') used in his own new answer
         stays as before (3+ words: independent; shorter: helped).
  GR-32  the same for grammar: a use on his line whose words the tutor's correction (or the line he echoes) gave him in
         the 30 s before is not a use (scripts/detect_grammar_usage.py, not_uses_auto with the reason).

    python scripts/word_coverage.py report 2026-10-08     # every Arabic word of his and its state (after a build)
"""
import difflib, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
FROM = "2026-10-08"
BY = "word-coverage"
REVIEW_P = os.path.join(REPO, "docs", "data", "word-bank-review.json")
EVID_P = os.path.join(REPO, "docs", "data", "word-bank-evidence.json")
WORDS_P = os.path.join(REPO, "docs", "data", "words.json")
REPEAT_S = 15.0          # WS-31: the tutor's word in the 15 s before (the matcher's own 'helped' window)
GRAMMAR_REPEAT_S = 30.0  # GR-32: the same window as GR-28 / GR-12
RECAST_S = 20.0          # her line recasts his Arabic line of the 20 s before it
FIX_S = 3.0              # a counted slip's fix time within 3 s of her line names that line as her fix
CUE = re.compile(r"\b(no|instead|wrong|pronounce|correction)\b|(?:^|\s)(لا|مش)(?:\s|[.،؟?]|$)", re.I)
ASKS = re.compile(r"how do (?:i|you|we) say|how (?:would|do) (?:i|you) say|i don.?t know how to say|what.?s .{1,25} in arabic|"
                  r"what is .{1,25} in arabic|شو يعني|shu ya3ni|كيف (?:بقول|بتقول|منقول)", re.I)
QWORDS = {"شو", "كيف", "وين", "ليش", "امتي", "مين", "قديش", "ايش", "كم", "شلون", "ليه", "اديش", "هل"}
FUNCTION = {"انا", "انت", "انتي", "هو", "هي", "احنا", "هم", "في", "على", "من", "مع", "عن", "هاد", "هادا", "هادي", "هيك",
            "كمان", "بس", "لسه", "لسة", "كتير", "شوي", "يعني", "طيب", "تمام", "منيح", "عادي", "اللي", "كان", "كانت", "مش", "ما"}
FILLERS = {"اه", "اا", "ام", "امم", "اممم", "مم", "ممم", "هه", "هم", "اوه", "يعني", "اوف", "واو", "اهه", "اها"}
SOUND_TAG = re.compile(r"\[[^\[\]\n]{1,60}\]")
AR_TOK = re.compile(r"[ء-يً-ٰٟـ]+(?:\.\.\.|…|--|—|-)?")


def in_scope(date):
    return str(date) >= FROM


def J(p, d=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def sha(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def norm(w):
    import transcript_marks as TM
    return TM.normalise(w or "")[0].strip()


def core(w):
    """The word without el- and a leading w- (و) - what two people saying 'the same word' share."""
    n = norm(w)
    if n.startswith("وال") and len(n) > 4:
        n = n[1:]
    if n.startswith("ال") and len(n) > 3:
        n = n[2:]
    return n


def similar(a, b):
    a, b = core(a), core(b)
    if not a or not b:
        return False
    if a == b:
        return True
    return min(len(a), len(b)) >= 3 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


LAT_TOK = re.compile(r"[A-Za-z0-9'\u2019`]+(?:-[A-Za-z0-9'\u2019`]+)*(?:--|\u2014|-)?|[\u0621-\u064A\u064B-\u065F\u0670\u0640]+(?:\.\.\.|\u2026|--|\u2014|-)?|\S")
LAT_FILL = {"uh", "um", "umm", "uhm", "mm", "hmm", "er", "eh", "ah", "like", "oh", "okay", "ok", "yeah", "so"}


def word_tokens(text):
    """[{ar, cut, shown}] - the Arabic words of a line. Arabic script as written. A Latin word is one of hers when
    scripts/arabizi_reader.py reads it (her Doc words, her closed list); in a line that also has English it must be
    sure (an Arabizi digit 2 3 5 6 7 8 9, a closed-list word, or an Arabic word next to it), so 'name' or 'hate' in an
    English sentence is never his Arabic. shown = the word as the line writes it (el- kept: 'el nar')."""
    import arabizi_reader as AZ
    raw = [m.group(0) for m in LAT_TOK.finditer(SOUND_TAG.sub(" ", text or ""))]
    items, english, pend = [], 0, None
    for tok in raw:
        if re.match(r"[A-Za-z0-9]", tok):
            lw = tok.lower().strip("'\u2019`-\u2014")
            if lw in LAT_FILL:
                continue
            if lw in AZ.ARTICLE:
                pend = tok
                continue
            cut = tok.endswith(("--", "\u2014", "-"))
            ar = None if cut else AZ.word(lw)
            if ar is None:
                english += 0 if cut else 1
                items.append(None)
                pend = None
                continue
            strong = lw in AZ.FUNC or bool(re.search(r"[235789]", lw))
            if pend:
                ar, tok = "\u0627\u0644" + re.sub(r"^\u0627\u0644", "", ar), pend + " " + tok
                pend = None
            items.append({"ar": ar, "cut": False, "shown": tok, "latin": True, "strong": strong})
        elif re.match(r"[\u0621-\u064A]", tok):
            pend = None
            w = tok
            cut = w.endswith(("...", "\u2026", "--", "\u2014", "-", "\u0640"))
            w = w.rstrip(".\u2026-\u2014")
            n = norm(w)
            if not n or n in FILLERS or len(n) < 2 or re.fullmatch(r"[\u0627\u0622\u0647\u0645\u0649]+", n):
                items.append(None)
                continue
            items.append({"ar": w.rstrip("\u0640"), "cut": cut, "shown": w.rstrip("\u0640"), "latin": False, "strong": True})
        elif tok not in (",", "\u060c"):
            pend = None
    out = []
    for k, it in enumerate(items):
        if it is None:
            continue
        if it["latin"] and english and not it["strong"]:
            near = [items[x] for x in (k - 1, k + 1) if 0 <= x < len(items) and items[x] is not None]
            if not any(not x["latin"] or x["strong"] for x in near):
                continue
        out.append(it)
    return out


def arabic_tokens(text):
    """[(word, cut_off)] - word_tokens() in Arabic letters."""
    return [(t["ar"], t["cut"]) for t in word_tokens(text)]


def _is_amal(u):
    return u.get("who") == "Amal" or (u.get("who") == "chat" and u.get("typed_by") == "Amal")


def supplies(turns, fix_times=()):
    """{turn index: why} - the tutor's lines that GIVE him a form (WS-31): her typed chat line; a line a counted slip
    names as her fix (its t_fix within 3 s); her answer to his 'how do I say'; or a recast - her line shares a near-same
    Arabic word with his Arabic line of the 20 s before and does not open with a question word ('شو مالها؟' is a question
    to him, not a fix)."""
    out = {}
    fix_times = [float(x) for x in fix_times if x is not None]
    for j, u in enumerate(turns):
        if not _is_amal(u):
            continue
        toks = [w for w, cut in arabic_tokens(u.get("text")) if not cut]
        if u.get("who") == "chat":
            if toks or re.search(r"[0-9]", u.get("text") or ""):
                out[j] = "her typed line in the chat"
            continue
        if any(abs(float(u["t"]) - x) <= FIX_S for x in fix_times):
            out[j] = "her fix of a counted slip"
            continue
        if not toks:
            continue
        mine = [k for k in range(j - 1, max(-1, j - 12), -1) if turns[k].get("who") == "Medi" and float(u["t"]) - float(turns[k]["t"]) <= RECAST_S]
        if any(ASKS.search(turns[k].get("text") or "") for k in mine):
            out[j] = "her answer to his 'how do I say'"
            continue
        if norm(toks[0]) in QWORDS or core(toks[0]) in QWORDS or (
                re.search(r"[?؟]", u.get("text") or "") and any(core(w) in QWORDS or norm(w) in QWORDS for w in toks)):
            continue                      # a question to him ('شو اليوم؟', 'طب امتى الشمس بتطلع؟') gives him nothing to repeat
        his = [w for k in mine for w, cut in arabic_tokens(turns[k].get("text")) if not cut]
        content = [w for w in toks if len(core(w)) >= 3 and core(w) not in FUNCTION]
        if his and any(similar(a, b) for a in content for b in his):
            out[j] = "her recast of his line"
    return out


def tutor_before(turns, i, window):
    """Indexes of the tutor's lines (spoken or typed) in the `window` s before his line i, nearest first."""
    t = float(turns[i]["t"])
    return [j for j in range(i - 1, -1, -1) if _is_amal(turns[j]) and 0 <= t - float(turns[j]["t"]) <= window][:12]


def echo_of(turns, i, j):
    """His whole Arabic on line i is words of her line j (he says her words back)."""
    mine = [w for w, cut in arabic_tokens(turns[i].get("text")) if not cut]
    hers = [w for w, cut in arabic_tokens(turns[j].get("text")) if not cut]
    return bool(mine) and bool(hers) and all(any(similar(a, b) for b in hers) for a in mine)


def mmss(t):
    t = int(float(t))
    return "%02d:%02d" % divmod(t, 60)


def judge_word(turns, i, word, key, key_of, sup):
    """(state, reason, tutor turn index or None) for one word of his line i. state: repeat | helped | independent |
    unresolved. key_of(word) -> list key or None (her words matched the same way as his)."""
    same = []
    for j in tutor_before(turns, i, REPEAT_S):
        for w, cut in arabic_tokens(turns[j].get("text")):
            if cut:
                continue
            if similar(w, word) or (key and key_of(w) == key):
                same.append(j)
                break
    if same:
        j = same[0]
        if j in sup:
            return "repeat", "Repeat of the tutor's %s at %s («%s»): not credited, not a mistake (WS-31)" % (
                sup[j].replace("her ", ""), mmss(turns[j]["t"]), (turns[j].get("text") or "")[:80]), j
        if echo_of(turns, i, j):
            return "repeat", "He says the tutor's words back (%s «%s»): a repeat, not credited, not a mistake (WS-31)" % (
                mmss(turns[j]["t"]), (turns[j].get("text") or "")[:80]), j
        own = [w for w, cut in arabic_tokens(turns[i].get("text"))]
        if len(own) >= 3:
            return "independent", "Her question used the word; he used it in his own new answer (3+ words)", j
        return "helped", "Same vocabulary said by the tutor within 15 s (her own wording, not a fix): practice, half credit", j
    end = float(turns[i].get("end") or turns[i]["t"])
    after = [u for u in turns if _is_amal(u) and u.get("who") != "chat" and 0 <= float(u["t"]) - end <= 8]
    if any(CUE.search(u.get("text") or "") for u in after):
        return "unresolved", "A correction cue from the tutor right after; the readers decide", None
    return "independent", "Word he said on his own (WS-30: a word said alone counts like any other)", None


# ------------------------------------------------------------------ the Word Bank side (additions + patches)
class Keys:
    """Which list word a token is: the Word Bank's strict matcher first (one key = that word, two = unclear), then the
    Lessons page's sheet lookup (her forms with endings: راسها = راس + ها). sheet = {token: {on_sheet, key}} from
    scripts/lessons_page_node.cjs."""

    def __init__(self, words, sheet=None, catalog=None):
        import speaking_evidence as se
        self.se = se
        self.m = se.StrictMatcher(words)
        self.sheet = sheet or {}
        self.words = {w["key"]: w for w in words if w.get("active", True)}
        self.keys = set(self.words)
        catalog = (J(os.path.join(REPO, "docs", "data", "word-bank-catalog.json"), {}) or {}) if catalog is None else catalog
        self.group = {}                   # key -> catalog group (verbs and their forms)
        self.forms = {}                   # normalised form -> {(group key, entry id, documented)}
        for g in catalog.get("groups") or []:
            for k in g.get("keys") or [g["key"]]:
                self.group[k] = g
            for f in g.get("entries") or []:
                cand = [(f.get("word"), f.get("provenance") != "inferred"), (f.get("arabic"), f.get("provenance") != "inferred")]
                for p_ in f.get("persons") or []:
                    cand += [(re.sub(r"^(Ana|inta|inti|huwwe|heyye|i7na|intu|humme)\s+", "", str(p_.get("word") or ""), flags=re.I), p_.get("provenance") != "inferred"),
                             (PRONOUNS.sub("", str(p_.get("arabic") or "")), p_.get("provenance") != "inferred")]
                for form, documented in cand:
                    n = jsnorm(form)
                    if n and " " not in n:
                        self.forms.setdefault(n, set()).add((g["key"], f["id"], documented))

    def of(self, w):
        k = self.lookup(w)
        return k[0] if k and k[1] == "one" else None

    def _stems(self, w):
        n = jsnorm(w)
        return (n,) + tuple(n[:-len(e)] for e in OBJ_ENDS if n.endswith(e) and len(n) - len(e) >= 3)

    def entry(self, key, w):
        """The Word Bank form (entry id) of a verb row this word is, None when none fits. Not a verb row -> ''."""
        g = self.group.get(key)
        if not g or g.get("type") != "Verb":
            return ""
        for n in self._stems(w):
            hits = {(k, e, d) for k, e, d in self.forms.get(n, ()) if k == g["key"]}
            if len({e for _, e, _ in hits}) == 1:
                return next(iter(hits))[1]
            doc = {e for _, e, d in hits if d}
            if len(doc) == 1:
                return next(iter(doc))
        return None

    def lookup(self, w):
        """(key or keys, how) - how: one | unclear | sheet | part | none."""
        m = self.m.match(w)
        if len(m) == 1:
            return next(iter(m)), "one"
        if len(m) > 1:
            return sorted(m), "unclear"
        for cand in self._stems(w):
            gk = {k for k, _, _ in self.forms.get(cand, ())}
            if len(gk) == 1:
                return next(iter(gk)), "one"
            if len(gk) > 1:
                return sorted(gk), "unclear"
        sh = self.sheet.get(norm(w)) or {}
        k = sh.get("key")
        if sh.get("on_sheet") and k in self.keys:
            if k in self.group and self.group[k].get("type") == "Verb":
                return None, "none"       # a verb is only ever matched by one of its own forms (above)
            if related(w, self.words[k]):
                return k, "one"
            return k, "part"              # one word of a longer list phrase (أنا of 'أنا بطبخ'): not that list word
        if sh.get("on_sheet") and k:
            return k, "sheet"             # a taught verb not yet in the saved copy of her list (taught:...)
        return None, "none"


OBJ_ENDS = ("هم", "كم", "ها", "نا", "ني", "ك", "ه", "ي")
PRONOUNS = re.compile(r"^(أنا|انا|إنت|انت|إنتي|انتي|هو|هي|إحنا|احنا|إنتو|انتو|هم)\s+")


def jsnorm(s):
    """word-bank-core.js normalize(): NFKC, no marks, one alif."""
    import speaking_evidence as se
    return se.normalize(str(s or "")).strip(" .،,؟?!")


def related(w, doc):
    """Is this word a form of the list word (the word itself, + el-, + an ending: راسها of راس)? A word of a longer list
    phrase is not (أنا of 'أنا بطبخ')."""
    n = core(w)
    for f in re.split(r"[/،,(]", str(doc.get("arabic") or "")):
        f = PRONOUNS.sub("", f.strip()).strip(" )؟?")
        if not f or " " in f:
            continue
        c = core(f)
        if c and (n == c or (len(c) >= 3 and n.startswith(c) and len(n) - len(c) <= 3)):
            return True
    return False


def lesson_events(events, date):
    return [e for e in events if e.get("lesson_date") == date and e.get("speaker") == "Medi"]


def event_on(evs, t0, t1, word, key):
    for e in evs:
        if t0 - 1.0 <= float(e.get("t_start") or -99) <= t1 + 1.0 and (
                (key and e.get("word_key") == key) or (e.get("text") and similar(e["text"].strip(" .،؟?!"), word))):
            return e
    return None


def fix_times_of(detail):
    out = []
    for g in (detail.get("grammar_errors") or []) + (detail.get("vocab_errors") or []):
        for k in ("t_fix",):
            if g.get(k) is not None:
                out.append(g[k])
    return out


def his_rulings(date, rows=None):
    """[row] - his own heard-word rows on this lesson that name the list word or the credit (WS-29: 'keefak, no credit')."""
    if rows is None:
        try:
            import medi_corrections as MC
            rows = MC.text_rows()
        except Exception:  # noqa: BLE001
            rows = []
    return [r for r in rows if str(r.get("date")) == date and r.get("by") == "medi" and r.get("who") == "Medi"
            and (r.get("word_key") or r.get("credit"))]


def plan(date, detail, events, keys, off=(), rulings=None):
    """What the Word Bank needs for one lesson: (additions, patches, rows). rows = every Arabic word of his with the
    event it will be judged by (or why none)."""
    turns = detail["turns"]
    sup = supplies(turns, fix_times_of(detail))
    evs = lesson_events(events, date)
    anchor = next((e for e in sorted(evs, key=lambda e: e.get("t_start") or 0)), None)
    adds, patches, rows = [], {}, []
    mine = his_rulings(date, rulings)
    for i, u in enumerate(turns):
        if u.get("who") != "Medi":
            continue
        t0, t1 = float(u["t"]), float(u.get("end") or u["t"])
        if any(a <= t0 <= b for a, b in off):
            for w, cut in arabic_tokens(u.get("text")):
                rows.append({"i": i, "t": t0, "word": w, "state": "na", "why": "off-lesson"})
            continue
        for n, tk in enumerate(word_tokens(u.get("text"))):
            w, cut, shown = tk["ar"], tk["cut"], tk["shown"]
            row = {"i": i, "t": t0, "word": w, **({"shown": shown} if shown != w else {})}
            if cut:
                rows.append(dict(row, state="na", why="broken off before the end of the word (not a try)"))
                continue
            key, how = keys.lookup(w)
            ruling = next((r for r in mine if abs(float(r["t"]) - t0) <= 1.0 and (similar(r.get("heard") or "", w) or
                                                                                (r.get("word_key") and r["word_key"] in ([key] if isinstance(key, str) else key or [])))), None)
            if ruling and ruling.get("credit") == "none":
                rows.append(dict(row, state="na", key=ruling.get("word_key"), why="his own note: " + str(ruling.get("quote") or "no credit")))
                continue
            if ruling and ruling.get("word_key") and how == "unclear" and ruling["word_key"] in key:
                key, how = ruling["word_key"], "one"
            if how == "unclear":
                rows.append(dict(row, state="na", why="two list words are spelled this way (%s): unclear which he meant" % " / ".join(
                    "%s '%s'" % (k, (keys.words.get(k) or {}).get("english") or "") for k in key)))
                continue
            if how == "part":
                rows.append(dict(row, state="na", why="one word of a longer list phrase (%s), not a list word by itself" % key))
                continue
            if how in ("none", "sheet"):
                import loanwords
                why = ("a name, dish or loan word (never on her list)" if _loan(loanwords, w)
                       else "a word the tutor taught that is not in the saved copy of her list yet" if how == "sheet"
                       else "not on her word list (left out of the Words %; it goes to her new-words list)")
                rows.append(dict(row, state="na", why=why, key=key))
                continue
            row["key"] = key
            e = event_on(evs, t0, t1, w, key)
            state, why, j = judge_word(turns, i, w, key, keys.of, sup)
            if e is not None:
                row["event"] = e["id"]
                p = _patch(e, state, why, turns, j)
                if p:
                    patches[e["id"]] = p
                    row["patched"] = state
                rows.append(row)
                continue
            if anchor is None:
                rows.append(dict(row, state="na", why="no Word Bank evidence for this lesson yet"))
                continue
            entry = keys.entry(key, w)
            if entry is None:
                rows.append(dict(row, state="na", why="a form of %s the Word Bank does not list yet (it cannot place this one)" % key))
                continue
            ev = _event(date, anchor, u, i, n, shown, key, state, why, turns, j)
            if entry:
                ev["entry_id"] = entry
            adds.append({"anchor_id": anchor["id"], "expected_source": anchor.get("source_sha256"), "event": ev, "by": BY})
            evs.append(ev)
            row["event"] = ev["id"]
            row["added"] = state
            rows.append(row)
    return adds, patches, rows


def _loan(loanwords, w):
    try:
        return bool(loanwords.loan_token(w))
    except Exception:  # noqa: BLE001 - a lookup hiccup is 'not a loan word'
        return False


def _repeat_fields(turns, j):
    return {"immediate_repeat": True, "repeat": True,
            **({"repeat_of": {"t": float(turns[j]["t"]), "text": (turns[j].get("text") or "")[:120]}} if j is not None else {})}


def _patch(e, state, why, turns, j):
    """A patch on a Word Bank event the engine words made: a repeat of her fix loses its credit (WS-31); a word said alone
    that sat 'unresolved' is judged (WS-30). Nothing else is touched (a reader's or Amal's ruling stays)."""
    if e.get("review_locked") or e.get("medi_ruling") or e.get("assessment") in ("incorrect", "recall_failure"):
        return None
    exp = {k: e.get(k) for k in ["source_sha256", "row_id", "word_key", "text", "t_start", "t_end", "assessment", "reason"]}
    if state == "repeat":
        ch = {"assessment": "helped", "reason": why, "by": BY, "rule": "WS-31", **_repeat_fields(turns, j)}
    elif e.get("assessment") == "unresolved" and str(e.get("reason") or "").startswith("Isolated production") and state in ("independent", "helped"):
        ch = {"assessment": state, "reason": why + " (WS-30)", "by": BY, "rule": "WS-30", "classification": "lexical",
              "vocab_points": {"independent": 1, "helped": 0.5}[state]}
    else:
        return None
    return {"expected": exp, "changes": ch}


def _event(date, a, u, i, n, w, key, state, why, turns, j):
    off = float(a.get("t_start") or 0) - float(a.get("local_start") or 0)
    t0, t1 = float(u["t"]), float(u.get("end") or u["t"])
    rid = "cover:%s:%s" % (date, round(t0, 2))
    ev = {"id": sha([BY, date, round(t0, 2), n, key, w]), "lesson_date": date, "word_key": key,
          "local_start": round(t0 - off, 3), "local_end": round(t1 - off, 3), "candidate_keys": [key],
          "source_id": a.get("source_id"), "source_sha256": a.get("source_sha256"), "row_id": rid, "item_ids": [],
          "t_start": t0, "t_end": t1, "speaker": "Medi", "speaker_basis": a.get("speaker_basis"), "text": w,
          "original_text": u.get("engine") or u.get("text") or "", "match_method": "word_coverage",
          "assessment": "helped" if state == "repeat" else state, "assessment_status": "provisional", "spoken": True,
          "wording_status": "asr", "review_ids": [], "version": a.get("version"),
          "context": [{"row_id": rid, "speaker": "Medi", "text": u.get("text") or "", "timeline_start": t0, "timeline_end": t1}],
          "reason": why, "rule": "WS-31" if state == "repeat" else "WS-30", "classification": "lexical", "coverage": True}
    if state == "repeat":
        ev.update(_repeat_fields(turns, j))
    elif state in ("independent", "helped"):
        ev["vocab_points"] = {"independent": 1, "helped": 0.5}[state]
    return ev


def refresh(per, sheet, off_by_date=None, path=REVIEW_P, log=print, events=None, words=None):
    """Rebuild this file's additions and patches in the review overlay for every lesson in scope. -> {date: rows}."""
    review = J(path)
    if review is None:
        return {}
    words = (J(WORDS_P, {}) or {}).get("items", []) if words is None else words
    events = (J(EVID_P, {}) or {}).get("events", []) if events is None else events
    # the review overlay's other additions are evidence too (his own heard credits, WS-29): never a second event
    others = [x["event"] for x in review.get("additions") or [] if x.get("by") != BY]
    keys = Keys(words, sheet)
    try:
        import medi_corrections as MC
        rulings = MC.text_rows()
    except Exception:  # noqa: BLE001
        rulings = []
    adds, pats, out = [], {}, {}
    for d in sorted(per):
        if not in_scope(d):
            continue
        a, p, rows = plan(d, per[d], events + others, keys, (off_by_date or {}).get(d) or (), rulings)
        adds += a
        pats.update(p)
        out[d] = rows
    keep = [x for x in review.get("additions") or [] if x.get("by") != BY]
    P = review.setdefault("patches", {})
    old = {k: v for k, v in P.items() if (v.get("changes") or {}).get("by") == BY}
    pats = {k: v for k, v in pats.items() if k not in P or (P[k].get("changes") or {}).get("by") == BY}
    if [x for x in review.get("additions") or [] if x.get("by") == BY] != adds or old != pats:
        for k in old:
            P.pop(k, None)
        P.update(pats)
        review["additions"] = keep + adds
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(review, f, ensure_ascii=False, indent=2)
            f.write("\n")
    log("word_coverage: %d words added to the Word Bank, %d engine-word events re-judged (%d repeats) in %d lesson(s) from %s"
        % (len(adds), len(pats), sum(1 for v in pats.values() if v["changes"].get("repeat")) + sum(1 for x in adds if x["event"].get("repeat")),
           len(out), FROM))
    return out


CLIPS_P = os.path.join(REPO, "docs", "data", "word-bank-clips.json")


def ensure_clips(path=CLIPS_P, review_p=REVIEW_P, log=print, cut=None):
    """Every word event the review overlay adds (this file's, his heard credits) gets its clip, like the matcher's own
    events (the Word Bank audit requires a playable clip that holds the line): cut from the lesson page audio
    docs/lessons/<date>/audio/lesson.mp3 (the lesson clock), named like scripts/build_audit_audio.py. -> clips cut."""
    import math, subprocess, shutil
    doc = J(path)
    review = J(review_p) or {}
    if doc is None:
        return 0
    clips = doc.setdefault("clips", {})
    ffmpeg = shutil.which("ffmpeg")
    n = 0
    changed = False
    for a in review.get("additions") or []:
        e = a.get("event") or {}
        if e.get("speaker") != "Medi" or a.get("by") not in (BY, "heard-credit") or e.get("id") in clips:
            continue
        date = e["lesson_date"]
        src = os.path.join(REPO, "docs", "lessons", date, "audio", "lesson.mp3")
        ctx = e.get("context") or []
        start = max(0, math.floor(min([e["t_start"]] + [r["timeline_start"] for r in ctx if isinstance(r.get("timeline_start"), (int, float))]) - 1))
        end = math.ceil(max([e["t_end"]] + [r["timeline_end"] for r in ctx if isinstance(r.get("timeline_end"), (int, float))]) + 1)
        name = "context-" + hashlib.sha256(str((date, start, end)).encode()).hexdigest()[:16] + ".mp3"
        url = "lessons/%s/clips/%s" % (date, name)
        out = os.path.join(REPO, "docs", url)
        if not os.path.exists(out):
            if not os.path.exists(src) or not (ffmpeg or cut):
                log("word_coverage: no clip for %s %s (no lesson audio or no ffmpeg)" % (date, e.get("text")))
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if cut:
                cut(src, start, end, out)
            else:
                subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-i", src, "-t", str(end - start),
                                "-ar", "16000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "48k", out], check=True, capture_output=True)
            n += 1
        with open(out, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        clips[e["id"]] = {"event_id": e["id"], "lesson": date, "source_sha256": e.get("source_sha256"), "sentence_audio_url": url,
                          "start": start, "end": end, "duration": end - start, "speakers": ["Amal", "Medi"], "partial_coverage": False,
                          "source_bound": True, "contains_displayed_context": True, "clip_sha256": h, "cut_by": BY}
        changed = True
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
    log("word_coverage: %d new clips cut" % n)
    return n


def tokens_for_sheet(per):
    out = set()
    for d, v in per.items():
        if not in_scope(d):
            continue
        for u in v["turns"]:
            if u.get("who") == "Medi" or _is_amal(u):
                for w, cut in arabic_tokens(u.get("text")):
                    if not cut:
                        out.add(norm(w))
    return sorted(out)


# ------------------------------------------------------------------ the transcript side (chips)
def chips(date, detail, rows, unscored=()):
    """[(turn index, chip)] for every Arabic word of his that no vocab chip judges yet: a repeat chip (WS-31) or a grey
    chip with the reason (WS-30). unscored = the Word Bank's own null-point events of this lesson (lessons_page_node.cjs)."""
    if not in_scope(date):
        return []
    tm = detail.get("tmarks") or {}
    have = {}
    for k, v in tm.items():
        for c in v.get("c", []):
            if c.get("k") == "vocab":
                have.setdefault(int(k), []).append(c)
    by_id = {e["id"]: e for e in unscored or []}
    out, seen = [], set()
    for r in rows:
        i = r["i"]
        dup = (i, core(r["word"]))
        if dup in seen:
            continue
        seen.add(dup)
        mine = have.get(i, [])
        if any((r.get("key") and c.get("key") == r.get("key")) or similar(c.get("ar") or "", r["word"]) or
               any(similar(x, r["word"]) for x in re.split(r"[\s،,.؟?]+", str(c.get("said") or "")) if x) for c in mine):
            continue
        e = by_id.get(r.get("event"))
        if r.get("state") == "na":
            out.append((i, {"k": "na", "s": "na", "label": "vocab", "w": None, "ar": r["word"], "why": r["word"] + ": " + r["why"], "rule": "WS-30"}))
        elif (e and e.get("repeat")) or r.get("added") == "repeat" or r.get("patched") == "repeat":
            rep = (e or {}).get("repeat_of") or {}
            out.append((i, {"k": "vocab", "s": "repeat", "ar": r["word"], "key": r.get("key"),
                            "why": (e or {}).get("reason") or "repeat of the tutor's word: not credited, not a mistake (WS-31)",
                            **({"amal_t": rep.get("t"), "amal_line": rep.get("text")} if rep else {}), "rule": "WS-31",
                            **({"src": "wb:" + r["event"]} if r.get("event") else {})}))
        elif e:
            out.append((i, {"k": "na", "s": "na", "label": "vocab", "ar": r["word"], "key": r.get("key"),
                            "why": r["word"] + ": " + (e.get("reason") or "not scored"), "rule": "WS-30",
                            **({"src": "wb:" + r["event"]} if r.get("event") else {})}))
        elif r.get("added") or r.get("patched"):
            out.append((i, {"k": "na", "s": "na", "label": "vocab", "ar": r["word"], "key": r.get("key"),
                            "why": r["word"] + ": judged on the next rebuild (%s)" % (r.get("added") or r.get("patched")), "rule": "WS-30"}))
        else:
            out.append((i, {"k": "na", "s": "na", "label": "vocab", "ar": r["word"], "key": r.get("key"),
                            "why": r["word"] + ": on her list, no Word Bank mark yet", "rule": "WS-30"}))
    return out


def report(date, repo=REPO):
    """Every Arabic word of his on the published lesson and the chip it carries (vocab ✓ ◐ ✗ ↻ or grey reason)."""
    d = J(os.path.join(repo, "docs", "data", "lessons", date + ".json"), {}) or {}
    turns, tm = d.get("turns") or [], d.get("tmarks") or {}
    out = []
    for i, u in enumerate(turns):
        if u.get("who") != "Medi":
            continue
        cs = [c for c in (tm.get(str(i)) or {}).get("c", []) if c.get("k") == "vocab" or (c.get("k") == "na" and c.get("label") in ("vocab", "lesson"))]
        for w, cut in arabic_tokens(u.get("text")):
            hit = next((c for c in cs if similar(c.get("ar") or "", w) or (c.get("why") or "").startswith(w + ":")
                        or any(similar(x, w) for x in re.split(r"[\s،,.؟?]+", str(c.get("said") or "")) if x)), None)
            if hit is None and cs and any(c.get("label") == "lesson" for c in cs):
                hit = cs[0]
            out.append({"t": mmss(u["t"]), "word": w, "cut": cut, "state": (hit or {}).get("s"), "why": (hit or {}).get("why")})
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 3 and sys.argv[1] == "report":
        rows = report(sys.argv[2])
        from collections import Counter
        for r in rows:
            print(r["t"], r["word"], r["state"] or "-- NO MARK --", (r["why"] or "")[:90])
        print(Counter(r["state"] or "none" for r in rows))
