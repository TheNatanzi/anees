# -*- coding: utf-8 -*-
"""Names & places layer (Medi 2026-09-28: "yes"; his example Sep 21 65:27 - Amal's "Bass ma, ma bazonn fih Irani. yemken fih
رام Allah, Bass Bait La7em, la." split into house + meat and "Allah", and the event showed as Unresolved).

Proper names are recognised FIRST, longest match first, before any word matching: "Bait La7em", "بيت لحم", "رام الله",
"Ram Allah", "رام Allah" (the engine's mixed-script split), "Ramallah" are each ONE place token. Every AI step reads the
same layer: the transcript engine gets them as keyterms, the lesson readers get a glossary, the pages show a chip, and
the counters never score a name as a word.

    python scripts/names.py fetch            # download the open source once (Wikidata SPARQL, CC0) -> data/names-source/
    python scripts/names.py build            # data/names-source + words.json + confirmed labels -> docs/data/names.json
    python scripts/names.py layer [DATE..]   # docs/data/lesson-names/<date>.json (name spans on the transcript, S2-safe)
    python scripts/names.py possible         # docs/data/possible-names.json ("Possible names" on AI Reports › Robot blind spots)
    python scripts/names.py vocab-events     # word-bank-evidence events that fall on a name (for the overlay owner)
    python scripts/names.py find "text"      # print the spans (debug)
    python scripts/names.py keyterms amal|medi|mixed

Data rules
  * Source: Wikidata (CC0 1.0, no attribution required; credited anyway in names.json). Countries (sovereign states +
    Palestine), their capitals, cities with population >= 1,000,000, and a hand seed of Palestinian / Levant places.
    English + Arabic labels come from Wikidata. The Arabizi / colloquial variants in SEED and NATIONALITIES below are
    hand-written FOR MATCHING ONLY (RULES S1: a name is displayed in Arabic script or English, never in an invented Arabizi).
  * Decision 3: a country / nationality whose word is on Amal's list (docs/data/words.json) stays VOCAB and is scored
    normally (today: Irani, Amriki). Any single-word variant of a place that equals one of her words is dropped too (her
    word wins: صور pictures, not Tyre). Multi-word names win over their parts (بيت لحم is a name, not house + meat).
  * People are private (the repo and site are public): only salted SHA-256 fingerprints of their normalised forms are
    stored. The salt is committed on purpose - the point is no readable roster, not secrecy against a determined attacker.
    Seed: Amal, Medi (Mahdi / Mehdi). Everyone else comes from Medi's one-tap confirmations (supabase name_labels, 021).
  * docs/js/names.js is the same matcher for the browser; tests/test_names.py + tests/test_names_parity.cjs pin parity.

Matching (identical in names.js)
  tokens: Arabic letter runs | Latin/Arabizi runs [A-Za-z0-9 accented '’]; hyphens split Latin tokens.
  Arabic norm = scripts/arabizi.arabic_norm (marks + tatweel dropped, أإآٱ->ا, ة->ه, ى->ي, ؤ->و, ئ->ي, ء dropped).
  Latin norm = NFKD, accents and apostrophes dropped, lower case. Latin articles il/el/al/l/ul are transparent.
  The first Arabic token may carry و ب ل ف ك ع (+ ال / لل): برام الله, بالقدس, للقدس, عالقدس.
  Tokens of one name must be separated by spaces / hyphens only. Longest match first (up to 4 tokens); places, countries
  and cities before people. Some Latin variants only match capitalised (Turkey, China) or in capitals (UAE, USA, UK).
"""
import argparse, datetime as dt, glob, hashlib, io, itertools, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DOCS = os.path.join(REPO, "docs")
DATA = os.path.join(DOCS, "data")
SRC_DIR = os.path.join(REPO, "data", "names-source")
SRC = os.path.join(SRC_DIR, "wikidata.json")
OUT = os.path.join(DATA, "names.json")
POSSIBLE = os.path.join(DATA, "possible-names.json")
LAYER_DIR = os.path.join(DATA, "lesson-names")
WORDS = os.path.join(DATA, "words.json")
VERSION = "2026-09-28"
SALT = "anees-names-v1|2026-09-28|public-salt"   # committed on purpose (see docstring)
MAXN = 4
LICENCE = ("Place names: Wikidata (https://www.wikidata.org), CC0 1.0 public domain dedication - no attribution required, "
           "credited here anyway. Arabizi/colloquial variants: hand-written by Anees for matching only (never displayed).")

# ------------------------------------------------------------------ normalisation (mirrored in docs/js/names.js)
AR_RUN = "ء-غـ-ٰٟ-ۓ"
LAT_RUN = "A-Za-z0-9À-ɏ'’"
TOKEN = re.compile("[" + AR_RUN + "]+|[" + LAT_RUN + "]+")
AR_TEST = re.compile("[ء-غف-يٱ-ۓ]")
MARKS = re.compile("[ً-ٰٟـ]")
LAT_MARKS = re.compile("[̀-ͯ]")
GAP_OK = re.compile(r"^[\s\-ـ]*$")
LAT_ART = {"il", "el", "al", "l", "ul"}
AR_PREFIXES = ("وبال", "وفال", "ولل", "وال", "بال", "فال", "عال", "لل", "وب", "ول", "وف", "و", "ب", "ل", "ف")
PERSON_PREFIXES = ("و", "ل")        # يا أمل / لأمل / وأمل; never ب ف (بابا, فامل) - a name must not hide inside a word


def ar_norm(s):
    s = MARKS.sub("", s or "")
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي"), ("ء", ""),
                 ("ک", "ك"), ("ی", "ي"), ("ۀ", "ه")):
        s = s.replace(a, b)
    return s


def lat_norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = LAT_MARKS.sub("", s).lower()
    return re.sub("['’ʼ`]", "", s)


def is_ar(tok):
    return bool(AR_TEST.search(tok or ""))


def tokens(text):
    """[(start, end, raw, 'ar'|'lat')] in text order."""
    return [(m.start(), m.end(), m.group(0), "ar" if is_ar(m.group(0)) else "lat") for m in TOKEN.finditer(text or "")]


def norm_tok(raw, sc):
    return ar_norm(raw) if sc == "ar" else lat_norm(raw)


def variant_key(v):
    """A listed variant -> its key tuple (Latin articles dropped)."""
    out = []
    for s, e, raw, sc in tokens(v):
        n = norm_tok(raw, sc)
        if not n or (sc == "lat" and n in LAT_ART):
            continue
        out.append(n)
    return tuple(out)


def variant_scripts(v):
    return tuple(sc for s, e, raw, sc in tokens(v) if not (sc == "lat" and lat_norm(raw) in LAT_ART))


def fp(key):
    """Salted SHA-256 fingerprint of a normalised token tuple (people's names are stored ONLY like this)."""
    if isinstance(key, str):
        key = variant_key(key)
    return hashlib.sha256((SALT + "|" + " ".join(key)).encode("utf-8")).hexdigest()[:32]


def ar_forms(n):
    """(form, letters consumed from the front) for the first Arabic token of a candidate: the token, then without its
    proclitics (و ب ل ف ك ع, with the article restored after بال / لل / عال)."""
    out = [(n, 0)]
    for p in AR_PREFIXES:
        if n.startswith(p) and len(n) - len(p) >= 2:
            rest = n[len(p):]
            if p.endswith("ال"):
                out.append(("ال" + rest, len(p) - 2))
            elif p.endswith("لل"):
                out.append(("ال" + rest, len(p) - 1))
            else:
                out.append((rest, len(p)))
    return out


def raw_offset(raw, k):
    """Offset in the raw Arabic token after k normalised letters (marks / tatweel skipped)."""
    if k <= 0:
        return 0
    seen = 0
    for i, ch in enumerate(raw):
        if MARKS.match(ch):
            continue
        seen += 1
        if seen == k:
            j = i + 1
            while j < len(raw) and MARKS.match(raw[j]):
                j += 1
            return j
    return len(raw)


