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
FROM = "2026-08-25"   # every lesson: Medi 2026-10-09 "you are making rules for all these right? to solve in the future and past"
BY = "word-coverage"
# PG-43 (Medi 2026-10-10 "For these rules like this just keep a not of it on your end but dont publish. its not useful
# info"): a grey reason that only restates a standing rule, not something about his word. The chip stays in the data
# (WS-30 still accounts for the word: report() reads hidden chips) with quiet = the rule and hide = "quiet", so no page
# draws it; the build prints how many per lesson.
QUIET = {"a preposition: scored as grammar, not as a word": "PG-43"}
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


PRONOUN_WORDS = {"انا", "انت", "انتي", "هو", "هي", "احنا", "انتو", "هم", "همه", "هيه", "هوه"}


def is_pronoun(w):
    """WS-32 (Medi 2026-10-09 "Lets leave out all the anna inti inta heyya huwwe humme e7na we can assume I know these
    always"): a subject pronoun is never a judged word - no chip, no credit, no 'not on her list'."""
    n = re.sub(r"(.)\1{2,}$", r"\1", norm(w))       # a pronoun he stretches (10-09 03:27 أنااا) is the pronoun
    return n.lstrip("و") in PRONOUN_WORDS or n in PRONOUN_WORDS


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
            # WS-34: the article el- said alone (ال / أل / إل while he looks for the noun) is not a word
            if not n or n in FILLERS or len(n) < 2 or re.fullmatch(r"[\u0627\u0622\u0647\u0645\u0649]+", n) or re.fullmatch(r"[\u0627\u0623\u0625\u0622]\u0644", n):
                items.append(None)
                continue
            items.append({"ar": w.rstrip("\u0640"), "cut": cut, "shown": w.rstrip("\u0640"), "latin": False, "strong": True})
        elif tok not in (",", "\u060c"):
            pend = None
    out = []
    for k, it in enumerate(items):
        if it is None or is_pronoun(it["ar"]):
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


class Sup(dict):
    """{turn index: why} + given = {turn index: [Arabic words of her fix as the slip row writes it]}."""

    def __init__(self):
        super().__init__()
        self.given = {}


def her_words(turns, j, sup=None):
    """The Arabic words of her line j, plus the words of the fix a counted slip says she gave there (the engine may
    have written her Arabic in English letters: 10-08 07:12 'Men not.' = her من نار)."""
    out = [w for w, cut in arabic_tokens(turns[j].get("text")) if not cut]
    return out + list(((sup and getattr(sup, "given", None)) or {}).get(j, []))


def supplies(turns, fix_times=(), date=None):
    """{turn index: why} - the tutor's lines that GIVE him a form (WS-31): her typed chat line; a line a counted slip
    names as her fix (its t_fix within 3 s); her answer to his 'how do I say'; or a recast - her line shares a near-same
    Arabic word with his Arabic line of the 20 s before and does not open with a question word ('شو مالها؟' is a question
    to him, not a fix)."""
    out = Sup()
    fixes = [(float(x[0]), x[1]) if isinstance(x, (list, tuple)) else (float(x), None) for x in fix_times if x is not None
             and (not isinstance(x, (list, tuple)) or x[0] is not None)]
    # each fix belongs to her ONE line nearest its time (10-08 09:48 'بال مين؟' sat 2.5 s before her 09:51 fix 'بالي على
    # خطيبتي' and took its words, so his خطيبتي of 09:48 - said BEFORE the fix - read as a repeat of it)
    spoken = [j for j, u in enumerate(turns) if u.get("who") == "Amal"]
    owner = {}
    for t_, r in fixes:
        near = min(spoken, key=lambda j: abs(float(turns[j]["t"]) - t_), default=None)
        if near is not None and abs(float(turns[near]["t"]) - t_) <= FIX_S:
            owner.setdefault(near, []).append(r)
    for j, u in enumerate(turns):
        if not _is_amal(u):
            continue
        toks = [w for w, cut in arabic_tokens(u.get("text")) if not cut]
        if u.get("who") == "chat":
            if toks or re.search(r"[0-9]", u.get("text") or ""):
                out[j] = "her typed line in the chat"
            continue
        mine_fix = owner.get(j, []) if str(date or "") >= AGAIN_FROM else [r for t_, r in fixes if abs(float(u["t"]) - t_) <= FIX_S]
        if mine_fix:
            out[j] = "her fix of a counted slip"
            out.given[j] = [w for r in mine_fix if r for w, cut in arabic_tokens(r) if not cut]
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


# GR-34 (Medi 2026-10-10 on 10-08 66:56 "شكراً. بشوفك. Bye.": "this isnt a repeat ... I replied to see you, with see
# you"): greetings, thanks and goodbyes are answered in kind - his بشوفك after her يلا بشوفك is his own reply, never a
# repeat of her word (words and grammar alike)
REPLY_WORDS = {"بشوفك", "بشوفكم", "مرحبا", "مرحبتين", "اهلا", "اهلين", "شكرا", "سلام", "السلامه", "مع", "يعطيك", "يعطيكي",
               "العافيه", "الله", "يعافيك", "يعافيكي", "تصبح", "تصبحي", "على", "خير", "الخير", "صباح", "مسا", "مساء", "كيفك",
               "كيفكم", "منيح", "منيحه", "الحمدلله", "الحمد", "لله", "يلا", "باي", "وانت", "وانتي", "من", "اهله", "تسلم",
               "تسلمي", "عفوا", "اهلًا", "شكراً", "ماشي", "تمام"}


REPLY_ONE = {"بشوفك", "بشوفكم", "مرحبا", "مرحبتين", "اهلا", "اهلين", "شكرا", "سلام", "باي", "يعطيك", "يعطيكي", "يعافيك",
             "يعافيكي", "تصبح", "تصبحي", "تسلم", "تسلمي", "عفوا"}


def is_reply(words):
    """GR-34: his Arabic is only greeting / thanks / goodbye words - a reply in kind, not a repeat."""
    ws = [jsnorm(w).replace("ة", "ه") for w in words]
    return bool(ws) and all(w in REPLY_WORDS or jsnorm(w) in REPLY_WORDS for w in ws)


def echo_of(turns, i, j):
    """His whole Arabic on line i is words of her line j (he says her words back)."""
    mine = [w for w, cut in arabic_tokens(turns[i].get("text")) if not cut]
    if is_reply(mine):
        return False
    hers = [w for w, cut in arabic_tokens(turns[j].get("text")) if not cut]
    return bool(mine) and bool(hers) and all(any(similar(a, b) for b in hers) for a in mine)


def mmss(t):
    t = int(float(t))
    return "%02d:%02d" % divmod(t, 60)


