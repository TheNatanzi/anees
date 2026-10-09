# -*- coding: utf-8 -*-
"""Count every time Medi USES a grammar rule, not just the times he got it wrong.

The audit only finds Amal's corrections, so a rule he uses correctly in every
lesson - the date, the clock, a b-verb - would score zero and show Untested.
This walks his own Arabic and marks each bucket where it fires.

Verbs are recognised from Amal's own vocabulary Doc (docs/data/words.json):
836 past-tense forms, 108 commands and 145 present verbs. A word counts as a
past verb only if it is one of HER past forms - not because it ends in ت.

Every use keeps the word(s) that triggered it ("hit"), so any count on the
page can be answered with "where?".

Output: docs/data/grammar-usage.json
"""
import json, os, re, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lesson_turns import page_lines  # noqa: E402  (2026-10-05: the counter reads the lines the pages show)
from arabizi_reader import to_arabic  # noqa: E402  (2026-10-01: Latin-letter turns are read too)

ANEES = r"C:\dev\anees\data\lessons"
# 2026-09-29: always this checkout's docs, so a worktree never writes into the live hourly checkout (see 278753d)
DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
OUT = os.path.join(DOCS, "data", "grammar-usage.json")

AR_WORD = re.compile(r"[\u0621-\u063A\u0641-\u064A\u064B-\u0652\u0670]+")
DIAC = re.compile(r"[\u064B-\u0652\u0670\u0640]")


def nrm(w):
    """Arabic word, spelling wobble removed (hamza forms, ة/ه, ى/ي, marks)."""
    w = DIAC.sub("", w or "")
    w = w.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
    return w


PRONOUN_WORDS = {nrm(w) for w in ("أنا", "انا", "إنت", "انت", "إنتي", "انتي", "إنتو", "انتو", "هو", "هي", "إحنا", "احنا", "هم", "همه")}
SUFFIXES = ("هم", "كم", "ها", "نا", "ني", "ه", "ك", "ي")


def strip_pron(w):
    out = {w}
    for s in SUFFIXES:
        if w.endswith(s) and len(w) - len(s) >= 2:
            out.add(w[: -len(s)])
    return out


# ---------------------------------------------------------------- Amal's verbs
_items = json.load(open(os.path.join(DOCS, "data", "words.json"), encoding="utf-8"))["items"]


def _forms(topic, first_only=False):
    out = set()
    for x in _items:
        if x.get("topic") != topic:
            continue
        ws = [nrm(w) for w in AR_WORD.findall(x.get("arabic") or "")]
        ws = [w for w in ws if w not in PRONOUN_WORDS and w != nrm("ما") and len(w) >= 2]
        if first_only:
            ws = ws[:1]
        out.update(ws)
    return out


NOT_PAST = {nrm(w) for w in ("عندي", "عندك", "عنده", "عندها", "عندنا", "عندكم", "عندهم", "راح", "كان", "كانت",
                              "كنت", "كانوا", "اكل", "أكل", "شغل", "كل", "مش", "حدا", "شي", "إشي", "اشي", "غير", "مرة")}
# a past form ends in a past person ending, or is the bare he-form (خرب, شرب) - never
# a noun in ة or an I-form in أ...ي
PAST = {w for w in _forms("Past Tense", first_only=True) if len(w) >= 3 and not w.endswith("ه")
        and (re.search(r"(ت|تي|تو|توا|نا|وا)$", w) or (len(w) == 3 and w[0] not in "ابتين"))} - NOT_PAST
# commands that are also everyday words (شغل work, غير other) are left out
COMMAND = {w for w in _forms("Command Tense", first_only=True) if len(w) >= 3} - {nrm(x) for x in ("كل", "شغل", "غير")}
PRESENT_STEMS = set()
for w in _forms("Verbs List"):
    for p in ("بت", "بن", "بي", "ب"):
        if w.startswith(p) and len(w) - len(p) >= 2:
            PRESENT_STEMS.add(w[len(p):])
            break
ADJ = {w for w in _forms("Adjectives") if len(w) >= 3} - {nrm(x) for x in ("هادي", "نفس", "مرة")}  # also "this", "same", "a time"
FEM_NOUNS = set()
for x in _items:
    for w in AR_WORD.findall(x.get("arabic") or ""):
        if w.endswith("ة") and len(w) >= 3:
            FEM_NOUNS.add(nrm(w))
# Nouns from Amal's Doc (one-word entries of her noun topics), for possession: a noun + an owner (2026-10-01, the 09-30
# idafa drill: dars el-3arabi, bab el-8urfa, bent jaari, kundret el-Chanel were not on the old fixed head-word list).
NOUN_TOPICS = {"Food and Drink", "Travel and Weather", "Time and Calendar", "Nature and Places", "Household Items",
               "People, Family, and Professions", "Body Parts and Clothing", "Random Nouns", "Animals"}
NOUNS = set()
for x in _items:
    ws = AR_WORD.findall(re.split(r"\s*/\s*", x.get("arabic") or "")[0])
    if x.get("topic") in NOUN_TOPICS and len(ws) == 1 and len(nrm(ws[0])) >= 2 and not ws[0].startswith("ال"):
        NOUNS.add(nrm(ws[0]))
NOUNS -= ADJ | PAST | COMMAND | PRONOUN_WORDS | {nrm(w) for w in ("هادي", "نفس", "مرة", "يوم", "شي", "إشي")}
POSS = ("ي", "ك", "ه", "ها", "نا", "هم", "كم")


