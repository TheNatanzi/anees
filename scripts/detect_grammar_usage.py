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
from lesson_turns import lesson_turns  # noqa: E402

ANEES = r"C:\dev\anees\data\lessons"
DOCS = r"C:\dev\anees-hourly\docs"
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
BARE_IMPERF = r"(?!ال)(?!(?:أنا|انا|إنت|انت|إنتي|انتي|احنا|إحنا)(?:\s|$))(?:أ|ا|ت|ي|ن)[\u0621-\u064A]{2,}"

# Regex rules. Each fires at most once per turn per bucket.
P = {
 "A2":  [r"(?:^|\s)(?:بيت|اسم|باب|سيارة|شغل|أخو|بنت|ابن|نفس|آخر|أول|عكس|درجة|شمال|جنوب)\s+ال[\u0621-\u064A]{2,}"],
 "A3":  [r"(?:^|\s)(?!ال|مرة)[ء-ي]{2,}ة\s+ال[ء-ي]{2,}"],  # a feminine noun before its owner
 "A4":  [r"(?:^|\s)(?:اسمي|اسمك|اسمها|بيتي|بيتك|بيتها|شغلي|شغلك|عمري|عمرك|حالي|حالك|إلي|إلك|صاحبي|صاحبتي|بلوزتي|أواعي|أهلي|عيلتي)" + E],
 "A5":  [r"(?:^|\s)(?:باب|مفتاح|صاحب)\s+[\u0621-\u064A]{3,}\s+ال[\u0621-\u064A]{3,}"],
 # A job made of TWO words (doktoar snaan, m3allem el-3arabi). A lone job word is vocabulary, not this rule.
 "A6":  [r"(?:^|\s)(?:دكتور|دكتورة|معلم|معلمة|أستاذ|أستاذة|مهندس|مهندسة|محامي|محامية|طبيب|طبيبة)"
         r"\s+(?!(?:و|في|من|مع|على|عن|يعني|شو|مش|هو|هي|كمان|بس)(?:\s|$))[ء-ي]{2,}"],
 # kam + a noun (Medi 2026-09-24): the noun after kam is singular. A use = kam followed by a word.
 "E5":  [r"(?:^|\s)كم\s+(?!(?:و|في|من|مع|على|عن|يعني|شو|مش|هو|هي|مرة)(?:\s|$))[ء-ي]{2,}"],
 "A7":  [r"(?:^|\s)(?!اليوم|الله)ال[\u0621-\u064A]{2,}\s+(?!اللي|اليوم|الله)ال[\u0621-\u064A]{2,}"],
 "A9":  [r"(?:^|\s)(?:بيوت|أيام|ايام|ساعات|ولاد|بنات|شبابيك|أبواب|كتب|ألوان|أشياء|ناس|زلام|نسوان|مطاعم|صور|خطط|دول|مرات)" + E],
 "A9b": [r"(?:^|\s)(?:بيوت|بواب|شبابيك|سيوف|عيون|مكاتب|مساجد|مطاعم|أولاد|ولاد)" + E],
 "A10": [r"(?:^|\s)(?:هاد|هادي|هدول|هذا|هذي|هداك|هديك|هاي)" + E],
 "A10b":[r"(?:^|\s)(?:هاد|هادي|هدول|هذا|هذي|هاي)\s+ال[\u0621-\u064A]{2,}"],
 "A11": [r"(?:^|\s)الكل" + E, r"(?:^|\s)كل\s+(?:حدا|إشي|اشي|شي|يوم|الناس|ال[\u0621-\u064A]{2,})"],

 "B2":  [r"(?:^|\s)(?:بدي|بدك|بدها|بدنا|بدهم|لازم|ممكن|بحب|بقدر|بتقدر|بجرب|ببلش|بعرف)\s+" + BARE_IMPERF],
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

# El- (A1): any real word with the article - not "الله", not "اللي", not a
# dangling "الـ".
A1_SKIP = {nrm(w) for w in ("الله", "اللي", "اللهم")}


def word_rules(words):
    """Buckets that come from single words (Doc lexicons), with the word."""
    hits = {}
    for w in words:
        n = nrm(w)
        if w.startswith("ال") and len(n) >= 4 and n not in A1_SKIP and "A1" not in hits:
            hits["A1"] = w
        if is_b_present(n) and "B1" not in hits:
            hits["B1"] = w
        if is_past(n) and "B5" not in hits:
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

if __name__ == "__main__":
    dates = sorted(d for d in os.listdir(ANEES) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    NOT_ARABIC = {"2026-08-22", "2026-08-23", "2026-09-01"}

    uses = defaultdict(list)
    per_lesson = {}
    for date in dates:
        if date in NOT_ARABIC:
            continue
        T, src = lesson_turns(date)
        if not T:
            continue
        medi = [t for t in T if t["speaker"] == "Medi" and AR_WORD.search(t["text"])]
        seen_here = Counter()
        for t in medi:
            txt = re.sub(r"(?:^|\s)الـ(?=\s|$|[،,.])", " ", t["text"])
            txt = re.sub(r"\S+(--|—)", " ", txt)  # a word he broke off
            words = AR_WORD.findall(txt)
            found = word_rules(words)
            for bid in ids:
                if bid in NOT_COUNTED or bid in found:
                    continue
                for pat in P.get(bid, []):
                    mt = re.search(pat, txt)
                    if mt:
                        found[bid] = mt.group(0).strip()
                        break
            for bid, hit in found.items():
                seen_here[bid] += 1
                uses[bid].append({
                    "date": date,
                    "t": round(t["start"], 1),
                    "mmss": "%02d:%02d" % (int(t["start"]) // 60, int(t["start"]) % 60),
                    "hit": hit,
                    "said": t["text"][:300],
                })
        per_lesson[date] = {
            "source": src,
            "medi_arabic_turns": len(medi),
            "uses": sum(seen_here.values()),
            "unique_rules": len(seen_here),
            "by_bucket": dict(seen_here),
        }
        print("%s  Medi Arabic turns=%4d  rule uses=%5d  unique rules=%2d"
              % (date, len(medi), sum(seen_here.values()), len(seen_here)))

    totals = {bid: len(v) for bid, v in uses.items()}
    json.dump({
        "updated": "2026-09-23",
        "method": ("Every Medi turn in Arabic script is checked once per bucket. Verbs (B1 present, B5 past, "
                   "B10 command) and adjectives (A8) are recognised from Amal's vocabulary Doc; the rest by "
                   "pattern. Each use keeps the word that triggered it ('hit'). A use is the rule being "
                   "exercised, right or wrong - it is not a mistake. Turns Scribe wrote in Latin letters "
                   "are not counted here."),
        "lessons": per_lesson,
        "totals": totals,
        "uses": {k: v for k, v in uses.items()},
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\nwrote", OUT)
    print("lexicons: past %d, command %d, present stems %d, adjectives %d" % (len(PAST), len(COMMAND), len(PRESENT_STEMS), len(ADJ)))
    print("rules with at least one use:", len(totals), "of", len(ids))
    for bid, n in sorted(totals.items(), key=lambda x: -x[1]):
        print("  %-5s %-34s %4d" % (bid, names[bid], n))
    never = [b for b in ids if not totals.get(b)]
    print("\nnever used:", ", ".join(never) if never else "none")