def judge_word(turns, i, word, key, key_of, sup, plural=None, strict=False):
    """(state, reason, tutor turn index or None) for one word of his line i. state: repeat | helped | independent |
    unresolved. key_of(word) -> list key or None (her words matched the same way as his)."""
    same = []
    if jsnorm(word).replace("ة", "ه") in REPLY_ONE and any(  # GR-34
            is_reply([w for w, c in arabic_tokens(turns[j].get("text")) if not c][-2:]) for j in tutor_before(turns, i, REPEAT_S)):
        return "independent", "His own reply in kind (a greeting, thanks or goodbye): counts like any word (GR-34)", None
    for j in tutor_before(turns, i, REPEAT_S):
        # WS-34: when she ASKS for a form ('شو plural حجر؟'), only her exact form is hers; the form he finds (حجار) is his
        ask = j not in sup and re.search(r"[?؟]", turns[j].get("text") or "")
        for w in her_words(turns, j, sup):
            if ask and core(w) != core(word):
                continue
            if plural and plural(word) and not plural(w) and core(w) != core(word):
                continue                  # she gave the singular (حجر); the plural he makes of it (حجار) is his own
            kw = key_of(w) if strict else None
            if (similar(w, word) and not (key and kw and kw != key)) or (key and (kw if strict else key_of(w)) == key):
                same.append(j)        # WS-36 (strict): two list words a letter apart are two words (her عيان is not his عشان)
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
        # colour adjectives on the af3al pattern (أسود aswad 'Black (M/F)'): her row covers the feminine fa3la' and the
        # plural fu3l (سودا / سوداء / سود) - 10-08 08:36 'بلوزة سودا' (Medi: "soda is the femanine for aswad")
        self.colour = {}
        for w in self.words.values():
            m = re.fullmatch(r"ا(\S)(\S)(\S)", jsnorm(w.get("arabic") or ""))
            if m and w.get("topic") == "Adjectives":
                x = "".join(m.groups())
                for f in (x + "ا", x + "اء", x):
                    self.colour.setdefault(f, set()).add(w["key"])
        # WS-34 (Medi 2026-10-09 "can you give me a list of these from 10-8 not scored ... fix in a new chip"): her one-word
        # rows by their word (شمس, عند, مبارح), her Doc's plural column (حجار = her 7ajar's plural 7jaar), a day name
        # without يوم (الخميس = her 'يوم الخميس' Thursday)
        self.one, self.plural, self.inner, self.coll = {}, {}, {}, {}
        for w in self.words.values():
            for f in one_word_forms(w.get("arabic")):
                self.one.setdefault(f, set()).add(w["key"])
                m = re.match(r"(?:بال|لل|عال|فال)(\S{3,})$", f)     # her بالليل 'At night': ليل is its noun
                if m:
                    self.inner.setdefault(m.group(1), set()).add(w["key"])
            for piece in re.split(r"[/،,(]", str(w.get("arabic") or "")):
                piece = piece.strip(" )")
                if re.fullmatch(r"[^\s]{3,}ة", piece) and not jsnorm(piece).startswith("ال"):   # never الليلة "Tonight"             # her وردة 'Flower': ورد (flowers), وردات
                    for x in (jsnorm(piece)[:-1], jsnorm(piece)[:-1] + "ات"):
                        self.coll.setdefault(x, set()).add(w["key"])
            m = re.fullmatch(r"يوم\s+(\S+)", jsnorm(w.get("arabic") or ""))
            if m:
                self.one.setdefault(core(m.group(1)), set()).add(w["key"])
            if not one_word_forms(w.get("arabic")):
                continue
            pl = str(w.get("plural") or "")
            cands = [skel_ar(x) for x in re.findall(r"[\u0621-\u064A]+", pl)]
            cands += [skel_lat(x.split()[0]) for x in re.split(r"[/,]", re.sub(r"\([^)]*\)", "", pl))
                      if x.strip() and re.match(r"[A-Za-z0-9]", x.strip())]
            for sk in cands:
                if len(sk) >= 4 or (len(sk) == 3 and "A" in sk):   # three short letters (Hadaya -> hdy) match too much
                    self.plural.setdefault(sk, set()).add(w["key"])
                if len(_squeeze(sk.replace("A", ""))) >= 4:
                    self.plural.setdefault("~" + _squeeze(sk.replace("A", "")), set()).add(w["key"])
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
            # WS-35: the bare form after رح / بدي / لازم is the present without its b- (her بعمل: أعمل, نعمل, تعمل,
            # يعمل) - the Word Bank's Future entry, whose Arabic her catalog leaves empty (10-08 14:53 نعمل, 15:33 أعمله)
            fut = next((f for f in g.get("entries") or [] if f.get("label") == "Future"), None)
            pres = next((f for f in g.get("entries") or [] if f.get("label") == "Present"), None)
            if fut and pres and g.get("type") == "Verb":
                for p_ in pres.get("persons") or []:
                    n = jsnorm(PRONOUNS.sub("", str(p_.get("arabic") or "")))
                    m = re.fullmatch(r"ب([تين])(\S{2,})", n) or re.fullmatch(r"ب(\S{3,})", n)
                    if not m or " " in n:
                        continue
                    bare = (m.group(1) + m.group(2)) if m.re.groups == 2 else "ا" + m.group(1)
                    if not any(k == g["key"] for k, _, _ in self.forms.get(bare, ())):   # her own entry for it wins
                        self.forms.setdefault(bare, set()).add((g["key"], fut["id"], False))

    def of(self, w):
        k = self.lookup(w)
        return k[0] if k and k[1] == "one" else None

    def same_word(self, keys):
        """Two rows of her list that are the same word (بلبس: 'balbes' and 'ana balbes', both 'I wear'): the row the Word
        Bank keeps the forms on (a catalog group), else the first - or None when they are really different words."""
        forms = {PRONOUNS.sub("", jsnorm((self.words.get(k) or {}).get("arabic") or "")).strip() for k in keys}
        if len(forms) != 1 or not next(iter(forms)):
            return None
        # the same MEANING too: مرة is her 'Bitter (F)', 'Woman' and 'One time' - three words, not one (WS-33)
        mean = [set(re.findall(r"[a-z]{3,}", ((self.words.get(k) or {}).get("english") or "").lower())) - {"the", "and", "for"} for k in keys]
        if not set.intersection(*mean):
            return None
        grouped = [k for k in keys if k in self.group]
        return (grouped or keys)[0]

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
        self.via = None
        m = self.m.match(w)
        if len(m) == 1:
            return next(iter(m)), "one"
        if len(m) > 1:
            same = self.same_word(sorted(m))
            return (same, "one") if same else (sorted(m), "unclear")
        c = self.colour.get(jsnorm(w))
        if c and len(c) == 1:
            return next(iter(c)), "one"
        # the engine writes his د as ذ, ت as ث, ض as ظ (هذاك for her هداك Hadaak 'That (M)', 10-08 1:03:37): her word
        f = w.translate(SOUND_FOLD)
        if f != w:
            m = self.m.match(f)
            if len(m) == 1:
                return next(iter(m)), "one"
        for cand in self._stems(w):
            gk = {k for k, _, _ in self.forms.get(cand, ())}
            if len(gk) == 1:
                return next(iter(gk)), "one"
            if len(gk) > 1:
                return sorted(gk), "unclear"
        sh = self.sheet.get(norm(w)) or {}
        k = sh.get("key")
        verb = k in self.group and self.group[k].get("type") == "Verb"
        rel = sh.get("on_sheet") and k in self.keys and not verb and related(w, self.words[k])
        if rel is True:
            return k, "one"
        # WS-34 (self.via says so: a word found only this way that she taught today is still a new word, WS-18)
        self.via = "WS-34"
        if rel:                           # her one-word row said a letter off (بتلج of her بتتلج)
            return k, "one"
        # her 'that' أنو is his إنه (the -o ending is written ـو or ـه)
        if f.endswith("ه") and len(jsnorm(f)) >= 3:
            m = self.m.match(f[:-1] + "و")
            if len(m) == 1:
                return next(iter(m)), "one"
        n = jsnorm(w)                     # a word with و (and) in front is the word (وعشرين, والشمس)
        if n.startswith("و") and len(n) >= 4 and not self.m.match(w):
            k2, how2 = self.lookup(n[1:])
            self.via = "WS-34"
            if how2 == "one":
                return k2, how2
        hit = self.her_word(w)
        if hit and hit[1] == "one":
            return hit
        if getattr(self, "sound", False) and not hit:
            k3 = self.sound_word(w)
            if k3:
                self.via = "WS-37"
                return k3, "one"
        self.via = None
        if sh.get("on_sheet") and k in self.keys:
            if verb:
                return None, "none"       # a verb is only ever matched by one of its own forms (above)
            if hit:
                return hit                # two rows of hers this word could be (ولاد: 'Son' / 'Boy'): unclear
            if not in_phrase(w, self.words[k]):
                return None, "none"       # the sheet's guess is not a word of that phrase (لا inside '3لا3ة'): not on her list
            return k, "part"              # one word of a longer list phrase (مش of 'مش زاكي'): not that list word
        if hit:
            return hit
        if sh.get("on_sheet") and k:
            return k, "sheet"             # a taught verb not yet in the saved copy of her list (taught:...)
        return None, "none"


    def sound_word(self, w):
        """WS-37 (2026-10-10 audit of 10-08 / 10-09): her ONE word that his word is when only his sounds differ (S4: never a
        miss) - ق / غ / ك / ء are one sound for him (Farsi; her 2 is ق): أوي = her قوي 2awi, أكلب = her أغلب a8lab; the
        engine's ذ / ظ / ض / ز and ت / ط, س / ص swap (بوذة = her بوظة, مابسوت = her مبسوط); a long ا written in (ماي = her
        مي); the ending ة for her ا (هوة = her هوا). Only when exactly one word of hers fits."""
        n = jsnorm(w)
        if len(n) < 2 or n in FUNCTION or is_pronoun(w):
            return None
        cls = [set("قغك"), set("قءأئؤ"), set("ذظضزد"), set("تطث"), set("سصث")]
        opts = []
        for k, ch in enumerate(n):
            o = {ch}
            for c in cls:
                if ch in c:
                    o |= c
            if k == 0 and ch == "ا" and str(w).strip()[:1] == "أ":
                o |= set("قء")            # his written أ for her ق (أوي = قوي); never إ (إدام is not قدام)
            if k == len(n) - 1 and ch in "ةاه":
                o |= set("ةاه")
            opts.append(sorted(o))
        most = 1 if len(n) <= 4 else 2        # one sound changed in a short word, two in a long one (مابسوت = مبسوط)
        cands = {("", 0)}
        for k, o in enumerate(opts):
            nxt = set()
            for c, ch_ in cands:
                for x in o:
                    if ch_ + (x != n[k]) <= most:
                        nxt.add((c + x, ch_ + (x != n[k])))
                if n[k] == "ا" and 0 < k < len(n) - 1 and ch_ < most:
                    nxt.add((c, ch_ + 1))     # a long a he stretched or the engine wrote in
            cands = nxt
        one_change = {c for c, ch_ in cands if ch_ <= 1} - {n}
        cands = {c for c, ch_ in cands} - {n}
        hits = set()
        for c in cands:
            if len(c) < 2 or (len(c) < 3 and len(n) < 3):
                continue
            if c in self.one and len(self.one[c]) == 1:
                hits |= set(self.one[c])
                continue
            m = self.m.match(c)
            if len(m) == 1:
                hits |= set(m)
        if not hits and len(one_change) <= 400:   # with an ending (بوذتي = her بوظة + -i: the ة is ت before it); one sound only
            for c in one_change:
                m2 = re.match(r"(\S{2,})ت(ي|ك|كي|ه|ها|نا|كم|هم)$", c)
                for x in ([m2.group(1) + "ة"] if m2 else []) + [c]:
                    if len(x) >= 3:
                        h = (sorted(self.one[x])[0], "one") if len(self.one.get(x) or ()) == 1 else self.her_word(x)
                        if h and h[1] == "one":
                            hits.add(h[0])
        hits -= preps()                   # a sound match never makes a word a preposition (10-08 51:19 إدام is not قدام)
        hits = {k for k in hits if (self.group.get(k) or {}).get("type") != "Verb"}   # nor a verb form (10-09 9:44 قارة)
        return next(iter(hits)) if len(hits) == 1 else None

    def is_plural(self, w):
        """WS-34: is this word her Doc's plural of a row (حجار of 7ajar), not the row's own word?"""
        c = core(w)
        if c in self.one or self.m.match(w):
            return False
        sk = skel_ar(c)
        return bool(self.plural.get(sk) or ("A" in sk and self.plural.get("~" + _squeeze(sk.replace("A", "")))))

    def her_word(self, w):
        """WS-34: the one-word row of hers this word is (the word, + an ending, an extra إ in front: إمبارح = her مبارح),
        else the singular row whose plural (her Doc's plural column) it is. (key, 'one') | (keys, 'unclear') | None."""
        raw = str(w or "").strip()
        raw = raw[1:] if raw[:1] == "و" and len(jsnorm(raw)) >= 4 else raw
        c = core(MSA.get(jsnorm(w), w))
        tries = ([(jsnorm(w), False)] if jsnorm(w) != c else []) + [(c, False)]
        for x in (jsnorm(w), c):          # WS-35: the MSA ـاء (الهواء) and a long a written in (الهاوا) of her الهوا
            if x.endswith("اء") and len(x) >= 4:
                tries.append((x[:-1], False))
            if x.endswith("ا") and "ا" in x[1:-1] and len(x) >= 4:
                tries += [(x[:k] + x[k + 1:], False) for k in range(1, len(x) - 1) if x[k] == "ا"]
        m = re.match(r"(?:بال|لل|عال|فال)(\S{3,})$", jsnorm(w))
        if m:                             # بالأرض = her أرض with 'in the'
            tries += [("ال" + m.group(1), False), (m.group(1), False)]
        if c[:1] == "ا" and len(c) >= 4:  # إمبارح / امبارح = her مبارح; أ in front only on a verb (أشوف), never أهلا = هلا
            tries.append((c[1:], raw[:1] == "أ"))
        if not raw.endswith("ة"):         # ة is not the 'his' ending (سلامة is not سلام)
            tries += [(x[:-len(e)], v) for x, v in list(tries) for e in OBJ_ENDS if x.endswith(e) and len(x) - len(e) >= 3]
        if re.match(r"[ينت]", c) and len(c) >= 4:   # a verb's person prefix (نعمل, يبدأ): only ever one of her verbs
            tries.append((c[1:], True))
        for x, verb_only in tries:
            sk = skel_ar(x)
            bare = _squeeze(sk.replace("A", ""))    # her Latin often writes a long a single (Fasateen for فساتين)
            for hits in (self.one.get(x), self.inner.get(x), self.plural.get(sk) if len(sk) >= 3 else None,
                         self.plural.get("~" + bare) if len(bare) >= 4 and "A" in sk else None, self.coll.get(x)):
                if hits and verb_only and not all((self.group.get(k) or {}).get("type") == "Verb" for k in hits):
                    hits = None
                if hits and jsnorm(w) in MSA:
                    hits = {k for k in hits if str((self.words.get(k) or {}).get("english") or "").startswith(MSA_MEANS)} or hits
                if hits:
                    hits = sorted(hits)
                    if len(hits) == 1:
                        return hits[0], "one"
                    same = self.same_word(hits)
                    return (same, "one") if same else (hits, "unclear")
        return None