def is_past(w):
    return any(x in PAST for x in strip_pron(w))


def is_b_present(w):
    for p in ("بت", "بن", "بي", "ب"):
        if w.startswith(p) and len(w) - len(p) >= 2:
            for x in strip_pron(w[len(p):]):
                if x in PRESENT_STEMS:
                    return True
    return False


# ---------------------------------------------------------------- patterns
E = r"(?=\s|$|[،.؟?!])"
FUNC = r"(?:و|في|من|مع|على|عن|يعني|شو|مش|هو|هي|بس|كمان|لما|إذا|اذا|إنه|انه|إنو|انو|لأنه|لانه|عشان|ما|لا|أو|او)(?=\s|$|[،.؟?!])"   # not a noun after a tool word
BARE_IMPERF = r"(?!ال)(?!(?:أنا|انا|إنت|انت|إنتي|انتي|احنا|إحنا)(?:\s|$))(?:أ|ا|ت|ي|ن)[\u0621-\u064A]{2,}"

# Regex rules. Each fires at most once per turn per bucket.
P = {
 "A2":  [r"(?:^|\s)(?:بيت|اسم|باب|سيارة|شغل|أخو|بنت|ابن|نفس|آخر|أول|عكس|درجة|شمال|جنوب)\s+ال[\u0621-\u064A]{2,}"],
 "A3":  [r"(?:^|\s)(?!ال|مرة)[ء-ي]{2,}ة\s+ال[ء-ي]{2,}"],  # a feminine noun before its owner
 "A4":  [r"(?:^|\s)(?:اسمي|اسمك|اسمها|بيتي|بيتك|بيتها|شغلي|شغلك|عمري|عمرك|حالي|حالك|إلي|إلك|صاحبي|صاحبتي|بلوزتي|أواعي|أهلي|عيلتي)" + E],
 # the middle noun is bare: bab el-8urfa el-maftoo7 (noun + owner + adjective) is not a chain (2026-10-01)
 "A5":  [r"(?:^|\s)(?:باب|مفتاح|صاحب)\s+(?!ال)[\u0621-\u064A]{3,}\s+ال[\u0621-\u064A]{3,}"],
 # A job made of TWO words (doktoar snaan, m3allem el-3arabi). A lone job word is vocabulary, not this rule.
 "A6":  [r"(?:^|\s)(?:دكتور|دكتورة|معلم|معلمة|أستاذ|أستاذة|مهندس|مهندسة|محامي|محامية|طبيب|طبيبة)"
         r"\s+(?!(?:و|في|من|مع|على|عن|يعني|شو|مش|هو|هي|كمان|بس)(?:\s|$))[ء-ي]{2,}"],
 # kam + a noun (Medi 2026-09-24): the noun after kam is singular. A use = kam followed by a word.
 "E5":  [r"(?:^|\s)كم\s+(?!(?:و|في|من|مع|على|عن|يعني|شو|مش|هو|هي|مرة)(?:\s|$))[ء-ي]{2,}"],
 "A7":  [r"(?:^|\s)(?!اليوم|الله)ال[\u0621-\u064A]{2,}\s+(?!اللي|اليوم|الله)ال[\u0621-\u064A]{2,}"],
 "A9":  [r"(?:^|\s)(?:بيوت|أيام|ايام|ساعات|ولاد|بنات|شبابيك|أبواب|كتب|ألوان|أشياء|ناس|زلام|نسوان|مطاعم|صور|خطط|دول|مرات)" + E],
 "A9b": [r"(?:^|\s)(?:بيوت|بواب|شبابيك|سيوف|عيون|مكاتب|مساجد|مطاعم|أولاد|ولاد)" + E],
 "A10": [r"(?:^|\s)(?:هاد|هادي|هدول|هذا|هذي|هداك|هديك|هاي)" + E],
 "A10b":[r"(?:^|\s)(?:هاد|هادي|هدول|هذا|هذي|هاي|هداك|هديك|هدولاك)\s+ال[\u0621-\u064A]{2,}"],
 "A11": [r"(?:^|\s)الكل" + E, r"(?:^|\s)كل\s+(?:حدا|إشي|اشي|شي|يوم|الناس|ال[\u0621-\u064A]{2,})"],
 # GR-30 (2026-10-07): the Oct 2 tool words before or after a noun (A13 awal / oola, A14 taani, A15 aa5er / a5eer, A16 8eir,
 # A17 nafs). A use = the tool word with a noun next to it (a function word after it is not a noun). The wrong forms
 # (el- before nafs / 8eir / taani) are uses too: a slip is still an attempt at the rule.
 "A13": [r"(?:^|\s)(?:ال)?أول[ىي]?\s+(?!" + FUNC + r")(?:ال)?[\u0621-\u064A]{2,}", r"(?:^|\s)ال[\u0621-\u064A]{2,}\s+الأول[ىي]?" + E],
 "A14": [r"(?:^|\s)(?:ال)?تان[يى][ةه]?\s+(?!" + FUNC + r")(?:ال)?[\u0621-\u064A]{2,}", r"(?:^|\s)(?:ال)?[\u0621-\u064A]{2,}\s+(?:ال)?تان[يى][ةه]?" + E],
 "A15": [r"(?:^|\s)(?:ال)?آخر\s+(?!" + FUNC + r")(?:ال)?[\u0621-\u064A]{2,}", r"(?:^|\s)(?:ال)?[\u0621-\u064A]{2,}\s+الأخير(?:ة|ه|ات)?" + E],
 "A16": [r"(?:^|\s)(?:ال)?غير\s+(?!" + FUNC + r")(?!هيك|إنه|انه|إنو|انو|كده|كدا)(?:ال)?[\u0621-\u064A]{2,}"],
 "A17": [r"(?:^|\s)(?:ال)?نفس\s+(?!" + FUNC + r")(?:ال)?[\u0621-\u064A]{2,}"],

 "B2":  [r"(?:^|\s)(?:بدي|بدك|بدها|بدنا|بدهم|لازم|ممكن|بحب|بقدر|بتقدر|بجرب|ببلش|بعرف)\s+" + BARE_IMPERF,
         # Amal's notes 2026-09-27: also after "it's important / most likely / I feel like" statements
         # (muhem te3raf, 3ala el-a8lab niji, jaay 3abali). إنه / إني after مهم is "that", not a verb.
         r"(?:^|\s)(?:مهم|على الأغلب|على الاغلب|عالأغلب|عالاغلب|جاي على بالي|جاي عبالي|جاية على بالي|جاية عبالي)\s+"
         r"(?!(?:انه|انها|اني|انك|انهم|انو)(?:\s|$))" + BARE_IMPERF],
 "B3":  [r"(?:^|\s)(?:لما|عشان|قبل ما|بعد ما|حتى)\s+" + BARE_IMPERF],
 "B4":  [r"(?:^|\s)(?:بدي|لازم|ممكن)\s+" + BARE_IMPERF + r"\s+و\s*" + BARE_IMPERF],
 "B4b": [r"(?:^|\s)(?:لما|إذا|اذا)\s+(?:ما\s+)?ب[\u0621-\u064A]{2,}"],
 "B6":  [r"(?:^|\s)(?:كان|كانت|كنت|كنا|كانوا|كنتي|كنتو)" + E],
 "B7":  [r"(?:^|\s)(?:كان|كنت|كانت|كنا|كانوا)\s+ب[\u0621-\u064A]{3,}"],
 "B8":  [r"(?:^|\s)(?:أكون|اكون|تكون|يكون|نكون|بكون|بتكون|بيكون|بنكون)" + E],
 "B9":  [r"(?:^|\s)(?:نكون|يكونوا|تكوني|تكونوا|بنكون|بيكونوا)" + E],
 "B11": [r"(?:^|\s)ما\s+ت[\u0621-\u064A]{2,}(?:ي|وا|و)?" + E],
 "B12": [r"(?:^|\s)(?:ببسط|بنبسط|بضحك|بضحّك|بزعل|بزعّل|بتعب|بتعّب|بزهق|بزهّق|بخوف|بخوّف|بجهز|بجهّز|بعصب|بعصّب|بخرب|بخرّب|بزعج|بنزعج|بكسر|بنكسر)"],
 "B13": [r"(?:^|\s)(?:رح|راح)\s+" + BARE_IMPERF],
 "B14": [r"(?:^|\s)عم\s+ب?[\u0621-\u064A]{3,}"],
 "B15": [r"(?:^|\s)(?:رايح|رايحة|ناسي|ناسية|عارف|عارفة|قاعد|قاعدة|ساكن|ساكنة|شايف|شايفة|جايب|جاي|جاية|مبسوط|مبسوطة|مزعوج|مزعوجة|متأكد|متأكدة|مشغول|مشغولة|معصب|معصبة|خربان|خربانة)" + E],
 "B16": [r"(?:^|\s)(?:كان|كانت|كنت)\s+لازم"],
 "B17": [r"(?:^|\s)صارل[\u0621-\u064A]*|(?:^|\s)صار\s+ل[\u0621-\u064A]+"],

 "C1":  [r"(?:^|\s)(?:أنا|انا|هو|هي|إنت|انت|احنا|إحنا)\s+(?:مبسوط|مبسوطة|تعبان|تعبانة|جاهز|جاهزة|مشغول|مشغولة|هون|هناك|من|في|متأكد|متأكدة|منيح|منيحة|كويس|تمام)" + E],
 "C2":  [r"(?:^|\s)اللي\s+[\u0621-\u064A]{3,}(?:ه|ها|هم)" + E],
 "C3":  [r"(?:^|\s)(?:أكتر|اكتر|أكثر|أحسن|احسن|أقل|اقل|أسوأ|أصعب|أسهل|أكبر|أصغر|أحلى|أول)" + E],
 "C4":  [r"(?:^|\s)مش" + E, r"(?:^|\s)ما\s+ب[\u0621-\u064A]{2,}", r"(?:^|\s)(?:أبدا|ابدا|أبدًا|ابدًا)"],
 "C4b": [r"(?:^|\s)(?:أبدا|ابدا|أبدًا|ابدًا)\s+ما(?:\s|$)", r"(?:^|\s)ولا\s+(?:إشي|اشي|شي|حدا|مرة)"],
 "C5":  [r"(?:^|\s)أو" + E, r"(?:^|\s)ولا" + E],
 "C6":  [r"(?:^|\s)(?:لما|إذا|اذا)" + E],
 "C7":  [r"(?:^|\s)اللي" + E, r"(?:^|\s)إللي" + E],
 "C8":  [r"(?:^|\s)(?:شو|وين|ليش|مين|كيف|قديش|أديش|إمتى|امتى|لوين)" + E],
 "C9":  [r"(?:^|\s)(?!بال)(?:ب|بي|بت|بن)[\u0621-\u064A]{3,}\s+ال[\u0621-\u064A]{2,}"],
 "C10": [r"(?:^|\s)(?:من وين|لوين|على شو|عن شو|مع مين|لمين|من مين|من إمتى|من امتى|بشو)" + E],

 "D1":  [r"(?:^|\s)(?:من|على|في|مع|عن)\s+(?!ما(?:\s|$)|في(?:\s|$))[\u0621-\u064A]{2,}"],
 "D2":  [r"(?:^|\s)(?:بطلب|أطلب|خايف|خايفة|مشتاق|مشتاقة|قلقان|مختلف|بدفع|أدفع|انبسطت|انبسطنا|بتأسف|اتأسف|زعلان|زعلانة)\s+(?:من|ل|على|عن|مع|في|ب)"],
 "D3":  [r"(?:^|\s)(?:معي|معك|معه|معها|معنا|منك|منه|منها|منهم|مني|عندي|عندك|عنده|عندها|عندنا|عندهم|عنا|عليه|عليها|علي|إلي|إلك|إلهم|فيه|فيها|فيهم)" + E],
 "D4":  [r"(?:^|\s)(?:ب|ت|ي|ن|أ|ا)[\u0621-\u064A]{2,}(?:لك|لي|له|لها|لهم|ني)" + E],
 "D5":  [r"(?:^|\s)(?:من|على|في|مع|عن)\s+ال[\u0621-\u064A]{2,}", r"(?:^|\s)(?:بال|لل|فال)[\u0621-\u064A]{2,}"],
 "D6":  [r"(?:^|\s)(?:إياه|اياه|إياك|اياك|إياها|اياها|إياهم|اياهم)" + E],

 "E1":  [r"(?:^|\s)(?:يومين|ساعتين|شهرين|سنتين|مرتين)" + E,
         r"(?:^|\s)(?:تلات|تلاتة|ثلاث|أربع|أربعة|خمس|خمسة|ست|ستة|سبع|سبعة|تمان|تمانية|تسع|تسعة|عشر|عشرة|عشرين|تلاتين)\s+(?:يوم|أيام|ايام|ساعة|ساعات|دقيقة|دقايق|مرة|مرات|سنة|سنين|شهر|شهور|أسبوع|اسابيع)" + E],
 "E2":  [r"(?:^|\s)الساعة" + E, r"(?:^|\s)(?:ونص|وربع|إلا ربع|الا ربع|إلا ثلث|الا ثلث|إلا تلت|الا تلت)" + E],
 "E3":  [r"(?:^|\s)(?:دقيقة|دقيقتين|دقايق|ساعة|ساعتين|ساعات|يوم|يومين|أيام|ايام|أسبوع|اسبوعين)" + E],
 "E4":  [r"(?:^|\s)(?:الاتنين|الإتنين|الاثنين|التلاتا|الثلاثاء|الأربعا|الاربعا|الخميس|الجمعة|السبت|الأحد|الاحد)" + E,
         r"(?:^|\s)(?:مبارح|امبارح|بكرا|بكرة)" + E,
         r"(?:^|\s)(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر|أيلول|تشرين|آب|تموز)" + E,
         r"(?:^|\s)(?:ألفين|الفين)" + E],
}

