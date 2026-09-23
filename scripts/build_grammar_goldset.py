# -*- coding: utf-8 -*-
"""Hand-labelled gold set for the grammar detector.

Every Medi turn in two lessons was read by hand together with the 25 s after
it: Amal's voice, and the Meet chat where she types the fixed sentence.
Times are on Medi's track clock AFTER the track-start offset from
tracks/tracks.json (09-17's Medi track starts 93 s after Amal's).

kind:
  grammar  - scored for recall; bucket is the rule she fixed (UNFILED if none fits)
  vocab    - wrong or missing word; never a grammar slip
  pron     - Family F, rule M4; never a grammar slip
  self     - Medi fixed himself; feeds the self-correction chart, not a slip

Output: docs/data/grammar-goldset.json   ("source": "hand")
"""
import json, os

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "grammar-goldset.json")

# date, mm:ss, bucket, kind, channel, what Medi said, how Amal fixed it, note
R = [
# ---- 2026-09-17
("2026-09-17", "02:26", "D3", "grammar", "voice+chat", "عندهم زباين كتير", "عنا / 3indna", ""),
("2026-09-17", "03:09", "A2", "grammar", "chat", "أكل من الـ جنوب أمريكي", "akel min janoob amrica", "idafa, no el- on first term"),
("2026-09-17", "04:22", "D1", "grammar", "voice+chat", "عنده ماي بس", "فيها، not عندها", ""),
("2026-09-17", "07:02", "A1", "grammar", "chat", "daiman behtr, sos behtr", "daymaan beykoon el-sauce bey7re2", "Latin-script"),
("2026-09-17", "08:42", "E4", "grammar", "english", "سبعتاش ... خميس", "It's Thursday first then seventeenth", "date order"),
("2026-09-17", "09:02", "A1", "grammar", "chat", "يوم الخميس", "el-yoam el-5amees", ""),
("2026-09-17", "09:39", "A2", "grammar", "voice", "نفس الجو اليوم", "نفس جو اليوم or نفس اليوم", "he also self-corrected"),
("2026-09-17", "10:00", "A8", "grammar", "voice+english", "بتبدأ / دبات", "بدا - جو so it has to be masculine", ""),
("2026-09-17", "10:58", "A1", "grammar", "voice", "دنيا الجو / دنيا بارد", "الدنيا - either دنيا or جو", ""),
("2026-09-17", "13:22", "B13", "grammar", "voice+chat", "أنا راح أعمله", "إنت كنت راح تعمله / kunet ra7", ""),
("2026-09-17", "21:06", "B5", "grammar", "english", "(not transcribed)", "عم بعمل ... what's he made? عمل", "medi_text_missing"),
("2026-09-17", "22:06", "A11", "grammar", "voice+chat", "(not transcribed)", "تتأسفي / All كل / inti laazem tet2assafi lalkul", "medi_text_missing"),
("2026-09-17", "27:56", "D4", "grammar", "chat", "wala hada ra'ah yita'assif illi / fillik", "ma 7ada ra7 yet2assaflek", "Latin-script"),
("2026-09-17", "29:59", "D1", "grammar", "voice+chat", "ma ba'dar aru ala andik", "either على بيتك or عندك / 3indek", "Latin-script"),
("2026-09-17", "34:39", "B5", "grammar", "english", "kam khutat - is it still present tense?", "It's not present tense, no - have you ruined is past", "Latin-script"),
("2026-09-17", "36:30", "B12", "grammar", "voice+chat", "kharab, kharabit", "خرّبتي أو خرّبت / 5arrabti", "Latin-script"),
("2026-09-17", "36:58", "C2", "grammar", "english", "kharabti or kharabit", "This is pointer", "Latin-script"),
("2026-09-17", "37:54", "B6", "grammar", "voice+chat", "Kan / kanit", "كانوا / kaanu ili", "Latin-script"),
("2026-09-17", "38:22", "D3", "grammar", "voice", "kanuli", "كانوا إلي - no no no", "Latin-script"),
("2026-09-17", "43:22", "C7", "grammar", "voice", "بيصلح كل، كل إشي اللي بيخربه", "ما في كل إشي في الجملة ... اللي بيخربه", ""),
("2026-09-17", "44:57", "D4", "grammar", "voice", "ana kharabit, kharabt kom", "خربتهم", "Latin-script"),
("2026-09-17", "46:29", "B1", "grammar", "english", "Ehna abadan ma kharab na", "We never broke it - Break it (present)", "Latin-script"),
("2026-09-17", "47:22", "B11", "grammar", "voice+chat", "mat kharab po / matet kharab", "ما تخربوه", "Latin-script"),
("2026-09-17", "50:18", "B12", "grammar", "chat", "Kharab el dunya?", "ba5arreb el-denia", "Latin-script"),
("2026-09-17", "51:15", "B1", "grammar", "voice+chat", "lama khatibti tistamali", "Istamel / testa3mel", "Latin-script"),
("2026-09-17", "54:15", "B12", "grammar", "voice", "khawaf", "Al film kan bakhawaf", "Latin-script both sides"),
("2026-09-17", "57:15", "B15", "grammar", "voice", "inti bitibisti?", "Inti mabsuta?", "Latin-script both sides"),
("2026-09-17", "59:49", "D2", "grammar", "voice", "tadait, tadaitni / ma tadaitni", "Ma tdaya' minni", "Latin-script both sides"),
("2026-09-17", "60:35", "B12", "grammar", "voice", "ma tadaitini", "Ma dday'ini", "Latin-script both sides"),
("2026-09-17", "61:25", "B10", "grammar", "voice", "Taghiri blouzeti", "No t bas ghayiri", "Latin-script both sides"),
("2026-09-17", "62:06", "B11", "grammar", "voice", "wazayini", "Ma. -> ma tawazayini", "Latin-script both sides"),
("2026-09-17", "02:19", "VOCAB", "vocab", "chat", "الـ صباح", "el-subu7", ""),
("2026-09-17", "04:22", "VOCAB", "vocab", "voice+chat", "شوي", "خفيف", ""),
("2026-09-17", "06:32", "VOCAB", "vocab", "voice+chat", "sijal", "سجق / sujo2", ""),
("2026-09-17", "11:25", "VOCAB", "vocab", "voice", "ما قايمة", "مغيمة", ""),
("2026-09-17", "12:22", "VOCAB", "vocab", "voice", "زبال", "غبرة", ""),
("2026-09-17", "41:28", "VOCAB", "vocab", "chat", "ما تارات", "ma66arat", ""),
("2026-09-17", "07:13", "B8", "self", "self", "daiman behtr", "Daiman bykon", ""),
("2026-09-17", "08:31", "E4", "self", "self", "سبعتين", "سبعتاش", ""),
("2026-09-17", "30:52", "B10", "self", "self", "bit'assif or it'assifi", "(Amal: ممتاز)", ""),
# ---- 2026-09-21
("2026-09-21", "02:44", "B5", "grammar", "voice", "أتعلم-- بتعلمه؟", "تعلمتها", ""),
("2026-09-21", "06:46", "E4", "grammar", "chat", "تسعة آلافين تسعة وعشرين", "tes3a alfain u sitte u 3eshreen", ""),
("2026-09-21", "07:59", "A8", "grammar", "voice", "pantalón خضرا", "أخضر", ""),
("2026-09-21", "08:49", "A4", "grammar", "chat", "بلوزة نص كم", "bluzti noss kum", ""),
("2026-09-21", "09:00", "D3", "grammar", "voice", "عندهم", "عنا", ""),
("2026-09-21", "09:24", "E1", "grammar", "voice+chat", "تلاتين أيام", "تلاتين ... يوم / talateen yoam", ""),
("2026-09-21", "09:41", "D1", "grammar", "voice+chat", "نحتاج jacket / عندهم؟", "نحتاج الـ jacket فيهم / ne7taajhom fihom", ""),
("2026-09-21", "11:24", "B1", "grammar", "english+chat", "بتغير", "They change / byet8ayyaru", ""),
("2026-09-21", "12:48", "C7", "grammar", "english+chat", "أكلت الـ pizza دول", "The pizza that remained / el-pizza illi dallat", ""),
("2026-09-21", "12:56", "A2", "grammar", "chat", "الـ آخر الأسبوع", "min 2aa5er el-usboo3", ""),
("2026-09-21", "14:26", "B1", "grammar", "voice", "كل الـ fire department وambulance آجوا", "بيجو", ""),
("2026-09-21", "14:43", "A8", "grammar", "english", "دلوا", "Pizza is one ... feminine", ""),
("2026-09-21", "16:43", "A7", "grammar", "voice+chat", "الحرام pepperoni", "الفلفل الحرام / el-peporony el-7araam", ""),
("2026-09-21", "19:26", "B1", "grammar", "voice+chat", "ما حكينا كتير", "بنحكي / bne7ki", ""),
("2026-09-21", "22:28", "D4", "grammar", "voice+chat", "أستانك", "استناك / astannaaki", ""),
("2026-09-21", "23:53", "A4", "grammar", "voice+chat", "أديش الحق؟ / أديش حقو؟", "قديش حقها. Cuz it's coffee", ""),
("2026-09-21", "24:37", "D1", "grammar", "english", "أدفع ... min credit card?", "Which preposition? B.", ""),
("2026-09-21", "25:19", "D2", "grammar", "voice", "أدفع لهم", "أدفع عن. Pay for.", ""),
("2026-09-21", "26:07", "B10", "grammar", "voice+chat", "فتله", "تفضلي", ""),
("2026-09-21", "28:37", "A10", "grammar", "voice", "هذا الأكلة", "هذي الأكلة. هذي is for feminine", ""),
("2026-09-21", "29:03", "A8", "grammar", "chat", "مش ذكي", "mish zaakye", ""),
("2026-09-21", "29:21", "D1", "grammar", "voice", "غلط بي / بي ال", "فيها / أو فيها إشي غلط", ""),
("2026-09-21", "32:35", "A8", "grammar", "chat", "hamha mura oo hamida", "ta3emha murr u haamed", "Latin-script"),
("2026-09-21", "32:48", "A4", "grammar", "voice", "il ta-tam, tam mur", "طعمها. You said first.", "Latin-script"),
("2026-09-21", "38:10", "UNFILED", "grammar", "voice+chat", "mashhur bi atbuk", "في ... Noun is طبخ / bi el-tabe5", "verb->noun after a preposition; no bucket fits"),
("2026-09-21", "39:25", "D4", "grammar", "english", "ta'alami-- ta'alamathni", "Me. She taught me", "Latin-script"),
("2026-09-21", "40:03", "B16", "grammar", "voice+chat", "hadi mish lazim", "إنه ما كان لازم", "Latin-script"),
("2026-09-21", "41:01", "A8", "grammar", "voice", "bibi'u", "بتبيع because شركة is [feminine]", "Latin-script"),
("2026-09-21", "41:06", "C2", "grammar", "voice+chat", "bitbi'a il-roz", "بتبيعه / betbi3o", "Latin-script"),
("2026-09-21", "41:15", "A8", "grammar", "voice", "bigassel", "بتغسل", "Latin-script"),
("2026-09-21", "42:47", "B8", "grammar", "voice+chat", "lama ana kasul", "بكون / lamma ana bakoon kasool", "Latin-script"),
("2026-09-21", "43:03", "B1", "grammar", "voice+chat", "أساهم", "بستعمل / basta3mel", "ASR garbled his verb"),
("2026-09-21", "43:41", "B1", "grammar", "voice", "أنا أعمل، أعمله", "بعمله", ""),
("2026-09-21", "43:53", "A7", "grammar", "chat", "الطريقة طويل له", "el-tari2a el-taweela", ""),
("2026-09-21", "44:22", "B1", "grammar", "voice", "أطبخ، أطبخه", "بطبخه", ""),
("2026-09-21", "44:43", "E2", "grammar", "voice", "ثلث ساعية", "ثلث ساعة", ""),
("2026-09-21", "48:59", "A2", "grammar", "voice", "بالعكس المقلاة", "عكس الملعقة", ""),
("2026-09-21", "49:42", "E3", "grammar", "voice+chat", "aktar min thalath saa", "ثلاث ساعات / talat saa3aat", "Latin-script"),
("2026-09-21", "51:08", "A7", "grammar", "voice+chat", "hadi nar", "نار هادية / naar haadye", "Latin-script"),
("2026-09-21", "52:25", "A1", "grammar", "voice", "ihna Iraniyin", "إحنا الإيرانيين", "Latin-script"),
("2026-09-21", "55:16", "A1", "grammar", "voice", "alam", "العالم", "Latin-script"),
("2026-09-21", "56:33", "D3", "grammar", "voice", "'andhum", "عنا", "Latin-script"),
("2026-09-21", "56:55", "D1", "grammar", "voice", "il ta'am mashhoor min Iran", "فيه -> Fi Iran", "Latin-script"),
("2026-09-21", "57:12", "C4", "grammar", "voice", "Mish anna akil bihr", "ما عنا", "Latin-script"),
("2026-09-21", "60:41", "A2", "grammar", "english", "il ta'am il samak bihr", "one L. Where do I put the L? It's just one.", "Latin-script"),
("2026-09-21", "63:03", "C3", "grammar", "voice", "رزنا أحسن من الـ دنيا", "أحسن رز في الدنيا", ""),
("2026-09-21", "64:45", "C4", "grammar", "voice+chat", "بس مش عندك إيراني", "ما عندكم", "also D3 (-ak to -kom)"),
("2026-09-21", "65:57", "C3", "grammar", "english", "So مطعم...", "The best first.", ""),
("2026-09-21", "66:00", "A9", "grammar", "english+chat", "أحسن مطعم الإيراني", "Restaurants. / a7san ma6aa3em Iranyeen", ""),
("2026-09-21", "66:59", "B1", "grammar", "voice", "يفـ-- دفدوا", "بيفتحوا", ""),
("2026-09-21", "01:43", "VOCAB", "vocab", "voice+chat", "متوتر", "مضغوط", ""),
("2026-09-21", "03:30", "VOCAB", "vocab", "voice", "كامل نسيتو", "كليًا", ""),
("2026-09-21", "04:18", "VOCAB", "vocab", "voice", "مرجة", "نراجع / مراجعة", ""),
("2026-09-21", "06:13", "VOCAB", "vocab", "voice", "ربيع", "خريف", ""),
("2026-09-21", "26:46", "VOCAB", "vocab", "voice+chat", "يا تيك يا راسي", "الله يعافيك", ""),
("2026-09-21", "43:46", "VOCAB", "vocab", "voice", "الـ طريق", "الطريقة", ""),
("2026-09-21", "46:23", "VOCAB", "vocab", "voice", "زبداية", "زبدة", ""),
("2026-09-21", "48:33", "VOCAB", "vocab", "voice", "الـ تحت تاني", "تحت is just under", ""),
("2026-09-21", "51:02", "VOCAB", "vocab", "voice", "sot asir", "مش صوت", ""),
("2026-09-21", "51:45", "VOCAB", "vocab", "voice", "mishtihi", "مستوي", ""),
("2026-09-21", "62:14", "VOCAB", "vocab", "voice", "مخية", "مقلوبة", ""),
("2026-09-21", "18:11", "F2", "pron", "voice+chat", "نشاف", "ناشف", ""),
("2026-09-21", "07:31", "F", "pron", "voice", "pantalón", "بنطلون", ""),
("2026-09-21", "15:32", "B5", "self", "self", "ما أقدر، أقدرت", "قدرت", ""),
("2026-09-21", "52:19", "A9", "self", "self", "ihna Irani", "Iraniyin", ""),
]


def build():
    ev = []
    for d, mmss, b, k, ch, said, corr, note in R:
        m, s = mmss.split(":")
        ev.append({
            "date": d, "t": int(m) * 60 + int(s), "mmss": mmss, "bucket": b, "kind": k,
            "channel": ch, "said": said, "correction": corr, "note": note,
            "medi_text_missing": "medi_text_missing" in note,
            "latin_script": "Latin-script" in note, "source": "hand",
        })
    g = [e for e in ev if e["kind"] == "grammar"]
    out = {
        "updated": "2026-09-23", "source": "hand",
        "method": ("Every Medi turn in two lessons read by hand with the 25 s after it - Amal's voice and "
                   "her Meet chat. Times are on Medi's track after the track-start offset. Only kind=grammar "
                   "is scored for recall; vocab, pron (Family F, rule M4) and self are kept, never scored as grammar."),
        "lessons": {d: {"grammar": sum(1 for e in g if e["date"] == d)} for d in sorted({e["date"] for e in ev})},
        "counts": {k: sum(1 for e in ev if e["kind"] == k) for k in ("grammar", "vocab", "pron", "self")},
        "events": ev,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    o = build()
    print(o["lessons"], o["counts"])