def phrase_span(toks, n, arabic, text):
    """WS-34: (the phrase as his line writes it, its tokens) when the words from token n on are her whole phrase (لو سمحت,
    على قلبك, مش مشكلة) and stand together on the line; else None."""
    ph = [x for x in jsnorm(arabic or "").split() if x]
    if len(ph) < 2 or n + len(ph) > len(toks):
        return None
    got = toks[n:n + len(ph)]
    if any(t["cut"] or not (core(t["ar"]) == core(p) or similar(t["ar"], p)) for t, p in zip(got, ph)):
        return None
    shown = [t["shown"] for t in got]
    if not re.search(r"\s*[،,]?\s*".join(re.escape(x) for x in shown), text or ""):
        return None
    return " ".join(shown), got


def one_word_forms(arabic):
    """The one-word forms of a row's Arabic (pieces split on / ، ( ; a pronoun in front and a trailing لَ off: her
    'متحمس لَ' is متحمس). A phrase row (مش زاكي) and a pattern row (أول + الـ + اسم) have none."""
    if "+" in str(arabic or ""):
        return []
    out = []
    for f in re.split(r"[/،,(]", str(arabic or "")):
        f = PRONOUNS.sub("", jsnorm(f.strip(" )")))
        f = re.sub(r"\s+(ل|لـ|ب|بـ|…|\.\.\.)$", "", f).strip(" ؟?.…")
        if f and " " not in f and len(core(f)) >= 2:
            out.append(f)                 # her spelling, el- kept: اليوم 'Today' is not يوم 'Day' (WS-34)
    return out


def in_phrase(w, doc):
    """Is this word one of the words of her phrase (مش of 'مش زاكي'), not just letters inside one (لا of '3لا3ة')?"""
    c = core(w)
    return any(core(x) == c or core(x).lstrip("و") == c for x in jsnorm(doc.get("arabic") or "").split())


AR_LAT = {"ء": "2", "أ": "2", "إ": "2", "ؤ": "2", "ئ": "2", "آ": "2", "ا": "A", "ى": "A", "ب": "b", "ت": "t", "ث": "t",
          "ج": "j", "ح": "7", "خ": "5", "د": "d", "ذ": "d", "ر": "r", "ز": "z", "س": "s", "ش": "S", "ص": "s", "ض": "d",
          "ط": "t", "ظ": "d", "ع": "3", "غ": "8", "ف": "f", "ق": "2", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h",
          "و": "w", "ي": "y", "ة": ""}


def _squeeze(s):
    return re.sub(r"(.)\1+", r"\1", s)


def skel_ar(w):
    """A word's sound skeleton in her letters (consonants and long vowels: نجوم -> njwm, حجار -> 7jAr), so an Arabic
    word can be compared with her Latin plural (Nujoom, 7jaar)."""
    n = jsnorm(w)
    if n[:1] in "اأإآ":
        n = n[1:]
    n = re.sub(r"[هة]$", "", n)
    return _squeeze("".join(AR_LAT.get(ch, "") for ch in n))


def skel_lat(w):
    """skel_ar for her Latin spelling: aa = A, oo / uu = w, ee / ii = y, short vowels dropped (Fasateen -> fsAtyn)."""
    s = re.sub(r"[^a-z0-9]", "", str(w or "").lower())
    s = s.replace("sh", "S").replace("kh", "5").replace("gh", "8").replace("th", "t").replace("dh", "d")
    s = s.replace("q", "2").replace("9", "s").replace("6", "t")
    s = re.sub(r"a{2,}", "A", s)
    s = re.sub(r"[ou]{2,}", "w", s)
    s = re.sub(r"[ei]{2,}", "y", s)
    s = re.sub(r"^[aeiou]", "", s)
    s = re.sub(r"h$", "", s)
    return _squeeze(re.sub(r"[aeiou]", "", s))