# Names & places (2026-09-28, scripts/names.py): a name is never a rule trigger. Each Arabic-script name (رام الله,
# بيت لحم, القدس) is swapped for the neutral noun فلان before any rule runs, so "في رام الله" still counts as a
# preposition + noun but "الله" / "بيت" inside a name never fire A1 / A2 / A7 / C9. Text without a name is untouched.
NAME_STANDIN = "فلان"


def _is_farsi(text):
    try:
        from farsi import is_farsi
    except ImportError:
        return False
    return is_farsi(text)


def mask_names(text):
    """(text with each Arabic-script name replaced by NAME_STANDIN, [original names in order]). No names file -> unchanged."""
    try:
        import names
        return names.load().mask(text or "", NAME_STANDIN)
    except Exception:
        return text, []


def unmask(hit, back):
    """Put the real name back into a hit string (hits are shown as 'where?' on the page)."""
    for name in back:
        if NAME_STANDIN not in hit:
            break
        hit = hit.replace(NAME_STANDIN, name, 1)
    return hit


# El- (A1): any real word with the article - not "الله", not "اللي", not a
# dangling "الـ".
A1_SKIP = {nrm(w) for w in ("الله", "اللي", "اللهم")}


def _noun(w):
    """A bare noun of Amal's (also its feminine -t form before an owner: صديقت, شنتت)."""
    n = nrm(w)
    if w.startswith("ال") or n in ADJ or "ً" in w:      # tanween (عادةً) is an adverb, not a noun
        return False
    return n in NOUNS or (n.endswith("ت") and n[:-1] + "ه" in FEM_NOUNS)