# ------------------------------------------------------------------ matcher
class Names:
    """names.json -> matcher. find(text) -> [{s, e, text, kind, id?, en?, ar?, sub?, mixed?}] (non-overlapping, text order)."""

    def __init__(self, data=None):
        if data is None:
            data = json.load(io.open(OUT, encoding="utf-8"))
        self.data = data
        self.entries = data.get("entries") or []
        self.index = {}                         # key tuple -> (entry index, flag) flag 0 any case, 1 capitalised, 2 capitals
        for ei, e in enumerate(self.entries):
            for v in e.get("v") or []:
                self._add(variant_key(v), ei, 0)
            for v in e.get("cap") or []:
                self._add(variant_key(v), ei, 2 if v.upper() == v and re.search("[A-Z]", v) else 1)
            ars = [variant_key(v) for v in (e.get("v") or []) if all(sc == "ar" for sc in variant_scripts(v))]
            lats = [variant_key(v) for v in (e.get("v") or []) if all(sc == "lat" for sc in variant_scripts(v))]
            for a in ars:
                for l in lats:
                    if len(a) != len(l) or len(a) < 2 or len(a) > 3:
                        continue
                    for pick in itertools.product((0, 1), repeat=len(a)):
                        if 0 < sum(pick) < len(a):
                            self._add(tuple(l[i] if p else a[i] for i, p in enumerate(pick)), ei, 0)
        self.people = {}
        for p in data.get("people") or []:
            self.people[p["fp"]] = p

    def _add(self, key, ei, flag):
        if not key or len(key) > MAXN:
            return
        cur = self.index.get(key)
        if cur is None:
            self.index[key] = (ei, flag)
        elif cur[0] == ei and flag < cur[1]:
            self.index[key] = (ei, flag)

    @staticmethod
    def _case_ok(flag, raws):
        if flag == 0:
            return True
        for raw, sc in raws:
            if sc != "lat":
                continue
            letters = re.sub("[^A-Za-zÀ-ɏ]", "", raw)
            if not letters:
                continue
            if flag == 2 and letters.upper() != letters:
                return False
            if flag == 1 and not letters[0].isupper():
                return False
        return True

    def find(self, text):
        text = text or ""
        toks = tokens(text)
        content = [i for i, t in enumerate(toks) if not (t[3] == "lat" and lat_norm(t[2]) in LAT_ART)]
        norms = {i: norm_tok(toks[i][2], toks[i][3]) for i in content}
        out = []
        p = 0
        while p < len(content):
            best = None
            for n in range(min(MAXN, len(content) - p), 0, -1):
                idxs = content[p:p + n]
                if not self._adjacent(text, toks, idxs):
                    continue
                first = toks[idxs[0]]
                rest = tuple(norms[i] for i in idxs[1:])
                forms = ar_forms(norms[idxs[0]]) if first[3] == "ar" else [(norms[idxs[0]], 0)]
                raws = [(toks[i][2], toks[i][3]) for i in idxs]
                for form, k in forms:
                    key = (form,) + rest
                    hit = self.index.get(key)
                    if hit and self._case_ok(hit[1], raws):
                        best = (n, "entry", hit[0], k)
                        break
                if best:
                    break
                if n <= 3 and self.people and all(sc == "ar" or raw[:1].isupper() for raw, sc in raws):
                    pforms = [(f, k) for f, k in forms if k == 0 or (k == 1 and norms[idxs[0]][:1] in PERSON_PREFIXES)]
                    for form, k in pforms:
                        if fp((form,) + rest) in self.people:
                            best = (n, "person", None, k)
                            break
                if best:
                    break
            if not best:
                p += 1
                continue
            n, what, ei, k = best
            idxs = content[p:p + n]
            first = toks[idxs[0]]
            s = first[0] + (raw_offset(first[2], k) if first[3] == "ar" else 0)
            e = toks[idxs[-1]][1]
            if k == 0 and first[3] == "lat" and idxs[0] > 0:        # include a Latin article joined to it (il-Quds, al Quds)
                j = idxs[0] - 1
                pt = toks[j]
                if pt[3] == "lat" and lat_norm(pt[2]) in LAT_ART and GAP_OK.match(text[pt[1]:first[0]]) and \
                        (j == 0 or not (toks[j - 1][3] == "lat" and toks[j - 1][1] == pt[0] - 1 and text[pt[0] - 1] == "-")):
                    s = pt[0]
            scs = {toks[i][3] for i in idxs}
            sp = {"s": s, "e": e, "text": text[s:e]}
            if what == "entry":
                en = self.entries[ei]
                sp.update({"kind": en["kind"], "id": en["id"], "en": en.get("en"), "ar": en.get("ar")})
                if en.get("sub"):
                    sp["sub"] = en["sub"]
            else:
                sp["kind"] = "person"
            if len(scs) > 1:
                sp["mixed"] = True                     # the engine split one name across two scripts (رام Allah)
            out.append(sp)
            p += n
        return out

    @staticmethod
    def _adjacent(text, toks, idxs):
        for a, b in zip(idxs, idxs[1:]):
            for j in range(a, b):
                if not GAP_OK.match(text[toks[j][1]:toks[j + 1][0]]):
                    return False
            for j in range(a + 1, b):                  # only Latin articles may sit between two tokens of one name
                if not (toks[j][3] == "lat" and lat_norm(toks[j][2]) in LAT_ART):
                    return False
        return True

    def mask(self, text, repl="فلان"):
        """Text with every Arabic-script name replaced by a neutral placeholder noun (for the grammar detector), plus the
        [(placeholder start, original)] map so hits can be written back."""
        spans = [sp for sp in self.find(text) if is_ar(sp["text"])]
        if not spans:
            return text, []
        out, last, back = [], 0, []
        for sp in spans:
            out.append(text[last:sp["s"]])
            back.append(sp["text"])
            out.append(repl)
            last = sp["e"]
        out.append(text[last:])
        return "".join(out), back

    def keyterms(self, track="amal", limit=1000):
        """Scribe keyterms: names only, never vocabulary. Amal's track: every place, country and nationality; Medi's
        track (and a mixed file): places only (a country / nationality word on his side could hide his mistakes).
        People are fingerprints only, so no person keyterm is ever sent. Order = names.json priority; <= 50 chars."""
        out, seen = [], set()
        for e in self.entries:
            if track != "amal" and e["kind"] != "place":
                continue
            en = re.sub(r"\s*\([^)]*\)", "", e.get("en") or "").strip()
            en = re.sub(r"^the ", "", en)
            for v in [x for x in (e.get("v") or []) if is_ar(x)] + [en]:     # vetted variants only (المغرب = her word)
                k = ar_norm(v).replace(" ", "") if is_ar(v) else (v or "").lower()
                if not v or len(v) > 50 or k in seen or (is_ar(v) and MARKS.search(v)):
                    continue                                 # Arabizi variants are matching aids only: never sent (RULES S1)
                seen.add(k)
                out.append(v)
                if len(out) >= limit:
                    return out
        return out


_CACHE = {}


def load(path=OUT):
    if path not in _CACHE:
        _CACHE[path] = Names(json.load(io.open(path, encoding="utf-8")))
    return _CACHE[path]


