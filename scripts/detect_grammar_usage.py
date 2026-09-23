# -*- coding: utf-8 -*-
"""Count every time Medi USES a grammar rule, not just the times he got it wrong.

The first audit only looked for Amal's corrections, so a rule he uses
correctly in every lesson - saying the date, the clock, a b-verb - scored
zero and showed as Untested. This walks his own Arabic and marks each
bucket's pattern where it fires.

Output: docs/data/grammar-usage.json
"""
import json, os, re, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ANEES = r"C:\dev\anees\data\lessons"
DOCS = r"C:\dev\anees-hourly\docs"
OUT = os.path.join(DOCS, "data", "grammar-usage.json")

# Reuse the auditor's turn readers so both scripts see the same transcripts.
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "audit_grammar_lessons.py"), encoding="utf-8").read()
_ns = {}
exec(_src.split("# ---------------------------------------------------------------- run")[0], _ns)
lesson_turns = _ns["lesson_turns"]
arabic_toks = _ns["arabic_toks"]
norm = _ns["norm"]

W = r"(?:^|\s)"          # word start
E = r"(?=\s|$|[،.؟?!])"  # word end

# One or more patterns per bucket. A hit means Medi produced that structure.
# Patterns are deliberately conservative: a miss is better than a false count.
P = {
 "A1":  [r"(?:^|\s)ال[\u0621-\u064A]{2,}"],
 "A2":  [r"\b(?:بيت|اسم|باب|سيارة|شغل|أخو|بنت|ابن)\s+(?!ال)[\u0621-\u064A]{3,}"],
 "A3":  [r"[\u0621-\u064A]{2,}ت\s+ال[\u0621-\u064A]{2,}"],
 "A4":  [r"\b(?:اسمي|اسمك|اسمها|بيتي|بيتك|بيتها|شغلي|شغلك|عمري|عمرك|حالي|حالك|إلي|إلك)" + E],
 "A5":  [r"\b(?:باب|مفتاح|صاحب)\s+[\u0621-\u064A]{3,}\s+[\u0621-\u064A]{3,}"],
 "A6":  [r"\b(?:دكتور|معلم|أستاذ|مهندس|محامي)\s+[\u0621-\u064A]{3,}"],
 "A7":  [r"\bال[\u0621-\u064A]{2,}\s+ال[\u0621-\u064A]{2,}"],
 "A8":  [r"\b[\u0621-\u064A]{3,}ة" + E, r"\b(?:حلوة|كبيرة|صغيرة|زاكية|تعبانة|جديدة|كتيرة)" + E],
 "A9":  [r"\b(?:بيوت|أيام|ساعات|ولاد|بنات|شبابيك|أبواب|كتب|ألوان|أشياء|ناس|زلام|نسوان)" + E],
 "A9b": [r"\b(?:بيوت|بواب|شبابيك|سيوف|عيون|مكاتب|مساجد)" + E],
 "A10": [r"\b(?:هاد|هادي|هدول|هذا|هذي|هداك|هديك|هاي)" + E],
 "A10b":[r"\b(?:هاد|هادي|هدول|هذا|هذي|هاي)\s+ال[\u0621-\u064A]{2,}"],
 "A11": [r"\bالكل" + E, r"\bكل\s+[\u0621-\u064A]{2,}"],

 "B1":  [r"\b(?:با|بت|بي|بن|ب)[\u0621-\u064A]{3,}" + E],
 "B2":  [r"\b(?:بدي|بدك|بدها|بدنا|لازم|ممكن|بحب|بقدر|بجرب|ببلش)\s+[\u0621-\u064A]{3,}"],
 "B3":  [r"\b(?:لما|إذا|اذا|عشان|قبل ما|بعد ما|رح|راح|حتى)\s+[\u0621-\u064A]{3,}"],
 "B4":  [r"\b(?:بدي|لازم|ممكن|رح)\s+[\u0621-\u064A]{3,}\s+و\s*[\u0621-\u064A]{3,}"],
 "B5":  [r"\b[\u0621-\u064A]{3,}(?:ت|نا|توا|وا)" + E],
 "B6":  [r"\b(?:كان|كانت|كنت|كنا|كانوا)" + E],
 "B7":  [r"\b(?:كان|كنت|كانت|كنا)\s+ب[\u0621-\u064A]{3,}"],
 "B8":  [r"\b(?:أكون|اكون|تكون|يكون|نكون|بكون|بتكون|بيكون)" + E],
 "B9":  [r"\b(?:نكون|يكونوا|تكوني|تكونوا)" + E],
 "B10": [r"\b(?:روح|شوف|تعال|احكي|اشرب|كول|خلص|اعمل|جيب|خود)" + E],
 "B11": [r"\b(?:ما|لا)\s+ت[\u0621-\u064A]{3,}"],
 "B12": [r"\b(?:ببسط|بنبسط|بضحك|بضحّك|بزعل|بزعّل|بتعب|بتعّب|بزهق|بزهّق|بخوف|بجهز|بعصب|انبسط|انبسطت)"],
 "B13": [r"\b(?:رح|راح)\s+[\u0621-\u064A]{3,}"],
 "B14": [r"\bعم\s+ب?[\u0621-\u064A]{3,}"],
 "B15": [r"\b(?:رايح|رايحة|ناسي|ناسية|عارف|عارفة|قاعد|قاعدة|ساكن|شايف|جايب)" + E],
 "B16": [r"\b(?:كان|كانت|كنت)\s+لازم"],
 "B17": [r"\bصارل|\bصار\s+ل"],

 "C1":  [r"\b(?:أنا|انا|هو|هي|إنت|انت|احنا|إحنا)\s+(?!ب|ما|مش|رح)[\u0621-\u064A]{3,}" + E],
 "C2":  [r"\b(?:أكتر|اكتر)\s+(?:إشي|اشي|شي)\s+[\u0621-\u064A]{3,}(?:ه|ها|هم)" + E],
 "C3":  [r"\b(?:أكتر|اكتر|أحسن|احسن|أقل|اقل|أسوأ|أصعب|أسهل|أكبر|أصغر)" + E],
 "C4":  [r"\bمش" + E, r"\bما\s+ب[\u0621-\u064A]{2,}", r"\bأبدا|\bابدا"],
 "C4b": [r"\b(?:أبدا|ابدا)\s+ما\b"],
 "C5":  [r"\bأو" + E, r"\bولا" + E, r"\bبس" + E],
 "C6":  [r"\b(?:لما|إذا|اذا)" + E],
 "C7":  [r"\bاللي" + E, r"\bإللي" + E],
 "C8":  [r"\b(?:شو|وين|ليش|مين|كيف|قديش|كم|إمتى|امتى|لوين)" + E],
 "C9":  [r"\b(?:ب|بي|بت|بن)[\u0621-\u064A]{3,}\s+ال[\u0621-\u064A]{2,}"],
 "C10": [r"\b(?:من وين|لوين|على شو|عن شو|مع مين|لمين|من مين|من إمتى|من امتى|بشو)"],

 "D1":  [r"\b(?:من|على|في|مع|عن)\s+[\u0621-\u064A]{2,}"],
 "D2":  [r"\b(?:بطلب|أطلب|خايف|خايفة|مشتاق|مشتاقة|قلقان|مختلف)\s+(?:من|ل|على|عن)"],
 "D3":  [r"\b(?:معي|معك|معه|معها|منك|منه|منها|منهم|عندي|عندك|عنده|عندها|عليه|عليها|إلي|إلك|إلهم)" + E],
 "D4":  [r"\b[\u0621-\u064A]{3,}(?:ني|لك|لي|له|لها|لهم)" + E],
 "D5":  [r"\b(?:من|على|في|مع|عن)\s+ال[\u0621-\u064A]{2,}", r"\b(?:بال|لل|فال)[\u0621-\u064A]{2,}"],
 "D6":  [r"\b(?:إياه|اياه|إياك|اياك|إياها|اياها)" + E],

 "E1":  [r"\b(?:يومين|ساعتين|شهرين|سنتين|مرتين)" + E,
         r"\b(?:تلات|تلاتة|أربع|أربعة|خمس|خمسة|ست|ستة|سبع|سبعة|تمان|تمانية|تسع|تسعة|عشر|عشرة)\s+[\u0621-\u064A]{2,}"],
 "E2":  [r"\bالساعة" + E, r"\b(?:ونص|و نص|وربع|و ربع|إلا ربع|الا ربع)" + E],
 "E3":  [r"\b(?:دقيقة|دقيقتين|دقايق|ساعة|ساعتين|ساعات|يوم|يومين|أيام)" + E],
 "E4":  [r"\b(?:الاتنين|الإتنين|الثلاثاء|التلاتا|الأربعا|الاربعا|الخميس|الجمعة|السبت|الأحد|الاحد)" + E,
         r"\b(?:اليوم|مبارح|بكرا|الشهر|الأسبوع|الاسبوع|السنة)" + E,
         r"\b(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر|أيلول|تشرين|آب|تموز)" + E],

 "F1":  [r"[عطحخغصق]"],
 "F2":  [],   # cannot be judged from text
 "F3":  [r"[\u0621-\u064A]*[\u0651][\u0621-\u064A]*"],
}