def _owner(w):
    """The owner in a possession: an el- noun that is not an adjective, a noun with a possessive ending, or a name."""
    n = nrm(w)
    if w == NAME_STANDIN:
        return True
    if w.startswith("ال") and len(n) >= 4 and n not in A1_SKIP:
        return n[2:] not in ADJ
    for s_ in POSS:
        if n.endswith(s_) and len(n) - len(s_) >= 2:
            b = n[: -len(s_)]
            if b in NOUNS or (b.endswith("ت") and b[:-1] + "ه" in FEM_NOUNS):
                return True
    # a feminine noun with "my / your / her" not on her list (خطيبتي, 09-30 63:07); never a verb (حكيتي, شفتي)
    if re.search(r"ت(?:ي|ك|ها)$", n) and len(n) >= 5 and not is_past(n) and not is_b_present(n):
        return True
    return False


def possession(txt):
    """A2 / A5 from Amal's nouns. Commas are pauses; anything else that is not an Arabic word ends the phrase."""
    ws = [w if AR_WORD.fullmatch(w) else "." for w in re.findall(AR_WORD.pattern + r"|[^\s،,]+", txt)]
    # a restart is one word: "صديق، uh, صديقة" -> صديقة, "benet, uh, benet" -> benet
    ws = [w for k, w in enumerate(ws) if not (w != "." and k + 1 < len(ws) and ws[k + 1].startswith(w))]
    hits = {}
    for i in range(len(ws) - 1):
        a, b = ws[i], ws[i + 1]
        if "A5" not in hits and i + 2 < len(ws) and _noun(a) and _noun(b) and _owner(ws[i + 2]):
            hits["A5"] = " ".join(ws[i:i + 3])
        if "A2" not in hits and _noun(a) and _owner(b):
            hits["A2"] = a + " " + b
    return hits