SOUND_FOLD = str.maketrans({"ذ": "د", "ث": "ت", "ظ": "ض"})
# WS-34: the engine's MSA spelling of her word: هذا is her هادا 'This (M)', هذه / هذي her هادي 'This (F)'
MSA = {"هذا": "هادا", "هذه": "هادي", "هذي": "هادي", "هاذا": "هادا", "هاذي": "هادي",
       "شاطئ": "شط", "الشاطئ": "الشط", "بالشاطئ": "بالشط"}   # WS-37: the engine's MSA شاطئ for his شط (her Sha66: 'You used شط')
MSA_MEANS = "This"                # her هادي is 'This (F)' and also 'Calm': the MSA spelling is always the 'this' one
OBJ_ENDS = ("هم", "كم", "ها", "نا", "ني", "ك", "ه", "ي")
PRONOUNS = re.compile(r"^(أنا|انا|إنت|انت|إنتي|انتي|هو|هي|إحنا|احنا|إنتو|انتو|هم)\s+")


HAMZA = str.maketrans({"ئ": "ي", "ء": "ي"})    # compare only: بطيء / بطيئ / بطيي


def jsnorm(s):
    """word-bank-core.js normalize(): NFKC, no marks, one alif."""
    import speaking_evidence as se
    return se.normalize(str(s or "")).strip(" .،,؟?!")


def _fem(c):
    return re.sub(r"[اهة]$", "", c) if len(c) >= 4 else c


def related(w, doc):
    """Is this word a form of the list word (the word itself, + el-, + an ending: راسها of راس)? A word of a longer list
    phrase is not (أنا of 'أنا بطبخ')."""
    n = core(w)
    for f in re.split(r"[/،,(]", str(doc.get("arabic") or "")):
        f = PRONOUNS.sub("", f.strip()).strip(" )؟?")
        if not f or " " in f:
            continue
        c = core(f)
        if c and (n == c or _fem(n) == _fem(c) or (len(c) >= 3 and n.startswith(c) and len(n) - len(c) <= 3)):
            return True
    # WS-34: her one-word row said a letter off or with an extra إ in front (بتلج of her بتتلج, ملان of مليان, إمبارح)
    n = n.translate(SOUND_FOLD).translate(HAMZA)
    for c in one_word_forms(doc.get("arabic")):
        c = core(c).translate(HAMZA)
        for x in (n, n[1:] if str(w or "").strip()[:1] in "اإ" and len(n) >= 4 else n):
            if min(len(x), len(c)) >= 4 and difflib.SequenceMatcher(None, x, c).ratio() >= 0.8:
                return "loose"
            # a three-letter row: only a long vowel added inside it (خلاص of her خلص), never a letter in front (أحيه)
            if len(c) == 3 and len(x) == 4 and any(x[:k] + x[k + 1:] == c and x[k] in "اوي" for k in range(1, 4)):
                return "loose"
    return False


def slip_on(detail, t0, t1, w):
    """A counted slip (grammar or word) on his line whose wrong part holds this word."""
    for g in (detail.get("grammar_errors") or []) + (detail.get("vocab_errors") or []):
        t = g.get("t")
        if t is not None and t0 - 2 <= float(t) <= t1 + 2 and any(similar(x, w) for x, cut in arabic_tokens(g.get("wrong") or g.get("said") or "")):
            return True
    return False


EXTRA = {k: v for k, v in ((J(os.path.join(REPO, "docs", "data", "arabizi-extra.json"), {}) or {}).get("words") or {}).items()
         if isinstance(v, dict)}


def lesson_events(events, date):
    return [e for e in events if e.get("lesson_date") == date and e.get("speaker") == "Medi"]


def event_on(evs, t0, t1, word, key):
    for e in evs:
        if t0 - 1.0 <= float(e.get("t_start") or -99) <= t1 + 1.0 and (
                (key and e.get("word_key") == key) or (e.get("text") and similar(e["text"].strip(" .،؟?!"), word))):
            return e
    return None


def fix_times_of(detail):
    """[(time of her fix, the right form the slip row gives)] of every counted slip."""
    return [(g["t_fix"], g.get("right") or g.get("fix")) for g in (detail.get("grammar_errors") or []) + (detail.get("vocab_errors") or [])
            if g.get("t_fix") is not None]


def preps():
    """The Word Bank's prepositions (word-bank-core.js PREPOSITIONS): grammar, never a vocabulary word."""
    try:
        s = open(os.path.join(REPO, "docs", "js", "word-bank-core.js"), encoding="utf-8").read()
        return set(re.findall(r"'([^']+)'", re.search(r"PREPOSITIONS=new Set\(\[(.*?)\]\)", s).group(1)))
    except (OSError, AttributeError):
        return set()


PHON = str.maketrans({"ط": "ت", "ث": "ت", "ص": "س", "ش": "س", "ض": "د", "ظ": "د", "ذ": "د", "ف": "ب", "ق": "ك", "ة": "ه"})


def recent_word(turns, i, w, keys, window=60.0):
    """WS-35: (key, 'one') when his word is, a letter off, a word of her list the tutor said in the minute before
    (10-08 31:34 الهاوا after her الهوا), else None. Only 4+ letter words, only one list word."""
    cw = core(w)
    if len(cw) < 4:
        return None
    for j in tutor_before(turns, i, window):
        for hw in her_words(turns, j):
            ch = core(hw)
            if len(ch) >= 4 and ch != cw and difflib.SequenceMatcher(None, ch, cw).ratio() >= 0.8:
                k, how = keys.lookup(hw)
                if how == "one":
                    return k, "one"
    return None


def said_back(turns, i, w, window=6.0):
    """WS-35: the time (mm:ss) of the tutor's short line right after his that says his word back ('أها، الإدام'), else
    None. Only a content word of 4+ letters (never لا, اللي, فيها), never a dish or name (WS-15), and her line is a short
    confirmation (3 Arabic words at most), not her own sentence that happens to use it."""
    import loanwords
    if len(core(w)) < 4 or core(w) in FUNCTION or norm(w) in FUNCTION or _loan(loanwords, w):
        return None
    end = float(turns[i].get("end") or turns[i]["t"])
    for u in turns[i + 1:i + 4]:
        if not _is_amal(u) or u.get("who") == "chat" or float(u["t"]) - end > window:
            continue
        hers = [x for x, cut in arabic_tokens(u.get("text")) if not cut]
        if len(hers) <= 3 and any(core(x) == core(w) for x in hers):
            return mmss(u["t"])
    return None


def _verb_stem(w):
    """WS-35: a verb's stem without its person / tense pieces (بدير, ديرت, ديري -> دير; بمطر, مطرت -> مطر)."""
    n = core(w)
    n = re.sub(r"^(?:بي|بت|بن|ب|ي|ت|ن|ا)(?=\S{3})", "", n)
    return re.sub(r"(?<=\S{3})(?:تي|تو|نا|وا|ت|و|ي|ه|ها)$", "", n)


def taught_match(a, w, ta=None, tw=None, loose=True, sounds=False):
    """Is his word w the taught word a? The word itself, + an ending, one letter off in a 4+ letter word; and (WS-35)
    another form of the verb she taught (ديرت of her بدير), the same word with letters the engine swaps by sound (ختيفتي
    of her خطيبتي), a long vowel added inside a three-letter word (حجور of her حجر), or - when he says it within 90 s of
    her teaching it (ta, tw in seconds) - the same word with one letter off (سجر for her فجر)."""
    ca, cw = core(a), core(w)
    if not ca or not cw:
        return False
    if ca == cw or (len(ca) >= 3 and cw.startswith(ca) and len(cw) - len(ca) <= 3):
        return True
    if min(len(ca), len(cw)) >= 4 and difflib.SequenceMatcher(None, ca, cw).ratio() >= 0.8:
        return True
    if not loose:                         # a word found on her list keeps its list match (50:27 حجار = her 7ajar)
        return False
    sa, sw = _verb_stem(a), _verb_stem(w)
    if len(sa) >= 3 and sa == sw:
        return True
    fa, fw = ca.translate(PHON), cw.translate(PHON)
    if min(len(fa), len(fw)) >= 4 and (fa == fw or difflib.SequenceMatcher(None, fa, fw).ratio() >= 0.85):
        return True
    if len(ca) == 3 and len(cw) == 4 and any(cw[:k] + cw[k + 1:] == ca and cw[k] in "اوي" for k in range(1, 3)):
        return True
    if ta is not None and tw is not None and abs(tw - ta) <= 90 and len(ca) == len(cw) >= 3 and sum(x != y for x, y in zip(ca, cw)) == 1:
        return True
    if sounds and ta is not None and tw is not None and abs(tw - ta) <= 120 and min(len(ca), len(cw)) >= 3:
        # WS-37: his sounds, right after she taught it - ع and long vowels dropped, ق / غ / ك one sound (نانا for her
        # نعنع, 10-09 04:20; قبه for her غابة, 27:10)
        sk = lambda x: re.sub(r"[اعءأإآىةه]", "", x).translate(str.maketrans("قغ", "كك"))
        if len(sk(ca)) >= 2 and sk(ca) == sk(cw):
            return True
    return False