def _sha(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        return ""


def names_sha(path=OUT):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        return None


# ------------------------------------------------------------------ seed (hand-written; Arabizi = matching only)
# (id, English, Wikidata QID or None, extra Arabic variants, Latin variants, sub)
SEED = [
    ("ramallah", "Ramallah", "Q158119", ["رام الله", "رامالله"], ["Ramallah", "Ram Allah", "Ramalla", "Ramala"], "levant"),
    ("bethlehem", "Bethlehem", "Q5776", ["بيت لحم", "بيتلحم"], ["Bethlehem", "Bait La7em", "Bait Lahem", "Bait Lahm", "Beit Lahm",
                                                                  "Beit Lahem", "Beit La7em", "Bet La7em", "Bet Lahem", "Beitlahem"], "levant"),
    ("jerusalem", "Jerusalem", "Q1218", ["القدس", "بيت المقدس"], ["Jerusalem", "il-Quds", "el-Quds", "Quds", "il-2ods", "il-Uds"], "levant"),
    ("nablus", "Nablus", "Q214178", ["نابلس"], ["Nablus", "Nables", "Nabulus"], "levant"),
    ("haifa", "Haifa", "Q41621", ["حيفا"], ["Haifa", "Hayfa", "7eifa", "7aifa", "7ayfa"], "levant"),
    ("jaffa", "Jaffa", "Q180294", ["يافا"], ["Jaffa", "Yafa", "Yaffa", "Yafo"], "levant"),
    ("gaza", "Gaza", "Q47492", ["غزة", "غزه"], ["Gaza", "Ghazza", "Ghaza", "8azza", "8aza", "Ghazze"], "levant"),
    ("jenin", "Jenin", None, ["جنين"], ["Jenin", "Jinin", "Janin"], "levant"),
    ("hebron", "Hebron", "Q168225", ["الخليل"], ["Hebron", "il-Khalil", "el-Khalil", "il-5alil", "Khalil"], "levant"),
    ("akka", "Akka (Acre)", None, ["عكا", "عكّا"], ["Akka", "3akka", "3aka", "Acre", "Akko"], "levant"),
    ("nazareth", "Nazareth", "Q430776", ["الناصرة", "الناصره", "ناصرة"], ["Nazareth", "Naasra", "Nasra", "Na9ra", "in-Nasra", "Nasira"], "levant"),
    ("tulkarem", "Tulkarem", "Q985531", ["طولكرم", "طول كرم"], ["Tulkarem", "Tulkarm", "6ulkarem", "Tulkarim"], "levant"),
    ("qalqilya", "Qalqilya", "Q623159", ["قلقيلية", "قلقيليه"], ["Qalqilya", "Qalqilia", "Qalqiliya", "2al2ilya"], "levant"),
    ("jericho", "Jericho (Ariha)", "Q5687", ["أريحا", "اريحا"], ["Jericho", "Ariha", "Ari7a", "Ari7ah"], "levant"),
    ("amman", "Amman", "Q3805", ["عمان", "عمّان"], ["Amman", "3amman", "3aman"], "levant"),
    ("beirut", "Beirut", "Q3820", ["بيروت"], ["Beirut", "Bairut", "Beyrouth", "Bayrut", "Beirout"], "levant"),
    ("damascus", "Damascus (ish-Sham)", "Q3766", ["دمشق", "الشام"], ["Damascus", "ish-Sham", "Dimashq", "Dimasheq", "Sham"], "levant"),
    ("cairo", "Cairo", "Q85", ["القاهرة", "القاهره"], ["Cairo", "il-Qahira", "il-2ahira"], "levant"),
    ("aleppo", "Aleppo", "Q41183", ["حلب"], ["Aleppo", "7alab", "Halab"], "levant"),
    ("homs", "Homs", "Q131301", ["حمص"], ["Homs", "7oms"], "levant"),
    ("hama", "Hama", "Q173545", ["حماة"], ["Hama"], "levant"),
    ("latakia", "Latakia", "Q200030", ["اللاذقية", "اللاذقيه"], ["Latakia", "Lattakia", "Lazqiyye"], "levant"),
    ("tartus", "Tartus", "Q174916", ["طرطوس"], ["Tartus", "Tartous"], "levant"),
    ("tripoli", "Tripoli", None, ["طرابلس"], ["Tripoli", "Trablus", "Tarablus", "6arablus"], "levant"),
    ("sidon", "Sidon (Saida)", "Q163490", ["صيدا"], ["Sidon", "Saida", "Sayda", "9aida"], "levant"),
    ("tyre", "Tyre (Sur)", None, [], ["Tyre"], "levant"),          # صور = pictures in every lesson
    ("byblos", "Byblos (Jbeil)", "Q173532", ["جبيل"], ["Byblos", "Jbeil", "Jbail"], "levant"),
    ("baalbek", "Baalbek", "Q178835", ["بعلبك"], ["Baalbek", "Ba3labak", "Baalbak"], "levant"),
    ("jounieh", "Jounieh", "Q26155", ["جونيه", "جونية"], ["Jounieh", "Junieh"], "levant"),
    ("irbid", "Irbid", "Q194165", ["إربد", "اربد"], ["Irbid", "Irbed", "Erbed"], "levant"),
    ("zarqa", "Zarqa", "Q148062", ["الزرقاء"], ["Zarqa", "iz-Zar2a"], "levant"),
    ("madaba", "Madaba", "Q1683958", ["مادبا", "مأدبا"], ["Madaba", "Madaba"], "levant"),
    ("jerash", "Jerash", "Q31565", ["جرش"], ["Jerash", "Jarash"], "levant"),
    ("petra", "Petra", "Q5788", ["البتراء", "البترا"], ["Petra", "il-Batra"], "levant"),
    ("aqaba", "Aqaba", "Q180522", ["العقبة", "العقبه"], ["Aqaba", "il-3a2aba", "Akaba"], "levant"),
    ("tiberias", "Tiberias", "Q151920", ["طبريا", "طبرية"], ["Tiberias", "Tabariyya", "Tabaria", "6abariyya"], "levant"),
    ("safad", "Safad", "Q188336", ["صفد"], ["Safad", "Safed", "9afad"], "levant"),
    ("lod", "Lydd (Lod)", "Q207540", ["اللد"], ["Lydd", "Lydda", "Lod", "il-Lidd"], "levant"),
    ("ramla", "Ramla", "Q221447", ["الرملة", "الرمله"], ["Ramla", "Ramle", "ir-Ramle"], "levant"),
    ("beit-sahour", "Beit Sahour", "Q803990", ["بيت ساحور"], ["Beit Sahour", "Bait Sa7ur", "Beit Sa7our", "Beit Sahur"], "levant"),
    ("beit-jala", "Beit Jala", None, ["بيت جالا"], ["Beit Jala", "Bait Jala"], "levant"),
    ("tel-aviv", "Tel Aviv", "Q33935", ["تل أبيب", "تل ابيب", "تل الربيع"], ["Tel Aviv", "Tel Abib"], "levant"),
    ("khan-yunis", "Khan Yunis", "Q309348", ["خان يونس", "خانيونس"], ["Khan Yunis", "Khan Younis", "5an Yunis"], "levant"),
    ("rafah", "Rafah", "Q172343", ["رفح"], ["Rafah", "Rafa7"], "levant"),
    ("umm-al-fahm", "Umm al-Fahm", "Q168245", ["أم الفحم", "ام الفحم"], ["Umm al-Fahm", "Umm il-Fa7em"], "levant"),
    ("dead-sea", "the Dead Sea", "Q23883", ["البحر الميت"], ["Dead Sea", "il-Ba7r il-Mayyit", "il-Bahr il-Mayyet"], "region"),
    ("galilee", "Galilee", "Q83241", ["الجليل"], ["Galilee", "il-Jalil"], "region"),
    ("west-bank", "the West Bank", "Q36678", ["الضفة الغربية", "الضفة", "الضفه"], ["West Bank", "i9-9iffe", "id-Diffe", "Diffe"], "region"),
    ("gaza-strip", "the Gaza Strip", "Q39760", ["قطاع غزة", "قطاع غزه"], ["Gaza Strip", "2i6a3 Ghazza"], "region"),
    ("mecca", "Mecca", "Q5806", ["مكة", "مكة المكرمة", "مكه"], ["Mecca", "Makka", "Makkah"], "levant"),
    ("medina", "Medina", "Q35484", ["المدينة المنورة"], ["Medina", "il-Madina il-Munawwara"], "levant"),
    ("dubai", "Dubai", "Q612", ["دبي"], ["Dubai", "Dbai", "Dubay"], "levant"),
    ("abu-dhabi", "Abu Dhabi", "Q1519", ["أبو ظبي", "ابو ظبي", "أبوظبي"], ["Abu Dhabi", "Abu Zabi", "Abu Thabi"], "levant"),
    ("doha", "Doha", "Q3861", ["الدوحة", "الدوحه"], ["Doha", "id-Do7a"], "levant"),
    ("istanbul", "Istanbul", "Q406", ["إسطنبول", "اسطنبول"], ["Istanbul", "Stambul", "Istanbool"], "levant"),
    ("tehran", "Tehran", "Q3616", ["طهران"], ["Tehran", "Teheran"], "levant"),
    ("toronto", "Toronto", "Q172", ["تورونتو", "تورنتو"], ["Toronto"], "levant"),
    ("middle-east", "the Middle East", None, ["الشرق الأوسط", "الشرق الاوسط"], ["Middle East", "ish-Sharq il-Awsa6"], "region"),
]
SEED_QIDS = {q for _, _, q, _, _, _ in SEED if q}

# Countries: extra matching variants (Arabizi + colloquial), keyed by ISO code.
COUNTRY_EXTRA = {
    "PS": (["فلسطين"], ["Palestine", "Falastin", "Filastin", "Falas6in", "Filas6in", "Falasteen"]),
    "JO": (["الأردن", "الاردن"], ["Jordan", "il-Urdun", "l-Urdon", "Urdon", "Urdun"]),
    "LB": (["لبنان"], ["Lebanon", "Lubnan", "Libnan", "Lebnan"]),
    "SY": (["سوريا", "سورية", "سوريه"], ["Syria", "Surya", "Suria", "Souria", "Suriya"]),
    "EG": (["مصر"], ["Egypt", "Masr", "Ma9r", "Misr"]),
    "IQ": (["العراق"], ["Iraq", "il-3ira2", "3ira2", "3iraq", "Ira2"]),
    "SA": (["السعودية", "السعوديه"], ["Saudi Arabia", "KSA", "Saudi", "is-Sa3udiyye", "Sa3udiyye", "Sa3oudiyye"]),
    "AE": (["الإمارات", "الامارات"], ["UAE", "Emirates", "il-Imarat", "Imarat", "Emarat"]),
    "QA": (["قطر"], ["Qatar", "Qa6ar", "2a6ar"]),
    "KW": (["الكويت"], ["Kuwait", "il-Kweit", "Kweit"]),
    "IR": (["إيران", "ايران"], ["Iran", "Iraan"]),
    "TR": (["تركيا"], ["Turkya", "Turkiya", "Turkiye"]),
    "US": (["أمريكا", "أميركا", "امريكا", "اميركا"], ["America", "Amrika", "Amerka", "Amreeka", "Amrica", "Amereeka", "United States", "USA", "US"]),
    "DE": (["ألمانيا", "المانيا"], ["Germany", "Almanya", "Almania"]),
    "IN": (["الهند"], ["India", "il-Hind"]),
    "FR": (["فرنسا"], ["France", "Fransa", "Faransa"]),
    "GB": (["بريطانيا", "إنجلترا", "انجلترا", "انكلترا"], ["Britain", "England", "Bri6anya", "Ingiltra", "Inglatera", "United Kingdom", "UK"]),
    "IT": (["إيطاليا", "ايطاليا"], ["Italy", "Italia", "Italya", "I6alya"]),
    "ES": (["إسبانيا", "اسبانيا"], ["Spain", "Isbanya", "Esbanya"]),
    "CN": (["الصين"], []),
    "JP": (["اليابان"], ["Japan", "il-Yaban", "Yaban"]),
    "RU": (["روسيا"], ["Russia", "Rusya", "Rousya"]),
    "CA": (["كندا"], ["Canada", "Kanada"]),
    "MA": (["المغرب"], ["Morocco"]),
    "TN": (["تونس"], ["Tunisia", "Tunis"]),
    "DZ": (["الجزائر"], ["Algeria", "il-Jaza2ir", "Jaza2er"]),
    "LY": (["ليبيا"], ["Libya", "Libia"]),
    "SD": (["السودان"], ["Sudan", "is-Sudan"]),
    "YE": (["اليمن"], ["Yemen", "il-Yaman", "Yaman"]),
    "OM": (["عمان", "سلطنة عمان"], ["Oman", "3uman"]),
    "BH": (["البحرين"], ["Bahrain", "il-Ba7rein", "Ba7rain"]),
    "PK": (["باكستان"], ["Pakistan", "Bakistan"]),
    "AF": (["أفغانستان", "افغانستان"], ["Afghanistan"]),
    "KR": (["كوريا"], ["Korea", "Kurya"]),
    "BR": (["البرازيل"], ["Brazil", "il-Brazil"]),
    "MX": (["المكسيك"], ["Mexico", "il-Mexik"]),
    "GR": (["اليونان"], ["Greece", "il-Yunan"]),
    "NL": (["هولندا"], ["Netherlands", "Holland", "Holanda"]),
    "SE": (["السويد"], ["Sweden", "is-Swed"]),
    "AU": (["أستراليا", "استراليا"], ["Australia", "Ostralya", "Ustralya"]),
    "IL": (["إسرائيل", "اسرائيل"], ["Israel", "Isra2il", "Isra2eel"]),
    "CY": (["قبرص"], ["Cyprus", "2ubru9", "Qubrus"]),
}
# Latin variants that only count when capitalised: lower case they are an English word, a person's name or an Arabizi word.
CAP_ONLY = {"turkey", "china", "chad", "jordan", "georgia", "guinea", "niger", "cuba", "wales", "reading", "nice", "split",
            "mobile", "bath", "sale", "worms", "tours", "male", "mali", "acre", "tyre", "petra", "sofia", "victoria", "florence",
            "lincoln", "kingston", "orange", "hamilton", "columbus", "phoenix", "austin", "charlotte", "jackson", "santiago",
            "sham", "hama", "khalil", "hind", "aman", "masr", "misr", "medina", "ramla", "ramle", "nasra", "saida", "homs", "doha",
            "diffe", "makka", "saudi", "salt", "lod", "akka", "urdun", "yaban", "yaman", "tunis", "lubnan", "surya", "suria",
            "imarat", "kweit", "hama", "halab", "sur"}
ALL_CAPS_OK = {"UAE", "USA", "US", "UK", "KSA"}
WORLD = ""     # marks a Latin label that came from Wikidata (one word -> must be capitalised in the text)
# Everyday words that happen to spell a place and are too common in the lessons to ever mean it.
NEVER = {ar_norm(w) for w in "طيبة المدينة مدينة البلد بلد بكة الوطن صور ابا مالي كراجي يمني بنين".split()} | {
    "sur", "ain", "un", "us", "as", "is", "it", "id", "in", "on", "of", "or", "an", "am", "ma", "la", "fi", "me", "no", "so",
    "to", "do", "go", "be", "he", "we", "ok", "hi", "ha", "bat", "man", "van", "ada", "ali", "per", "aba", "benin", "hang", "bahamas"}

# Nationalities (Arabic masculine, Arabizi masculine, English). Feminine / plural / article forms are generated.
NATIONALITIES = [
    ("PS", "فلسطيني", "Falastini", "Palestinian"), ("JO", "أردني", "Urduni", "Jordanian"), ("LB", "لبناني", "Lubnani", "Lebanese"),
    ("EG", "مصري", "Masri", "Egyptian"), ("IQ", "عراقي", "3ira2i", "Iraqi"), ("SA", "سعودي", "Sa3udi", "Saudi"),
    ("AE", "إماراتي", "Imarati", "Emirati"), ("QA", "قطري", "2a6ari", "Qatari"), ("KW", "كويتي", "Kweiti", "Kuwaiti"),
    ("IR", "إيراني", "Irani", "Iranian"), ("US", "أمريكي", "Amriki", "American"), ("DE", "ألماني", "Almani", "German"),
    ("IN", "هندي", "Hindi", "Indian"), ("FR", "فرنسي", "Faransi", "French"), ("FR", "فرنساوي", "Fransawi", "French"),
    ("IT", "إيطالي", "I6ali", "Italian"), ("ES", "إسباني", "Isbani", "Spanish"), ("CN", "صيني", "9ini", "Chinese"),
    ("JP", "ياباني", "Yabani", "Japanese"), ("RU", "روسي", "Rusi", "Russian"), ("CA", "كندي", "Kanadi", "Canadian"),
    ("TR", "تركي", "Turki", "Turkish"), ("MA", "مغربي", "Ma8ribi", "Moroccan"), ("TN", "تونسي", "Tunsi", "Tunisian"),
    ("DZ", "جزائري", "Jaza2iri", "Algerian"), ("LY", "ليبي", "Libi", "Libyan"), ("SD", "سوداني", "Sudani", "Sudanese"),
    ("PK", "باكستاني", "Pakistani", "Pakistani"), ("AF", "أفغاني", "Afghani", "Afghan"),
    ("KR", "كوري", "Kuri", "Korean"), ("GR", "يوناني", "Yunani", "Greek"), ("GB", "بريطاني", "Bri6ani", "British"),
    ("GB", "إنجليزي", None, "English (person)"), ("IL", "إسرائيلي", "Isra2ili", "Israeli"), ("SY", "سوري", None, "Syrian"),
    ("BR", "برازيلي", "Brazili", "Brazilian"), ("MX", "مكسيكي", "Meksiki", "Mexican"), ("AU", "أسترالي", "Ostrali", "Australian"),
    ("OM", "عماني", "3umani", "Omani"), ("BH", "بحريني", "Ba7reini", "Bahraini"),
]
# سوري is "sorry" in the transcripts and إنجليزي is the language: kept out of matching (listed so the report can say why).
NAT_SKIP_AR = {ar_norm("سوري"), ar_norm("إنجليزي")}

PEOPLE_SEED = ["Amal", "أمل", "Medi", "ميدي", "Mahdi", "Mehdi", "مهدي"]


# ------------------------------------------------------------------ fetch (once) + build
QUERIES = {
    "countries": """SELECT ?c ?en ?ar ?iso (GROUP_CONCAT(DISTINCT ?enAlt; separator="|") AS ?enAlts) (GROUP_CONCAT(DISTINCT ?arAlt; separator="|") AS ?arAlts) (GROUP_CONCAT(DISTINCT ?cap; separator="|") AS ?caps) (MAX(?pop) AS ?p) WHERE {
  { ?c wdt:P31 wd:Q3624078 } UNION { VALUES ?c { wd:Q219060 } }
  FILTER NOT EXISTS { ?c wdt:P576 ?end }
  OPTIONAL { ?c wdt:P297 ?iso } OPTIONAL { ?c wdt:P1082 ?pop } OPTIONAL { ?c wdt:P36 ?cap }
  OPTIONAL { ?c rdfs:label ?en FILTER(LANG(?en)="en") } OPTIONAL { ?c rdfs:label ?ar FILTER(LANG(?ar)="ar") }
  OPTIONAL { ?c skos:altLabel ?enAlt FILTER(LANG(?enAlt)="en") } OPTIONAL { ?c skos:altLabel ?arAlt FILTER(LANG(?arAlt)="ar") }
} GROUP BY ?c ?en ?ar ?iso""",
    "cities": """SELECT ?c ?en ?ar (MAX(?pop) AS ?p) (SAMPLE(?cc) AS ?country) (GROUP_CONCAT(DISTINCT ?enAlt; separator="|") AS ?enAlts) (GROUP_CONCAT(DISTINCT ?arAlt; separator="|") AS ?arAlts) WHERE {
  ?c wdt:P1082 ?pop . FILTER(?pop >= 1000000)
  ?c wdt:P31/wdt:P279* wd:Q515 .
  FILTER NOT EXISTS { ?c wdt:P576 ?end }
  OPTIONAL { ?c wdt:P17 ?cc }
  OPTIONAL { ?c rdfs:label ?en FILTER(LANG(?en)="en") } OPTIONAL { ?c rdfs:label ?ar FILTER(LANG(?ar)="ar") }
  OPTIONAL { ?c skos:altLabel ?enAlt FILTER(LANG(?enAlt)="en") } OPTIONAL { ?c skos:altLabel ?arAlt FILTER(LANG(?arAlt)="ar") }
} GROUP BY ?c ?en ?ar""",
    "capitals": """SELECT ?c ?en ?ar (SAMPLE(?cc) AS ?country) (MAX(?pop) AS ?p) (GROUP_CONCAT(DISTINCT ?enAlt; separator="|") AS ?enAlts) (GROUP_CONCAT(DISTINCT ?arAlt; separator="|") AS ?arAlts) WHERE {
  { ?cc wdt:P31 wd:Q3624078 } UNION { VALUES ?cc { wd:Q219060 } }
  ?cc wdt:P36 ?c . OPTIONAL { ?c wdt:P1082 ?pop }
  OPTIONAL { ?c rdfs:label ?en FILTER(LANG(?en)="en") } OPTIONAL { ?c rdfs:label ?ar FILTER(LANG(?ar)="ar") }
  OPTIONAL { ?c skos:altLabel ?enAlt FILTER(LANG(?enAlt)="en") } OPTIONAL { ?c skos:altLabel ?arAlt FILTER(LANG(?arAlt)="ar") }
} GROUP BY ?c ?en ?ar""",
    "seed": """SELECT ?c ?en ?ar (GROUP_CONCAT(DISTINCT ?enAlt; separator="|") AS ?enAlts) (GROUP_CONCAT(DISTINCT ?arAlt; separator="|") AS ?arAlts) WHERE {
  VALUES ?c { %s }
  OPTIONAL { ?c rdfs:label ?en FILTER(LANG(?en)="en") } OPTIONAL { ?c rdfs:label ?ar FILTER(LANG(?ar)="ar") }
  OPTIONAL { ?c skos:altLabel ?enAlt FILTER(LANG(?enAlt)="en") } OPTIONAL { ?c skos:altLabel ?arAlt FILTER(LANG(?arAlt)="ar") }
} GROUP BY ?c ?en ?ar""",
}


def fetch():
    import requests
    out = {"source": "Wikidata Query Service (https://query.wikidata.org)", "licence": "CC0 1.0", "fetched": dt.date.today().isoformat(),
           "queries": {}}
    for name, q in QUERIES.items():
        if name == "seed":
            q = q % " ".join("wd:" + x for x in sorted(SEED_QIDS))
        r = requests.get("https://query.wikidata.org/sparql", params={"query": q}, timeout=300,
                         headers={"Accept": "application/sparql-results+json", "User-Agent": "anees-names/1.0 (https://github.com/thenatanzi/anees)"})
        r.raise_for_status()
        rows = []
        for b in r.json()["results"]["bindings"]:
            g = lambda k: (b.get(k) or {}).get("value")
            row = {"q": g("c").rsplit("/", 1)[-1], "en": g("en"), "ar": g("ar")}
            for k, kk in (("enAlts", "en_alt"), ("arAlts", "ar_alt")):
                if g(k):
                    row[kk] = [x for x in g(k).split("|") if x]
            if g("iso"):
                row["iso"] = g("iso")
            if g("p"):
                row["pop"] = int(float(g("p")))
            if g("country"):
                row["cc"] = g("country").rsplit("/", 1)[-1]
            if g("caps"):
                row["caps"] = [x.rsplit("/", 1)[-1] for x in g("caps").split("|")]
            rows.append(row)
        out["queries"][name] = {"sparql": q, "rows": sorted(rows, key=lambda x: x["q"])}
        print(name, len(rows))
    os.makedirs(SRC_DIR, exist_ok=True)
    io.open(SRC, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=0))
    print("wrote", SRC)