def word_rules(words):
    """Buckets that come from single words (Doc lexicons), with the word."""
    hits = {}
    for w in words:
        n = nrm(w)
        if w.startswith("ال") and len(n) >= 4 and n not in A1_SKIP and "A1" not in hits:
            hits["A1"] = w
        if is_b_present(n) and "B1" not in hits:
            hits["B1"] = w
        if is_past(n) and n not in NOUNS and "B5" not in hits:   # درس is "a lesson" far more than "he studied"
            hits["B5"] = w
        if n in COMMAND and not w.startswith("أ") and "B10" not in hits:
            hits["B10"] = w
        if n in ADJ and "A8" not in hits:
            hits["A8"] = w
        # the pointer: a verb of hers with an object ending (بعمله, بتبيعه, خربتهم)
        if "C2" not in hits and not w.endswith("ة"):
            for s_ in ("ها", "هم", "ه"):
                if n.endswith(s_) and len(n) - len(s_) >= 3 and (is_b_present(n[:-len(s_)]) or n[:-len(s_)] in PAST):
                    hits["C2"] = w
                    break
    for i, w in enumerate(words[:-1]):
        n = nrm(w)
        if n.endswith("ت") and n[:-1] + "ه" in FEM_NOUNS and "A3" not in hits \
                and words[i + 1].startswith("ال") and nrm(words[i + 1]) != n:
            hits["A3"] = w + " " + words[i + 1]
    return hits


