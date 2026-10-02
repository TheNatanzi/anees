# -*- coding: utf-8 -*-
"""Dish names, foods, brands, loan words and countries never go on Amal's 'not on sheet' / new-word lists
(rule WS-15, Medi 2026-09-23: "we dont need to add proper nouns like kabaab and ma2loobe and cake and countries").

One shared test for every list that reaches Amal:
  * scripts/build_amal_review.py   - 'Not on sheet' cards (docs/data/amal-review.json new_words)
  * scripts/amal_new_words.py      - the Tutor hub 'New words from our lessons' task (candidates and the build)

    loan_token(raw)    -> True when one token is a dish / food / brand / loan word (Arabic or Latin, any article or prefix)
    loan_entry(text)   -> True when a list entry ("كعكة / بسكوتة", "cash (بدفع cash)", "الـ air conditioning تبعي",
                          "في أمريكا") is ONLY such words plus grammar glue: every '/' alternative of its headword has at
                          least one content word and every content word is a loan word or a country / place
                          (docs/data/names.json via scripts/names.py). "دكتور عام" stays (عام is a real word).

This changes what Amal is asked, never a score (a not-on-sheet card is unscored either way). Nothing here edits her Doc.
To add a word: append it below (Arabic in any spelling - it is normalised - or Latin in lower case).
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Dishes and foods (Levantine dishes Medi named + the common foods / ingredients that come up when he talks about meals).
DISHES_AR = """كباب كبab مقلوبه مقلوبة منسف مسخن ملوخيه ملوخية فلافل حمص تبوله فتوش شاورما كبه كبة ورق_عنب محشي مجدره مجدرة
فته فتة كنافه كنافة بقلاوه بقلاوة قطايف معمول هريسه هريسة زعتر منقوشه منقوشة مناقيش لبنه لبنة شيش_طاووق طاووق كفته كفتة
مندي كبسه كبسة برياني مسقعه مسقعة شكشوكه شكشوكة فول""".split()
FOODS_AR = """رز ارز زعفران كمون بهارات خبز جبنه جبنة لحمه لحمة دجاج جاج سمك بيض بطاطا بندوره بندورة خيار سلطه سلطة شوربه شوربة
عدس فاصوليا حلويات كعك كعكه كعكة بسكوت بسكوته بسكوتة شوكولا شوكولاته شوكولاتة تشوكلت سكر ملح فلفل زيت زيتون""".split()
LOANS_AR = """كيك كيكه كيكة بيتزا برجر برغر همبرجر همبرغر سوشي باستا معكرونه معكرونة سباغيتي سندويش ساندويش سندويشه سندويشة
شيبس كاتشب مايونيز ستيك نوتيلا كوكا كولا بيبسي ستاربكس ماكدونالدز كوستكو امازون ايفون ايباد سامسونج تويوتا تسلا اوبر نتفليكس
ماكينه ماكينة مكينه مكينة كمبيوتر كومبيوتر لابتوب موبايل تلفون تليفون انترنت ايميل واي_فاي تكسي باص اوتوبيس كاش فيزا
دكتور تلفزيون راديو فيديو كاميرا سينما كافيه كافيتيريا مول سوبرماركت ماركت بنك اوكي باي هاي سوري تكييف مكيف""".split()
LATIN = set("""kabab kebab kabob kebob kabaab ma2loobe ma2loube ma2luba maqluba maqlooba maqlouba mansaf musakhan msakhan molokhia
mlokhiyye falafel hummus hommos tabbouleh tabouleh fattoush shawarma shawerma kibbeh kebbeh mahshi mujaddara knafeh kunafa kanafeh
baklava qatayef ma3moul zaatar za3tar manakish man2oushe labneh tawook kofta kafta mandi kabseh biryani shakshuka ful
rice saffron bread cheese chicken fish egg eggs potato potatoes tomato tomatoes salad soup lentils sugar salt pepper oil olive olives
cake cakes cupcake cookie cookies biscuit biscuits pastry chocolate pizza burger burgers hamburger sushi pasta spaghetti sandwich
chips fries ketchup mayo mayonnaise steak nutella coke cola pepsi starbucks mcdonalds costco amazon iphone ipad samsung toyota tesla
uber netflix google youtube whatsapp instagram facebook tiktok
machine makina computer laptop mobile phone internet email wifi taxi bus cash visa card doctor tv television radio video camera
cinema cafe cafeteria mall supermarket market bank air conditioning conditioner ac""".split())
# grammar glue that may sit around a loan word in a list entry (articles, possessives, a few particles)
GLUE_AR = set("""ال الـ تبعي تبعك تبعه تبعها تبعنا تبعكم تبعهم تبع تاعي في من على ع مع و ب بال لل يا""".split())
GLUE_LAT = {"il", "el", "al", "l", "the", "a", "an", "my", "your", "his", "her", "our", "of", "in", "with", "and", "one", "some",
            "fi", "ma3", "bel", "bil", "w", "tab3i", "taba3i"}

MARKS = re.compile("[ً-ٰٟـ]")
TOKEN = re.compile("[ء-غف-يٱ-ۓً-ٰٟـ]+|[A-Za-z0-9'’]+")
AR_TEST = re.compile("[ء-غف-يٱ-ۓ]")
PREFIXES = ("وبال", "وال", "بال", "فال", "عال", "لل", "ال", "و", "ب", "ل", "ف", "ع")


def ar_norm(s):
    s = MARKS.sub("", s or "")
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي"), ("ء", "")):
        s = s.replace(a, b)
    return s


def _ar_set(words):
    out = set()
    for w in words:
        for part in w.split("_"):          # ورق_عنب: each part of a two-word dish counts
            if AR_TEST.search(part):
                out.add(ar_norm(part))
    return out


LOAN_AR = _ar_set(DISHES_AR + FOODS_AR + LOANS_AR)


def _ar_forms(n):
    forms = {n}
    for p in PREFIXES:
        if n.startswith(p) and len(n) - len(p) >= 2:
            forms.add(n[len(p):])
    for f in list(forms):
        for s in ("ات", "ه", "ي", "و"):
            if f.endswith(s) and len(f) - len(s) >= 2:
                forms.add(f[:-len(s)])
    return forms


def loan_token(raw):
    """One token (Arabic or Latin) is a dish / food / brand / loan word."""
    if not raw:
        return False
    if AR_TEST.search(raw):
        return bool(_ar_forms(ar_norm(raw)) & LOAN_AR)
    n = re.sub("['’]", "", raw.lower())
    if n in LATIN:
        return True
    m = re.match(r"^(?:el|il|al)-?(.+)$", n)
    return bool(m and m.group(1) in LATIN) or (n.endswith("s") and n[:-1] in LATIN)


def _glue(raw):
    if AR_TEST.search(raw):
        return ar_norm(raw) in GLUE_AR
    return raw.lower() in GLUE_LAT


_NAMES = None


def _place_spans(text):
    """[(s, e)] of countries / places / cities (scripts/names.py); [] when names.json is missing."""
    global _NAMES
    if _NAMES is None:
        try:
            import names
            _NAMES = names.Names()
        except Exception:
            _NAMES = False
    if not _NAMES:
        return []
    return [(s["s"], s["e"]) for s in _NAMES.find(text) if s.get("kind") in ("country", "place", "city", "capital")]


def _alternative_is_loan(alt):
    spans = _place_spans(alt)
    content = 0
    for m in TOKEN.finditer(alt):
        raw = m.group(0)
        if any(s <= m.start() and m.end() <= e for s, e in spans):
            content += 1
            continue
        if _glue(raw):
            continue
        if not loan_token(raw):
            return False
        content += 1
    return content > 0


def headword(text):
    """The listed word of an entry: the text before a ' (' gloss ('cash (بدفع cash)' -> 'cash')."""
    t = (text or "").strip()
    return t.split(" (", 1)[0].strip() if " (" in t and not t.startswith("(") else t


def loan_entry(text):
    """A whole list entry is only dish / food / brand / loan words / countries (see the module docstring)."""
    h = headword(text)
    alts = [a.strip() for a in re.split(r"\s/\s|/", h) if a.strip()]
    return bool(alts) and all(_alternative_is_loan(a) for a in alts)