def _similar(a, b):
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


def _clean_alts(main, alts, script):
    """Keep only spelling variants of the main label (no 'city of', governorates, nicknames, ancient names)."""
    out = []
    for a in alts or []:
        if not a or len(a) > 40 or re.search(r"[(),،/:]|\d", a):
            continue
        if script == "ar":
            if not is_ar(a) or re.search("مدينة|محافظة|منطقة|حي |قضاء|ولاية|إمارة|جمهورية|مملكة|دولة|بلدية", a):
                continue
            if main and _similar(ar_norm(a), ar_norm(main)) < 0.75:
                continue
        else:
            if is_ar(a) or not re.fullmatch(r"[A-Za-zÀ-ɏ' \-.]+", a) or len(a.split()) > 3:
                continue
            if re.search(r"\b(?:City of|Republic|Kingdom|State of|Federation|Commonwealth|Municipality|Governorate|Province)\b", a):
                continue
            if a.isupper() and a not in ALL_CAPS_OK:
                continue                                     # ISO codes (PSE, ISR) are not how anyone says it
            if main and _similar(lat_norm(a), lat_norm(main)) < 0.6 and a not in ALL_CAPS_OK:
                continue
        out.append(a)
    return out


def _vocab():
    """Amal's words: whole Arabic entries (arabic_norm, each '/' part) and whole Latin entries (loose)."""
    sys.path.insert(0, HERE)
    from arabizi import loose
    items = json.load(io.open(WORDS, encoding="utf-8"))["items"]
    ar, lat = {}, {}
    for w in items:
        for part in re.split(r"\s*/\s*", w.get("arabic") or ""):
            part = re.sub(r"\([^)]*\)", " ", part).strip()
            k = variant_key(part)
            if k:
                ar.setdefault(k, w["key"])
        for f in [w.get("arabizi")] + list(w.get("aliases") or []):
            for part in re.split(r"\s*/\s*", f or ""):
                part = re.sub(r"\([^)]*\)", " ", part).strip()
                if part:
                    lat.setdefault(loose(part), w["key"])
    return ar, lat, loose


