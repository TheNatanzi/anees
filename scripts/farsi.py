"""Farsi side conversation detector (Medi 2026-09-28: "this is farsi talking to my dad he interrupted my lesson").

A turn with >= 2 Persian signals (letters پ چ ژ گ ی ک, ZWNJ, Persian-only words, می + verb) is not the lesson.
Words that are also everyday Levantine/MSA are deliberately not signals, so an Arabic line never trips it.
Used by audit_vocab_unresolved.py (vocab), build_sentence_ladder.py (ladder) and detect_grammar_usage.py (grammar)."""
import re
import unicodedata

MIN_SIGNALS = 2


def fold(s):
    s = unicodedata.normalize('NFKC', str(s or ''))
    s = re.sub(r'[ً-ٰٟـ]', '', s)
    return s.replace('ی', 'ي').replace('ک', 'ك').replace('ى', 'ي').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه').lower()


FA_LETTERS = {'پ': 'pe', 'چ': 'che', 'ژ': 'zhe', 'گ': 'gaf', 'ی': 'fa_ye', 'ک': 'fa_kaf', '‌': 'zwnj'}
# Persian-only function words and verb forms. Words that are also everyday Levantine/MSA (من ما هم با به تو ده الان خوب مي ...)
# are deliberately left out so an Arabic line never scores on them.
FA_WORDS = {fold(w) for w in (
    'رو', 'است', 'هست', 'نیست', 'این', 'اون', 'بیرون', 'پنجره', 'خیلی', 'چی', 'کجا', 'چرا', 'چطور', 'روشنه', 'خاموش',
    'دارم', 'داری', 'برو', 'بیا', 'بکن', 'باشه', 'چیه', 'کیه', 'اینجا', 'اونجا', 'دیروز', 'فردا', 'بابا', 'مامان', 'ولی',
    'چون', 'خوبه', 'رسیده', 'بندی', 'ببند', 'جان', 'جون', 'میرم', 'میری', 'میره', 'میام', 'میاد', 'میخوام', 'میخوای', 'میکنم',
    'میکنی', 'میکنه', 'میگم', 'میگی', 'میگه', 'میدونم', 'نمیدونم', 'میشه', 'نمیشه', 'بشین', 'بخور', 'بریم', 'کردم', 'کردی',
    'رفتم', 'اومدم', 'بگو', 'ببین', 'نکن', 'خونه', 'یکی', 'هفتاد')}
MI_VERB = re.compile(r'(?:^|[\s،,.])ن?مي[\s‌][؀-ۿ]{2,}')


def farsi_signals(text):
    t = str(text or '')
    sig = {n for ch, n in FA_LETTERS.items() if ch in t}
    for w in re.findall(r'[؀-ۿ‌]+', t):
        if fold(w) in FA_WORDS:
            sig.add('w:' + fold(w))
    if MI_VERB.search(fold(t)):
        sig.add('mi+verb')
    return sig


def is_farsi(text):
    """True when the text has at least MIN_SIGNALS Persian signals."""
    return len(farsi_signals(text)) >= MIN_SIGNALS