def _sec(t):
    try:
        return sum(float(x) * 60 ** k for k, x in enumerate(reversed(str(t).split(":"))))
    except ValueError:
        return None


def taught_today(date, repo=REPO):
    """[(arabic, mm:ss)] the tutor taught in this lesson (the same-day reader's taught_words, LS-08)."""
    d = J(os.path.join(repo, "data", "lesson-work", "lesson-types", date + ".json"), {}) or {}
    out = []
    for w in d.get("taught_words") or []:
        if isinstance(w, dict) and w.get("arabic"):
            for a in re.split(r"\s*/\s*", w["arabic"]):
                for x in a.split():          # a taught phrase: each of its own words (not على, في ...)
                    if len(core(x)) >= 3 and core(x) not in FUNCTION:
                        out.append((x, w.get("t") or ""))
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
    keys.sound = date >= AGAIN_FROM       # WS-37: his sounds (10-08 and 10-09 only, Medi 2026-10-10)
    sup = supplies(turns, fix_times_of(detail), date)
    evs = lesson_events(events, date)
    anchor = next((e for e in sorted(evs, key=lambda e: e.get("t_start") or 0)), None)
    adds, patches, rows = [], {}, []
    mine = his_rulings(date, rulings)
    PREP = preps()
    taught = taught_today(date)
    fresh_today = {}                      # WS-35: core -> why, the words already ★ new in this lesson
    try:                                  # her Meet chat of this lesson (lesson_turns.chat_lines)
        import lesson_turns
        chat = [c["text"] for c in lesson_turns.chat_lines(date) if c.get("speaker") == "Amal"]
    except Exception:  # noqa: BLE001
        chat = []
    chat_words = {x.lower().strip("'’.,?!") for c in chat for x in c.split()}
    for i, u in enumerate(turns):
        if u.get("who") != "Medi":
            continue
        t0, t1 = float(u["t"]), float(u.get("end") or u["t"])
        if any(a <= t0 <= b for a, b in off):
            for w, cut in arabic_tokens(u.get("text")):
                rows.append({"i": i, "t": t0, "word": w, "state": "na", "why": "off-lesson"})
            continue
        toks = word_tokens(u.get("text"))
        covered = {}                      # WS-34: token index -> the phrase of hers he said whole that holds it
        start = len(rows)
        for n, tk in enumerate(toks):
            w, cut, shown = tk["ar"], tk["cut"], tk["shown"]
            row = {"i": i, "t": t0, "word": w, **({"shown": shown} if shown != w else {})}
            if cut:
                rows.append(dict(row, state="na", why="broken off before the end of the word (not a try)"))
                continue
            if n in covered:
                rows.append(dict(row, state="na", covered=True, key=covered[n],
                                 why="part of her phrase %s, which he said whole (judged once, as that phrase)" % covered[n]))
                continue
            key, how = keys.lookup(w)
            if date >= AGAIN_FROM and how != "one" and norm(w) in {norm(x) for x in LI_FORMS}:
                rows.append(dict(row, state="na", grammar=True, why="a preposition: scored as grammar, not as a word"))
                continue
            if how == "unclear" and "mara~time" in key:
                key, how = ("mara" if re.search(r"مرت|زوج|wife|woman", u.get("text") or "") else "mara~time"), "one"
            if how == "unclear" and "8air" in key and core(w) == "غير":
                prv = norm(toks[n - 1]["ar"]) if n > 0 else ""
                verbish = prv in PRONOUN_WORDS or prv in ("لازم", "بدي", "رح", "راح", "ما", "بدك")
                key, how = (next((k for k in key if k != "8air"), key[0]) if verbish else "8air"), "one"   # WS-35
            if how == "unclear" and date >= AGAIN_FROM and set(key) == {"hAdi", "hadi"}:
                # WS-37: هادي is her 'This (F)' (hadi); 'Calm' (hAdi) only on a line about calm / quiet
                key, how = ("hAdi" if re.search(r"calm|quiet|relax", u.get("text") or "", re.I) else "hadi"), "one"
            if how == "unclear" and date >= AGAIN_FROM and set(key) == {"nafas", "nafs"}:
                # WS-37: نفس before a word is her 'Same' (nafs); 'Breath' (nafas) only with خد / take a breath
                key, how = ("nafas" if re.search(r"خد|خذ|breath", u.get("text") or "") else "nafs"), "one"
            if how == "unclear" and date >= AGAIN_FROM and set(key) == {"ana barawe7", "ana baru7"}:
                # WS-37: روح is her 'I go' (baru7); 'I go home' (barawe7) only with البيت / home on the line
                key, how = ("ana barawe7" if re.search(r"بيت|home", u.get("text") or "") else "ana baru7"), "one"
            if how == "unclear" and set(key) == {"ra7", "rA7"}:
                nxt = toks[n + 1]["ar"] if n + 1 < len(toks) else next_his_word(turns, i) if date >= AGAIN_FROM else ""   # WS-36: 15:30 أنا راح، / 15:33 أعمله
                key, how = ("ra7" if re.match(r"[اأنتيب]\S{2,}", norm(nxt) or "") and norm(nxt) not in FUNCTION else "rA7"), "one"
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
            via = keys.via if how == "one" else None
            new = next((t_ for a, t_ in taught if taught_match(a, w, _sec(t_), t0, loose=how != "one", sounds=date >= AGAIN_FROM)), None)
            if new is None and how == "none" and core(w) in fresh_today:
                new = fresh_today[core(w)]        # the same new word again later in the lesson (51:22 الإدام)
            lat = (EXTRA.get(w) or EXTRA.get(norm(w)) or {}).get("latin")
            typed = "she typed '%s' in the chat" % lat if lat and lat.lower() in chat_words else None
            if new is None and how in ("none", "sheet", "part"):
                new = typed
            fresh = new or typed          # a form the Word Bank cannot place that she taught / typed today stays ★ new
            if how == "part" and new is None:
                span = phrase_span(toks, n, (keys.words.get(key) or {}).get("arabic"), u.get("text"))
                if span:                  # he said her whole phrase (لو سمحت): the phrase is the word
                    for x in range(n + 1, n + len(span[1])):
                        covered[x] = key
                    shown, how = span[0], "one"
                    row["shown"] = shown
            if how == "part" and new is None:
                d_ = keys.words.get(key) or {}
                rows.append(dict(row, state="na", why="not on her list by itself: she has it only inside her phrase %s '%s' (%s), "
                                 "so it is left out of the Words %%" % (d_.get("arabic") or key, d_.get("english") or "", key)))
                continue
            if how == "none" and new is None:
                near = recent_word(turns, i, w, keys)
                if near:
                    key, how = near
                else:
                    back = said_back(turns, i, w)
                    if back:
                        new = "she said it back to you at %s" % back
            if (how in ("none", "sheet", "part") or via) and new is not None:
                fresh_today.setdefault(core(w), new)
                rows.append(dict(row, state="new", key=key, why=("new word: not on her list, and %s; not scored" % new) if new.startswith("she said")
                                 else "new word: the tutor taught it in this lesson (%s); not on her list yet, not scored" % new))
                continue
            if how in ("none", "sheet") and norm(w) in LI_FORMS and new is None:
                rows.append(dict(row, state="na", grammar=True, why="a preposition: scored as grammar, not as a word"))
                continue
            if how in ("none", "sheet"):
                import loanwords
                why = ("a name, dish or loan word (never on her list)" if _loan(loanwords, w) or (date >= AGAIN_FROM and _place(loanwords, w))
                       else "a word the tutor taught that is not in the saved copy of her list yet" if how == "sheet"
                       else "not on her word list (left out of the Words %; it goes to her new-words list)")
                rows.append(dict(row, state="na", why=why, key=key))
                continue
            row["key"] = key
            if key in PREP:
                rows.append(dict(row, state="na", grammar=True, why="a preposition: scored as grammar, not as a word"))
                continue
            e = event_on(evs, t0, t1, w, key) or (event_on(evs, t0, t1, w, None) if key == "mara~time" else None)
            if e is not None and key == "mara~time" and e.get("word_key") in ("mura", "mara", "mur") and not ledger_ids() & {e.get("id")}:
                exp = {k: e.get(k) for k in ["source_sha256", "row_id", "word_key", "text", "t_start", "t_end", "assessment", "reason"]}
                patches[e["id"]] = {"expected": exp, "changes": {"word_key": "mara~time", "candidate_keys": sorted(set((e.get("candidate_keys") or []) + ["mara~time"])),
                                                                  "reason": "مرة here is her 'one time' row (Marra), not 'bitter' or 'woman' (WS-33)", "by": BY, "rule": "WS-33"}}
                row.update(key=key, event=e["id"], patched="key")
                rows.append(row)
                continue
            if e is not None and e.get("text") and core(e["text"].strip(" .،,؟?!")) != core(w) and any(
                    x is not tk and similar(x["ar"], e["text"].strip(" .،,؟?!")) for x in toks):
                e = None                  # WS-34: that event is another word of this line (حجرات before his حجار, 10-08 50:27)
            if e is not None and e.get("text") and core(e["text"].strip(" .،,؟?!")) != core(w) and date >= AGAIN_FROM and any(
                    h.get("correction") and core(w) in [core(x) for x, c_ in arabic_tokens(h.get("heard"))] for h in u.get("heard") or []):
                e = None                  # WS-29: HIS own fix put this word on the line (20:05 اليوم -> غيوم): judged as said
            if e is not None and date >= AGAIN_FROM and e.get("word_key") == key and re.search(r"[A-Za-z]", e.get("text") or ""):
                pass                      # WS-37: the second listen wrote his Latin 'Marhaba' as مرحبا - the same word of hers
            elif e is not None and e.get("text") and core(e["text"].strip(" .،,؟?!")) != core(w) and not re.search(r"[A-Za-z]", w):
                # the second listen changed this word (engine فاتح -> heard فاتحة): the tutor's listen decides it (TR-27),
                # never this file
                rows.append(dict(row, state="na", why="the second listen changed this word; the tutor's listen decides it (TR-27)"))
                continue
            if e is not None and e.get("word_key") != key:
                e = None                  # the matcher's event names no list word (two candidates): it scores nothing, so this word gets its own
            state, why, j = judge_word(turns, i, w, key, keys.of, sup, keys.is_plural, strict=date >= AGAIN_FROM)
            qj = quotes_her(turns, i) if date >= AGAIN_FROM and state != "repeat" else None
            if qj is not None and any(similar(x, w) or core(x) == core(w) for x in her_words(turns, qj, sup)):
                state, why, j = "repeat", ("He quotes the tutor's words (%s «%s») to ask about them: a repeat, not credited, "
                                           "not a mistake (WS-36)" % (mmss(turns[qj]["t"]), (turns[qj].get("text") or "")[:80])), qj
            if state == "unresolved" and not slip_on(detail, t0, t1, w):
                state, why = "independent", ("Word he said on his own: the tutor's 'no' right after was not about it - the three "
                                             "readers wrote no slip on it (WS-30)")
            if e is not None:
                row["event"] = e["id"]
                ent = keys.entry(key, e.get("text") or w)
                if ent is None and state != "repeat":
                    rows.append(dict(row, state="new", key=key, why="new word: the tutor taught it in this lesson (%s); not on her list yet, not scored" % fresh)
                                if fresh else dict(row, state="na", why="a form of %s the Word Bank does not list yet (it cannot place this one)" % key))
                    continue
                p = _patch(e, state, why, turns, j)
                if p and ent:
                    p["changes"]["entry_id"] = ent
                if p:
                    patches[e["id"]] = p
                    row["patched"] = state
                rows.append(row)
                continue
            if anchor is None:
                rows.append(dict(row, state="na", why="no Word Bank evidence for this lesson yet"))
                continue
            if t0 - (float(anchor.get("t_start") or 0) - float(anchor.get("local_start") or 0)) < 0:
                rows.append(dict(row, state="na", why="said before his own recording starts (no clip of his voice)"))
                continue
            entry = keys.entry(key, w)
            if not re.search(r"(?<!\w)%s(?!\w)" % re.escape(shown), u.get("text") or ""):
                rows.append(dict(row, state="na", why="read from the line's letters but not written as one word there (left to the readers)"))
                continue
            if entry is None:
                rows.append(dict(row, state="new", key=key, why="new word: the tutor taught it in this lesson (%s); not on her list yet, not scored" % fresh)
                            if fresh else dict(row, state="na", why="a form of %s the Word Bank does not list yet (it cannot place this one)" % key))
                continue
            ev = _event(date, anchor, u, i, n, shown, key, state, why, turns, j)
            if entry:
                ev["entry_id"] = entry
            adds.append({"anchor_id": anchor["id"], "expected_source": anchor.get("source_sha256"), "event": ev, "by": BY})
            evs.append(ev)
            row["event"] = ev["id"]
            row["added"] = state
            rows.append(row)
        for r in rows[start:]:            # a phrase that got no mark (said before his recording ...): its words say why
            head = next((h for h in rows[start:] if not h.get("covered") and h.get("key") == r.get("key")), None) if r.get("covered") else None
            if head is not None and head.get("state") == "na":
                r.pop("covered")
                r["why"] = head["why"]
    if date >= AGAIN_FROM:
        said_again(date, turns, rows, adds, patches, evs)
        quoted_events(turns, evs, keys, patches, rows)
    return adds, patches, rows