def _labels():
    """Medi's confirmations from supabase name_labels (migration 021). Missing table / offline -> []. Latest row per
    candidate wins."""
    try:
        import requests
        cfg = io.open(os.path.join(DOCS, "js", "config.js"), encoding="utf-8").read()
        url = re.search(r"url:\s*'([^']+)'", cfg).group(1)
        anon = re.search(r"anon:\s*'([^']+)'", cfg).group(1)
        r = requests.get(url + "/rest/v1/name_labels?select=id,cand_fp,label,kind,text,ts,created_at&order=ts.asc&limit=5000",
                         headers={"apikey": anon, "Authorization": "Bearer " + anon}, timeout=20)
        if r.status_code != 200:
            return [], f"name_labels unavailable (HTTP {r.status_code}: migration 021 not applied yet?)"
        latest = {}
        for row in r.json():
            latest[row["cand_fp"]] = row
        return list(latest.values()), f"{len(latest)} confirmed labels"
    except Exception as e:  # offline is fine
        return [], f"name_labels not read ({type(e).__name__})"


def build(labels=None, write=True):
    src = json.load(io.open(SRC, encoding="utf-8"))
    Q = {k: v["rows"] for k, v in src["queries"].items()}
    vocab_ar, vocab_lat, loose = _vocab()
    by_q = {}
    for k in ("seed", "countries", "capitals", "cities"):
        for r in Q.get(k, []):
            by_q.setdefault(r["q"], r)
    iso_of = {r["q"]: r.get("iso") for r in Q["countries"]}
    entries, vocab_hits, dropped = [], [], []
    seen_ids = set()

    def lat_ok(v, e):
        n = variant_key(v)
        if v.isupper() and v in ALL_CAPS_OK:
            return True
        if not n or any(len(x) < 3 for x in n) or (len(n) == 1 and n[0] in NEVER):
            dropped.append({"id": e["id"], "v": v, "why": "too short / everyday word"}); return False
        if len(n) == 1 and loose(v) in vocab_lat:
            dropped.append({"id": e["id"], "v": v, "why": "her word " + vocab_lat[loose(v)]}); return False
        return True

    def ar_ok(v, e):
        n = variant_key(v)
        if not n or (len(n) == 1 and len(n[0]) < 3) or (len(n) == 1 and n[0] in NEVER):
            dropped.append({"id": e["id"], "v": v, "why": "too short / everyday word"}); return False
        if n in vocab_ar:
            dropped.append({"id": e["id"], "v": v, "why": "her word " + vocab_ar[n]}); return False
        return True

    def add(e, ars, lats):
        v, cap = [], []
        for a in ars:
            if a and a not in v and ar_ok(a, e):
                v.append(a)
        for l in lats:
            world = l.startswith(WORLD)
            l = l[len(WORLD):] if world else l
            if not l or l in v or l in cap:
                continue
            if not lat_ok(l, e):
                continue
            key = variant_key(l)
            if (world and len(key) == 1) or (len(key) == 1 and key[0] in CAP_ONLY) or (l.isupper() and len(l) <= 4) or \
                    (len(key) == 1 and key[0] in EN_COMMON):
                cap.append(l)
            else:
                v.append(l)
        if not v and not cap:
            return
        e["v"] = v
        if cap:
            e["cap"] = cap
        if e["id"] in seen_ids:
            e["id"] = e["id"] + "-" + str(len(entries))
        seen_ids.add(e["id"])
        entries.append(e)

    # 1 Levant / Arab-world seed (Arabic label + spelling variants from Wikidata, matching variants by hand)
    for sid, en, q, ar_extra, lat, sub in SEED:
        r = by_q.get(q) or {}
        ar_main = ar_extra[0] if ar_extra else ("صور" if sid == "tyre" else r.get("ar"))
        ars = list(ar_extra) + ([r["ar"]] if r.get("ar") and "(" not in r["ar"] else []) + _clean_alts(ar_main, r.get("ar_alt"), "ar")
        lats = list(lat) + ([r["en"]] if r.get("en") else [])
        add({"id": sid, "kind": "place", "sub": sub, "en": en, "ar": ar_main, **({"q": q} if q else {})}, ars, lats)

    # 2 countries (+ decision 3: a country whose word is on her list stays vocab)
    countries = sorted([r for r in Q["countries"] if r.get("en")], key=lambda r: -(r.get("pop") or 0))
    for r in countries:
        iso = r.get("iso") or r["q"]
        extra_ar, extra_lat = COUNTRY_EXTRA.get(iso, ([], []))
        ars = list(extra_ar) + ([r["ar"]] if r.get("ar") else []) + _clean_alts(r.get("ar"), r.get("ar_alt"), "ar")
        en_main = {"PS": "Palestine", "US": "America (USA)", "GB": "Britain (UK)", "CN": "China", "KR": "Korea",
                   "TR": "Turkey"}.get(iso, r["en"])
        lats = list(extra_lat) + [WORLD + l for l in [r["en"]] + _clean_alts(r["en"], r.get("en_alt"), "lat")]
        if iso == "TR":
            lats.append("Turkey")
        if iso == "CN":
            lats.append("China")
        ar_main = extra_ar[0] if extra_ar else r.get("ar")
        vk = [a for a in ars if variant_key(a) in vocab_ar]
        if vk:                        # her word stays vocab (the variant is dropped below); the other spellings stay a name
            vocab_hits.append({"id": "c-" + iso.lower(), "en": en_main, "kind": "country", "ar": vk[0], "word_key": vocab_ar[variant_key(vk[0])]})
        add({"id": "c-" + iso.lower(), "kind": "country", "en": en_main, "ar": ar_main, "q": r["q"], "cc": iso}, ars, lats)

    # 3 nationalities (Arabic masc / fem / plural / with article; Arabizi masc + fem for matching)
    for iso, ar, az, en in NATIONALITIES:
        n = ar_norm(ar)
        forms_ar = [ar, ar + "ة", ar + "ه", ar + "ين", "ال" + ar, "ال" + ar + "ة", "ال" + ar + "ين"]
        if n in NAT_SKIP_AR:
            dropped.append({"id": "n-" + iso.lower(), "v": ar, "why": "everyday word in the transcripts (sorry / the English language)"})
            continue
        if (n,) in vocab_ar or (az and loose(az) in vocab_lat):
            vocab_hits.append({"id": "n-" + iso.lower(), "en": en, "kind": "nationality", "ar": ar, "arabizi": az,
                               "word_key": vocab_ar.get((n,)) or vocab_lat.get(loose(az or ""))})
            continue
        lats = [az, az + "yye", az + "yyeh", az + "yya"] if az else []
        add({"id": "n-" + re.sub(r"[^a-z]+", "-", en.lower()).strip("-"), "kind": "country", "sub": "nationality", "en": en, "ar": ar, "cc": iso},
            forms_ar, lats + [en])

    # 4 capitals + cities >= 1M (Arabic label + close spelling variants; English label + close variants)
    done = {e.get("q") for e in entries}
    caps = {c for r in Q["countries"] for c in r.get("caps") or []}
    rows = [dict(r, sub="capital") for r in Q["capitals"]] + [dict(r, sub="city") for r in Q["cities"]]
    rows.sort(key=lambda r: (r["sub"] != "capital", -(r.get("pop") or 0)))
    for r in rows:
        if r["q"] in done or not r.get("en") or not r.get("ar"):
            continue
        if r["sub"] == "capital" and r["q"] not in caps:
            continue
        done.add(r["q"])
        ars = [a for a in [r["ar"]] if "(" not in a]         # world cities: the Arabic label only (alt spellings collide: كراجي)
        lats = [r["en"]] + _clean_alts(r["en"], r.get("en_alt"), "lat")
        lats = [WORLD + l for l in lats]
        slug = re.sub(r"[^a-z0-9]+", "-", lat_norm(r["en"])).strip("-")
        add({"id": slug, "kind": "place", "sub": r["sub"], "en": r["en"], "ar": ar_norm(r["ar"]) if MARKS.search(r["ar"]) else r["ar"],
             "q": r["q"], **({"cc": iso_of.get(r.get("cc"))} if iso_of.get(r.get("cc")) else {}), **({"pop": r["pop"]} if r.get("pop") else {})},
            ars, lats)

    # 5 confirmed labels (Medi's one-tap answers): places / other as text, people as fingerprints only
    labels, label_note = (labels, "given") if labels is not None else _labels()
    people = [{"fp": fp(p), "src": "seed"} for p in PEOPLE_SEED]
    not_names = []
    for row in labels:
        if row.get("label") == "not_name":
            not_names.append(row["cand_fp"])
        elif row.get("label") == "name" and row.get("kind") == "person":
            people.append({"fp": row["cand_fp"], "src": "confirmed"})
        elif row.get("label") == "name" and row.get("text"):
            t = row["text"].strip()
            add({"id": "x-" + row["cand_fp"][:10], "kind": row.get("kind") if row.get("kind") in ("place", "country", "other") else "other",
                 "sub": "confirmed", "en": None if is_ar(t) else t, "ar": t if is_ar(t) else None}, [t] if is_ar(t) else [], [] if is_ar(t) else [t])
    ppl = {}
    for p in people:
        ppl.setdefault(p["fp"], p)
    counts = Counter((e["kind"], e.get("sub")) for e in entries)
    out = {
        "version": VERSION, "built_from": {"words_json_sha": _sha(WORDS)[:16], "source_fetched": src.get("fetched")},
        "licence": LICENCE, "source": {"file": "data/names-source/wikidata.json", "fetched": src.get("fetched"), "licence": src.get("licence")},
        "salt": SALT,
        "how": "Matched before Amal's words, longest first (scripts/names.py = docs/js/names.js). v = any case; cap = Latin "
               "forms that must be capitalised (all-caps forms must be in capitals). People: salted sha256 fingerprints only.",
        "stats": {"places": sum(v for (k, s), v in counts.items() if k == "place" and s in ("levant", "region")),
                  "countries": counts[("country", None)], "nationalities": counts[("country", "nationality")],
                  "capitals": counts[("place", "capital")], "cities": counts[("place", "city")],
                  "confirmed": sum(v for (k, s), v in counts.items() if s == "confirmed"),
                  "people_fingerprints": len(ppl), "variants": sum(len(e["v"]) + len(e.get("cap") or []) for e in entries),
                  "labels": label_note},
        "vocab": vocab_hits,
        "not_names": sorted(set(not_names)),
        "people": list(ppl.values()),
        "entries": entries,
        "dropped": dropped,
    }
    if write:
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
        _CACHE.pop(OUT, None)
        print("wrote", OUT, json.dumps(out["stats"], ensure_ascii=False))
    return out