buckets = json.load(open(os.path.join(DOCS, "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]
ids = [b["id"] for b in buckets]
names = {b["id"]: b["name"] for b in buckets}

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
    medi = [t for t in T if t["speaker"] == "Medi" and arabic_toks(t["text"])]
    seen_here = Counter()
    for t in medi:
        txt = t["text"]
        for bid in ids:
            for pat in P.get(bid, []):
                if re.search(pat, txt):
                    seen_here[bid] += 1
                    uses[bid].append({
                        "date": date,
                        "t": round(t["start"], 1),
                        "mmss": "%02d:%02d" % (int(t["start"]) // 60, int(t["start"]) % 60),
                        "said": txt[:300],
                    })
                    break
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
    "method": ("Every Medi turn containing Arabic is matched against each bucket's pattern. "
               "A hit is one USE of that rule, right or wrong - it is not a mistake."),
    "lessons": per_lesson,
    "totals": totals,
    "uses": {k: v for k, v in uses.items()},
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("\nwrote", OUT)
print("rules with at least one use:", len(totals), "of", len(ids))
for bid, n in sorted(totals.items(), key=lambda x: -x[1])[:22]:
    print("  %-5s %-34s %4d" % (bid, names[bid], n))
never = [b for b in ids if not totals.get(b)]
print("\nnever used:", ", ".join(never) if never else "none")