AGAIN_FROM = "2026-10-08"     # WS-36: Medi chose 10-08 and 10-09 only (2026-10-10); earlier lessons wait for his yes
LI_FORMS = {"لي", "لك", "لكي", "له", "لها", "لنا", "لكم", "لهم",   # PG-43: a preposition + a pronoun ending is a preposition
            "فيهم", "فيها", "فيك", "فيكي", "فيكم", "فينا", "فيي", "عليها", "عليه", "عليك", "عليكي", "منها", "منه", "منك",
            "منكم", "عنها", "عنه", "عنك", "معي", "معك", "معكي", "معه", "معها", "معهم", "الي", "إلي", "إلك", "الك", "إله", "اله"}
TUTOR_NOD = re.compile(r"^(?:\W*(?:m+|m+-?hm+|mhm+|uh-huh|مهم|ممم|مم)\W*)+$", re.I)    # her nod, not a word


def quotes_her(turns, i, window=20.0):
    """WS-36 (Medi 2026-10-09 on 10-08 59:29 'these are all repeats', 59:44 'all repeates'): his line is an English question
    about her words ('so it is il mufaddal, but why is it il here?' after her 'هاد الدرس المفضل عندي') - 4+ English words and
    a '?' - and quotes her line of the 20 s before: that line's index, else None. Her words in it are hers, not his uses."""
    mine = [w for w, cut in arabic_tokens(turns[i].get("text")) if not cut]
    for j in question_about(turns, i, window):
        hers = {core(w) for w in her_words(turns, j)}
        if any(core(w) in hers for w in mine):
            return j
    return None


def question_about(turns, i, window=20.0):
    """The tutor's lines of the 20 s before when his line i is an English question (4+ English words and a '?'), else []."""
    text = turns[i].get("text") or ""
    if "?" not in text and "؟" not in text:
        return []
    english = [x for x in re.findall(r"[A-Za-z']+", text) if x.lower() not in LATIN_AR and not re.search(r"\d", x)]
    return tutor_before(turns, i, window) if len(english) >= 4 else []


def quoted_events(turns, evs, keys, patches, rows):
    """WS-36: the Word Bank's own events on his English question lines (his Latin il mufaddal the matcher read) whose word
    is a word of her line he asks about: a repeat, like the words this file judges (10-08 59:29, 59:39, 59:47)."""
    for i, u in enumerate(turns):
        if u.get("who") != "Medi":
            continue
        js = question_about(turns, i)
        if not js:
            continue
        hers, word = {}, {}
        for j in js:
            for w in her_words(turns, j):
                k, how = keys.lookup(w)
                if how == "one" and isinstance(k, str):
                    hers.setdefault(k, j)
                    word.setdefault(k, w)
        t0, t1 = float(u["t"]) - 0.3, float(u.get("end") or u["t"]) + 0.3
        for e in evs:
            if e.get("speaker") != "Medi" or e.get("word_key") not in hers or e["id"] in patches or e.get("repeat") or e.get("coverage"):
                continue
            ts = float(e.get("t_start") or -1)
            if not (t0 <= ts <= t1):
                continue
            j = hers[e["word_key"]]
            why = "He quotes the tutor's words (%s «%s») to ask about them: a repeat, not credited, not a mistake (WS-36)" % (
                mmss(turns[j]["t"]), (turns[j].get("text") or "")[:80])
            if e.get("review_locked") or e.get("medi_ruling") or e.get("id") in ledger_ids() or e.get("assessment") in ("incorrect", "recall_failure"):
                continue
            exp = {k: e.get(k) for k in ["source_sha256", "row_id", "word_key", "text", "t_start", "t_end", "assessment", "reason"]}
            patches[e["id"]] = {"expected": exp, "changes": {"assessment": "helped", "reason": why, "by": BY, "rule": "WS-36",
                                                              **_repeat_fields(turns, j)}}
            if not any(r["i"] == i and r.get("key") == e["word_key"] for r in rows):     # its ↻ chip on the line
                rows.append({"i": i, "t": float(u["t"]), "word": word[e["word_key"]], "key": e["word_key"], "event": e["id"], "patched": "repeat"})