EN_COMMON = {"turkey", "china", "chad", "jordan", "georgia", "guinea", "niger", "reading", "nice", "split", "mobile", "bath"}


# ------------------------------------------------------------------ lesson layer (S2: derived, never edits a transcript)
def lesson_dates():
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(DATA, "lessons", "20??-??-??.json")))


def layer(date, nm=None, write=True):
    """docs/data/lesson-names/<date>.json (outside docs/data/lessons/ so no lesson glob picks it up): every name span on the lesson's turns (turn index, char offsets into the turn's
    text exactly as recorded, kind, canonical English + Arabic). mixed = the engine split one name over two scripts."""
    nm = nm or load()
    doc = json.load(io.open(os.path.join(DATA, "lessons", date + ".json"), encoding="utf-8"))
    spans = []
    for i, t in enumerate(doc.get("turns") or []):
        for sp in nm.find(t.get("text") or ""):
            row = {"i": i, "t": t.get("t"), "who": t.get("who"), **sp}
            if t.get("who") == "chat":
                row["typed_by"] = t.get("typed_by") or "Amal"
            spans.append(row)
    out = {"date": date, "version": VERSION, "names_sha": (names_sha() or "")[:16],
           "how": "Derived layer (RULES S2): the transcript is untouched; s/e are character offsets into turns[i].text. "
                  "People: kind person, shown as said, never stored in names.json except as a fingerprint.",
           "counts": dict(Counter(s["kind"] for s in spans)), "spans": spans}
    if write:
        os.makedirs(LAYER_DIR, exist_ok=True)
        io.open(os.path.join(LAYER_DIR, date + ".json"), "w", encoding="utf-8").write(
            json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return out


def glossary(date, nm=None, limit=60):
    """Short 'names in this lesson' list for the AI readers' prompts (kept in memory; never written to disk)."""
    try:
        lay = layer(date, nm, write=False)
    except (OSError, ValueError):
        return ""
    seen, rows = {}, []
    for s in lay["spans"]:
        if s["kind"] == "person":
            k = ("person", ar_norm(s["text"]) if is_ar(s["text"]) else lat_norm(s["text"]))
            label = f'{s["text"]} = a person\'s name'
        else:
            k = ("id", s["id"])
            en = (s.get("en") or "").strip()
            what = {"place": "place", "country": "nationality" if s.get("sub") == "nationality" else "country", "other": "name"}[s["kind"]]
            label = f'{s["text"]}' + (f' ({s["ar"]})' if s.get("ar") and s["ar"] != s["text"] else "") + f' = {en} ({what})'
        if k not in seen:
            seen[k] = label
            rows.append(label)
    if not rows:
        return ""
    return ("Names in this lesson (proper names, not vocabulary - never gloss them word by word, never count or flag them as "
            "wrong or unknown words; a name split across scripts such as 'رام Allah' is still ONE name): " + "; ".join(rows[:limit]) + ".")


# ------------------------------------------------------------------ possible names (auto-spotting)
PREP_LAT = {"fi", "fe", "min", "mn", "3a", "3al", "3ala", "la", "li", "lal", "b", "bi", "bil", "3end"}   # Arabizi only (English "to" takes verbs)
PREP_AR = {ar_norm(w) for w in "في من ع على عند ل لل ب".split()}
WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march", "april",
            "may", "june", "july", "august", "september", "october", "november", "december", "i", "i'm", "i've", "i'll", "i'd",
            "okay", "ok", "oh", "yeah", "yes", "no", "so", "and", "but", "the", "english", "arabic", "farsi", "persian", "google",
            "whatsapp", "zoom", "chatgpt", "quizlet", "anees", "god", "huh", "lol", "hmm", "mm", "wow", "celsius", "fahrenheit"}