buckets = json.load(open(os.path.join(DOCS, "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]
ids = [b["id"] for b in buckets]
names = {b["id"]: b["name"] for b in buckets}
# F1/F2/F3 are sounds (rule M4) - not counted as grammar uses.
NOT_COUNTED = {"F1", "F2", "F3"}

def detect(txt, only=None):
    """{bucket: hit} for one line already in Arabic script (names masked). `only` limits the buckets."""
    txt = re.sub(r"(?:^|\s)الـ(?=\s|$|[،,.])", " ", txt)
    txt = re.sub(r"\S+(--|—)", " ", txt)  # a word he broke off
    words = AR_WORD.findall(txt)
    found = word_rules(words)
    for bid, hit in possession(txt).items():
        found.setdefault(bid, hit)
    for bid in ids:
        if bid in NOT_COUNTED or bid in found:
            continue
        for pat in P.get(bid, []):
            mt = re.search(pat, txt)
            if mt:
                found[bid] = mt.group(0).strip()
                break
    return {k: v for k, v in found.items() if only is None or k in only}


# A phrase he spreads over two or three turns ("so بيت" / "صديقة،" / "خطيبتي،" at 09-30 63:00, or "Hadi el," / "uh,
# shanta" at 59:28) is one phrase: consecutive Medi turns <= JOIN_GAP s apart, with at most a one-word "yes / mm" from
# Amal between them, are read together for the phrase rules below. A hit counts only when it crosses a turn boundary
# (a hit inside one turn was already counted there), once per bucket per joined stretch.
JOIN_GAP = 4.0
OPEN_END = re.compile(r"(?:b(?:el|al|il)|الـ|ال)\s*[,،]?\s*$", re.I)   # "Hadi el," - the noun is still coming
OPEN_GAP = 8.0
JOIN_RULES = {"A2", "A3", "A5", "A6", "A7", "A10b"}
BACKCHANNEL = {nrm(w) for w in ("إيه", "ايه", "اه", "آه", "مم", "ممم", "اي", "أيوه", "ايوه", "نعم", "صح", "اوكي", "أوكي")} | \
    {"mm", "mhm", "mm-hmm", "uh-huh", "yes", "yeah", "okay", "ok", "right"}

# Hand rulings on USES (2026-10-01, Medi's read of the 09-30 lesson): a moment the counter took for a use that is not one
# (a question about the rule, or one slip the counter also counted as a right use). Matched by date + bucket + time
# (+-3 s). Never deleted: each lands in grammar-usage.json "ruled_out" with its reason and is left out of every count.
RULINGS_FILE = os.path.join(os.path.dirname(DOCS), "data", "grammar-usage-rulings.json")


def _secs(v):
    p = [float(x) for x in str(v).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def load_rulings():
    rows = [dict(r, _t=_secs(r["t"])) for r in json.load(open(RULINGS_FILE, encoding="utf-8"))["rows"]] if os.path.exists(RULINGS_FILE) else []
    try:   # PR-15: Medi's 'Not a use' taps on the Lessons transcript + his standing not-use rules (MC-nnn)
        import medi_corrections as MC
        rows += [dict(r, _t=None if r.get("pattern") else float(r["t"])) for r in MC.use_rulings()]
    except Exception as e:  # noqa: BLE001 - a bad corrections file never stops a build (council 5)
        print("detect_grammar_usage: Medi's corrections not applied (%s)" % type(e).__name__)
    return rows


def ruled(rulings, date, bucket, t, hit=None):
    for r in rulings:
        if r.get("pattern"):
            if r["bucket"] == bucket and hit is not None and _mc_piece(hit) == _mc_piece(r.get("hit")):
                return r
        elif r["date"] == date and r["bucket"] == bucket and abs(r["_t"] - t) <= 3.0:
            return r
    return None


def _mc_piece(s):
    import medi_corrections as MC
    return MC._piece(s)


def _is_backchannel(text):
    w = re.sub(r"[^\wء-ي-]+", " ", (text or "").lower()).split()
    return len(w) <= 1 and (not w or nrm(w[0]) in BACKCHANNEL)


def stretches(T):
    """Runs of consecutive Medi turns (indexes into T) that read as one phrase (see JOIN_GAP)."""
    runs, cur, last_end = [], [], None
    for i, t in enumerate(T):
        if t["speaker"] != "Medi":
            if cur and t["start"] < last_end:
                continue                                    # said while he still held the floor (his turn spans it)
            if cur and not _is_backchannel(t["text"]):
                runs.append(cur)
                cur = []
            continue
        gap = OPEN_GAP if cur and OPEN_END.search(T[cur[-1]]["text"]) else JOIN_GAP
        if cur and t["start"] - last_end > gap:
            runs.append(cur)
            cur = []
        cur.append(i)
        last_end = t.get("end", t["start"])
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) > 1]


SOUND_TAG = re.compile(r"\[[^\[\]\n]{1,60}\]")     # GR-31: an engine sound tag in square brackets


def read_turn(t):
    """(text in Arabic script with names masked, names, read_as or None). read_as = the line as the counter read it
    when it had Latin letters (Arabizi), so the page can show what was counted."""
    if _is_farsi(t["text"]):
        return None, [], None                       # Farsi side conversation (2026-09-28) is no grammar evidence
    # GR-31 (Medi 2026-10-09 "remvoe the [lauging] grammar errors"): the engine's sound tags ([ضحك], [ضحكة], [laughs],
    # [صوت من behind الكاميرا]) are no words of his - 22 of them had counted as B5 / B10 / A1 / A8 uses
    txt, back = mask_names(SOUND_TAG.sub(" ", t["text"]))   # names are never rule triggers (see mask_names)
    ar = to_arabic(txt)
    if not AR_WORD.search(ar):
        return None, back, None
    return ar, back, (unmask(ar, back) if ar != txt else None)


# Automatic "not a use" rules (Medi 2026-10-02: "you are creating rules for yourself for future lessons right"). Each
# came from a hand ruling; every moment they skip is listed in grammar-usage.json "not_uses_auto" with the reason.
# 1. A question ABOUT the rule: English "when is it / is it / do I say / how do you say / what's" right before the Arabic
#    (09-30 34:49 "but when is it طاولة الكبير?") - he is asking, not using.
ASK_FRAME = re.compile(r"\b(?:when is it|when do (?:i|you|we)|is it|do (?:i|you|we) say|how do (?:i|you|we) say|"
                       r"what(?: i|')s|what does)\W*(?:\w+\W+){0,2}$", re.I)


def asks_about_rule(text):
    m = re.search(r"[ء-ي]", text or "")
    return bool(m and ASK_FRAME.search(text[:m.start()]))


# 2. "كم مرة؟" alone right after Amal spoke, and her next line repeats hers: he asked "kaman marra?" (again?) and Scribe
#    dropped the -an (five moments, 09-10 .. 09-26). A real "how many times?" gets a number, not her sentence again.
def asks_again(T, i, txt):
    if re.sub(r"[^ء-ي ]|آآآ|اه|امم", " ", txt).split()[-2:] != ["كم", "مرة"]:
        return False
    before = next((T[j]["text"] for j in range(i - 1, max(-1, i - 4), -1) if T[j]["speaker"] != "Medi"), "")
    after = next((T[j]["text"] for j in range(i + 1, min(len(T), i + 4)) if T[j]["speaker"] != "Medi"), "")
    w = lambda x: {nrm(y) for y in AR_WORD.findall(x or "") if len(y) >= 3}
    return len(w(before) & w(after)) >= 2


# 3. GR-28 (Medi 2026-10-05, 10-02 07:34 -> 07:38 "'ala el-3ashrah": "this is a repeat of a mistake and should be marked as
#    repeat and not counted"): a Medi line that says the SAME phrase again within 30 s after Amal spoke - the fixed version of
#    the line she just prompted on - is one moment with the slip, not fresh correct uses. Same Arabic words once el- (ال) and
#    fillers are stripped; at least two words; Amal (or chat) spoke between the two lines.
FILLERS = {"آآآ", "اه", "امم", "اممم", "آآ", "اا", "ام", "يعني"}


def _core(text):
    out = set()
    for w in AR_WORD.findall(text or ""):
        w = nrm(w)
        if w in FILLERS or len(w) < 2 or re.fullmatch(r"[اهميى]+", w):   # آآآ / اممم / يعني-less hums after nrm()
            continue
        out.add(w[2:] if w.startswith("ال") and len(w) > 3 else w)
    return out


def repeat_of_fixed(T, i, window=30.0):
    """The earlier Medi line this one repeats (same core words, Amal between, within `window` s), or None."""
    me = _core(T[i]["text"])
    if len(me) < 2:
        return None
    saw_amal = False
    for j in range(i - 1, -1, -1):
        if T[i]["start"] - T[j]["start"] > window:
            return None
        if T[j]["speaker"] != "Medi":
            saw_amal = True
            continue
        if saw_amal and _core(T[j]["text"]) == me and nrm(T[j]["text"]) != nrm(T[i]["text"]):
            return T[j]
    return None


# 4. GR-32 (Medi 2026-10-09 on 10-08: "You are also doing a poor job of realizing for grammar errors that I am being
#    corrected and repeating the correctiong. THese should also be marked as repeat and uncounted"): from
#    word_coverage.FROM on, a use whose words the tutor GAVE him in the 30 s before - her correction or recast of his line
#    or the fix a counted slip names (word_coverage.supplies), or the line he says back word for word - is not a use
#    (10-08 04:06 هي راسها بيوجع after her 04:00 هي راسها بيوجع: the B1 use). GR-28 is the case of his own earlier line.
def audit_fix_times(date, path=None):
    """Times of the tutor's fixes the counted slips name (the full audit's sweep_compat rows, grammar and words)."""
    p = path or os.path.join(os.path.dirname(DOCS), "data", "full-audit-2026-09-26.json")
    try:
        sc = json.load(open(p, encoding="utf-8"))["sweep_compat"]
    except (OSError, ValueError, KeyError):
        return []
    out = []
    for r in (sc.get("rows") or []) + (sc.get("vocab") or []):
        if r.get("date") == date and r.get("t_amal"):
            try:
                out.append((_secs(r["t_amal"]), r.get("right") or r.get("amal_gave")))
            except ValueError:
                pass
    return out


def as_turns(T):
    return [{"who": "Medi" if t["speaker"] == "Medi" else "Amal", "t": t["start"], "end": t.get("end", t["start"]), "text": t["text"]} for t in T]


def grammar_repeat(Tw, i, hit, sup):
    """The tutor line (index) whose words give this use, or None (GR-32): every word of the hit is one of hers (el- and
    w- aside, letter for letter otherwise - his عيان after her عيانة is NOT her word, it is the slip again), and her line
    is a correction / recast / a form she gave (sup)."""
    import word_coverage as WC
    same = lambda w: re.sub(r"^و(?=ال)", "", WC.norm(w))       # the form itself: el- counts (her قمر, his القمر = his own el-)
    hw = [same(w) for w, cut in WC.arabic_tokens(hit) if not cut]
    if not hw:
        return None
    for j in WC.tutor_before(Tw, i, WC.GRAMMAR_REPEAT_S):
        if j not in sup:
            continue                      # only her correction / recast / given form (a question of hers is not one)
        hers = {same(w) for w in WC.her_words(Tw, j, sup)}
        if all(h in hers for h in hw):
            return j
    return None


def repeat_row(date, t, j_turn, bid, hit, said):
    return {"date": date, "t": round(t, 1), "said": said[:300], "bucket": bid, "hit": hit, "repeat": True,
            "amal_t": round(float(j_turn["t"]), 1), "amal_line": (j_turn.get("text") or "")[:160], "rule": "GR-32",
            "why": "repeat of the tutor's correction at %02d:%02d («%s»): said after she gave it, not a use (GR-32, Medi 2026-10-09)"
                   % (int(j_turn["t"]) // 60, int(j_turn["t"]) % 60, (j_turn.get("text") or "")[:60])}


if __name__ == "__main__":
    import word_coverage as WC
    dates = sorted(d for d in os.listdir(ANEES) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    # only lessons with a published page (same list as full_audit_build.py), so the Lessons page and the console add up
    dates = [d for d in dates if os.path.exists(os.path.join(DOCS, "lessons", d + ".html"))]
    NOT_ARABIC = {"2026-08-22", "2026-08-23", "2026-09-01"}
    RULINGS = load_rulings()

    uses = defaultdict(list)
    ruled_out = []
    not_uses = []
    per_lesson = {}
    for date in dates:
        if date in NOT_ARABIC:
            continue
        T, src = page_lines(date)          # the delivered transcript: the same lines as docs/data/lessons/<date>.json
        if not T:
            continue
        seen_here = Counter()
        n_turns = n_latin = 0
        read = {}
        TW = as_turns(T)
        SUP = WC.supplies(TW, audit_fix_times(date)) if WC.in_scope(date) else {}

        def add(t, bid, hit, read_as, back, joined=None):
            if back:
                hit = unmask(hit, back)
            u = {"date": date, "t": round(t["start"], 1),
                 "mmss": "%02d:%02d" % (int(t["start"]) // 60, int(t["start"]) % 60), "hit": hit, "said": t["text"][:300]}
            if read_as:
                u["read_as"] = read_as[:300]
            if joined:
                u["joined"] = joined
            r = ruled(RULINGS, date, bid, t["start"], hit)
            if r:
                ruled_out.append(dict(u, bucket=bid, why=r["why"], ruling_by=r.get("by")))
                return
            seen_here[bid] += 1
            uses[bid].append(u)

        for i, t in enumerate(T):
            if t["speaker"] != "Medi":
                continue
            txt, back, read_as = read_turn(t)
            if txt is None:
                continue
            read[i] = (txt, back, read_as)
            n_turns += 1
            n_latin += bool(read_as and not AR_WORD.search(t["text"]))
            if asks_about_rule(t["text"]):
                not_uses.append({"date": date, "t": round(t["start"], 1), "said": t["text"][:300],
                                 "why": "a question about the rule, not a use (automatic rule, Medi 2026-10-01)"})
                continue
            prev = repeat_of_fixed(T, i)
            if prev is not None:
                not_uses.append({"date": date, "t": round(t["start"], 1), "said": t["text"][:300], "repeat": True, "rule": "GR-28",
                                 "why": "repeat of the line Amal just fixed (%02d:%02d): one moment with the slip, not a new use (GR-28, Medi 2026-10-05)"
                                        % (int(prev["start"]) // 60, int(prev["start"]) % 60)})
                continue
            found = detect(txt)
            if "E5" in found and asks_again(T, i, txt):
                not_uses.append({"date": date, "t": round(t["start"], 1), "said": t["text"][:300], "bucket": "E5",
                                 "why": "'كم مرة؟' and Amal repeats herself: he asked 'kaman marra' (again?) "
                                        "(automatic rule, Medi 2026-10-02)"})
                del found["E5"]
            for bid, hit in found.items():
                j = grammar_repeat(TW, i, unmask(hit, back) if back else hit, SUP) if SUP else None
                if j is not None:
                    not_uses.append(repeat_row(date, t["start"], TW[j], bid, unmask(hit, back) if back else hit, t["text"]))
                    continue
                add(t, bid, hit, read_as, back)
        for run in stretches(T):
            run = [i for i in run if not _is_farsi(T[i]["text"])]
            if len(run) < 2 or not any(i in read for i in run):
                continue
            # the raw lines are joined BEFORE the Arabizi read, so an el- at the end of one turn meets its noun in
            # the next ("Hadi el," / "uh, shanta")
            raw, back = mask_names(" , ".join(T[i]["text"] for i in run))
            joined_txt = to_arabic(raw)
            singles = [read[i][0] for i in run if i in read]
            for bid, hit in detect(joined_txt, only=JOIN_RULES).items():
                if any(hit in s_ for s_ in singles):
                    continue                        # inside one turn: already counted there
                first = hit.split()[0]
                at = next((i for i in run if i in read and first in read[i][0]), run[0])
                j = grammar_repeat(TW, at, unmask(hit, back), SUP) if SUP else None
                if j is not None:
                    not_uses.append(repeat_row(date, T[at]["start"], TW[j], bid, unmask(hit, back), T[at]["text"]))
                    continue
                add(T[at], bid, hit, unmask(joined_txt, back), back, joined=[round(T[i]["start"], 1) for i in run])
        per_lesson[date] = {
            "source": src,
            "medi_arabic_turns": n_turns,
            "medi_latin_turns_read": n_latin,
            "uses": sum(seen_here.values()),
            "unique_rules": len(seen_here),
            "by_bucket": dict(seen_here),
        }
        print("%s  Medi Arabic turns=%4d (Latin %3d)  rule uses=%5d  unique rules=%2d"
              % (date, n_turns, n_latin, sum(seen_here.values()), len(seen_here)))

    totals = {bid: len(v) for bid, v in uses.items()}
    json.dump({
        "updated": "2026-10-01",
        "method": ("Every Medi turn with Arabic in it is checked once per bucket - in Arabic script, or in Latin letters "
                   "(Arabizi), which scripts/arabizi_reader.py reads as Arabic first (Amal's spelling of her own words; "
                   "English and unknown words are breaks, never guessed); such a use keeps 'read_as'. Verbs (B1 present, "
                   "B5 past, B10 command) and adjectives (A8) are recognised from Amal's vocabulary Doc; possession "
                   "(A2 / A5) from her nouns; the rest by pattern. A phrase spread over consecutive turns is read "
                   "together for the phrase rules (A2 A3 A5 A6 A7 A10b; 'joined' = the turns). Each use keeps the word "
                   "that triggered it ('hit'). A use is the rule being exercised, right or wrong - it is not a mistake. "
                   "Hand rulings (data/grammar-usage-rulings.json) move a moment that is not a use to 'ruled_out', "
                   "with the reason; it is never deleted."),
        "lessons": per_lesson,
        "totals": totals,
        "uses": {k: v for k, v in uses.items()},
        "ruled_out": ruled_out,
        "not_uses_auto": not_uses,
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\nwrote", OUT)
    print("ruled out by hand:", len(ruled_out), "| skipped by the automatic rules:", len(not_uses))
    print("lexicons: past %d, command %d, present stems %d, adjectives %d, nouns %d"
          % (len(PAST), len(COMMAND), len(PRESENT_STEMS), len(ADJ), len(NOUNS)))
    print("rules with at least one use:", len(totals), "of", len(ids))
    for bid, n in sorted(totals.items(), key=lambda x: -x[1]):
        print("  %-5s %-34s %4d" % (bid, names[bid], n))
    never = [b for b in ids if not totals.get(b)]
    print("\nnever used:", ", ".join(never) if never else "none")