LATIN_AR = {"il", "el", "al", "dars", "mufaddal", "ahada", "hada", "hadi"}   # his Arabizi in an English line is not English


def next_his_word(turns, i, window=8.0):
    """WS-36: the first Arabic word of his next line within 8 s, when nobody else spoke in between (his line that ends on
    راح goes on in the next one: 10-08 15:30 'أنا راح،' / 15:33 'أعمله،' is ra7 'will')."""
    t1 = float(turns[i].get("end") or turns[i]["t"])
    for u in turns[i + 1:]:
        if float(u["t"]) - t1 > window:
            return ""
        if u.get("who") != "Medi":
            if TUTOR_NOD.match(u.get("text") or ""):
                continue
            return ""
        toks = [x for x in word_tokens(u.get("text")) if not x["cut"] and not is_pronoun(x["ar"]) and norm(x["ar"]) not in ("راح", "رح")]
        if toks:
            return toks[0]["ar"]
    return ""


def said_again(date, turns, rows, adds, patches, evs, window=10.0):
    """WS-36 (Medi 2026-10-09 on 10-08 22:01 "dont double count 2amar", 47:07 "dont double count"): the same list word of
    his on two lines in a row - nothing from the tutor between but a nod (Mm, Mm-hmm, Yeah) and at most 10 s apart - is
    ONE try: the first keeps its mark, the second is 'said again', not counted (10-08 22:03 قمر / 22:05 القمر, 47:07 /
    47:09 شجر). A repeat of her word stays a repeat; a mark a person gave (a reader, Amal, a review) is never changed."""
    by_ev = {e["id"]: e for e in evs}
    add_by = {a["event"]["id"]: a["event"] for a in adds}
    credited = {}
    for r in rows:
        if r.get("event") and r.get("key") and r.get("state") not in ("na", "new") and "repeat" not in (r.get("added"), r.get("patched")):
            credited.setdefault(r["i"], []).append(r)
    prev = None
    for i, u in enumerate(turns):
        if u.get("who") != "Medi":
            if not TUTOR_NOD.match(u.get("text") or ""):
                prev = None
            continue
        if prev is not None and i not in credited and not [x for x in word_tokens(u.get("text")) if not x["cut"]]:
            continue                      # his filler line (آآآم.) between two tries does not break them apart
        if prev is not None and float(u["t"]) - float(turns[prev].get("end") or turns[prev]["t"]) <= window:
            before = {r["key"]: r for r in credited.get(prev, [])}
            for r in credited.get(i, []):
                b = before.get(r["key"])
                # the same word, not another form of it (38:43 غيوم then 38:46 غيم are two tries: plural, singular)
                if b is None or core(b["word"]) != core(r["word"]):
                    continue
                why = "said again right after his own %s at %s with nothing from the tutor between: one try, counted once (WS-36)" % (
                    before[r["key"]]["word"], mmss(turns[prev]["t"]))
                ev = add_by.get(r["event"])
                if ev is not None:
                    ev.update(assessment="unresolved", vocab_points=None, ignored=True, classification="ignored", reason=why, rule="WS-36",
                              audit_bin="not_counted", audit_kind="repeat")
                    r["added"] = "again"
                    continue
                e = by_ev.get(r["event"])
                if e is None or e.get("review_locked") or e.get("medi_ruling") or e.get("id") in ledger_ids():
                    continue
                exp = {k: e.get(k) for k in ["source_sha256", "row_id", "word_key", "text", "t_start", "t_end", "assessment", "reason"]}
                patches[e["id"]] = {"expected": exp, "changes": {"assessment": "unresolved", "vocab_points": None, "ignored": True,
                                                                  "classification": "ignored", "reason": why, "by": BY, "rule": "WS-36",
                                                                  "audit_bin": "not_counted", "audit_kind": "repeat"}}
                r["patched"] = "again"
        prev = i


PLACES_EXTRA = {"كاليفورنيا", "تكساس", "نيويورك", "فلوريدا"}   # US states the place list (Wikidata countries / cities) lacks


def _place(loanwords, w):
    """WS-37: a country, city or place name (scripts/names.py; 10-09 11:13 إيران, 52:16 أمريكا, 19:44 كاليفورنيا) is a name,
    not 'not on her word list'."""
    if jsnorm(w) in {jsnorm(x) for x in PLACES_EXTRA}:
        return True
    try:
        sp = loanwords._place_spans(w)
    except Exception:  # noqa: BLE001
        return False
    return any(s_ == 0 and e_ >= len(w.strip(" .،,؟?!")) for s_, e_ in sp)


def _loan(loanwords, w):
    try:
        return bool(loanwords.loan_token(w))
    except Exception:  # noqa: BLE001 - a lookup hiccup is 'not a loan word'
        return False


def _repeat_fields(turns, j):
    return {"immediate_repeat": True, "repeat": True,
            **({"repeat_of": {"t": float(turns[j]["t"]), "text": (turns[j].get("text") or "")[:120]}} if j is not None else {})}


LEDGER_IDS = None


def ledger_ids():
    """Word Bank events the lesson ledger already ruled on (docs/data/word-bank-audit-slips.json overrides, LS-11)."""
    global LEDGER_IDS
    if LEDGER_IDS is None:
        d = J(os.path.join(REPO, "docs", "data", "word-bank-audit-slips.json"), {}) or {}
        LEDGER_IDS = {o.get("event_id") for o in d.get("overrides") or []}
    return LEDGER_IDS


def _patch(e, state, why, turns, j):
    """A patch on a Word Bank event the engine words made: a repeat of her fix loses its credit (WS-31); a word said alone
    that sat 'unresolved' is judged (WS-30). Nothing else is touched (a reader's or Amal's ruling stays)."""
    if e.get("review_locked") or e.get("medi_ruling") or e.get("grammar_only") or e.get("assessment") in ("incorrect", "recall_failure")             or e.get("id") in ledger_ids():
        return None
    exp = {k: e.get(k) for k in ["source_sha256", "row_id", "word_key", "text", "t_start", "t_end", "assessment", "reason"]}
    if state == "repeat":
        ch = {"assessment": "helped", "reason": why, "by": BY, "rule": "WS-31", **_repeat_fields(turns, j)}
    elif e.get("assessment") == "unresolved" and state in ("independent", "helped"):
        ch = {"assessment": state, "reason": why + " (WS-30)", "by": BY, "rule": "WS-30", "classification": "lexical",
              "vocab_points": {"independent": 1, "helped": 0.5}[state]}
    else:
        return None
    return {"expected": exp, "changes": ch}