AR_SUFFIX_LAT = re.compile(r"(?:iyyin|iyin|yeen|yin|iyye|iyyeh|yye|een|in|at|ha|hum|na|ak|ik|o|i)$")


def _sentence_of(text, s, e):
    a = max(text.rfind(c, 0, s) for c in ".?!؟\n") + 1
    b = min([x for x in (text.find(c, e) for c in ".?!؟\n") if x >= 0] or [len(text)])
    return text[a:b + 1].strip()[:240]


def possible(write=True):
    """Tokens that match neither a name nor Amal's words and look like names -> docs/data/possible-names.json."""
    import build_sentence_ladder as L
    nm = load()
    bk = L.bank()
    data = json.load(io.open(OUT, encoding="utf-8"))
    rejected = set(data.get("not_names") or [])
    en_skip = {lat_norm(v.get("en") or "") for v in data.get("vocab") or []} | {lat_norm(v.get("arabizi") or "") for v in data.get("vocab") or []}
    en_skip |= {lat_norm(x) for e in data["entries"] for x in (e.get("v") or []) + (e.get("cap") or []) if not is_ar(x)}
    en_skip.discard("")
    cands = {}
    for date in lesson_dates():
        doc = json.load(io.open(os.path.join(DATA, "lessons", date + ".json"), encoding="utf-8"))
        for ti, t in enumerate(doc.get("turns") or []):
            text = t.get("text") or ""
            who = t.get("who")
            taken = [(sp["s"], sp["e"]) for sp in nm.find(text)]
            toks = tokens(text)
            for j, (s, e, raw, sc) in enumerate(toks):
                if any(a <= s < b for a, b in taken):
                    continue
                n = norm_tok(raw, sc)
                if len(n) < 3 or n.isdigit() or re.search(r"\d", n) and sc == "lat" and not re.search("[a-z]{3}", n):
                    continue
                if sc == "lat":
                    low = raw.lower().replace("’", "'")
                    if re.search(r"\d", n) or "'" in low or low in L.EN_WORDS or n in en_skip or                             text[max(0, s - 1):s] == "‹" or text[e:e + 1] == "›":
                        continue                      # Arabizi with digits, contractions (I'll), ‹quoted› words, known English
                    stem = AR_SUFFIX_LAT.sub("", n)
                    if len(stem) >= 3 and (bk.keys_lat(stem)[0] or stem in en_skip):
                        continue                      # her word + an ending (Iraniyin, Iranyeen)
                    if n in L.EN_WORDS or n in WEEKDAYS or n in L.FILLER_LAT or L.latin_kind(raw, bk) == "fill":
                        continue
                    if bk.keys_lat(n)[0] or n in L.LAT_AR or n in L.LAT_FN:
                        continue
                else:
                    if bk.keys_ar(L.an(raw))[0] or L.an(raw) in L.FN_AR or L.FILLER_AR.match(L.an(raw)):
                        continue
                prev = norm_tok(toks[j - 1][2], toks[j - 1][3]) if j else ""
                before = text[:s].rstrip()
                sent_start = (not before) or before[-1] in ".?!؟:\"“-—]…" or (j and toks[j - 1][3] == "lat" and prev in LAT_ART and not text[:toks[j - 1][0]].strip())
                sig = set()
                if sc == "lat" and raw[:1].isupper() and not raw.isupper() and not sent_start:
                    sig.add("chat_cap" if who == "chat" else "capital")
                if prev in (PREP_LAT if sc == "lat" else PREP_AR) or (j >= 2 and prev == "3end" and norm_tok(toks[j - 2][2], toks[j - 2][3]) == "min"):
                    sig.add("after_fi_min")
                if not sig:
                    continue
                if sc == "lat" and "capital" not in sig and "chat_cap" not in sig and L.EN_SUFFIX.search(n):
                    continue
                c = cands.setdefault(n, {"key": n, "fp": fp((n,)), "forms": Counter(), "signals": Counter(), "dates": set(), "hits": 0,
                                         "examples": []})
                if c["fp"] in rejected:
                    continue
                c["forms"][raw] += 1
                c["signals"].update(sig)
                c["dates"].add(date)
                c["hits"] += 1
                if len(c["examples"]) < 3 and not any(x["date"] == date and abs(x["t"] - float(t.get("t") or 0)) < 5 for x in c["examples"]):
                    c["examples"].append({"date": date, "t": round(float(t.get("t") or 0), 1), "who": t.get("typed_by") or who if who == "chat" else who,
                                          "chat": who == "chat", "sentence": _sentence_of(text, s, e), "word": raw})
    items = []
    for c in cands.values():
        if c["fp"] in rejected:
            continue
        sig = c["signals"]
        lat = not is_ar(c["key"])
        strong = sig.get("capital", 0) + sig.get("chat_cap", 0)
        # Latin: capitalised mid-sentence (or typed so by Amal). Arabic script has no capitals: after fi / min AND heard in
        # 3+ lessons (one-off Arabic words after a preposition are mostly engine slips, not names).
        if lat and not strong:
            if not (sig.get("after_fi_min") and len(c["dates"]) >= 2):
                continue
        if not lat and len(c["dates"]) < 3:
            continue                                  # Arabic script has no capitals: after fi / min in 3+ lessons
        if lat and strong and not sig.get("chat_cap") and not sig.get("after_fi_min") and                 not ((len(c["dates"]) >= 2 and c["hits"] >= 2) or c["hits"] >= 3):
            continue                                  # capitalised once in one lesson: too thin
        kind = "place" if sig.get("after_fi_min", 0) >= max(1, c["hits"] // 2) else "person"
        score = 2 * sig.get("chat_cap", 0) + sig.get("capital", 0) + sig.get("after_fi_min", 0) + 2 * (len(c["dates"]) - 1)
        items.append({"cand": c["fp"], "text": c["forms"].most_common(1)[0][0], "kind_guess": kind, "signals": dict(sig),
                      "lessons": len(c["dates"]), "hits": c["hits"], "score": score,
                      "examples": sorted(c["examples"], key=lambda x: (x["date"], x["t"]))})
    items.sort(key=lambda x: (-x["score"], -x["lessons"], x["text"]))
    items = items[:80]
    out = {"version": VERSION, "generated": dt.datetime.now().isoformat(timespec="seconds"), "names_sha": (names_sha() or "")[:16],
           "how": "Tokens on no names list and not Amal's words that look like names: capitalised mid-sentence (Latin), typed "
                  "capitalised in the Meet chat, after fi / min / 3a / la / min 3end, seen in 2+ lessons. Medi taps Name / Not a "
                  "name (supabase name_labels, migration 021); the next build reads the answers. kind_guess: after fi/min = place, "
                  "otherwise person (a confirmed person is stored only as a fingerprint).",
           "n": len(items), "items": items}
    if write:
        io.open(POSSIBLE, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=0))
        print("wrote", POSSIBLE, len(items), "possible names")
    return out