def _event(date, a, u, i, n, w, key, state, why, turns, j):
    off = float(a.get("t_start") or 0) - float(a.get("local_start") or 0)
    t0 = float(u["t"])
    t1 = max(t0 + 0.3, float(u.get("end") or u["t"]))
    rid = "cover:%s:%s" % (date, round(t0, 2))
    ev = {"id": sha([BY, date, round(t0, 2), n, key, w]), "lesson_date": date, "word_key": key,
          "local_start": round(t0 - off, 3), "local_end": round(t1 - off, 3), "candidate_keys": [key],
          "source_id": a.get("source_id"), "source_sha256": a.get("source_sha256"), "row_id": rid, "item_ids": [],
          # whole seconds stay whole, as JS writes them (the ledger compares them as text)
          "t_start": int(t0) if t0.is_integer() else t0, "t_end": int(t1) if float(t1).is_integer() else t1, "speaker": "Medi", "speaker_basis": a.get("speaker_basis"), "text": w,
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
    # an older patch that only left the word an open question (the 2026-09-28 audit: audit_created, no verdict) gives way
    # to a judgment; its note is kept on the new patch (replaced_audit)
    def _open(x):
        ch = (x or {}).get("changes") or {}
        return ch.get("audit_created") and ch.get("assessment") in (None, "unresolved")
    for k, v in pats.items():
        if k in P and _open(P[k]):
            v["changes"]["replaced_audit"] = P[k]["changes"]
    pats = {k: v for k, v in pats.items() if k not in P or (P[k].get("changes") or {}).get("by") == BY or _open(P[k])}
    if [x for x in review.get("additions") or [] if x.get("by") == BY] != adds or old != pats:
        for k in old:
            ra = (P[k].get("changes") or {}).get("replaced_audit")
            P.pop(k, None)
            if ra and k not in pats:                      # put the open question back when this file no longer judges it
                P[k] = {"expected": old[k]["expected"], "changes": ra}
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
    by_lesson = {}
    for c in clips.values():
        by_lesson.setdefault(c.get("lesson"), []).append(c)
    for a in review.get("additions") or []:
        e = a.get("event") or {}
        if e.get("speaker") != "Medi" or a.get("by") not in (BY, "heard-credit"):
            continue
        have = clips.get(e.get("id"))
        if have and have.get("start", 1e9) <= e["t_start"] and have.get("end", -1) >= e["t_end"]:
            continue                      # its clip still holds it
        date = e["lesson_date"]
        src = os.path.join(REPO, "docs", "lessons", date, "audio", "lesson.mp3")
        ctx = e.get("context") or []
        lo = min([e["t_start"]] + [r["timeline_start"] for r in ctx if isinstance(r.get("timeline_start"), (int, float))])
        hi = max([e["t_end"]] + [r["timeline_end"] for r in ctx if isinstance(r.get("timeline_end"), (int, float))])
        # a clip already cut for this lesson that holds the whole line is reused (no new file: 10-08's clips are 50 MB)
        old = next((c for c in sorted(by_lesson.get(date, []), key=lambda c: c["end"] - c["start"])
                    if c.get("source_sha256") == e.get("source_sha256") and c["start"] <= lo and c["end"] >= hi
                    and os.path.exists(os.path.join(REPO, "docs", c["sentence_audio_url"]))), None)
        if old:
            clips[e["id"]] = dict(old, event_id=e["id"], cut_by=BY, reused=True)
            changed = True
            continue
        start = max(0, math.floor(min([e["t_start"]] + [r["timeline_start"] for r in ctx if isinstance(r.get("timeline_start"), (int, float))]) - 1))
        end = math.ceil(max([e["t_end"]] + [r["timeline_end"] for r in ctx if isinstance(r.get("timeline_end"), (int, float))]) + 1)
        name = "context-" + hashlib.sha256(str((date, start, end)).encode()).hexdigest()[:16] + ".mp3"
        url = "lessons/%s/clips/%s" % (date, name)
        out = os.path.join(REPO, "docs", url)
        tracks = [os.path.join(REPO, "docs", "lessons", date, "audio", x + ".mp3") for x in ("Amal", "Medi")]
        two = not os.path.exists(src) and all(os.path.exists(t) for t in tracks)     # 09-10: one file per speaker
        if not os.path.exists(out):
            if not (os.path.exists(src) or two) or not (ffmpeg or cut):
                log("word_coverage: no clip for %s %s (no lesson audio or no ffmpeg)" % (date, e.get("text")))
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if cut:
                cut(src, start, end, out)
            elif two:
                subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-t", str(end - start), "-i", tracks[0],
                                "-ss", str(start), "-t", str(end - start), "-i", tracks[1], "-filter_complex", "amix=inputs=2:duration=longest:normalize=0",
                                "-ar", "16000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "48k", out], check=True, capture_output=True)
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
def _covers(c, r, line=()):
    """Does the vocab chip c already judge his word r? A chip that names the word he said (tok) does not judge ANOTHER
    word of the same line: on 10-08 50:27 the ✓ on حجار (her حجر, key 7ajar) is not the judgment of his حجور or حجرات
    before it (WS-34). line = the cores of the line's words."""
    toks = {core(x) for x in str(c.get("tok") or "").split()} & set(line)
    if c.get("k") == "vocab" and c.get("s") != "wrong" and toks and core(r["word"]) not in toks:
        return False
    return bool((r.get("key") and c.get("key") == r.get("key")) or similar(c.get("ar") or "", r["word"]) or similar(c.get("tok") or "", r["word"])
                or jsnorm(c.get("ar") or "") == jsnorm(re.sub("ه$", "و", r["word"]))
                or any(similar(x, r["word"]) for x in re.split(r"[\s،,.؟?/]+", str(c.get("ar") or "")) if x)
                or (c.get("s") == "wrong" and any(similar(x, r["word"]) for x in re.split(r"[\s،,.؟?]+", str(c.get("said") or "")) if x)))


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
        if any(_covers(c, r, [core(x) for x, cut in arabic_tokens(detail["turns"][i].get("text"))]) for c in mine):
            continue
        e = by_id.get(r.get("event"))
        if r.get("covered"):
            continue
        if r.get("state") == "new":
            out.append((i, {"k": "vocab", "s": "new", "ar": r["word"], "why": r["why"], "rule": "WS-18"}))
        elif r.get("state") == "na":
            out.append((i, {"k": "na", "s": "na", "label": "vocab", "w": None, "ar": r["word"], "why": r["word"] + ": " + r["why"], "rule": "WS-30",
                            **({"grammar_word": True} if r.get("grammar") else {}),
                            **({"quiet": QUIET[r["why"]], "hide": "quiet"} if r["why"] in QUIET else {})}))
        elif (e and e.get("repeat")) or r.get("added") == "repeat" or r.get("patched") == "repeat":
            rep = (e or {}).get("repeat_of") or {}
            out.append((i, {"k": "vocab", "s": "repeat", "ar": r["word"], "key": r.get("key"),
                            "why": (e or {}).get("reason") or "repeat of the tutor's word: not credited, not a mistake (WS-31)",
                            **({"amal_t": rep.get("t"), "amal_line": rep.get("text")} if rep else {}), "rule": "WS-31",
                            **({"src": "wb:" + r["event"]} if r.get("event") else {})}))
        elif e:
            # the Word Bank's own verdict on this event when it has one ('Said here · another word intended': 10-08 36:16
            # سنان when he meant her سنين) - never this file's 'said on his own' reason under a verdict that scores nothing
            oc = e.get("outcome") if e.get("outcome") not in (None, "Ignored pending review", "Not scored") else None
            out.append((i, {"k": "na", "s": "na", "label": "vocab", "ar": r["word"], "key": r.get("key"),
                            "why": r["word"] + ": " + (oc or e.get("reason") or "not scored"), "rule": "WS-30",
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
        cs = [c for c in (tm.get(str(i)) or {}).get("c", []) if c.get("k") in ("vocab", "grammar") or (c.get("k") == "na" and c.get("label") in ("vocab", "lesson"))]
        cs = [c for c in cs if not c.get("hide")] + [c for c in cs if c.get("hide")]     # the chip he sees first
        line = [core(x) for x, cut in arabic_tokens(u.get("text"))]
        for w, cut in arabic_tokens(u.get("text")):
            hit = next((c for c in cs if (c.get("why") or "").startswith(w + ":")), None) or next(
                (c for c in cs if c.get("tok") and jsnorm(c["tok"]) == jsnorm(w)), None) or next(   # WS-37: the word he said
                (c for c in cs if c.get("k") == "vocab" and w not in (u.get("text") or "") and any(                       # her
                    similar(x, MSA.get(jsnorm(w), w)) or similar(x, w)
                 for x in re.split(r"\s*/\s*", str(c.get("ar") or "")) if x)), None) or next(     # 'هادا / هادي' row
                (c for c in cs if _covers(c, {"word": w}, line) and (
                    similar(c.get("ar") or "", w) or jsnorm(c.get("ar") or "") == jsnorm(re.sub("ه$", "و", w)) or (c.get("k") == "vocab" and any(similar(x, w) for x in str(c.get("ar") or "").split()))
                    or any(similar(x["ar"] or "", w) for x in c.get("words") or [] if x.get("ar")))), None) or next(
                (c for c in cs if any(similar(x, w) for x in re.split(r"[\s،,.؟?]+", str(c.get("said") or "")) if x)), None)
            if hit is None and cs and any(c.get("label") == "lesson" for c in cs):
                hit = cs[0]
            voc = [c for c in cs if c.get("k") == "vocab"]
            if hit is None and w not in (u.get("text") or "") and len(voc) == 1:
                hit = voc[0]              # his Latin word the reader read (57:42 'kan'): the line's one word chip
            out.append({"t": mmss(u["t"]), "word": w, "cut": cut, "state": (hit or {}).get("s"), "why": (hit or {}).get("why"),
                        "quiet": (hit or {}).get("quiet")})
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 3 and sys.argv[1] == "report":
        rows = report(sys.argv[2])
        from collections import Counter
        for r in rows:
            print(r["t"], r["word"], r["state"] or "-- NO MARK --", (r["why"] or "")[:90])
        print(Counter(r["state"] or "none" for r in rows))