# ------------------------------------------------------------------ vocab events that fall on a name (for the overlay owner)
def vocab_events(nm=None):
    """word-bank-evidence.json events whose word sits inside a name span of its own row text. Row items are numbered
    row+2, row+4 ... per word when the ids allow it; otherwise the event counts only when every occurrence of its word in
    the row is inside a name."""
    nm = nm or load()
    ev = json.load(io.open(os.path.join(DATA, "word-bank-evidence.json"), encoding="utf-8"))["events"]
    out = []
    for e in ev:
        row = next((c for c in e.get("context") or [] if c.get("row_id") == e.get("row_id")), None)
        if not row:
            continue
        text = row.get("text") or ""
        spans = nm.find(text)
        if not spans:
            continue
        toks = [t for t in tokens(text)]
        word = (e.get("original_text") or e.get("text") or "").strip()
        wt = tokens(word)
        if not wt:
            continue
        wn = norm_tok(wt[0][2], wt[0][3])
        occ = [k for k, t in enumerate(toks) if norm_tok(t[2], t[3]) == wn or norm_tok(t[2], t[3]).endswith(wn)]
        inside = lambda k: next((sp for sp in spans if sp["s"] <= toks[k][0] < sp["e"] or toks[k][0] <= sp["s"] < toks[k][1]), None)
        pick = None
        m_row = re.search(r":row:(\d+)$", e.get("row_id") or "")
        m_it = re.search(r":item:(\d+)$", (e.get("item_ids") or [""])[0])
        if m_row and m_it:
            k = (int(m_it.group(1)) - int(m_row.group(1))) // 2
            if 0 <= k < len(toks) and k in occ:
                pick = inside(k)
                if pick is None:
                    continue
        if pick is None:
            hits = [inside(k) for k in occ]
            if not hits or any(h is None for h in hits):
                continue
            pick = hits[0]
        out.append({"id": e["id"], "lesson_date": e.get("lesson_date"), "t": round(e.get("t_start") or 0, 1), "speaker": e.get("speaker"),
                    "word": word, "word_key": e.get("word_key"), "assessment": e.get("assessment"),
                    "name": pick["text"], "name_kind": pick["kind"], "name_en": pick.get("en"), "name_id": pick.get("id")})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "build", "layer", "possible", "vocab-events", "find", "keyterms", "all"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch()
    elif a.cmd == "build":
        build()
    elif a.cmd in ("layer", "all"):
        if a.cmd == "all":
            build()
        nm = load()
        tot = Counter()
        for d in (a.args if a.cmd == "layer" and a.args else lesson_dates()):
            lay = layer(d, nm)
            tot.update(lay["counts"])
            print(d, lay["counts"], sum(1 for s in lay["spans"] if s.get("mixed")), "mixed")
        print("total", dict(tot))
        if a.cmd == "all":
            possible()
    elif a.cmd == "possible":
        possible()
    elif a.cmd == "vocab-events":
        rows = vocab_events()
        out = os.path.join(REPO, "data", "lesson-work", "vocab-events-on-names.json")
        io.open(out, "w", encoding="utf-8").write(json.dumps({"generated": dt.datetime.now().isoformat(timespec="seconds"),
                                                                "n": len(rows), "events": rows}, ensure_ascii=False, indent=1))
        print("wrote", out, len(rows))
    elif a.cmd == "find":
        for sp in load().find(" ".join(a.args)):
            print(json.dumps(sp, ensure_ascii=False))
    elif a.cmd == "keyterms":
        k = load().keyterms((a.args or ["amal"])[0])
        print(len(k))
        print(json.dumps(k[:60], ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
